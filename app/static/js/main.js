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
    
    // Current state
    let currentCustomer = customerSelect.value;
    let currentProject = projectSelect.value;
    let messageHistory = [];
    
    // Initialize
    loadProjects(currentCustomer);
    
    // Event listeners
    customerSelect.addEventListener('change', function() {
        currentCustomer = this.value;
        loadProjects(currentCustomer);
    });
    
    projectSelect.addEventListener('change', function() {
        currentProject = this.value;
        loadMessages();
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
        
        // Only load messages if not using template
        if (currentProject !== 'template') {
            fetch(`/api/proxy/projects/${currentCustomer}/${currentProject}/messages`)
                .then(response => response.json())
                .then(data => {
                    if (data.messages && data.messages.length > 0) {
                        messageHistory = data.messages;
                        displayMessages(data.messages);
                    }
                })
                .catch(error => {
                    console.error('Error loading messages:', error);
                    logDebug('Error loading messages: ' + error.message);
                });
        }
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
            
            // For now, just display the selected files as the response
            // In a real implementation, we would poll for the assistant's response
            if (data.selected_files) {
                const responseText = `Selected files for context:\n${data.selected_files.join('\n')}`;
                addMessageToUI('assistant', responseText);
            }
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
