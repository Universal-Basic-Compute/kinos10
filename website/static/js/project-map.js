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
        
        fetch(`/api/projects/${projectPath}/files/map.json`)
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
        
        // Process files and folders
        function processNode(node, parent = 'root') {
            const nodeId = parent === 'root' ? node.path : `${parent}/${node.path}`;
            
            // Add node
            nodes.push({
                id: nodeId,
                name: node.path,
                type: node.type || 'file',
                description: node.description || `${node.path} ${node.type || 'file'}`
            });
            
            // Add link to parent
            links.push({
                source: parent,
                target: nodeId
            });
            
            // Process children if any
            if (node.children && node.children.length > 0) {
                node.children.forEach(child => {
                    processNode(child, nodeId);
                });
            }
        }
        
        // Process all top-level nodes
        if (data.nodes && Array.isArray(data.nodes)) {
            data.nodes.forEach(node => {
                processNode(node);
            });
        }
        
        // Add additional links if specified in the data
        if (data.links && Array.isArray(data.links)) {
            data.links.forEach(link => {
                links.push({
                    source: link.source,
                    target: link.target
                });
            });
        }
        
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
