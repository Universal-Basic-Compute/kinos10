# Memory Indexes

This directory contains index files that help organize and retrieve information from the memory system.

## Purpose

Memory indexes serve to:
- Provide efficient lookup of related memory files
- Map topics to relevant memory locations
- Track relationships between different memories
- Optimize context selection and retrieval
- Support memory consolidation processes

## Organization

Files in this directory should be organized by:
- Type of index (topic map, recency index, relationship map)
- Scope of coverage (global, domain-specific)
- Level of detail

Example filenames:
- `topic_map.json`
- `user_preferences_index.json`
- `file_relationships.json`
- `domain_knowledge_index.json`

## Content Guidelines

Each index file should include:
- Clear structure for lookup and retrieval
- Metadata about indexed content
- Relevance or importance scores when applicable
- Last updated timestamp
- Coverage information (what's included in the index)

## Lifecycle

Files in this directory should:
- Be created when a new category of information needs indexing
- Be updated regularly as new memories are created
- Be regenerated periodically to optimize organization
- Be maintained as core infrastructure for memory retrieval

## Usage

When retrieving context, memory indexes should be:
- Used to identify the most relevant files for a given topic
- Referenced to find related information across memory types
- Consulted to determine importance and recency of memories
- Leveraged to optimize token usage in context selection
