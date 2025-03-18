document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const customerSelect = document.getElementById('customer-select');
    const projectSelect = document.getElementById('project-select');
    const createProjectBtn = document.getElementById('create-project-btn');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages');
    const debugOutput = document.getElementById('debug-output');
    
    // Modal elements
    const modal = document.getElementById('create-project-modal');
    const closeModal = document.querySelector('.close');
    const projectNameInput = document.getElementById('project-name');
    const confirmCreateBtn = document.getElementById('confirm-create-btn');
    
    // File browser elements
    const fileTree = document.getElementById('file-tree');
    const fileContentModal = document.getElementById('file-content-modal');
    const fileContentTitle = document.getElementById('file-content-title');
    const fileContentBody = document.getElementById('file-content-body');
    const closeFileModal = document.getElementById('close-file-modal');
    
    // Current state
    let currentCustomer = customerSelect.value;
    let currentProject = projectSelect.value;
    let messageHistory = [];
    let pollingInterval = null;
    let lastMessageTimestamp = null;
    
    // Initialize
    loadProjects(currentCustomer);
    
    // Event listeners
    customerSelect.addEventListener('change', function() {
        currentCustomer = this.value;
        loadProjects(currentCustomer);
        // loadMessages will be called after projects are loaded
    });
    
    projectSelect.addEventListener('change', function() {
        currentProject = this.value;
        loadMessages();
    });
    
    // Add event listeners for page visibility to manage polling
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            // Resume polling when page becomes visible
            if (currentProject !== 'template') {
                startPolling();
            }
        } else {
            // Pause polling when page is hidden
            stopPolling();
        }
    });
    
    createProjectBtn.addEventListener('click', function() {
        modal.style.display = 'block';
    });
    
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    confirmCreateBtn.addEventListener('click', function() {
        const projectName = projectNameInput.value.trim();
        if (projectName) {
            createProject(projectName);
        }
    });
    
    sendBtn.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Window click to close modal
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
        if (e.target === fileContentModal) {
            fileContentModal.style.display = 'none';
        }
    });
    
    // Add event listener for closing the file modal
    closeFileModal.addEventListener('click', function() {
        fileContentModal.style.display = 'none';
    });
    
    // Functions
    function loadProjects(customer) {
        fetch(`/api/customers/${customer}/projects`)
            .then(response => response.json())
            .then(data => {
                projectSelect.innerHTML = '';
                data.projects.forEach(project => {
                    const option = document.createElement('option');
                    option.value = project;
                    option.textContent = project;
                    projectSelect.appendChild(option);
                });
                currentProject = projectSelect.value;
                loadMessages();
            })
            .catch(error => {
                console.error('Error loading projects:', error);
                logDebug('Error loading projects: ' + error.message);
            });
    }
    
    function loadMessages() {
        // Clear messages container
        messagesContainer.innerHTML = '';
        messageHistory = [];
        lastMessageTimestamp = null;
        
        // Stop any existing polling
        stopPolling();
        
        // Load file tree
        loadFileTree();
        
        // Only load messages if not using template
        if (currentProject !== 'template') {
            fetch(`/api/proxy/projects/${currentCustomer}/${currentProject}/messages`)
                .then(response => response.json())
                .then(data => {
                    if (data.messages && data.messages.length > 0) {
                        messageHistory = data.messages;
                        displayMessages(data.messages);
                        
                        // Set the last message timestamp
                        const lastMessage = data.messages[data.messages.length - 1];
                        lastMessageTimestamp = lastMessage.timestamp;
                    }
                    
                    // Start polling for new messages
                    startPolling();
                })
                .catch(error => {
                    console.error('Error loading messages:', error);
                    logDebug('Error loading messages: ' + error.message);
                });
        }
    }
    
    // Function to parse gitignore file content
    function parseGitignore(gitignoreContent) {
        if (!gitignoreContent) return [];
        
        // Split by lines and filter out comments and empty lines
        return gitignoreContent.split('\n')
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('#'));
    }

    // Function to check if a file should be ignored based on gitignore patterns
    function shouldIgnoreFile(filePath, ignorePatterns) {
        if (!ignorePatterns || ignorePatterns.length === 0) return false;
        
        // Simple pattern matching (can be expanded for more complex gitignore rules)
        for (const pattern of ignorePatterns) {
            // Handle directory wildcards (e.g., node_modules/)
            if (pattern.endsWith('/')) {
                const dirPattern = pattern.slice(0, -1);
                if (filePath === dirPattern || filePath.startsWith(dirPattern + '/')) {
                    return true;
                }
            }
            // Handle file extensions (e.g., *.log)
            else if (pattern.startsWith('*.')) {
                const extension = pattern.slice(1); // *.log -> .log
                if (filePath.endsWith(extension)) {
                    return true;
                }
            }
            // Handle exact matches
            else if (filePath === pattern) {
                return true;
            }
            // Handle directory wildcards with extensions (e.g., **/*.log)
            else if (pattern.startsWith('**/')) {
                const subPattern = pattern.slice(3);
                if (filePath.endsWith(subPattern)) {
                    return true;
                }
            }
        }
        
        return false;
    }

    // Function to load the file tree
    function loadFileTree() {
        // For both template and regular projects, we should load files
        const projectPath = currentProject === 'template' ? 
            `${currentCustomer}/template` : 
            `${currentCustomer}/${currentProject}`;
        
        // First try to load .gitignore file
        let ignorePatterns = [];
        
        fetch(`/api/proxy/projects/${projectPath}/files/.gitignore`)
            .then(response => {
                if (response.ok) {
                    return response.text();
                }
                return null;
            })
            .then(gitignoreContent => {
                if (gitignoreContent) {
                    ignorePatterns = parseGitignore(gitignoreContent);
                    logDebug(`Loaded .gitignore with ${ignorePatterns.length} patterns`);
                }
                
                // Now load the file list
                return fetch(`/api/proxy/projects/${projectPath}/files`);
            })
            .catch(() => {
                // If .gitignore fetch fails, just continue with empty patterns
                return fetch(`/api/proxy/projects/${projectPath}/files`);
            })
            .then(response => response.json())
            .then(data => {
                if (data.files && data.files.length > 0) {
                    // Filter out files that match gitignore patterns
                    const filteredFiles = data.files.filter(file => 
                        !shouldIgnoreFile(file.path, ignorePatterns) && 
                        file.path !== '.gitignore' // Also hide .gitignore itself
                    );
                    
                    if (filteredFiles.length > 0) {
                        // Build tree structure from filtered file list
                        const tree = buildFileTree(filteredFiles);
                        // Render the tree
                        fileTree.innerHTML = '';
                        renderFileTree(tree, fileTree);
                    } else {
                        fileTree.innerHTML = '<div class="file-item">No visible files found</div>';
                    }
                } else {
                    fileTree.innerHTML = '<div class="file-item">No files found</div>';
                }
            })
            .catch(error => {
                console.error('Error loading file tree:', error);
                logDebug('Error loading file tree: ' + error.message);
                fileTree.innerHTML = '<div class="file-item">Error loading files</div>';
            });
    }

    // Function to build a tree structure from flat file list
    function buildFileTree(files) {
        const root = { name: '', children: {}, type: 'directory' };
        
        files.forEach(file => {
            const parts = file.path.split('/');
            let current = root;
            
            parts.forEach((part, index) => {
                if (!part) return;
                
                if (!current.children[part]) {
                    current.children[part] = {
                        name: part,
                        children: {},
                        type: index === parts.length - 1 ? file.type : 'directory',
                        path: parts.slice(0, index + 1).join('/')
                    };
                }
                
                current = current.children[part];
            });
        });
        
        return root;
    }

    // Function to render the file tree
    function renderFileTree(node, container, path = '') {
        // Sort children: directories first, then files, both alphabetically
        const sortedChildren = Object.values(node.children).sort((a, b) => {
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            return a.name.localeCompare(b.name);
        });
        
        sortedChildren.forEach(child => {
            const childPath = path ? `${path}/${child.name}` : child.name;
            const item = document.createElement('div');
            
            if (child.type === 'directory') {
                item.className = 'file-item file-folder';
                item.textContent = child.name;
                item.addEventListener('click', function(e) {
                    e.stopPropagation();
                    this.classList.toggle('open');
                    const childrenContainer = this.nextElementSibling;
                    childrenContainer.classList.toggle('open');
                });
                
                container.appendChild(item);
                
                const childrenContainer = document.createElement('div');
                childrenContainer.className = 'file-children';
                container.appendChild(childrenContainer);
                
                renderFileTree(child, childrenContainer, childPath);
            } else {
                item.className = 'file-item file-document';
                item.textContent = child.name;
                item.addEventListener('click', function(e) {
                    e.stopPropagation();
                    openFile(childPath);
                });
                
                container.appendChild(item);
            }
        });
    }

    // Function to open a file
    function openFile(filePath) {
        const projectPath = currentProject === 'template' ? 
            `${currentCustomer}/template` : 
            `${currentCustomer}/${currentProject}`;
        
        fetch(`/api/proxy/projects/${projectPath}/files/${filePath}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(content => {
                // Display file content in modal
                fileContentTitle.textContent = filePath;
                fileContentBody.textContent = content;
                fileContentModal.style.display = 'block';
                logDebug(`Opened file: ${filePath}`);
            })
            .catch(error => {
                console.error('Error opening file:', error);
                logDebug('Error opening file: ' + error.message);
            });
    }
    
    function startPolling() {
        // Clear any existing polling interval
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        // Set up polling every 2 seconds
        pollingInterval = setInterval(pollMessages, 2000);
        
        // Log that polling has started
        logDebug(`Started polling for ${currentCustomer}/${currentProject}`);
    }
    
    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            logDebug('Stopped polling');
        }
    }
    
    function pollMessages() {
        // Only poll if we're not on the template
        if (currentProject === 'template') {
            return;
        }
        
        // Build URL with timestamp if we have one
        let url = `/api/proxy/projects/${currentCustomer}/${currentProject}/messages`;
        if (lastMessageTimestamp) {
            url += `?since=${encodeURIComponent(lastMessageTimestamp)}`;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    // Display only new messages
                    displayMessages(data.messages);
                    
                    // Update the last message timestamp
                    const lastMessage = data.messages[data.messages.length - 1];
                    lastMessageTimestamp = lastMessage.timestamp;
                    
                    // Add to message history
                    messageHistory = messageHistory.concat(data.messages);
                }
            })
            .catch(error => {
                console.error('Error polling messages:', error);
                logDebug('Error polling messages: ' + error.message);
            });
    }
    
    function createProject(projectName) {
        const data = {
            project_name: projectName,
            customer: currentCustomer
        };
        
        fetch('/api/proxy/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            modal.style.display = 'none';
            projectNameInput.value = '';
            logDebug('Project created: ' + JSON.stringify(data));
            
            // Reload projects
            loadProjects(currentCustomer);
        })
        .catch(error => {
            console.error('Error creating project:', error);
            logDebug('Error creating project: ' + error.message);
        });
    }
    
    function sendMessage() {
        const content = messageInput.value.trim();
        if (!content) return;
        
        // Add user message to UI
        addMessageToUI('user', content);
        
        // Clear input
        messageInput.value = '';
        
        // Send to API
        const data = {
            content: content
        };
        
        logDebug(`Sending message to ${currentCustomer}/${currentProject}: ${content}`);
        
        fetch(`/api/proxy/projects/${currentCustomer}/${currentProject}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            logDebug('Message sent, response: ' + JSON.stringify(data));
            
            // The assistant's response will be picked up by polling
        })
        .catch(error => {
            console.error('Error sending message:', error);
            logDebug('Error sending message: ' + error.message);
        });
    }
    
    function displayMessages(messages) {
        messages.forEach(message => {
            addMessageToUI(message.role, message.content);
        });
    }
    
    function addMessageToUI(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        // Format content with line breaks
        const formattedContent = content.replace(/\n/g, '<br>');
        messageDiv.innerHTML = formattedContent;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function logDebug(message) {
        const timestamp = new Date().toISOString();
        debugOutput.innerHTML += `<div>[${timestamp}] ${message}</div>`;
        debugOutput.scrollTop = debugOutput.scrollHeight;
    }
});
