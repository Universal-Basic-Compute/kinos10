document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a project detail page
    const projectMapContainer = document.getElementById('project-map-container');
    if (!projectMapContainer) return;
    
    // Get project info from data attributes
    const customer = projectMapContainer.dataset.customer;
    const project = projectMapContainer.dataset.project;
    
    if (!customer || !project) {
        showNoMapData("No project selected");
        return;
    }
    
    // Fetch project map data
    fetchProjectMap(customer, project);
    
    // Function to fetch project map data
    function fetchProjectMap(customer, project) {
        const projectPath = `${customer}/${project}`;
        
        fetch(`/api/proxy/projects/${projectPath}/files/map.json`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && Object.keys(data).length > 0) {
                    createForceDirectedGraph(data);
                } else {
                    showNoMapData("No map data available for this project");
                }
            })
            .catch(error => {
                console.error('Error fetching project map:', error);
                showNoMapData("Error loading project map");
            });
    }
    
    // Function to show a message when no map data is available
    function showNoMapData(message) {
        const projectMap = document.getElementById('project-map');
        if (!projectMap) return;
        
        projectMap.innerHTML = `
            <div class="no-map-data">
                <i class="fas fa-map-marked-alt"></i>
                <h3>${message}</h3>
                <p>The project map could not be loaded. This might be because the project doesn't have a map.json file or the file is not properly formatted.</p>
            </div>
        `;
    }
    
    // Function to create the force-directed graph
    function createForceDirectedGraph(data) {
        // If data is empty or doesn't have the expected structure, use a fallback
        if (!data || Object.keys(data).length === 0) {
            showNoMapData("Invalid map data format");
            return;
        }
        
        // Clear any existing content
        const projectMap = document.getElementById('project-map');
        projectMap.innerHTML = '';
        
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        projectMapContainer.appendChild(tooltip);
        
        // Set up the SVG container
        const width = projectMap.clientWidth;
        const height = projectMap.clientHeight;
        
        const svg = d3.select('#project-map')
            .append('svg')
            .attr('width', width)
            .attr('height', height);
        
        // Create a group for the graph
        const g = svg.append('g');
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        
        svg.call(zoom);
        
        // Process the data to create nodes and links
        const nodes = [];
        const links = [];
        
        // Add root node
        nodes.push({
            id: 'root',
            name: project,
            type: 'project',
            description: `Root of ${project} project`
        });
        
        // Helper function to process files from the map.json structure
        function processMapData(mapData) {
            // Process files section if it exists
            if (mapData.files && Array.isArray(mapData.files)) {
                mapData.files.forEach(file => {
                    nodes.push({
                        id: file.path,
                        name: file.path.split('/').pop(), // Get just the filename
                        type: 'file',
                        description: file.description || `File: ${file.path}`
                    });
                    
                    // Link to root or parent folder
                    const parentPath = file.path.split('/').slice(0, -1).join('/');
                    const parentId = parentPath ? parentPath : 'root';
                    
                    links.push({
                        source: parentId,
                        target: file.path
                    });
                });
            }
            
            // Process folders section if it exists
            if (mapData.folders && Array.isArray(mapData.folders)) {
                mapData.folders.forEach(folder => {
                    nodes.push({
                        id: folder.path,
                        name: folder.path.split('/').pop() || folder.path, // Get just the folder name
                        type: 'folder',
                        description: folder.description || `Folder: ${folder.path}`
                    });
                    
                    // Link to root or parent folder
                    const parentPath = folder.path.split('/').slice(0, -1).join('/');
                    const parentId = parentPath ? parentPath : 'root';
                    
                    links.push({
                        source: parentId,
                        target: folder.path
                    });
                });
            }
            
            // Process links section if it exists
            if (mapData.links && Array.isArray(mapData.links)) {
                mapData.links.forEach(link => {
                    links.push({
                        source: link.source,
                        target: link.target,
                        description: link.description || `Link from ${link.source} to ${link.target}`
                    });
                });
            }
            
            // If we have nodes array directly in the data
            if (mapData.nodes && Array.isArray(mapData.nodes)) {
                // Process each node
                mapData.nodes.forEach(node => {
                    // Add the node
                    nodes.push({
                        id: node.path,
                        name: node.path.split('/').pop() || node.path,
                        type: node.type || 'file',
                        description: node.description || `${node.path}`
                    });
                    
                    // Link to root by default
                    links.push({
                        source: 'root',
                        target: node.path
                    });
                    
                    // Process children recursively
                    if (node.children && Array.isArray(node.children)) {
                        processChildren(node.children, node.path);
                    }
                });
            }
        }
        
        // Helper function to process child nodes
        function processChildren(children, parentId) {
            children.forEach(child => {
                const childId = `${parentId}/${child.path}`;
                
                // Add the child node
                nodes.push({
                    id: childId,
                    name: child.path,
                    type: child.type || 'file',
                    description: child.description || `${child.path}`
                });
                
                // Link to parent
                links.push({
                    source: parentId,
                    target: childId
                });
                
                // Process grandchildren recursively
                if (child.children && Array.isArray(child.children)) {
                    processChildren(child.children, childId);
                }
            });
        }
        
        // Process the map data
        processMapData(data);
        
        // If no nodes were created (except root), show error
        if (nodes.length <= 1) {
            showNoMapData("No valid nodes found in map data");
            return;
        }
        
        console.log("Processed nodes:", nodes);
        console.log("Processed links:", links);
        
        // Create the force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));
        
        // Create the links
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('class', 'link');
        
        // Create the nodes
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('.node')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', d => `node ${d.type}`)
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        // Add circles to nodes
        node.append('circle')
            .attr('r', d => d.type === 'project' ? 15 : d.type === 'folder' ? 10 : 8);
        
        // Add text labels to nodes
        node.append('text')
            .attr('dy', 25)
            .text(d => d.name);
        
        // Add tooltip behavior
        node.on('mouseover', function(event, d) {
            tooltip.innerHTML = `
                <h3>${d.name}</h3>
                <p>${d.description || 'No description available'}</p>
            `;
            tooltip.style.opacity = 1;
            tooltip.style.left = `${event.pageX + 10}px`;
            tooltip.style.top = `${event.pageY + 10}px`;
        })
        .on('mousemove', function(event) {
            tooltip.style.left = `${event.pageX + 10}px`;
            tooltip.style.top = `${event.pageY + 10}px`;
        })
        .on('mouseout', function() {
            tooltip.style.opacity = 0;
        });
        
        // Update positions on each tick of the simulation
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
        
        // Add control buttons
        const mapControls = document.createElement('div');
        mapControls.className = 'map-controls';
        mapControls.innerHTML = `
            <button class="map-control-button" id="zoom-in">
                <i class="fas fa-plus"></i>
            </button>
            <button class="map-control-button" id="zoom-out">
                <i class="fas fa-minus"></i>
            </button>
            <button class="map-control-button" id="reset-zoom">
                <i class="fas fa-home"></i>
            </button>
        `;
        projectMapContainer.appendChild(mapControls);
        
        // Add event listeners to control buttons
        document.getElementById('zoom-in').addEventListener('click', () => {
            svg.transition().duration(300).call(zoom.scaleBy, 1.3);
        });
        
        document.getElementById('zoom-out').addEventListener('click', () => {
            svg.transition().duration(300).call(zoom.scaleBy, 0.7);
        });
        
        document.getElementById('reset-zoom').addEventListener('click', () => {
            svg.transition().duration(300).call(
                zoom.transform,
                d3.zoomIdentity.translate(width / 2, height / 2).scale(1)
            );
        });
        
        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    }
});
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a project detail page
    const projectMapContainer = document.getElementById('project-map-container');
    if (!projectMapContainer) return;
    
    // Get project info from data attributes
    const customer = projectMapContainer.dataset.customer;
    const project = projectMapContainer.dataset.project;
    
    if (!customer || !project) {
        showNoMapData("No project selected");
        return;
    }
    
    // Fetch project map data
    fetchProjectMap(customer, project);
    
    // Function to fetch project map data
    function fetchProjectMap(customer, project) {
        const projectPath = `${customer}/${project}`;
        
        fetch(`/api/proxy/projects/${projectPath}/files/map.json`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && Object.keys(data).length > 0) {
                    createForceDirectedGraph(data);
                } else {
                    showNoMapData("No map data available for this project");
                }
            })
            .catch(error => {
                console.error('Error fetching project map:', error);
                showNoMapData("Error loading project map");
            });
    }
    
    // Function to show a message when no map data is available
    function showNoMapData(message) {
        const projectMap = document.getElementById('project-map');
        if (!projectMap) return;
        
        projectMap.innerHTML = `
            <div class="no-map-data">
                <i class="fas fa-map-marked-alt"></i>
                <h3>${message}</h3>
                <p>The project map could not be loaded. This might be because the project doesn't have a map.json file or the file is not properly formatted.</p>
            </div>
        `;
    }
    
    // Function to create the force-directed graph
    function createForceDirectedGraph(data) {
        // If data is empty or doesn't have the expected structure, use a fallback
        if (!data || Object.keys(data).length === 0) {
            showNoMapData("Invalid map data format");
            return;
        }
        
        // Clear any existing content
        const projectMap = document.getElementById('project-map');
        projectMap.innerHTML = '';
        
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        projectMapContainer.appendChild(tooltip);
        
        // Set up the SVG container
        const width = projectMap.clientWidth;
        const height = projectMap.clientHeight;
        
        const svg = d3.select('#project-map')
            .append('svg')
            .attr('width', width)
            .attr('height', height);
        
        // Create a group for the graph
        const g = svg.append('g');
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        
        svg.call(zoom);
        
        // Process the data to create nodes and links
        const nodes = [];
        const links = [];
        
        // Add root node
        nodes.push({
            id: 'root',
            name: project,
            type: 'project',
            description: `Root of ${project} project`
        });
        
        // Helper function to process files from the map.json structure
        function processMapData(mapData) {
            // Process files section if it exists
            if (mapData.files && Array.isArray(mapData.files)) {
                mapData.files.forEach(file => {
                    nodes.push({
                        id: file.path,
                        name: file.path.split('/').pop(), // Get just the filename
                        type: 'file',
                        description: file.description || `File: ${file.path}`
                    });
                    
                    // Link to root or parent folder
                    const parentPath = file.path.split('/').slice(0, -1).join('/');
                    const parentId = parentPath ? parentPath : 'root';
                    
                    links.push({
                        source: parentId,
                        target: file.path
                    });
                });
            }
            
            // Process folders section if it exists
            if (mapData.folders && Array.isArray(mapData.folders)) {
                mapData.folders.forEach(folder => {
                    nodes.push({
                        id: folder.path,
                        name: folder.path.split('/').pop() || folder.path, // Get just the folder name
                        type: 'folder',
                        description: folder.description || `Folder: ${folder.path}`
                    });
                    
                    // Link to root or parent folder
                    const parentPath = folder.path.split('/').slice(0, -1).join('/');
                    const parentId = parentPath ? parentPath : 'root';
                    
                    links.push({
                        source: parentId,
                        target: folder.path
                    });
                });
            }
            
            // Process links section if it exists
            if (mapData.links && Array.isArray(mapData.links)) {
                mapData.links.forEach(link => {
                    links.push({
                        source: link.source,
                        target: link.target,
                        description: link.description || `Link from ${link.source} to ${link.target}`
                    });
                });
            }
            
            // If we have nodes array directly in the data
            if (mapData.nodes && Array.isArray(mapData.nodes)) {
                // Process each node
                mapData.nodes.forEach(node => {
                    // Add the node
                    nodes.push({
                        id: node.id || node.path,
                        name: node.name || (node.path ? node.path.split('/').pop() : node.id),
                        type: node.type || 'file',
                        description: node.description || `${node.path || node.id}`
                    });
                    
                    // Link to root by default if no parent specified
                    if (!node.parent) {
                        links.push({
                            source: 'root',
                            target: node.id || node.path
                        });
                    }
                    
                    // Process children recursively
                    if (node.children && Array.isArray(node.children)) {
                        processChildren(node.children, node.id || node.path);
                    }
                });
            }
            
            // Process connections/edges if they exist
            if (mapData.connections && Array.isArray(mapData.connections)) {
                mapData.connections.forEach(conn => {
                    links.push({
                        source: conn.source,
                        target: conn.target,
                        description: conn.description || `Connection from ${conn.source} to ${conn.target}`
                    });
                });
            }
        }
        
        // Helper function to process child nodes
        function processChildren(children, parentId) {
            children.forEach(child => {
                const childId = child.id || (child.path ? `${parentId}/${child.path}` : `${parentId}_child_${Math.random().toString(36).substr(2, 9)}`);
                
                // Add the child node
                nodes.push({
                    id: childId,
                    name: child.name || (child.path || '').split('/').pop() || childId,
                    type: child.type || 'file',
                    description: child.description || `${child.path || childId}`
                });
                
                // Link to parent
                links.push({
                    source: parentId,
                    target: childId
                });
                
                // Process grandchildren recursively
                if (child.children && Array.isArray(child.children)) {
                    processChildren(child.children, childId);
                }
            });
        }
        
        // Process the map data
        processMapData(data);
        
        // If no nodes were created (except root), show error
        if (nodes.length <= 1) {
            showNoMapData("No valid nodes found in map data");
            return;
        }
        
        console.log("Processed nodes:", nodes);
        console.log("Processed links:", links);
        
        // Create the force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));
        
        // Create the links
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('class', 'link');
        
        // Create the nodes
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('.node')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', d => `node ${d.type}`)
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        // Add circles to nodes
        node.append('circle')
            .attr('r', d => d.type === 'project' ? 15 : d.type === 'folder' ? 10 : 8);
        
        // Add text labels to nodes
        node.append('text')
            .attr('dy', 25)
            .text(d => d.name);
        
        // Add tooltip behavior
        node.on('mouseover', function(event, d) {
            tooltip.innerHTML = `
                <h3>${d.name}</h3>
                <p>${d.description || 'No description available'}</p>
            `;
            tooltip.style.opacity = 1;
            tooltip.style.left = `${event.pageX + 10}px`;
            tooltip.style.top = `${event.pageY + 10}px`;
        })
        .on('mousemove', function(event) {
            tooltip.style.left = `${event.pageX + 10}px`;
            tooltip.style.top = `${event.pageY + 10}px`;
        })
        .on('mouseout', function() {
            tooltip.style.opacity = 0;
        });
        
        // Update positions on each tick of the simulation
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
        
        // Add control buttons
        const mapControls = document.createElement('div');
        mapControls.className = 'map-controls';
        mapControls.innerHTML = `
            <button class="map-control-button" id="zoom-in">
                <i class="fas fa-plus"></i>
            </button>
            <button class="map-control-button" id="zoom-out">
                <i class="fas fa-minus"></i>
            </button>
            <button class="map-control-button" id="reset-zoom">
                <i class="fas fa-home"></i>
            </button>
        `;
        projectMapContainer.appendChild(mapControls);
        
        // Add event listeners to control buttons
        document.getElementById('zoom-in').addEventListener('click', () => {
            svg.transition().duration(300).call(zoom.scaleBy, 1.3);
        });
        
        document.getElementById('zoom-out').addEventListener('click', () => {
            svg.transition().duration(300).call(zoom.scaleBy, 0.7);
        });
        
        document.getElementById('reset-zoom').addEventListener('click', () => {
            svg.transition().duration(300).call(
                zoom.transform,
                d3.zoomIdentity.translate(width / 2, height / 2).scale(1)
            );
        });
        
        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    }
});
