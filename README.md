# KinOS API

KinOS API is the backend service for the KinOS Adaptive Context Management System. It provides endpoints for managing kins, messages, files, and text-to-speech functionality.

## Features

- **kin Management**: Create and manage kins for different blueprints
- **Message Handling**: Process user messages with Claude AI and Aider
- **File Management**: Access and modify kin files
- **Text-to-Speech**: Convert text to speech using ElevenLabs
- **Debug Tools**: Endpoints for system diagnostics and monitoring

## Prerequisites

- Python 3.8+
- Anthropic API key (for Claude)
- ElevenLabs API key (for TTS, optional)
- Aider.chat installed

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/kinos.git
   cd kinos
   ```

2. Install dependencies:
   ```
   cd api
   pip install -r requirements.txt
   pip install aider-chat
   ```

3. Create a `.env` file in the api directory:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

## Running the API

Start the API server:
```
cd api
python app.py
```

The server will run on port 5000 by default (configurable via PORT environment variable).

## API Endpoints

### kins
- `POST /api/kins`: Create a new kin
- `GET /api/kins/<blueprint>/kins`: List kins for a blueprint
- `GET /api/kins/all`: List all blueprints and their kins

### Messages
- `GET /api/kins/<blueprint>/<kin_id>/messages`: Get conversation history
- `POST /api/kins/<blueprint>/<kin_id>/messages`: Send a message
- `GET /api/kins/<blueprint>/<kin_id>/aider_logs`: Get Aider logs

### Files
- `GET /api/kins/<path:kin_path>/files`: List kin files
- `GET /api/kins/<path:kin_path>/files/<path:file_path>`: Get file content

### Text-to-Speech
- `POST /api/tts`: Convert text to speech

### Debug
- `GET /api/debug`: Get system debug information
- `GET /api/health`: Health check endpoint

## Docker Deployment

Build and run the Docker container:
```
cd api
docker build -t kinos-api .
docker run -p 5000:5000 -e ANTHROPIC_API_KEY=your_key -e ELEVENLABS_API_KEY=your_key kinos-api
```

## Environment Variables

- `ANTHROPIC_API_KEY`: Required for Claude API access
- `ELEVENLABS_API_KEY`: Required for text-to-speech functionality
- `PORT`: Port to run the API server (default: 5000)
- `WEBSITE_URL`: URL of the website for health checks

## kin Structure

The API organizes kins in a blueprint-centric hierarchy:
```
/blueprints/
  /[blueprint_NAME]/
    /template/          # Template for new kins
    /kins/
      /[kin_ID]/    # Individual kins
```

## License

This kin is licensed under the MIT License - see the LICENSE file for details.
