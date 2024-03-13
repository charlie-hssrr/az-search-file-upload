import asyncio
from ctypes import Union
import logging
import os
from pathlib import Path

from quart import (
    Blueprint,
    Quart,
    current_app,
    jsonify,
    request,
    websocket
)

from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential

from core.uploadFiles import allowed_file, save_file
from core.scripthelper import ScriptHelper
from core.redisworker import worker, job_complete
from core.websockethelper import WebSocketHelper

bp = Blueprint("routes", __name__, static_folder="static")

@bp.route("/config", methods=["GET"])
def config():
    return jsonify(
        {
            "azure_storage_container": current_app.config["azure_storage_container"],
            "azure_storage_account": current_app.config["azure_storage_account"],
            "redis_url": current_app.config["redis_url"],
            "redis_queue": current_app.config["redis_queue"],
            "redis_completion_channel": current_app.config["redis_completion_channel"]
        }
    )

@bp.route("/ping", methods=["GET"])
def ping():
    return jsonify(
        {
            "pong": "bozo",
        }
    )

@bp.route('/upload', methods=['POST', 'GET'])
async def fileUpload():
    files = await request.files
    
    uploaded_files = files.getlist('files')
    logging.info(f"Received files: {[file.filename for file in uploaded_files]}")

    errors = {}
    success = False

    for file in uploaded_files:
        if file and allowed_file(file.filename):
            saved_filename = await save_file(file)
            logging.info(f"saved_filename {saved_filename}")
            success = True
        else:
            errors[file.filename] = 'Invalid file type'
            
    if success:
        try:
            job_id, _, _ = await ScriptHelper.enqueue_script_job(
                'prepdocs.sh', 
                redis_url=current_app.config["redis_url"],
                redis_queue_name=current_app.config["redis_queue"],
            )
            
            return jsonify({
                "message": "Files successfully uploaded", 
                "job_id": job_id
            })
        except Exception as e:
            logging.error(f"Failed to enqueue script: {str(e)}")
            return jsonify({"message": "Failed to start the script processing", "status": 'failed'}), 500
    elif errors:
        return jsonify(errors), 500

@bp.route('/blobs', methods=['GET'])
async def fetch_blobs():
    blob_container_client = current_app.config["blob_container_client"]
    blobs = []
    try:
        async for blob in blob_container_client.list_blobs():
            blob_client = blob_container_client.get_blob_client(blob.name)
            properties = await blob_client.get_blob_properties()

            blob_detail = {
                "name": blob.name,
                "blobType": properties.blob_type,
                "contentLength": properties.size,
                "contentType": properties.content_settings.content_type,
                "contentEncoding": properties.content_settings.content_encoding,
                "contentLanguage": properties.content_settings.content_language,
                "cacheControl": properties.content_settings.cache_control,
                "leaseStatus": properties.lease.status,
                "leaseState": properties.lease.state,
                "leaseDuration": properties.lease.duration,
                "lastModified": properties.last_modified.isoformat() if properties.last_modified else None,
                "etag": properties.etag,
                "serverEncrypted": properties.server_encrypted,
                "archiveStatus": properties.archive_status,
                "customerProvidedKeySha256": properties.encryption_key_sha256,
                "encryptionScope": properties.encryption_scope,
                "isServerEncrypted": properties.server_encrypted,
                "tags": properties.tag_count,
                "versionId": properties.version_id,
                "isLatestVersion": properties.is_current_version
            }
            blobs.append(blob_detail)

        return jsonify(blobs)
    except ResourceNotFoundError as e:
        logging.error(f"Failed to fetch blobs: {str(e)}")
        return jsonify({"message": "Failed to fetch blobs", "status": 'failed'}), 500

@bp.before_app_serving
async def setup_clients():
    # Replace these with your own values, either in environment variables or directly here
    AZURE_STORAGE_ACCOUNT = "[yourstoragename]"
    AZURE_STORAGE_CONTAINER = "[yourcontainername]"
    REDIS_URL = "redis://localhost"
    REDIS_QUEUE_NAME="script_queue"
    REDIS_COMPLETION_CHANNEL = "script_completion_channel"

    current_app.config["redis_url"] = REDIS_URL
    current_app.config["redis_queue"] = REDIS_QUEUE_NAME
    current_app.config["redis_completion_channel"] = REDIS_COMPLETION_CHANNEL
    current_app.config["azure_storage_container"] = AZURE_STORAGE_CONTAINER
    current_app.config["azure_storage_account"] = AZURE_STORAGE_ACCOUNT

    azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", credential=azure_credential
    )
    blob_container_client = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)
    current_app.config["blob_container_client"] = blob_container_client

@bp.after_app_serving
async def close_clients():
    await current_app.config["blob_container_client"].close()

def create_app():
    app = Quart(__name__)
    app.register_blueprint(bp)

    @app.websocket('/ws')
    async def ws():
        await WebSocketHelper.register()
        try:
            while True:
                message = await websocket.receive()
                if message == "job_complete":
                    # Handle completion message from client
                    print("Job completion message received from client")

                # Echo back to client
                await WebSocketHelper.broadcast(f"WS server echo: {message}")
        finally:
            await WebSocketHelper.unregister()

    @app.before_serving
    async def run_redis_worker():
        redis_url = current_app.config['redis_url']
        redis_queue_name = current_app.config['redis_queue']
        redis_completion_channel = current_app.config['redis_completion_channel']

        # Start the worker as a background task
        app.redis_worker_task = asyncio.create_task(worker(
            redis_url, 
            redis_queue_name, 
            redis_completion_channel
        ))

        # Start the job_complete listener as another background task
        # This listens for job completion messages notifies any connected clients via Websockets
        app.redis_job_complete_listener_task = asyncio.create_task(job_complete(
            redis_url,
            redis_completion_channel
        ))

    @app.after_serving
    async def shutdown_background_tasks():
        logging.info("Beginning shutdown process, cancelling background tasks...")

        tasks = [app.redis_worker_task, app.redis_job_complete_listener_task]
        
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logging.info(f"Task {task} cancelled successfully.")
            except Exception as e:
                logging.error(f"Error during task cancellation: {e}")

        logging.info("Shutdown process completed.")


    # Folder path to upload files
    app.config['UPLOAD_FOLDER'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'data')
    )

    default_level = "INFO"
    logging.basicConfig(level=os.getenv("APP_LOG_LEVEL", default_level))

    return app
