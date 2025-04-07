document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const blueprintSelect = document.getElementById('blueprint-select');
    const kinSelect = document.getElementById('kin-select');
    const createkinBtn = document.getElementById('create-kin-btn');
    const initializeblueprintBtn = document.getElementById('initialize-blueprint-btn');
    const viewAiderLogsBtn = document.getElementById('view-aider-logs-btn');
    const viewGitHistoryBtn = document.getElementById('view-git-history-btn');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages');
    const debugOutput = document.getElementById('debug-output');
    const loadingIndicator = document.getElementById('loading-indicator');
    const sendSpinner = document.getElementById('send-spinner');
    const screenshotBtn = document.getElementById('screenshot-btn');
    
    // Modal elements
    const modal = document.getElementById('create-kin-modal');
    const closeModal = document.querySelector('.close');
    const kinNameInput = document.getElementById('kin-name');
    const confirmCreateBtn = document.getElementById('confirm-create-btn');
    
    // File browser elements
    const fileTree = document.getElementById('file-tree');
    const fileContentModal = document.getElementById('file-content-modal');
    const fileContentTitle = document.getElementById('file-content-title');
    const fileContentBody = document.getElementById('file-content-body');
    const closeFileModal = document.getElementById('close-file-modal');
    
    // Aider logs elements
    const aiderLogsModal = document.getElementById('aider-logs-modal');
    const closeAiderLogs = document.getElementById('close-aider-logs');
    const aiderLogsContent = document.getElementById('aider-logs-content');
    
    // Git history elements
    const gitHistoryModal = document.getElementById('git-history-modal');
    const closeGitHistory = document.getElementById('close-git-history');
    const gitHistoryTbody = document.getElementById('git-history-tbody');
    
    // Current state
    let currentblueprint = blueprintSelect.value;
    let currentkin = kinSelect.value;
    let messageHistory = [];
    let pollingInterval = null;
    let lastMessageTimestamp = null;
    let capturedImages = [];
    
    // Initialize
    loadkins(currentblueprint);
    
    // Event listeners
    blueprintSelect.addEventListener('change', function() {
        currentblueprint = this.value;
        loadkins(currentblueprint);
        // loadMessages will be called after kins are loaded
    });
    
    kinSelect.addEventListener('change', function() {
        currentkin = this.value;
        loadMessages();
    });
    
    // Add event listeners for page visibility to manage polling
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            // Resume polling when page becomes visible
            if (currentkin !== 'template') {
                startPolling();
            }
        } else {
            // Pause polling when page is hidden
            stopPolling();
        }
    });
    
    createkinBtn.addEventListener('click', function() {
        modal.style.display = 'block';
    });
    
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    confirmCreateBtn.addEventListener('click', function() {
        const kinName = kinNameInput.value.trim();
        if (kinName) {
            createkin(kinName);
        }
    });
    
    initializeblueprintBtn.addEventListener('click', function() {
        const blueprint = blueprintSelect.value;
        
        if (confirm(`Are you sure you want to initialize/reinitialize the '${blueprint}' blueprint?`)) {
            fetch(`/api/proxy/blueprints/${blueprint}/initialize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'  // Change content type
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                logDebug(`blueprint initialization: ${JSON.stringify(data)}`);
                alert(`blueprint '${blueprint}' initialized successfully.`);
                
                // Reload kins
                loadkins(blueprint);
            })
            .catch(error => {
                console.error('Error initializing blueprint:', error);
                logDebug('Error initializing blueprint: ' + error.message);
                alert(`Error initializing blueprint: ${error.message}`);
            });
        }
    });
    
    viewAiderLogsBtn.addEventListener('click', function() {
        // Only show logs if not on template
        if (currentkin === 'template') {
            alert('Aider logs are not available for template kins.');
            return;
        }
        
        // Fetch and display Aider logs
        fetch(`/api/proxy/kins/${currentblueprint}/${currentkin}/aider_logs`)
            .then(response => response.json())
            .then(data => {
                aiderLogsContent.textContent = data.logs;
                aiderLogsModal.style.display = 'block';
            })
            .catch(error => {
                console.error('Error fetching Aider logs:', error);
                logDebug('Error fetching Aider logs: ' + error.message);
                alert('Error fetching Aider logs: ' + error.message);
            });
    });
    
    closeAiderLogs.addEventListener('click', function() {
        aiderLogsModal.style.display = 'none';
    });
    
    viewGitHistoryBtn.addEventListener('click', function() {
        // Only show history if not on template
        if (currentkin === 'template') {
            alert('Git history is not available for template kins.');
            return;
        }
        
        // Fetch and display Git history
        fetch(`/api/proxy/kins/${currentblueprint}/${currentkin}/git_history`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Clear existing content
                gitHistoryTbody.innerHTML = '';
                
                if (data.commits && data.commits.length > 0) {
                    // Add each commit to the table
                    data.commits.forEach(commit => {
                        const row = document.createElement('tr');
                        
                        // Hash cell
                        const hashCell = document.createElement('td');
                        hashCell.className = 'commit-hash';
                        hashCell.textContent = commit.hash;
                        row.appendChild(hashCell);
                        
                        // Author cell
                        const authorCell = document.createElement('td');
                        authorCell.className = 'commit-author';
                        authorCell.textContent = commit.author;
                        row.appendChild(authorCell);
                        
                        // Date cell
                        const dateCell = document.createElement('td');
                        dateCell.className = 'commit-date';
                        dateCell.textContent = commit.date;
                        row.appendChild(dateCell);
                        
                        // Message cell
                        const messageCell = document.createElement('td');
                        messageCell.className = 'commit-message';
                        messageCell.textContent = commit.message;
                        row.appendChild(messageCell);
                        
                        gitHistoryTbody.appendChild(row);
                    });
                } else {
                    // No commits found
                    const row = document.createElement('tr');
                    const cell = document.createElement('td');
                    cell.colSpan = 4;
                    cell.textContent = 'No commit history found.';
                    cell.style.textAlign = 'center';
                    row.appendChild(cell);
                    gitHistoryTbody.appendChild(row);
                }
                
                // Show the modal
                gitHistoryModal.style.display = 'block';
            })
            .catch(error => {
                console.error('Error fetching Git history:', error);
                logDebug('Error fetching Git history: ' + error.message);
                
                // Show error in modal
                gitHistoryTbody.innerHTML = '';
                const row = document.createElement('tr');
                const cell = document.createElement('td');
                cell.colSpan = 4;
                cell.textContent = 'Error fetching Git history: ' + error.message;
                cell.style.textAlign = 'center';
                cell.style.color = 'red';
                row.appendChild(cell);
                gitHistoryTbody.appendChild(row);
                
                // Show the modal anyway to display the error
                gitHistoryModal.style.display = 'block';
            });
    });
    
    closeGitHistory.addEventListener('click', function() {
        gitHistoryModal.style.display = 'none';
    });
    
    sendBtn.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Add event listener for screenshot button
    screenshotBtn.addEventListener('click', captureScreenshot);
    
    // Window click to close modal
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
        if (e.target === fileContentModal) {
            fileContentModal.style.display = 'none';
        }
        if (e.target === aiderLogsModal) {
            aiderLogsModal.style.display = 'none';
        }
        if (e.target === gitHistoryModal) {
            gitHistoryModal.style.display = 'none';
        }
    });
    
    // Add event listener for closing the file modal
    closeFileModal.addEventListener('click', function() {
        fileContentModal.style.display = 'none';
    });
    
    // Functions
    function loadkins(blueprint) {
        fetch(`/api/proxy/kins/${blueprint}/kins`)
            .then(response => response.json())
            .then(data => {
                kinSelect.innerHTML = '';
                data.kins.forEach(kin => {
                    const option = document.createElement('option');
                    option.value = kin;
                    option.textContent = kin;
                    kinSelect.appendChild(option);
                });
                currentkin = kinSelect.value;
                loadMessages();
            })
            .catch(error => {
                console.error('Error loading kins:', error);
                logDebug('Error loading kins: ' + error.message);
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
        if (currentkin !== 'template') {
            fetch(`/api/proxy/kins/${currentblueprint}/${currentkin}/messages`)
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
        // Common version control and editor files to always ignore
        const alwaysIgnore = [
            '.git', '.svn', '.hg',           // Version control
            '.vscode', '.idea', '.vs',       // Editors
            '__pycache__', '*.pyc', '*.pyo', // Python
            '.DS_Store',                     // macOS
            '.aider*'                        // Aider files
        ];
        
        // Check against always-ignore patterns first
        for (const pattern of alwaysIgnore) {
            if (pattern.endsWith('/')) {
                // Directory pattern
                const dirPattern = pattern.slice(0, -1);
                if (filePath === dirPattern || filePath.startsWith(dirPattern + '/')) {
                    return true;
                }
            } else if (pattern.startsWith('*.')) {
                // File extension pattern
                const extension = pattern.slice(1); // *.log -> .log
                if (filePath.endsWith(extension)) {
                    return true;
                }
            } else if (pattern.includes('*')) {
                // Simple wildcard pattern (e.g., .aider*)
                const parts = pattern.split('*');
                const prefix = parts[0];
                const suffix = parts[1];
                if (filePath.startsWith(prefix) && filePath.endsWith(suffix)) {
                    return true;
                }
            } else if (filePath === pattern || filePath.startsWith(pattern + '/')) {
                // Exact match or directory
                return true;
            }
        }
        
        // Then check against gitignore patterns
        if (!ignorePatterns || ignorePatterns.length === 0) return false;
        
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
        // For both template and regular kins, we should load files
        const kinPath = currentkin === 'template' ? 
            `${currentblueprint}/template` : 
            `${currentblueprint}/${currentkin}`;
        
        // First try to load .gitignore file
        let ignorePatterns = [];
        
        fetch(`/api/proxy/kins/${kinPath}/files/.gitignore`)
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
                return fetch(`/api/proxy/kins/${kinPath}/files`);
            })
            .catch(() => {
                // If .gitignore fetch fails, just continue with empty patterns
                return fetch(`/api/proxy/kins/${kinPath}/files`);
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
                        path: parts.slice(0, index + 1).join('/'),
                        last_modified: index === parts.length - 1 ? file.last_modified : null
                    };
                }
                
                current = current.children[part];
            });
        });
        
        return root;
    }

    // Function to render the file tree
    function renderFileTree(node, container, path = '') {
        // Sort children: directories first, then files sorted by last_modified date (most recent first)
        const sortedChildren = Object.values(node.children).sort((a, b) => {
            // First sort by type (directories first)
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            
            // Then sort by last_modified date if available (most recent first)
            if (a.last_modified && b.last_modified) {
                return new Date(b.last_modified) - new Date(a.last_modified);
            }
            
            // Fall back to alphabetical sorting if no date is available
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
                
                // Add last modified date to the display if available
                if (child.last_modified) {
                    const modDate = new Date(child.last_modified);
                    const formattedDate = modDate.toLocaleDateString() + ' ' + 
                                         modDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    item.textContent = `${child.name} (${formattedDate})`;
                } else {
                    item.textContent = child.name;
                }
                
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
        const kinPath = currentkin === 'template' ? 
            `${currentblueprint}/template` : 
            `${currentblueprint}/${currentkin}`;
        
        fetch(`/api/proxy/kins/${kinPath}/files/${filePath}`)
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
        logDebug(`Started polling for ${currentblueprint}/${currentkin}`);
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
        if (currentkin === 'template') {
            return;
        }
        
        // Build URL with timestamp if we have one
        let url = `/api/proxy/kins/${currentblueprint}/${currentkin}/messages`;
        if (lastMessageTimestamp) {
            url += `?since=${encodeURIComponent(lastMessageTimestamp)}`;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    // Check if we received an assistant message
                    const hasAssistantMessage = data.messages.some(msg => msg.role === 'assistant');
                    
                    // Display only new messages
                    displayMessages(data.messages);
                    
                    // Update the last message timestamp
                    const lastMessage = data.messages[data.messages.length - 1];
                    lastMessageTimestamp = lastMessage.timestamp;
                    
                    // Add to message history
                    messageHistory = messageHistory.concat(data.messages);
                    
                    // Hide loading indicators if we received an assistant message
                    if (hasAssistantMessage) {
                        loadingIndicator.style.display = 'none';
                        sendSpinner.style.display = 'none';
                        sendBtn.disabled = false;
                        
                        // Log that we received an assistant message
                        logDebug("Received assistant response, hiding loading indicators");
                    }
                }
            })
            .catch(error => {
                console.error('Error polling messages:', error);
                logDebug('Error polling messages: ' + error.message);
                
                // Hide loading indicators on error to prevent hanging
                loadingIndicator.style.display = 'none';
                sendSpinner.style.display = 'none';
                sendBtn.disabled = false;
            });
    }
    
    function createkin(kinName) {
        const data = {
            kin_name: kinName,
            blueprint: currentblueprint
        };
        
        fetch('/api/proxy/kins', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            modal.style.display = 'none';
            kinNameInput.value = '';
            logDebug('kin created: ' + JSON.stringify(data));
            
            // Reload kins
            loadkins(currentblueprint);
        })
        .catch(error => {
            console.error('Error creating kin:', error);
            logDebug('Error creating kin: ' + error.message);
        });
    }
    
    // Function to capture screenshot
    function captureScreenshot() {
        // Create a preview container if it doesn't exist
        let previewContainer = document.querySelector('.image-preview-container');
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.className = 'image-preview-container';
            document.querySelector('.message-input').insertBefore(previewContainer, messageInput);
        }
        
        // Use html2canvas to capture the visible part of the page
        html2canvas(document.body).then(canvas => {
            // Convert canvas to base64 image
            const imageData = canvas.toDataURL('image/png');
            
            // Add to captured images array
            capturedImages.push(imageData);
            
            // Create preview element
            const preview = document.createElement('div');
            preview.className = 'image-preview';
            
            // Create image element
            const img = document.createElement('img');
            img.src = imageData;
            preview.appendChild(img);
            
            // Create remove button
            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-image';
            removeBtn.innerHTML = '×';
            removeBtn.addEventListener('click', function() {
                // Remove from array
                const index = capturedImages.indexOf(imageData);
                if (index > -1) {
                    capturedImages.splice(index, 1);
                }
                
                // Remove preview
                preview.remove();
                
                // Remove container if empty
                if (previewContainer.children.length === 0) {
                    previewContainer.remove();
                }
            });
            preview.appendChild(removeBtn);
            
            // Add to preview container
            previewContainer.appendChild(preview);
            
            logDebug('Screenshot captured');
        }).catch(error => {
            console.error('Error capturing screenshot:', error);
            logDebug('Error capturing screenshot: ' + error.message);
        });
    }

    function sendMessage() {
        const content = messageInput.value.trim();
        if (!content && capturedImages.length === 0) return;
        
        // Add user message to UI
        addMessageToUI('user', content);
        
        // Clear input
        messageInput.value = '';
        
        // Show loading indicators
        loadingIndicator.style.display = 'block';
        sendSpinner.style.display = 'inline-block';
        sendBtn.disabled = true;
        
        // Scroll to show the loading indicator
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Set a timeout to hide loading indicators if no response after 30 seconds
        const loadingTimeout = setTimeout(() => {
            if (loadingIndicator.style.display === 'block') {
                loadingIndicator.style.display = 'none';
                sendSpinner.style.display = 'none';
                sendBtn.disabled = false;
                logDebug("Response timeout - hiding loading indicators");
                addMessageToUI('assistant', "I'm sorry, but I didn't receive a response in time. Please try again.");
            }
        }, 30000);
        
        // Send to API
        const data = {
            content: content,
            images: capturedImages
        };
        
        logDebug(`Sending message to ${currentblueprint}/${currentkin}: ${content} with ${capturedImages.length} images`);
        
        fetch(`/api/proxy/kins/${currentblueprint}/${currentkin}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            logDebug('Message sent, response: ' + JSON.stringify(data));
            
            // Clear the timeout
            clearTimeout(loadingTimeout);
            
            // If the response contains a direct answer, display it immediately
            if (data.response) {
                addMessageToUI('assistant', data.response);
                loadingIndicator.style.display = 'none';
                sendSpinner.style.display = 'none';
                sendBtn.disabled = false;
            }
            // Otherwise, the assistant's response will be picked up by polling
            
            // Clear captured images
            capturedImages = [];
            
            // Remove image previews
            const previewContainer = document.querySelector('.image-preview-container');
            if (previewContainer) {
                previewContainer.remove();
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            logDebug('Error sending message: ' + error.message);
            
            // Clear the timeout
            clearTimeout(loadingTimeout);
            
            // Hide loading indicators on error
            loadingIndicator.style.display = 'none';
            sendSpinner.style.display = 'none';
            sendBtn.disabled = false;
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
        
        // Add avatar container
        const avatarContainer = document.createElement('div');
        avatarContainer.className = 'avatar-container';
        
        // Add avatar image based on role
        const avatarImg = document.createElement('img');
        avatarImg.className = 'avatar';
        if (role === 'user') {
            avatarImg.src = '/static/images/user-avatar.png';
        } else {
            avatarImg.src = '/static/images/assistant-avatar.png';
        }
        avatarContainer.appendChild(avatarImg);
        
        // Create message content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'message-content';
        
        // Format content with line breaks
        const formattedContent = content.replace(/\n/g, '<br>');
        contentContainer.innerHTML = formattedContent;
        
        // Add TTS button for assistant messages
        if (role === 'assistant') {
            const ttsButton = document.createElement('button');
            ttsButton.className = 'tts-button';
            ttsButton.innerHTML = '🔊';
            ttsButton.onclick = () => playTTS(content);
            contentContainer.appendChild(ttsButton);
        }
        
        // Assemble the message
        messageDiv.appendChild(avatarContainer);
        messageDiv.appendChild(contentContainer);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Add TTS function
    async function playTTS(text) {
        try {
            const response = await fetch('/v2/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text })
            });
            
            if (!response.ok) throw new Error('TTS request failed');
            
            // Create and play audio from the response
            const blob = await response.blob();
            const audio = new Audio(URL.createObjectURL(blob));
            audio.play();
        } catch (error) {
            console.error('TTS error:', error);
        }
    }
    
    function logDebug(message) {
        const timestamp = new Date().toISOString();
        debugOutput.innerHTML += `<div>[${timestamp}] ${message}</div>`;
        debugOutput.scrollTop = debugOutput.scrollHeight;
    }
});
