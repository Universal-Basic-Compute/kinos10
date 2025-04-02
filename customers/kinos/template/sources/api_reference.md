# KinOS API Reference

This document provides a comprehensive reference for the KinOS API available at `http://api.kinos-engine.ai`.

## Base URL

All API endpoints are relative to the base URL:

```
http://api.kinos-engine.ai
```

## Authentication

Currently, the API does not require authentication.

## API Endpoints

### Get Customers

Get a list of all customers.

**Endpoint:** `GET /customers`

**Response:**
```json
{
  "customers": ["kinos", "deskmate", "stride"]
}
```

**Example Usage:**
```javascript
fetch('/customers')
  .then(response => response.json())
  .then(data => {
    console.log('Customers:', data.customers);
  });
```

### Health Check

Check if the API is running properly.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy"
}
```

### API Information

Get general information about the API.

**Endpoint:** `GET /`

**Response:**
```json
{
  "status": "running",
  "message": "KinOS API is running",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "projects": "/projects",
    "messages": "/projects/{customer}/{project_id}/messages",
    "files": "/projects/{customer}/{project_id}/files"
  }
}
```

### Create Project

Create a new project for a customer.

**Endpoint:** `POST /projects`

**Request Body:**
```json
{
  "project_name": "My New Project",
  "customer": "kinos",
  "template_override": "deskmate"  // Optional
}
```

**Response:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer": "kinos",
  "status": "created"
}
```

### Get Customer Projects

Get a list of projects for a specific customer.

**Endpoint:** `GET /projects/{customer}/projects`

**Response:**
```json
{
  "projects": ["template", "550e8400-e29b-41d4-a716-446655440000"]
}
```

### Get Project Messages

Get messages for a specific project.

**Endpoint:** `GET /projects/{customer}/{project_id}/messages`

**Query Parameters:**
- `since` (optional): ISO timestamp to get only messages after this time

**Response:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello, can you help me with this project?",
      "timestamp": "2023-09-15T14:30:45.123456"
    },
    {
      "role": "assistant",
      "content": "Of course! I'd be happy to help with your project. What would you like to know?",
      "timestamp": "2023-09-15T14:30:50.654321"
    }
  ]
}
```

### Send Message

Send a message to a project.

**Endpoint:** `POST /projects/{customer}/{project_id}/messages`

**Request Body:**
```json
{
  "content": "Can you explain how this code works?",
  "attachments": [],  // Optional
  "images": [],  // Optional, base64-encoded images
  "model": "claude-3-5-haiku-latest",  // Optional, defaults to claude-3-5-haiku-latest
  "history_length": 25,  // Optional, number of recent messages to include in context (defaults to 25)
  "mode": "code_review",  // Optional, specifies a mode to help guide context selection
  "addSystem": "Always respond in a concise manner"  // Optional, additional text to append to the system prompt
}
```

**Response:**
```json
{
  "status": "completed",
  "message_id": "12",
  "response": "The code works by..."
}
```

### Get Project Files

Get a list of files in a project.

**Endpoint:** `GET /projects/{path:project_path}/files`

Where `project_path` is in the format `{customer}/{project_id}` or `{customer}/template`.

**Response:**
```json
{
  "files": [
    {
      "path": "system.txt",
      "type": "file",
      "last_modified": "2023-09-15T14:30:45.123456"
    },
    {
      "path": "persona.txt",
      "type": "file",
      "last_modified": "2023-09-15T14:30:45.123456"
    }
  ]
}
```

### Get File Content

Get the content of a specific file.

**Endpoint:** `GET /projects/{path:project_path}/files/{path:file_path}`

Where:
- `project_path` is in the format `{customer}/{project_id}` or `{customer}/template`
- `file_path` is the path to the file within the project

**Response:**
For text files, returns the raw content with Content-Type: text/plain.
For images, returns:
```json
{
  "content": "base64-encoded-content",
  "type": "image"
}
```

### Get Project Content

Get the content of all files in a project folder as JSON.

**Endpoint:** `GET /projects/{path:project_path}/content`

Where `project_path` is in the format `{customer}/{project_id}` or `{customer}/template`.

**Query Parameters:**
- `path` (optional): Filter by specific file or directory within the project

**Response for a file:**
```json
{
  "path": "file.txt",
  "content": "File contents here...",
  "is_directory": false
}
```

**Response for a directory:**
```json
{
  "path": "directory",
  "is_directory": true,
  "files": [
    {
      "path": "directory/file1.txt",
      "content": "File 1 contents...",
      "is_binary": false
    },
    {
      "path": "directory/file2.txt",
      "content": "File 2 contents...",
      "is_binary": false
    }
  ]
}
```

**Example Usage:**
```javascript
// Get all files in a project
fetch('/projects/customer/project_id/content')
  .then(response => response.json())
  .then(data => {
    console.log('Project content:', data);
  });

// Get files in a specific directory
fetch('/projects/customer/project_id/content?path=directory')
  .then(response => response.json())
  .then(data => {
    console.log('Directory content:', data);
  });

// Get a specific file
fetch('/projects/customer/project_id/content?path=file.txt')
  .then(response => response.json())
  .then(data => {
    console.log('File content:', data.content);
  });
```

### Initialize Customer

Initialize or reinitialize a customer's template.

**Endpoint:** `POST /customers/{customer}/initialize`

**Response:**
```json
{
  "status": "success",
  "message": "Customer 'kinos' initialized"
}
```

### Get Aider Logs

Get the Aider logs for a project.

**Endpoint:** `GET /projects/{customer}/{project_id}/aider_logs`

**Response:**
```json
{
  "logs": "--- Aider run at 2023-09-15T14:30:45.123456 ---\nCommand: aider --sonnet --yes-always\nInput: Can you help me with this code?\nOutput: I'll help you with this code...\n--- End of Aider run ---"
}
```

### Analyze Message

Analyze a message with Claude without saving it or triggering context updates.

**Endpoint:** `POST /projects/{customer}/{project_id}/analysis`

**Request Body:**
```json
{
  "message": "What is the purpose of this project?",
  "images": [],  // Optional, base64-encoded images
  "model": "claude-3-5-haiku-latest",  // Optional, defaults to claude-3-5-haiku-latest
  "history_length": 25,  // Optional, number of recent messages to include in context (defaults to 25)
  "addSystem": "Provide a detailed analysis"  // Optional, additional system instructions
}
```

**Response:**
```json
{
  "status": "completed",
  "response": "Based on my analysis of the project files..."
}
```

**Example Usage:**
```javascript
fetch('/projects/kinos/my-project/analysis', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: "What is the purpose of this project?"
  })
})
.then(response => response.json())
.then(data => {
  console.log('Analysis:', data.response);
});
```

**Error Responses:**
- `400 Bad Request`: Missing required message parameter
- `404 Not Found`: Customer or project not found
- `500 Internal Server Error`: Server error

### Analyze Project

Analyze a project with Claude without modifying files.

**Endpoint:** `POST /projects/{customer}/{project_id}/analysis`

**Request Body:**
```json
{
  "message": "Explain the architecture of this project",
  "model": "claude-3-5-haiku-latest"  // Optional, defaults to claude-3-5-haiku-latest
}
```

**Response:**
```json
{
  "status": "success",
  "response": "This project follows a layered architecture with..."
}
```

**Example Usage:**
```javascript
fetch('/projects/kinos/my-project/analysis', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Explain the architecture of this project'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Analysis:', data.response);
});
```

**Error Responses:**
- `400 Bad Request`: Missing required message parameter
- `404 Not Found`: Customer or project not found
- `500 Internal Server Error`: Server error

### Generate Image

Generate an image based on a message using Ideogram API.

**Endpoint:** `POST /projects/{customer}/{project_id}/image`

**Request Body:**
```json
{
  "message": "Create an image of a futuristic city with flying cars",
  "aspect_ratio": "ASPECT_1_1",  // Optional, default: ASPECT_1_1
  "model": "V_2",  // Optional, default: V_2
  "magic_prompt_option": "AUTO"  // Optional, default: AUTO
}
```

**Response:**
```json
{
  "status": "success",
  "prompt": "A detailed, expansive view of a futuristic metropolis with sleek skyscrapers...",
  "result": {
    "created": "2023-09-15T14:30:45.123456",
    "data": [
      {
        "prompt": "A detailed, expansive view of a futuristic metropolis...",
        "resolution": "1024x1024",
        "is_image_safe": true,
        "seed": 12345,
        "url": "https://ideogram.ai/api/images/direct/8YEpFzHuS-S6xXEGmCsf7g",
        "style_type": "REALISTIC"
      }
    ],
    "local_path": "images/ideogram_20230915_143045.jpg"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Missing required message parameter
- `404 Not Found`: Customer or project not found
- `500 Internal Server Error`: Ideogram API key not configured or other server error

### Text-to-Speech

Convert text to speech using ElevenLabs API.

**Endpoint:** `POST /tts`

**Request Body:**
```json
{
  "text": "Text to convert to speech",
  "voiceId": "IKne3meq5aSn9XLyUdCD",  // Optional, default ElevenLabs voice ID
  "model": "eleven_flash_v2_5"  // Optional, default model
}
```

**Response:**
Returns an audio stream with Content-Type: audio/mpeg.

**Example Usage:**
```javascript
fetch('/tts', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: 'Hello, this is a test',
    voiceId: 'IKne3meq5aSn9XLyUdCD'
  })
})
.then(response => response.blob())
.then(blob => {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.play();
});
```

**Error Responses:**
- `400 Bad Request`: Missing required text parameter
- `500 Internal Server Error`: ElevenLabs API key not configured or other server error

### Speech-to-Text

Convert audio to text using OpenAI's Whisper API.

**Endpoint:** `POST /stt`

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
  "text": "Transcribed text from the audio file"
}
```

**Example Usage:**
```javascript
// Create a FormData object
const formData = new FormData();

// Add the audio file
formData.append('file', audioFile);  // audioFile is a File object from input or recording

// Add optional parameters
formData.append('model', 'whisper-1');
formData.append('language', 'en');  // English

// Send the request
fetch('/stt', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('Transcription:', data.text);
});
```

**Error Responses:**
- `400 Bad Request`: No audio file provided or invalid parameters
- `500 Internal Server Error`: OpenAI API key not configured or other server error

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200 OK`: Request succeeded
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object with an error message:

```json
{
  "error": "Error message details"
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

## File Operations

The API provides read-only access to project files. Files are filtered according to common ignore patterns (similar to .gitignore) to exclude temporary files, version control directories, and other non-essential files.
