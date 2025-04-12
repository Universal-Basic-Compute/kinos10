document.addEventListener('DOMContentLoaded', function() {
    // Create the chat widget elements
    const body = document.querySelector('body');
    
    // Create container
    const chatWidgetContainer = document.createElement('div');
    chatWidgetContainer.className = 'chat-widget-container';
    
    // Create button
    const chatWidgetButton = document.createElement('div');
    chatWidgetButton.className = 'chat-widget-button';
    chatWidgetButton.innerHTML = '<i class="fas fa-comment"></i>';
    
    // Create panel
    const chatWidgetPanel = document.createElement('div');
    chatWidgetPanel.className = 'chat-widget-panel';
    
    // Create header
    const chatWidgetHeader = document.createElement('div');
    chatWidgetHeader.className = 'chat-widget-header';
    chatWidgetHeader.innerHTML = `
        <h3>KinOS Assistant</h3>
        <button class="chat-widget-close"><i class="fas fa-times"></i></button>
    `;
    
    // Create messages container
    const chatWidgetMessages = document.createElement('div');
    chatWidgetMessages.className = 'chat-widget-messages';
    
    // Create input area
    const chatWidgetInput = document.createElement('div');
    chatWidgetInput.className = 'chat-widget-input';
    chatWidgetInput.innerHTML = `
        <input type="text" placeholder="Type your message...">
        <button><i class="fas fa-paper-plane"></i></button>
    `;
    
    // Assemble the widget
    chatWidgetPanel.appendChild(chatWidgetHeader);
    chatWidgetPanel.appendChild(chatWidgetMessages);
    chatWidgetPanel.appendChild(chatWidgetInput);
    
    chatWidgetContainer.appendChild(chatWidgetButton);
    chatWidgetContainer.appendChild(chatWidgetPanel);
    
    body.appendChild(chatWidgetContainer);
    
    // Add event listeners
    chatWidgetButton.addEventListener('click', function() {
        chatWidgetPanel.classList.add('open');
        // Add initial message if messages are empty
        if (chatWidgetMessages.children.length === 0) {
            addMessage('ai', 'Hello! I\'m the KinOS Assistant. How can I help you today?');
        }
    });
    
    const closeButton = chatWidgetHeader.querySelector('.chat-widget-close');
    closeButton.addEventListener('click', function(e) {
        e.stopPropagation();
        chatWidgetPanel.classList.remove('open');
    });
    
    const inputField = chatWidgetInput.querySelector('input');
    const sendButton = chatWidgetInput.querySelector('button');
    
    // Function to send message
    function sendMessage() {
        const message = inputField.value.trim();
        if (message) {
            // Add user message to chat
            addMessage('user', message);
            
            // Clear input field
            inputField.value = '';
            
            // Show typing indicator
            showTypingIndicator();
            
            // Process the message and get AI response
            processMessage(message);
        }
    }
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    inputField.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Function to add a message to the chat
    function addMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${sender}`;
        messageElement.textContent = text;
        chatWidgetMessages.appendChild(messageElement);
        
        // Scroll to bottom
        chatWidgetMessages.scrollTop = chatWidgetMessages.scrollHeight;
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        typingIndicator.id = 'typing-indicator';
        chatWidgetMessages.appendChild(typingIndicator);
        chatWidgetMessages.scrollTop = chatWidgetMessages.scrollHeight;
    }
    
    // Function to hide typing indicator
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Function to process user message and get AI response
    function processMessage(message) {
        // Show typing indicator
        showTypingIndicator();
        
        // Make API call to KinOS API v2 via our proxy endpoint
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                blueprint: 'kinos',
                kin_id: 'builder'
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add AI response to chat
            addMessage('ai', data.response);
        })
        .catch(error => {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Show error message
            addMessage('ai', "I'm sorry, I'm having trouble connecting to my brain right now. Please try again later.");
            console.error('Error:', error);
        });
    }
});
