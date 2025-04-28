# KinOS Memory System

This directory contains the hierarchical memory system for KinOS, designed to store, organize, and retrieve information effectively across different types of memory.

## Memory Structure

The memory system is organized into four main categories:

### 1. Episodic Memory
Located in `/memories/episodic/`, this stores time-based conversation memories:
- **Recent**: Last 30 days of interactions in `/memories/episodic/recent/`
- **Archived**: Older interactions in `/memories/episodic/archived/`, organized by month/year

### 2. Semantic Memory
Located in `/memories/semantic/`, this stores conceptual knowledge organized by topic:
- **User**: User-specific knowledge in `/memories/semantic/user/` (preferences, history)
- **Domain**: Domain-specific knowledge in `/memories/semantic/domain/` (organized by subject)

### 3. Procedural Memory
Located in `/memories/procedural/`, this stores how-to knowledge and processes:
- **Workflows**: Common task sequences in `/memories/procedural/workflows/`
- **Methods**: Specific techniques in `/memories/procedural/methods/`

### 4. Meta Memory
Located in `/memories/meta/`, this stores memory about the memory system itself:
- **Indexes**: Cross-references and retrieval helpers in `/memories/meta/indexes/`
- **Statistics**: Usage patterns and effectiveness metrics in `/memories/meta/statistics/`

## Memory Lifecycle

Each memory file follows a lifecycle:

1. **Creation**: New memories are created when significant information is encountered
2. **Updating**: Existing memories are updated with new relevant information
3. **Consolidation**: Related memories are periodically merged and synthesized
4. **Archiving**: Less-relevant memories are moved to long-term storage
5. **Pruning**: Outdated or superseded information is removed

## Usage Guidelines

- Store information in the most appropriate memory category
- Use consistent naming conventions for memory files
- Include creation and last modified dates in file headers
- Reference related memory files when appropriate
- Follow the memory lifecycle management guidelines in `memory_lifecycle.txt`
