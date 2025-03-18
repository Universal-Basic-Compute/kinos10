document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
    
    // Customer section toggle
    const customerHeaders = document.querySelectorAll('.customer-header');
    
    customerHeaders.forEach(header => {
        header.addEventListener('click', function() {
            // Toggle this customer section
            this.classList.toggle('collapsed');
            const projectList = this.nextElementSibling;
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
        
        // Expand the first customer section by default
        if (header === customerHeaders[0]) {
            header.click();
        }
    });
    
    // Highlight active project if applicable
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
});
