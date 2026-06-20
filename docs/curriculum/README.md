# Curriculum System

Curriculum content is defined as data so that learning progression can evolve without changing core logic.

## Structure

Curriculum files are expected to be YAML documents organised by language, proficiency level,
topic, learning objective, and scenario definition.

## Proficiency Levels

- Spanish, French, and German use CEFR-style levels A1 through C1.
- Japanese uses JLPT-style levels N5 through N1.

## MCP Integration

The Curriculum MCP reads curriculum files to select lessons, topics, objectives, and scenario prompts
that match the learner's language, locale, and proficiency.
