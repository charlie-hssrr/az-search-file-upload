import asyncio
import logging
import json
import os
from redis.asyncio import Redis

from core.websockethelper import WebSocketHelper

async def process_job(redis, job_id, redis_completion_channel):
    job_data_bytes = await redis.hgetall(job_id)
    # Asynchronously retrieves all fields and values of the hash stored at job_id in Redis.
    # `job_data` is a dictionary where each key-value pair corresponds to a field and its value in the hash.

    job_data = {key.decode('utf-8'): value.decode('utf-8') for key, value in job_data_bytes.items()}
    # Convert the byte keys and values to strings.
    
    logging.info(f"job_data: {job_data}")
    
    script_path = job_data.get("script_path")
    # Extracts the script path from the job data. This is the path to the script that needs to be executed.

    if not script_path:
        logging.error(f"Script path for job {job_id} is None or missing.")
    
    args = json.loads(job_data.get("args", "[]"))
    # Deserializes the JSON-encoded argument list from the job data. If "args" is not present, defaults to an empty list.
    
    if script_path and os.path.exists(script_path) and os.access(script_path, os.X_OK):
        # Checks if the script_path is not None, exists on the filesystem, and is executable.
        
        command = [script_path] + args
        # Constructs the command to be executed by combining the script path with any arguments.
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Asynchronously starts a subprocess to execute the command. It captures the output and error streams,
        # and specifies that the output should be treated as text (strings) instead of bytes.
        
        stdout, stderr = await process.communicate()  # Wait for the subprocess to finish
        # Asynchronously waits for the subprocess to complete and captures its stdout and stderr.
        
        output = stdout.decode('utf-8') if stdout else ''
        error = stderr.decode('utf-8') if stderr else ''

        completion_status = "completed" if process.returncode == 0 else "failed"
        # Determines the completion status of the job based on the subprocess's return code.

        logging.info(f"Script worker process {completion_status}")
    else:
        logging.error(f"Invalid script path: {script_path}")
        
        completion_status = "failed"
        output = ""
        error = f"Invalid script path: {script_path}"

    await redis.publish(redis_completion_channel, json.dumps({
        "job_id": job_id,
        "status": completion_status,
        "output": output,
        "error": error
    }))
    # Asynchronously publishes a message to the Redis channel `COMPLETION_CHANNEL`. The message is a JSON-encoded
    # string containing the job ID, completion status, output, and error information. This message notifies other
    # parts of the application (or other applications) about the completion and result of the job.


async def job_complete(redis_url, redis_completion_channel):
    # This static method listens for job completion messages on the specified Redis channel.
    # It subscribes to the channel and continuously checks for new messages.

    # Establish a Redis connection using the provided URL.
    subscriber = Redis.from_url(redis_url)

    pubsub = subscriber.pubsub()
    # Initialize a pub/sub object for the Redis connection.

    await pubsub.subscribe(redis_completion_channel)
    # Subscribe to the completion channel.

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        # Wait for a new message on the subscribed channel.

        if message:
            data = json.loads(message['data'])
            # Deserialize the message data from JSON format into a Python object.
            
            complete_message = f"Job complete: {data}"
            logging.info(f"{complete_message}")
            # Log the received message data for debugging and verification purposes.

            await WebSocketHelper.broadcast(complete_message)
            # Call the broadcast method using the class name WebSocketHelper
            # and await its completion since it's an async method.
        # Check if a message has been received.

        await asyncio.sleep(1)
        # Introduce a short sleep to prevent a busy loop and allow other coroutines to run.

        # Note: Exception handling, message processing, reconnection logic, and resource cleanup
        # should be added as needed for a complete and robust implementation.
    # Enter an infinite loop to continuously listen for messages.

async def worker(redis_url, redis_queue_name, redis_completion_channel):
    async with Redis.from_url(redis_url) as redis:
        # Establishes an asynchronous context manager for a Redis connection.
        # This creates a Redis client connected to the specified REDIS_URL
        # and ensures the connection is closed automatically when the block is exited.
        
        logging.info(f"Redis worker - URL: {redis_url}, Queue: {redis_queue_name}, Completion Ch: {redis_completion_channel}")
        
        while True:
            # Starts an infinite loop to continuously process jobs from the Redis queue.
            
            job_id_bytes = await redis.brpoplpush(redis_queue_name, f"{redis_queue_name}:processing", timeout=0)
            # Waits (asynchronously) for a job ID to appear in the Redis list named QUEUE_NAME.
            # Once a job ID appears, it atomically removes the job ID from QUEUE_NAME
            # and pushes it to another list named "{QUEUE_NAME}:processing".
            # This operation blocks until a job is available if the queue is empty (timeout=0 means it waits indefinitely).
            
            job_id = job_id_bytes.decode('utf-8')
            # Decodes the job ID from bytes to a UTF-8 string.
            # This is necessary because Redis stores and returns data as bytes,
            # but the job ID needs to be a string for further processing.
            
            await process_job(redis, job_id, redis_completion_channel)
            # Calls the asynchronous function `process_job`, passing the Redis client and the decoded job ID.
            # This function is responsible for processing the job identified by job_id.
            
            await redis.lrem(f"{redis_queue_name}:processing", 0, job_id)
            # Removes the job ID from the "{QUEUE_NAME}:processing" list after processing is complete.
            # The number 0 indicates that all instances of job_id should be removed from the list.

if __name__ == "__main__":
    asyncio.run(worker())
