# Natural Language Database Query System

A Python-based system that transforms natural language questions into database queries using Model Context Protocol (MCP) servers.

## Overview

This system enables Marcus's team to serve data requests by:
- Creating MCP servers for both primary and analytics databases
- Translating business questions in plain English to SQL queries
- Automatically discovering and navigating complex data relationships
- Presenting results in a user-friendly format for non-technical users
- Handling errors gracefully and providing meaningful feedback

## Architecture

- **MCP Servers**: Handle secure connections and queries to multiple databases
- **Natural Language Processing**: Converts English questions to SQL queries
- **Schema Discovery**: Automatically maps database structures and relationships
- **Query Execution**: Safe query execution with result formatting
- **Error Handling**: Comprehensive error management and validation

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from nldb_query import NLDBQuerySystem

# Initialize the system
query_system = NLDBQuerySystem()

# Ask a question in natural language
result = query_system.query("What are our top 10 customers by revenue this quarter?")
print(result.formatted_response)
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
black src/ tests/
flake8 src/ tests/
```

## Configuration

See `docs/configuration.md` for detailed configuration options.

## License

MIT License
