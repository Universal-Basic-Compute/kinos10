# User Semantic Memories

This directory contains semantic memories related to user-specific knowledge, including preferences, characteristics, history, and patterns of interaction.

## Purpose

User semantic memories serve to:
- Store knowledge about user preferences and characteristics
- Enable personalization of responses
- Maintain consistent understanding of the user across interactions
- Support adaptation to user needs and communication style

## Organization

Files in this directory should be organized by:
- Category of user knowledge (preferences, expertise, history)
- Specific aspect within each category
- Level of detail (general vs. specific)

Example filenames:
- `communication_preferences.txt`
- `expertise_level.txt`
- `interaction_history.txt`
- `technical_interests.txt`

## Content Guidelines

Each user semantic memory file should include:
- Clear categorization of the knowledge
- Specific details and examples
- Source references (which episodic memories contributed)
- Confidence level for inferred preferences
- Last updated timestamp
- Potential conflicts or changes over time

## Lifecycle

Files in this directory should:
- Be created when significant user preferences are identified
- Be updated when new information is learned
- Be consolidated when multiple related preferences are discovered
- Be maintained long-term as core user knowledge

## Usage

When retrieving context, user semantic memories should be:
- Prioritized for personalization of responses
- Selected based on relevance to current interaction
- Used to adapt communication style and content
- Referenced when discussing user preferences or history
