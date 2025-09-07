# System Architecture

## Overview

The Natural Language Database Query System is designed to transform how Marcus's team serves data requests by providing a sophisticated interface that converts business questions in plain English into SQL queries across multiple databases.

## Core Components

### 1. Model Context Protocol (MCP) Server

The MCP server acts as the central hub for database operations:

- **Purpose**: Provides secure, standardized interface for database connections
- **Location**: `src/nldb_query/mcp/`
- **Key Features**:
  - Handles connections to both primary and analytics databases
  - Implements protocol-based communication
  - Manages query execution and schema discovery
  - Provides cross-database relationship mapping

### 2. Natural Language Processing Engine

Converts natural language into SQL queries:

- **Location**: `src/nldb_query/nlp/`
- **Components**:
  - **Query Analyzer** (`analyzer.py`): Extracts entities, keywords, and business concepts
  - **Intent Classifier** (`intent.py`): Determines query intent (aggregation, filtering, etc.)
  - **SQL Translator** (`translator.py`): Converts analyzed queries to SQL
  - **NL Processor** (`processor.py`): Orchestrates the entire pipeline

### 3. Core System

Integrates all components and manages the query lifecycle:

- **Location**: `src/nldb_query/core.py`
- **Responsibilities**:
  - System initialization and configuration
  - Query processing orchestration
  - Result formatting and error handling
  - Metrics collection and performance monitoring

### 4. Database Schema Discovery

Automatically maps database structures:

- **Features**:
  - Discovers tables, columns, and data types
  - Maps relationships between tables
  - Identifies indexes and constraints
  - Caches schema information for performance

### 5. Query Validation and Safety

Ensures secure query execution:

- **Location**: `src/nldb_query/validators.py`
- **Safety Measures**:
  - Validates input questions for malicious content
  - Prevents dangerous SQL operations (DROP, DELETE, etc.)
  - Implements query timeouts and result limits
  - Provides helpful error messages and suggestions

## Data Flow

```
Natural Language Question
         ↓
    Input Validation
         ↓
   Question Analysis
    (keywords, entities, intent)
         ↓
   Schema Matching
    (find relevant tables)
         ↓
    SQL Generation
    (using OpenAI GPT-4)
         ↓
    Query Validation
         ↓
   Query Execution
    (via MCP server)
         ↓
   Result Formatting
    (user-friendly output)
```

## Security Architecture

### Query Safety
- Only SELECT statements are permitted
- Dangerous operations are blocked at multiple levels
- Input validation prevents SQL injection attempts
- Query timeouts prevent resource exhaustion

### Database Access
- Connection pooling for efficient resource usage
- Separate connections for different database roles
- Configurable access limits and timeouts

### API Security
- Environment variable configuration for sensitive data
- Masked credentials in logs and output
- Optional authentication and authorization hooks

## Scalability Considerations

### Performance
- Schema information caching
- Connection pooling for database access
- Async/await patterns for non-blocking operations
- Configurable query limits and timeouts

### Extensibility
- Plugin architecture for new database types
- Modular NLP pipeline for custom processing
- Configurable intent classification
- Support for custom business term mappings

## Configuration Management

The system uses a hierarchical configuration approach:

1. **Environment Variables** (highest priority)
2. **Configuration Files** (JSON format)
3. **Default Values** (fallback)

Key configuration areas:
- Database connections
- OpenAI API settings
- MCP server configuration
- Query limits and timeouts
- Security settings

## Monitoring and Metrics

Built-in metrics collection:
- Query success/failure rates
- Average processing times
- Confidence scores
- Intent distribution
- Error categorization

## Deployment Options

### Standalone Server
Run as an MCP server for integration with external systems

### CLI Interface
Interactive command-line tool for direct usage

### Library Integration
Import as a Python package for embedding in applications
