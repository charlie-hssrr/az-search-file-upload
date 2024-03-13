import json
import logging
import os
import uuid
from redis.asyncio import Redis

class ScriptHelper:
    @staticmethod
    async def enqueue_script_job(script_name, redis_url, redis_queue_name, args=None):
        job_id = str(uuid.uuid4())
        # Generates a unique job identifier using UUID and converts it to a string.

        logging.info(f"Script name provided: {script_name}")
        # Logs the provided script name for debugging purposes.

        # NOTE: Update the path to where your scripts directory with prepdocs.sh is located.
        script_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '..', '..', 'rag-co-pilot', 'app', 'backend', 'scripts', script_name
            )
        )
        # Constructs an absolute path to the script based on a relative path from this file's location.
        # The relative path navigates up one directory and then into a 'scripts' folder.

        logging.info(f"Attempting to use script path: {script_path}")
        # Logs the resolved absolute path to the script for debugging.

        if not script_path or not os.path.exists(script_path) or not os.access(script_path, os.X_OK):
            logging.error(f"Script path is invalid or not executable: {script_path}")
            return None, f"Script path is invalid or not executable: {script_path}", 1
        # Validates the script path: checks if the path is not None, if the file exists, and if it's executable.
        # If any of these checks fail, logs an error and returns None, an error message, and an error code.

        args = args or []
        # Initializes the args list if it wasn't provided.

        args_serialized = json.dumps(args)
        # Serializes the args list to a JSON string for storage in Redis. This allows complex data structures
        # to be passed as arguments.

        logging.info(f"Connecting to Redis at {redis_url}")
        # Logs an attempt to connect to Redis using the specified REDIS_URL.

        try:
            async with Redis.from_url(redis_url, encoding='utf-8') as client:
            # NOTE: with SSL: async with Redis.from_url(redis_url, encoding='utf-8', ssl=True, ssl_cert_reqs=None) as client:
                # Establishes an asynchronous connection to Redis and uses it within a context manager,
                # ensuring the connection is closed automatically after the block.

                await client.hset(job_id, mapping={
                    "script_path": script_path,
                    "args": args_serialized,
                    "status": "queued"
                })
                # Sets multiple hash fields to multiple values for the job in Redis. This includes the script path,
                # serialized arguments, and the job status set to "queued".

                logging.info(f"Pushing to Redis - job ID: {job_id}, queue name: {redis_queue_name}")
                # Logs the successful pushing of the job to Redis, including the job ID and queue name.

                await client.lpush(redis_queue_name, job_id)
                # Pushes the job ID to the left side of the Redis list named QUEUE_NAME, effectively enqueuing it.
        except Exception as e:
            logging.error(f"Failed to enqueue job in Redis: {str(e)}")
            return None, f"Failed to enqueue job in Redis: {str(e)}", 1
            # Catches and logs any exceptions that occur during the Redis operation, then returns None,
            # an error message, and an error code.

        return job_id, None, 0
        # Returns the job ID and None for both the error message and error code upon successful execution.
