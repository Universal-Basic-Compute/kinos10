document.addEventListener('DOMContentLoaded', function() {
    // File explorer toggle
    const fileExplorerToggle = document.getElementById('file-explorer-toggle');
    const fileExplorer = document.querySelector('.file-explorer');
    
    if (fileExplorerToggle && fileExplorer) {
        fileExplorerToggle.addEventListener('click', function() {
            fileExplorer.classList.toggle('collapsed');
        });
    }
    
    // Back to map button
    const backToMapButton = document.getElementById('back-to-map');
    const projectMapContainer = document.getElementById('project-map-container');
    const fileContentContainer = document.getElementById('file-content-container');
    
    if (backToMapButton && projectMapContainer && fileContentContainer) {
        backToMapButton.addEventListener('click', function() {
            fileContentContainer.style.display = 'none';
            projectMapContainer.style.display = 'block';
        });
    }
    
    // Check if we're on a project detail page
    if (!projectMapContainer) return;
    
    // Get project info from data attributes
    const customer = projectMapContainer.dataset.customer;
    const project = projectMapContainer.dataset.project;
    
    if (!customer || !project) return;
    
    // Load file tree
    loadFileTree(customer, project);
    
    // Function to load file tree
    function loadFileTree(customer, project) {
        const fileExplorerContent = document.querySelector('.file-explorer-content');
        if (!fileExplorerContent) return;
        
        fileExplorerContent.innerHTML = '<div class="loading"><p>Loading files...</p></div>';
        
        const projectPath = `${customer}/${project}`;
        
        fetch(`/api/projects/${projectPath}/files`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.files && data.files.length > 0) {
                    renderFileTree(data.files);
                } else {
                    fileExplorerContent.innerHTML = '<p class="no-data">No files found.</p>';
                }
            })
            .catch(error => {
                console.error('Error loading files:', error);
                fileExplorerContent.innerHTML = `
                    <div class="error-message">
                        <p>Error loading files. Please try again later.</p>
                        <button id="retry-files-button" class="button primary">Retry</button>
                    </div>
                `;
                
                // Add retry button functionality
                const retryButton = document.getElementById('retry-files-button');
                if (retryButton) {
                    retryButton.addEventListener('click', () => loadFileTree(customer, project));
                }
            });
    }
    
    // Function to render file tree
    function renderFileTree(files) {
        const fileExplorerContent = document.querySelector('.file-explorer-content');
        if (!fileExplorerContent) return;
        
        // Build a tree structure from flat file list
        const root = { name: '', children: {}, type: 'directory' };
        
        files.forEach(file => {
            const parts = file.path.split('/');
            let current = root;
            
            parts.forEach((part, index) => {
                if (!part) return;
                
                if (!current.children[part]) {
                    const isLastPart = index === parts.length - 1;
                    current.children[part] = {
                        name: part,
                        path: parts.slice(0, index + 1).join('/'),
                        children: {},
                        type: isLastPart ? file.type : 'directory',
                        last_modified: file.last_modified
                    };
                }
                
                current = current.children[part];
            });
        });
        
        // Create HTML for the file tree
        const treeHtml = `<ul class="file-tree">${renderTreeNode(root, true)}</ul>`;
        fileExplorerContent.innerHTML = treeHtml;
        
        // Add event listeners to tree items
        addTreeEventListeners();
    }
    
    // Function to render a tree node recursively
    function renderTreeNode(node, isRoot = false) {
        if (isRoot) {
            // For the root node, just render its children
            return Object.values(node.children)
                .sort((a, b) => {
                    // Directories first, then files
                    if (a.type === 'directory' && b.type !== 'directory') return -1;
                    if (a.type !== 'directory' && b.type === 'directory') return 1;
                    // Then sort by name
                    return a.name.localeCompare(b.name);
                })
                .map(child => renderTreeNode(child))
                .join('');
        }
        
        const hasChildren = Object.keys(node.children).length > 0;
        const isDirectory = node.type === 'directory';
        
        // Determine icon based on file type or directory
        let icon = isDirectory ? 'fa-folder' : 'fa-file-alt';
        
        // More specific icons based on file extension
        if (!isDirectory) {
            const extension = node.name.split('.').pop().toLowerCase();
            if (['js', 'jsx'].includes(extension)) icon = 'fa-file-code';
            else if (['html', 'htm'].includes(extension)) icon = 'fa-file-code';
            else if (['css', 'scss', 'sass'].includes(extension)) icon = 'fa-file-code';
            else if (['py'].includes(extension)) icon = 'fa-file-code';
            else if (['md', 'txt'].includes(extension)) icon = 'fa-file-alt';
            else if (['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(extension)) icon = 'fa-file-image';
            else if (['json'].includes(extension)) icon = 'fa-file-code';
        }
        
        // Create HTML for this node
        let html = `<li>`;
        
        if (isDirectory) {
            html += `
                <div class="file-tree-item" data-path="${node.path}" data-type="directory">
                    <span class="file-tree-toggle ${hasChildren ? '' : 'hidden'}">
                        <i class="fas fa-caret-down"></i>
                    </span>
                    <i class="fas ${icon}"></i>
                    <span>${node.name}</span>
                </div>
            `;
            
            if (hasChildren) {
                html += `<ul>`;
                html += Object.values(node.children)
                    .sort((a, b) => {
                        // Directories first, then files
                        if (a.type === 'directory' && b.type !== 'directory') return -1;
                        if (a.type !== 'directory' && b.type === 'directory') return 1;
                        // Then sort by name
                        return a.name.localeCompare(b.name);
                    })
                    .map(child => renderTreeNode(child))
                    .join('');
                html += `</ul>`;
            }
        } else {
            html += `
                <div class="file-tree-item" data-path="${node.path}" data-type="file">
                    <span class="file-tree-toggle hidden">
                        <i class="fas fa-caret-down"></i>
                    </span>
                    <i class="fas ${icon}"></i>
                    <span>${node.name}</span>
                </div>
            `;
        }
        
        html += `</li>`;
        return html;
    }
    
    // Function to add event listeners to tree items
    function addTreeEventListeners() {
        // Toggle directory expansion
        document.querySelectorAll('.file-tree-toggle:not(.hidden)').forEach(toggle => {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                
                const item = this.closest('.file-tree-item');
                const ul = item.nextElementSibling;
                
                if (ul && ul.tagName === 'UL') {
                    ul.style.display = ul.style.display === 'none' ? 'block' : 'none';
                    this.classList.toggle('collapsed');
                }
            });
        });
        
        // Handle file click
        document.querySelectorAll('.file-tree-item[data-type="file"]').forEach(item => {
            item.addEventListener('click', function() {
                const path = this.dataset.path;
                
                // Remove active class from all items
                document.querySelectorAll('.file-tree-item').forEach(el => {
                    el.classList.remove('active');
                });
                
                // Add active class to this item
                this.classList.add('active');
                
                // Load and display file content
                loadFileContent(customer, project, path);
            });
        });
        
        // Handle directory click (toggle expansion)
        document.querySelectorAll('.file-tree-item[data-type="directory"]').forEach(item => {
            item.addEventListener('click', function(e) {
                // Only handle if the click wasn't on the toggle button
                if (!e.target.closest('.file-tree-toggle')) {
                    const ul = this.nextElementSibling;
                    const toggle = this.querySelector('.file-tree-toggle');
                    
                    if (ul && ul.tagName === 'UL') {
                        ul.style.display = ul.style.display === 'none' ? 'block' : 'none';
                        if (toggle) toggle.classList.toggle('collapsed');
                    }
                }
            });
        });
    }
    
    // Function to load file content
    function loadFileContent(customer, project, filePath) {
        const projectPath = `${customer}/${project}`;
        const fileContentTitle = document.getElementById('file-content-title');
        const fileContent = document.getElementById('file-content');
        
        if (!fileContentTitle || !fileContent) return;
        
        // Show loading state
        fileContent.innerHTML = 'Loading file content...';
        fileContentTitle.textContent = filePath.split('/').pop();
        
        // Hide map, show file content
        if (projectMapContainer && fileContentContainer) {
            projectMapContainer.style.display = 'none';
            fileContentContainer.style.display = 'flex';
        }
        
        // Fetch file content
        fetch(`/api/projects/${projectPath}/files/${filePath}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                // Check if it's an image
                const contentType = response.headers.get('Content-Type');
                if (contentType && contentType.startsWith('image/')) {
                    return response.blob().then(blob => {
                        return { type: 'image', data: URL.createObjectURL(blob) };
                    });
                }
                
                // Otherwise treat as text
                return response.text().then(text => {
                    return { type: 'text', data: text };
                });
            })
            .then(result => {
                if (result.type === 'image') {
                    // Display image
                    fileContent.innerHTML = `<img src="${result.data}" alt="${filePath}" style="max-width: 100%;">`;
                } else {
                    // Display text content
                    fileContent.textContent = result.data;
                    
                    // Apply syntax highlighting if available
                    if (typeof hljs !== 'undefined') {
                        fileContent.innerHTML = hljs.highlightAuto(result.data).value;
                    }
                }
            })
            .catch(error => {
                console.error('Error loading file content:', error);
                fileContent.innerHTML = `<div class="error-message">Error loading file content: ${error.message}</div>`;
            });
    }
});
