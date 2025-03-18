# KinOS 10: Adaptive Context Management System

KinOS 10 is an advanced context management system designed to enhance Large Language Model (LLM) capabilities through automated system prompt and file context management. It provides a structured environment for LLMs to maintain context across sessions, adapt to various tasks, and manage project-specific knowledge.

## Features

- **Persistent Context Management**: Maintains conversation history and relevant context across sessions
- **Adaptive Mode Switching**: Dynamically switches between different operational modes based on user needs
- **File System Integration**: Organizes and manages project-specific files in a structured manner
- **Long-Term Memory**: Stores and retrieves important information for future reference
- **Multi-Customer Templates**: Supports different use cases through specialized customer templates
- **Aider Integration**: Works with Aider.chat for enhanced context management and file editing
- **Web UI**: Simple debug interface for interacting with the system

## Project Structure

KinOS organizes projects in a customer-centric hierarchy:

```
/customers/
  /[CUSTOMER_NAME]/     # e.g., kinos, deskmate
    /template/          # Initial state for new projects
      kinos.txt         # Explanation of how KinOS works
      system.txt        # Base system prompt for the project
      map.json          # Index and purpose of each file
      /modes/           # Different operational modes
      /adaptations/     # Context-specific behaviors
      /memories/        # Long-term storage
      /sources/         # Web-sourced information
    /projects/
      /[PROJECT_ID]/    # Individual user projects
        kinos.txt
        system.txt
        map.json
        thoughts.txt    # Internal reasoning of the AI
        messages.json   # Conversation history
        /modes/
        /adaptations/
        /memories/
        /sources/
```

## Customer Templates

KinOS comes with pre-configured templates for different use cases:

1. **KinOS**: Meta-cognitive system for self-development and architecture design
2. **DeskMate**: Educational assistant for homework help across different subjects
3. **More templates can be added**: Gaming companions, coding assistants, etc.

## Installation

### Prerequisites

- Python 3.8+
- Anthropic API key (for Claude access)
- Aider.chat installed

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/kinos.git
   cd kinos
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

## Usage

### Starting the Services

1. Start the API server:
   ```
   cd api
   python app.py
   ```

2. In a separate terminal, start the web UI:
   ```
   cd app
   python app.py
   ```

3. Access the web UI at `http://localhost:5001`

### Using the Web UI

1. Select a customer from the dropdown (e.g., kinos, deskmate)
2. Create a new project or select an existing one
3. Browse project files in the file browser
4. Send messages to interact with the system
5. View Aider logs to see how files are being updated

## API Endpoints

KinOS provides a RESTful API for integration with other systems:

- `POST /api/projects`: Create a new project
- `POST /api/projects/{customer}/{project_id}/messages`: Send a message
- `GET /api/projects/{customer}/{project_id}/messages`: Get conversation history
- `GET /api/projects/{customer}/{project_id}/files`: List project files
- `GET /api/projects/{customer}/{project_id}/files/{file_path}`: Get file content

## How It Works

1. **Context Building**: When a user sends a message, KinOS analyzes the conversation and selects relevant files to include in the context window.

2. **Response Generation**: The system processes the enhanced context and generates a response using Claude.

3. **File Updates**: In parallel, Aider.chat is used to update project files based on the conversation.

4. **Persistent Memory**: All interactions are stored in the project's file structure, allowing for long-term context retention.

## Deployment

For production deployment:

1. Set up proper authentication and HTTPS
2. Configure environment variables for production settings
3. Use a production-ready web server (e.g., Gunicorn)
4. Consider containerization with Docker

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
