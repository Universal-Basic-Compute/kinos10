document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
    
    // Fetch projects from API
    fetchProjects();
    
    // Function to fetch projects from API
    function fetchProjects() {
        const sidebarContent = document.querySelector('.sidebar-content');
        if (sidebarContent) {
            sidebarContent.innerHTML = '<div class="loading"><p>Loading projects...</p></div>';
        }
        
        fetch('/api/proxy/projects/all')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Render the customer sections
                renderCustomers(data.customers, data.projects);
            })
            .catch(error => {
                console.error('Error fetching projects:', error);
                // Show error message in sidebar
                if (sidebarContent) {
                    sidebarContent.innerHTML = `
                        <div class="error-message">
                            <p>Error loading projects. Please try again later.</p>
                            <button id="retry-button" class="button primary">Retry</button>
                        </div>
                    `;
                    
                    // Add retry button functionality
                    const retryButton = document.getElementById('retry-button');
                    if (retryButton) {
                        retryButton.addEventListener('click', fetchProjects);
                    }
                }
            });
    }
    
    // Function to render customer sections
    function renderCustomers(customers, projects) {
        const sidebarContent = document.querySelector('.sidebar-content');
        if (!sidebarContent) return;
        
        // Clear existing content
        sidebarContent.innerHTML = '';
        
        // If no customers, show message
        if (!customers || customers.length === 0) {
            sidebarContent.innerHTML = '<p class="no-data">No customers found.</p>';
            return;
        }
        
        // Create customer sections
        customers.forEach(customer => {
            const customerProjects = projects[customer] || [];
            
            const customerSection = document.createElement('div');
            customerSection.className = 'customer-section';
            
            const customerHeader = document.createElement('div');
            customerHeader.className = 'customer-header';
            customerHeader.innerHTML = `
                <span class="customer-name">${customer}</span>
                <i class="fas fa-chevron-down"></i>
            `;
            
            const projectList = document.createElement('ul');
            projectList.className = 'project-list';
            
            // Add projects to the list
            customerProjects.forEach(project => {
                const projectItem = document.createElement('li');
                projectItem.innerHTML = `<a href="/projects/${customer}/${project}">${project}</a>`;
                projectList.appendChild(projectItem);
            });
            
            // Add event listener to toggle project list
            customerHeader.addEventListener('click', function() {
                this.classList.toggle('collapsed');
                projectList.classList.toggle('expanded');
                
                // Update the chevron icon
                const icon = this.querySelector('i');
                if (projectList.classList.contains('expanded')) {
                    icon.classList.remove('fa-chevron-right');
                    icon.classList.add('fa-chevron-down');
                } else {
                    icon.classList.remove('fa-chevron-down');
                    icon.classList.add('fa-chevron-right');
                }
            });
            
            customerSection.appendChild(customerHeader);
            customerSection.appendChild(projectList);
            sidebarContent.appendChild(customerSection);
        });
        
        // Expand the first customer section by default
        const firstCustomerHeader = sidebarContent.querySelector('.customer-header');
        if (firstCustomerHeader) {
            firstCustomerHeader.click();
        }
        
        // Highlight active project if applicable
        highlightActiveProject();
    }
    
    // Function to highlight the active project
    function highlightActiveProject() {
        const currentPath = window.location.pathname;
        const projectLinks = document.querySelectorAll('.project-list li a');
        
        projectLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
                
                // Make sure parent customer section is expanded
                const parentList = link.closest('.project-list');
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
