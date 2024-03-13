# Redis Message Queues

Description ...

## Asynchronous script processing using Redis message queues

The provided Redis worker class in Python is designed to process jobs asynchronously using Redis for queue management. 
The jobs go through various stages during their lifecycle, as indicated by the code and the operations performed on Redis. 

### Statuses

Here's the correct order of statuses a key (job) can go through during file processing:

1. **Pending in Queue**: Initially, a job ID is placed in a Redis list (queue) specified by `redis_queue_name`. 
    This is the initial state of a job before it is picked up for processing.
2. **Processing**: When a worker is ready to process a job, it atomically moves the job ID from the initial queue (`redis_queue_name`) 
    to a processing list (`{redis_queue_name}:processing`) using the `brpoplpush` command. This marks the job as being processed and 
    ensures that no other worker picks up the same job.
3. **Script Execution**: During the `process_job` function execution, the worker attempts to run a specified script with the provided arguments. 
    At this stage, the job is actively being processed, and its outcome (success or failure) has not yet been determined.
4. **Completed or Failed**:
   - If the script executes successfully (i.e., returns a `0` exit code), the job is marked as **"completed"**.
   - If the script execution fails (i.e., returns a non-zero exit code), encounters an error (such as an invalid script path), or if the script 
    path is missing or not executable, the job is marked as **"failed"**.
5. **Notification Sent**: Regardless of the outcome (completed or failed), a message is published to a Redis channel (`redis_completion_channel`) 
    with the job ID, status, output, and error information. This step is crucial for notifying other parts of the application or other applications about the job's completion and its result.
6. **Removal from Processing List**: Finally, the job ID is removed from the processing list (`{redis_queue_name}:processing`) to indicate that 
processing is complete. This is done using the `lrem` command.
