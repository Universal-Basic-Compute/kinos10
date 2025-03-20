# KinOS API

KinOS API is the backend service for the KinOS Adaptive Context Management System. It provides endpoints for managing projects, messages, files, and text-to-speech functionality.

## Features

- **Project Management**: Create and manage projects for different customers
- **Message Handling**: Process user messages with Claude AI and Aider
- **File Management**: Access and modify project files
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

### Projects
- `POST /api/projects`: Create a new project
- `GET /api/projects/<customer>/projects`: List projects for a customer
- `GET /api/projects/all`: List all customers and their projects

### Messages
- `GET /api/projects/<customer>/<project_id>/messages`: Get conversation history
- `POST /api/projects/<customer>/<project_id>/messages`: Send a message
- `GET /api/projects/<customer>/<project_id>/aider_logs`: Get Aider logs

### Files
- `GET /api/projects/<path:project_path>/files`: List project files
- `GET /api/projects/<path:project_path>/files/<path:file_path>`: Get file content

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

## Project Structure

The API organizes projects in a customer-centric hierarchy:
```
/customers/
  /[CUSTOMER_NAME]/
    /template/          # Template for new projects
    /projects/
      /[PROJECT_ID]/    # Individual projects
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
