# KinOS 10: Adaptive Context Management System
## Specification Document

### 1. System Overview

KinOS 10 is an advanced wrapper around Aider.chat that provides automated system prompt and file context management within an online hosted environment. The system enables LLMs to adapt to various tasks continuously while maintaining long-term context memory across sessions.

#### 1.1 Core Capabilities
- **Persistent Context Management**: Maintains conversation history and relevant context across sessions
- **Adaptive Mode Switching**: Dynamically switches between different operational modes based on user needs
- **File System Integration**: Organizes and manages project-specific files in a structured manner
- **Long-Term Memory**: Stores and retrieves important information for future reference
- **Web Source Integration**: Gathers and incorporates information from external sources
- **Multi-Modal Support**: Handles text, code, and image inputs/outputs
- **API-Based Architecture**: Provides HTTP endpoints for seamless integration with frontends

#### 1.2 Target Use Cases
- Gaming companion
- Homework mentor
- Coding desktop assistant

### 2. System Architecture

#### 2.1 High-Level Components
1. **Project Manager**: Handles project lifecycle and structure maintenance
2. **Context Builder**: Selects relevant files for context window construction
3. **Context Updater**: Modifies project files based on conversation
4. **Response Generator**: Processes context and generates responses
5. **API Interface**: Provides endpoints for external systems

#### 2.2 Data Flow
1. Frontend sends request to API with PROJECT identifier and message
2. Project Manager loads project structure
3. Context Builder analyzes conversation and selects relevant files
4. Response Generator processes enhanced context and creates response
5. Context Updater modifies necessary files
6. Frontend polls for updates in messages.json

### 3. Project Structure

Each project follows a standardized folder structure:

```
/PROJECT_NAME/
  kinos.txt         # Explanation of how KinOS works
  system.txt        # Base system prompt for the project
  map.json          # Index and purpose of each file
  thoughts.txt      # Internal reasoning of the AI
  messages.json     # Conversation history
  /modes/           # Different operational modes
    general.txt     # Default mode
    [custom].txt    # Project-specific modes
  /adaptations/     # Context-specific behaviors
    [context].txt   # Adaptation instructions
  /memories/        # Long-term storage
    [category]/     # Categorized memories
  /sources/         # Web-sourced information
    [source].txt    # External information
  /images/          # Visual content
    [image].jpg     # Stored images
```

#### 3.1 File Descriptions

##### 3.1.1 Core Files
- **kinos.txt**: Explains the KinOS system to the LLM
- **system.txt**: Contains the base system prompt for the project
- **map.json**: JSON file describing each file's purpose and relationship
- **thoughts.txt**: Internal reasoning log of the AI, not directly shared with users
- **messages.json**: JSON array of message objects with user/assistant attribution

##### 3.1.2 Directories
- **modes/**: Contains different operational modes the system can adopt
- **adaptations/**: Contains instructions for adapting to specific contexts
- **memories/**: Stores important information for long-term reference
- **sources/**: Contains information gathered from external sources
- **images/**: Stores visual content related to the project

### 4. API Specification

#### 4.1 Endpoints

##### 4.1.1 Initialize Project
```
POST /api/projects
```
Request:
```json
{
  "project_name": "string",
  "template": "string" (optional)
}
```
Response:
```json
{
  "project_id": "string",
  "status": "created"
}
```

##### 4.1.2 Send Message
```
POST /api/projects/{project_id}/messages
```
Request:
```json
{
  "content": "string",
  "attachments": [
    {
      "type": "image|file",
      "content": "base64_string|url"
    }
  ] (optional)
}
```
Response:
```json
{
  "status": "processing",
  "message_id": "string"
}
```

##### 4.1.3 Poll Messages
```
GET /api/projects/{project_id}/messages?since={timestamp}
```
Response:
```json
{
  "messages": [
    {
      "id": "string",
      "role": "user|assistant",
      "content": "string",
      "timestamp": "ISO8601",
      "attachments": [] (optional)
    }
  ]
}
```

##### 4.1.4 Get Project Files
```
GET /api/projects/{project_id}/files
```
Response:
```json
{
  "files": [
    {
      "path": "string",
      "type": "file|directory",
      "last_modified": "ISO8601"
    }
  ]
}
```

##### 4.1.5 Get File Content
```
GET /api/projects/{project_id}/files/{file_path}
```
Response:
```
File content with appropriate Content-Type header
```

### 5. Core Components Implementation

#### 5.1 Context Builder

The Context Builder selects relevant files to include in the LLM's context window:

1. **Context Analysis**: Processes the current conversation state
2. **Relevance Scoring**: Assigns relevance scores to project files
3. **Context Window Construction**: Optimizes token usage while maintaining relevance
4. **Dynamic Adaptation**: Adjusts selection based on conversation flow

Implementation:
```python
def build_context(project_id, current_message):
    # Load project structure
    project = load_project(project_id)
    
    # Always include these files
    core_files = [
        "kinos.txt",
        "system.txt",
        "map.json"
    ]
    
    # Get recent messages (limiting to conserve tokens)
    recent_messages = get_recent_messages(project_id, limit=10)
    
    # Generate a context selection prompt
    selection_prompt = f"""
    Based on the current conversation:
    {format_messages(recent_messages)}
    
    And the new message:
    {current_message}
    
    Which project files would be most relevant to include in the context?
    Available files: {list_project_files(project_id)}
    
    Return a JSON array of file paths, sorted by relevance.
    """
    
    # LLM call to determine relevant files
    relevant_files = llm_select_files(selection_prompt)
    
    # Combine and optimize context
    context = build_optimized_context(core_files, relevant_files, recent_messages)
    
    return context
```

#### 5.2 Context Updater

The Context Updater modifies project files based on the conversation:

1. **Update Detection**: Identifies which files need to be updated
2. **Content Generation**: Generates new file content
3. **Consistency Check**: Ensures updates maintain project consistency
4. **File System Integration**: Writes updates to the file system

Implementation:
```python
def update_project_files(project_id, llm_response):
    # Extract file update instructions from LLM response
    file_updates = parse_update_instructions(llm_response)
    
    # Update messages.json with new response
    append_message(project_id, "assistant", llm_response.message)
    
    # Update thoughts.txt with reasoning
    append_thoughts(project_id, llm_response.reasoning)
    
    # Process each file update
    for update in file_updates:
        path = update["path"]
        content = update["content"]
        operation = update["operation"]  # create, update, delete
        
        if operation == "create":
            create_file(project_id, path, content)
        elif operation == "update":
            update_file(project_id, path, content)
        elif operation == "delete":
            delete_file(project_id, path)
    
    # Update map.json if files were added or removed
    if any(u["operation"] in ["create", "delete"] for u in file_updates):
        update_map(project_id)
```

#### 5.3 Response Generator

The Response Generator processes the context and generates responses:

1. **Context Processing**: Analyzes the constructed context
2. **Response Generation**: Generates user-facing response
3. **File Update Planning**: Determines necessary file updates
4. **Mode Selection**: Suggests mode changes if needed

Implementation:
```python
def generate_response(project_id, context, message):
    # Create Aider instance
    aider_instance = aider.Aider()
    
    # Configure Aider with project-specific settings
    configure_aider(aider_instance, project_id)
    
    # Process with Aider
    aider_response = aider_instance.process(context, message)
    
    # Parse response and extract components
    response = {
        "message": extract_user_message(aider_response),
        "reasoning": extract_reasoning(aider_response),
        "file_updates": extract_file_updates(aider_response),
        "mode_suggestion": extract_mode_suggestion(aider_response)
    }
    
    return response
```

### 6. Use Case Implementations

#### 6.1 Gaming Companion

Project structure for gaming companion:
```
/gaming_companion/
  system.txt          # Gaming-focused system prompt
  /modes/
    general.txt       # Default interaction mode
    game_analysis.txt # Mode for analyzing games
    strategy.txt      # Mode for providing strategic advice
    lore.txt          # Mode for discussing game lore
  /adaptations/
    game_specific/    # Game-specific adaptations
    player_level.txt  # Adaptations based on player skill
  /memories/
    games/            # Information about specific games
    player/           # Player preferences and history
  /sources/
    game_wikis/       # Information from official wikis
    strategy_guides/  # Information from strategy guides
```

#### 6.2 Homework Mentor

Project structure for homework mentor:
```
/homework_mentor/
  system.txt           # Education-focused system prompt
  /modes/
    general.txt        # Default interaction mode
    explainer.txt      # Mode for explaining concepts
    quiz.txt           # Mode for testing knowledge
    research.txt       # Mode for guiding research
  /adaptations/
    subject/           # Subject-specific adaptations
    grade_level.txt    # Adaptations based on education level
  /memories/
    subjects/          # Subject-specific knowledge
    student/           # Student progress and preferences
  /sources/
    textbooks/         # Information from educational sources
    exercises/         # Practice problems and solutions
```

#### 6.3 Coding Assistant

Project structure for coding assistant:
```
/coding_assistant/
  system.txt           # Development-focused system prompt
  /modes/
    general.txt        # Default interaction mode
    architect.txt      # Mode for system design
    debugger.txt       # Mode for debugging issues
    teacher.txt        # Mode for explaining concepts
  /adaptations/
    languages/         # Language-specific adaptations
    frameworks/        # Framework-specific adaptations
  /memories/
    snippets/          # Useful code patterns
    projects/          # Information about user projects
  /sources/
    documentation/     # Information from official docs
    best_practices/    # Coding standards and patterns
```

### 7. Implementation Plan

#### 7.1 Phase 1: Core System
- Implement basic project structure
- Develop API endpoints
- Create context builder/updater logic
- Integrate with Aider.chat

#### 7.2 Phase 2: Use Case Adaptation
- Implement gaming companion template
- Implement homework mentor template
- Implement coding assistant template
- Test with real-world scenarios

#### 7.3 Phase 3: Advanced Features
- Implement web source integration
- Add image handling capabilities
- Develop mode switching optimization
- Enhance memory management

#### 7.4 Phase 4: Deployment
- Set up hosting infrastructure
- Implement authentication and security
- Develop monitoring and logging
- Create user documentation

### 8. Technical Requirements

#### 8.1 Backend
- Python 3.8+
- Flask/FastAPI for API endpoints
- Integration with Aider.chat
- File system access
- LLM API integration

#### 8.2 Frontend (for testing)
- Simple web interface for interaction
- Polling mechanism for updates
- File browser component
- Message display component

#### 8.3 Deployment
- Docker container support
- HTTPS support
- Authentication system
- Data backup mechanisms

### 9. Future Enhancements

- **Multi-User Projects**: Allow multiple users to collaborate on the same project
- **Custom Templates**: User-definable project templates
- **Advanced Analytics**: Track and analyze LLM performance and usage patterns
- **Voice Integration**: Add support for voice input/output
- **GitHub Integration**: Connect with repositories for code assistance
- **Plugin System**: Allow for extensions to core functionality