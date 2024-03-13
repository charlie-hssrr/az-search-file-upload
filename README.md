# Async File Upload Web Service with Quart, Azure, and Redis

This project explores asynchronous web services using Quart, with Azure Blob Storage for file storage and Redis for job queue management and processing. Designed for file uploads, script execution queuing, and real-time WebSocket interactions, it offers a robust framework for asynchronous tasks.

## About This Project

This project builds on the [azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo), extending its core capabilities with features like file uploading, Redis job management, `prepdocs.sh` script execution, and real-time web services for client feedback.

This project excludes a frontend, so I'm using Postman to manage file uploads. The script queue is set up to run `prepdocs.sh` from the original demo, so double-check the job paths when you set it up.

For complete functionality, such as executing `prepdocs.sh` to handle file uploads to Azure Blob Storage, integrating this project with the original demo app is recommended. This ensures all new features seamlessly work within the established framework.

## Features

- **File Upload**: Accepts file uploads and validates them based on allowed file types.
- **Redis Job Queue**: Processes file uploads by queuing jobs in Redis for background processing.
- **Script Execution**: Executes predefined scripts (`prepdocs.sh`) on the server with uploaded files as input.
- **WebSockets**: Uses WebSockets for real-time communication to notify clients about the job completion status.
- **Azure Blob Storage Integration**: Successfully processed (`prepdocs.sh`) file blobs can be fetched from Azure Blob Storage.

### Authentication

```azd auth login```

## Prerequisites

- Python 3.8+
- Redis server
- Azure Blob Storage account
- [azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo) (for integration)

## Setup and Installation

1. **Clone the repository**

    ```bash
    git clone https://github.com/your-repository-url.git
    cd your-repository-name
    ```

2. **Configure environment variables**

    Variables are hardcoded but you can always create a `.env` file in the project root directory and specify the following variables:
    ```
    AZURE_STORAGE_ACCOUNT=your_storage_account_name
    AZURE_STORAGE_CONTAINER=your_container_name
    REDIS_URL=redis://localhost
    REDIS_QUEUE_NAME="script_queue"
    REDIS_COMPLETION_CHANNEL = "script_completion_channel"
    ```

3. **Update `prepdocs.sh` script path**

    This is the path to `prepdocs.sh` in your ```azure-openai-search-demo``` application:

    ```
    script_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', '[path_to_your_demo_app]', 'app', 'backend', 'scripts', 'prepdocs.sh'
        )
    )
    ```

4. **Start the server**

    Use the provided shell script to start the server:

    ```bash
    chmod +x start.sh
    ./start.sh
    ```

    The server will start on `localhost` at port `60666` by default.
 
## Usage

### Endpoints

- **GET /ping**: Test endpoint to check the service status.
- **GET /config**: Returns the current configuration of Azure storage and Redis.
- **POST /upload**: Endpoint to upload files. Files are validated, saved, and a background job is queued for processing.
- **GET /blobs**: Lists all blobs in the configured Azure Blob Storage container.

### WebSocket Endpoint

- **/ws**: WebSocket endpoint for real-time notifications about job completions.

## Development

This project is structured for asynchronous operation and is built on modern Python async/await features. The core functionality is divided among several modules:
- **core**: Contains helper classes for file uploads, script execution, Redis job processing, and WebSocket communication.
- **routes**: Defines Quart blueprint routes for HTTP endpoints.
