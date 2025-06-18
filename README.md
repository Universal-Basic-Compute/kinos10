# KinOS - Operating System for Artificial Intelligence

KinOS is an innovative system that gives long-term memory to AI, enabling the capability to adapt, improve, and remember over time. It works by providing AIs with the ability to build their own context and manage their files through an AI file management system called Aider.

## What is KinOS?

KinOS is an Adaptive Context Management System that allows AI to:
- **Remember** information across sessions
- **Learn** from interactions and improve over time
- **Create and modify** its own files and knowledge base
- **Develop** unique personalities and capabilities
- **Operate autonomously** with self-directed thinking

## Key Features

- **Blueprint System**: Templates that define the behavior and capabilities of AI instances
- **Kin Management**: Create and manage AI instances (kins) from blueprints
- **Long-term Memory**: Persistent storage of conversations and knowledge
- **Self-improvement**: AIs can modify their own files and behavior
- **Multi-channel Communication**: Support for multiple conversation threads
- **Media Processing**: Support for images, text-to-speech, and speech-to-text
- **GitHub Integration**: AIs can edit and push to GitHub repositories
- **Autonomous Thinking**: AIs can generate thoughts and initiatives without user prompting

## Architecture

KinOS organizes AI instances in a blueprint-centric hierarchy:
```
/blueprints/
  /<blueprint_name>/
    /template/          # Template for new kins
    /kins/
      /<kin_id>/        # Individual AI instances
        /messages.json  # Conversation history
        /system.txt     # Core system instructions
        /modes/         # Different operational modes
        /memories/      # Long-term memory storage
        /knowledge/     # Knowledge base
        /images/        # Image storage
```

## Prerequisites

- Python 3.8+
- LLM API keys (supports Claude, GPT, Gemini, DeepSeek, and local models)
- ElevenLabs API key (for TTS, optional)
- Ideogram API key (for image generation, optional)
- Git (for repository features)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/kinos.git
   cd kinos
   ```

2. Install dependencies:
   ```bash
   cd api
   pip install -r requirements.txt
   pip install aider-chat
   ```

3. Create a `.env` file in the api directory:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   IDEOGRAM_API_KEY=your_ideogram_api_key
   ```

## Running KinOS

Start the API server:
```bash
cd api
python app.py
```

The server will run on port 5000 by default (configurable via PORT environment variable).

## API Overview

KinOS provides a comprehensive API (v2) for interacting with AI instances:

### Blueprint Management
- Create, initialize, and reset blueprints
- Manage blueprint templates and configurations

### Kin Management
- Create, copy, rename, and reset kins
- Link kins to GitHub repositories

### Message Interaction
- Send messages to kins and receive responses
- Support for streaming responses
- Multi-channel communication
- Image and file attachments

### File Operations
- Access and modify kin files
- View commit history
- Get file content

### Special Features
- Generate images with Ideogram
- Text-to-speech conversion
- Speech-to-text transcription
- Autonomous thinking

For complete API documentation, see the [API Reference](https://api.kinos-engine.ai/v2/docs).

## Docker Deployment

Build and run the Docker container:
```bash
cd api
docker build -t kinos-api .
docker run -p 5000:5000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  -e ELEVENLABS_API_KEY=your_key \
  kinos-api
```

## Environment Variables

- `ANTHROPIC_API_KEY`: For Claude API access
- `OPENAI_API_KEY`: For GPT API access
- `GEMINI_API_KEY`: For Gemini API access
- `ELEVENLABS_API_KEY`: For text-to-speech functionality
- `IDEOGRAM_API_KEY`: For image generation
- `PORT`: Port to run the API server (default: 5000)
- `DEFAULT_LLM_PROVIDER`: Default LLM provider to use (default: "claude")
- `CLAUDE_MODEL`: Default Claude model (default: "claude-3-sonnet-20240229")
- `OPENAI_MODEL`: Default OpenAI model (default: "gpt-4o")

## Use Cases

- **Personal Assistants**: Create AI assistants that remember your preferences and history
- **Knowledge Workers**: AI researchers that can organize and expand their knowledge base
- **Creative Partners**: AI collaborators for writing, coding, or design projects
- **Code Guardians**: AI instances that understand and can modify codebases
- **Autonomous Agents**: Self-improving AI systems that operate with minimal supervision

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
