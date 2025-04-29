# KinOS API Reference v2

This document provides a comprehensive reference for version 2 of the KinOS API available at `https://api.kinos-engine.ai/v2`.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [Blueprint Management](#blueprint-management)
    - [Get Blueprints](#get-blueprints)
    - [Get Blueprint Details](#get-blueprint-details)
    - [Initialize Blueprint](#initialize-blueprint)
    - [Reset Blueprint](#reset-blueprint)
  - [Kin Management](#kin-management)
    - [Get Blueprint Kins](#get-blueprint-kins)
    - [Create Kin](#create-kin)
    - [Get Kin Details](#get-kin-details)
    - [Rename Kin](#rename-kin)
    - [Copy Kin](#copy-kin)
    - [Reset Kin](#reset-kin)
  - [Channel Management](#channel-management)
    - [Get Channels](#get-channels)
    - [Create Channel](#create-channel)
    - [Get Channel Details](#get-channel-details)
    - [Update Channel](#update-channel)
    - [Delete Channel](#delete-channel)
  - [Message Interaction](#message-interaction)
    - [Get Kin Messages](#get-kin-messages)
    - [Send Message](#send-message)
    - [Get Channel Messages](#get-channel-messages)
    - [Send Channel Message](#send-channel-message)
    - [Analyze Message](#analyze-message)
  - [File Operations](#file-operations)
    - [Get Kin Files](#get-kin-files)
    - [Get File Content](#get-file-content)
    - [Get Kin Content](#get-kin-content)
    - [Get Aider Logs](#get-aider-logs)
    - [Get Commit History](#get-commit-history)
  - [Kin Building](#kin-building)
    - [Build Kin](#build-kin)
    - [Listen](#listen)
  - [Modes and Configuration](#modes-and-configuration)
    - [Get Kin Modes](#get-kin-modes)
  - [Special Features](#special-features)
    - [Generate Image](#generate-image)
    - [Trigger Autonomous Thinking](#trigger-autonomous-thinking)
  - [Media Processing](#media-processing)
    - [Text-to-Speech](#text-to-speech)
    - [Speech-to-Text](#speech-to-text)
  - [System Information](#system-information)
    - [Health Check](#health-check)
    - [API Information](#api-information)
- [Error Handling](#error-handling)
- [Working with Images](#working-with-images)
- [Pagination](#pagination)
- [Versioning](#versioning)
- [Rate Limiting](#rate-limiting)
- [Glossary](#glossary)

## Base URL

All API v2 endpoints are relative to the base URL:

```
https://api.kinos-engine.ai/v2
```

## Authentication

The API requires authentication using an API key. You can provide the API key in one of two ways:

1. As a header: `X-API-Key: your_api_key_here`
2. As a query parameter: `?api_key=your_api_key_here`

All requests without a valid API key will receive a 401 Unauthorized response.

Example with header authentication:
```bash
curl -H "X-API-Key: your_api_key_here" https://api.kinos-engine.ai/v2/blueprints
```

Example with query parameter authentication:
```bash
curl https://api.kinos-engine.ai/v2/blueprints?api_key=your_api_key_here
```

## API Endpoints

### Blueprint Management

These endpoints allow you to manage blueprints, which are the templates that define the behavior and capabilities of kins.

#### Get Blueprints

Get a list of all blueprints.

**Endpoint:** `GET /v2/blueprints`

**Response:**
```json
{
  "blueprints": [
    {
      "id": "kinos",
      "name": "KinOS",
      "description": "The core KinOS blueprint"
    },
    {
      "id": "deskmate",
      "name": "Deskmate",
      "description": "A helpful desktop assistant"
    },
    {
      "id": "stride",
      "name": "Stride",
      "description": "A productivity-focused blueprint"
    }
  ]
}
```

**Example Usage:**
```javascript
fetch('/v2/blueprints')
  .then(response => response.json())
  .then(data => {
    console.log('blueprints:', data.blueprints);
  });
```

#### Get Blueprint Details

Get detailed information about a specific blueprint.

**Endpoint:** `GET /v2/blueprints/{blueprint}`

**Response:**
```json
{
  "id": "kinos",
  "name": "KinOS",
  "description": "The core KinOS blueprint",
  "version": "1.0.0",
  "created_at": "2023-09-15T14:30:45.123456",
  "updated_at": "2023-09-15T14:30:45.123456"
}
```

#### Initialize Blueprint

Initialize or reinitialize a blueprint's template.

**Endpoint:** `POST /v2/blueprints/{blueprint}/initialize`

**Response:**
```json
{
  "status": "success",
  "message": "Blueprint 'kinos' initialized"
}
```

#### Reset Blueprint

Reset a blueprint and all its kins to initial template state.

**Endpoint:** `POST /v2/blueprints/{blueprint}/reset`

**Response:**
```json
{
  "status": "success",
  "message": "Blueprint 'kinos' has been reset",
  "kins_reset": 3,
  "results": [
    {
      "kin_id": "my-kin-1",
      "status": "success",
      "message": "Kin reset to template state"
    },
    {
      "kin_id": "my-kin-2",
      "status": "success",
      "message": "Kin reset to template state"
    },
    {
      "kin_id": "my-kin-3",
      "status": "success",
      "message": "Kin reset to template state"
    }
  ]
}
```

### Kin Management

These endpoints allow you to create, manage, and manipulate kins, which are instances of blueprints with their own state and memory.

#### Get Blueprint Kins

Get a list of kins for a specific blueprint.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins`

**Response:**
```json
{
  "kins": [
    {
      "id": "template",
      "name": "Template",
      "created_at": "2023-09-15T14:30:45.123456"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Custom Kin",
      "created_at": "2023-09-15T14:30:45.123456"
    }
  ]
}
```

#### Create Kin

Create a new kin for a blueprint.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins`

**Request Body:**
```json
{
  "name": "my-new-kin",
  "template_override": "deskmate"  // Optional
}
```

**Response (Success):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-new-kin",
  "blueprint_id": "kinos",
  "created_at": "2023-09-15T14:30:45.123456",
  "status": "created"
}
```

**Response (Already Exists):**
```json
{
  "error": "Kin already exists",
  "status": 409,
  "existing_kin": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "my-new-kin",
    "blueprint_id": "kinos"
  }
}
```

When attempting to create a kin with a name that already exists, the API returns a 409 Conflict status code with details about the existing kin. This allows clients to handle duplicate kin creation appropriately.

#### Get Kin Details

Get detailed information about a specific kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}`

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-custom-kin",
  "blueprint_id": "kinos",
  "created_at": "2023-09-15T14:30:45.123456",
  "updated_at": "2023-09-15T14:30:45.123456"
}
```

#### Rename Kin

Rename a kin without changing its ID.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/rename`

**Request Body:**
```json
{
  "new_name": "updated-kin-name"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "kin 'my-kin-id' renamed to 'updated-kin-name'",
  "kin_id": "my-kin-id",
  "name": "updated-kin-name"
}
```

**Example Usage:**
```javascript
fetch('/v2/blueprints/kinos/kins/my-kin-id/rename', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    new_name: 'updated-kin-name'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Kin renamed:', data);
});
```

This endpoint updates the display name of a kin while preserving its ID and all associated files and data. The new name is stored in the kin's metadata file.

#### Copy Kin

Copy a kin to create a new kin with the same content within the same blueprint.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/copy`

**Request Body:**
```json
{
  "new_name": "copy-of-my-kin"
}
```

**Response:**
```json
{
  "status": "success", 
  "message": "Kin 'source-kin-id' copied to 'copy-of-my-kin'",
  "source_kin_id": "source-kin-id",
  "new_kin_id": "new-kin-id",
  "new_kin_name": "copy-of-my-kin"
}
```

This endpoint:
1. Creates a new kin with the provided name
2. Copies all files from the source kin to the new kin
3. Updates the new kin's metadata to reflect it was copied from the source kin

This endpoint is particularly useful for creating personalized templates:
1. Start with a base kin that has your desired configuration and files
2. Copy it to create new instances while preserving all customizations
3. Each copy maintains its own independent state and files

Common use cases:
- Create pre-configured kins with specific modes, knowledge, or settings
- Save a well-tuned kin as a starting point for similar projects
- Share standardized configurations across multiple instances
- Test different variations of a kin while keeping the original intact

The copied kin inherits all files and configurations from the source kin, making it an efficient way to replicate successful setups without starting from scratch.

#### Reset Kin

Reset a kin to its initial template state.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/reset`

**Response:**
```json
{
  "status": "success",
  "message": "Kin 'my-kin-id' has been reset to template state"
}
```

#### Link Repository

Link a kin to a GitHub repository.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/link-repo`

**Request Body:**
```json
{
  "github_url": "https://github.com/username/repo",
  "token": "optional_github_token",  // Optional
  "username": "optional_github_username"  // Optional
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Kin 'my-kin-id' linked to GitHub repository: https://github.com/username/repo",
  "blueprint": "kinos",
  "kin_id": "my-kin-id",
  "github_url": "https://github.com/username/repo"
}
```

This endpoint:
1. Removes any existing .git directory in the kin
2. Clones the GitHub repository
3. Moves all repository files to the kin root (overwriting conflicts)
4. Initializes git, commits all files, and pushes to the repository

The optional `token` parameter allows authentication for private repositories. If not provided, the endpoint will attempt to use the `GIT_TOKEN` environment variable.

#### Synchronize Repository

Synchronize a kin's repository with GitHub by performing git pull, merge, and push operations.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/sync-repo`

**Response:**
```json
{
  "status": "success",
  "message": "Repository synchronized successfully",
  "blueprint": "kinos",
  "kin_id": "my-kin-id",
  "operations": [
    {
      "operation": "fetch",
      "status": "success"
    },
    {
      "operation": "pull",
      "status": "success",
      "files_changed": 3,
      "message": "Changes pulled successfully"
    },
    {
      "operation": "commit",
      "status": "success",
      "files_changed": 2,
      "message": "Local changes committed"
    },
    {
      "operation": "push",
      "status": "success",
      "message": "Changes pushed to remote"
    }
  ],
  "repository_url": "https://github.com/username/repo",
  "branch": "main"
}
```

This endpoint:
1. Fetches the latest changes from the remote repository
2. Pulls any remote changes into the local repository
3. Commits any local changes with an automatic commit message
4. Pushes all changes back to the remote repository

The response includes details about each operation performed and whether it was successful.

#### Link Repository

Link a kin to a GitHub repository.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/link-repo`

**Request Body:**
```json
{
  "github_url": "https://github.com/username/repo",
  "token": "optional_github_token",  // Optional
  "username": "optional_github_username"  // Optional
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Kin 'my-kin-id' linked to GitHub repository: https://github.com/username/repo",
  "blueprint": "kinos",
  "kin_id": "my-kin-id",
  "github_url": "https://github.com/username/repo"
}
```

This endpoint:
1. Removes any existing .git directory in the kin
2. Clones the GitHub repository
3. Moves all repository files to the kin root (overwriting conflicts)
4. Initializes git, commits all files, and pushes to the repository

The optional `token` parameter allows authentication for private repositories. If not provided, the endpoint will attempt to use the `GIT_TOKEN` environment variable.

#### Synchronize Repository

Synchronize a kin's repository with GitHub by performing git pull, merge, and push operations.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/sync-repo`

**Response:**
```json
{
  "status": "success",
  "message": "Repository synchronized successfully",
  "blueprint": "kinos",
  "kin_id": "my-kin-id",
  "operations": [
    {
      "operation": "fetch",
      "status": "success"
    },
    {
      "operation": "pull",
      "status": "success",
      "files_changed": 3,
      "message": "Changes pulled successfully"
    },
    {
      "operation": "commit",
      "status": "success",
      "files_changed": 2,
      "message": "Local changes committed"
    },
    {
      "operation": "push",
      "status": "success",
      "message": "Changes pushed to remote"
    }
  ],
  "repository_url": "https://github.com/username/repo",
  "branch": "main"
}
```

This endpoint:
1. Fetches the latest changes from the remote repository
2. Pulls any remote changes into the local repository
3. Commits any local changes with an automatic commit message
4. Pushes all changes back to the remote repository

The response includes details about each operation performed and whether it was successful.

### Message Interaction

These endpoints allow you to interact with kins through messages, analyze content, and receive responses.

#### Get Kin Messages

Get messages for a specific kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/messages`

**Query Parameters:**
- `since` (optional): ISO timestamp to get only messages after this time
- `limit` (optional): Maximum number of messages to return (default: 50)
- `offset` (optional): Number of messages to skip (for pagination)
- `channel_id` (optional): Channel ID to get messages from (if not provided, uses main channel)

**Response:**
```json
{
  "messages": [
    {
      "id": "msg_123456",
      "role": "user",
      "content": "Hello, can you help me with this kin?",
      "timestamp": "2023-09-15T14:30:45.123456"
    },
    {
      "id": "msg_123457",
      "role": "assistant",
      "content": "Of course! I'd be happy to help with your kin. What would you like to know?",
      "timestamp": "2023-09-15T14:30:50.654321"
    }
  ],
  "pagination": {
    "total": 24,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Get Channel Messages

Get messages for a specific channel within a kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}/messages`

**Query Parameters:**
- `since` (optional): ISO timestamp to get only messages after this time
- `limit` (optional): Maximum number of messages to return (default: 50)
- `offset` (optional): Number of messages to skip (for pagination)

**Response:**
```json
{
  "messages": [
    {
      "id": "msg_123456",
      "role": "user",
      "content": "Hello, can you help me with this issue?",
      "timestamp": "2023-09-15T14:30:45.123456",
      "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"
    },
    {
      "id": "msg_123457",
      "role": "assistant",
      "content": "Of course! I'd be happy to help with your issue. What's happening?",
      "timestamp": "2023-09-15T14:30:50.654321",
      "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000",
  "pagination": {
    "total": 24,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Send Message

Send a message to a kin.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/messages`

**Request Body:**
```json
{
  "content": "Hello, can you help me with this?",
  "images": ["data:image/jpeg;base64,..."],
  "attachments": ["file1.txt", "file2.md"],
  "model": "claude-3-7-sonnet-latest",
  "history_length": 25,
  "mode": "creative",
  "addSystem": "Additional system instructions to guide the response",
  "addContext": ["memories/conversation_123.txt", "knowledge/topic.md", "sources/"],
  "min_files": 5,  // Optional, minimum number of context files (default: 5)
  "max_files": 10,  // Optional, maximum number of context files (default: 10)
  "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"  // Optional, channel to send message to
}
```

The `addContext` parameter allows you to specify additional files or directories that should always be included in the context for this message. This is useful for:

- Including specific memory files relevant to the current conversation
- Adding knowledge files that contain information needed for the response
- Ensuring entire directories of related content are available to the AI

When specifying a directory (e.g., "sources/"), all files within that directory will be included in the context. This parameter works alongside the automatic context building system but ensures these specific files are always included.

The `addSystem` parameter allows you to append custom instructions to the system prompt that's sent to Claude. These instructions are added at the end of the system prompt after all the context files, giving you a way to provide additional guidance or constraints for this specific interaction without modifying any files. This is particularly useful for:

- Temporarily changing the AI's behavior for a single message
- Adding specific instructions for handling the current query
- Providing additional context that shouldn't be permanently stored
- Overriding or enhancing the selected mode's behavior

Unlike mode selection which uses predefined behavior sets, `addSystem` allows for ad-hoc customization of the AI's behavior for a single interaction.

**Response:**
```json
{
  "id": "msg_123458",
  "status": "completed",
  "role": "assistant",
  "content": "The code works by...",
  "timestamp": "2023-09-15T14:31:00.123456",
  "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"  // Included if a channel was specified
}
```

The `min_files` and `max_files` parameters allow you to control how many files are included in the context when processing the message. This helps balance between having enough context for accurate responses while avoiding context overload.

#### Send Channel Message

Send a message to a specific channel within a kin.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}/messages`

**Request Body:**
```json
{
  "content": "Hello, can you help me with this issue?",
  "images": ["data:image/jpeg;base64,..."],
  "attachments": ["file1.txt", "file2.md"],
  "model": "claude-3-7-sonnet-latest",
  "history_length": 25,
  "mode": "creative",
  "addSystem": "Additional system instructions to guide the response",
  "addContext": ["memories/conversation_123.txt", "knowledge/topic.md", "sources/"],
  "min_files": 5,  // Optional, minimum number of context files (default: 5)
  "max_files": 10  // Optional, maximum number of context files (default: 10)
}
```

**Response:**
```json
{
  "id": "msg_123458",
  "status": "completed",
  "role": "assistant",
  "content": "I'll help you with your issue...",
  "timestamp": "2023-09-15T14:31:00.123456",
  "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"
}
```

#### Add Message

Add a message to messages.json without any processing or triggering a response.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/add-message`

**Request Body:**
```json
{
  "message": "This is a message to be recorded without processing",
  "role": "user",  // Optional, default: "user"
  "metadata": {    // Optional
    "source": "external_system",
    "tags": ["historical", "imported"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Message successfully added",
  "message_id": 42,
  "timestamp": "2023-09-15T14:30:45.123456"
}
```

This endpoint is useful for:
- Recording system messages without triggering AI processing
- Importing historical conversations
- Adding metadata-only entries
- Synchronizing messages between different interfaces

The message is simply appended to the messages.json file without any AI processing, context building, or file modifications.

#### Add Channel Message

Add a message to a specific channel's messages.json file without any processing.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}/add-message`

**Request Body:**
```json
{
  "message": "This is a channel message to be recorded without processing",
  "role": "user",  // Optional, default: "user"
  "metadata": {    // Optional
    "source": "external_system",
    "tags": ["historical", "imported"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Message successfully added",
  "message_id": 42,
  "timestamp": "2023-09-15T14:30:45.123456",
  "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"
}
```

This endpoint works the same way as the regular add-message endpoint but for channel-specific messages. It's particularly useful for:
- Recording system messages in specific channels
- Importing channel-specific historical conversations
- Adding metadata-only entries to channels
- Synchronizing channel messages between different interfaces

#### Analyze Message

Analyze a message with Claude without saving it or triggering context updates.

**Endpoints:** 
- `POST /v2/blueprints/{blueprint}/kins/{kin_id}/analysis`
- `GET /v2/blueprints/{blueprint}/kins/{kin_id}/analysis?message=your+message`

**POST Request Body:**
```json
{
  "message": "What is the purpose of this code?",
  "images": ["data:image/jpeg;base64,..."],
  "model": "claude-3-7-sonnet-latest",
  "addSystem": "Focus on explaining the architecture",
  "min_files": 5,  // Optional, minimum number of context files (default: 5)
  "max_files": 15,  // Optional, maximum number of context files (default: 15)
  "stream": true  // Optional, enable streaming response (default: false)
}
```

**GET Query Parameters:**
- `message`: The message to analyze (required)
- `model`: Model to use (optional, default: claude-3-7-sonnet-latest)
- `addSystem`: Additional system instructions (optional)
- `min_files`: Minimum number of context files (optional, default: 5)
- `max_files`: Maximum number of context files (optional, default: 15)
- `stream`: Enable streaming response (optional, default: false)

**Response (non-streaming):**
```json
{
  "status": "completed",
  "response": "This code implements a context builder that..."
}
```

**Streaming Response:**
When `stream: true` is specified, the response is sent as a series of Server-Sent Events (SSE) following the same format as the message streaming endpoint.

The `min_files` and `max_files` parameters allow you to control how many files are included in the context when processing the message. This helps balance between having enough context for accurate responses while avoiding context overload.

### File Operations

These endpoints allow you to access, view, and manage files within a kin.

#### Get Kin Files

Get a list of files in a kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/files`

**Query Parameters:**
- `path` (optional): Filter by specific directory within the kin

**Response:**
```json
{
  "files": [
    {
      "path": "system.txt",
      "type": "file",
      "size": 1024,
      "last_modified": "2023-09-15T14:30:45.123456"
    },
    {
      "path": "persona.txt",
      "type": "file",
      "size": 2048,
      "last_modified": "2023-09-15T14:30:45.123456"
    },
    {
      "path": "examples",
      "type": "directory",
      "last_modified": "2023-09-15T14:30:45.123456"
    }
  ]
}
```

#### Get File Content

Get the content of a specific file.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/files/{file_path}`

Where `file_path` is the path to the file within the kin.

**Response:**
For text files, returns the raw content with Content-Type: text/plain.
For images, returns the image with appropriate Content-Type.

For JSON response format, add query parameter `?format=json`:
```json
{
  "path": "system.txt",
  "content": "File contents here...",
  "type": "text/plain",
  "size": 1024,
  "last_modified": "2023-09-15T14:30:45.123456"
}
```

#### Get Kin Content

Get the content of all files in a kin folder as JSON.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/content`

**Query Parameters:**
- `path` (optional): Filter by specific file or directory within the kin

**Response for a file:**
```json
{
  "path": "file.txt",
  "content": "File contents here...",
  "is_directory": false,
  "size": 1024,
  "last_modified": "2023-09-15T14:30:45.123456"
}
```

**Response for a directory:**
```json
{
  "path": "directory",
  "is_directory": true,
  "last_modified": "2023-09-15T14:30:45.123456",
  "files": [
    {
      "path": "directory/file1.txt",
      "content": "File 1 contents...",
      "is_binary": false,
      "size": 1024,
      "last_modified": "2023-09-15T14:30:45.123456"
    },
    {
      "path": "directory/file2.txt",
      "content": "File 2 contents...",
      "is_binary": false,
      "size": 2048,
      "last_modified": "2023-09-15T14:30:45.123456"
    }
  ]
}
```

#### Get Aider Logs

Get the Aider logs for a kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/aider_logs`

**Query Parameters:**
- `limit` (optional): Maximum number of log entries to return (default: 50)
- `offset` (optional): Number of log entries to skip (for pagination)

**Response:**
```json
{
  "logs": [
    {
      "id": "log_123456",
      "timestamp": "2023-09-15T14:30:45.123456",
      "command": "aider --sonnet --yes-always",
      "input": "Can you help me with this code?",
      "output": "I'll help you with this code...",
      "duration_ms": 1500
    }
  ],
  "pagination": {
    "total": 5,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Get Commit History

Get the Git commit history for a kin, ordered by date (latest first).

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/commit-history`

**Response:**
```json
{
  "commits": [
    {
      "message": "Added source content from URL",
      "hash": "a1b2c3d",
      "date": "2024-04-06 12:34:56 +0000",
      "changes": {
        "files_changed": 3,
        "insertions": 150,
        "deletions": 20,
        "files": [
          {
            "path": "sources/example.txt",
            "added": 100,
            "deleted": 10
          },
          {
            "path": "knowledge/concepts.txt",
            "added": 50,
            "deleted": 10
          }
        ]
      }
    },
    {
      "message": "Initial commit",
      "hash": "e5f6g7h",
      "date": "2024-04-06 12:30:00 +0000",
      "changes": {
        "files_changed": 1,
        "insertions": 100,
        "deletions": 0,
        "files": [
          {
            "path": "system.txt",
            "added": 100,
            "deleted": 0
          }
        ]
      }
    }
  ],
  "total": 2
}
```

This endpoint:
1. Checks if the kin has a Git repository (.git directory)
2. Uses `git log` to retrieve the commit history with statistics
3. Returns up to 50 most recent commits, ordered by date (latest first)
4. Each commit includes:
   - The commit message
   - Short hash for reference
   - Date of the commit
   - Change statistics:
     - Number of files changed
     - Number of lines added (insertions)
     - Number of lines deleted (deletions)
     - List of changed files with per-file statistics

### Channel Management

These endpoints allow you to create and manage channels within a kin, enabling multiple conversation threads.

#### Get Channels

Get a list of all channels for a kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/channels`

**Response:**
```json
{
  "channels": [
    {
      "id": "main",
      "name": "Main Channel",
      "created_at": "2023-09-15T14:30:45.123456",
      "updated_at": "2023-09-15T14:30:45.123456",
      "type": "main",
      "is_main": true
    },
    {
      "id": "channel_550e8400-e29b-41d4-a716-446655440000",
      "name": "Support Chat",
      "created_at": "2023-09-15T14:30:45.123456",
      "updated_at": "2023-09-15T14:30:45.123456",
      "type": "direct",
      "user_id": "user_123",
      "metadata": {
        "description": "Support conversation about API integration",
        "tags": ["support", "api"]
      }
    }
  ]
}
```

#### Create Channel

Create a new channel for a kin.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/channels`

**Request Body:**
```json
{
  "name": "Support Chat",
  "type": "direct",
  "user_id": "user_123",
  "metadata": {
    "description": "Support conversation about API integration",
    "tags": ["support", "api"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Channel 'Support Chat' created",
  "channel_id": "channel_550e8400-e29b-41d4-a716-446655440000"
}
```

#### Get Channel Details

Get detailed information about a specific channel.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}`

**Response:**
```json
{
  "id": "channel_550e8400-e29b-41d4-a716-446655440000",
  "name": "Support Chat",
  "created_at": "2023-09-15T14:30:45.123456",
  "updated_at": "2023-09-15T14:30:45.123456",
  "type": "direct",
  "user_id": "user_123",
  "metadata": {
    "description": "Support conversation about API integration",
    "tags": ["support", "api"]
  }
}
```

#### Update Channel

Update a channel's information.

**Endpoint:** `PUT /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}`

**Request Body:**
```json
{
  "name": "Updated Channel Name",
  "metadata": {
    "description": "Updated description",
    "tags": ["updated", "tags"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Channel 'channel_550e8400-e29b-41d4-a716-446655440000' updated",
  "channel": {
    "id": "channel_550e8400-e29b-41d4-a716-446655440000",
    "name": "Updated Channel Name",
    "created_at": "2023-09-15T14:30:45.123456",
    "updated_at": "2023-09-15T14:31:00.123456",
    "type": "direct",
    "user_id": "user_123",
    "metadata": {
      "description": "Updated description",
      "tags": ["updated", "tags"]
    }
  }
}
```

#### Delete Channel

Delete a channel.

**Endpoint:** `DELETE /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}`

**Response:**
```json
{
  "status": "success",
  "message": "Channel 'channel_550e8400-e29b-41d4-a716-446655440000' deleted"
}
```

### Kin Building

These endpoints allow you to modify and update a kin's files and structure.

#### Build Kin

Send a message to Aider for file creation/modification without Claude response.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/build`

**Request Body:**
```json
{
  "message": "Create a new file called example.txt with some sample content",
  "addSystem": "Focus on creating well-structured files",  // Optional
  "min_files": 5,  // Optional, minimum number of context files (default: 5)
  "max_files": 15  // Optional, maximum number of context files (default: 15)
}
```

The `addSystem` parameter allows you to append custom instructions to the system prompt that's sent to Aider. These instructions are added at the end of the system prompt after all the context files, providing additional guidance for how the files should be created or modified.

**Response:**
```json
{
  "status": "completed",
  "response": "I've created the example.txt file with sample content..."
}
```

The `min_files` and `max_files` parameters allow you to control how many files are included in the context when processing the message. This helps balance between having enough context for accurate responses while avoiding context overload.

#### Listen

Have the kin listen to a message for file creation/modification (alias for /build endpoint).

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/listen`

**Request Body:**
```json
{
  "message": "Create a new file called example.txt with some sample content",
  "addSystem": "Focus on creating well-structured files"  // Optional
}
```

**Response:**
```json
{
  "status": "completed",
  "response": "I've created the example.txt file with sample content..."
}
```

This endpoint is an alias for the `/build` endpoint and behaves exactly the same way. It's provided for semantic clarity when having the kin listen to user messages for file operations.

### Modes and Configuration

These endpoints allow you to manage and interact with different operational modes of a kin.

#### Get Kin Modes

Get available modes for a kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/modes`

**Response:**
```json
{
  "modes": [
    {
      "id": "analysis",
      "title": "Analysis Mode: Informative Responses Without Memorization"
    },
    {
      "id": "code_review",
      "title": "Code Review Mode"
    },
    {
      "id": "creative",
      "title": "Creative Writing Mode"
    }
  ]
}
```

### Special Features

These endpoints provide specialized functionality for specific use cases.

#### Generate Image

Generate an image based on a message using Ideogram API.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/images`

**Request Body:**
```json
{
  "prompt": "Create an image of a futuristic city with flying cars",
  "aspect_ratio": "ASPECT_1_1",  // Optional, default: ASPECT_1_1
  "model": "V_2A",  // Optional, default: V_2A
  "magic_prompt_option": "AUTO"  // Optional, default: AUTO
}
```

**Response:**
```json
{
  "id": "img_123456",
  "status": "success",
  "prompt": "A detailed, expansive view of a futuristic metropolis with sleek skyscrapers...",
  "created_at": "2023-09-15T14:30:45.123456",
  "data": {
    "resolution": "1024x1024",
    "is_safe": true,
    "seed": 12345,
    "url": "https://ideogram.ai/api/images/direct/8YEpFzHuS-S6xXEGmCsf7g",
    "style": "REALISTIC"
  },
  "local_path": "images/ideogram_20230915_143045.jpg"
}
```


#### Trigger Autonomous Thinking

Trigger autonomous thinking for a kin, which generates random thoughts and self-reflections.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/autonomous_thinking`

**Request Body:**
```json
{
  "iterations": 3,  // Optional, default: 3
  "wait_time": 600,  // Optional, default: 600 seconds (10 minutes)
  "sync": false,  // Optional, default: false
  "webhook_url": "https://your-webhook-endpoint.com/hook"  // Optional, URL to receive real-time updates
}
```

**Response (Asynchronous Mode, sync=false):**
```json
{
  "status": "started",
  "message": "Autonomous thinking started for kinos/my-kin-id",
  "blueprint": "kinos",
  "kin_id": "my-kin-id",
  "iterations": 3,
  "wait_time": 600
}
```

**Response (Synchronous Mode, sync=true):**
```json
{
  "status": "completed",
  "blueprint": "kinos",
  "kin_id": "my-kin-id",
  "steps": [
    {
      "step": "keywords",
      "content": {
        "relevant_keywords": ["technology", "innovation", "future"],
        "emotions": ["excitement", "curiosity"],
        "problems": ["complexity", "adoption"],
        "surprising_words": ["quantum", "symbiotic", "emergent"],
        "adjacent_keywords": ["sustainability", "ethics"],
        "surprising_keywords": ["biomimicry", "transcendence"]
      }
    },
    {
      "step": "dream",
      "content": "In my dream, I found myself navigating a quantum network where ideas took physical form, connecting innovation to human experience in unexpected ways. The symbiotic relationship between technology and nature revealed itself as both beautiful and challenging."
    },
    {
      "step": "daydreaming",
      "content": "I wonder if the future of technology lies not in domination but in partnership with natural systems. What if our innovations could mirror the elegant solutions that nature has refined over billions of years? Perhaps the complexity we face isn't a problem to solve but a reality to embrace, finding ways to make emergent properties work for human flourishing rather than against it."
    },
    {
      "step": "initiative",
      "content": "Goal: Explore biomimicry in technological design\n\nSteps:\n1. Research examples of successful biomimetic technologies\n2. Identify three natural processes that could inspire new computing paradigms\n3. Draft a proposal for an ethical framework that balances innovation with sustainability\n4. Create a visualization of how these principles might reshape our digital infrastructure"
    },
    {
      "step": "kin_response",
      "content": "Your thoughts have sparked some fascinating connections in my mind. The concept of biomimicry as a bridge between technology and nature is particularly compelling..."
    }
  ]
}
```

This endpoint has two modes of operation:

1. **Asynchronous Mode (default, sync=false):**
   - Starts a background process that:
     - Selects random files from the kin
     - Generates thoughts based on these files
     - Sends the thoughts to the kin for self-reflection
     - Repeats this process for the specified number of iterations
   - The process runs asynchronously, so the endpoint returns immediately while the thinking continues in the background
   - If a webhook URL is provided, each step of the thinking process will send data to this URL in real-time

2. **Synchronous Mode (sync=true):**
   - Executes a single iteration of the autonomous thinking process immediately
   - Returns the complete results of each step in the process:
     - Keywords extracted from the kin's files
     - Dream narrative generated from the keywords
     - Daydreaming paragraph developed from the dream
     - Initiative created based on the daydreaming
     - The kin's response to these thoughts
   - This mode is useful for applications that need to display the thinking process or capture the results for immediate use
   - If a webhook URL is provided, each step will also send data to this URL as it completes

The webhook receives JSON data for each step with this structure:
```json
{
  "type": "keywords|dream|daydreaming|initiative|kin_response|error",
  "blueprint": "blueprint_name",
  "kin_id": "kin_id",
  "iteration": 1,  // Only in asynchronous mode
  "content": { ... },  // The content generated in this step
  "timestamp": "2023-09-15T14:30:45.123456"
}
```

**Webhook Details:**

The webhook functionality provides real-time updates about the autonomous thinking process:

- **Reliability**: The system implements retry logic with exponential backoff for failed webhook calls
- **Timeout Protection**: Webhook requests have a configurable timeout to prevent hanging
- **Error Handling**: Different types of errors (connection, timeout, server errors) are handled appropriately
- **Event Types**:
  - `keywords`: Initial keywords extracted from the kin's files
  - `dream`: Dream narrative generated from the keywords
  - `daydreaming`: Free-flowing thoughts developed from the dream
  - `initiative`: Practical action plan created from the daydreaming
  - `kin_response`: The kin's response to the thoughts
  - `error`: Any errors that occur during the process

For production systems, it's recommended to implement idempotent webhook handlers that can handle potential duplicate events in case of retries.

### Media Processing

These endpoints allow you to convert between text and audio formats.

#### Text-to-Speech

Convert text to speech using ElevenLabs API.

**Endpoint:** `POST /v2/tts`

**Request Body:**
```json
{
  "text": "Text to convert to speech",
  "voice_id": "IKne3meq5aSn9XLyUdCD",  // Optional, default ElevenLabs voice ID
  "model": "eleven_flash_v2_5"  // Optional, default model
}
```

**Response:**
Returns an audio stream with Content-Type: audio/mpeg.

For JSON response (add query parameter `?format=json`):
```json
{
  "id": "tts_123456",
  "status": "success",
  "text": "Text to convert to speech",
  "audio_url": "/v2/tts/tts_123456/audio",
  "created_at": "2023-09-15T14:30:45.123456",
  "voice_id": "IKne3meq5aSn9XLyUdCD",
  "model": "eleven_flash_v2_5"
}
```

#### Speech-to-Text

Convert audio to text using OpenAI's Whisper API.

**Endpoint:** `POST /v2/stt`

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file`: The audio file to transcribe (required)
  - `model`: Model to use (optional, default: "whisper-1")
  - `language`: Language code in ISO-639-1 format (optional)
  - `prompt`: Text to guide the model's style (optional)
  - `response_format`: Format of the output (optional, default: "json")

**Response:**
```json
{
  "id": "stt_123456",
  "status": "success",
  "text": "Transcribed text from the audio file",
  "created_at": "2023-09-15T14:30:45.123456",
  "model": "whisper-1",
  "language": "en",
  "duration_ms": 3500
}
```

### System Information

These endpoints provide information about the API system status and configuration.

#### Health Check

Check if the API is running properly.

**Endpoint:** `GET /v2/health`

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2023-09-15T14:30:45.123456",
  "services": {
    "database": "connected",
    "claude": "available",
    "ideogram": "available",
    "elevenlabs": "available"
  }
}
```

#### API Information

Get general information about the API.

**Endpoint:** `GET /v2`

**Response:**
```json
{
  "status": "running",
  "message": "KinOS API v2 is running",
  "version": "2.0.0",
  "documentation": "/v2/docs",
  "endpoints": {
    "blueprints": "/v2/blueprints",
    "kins": "/v2/blueprints/{blueprint}/kins",
    "messages": "/v2/blueprints/{blueprint}/kins/{kin_id}/messages",
    "files": "/v2/blueprints/{blueprint}/kins/{kin_id}/files",
    "health": "/v2/health",
    "tts": "/v2/tts",
    "stt": "/v2/stt"
  }
}
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object with error details:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "The requested resource was not found",
    "details": "Blueprint 'nonexistent' does not exist"
  },
  "request_id": "req_123456"
}
```

## Streaming Responses

KinOS API supports streaming responses for message endpoints, allowing you to receive Claude's responses incrementally as they're generated. This is particularly useful for long responses or when you want to display content to users as it becomes available.

### How to Enable Streaming

To enable streaming, add the `stream: true` parameter to your message request:

```json
{
  "content": "Tell me about quantum computing",
  "stream": true
}
```

### Streaming Response Format

When streaming is enabled, the response is sent as a series of Server-Sent Events (SSE) following the Anthropic Claude API format. Each event has a type and associated JSON data:

1. `message_start`: Contains a Message object with empty content
2. A series of content blocks, each with:
   - `content_block_start`: Marks the beginning of a content block
   - One or more `content_block_delta` events: Contains incremental text chunks
   - `content_block_stop`: Marks the end of a content block
3. `message_delta`: Indicates top-level changes to the Message object
4. `message_stop`: Marks the end of the response

### Example Streaming Response

```
event: message_start
data: {"type": "message_start", "message": {"role": "assistant", "content": []}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Quantum"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " computing"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " is"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}}

event: message_stop
data: {"type": "message_stop"}
```

### Client Implementation

Here's how to consume streaming responses in JavaScript:

```javascript
async function streamMessage() {
  const response = await fetch('/v2/blueprints/kinos/kins/my-kin/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content: "Tell me about quantum computing",
      stream: true
    })
  });

  // Create a new EventSource from the response
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    // Decode the chunk and add it to our buffer
    buffer += decoder.decode(value, { stream: true });
    
    // Process complete events in the buffer
    let eventEnd = buffer.indexOf("\n\n");
    while (eventEnd > -1) {
      const eventText = buffer.substring(0, eventEnd);
      buffer = buffer.substring(eventEnd + 2);
      
      // Parse the event
      const eventLines = eventText.split('\n');
      const eventType = eventLines[0].substring(7); // Remove "event: "
      const eventData = JSON.parse(eventLines[1].substring(6)); // Remove "data: "
      
      // Handle different event types
      if (eventType === 'content_block_delta' && eventData.delta.type === 'text_delta') {
        // Append the text chunk to your UI
        appendToUI(eventData.delta.text);
      }
      
      eventEnd = buffer.indexOf("\n\n");
    }
  }
}

function appendToUI(text) {
  // Add the text to your UI element
  document.getElementById('response').textContent += text;
}
```

For Python clients, you can use the Anthropic Python SDK which has built-in streaming support:

```python
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    max_tokens=1024,
    messages=[{"role": "user", "content": "Tell me about quantum computing"}],
    model="claude-3-7-sonnet-20250219",
) as stream:
  for text in stream.text_stream:
      print(text, end="", flush=True)
```

### Streaming with the KinOS API

When using streaming with the KinOS API, the message is still saved to the kin's message history once the complete response is received. This means you don't need to handle saving the message yourself - the API takes care of that automatically.

The streaming feature is available on these endpoints:

- `POST /v2/blueprints/{blueprint}/kins/{kin_id}/messages`
- `POST /v2/blueprints/{blueprint}/kins/{kin_id}/channels/{channel_id}/messages`

Note that the `build` and `analysis` endpoints do not currently support streaming.

## Working with Images

When sending messages with images, encode the images as base64 strings and include them in the `images` array of the request body. The API will pass these images to Claude for analysis.

Example request with an image:

```json
{
  "content": "What's in this image?",
  "images": [
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  ]
}
```

## Pagination

Endpoints that return lists of resources support pagination through the following query parameters:

- `limit`: Maximum number of items to return (default varies by endpoint)
- `offset`: Number of items to skip (for offset-based pagination)

Paginated responses include a pagination object:

```json
{
  "items": [...],
  "pagination": {
    "total": 100,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

## Versioning

This API is version 2 (v2) and all endpoints are prefixed with `/v2`. The API follows semantic versioning:

- Minor updates (e.g., 2.1.0) are backward compatible
- Patch updates (e.g., 2.0.1) are for bug fixes only

The legacy API (v1) remains available at the root path for backward compatibility but is deprecated and will be removed in the future.

## Rate Limiting

The API implements rate limiting to ensure fair usage. Rate limit information is included in response headers:

- `X-RateLimit-Limit`: Number of requests allowed in the current time window
- `X-RateLimit-Remaining`: Number of requests remaining in the current time window
- `X-RateLimit-Reset`: Time when the rate limit window resets (Unix timestamp)

When rate limits are exceeded, the API returns a 429 Too Many Requests status code.

## Glossary

- **Blueprint**: A template that defines the behavior, capabilities, and structure of kins. Blueprints contain the core files and configuration that determine how kins function.

- **Kin**: An instance of a blueprint. Each kin has its own state, memory, and files, allowing for personalized interactions while inheriting the core functionality of its blueprint.

- **Channel**: A conversation thread within a kin that maintains its own message history. Channels allow a kin to have multiple separate conversations with different users or for different purposes.

- **Main Channel**: The default channel that exists for every kin, represented by the root messages.json file. This maintains backward compatibility with the original single-conversation model.

- **Mode**: A predefined behavior setting that modifies how a kin responds to messages. Modes can change the tone, style, or purpose of interactions without requiring changes to the kin's files.

- **Context**: The collection of files and information provided to Claude when processing a message. The context determines what knowledge the AI has access to when generating a response.

- **Aider**: A tool that processes messages to create or modify files within a kin. Aider helps kins maintain their memory and knowledge by updating files based on conversations.

- **Template**: The original version of a blueprint that serves as the starting point for all kins created from that blueprint.

- **System Prompt**: Instructions provided to Claude that define how it should behave and respond. The system prompt includes content from core files and selected context files.

- **Core Files**: Essential files like `kinos.txt`, `system.txt`, or `persona.txt` that define a kin's fundamental behavior and are always included in the context.

- **Autonomous Thinking**: A process where a kin generates thoughts and reflections without user input, helping it develop its understanding and personality.


- **Analysis Mode**: A special mode that provides information and explanations without modifying the kin's memory or files.

- **Build/Listen**: Endpoints that allow kins to modify their own files based on user messages, enabling them to learn and adapt over time.
