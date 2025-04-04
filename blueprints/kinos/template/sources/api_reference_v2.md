# KinOS API Reference v2

This document provides a comprehensive reference for version 2 of the KinOS API available at `https://api.kinos-engine.ai/v2`.

## Base URL

All API v2 endpoints are relative to the base URL:

```
https://api.kinos-engine.ai/v2
```

## Authentication

Currently, the API does not require authentication.

## API Endpoints

### Get Blueprints

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

### Get Blueprint Details

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

### Initialize Blueprint

Initialize or reinitialize a blueprint's template.

**Endpoint:** `POST /v2/blueprints/{blueprint}/initialize`

**Response:**
```json
{
  "status": "success",
  "message": "Blueprint 'kinos' initialized"
}
```

### Get Blueprint Kins

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

### Create Kin

Create a new kin for a blueprint.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins`

**Request Body:**
```json
{
  "name": "My New Kin",
  "template_override": "deskmate"  // Optional
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My New Kin",
  "blueprint_id": "kinos",
  "created_at": "2023-09-15T14:30:45.123456",
  "status": "created"
}
```

### Get Kin Details

Get detailed information about a specific kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}`

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Custom Kin",
  "blueprint_id": "kinos",
  "created_at": "2023-09-15T14:30:45.123456",
  "updated_at": "2023-09-15T14:30:45.123456"
}
```

### Rename Kin

Rename a kin without changing its ID.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/rename`

**Request Body:**
```json
{
  "new_name": "Updated Kin Name"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "kin 'my-kin-id' renamed to 'Updated Kin Name'",
  "kin_id": "my-kin-id",
  "name": "Updated Kin Name"
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
    new_name: 'Updated Kin Name'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Kin renamed:', data);
});
```

This endpoint updates the display name of a kin while preserving its ID and all associated files and data. The new name is stored in the kin's metadata file.

### Get Kin Messages

Get messages for a specific kin.

**Endpoint:** `GET /v2/blueprints/{blueprint}/kins/{kin_id}/messages`

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

### Send Message

Send a message to a kin.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/messages`

**Request Body:**
```json
{
  "content": "Hello, can you help me with this?",
  "images": ["data:image/jpeg;base64,..."],
  "attachments": ["file1.txt", "file2.md"],
  "model": "claude-3-5-haiku-latest",
  "history_length": 25,
  "mode": "creative",
  "addSystem": "Additional system instructions to guide the response"
}
```

**Response:**
```json
{
  "id": "msg_123458",
  "status": "completed",
  "role": "assistant",
  "content": "The code works by...",
  "timestamp": "2023-09-15T14:31:00.123456"
}
```

### Get Kin Files

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

### Get File Content

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

### Get Kin Content

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

### Get Aider Logs

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

### Analyze Message

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/analysis`

Analyze a message with Claude without saving it to the conversation history.

**Request Body:**
```json
{
  "message": "What is the purpose of this code?",
  "images": ["data:image/jpeg;base64,..."],
  "model": "claude-3-5-haiku-latest",
  "addSystem": "Focus on explaining the architecture"
}
```

**Response:**
```json
{
  "status": "success",
  "response": "This code implements a context builder that...",
  "mode": "observation"
}
```

The response includes the mode that was used for the analysis, which may be automatically selected based on the message content.

### Generate Image

Generate an image based on a message using Ideogram API.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/images`

**Request Body:**
```json
{
  "prompt": "Create an image of a futuristic city with flying cars",
  "aspect_ratio": "ASPECT_1_1",  // Optional, default: ASPECT_1_1
  "model": "V_2",  // Optional, default: V_2
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

### Reset Blueprint

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

### Reset Kin

Reset a kin to its initial template state.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/reset`

**Response:**
```json
{
  "status": "success",
  "message": "Kin 'my-kin-id' has been reset to template state"
}
```

### Build Kin

Send a message to Aider for file creation/modification without Claude response.

**Endpoint:** `POST /v2/blueprints/{blueprint}/kins/{kin_id}/build`

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

### Get Kin Modes

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

### Text-to-Speech

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

### Speech-to-Text

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

### Health Check

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

### API Information

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
