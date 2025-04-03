document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
    
    // Fetch kins from API
    fetchkins();
    
    // Function to fetch kins from API
    function fetchkins() {
        const sidebarContent = document.querySelector('.sidebar-content');
        if (sidebarContent) {
            sidebarContent.innerHTML = '<div class="loading"><p>Loading kins...</p></div>';
        }
        
        fetch('/api/kins/all')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Render the blueprint sections
                renderblueprints(data.blueprints, data.kins);
            })
            .catch(error => {
                console.error('Error fetching kins:', error);
                // Show error message in sidebar
                if (sidebarContent) {
                    sidebarContent.innerHTML = `
                        <div class="error-message">
                            <p>Error loading kins. Please try again later.</p>
                            <button id="retry-button" class="button primary">Retry</button>
                        </div>
                    `;
                    
                    // Add retry button functionality
                    const retryButton = document.getElementById('retry-button');
                    if (retryButton) {
                        retryButton.addEventListener('click', fetchkins);
                    }
                }
            });
    }
    
    // Function to render blueprint sections
    function renderblueprints(blueprints, kins) {
        const sidebarContent = document.querySelector('.sidebar-content');
        if (!sidebarContent) return;
        
        // Clear existing content
        sidebarContent.innerHTML = '';
        
        // If no blueprints, show message
        if (!blueprints || blueprints.length === 0) {
            sidebarContent.innerHTML = '<p class="no-data">No blueprints found.</p>';
            return;
        }
        
        // Create blueprint sections
        blueprints.forEach(blueprint => {
            const blueprintkins = kins[blueprint] || [];
            
            const blueprintSection = document.createElement('div');
            blueprintSection.className = 'blueprint-section';
            
            const blueprintHeader = document.createElement('div');
            blueprintHeader.className = 'blueprint-header';
            blueprintHeader.innerHTML = `
                <span class="blueprint-name">${blueprint}</span>
                <i class="fas fa-chevron-down"></i>
            `;
            
            const kinList = document.createElement('ul');
            kinList.className = 'kin-list';
            
            // Add kins to the list
            blueprintkins.forEach(kin => {
                const kinItem = document.createElement('li');
                kinItem.innerHTML = `<a href="/kins/${blueprint}/${kin}">${kin}</a>`;
                kinList.appendChild(kinItem);
            });
            
            // Add event listener to toggle kin list
            blueprintHeader.addEventListener('click', function() {
                this.classList.toggle('collapsed');
                kinList.classList.toggle('expanded');
                
                // Update the chevron icon
                const icon = this.querySelector('i');
                if (kinList.classList.contains('expanded')) {
                    icon.classList.remove('fa-chevron-right');
                    icon.classList.add('fa-chevron-down');
                } else {
                    icon.classList.remove('fa-chevron-down');
                    icon.classList.add('fa-chevron-right');
                }
            });
            
            blueprintSection.appendChild(blueprintHeader);
            blueprintSection.appendChild(kinList);
            sidebarContent.appendChild(blueprintSection);
        });
        
        // Expand the first blueprint section by default
        const firstblueprintHeader = sidebarContent.querySelector('.blueprint-header');
        if (firstblueprintHeader) {
            firstblueprintHeader.click();
        }
        
        // Highlight active kin if applicable
        highlightActivekin();
    }
    
    // Function to highlight the active kin
    function highlightActivekin() {
        const currentPath = window.location.pathname;
        const kinLinks = document.querySelectorAll('.kin-list li a');
        
        kinLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
                
                // Make sure parent blueprint section is expanded
                const parentList = link.closest('.kin-list');
                if (parentList && !parentList.classList.contains('expanded')) {
                    const parentHeader = parentList.previousElementSibling;
                    if (parentHeader) {
                        parentHeader.click();
                    }
                }
            }
        });
    }
});
