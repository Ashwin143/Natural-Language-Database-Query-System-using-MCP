# Configuration Guide

## Overview

The Natural Language Database Query System uses a flexible configuration system that supports environment variables, configuration files, and default values.

## Environment Variables

Create a `.env` file in your project root (copy from `.env.example`):

### Database Configuration

```bash
# Primary Database (required)
PRIMARY_DB_URL=postgresql://username:password@localhost:5432/primary_db
PRIMARY_DB_POOL_SIZE=10
PRIMARY_DB_TIMEOUT=30

# Analytics Database (optional)
ANALYTICS_DB_URL=postgresql://username:password@localhost:5432/analytics_db
ANALYTICS_DB_POOL_SIZE=10
ANALYTICS_DB_TIMEOUT=30
```

### OpenAI Configuration

```bash
# OpenAI API Configuration (required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.1
```

### Server Configuration

```bash
# MCP Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=INFO

# Security
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1

# Query Limits
MAX_QUERY_TIMEOUT=30
MAX_RESULT_ROWS=1000
```

## Configuration File

Alternatively, create a JSON configuration file:

```json
{
  "databases": {
    "primary": {
      "url": "postgresql://username:password@localhost:5432/primary_db",
      "driver": "postgresql",
      "pool_size": 10,
      "timeout": 30
    },
    "analytics": {
      "url": "postgresql://username:password@localhost:5432/analytics_db", 
      "driver": "postgresql",
      "pool_size": 10,
      "timeout": 30
    }
  },
  "openai": {
    "api_key": "your_openai_api_key_here",
    "model": "gpt-4",
    "temperature": 0.1
  },
  "mcp": {
    "host": "localhost",
    "port": 8000
  },
  "query": {
    "timeout": 30,
    "max_results": 1000
  }
}
```

Use the configuration file with:
```bash
nldb-query --config /path/to/config.json query "What are our top customers?"
```

## Database Support

### PostgreSQL
```bash
PRIMARY_DB_URL=postgresql://user:pass@host:port/dbname
# or with async driver
PRIMARY_DB_URL=postgresql+asyncpg://user:pass@host:port/dbname
```

### MySQL
```bash
PRIMARY_DB_URL=mysql://user:pass@host:port/dbname
# or with async driver
PRIMARY_DB_URL=mysql+aiomysql://user:pass@host:port/dbname
```

### SQLite
```bash
PRIMARY_DB_URL=sqlite:///path/to/database.db
# or with async driver
PRIMARY_DB_URL=sqlite+aiosqlite:///path/to/database.db
```

## OpenAI Models

Supported models:
- `gpt-4` (recommended for best results)
- `gpt-3.5-turbo` (faster, lower cost)
- `gpt-4-turbo` (latest version)

Temperature settings:
- `0.0`: Deterministic output
- `0.1`: Low creativity (recommended for SQL)
- `0.5`: Balanced
- `1.0`: High creativity

## Security Settings

### Query Safety
The system automatically prevents dangerous operations:
- `DROP TABLE`, `DELETE`, `UPDATE`, `INSERT` are blocked
- Only `SELECT` statements are allowed
- SQL injection patterns are detected and blocked

### Connection Security
- Use connection pooling to limit database connections
- Set appropriate timeouts to prevent hanging queries
- Use read-only database users when possible

## Performance Tuning

### Database Connection Pools
```bash
PRIMARY_DB_POOL_SIZE=20        # Max connections in pool
PRIMARY_DB_MAX_OVERFLOW=30     # Additional connections allowed
PRIMARY_DB_TIMEOUT=60          # Query timeout in seconds
```

### Query Limits
```bash
MAX_RESULT_ROWS=5000          # Maximum rows returned
MAX_QUERY_TIMEOUT=120         # Query timeout in seconds
```

### Schema Caching
Schema information is cached automatically to improve performance. The cache is refreshed:
- On system startup
- When schema discovery is explicitly requested
- After connection errors (automatic retry)

## Logging Configuration

```bash
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR
```

Log levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General information about system operation
- `WARNING`: Warning messages about potential issues
- `ERROR`: Error messages only

## Validation

Check your configuration:
```bash
nldb-query config
```

This will show:
- Database connection status
- OpenAI API configuration
- MCP server settings
- Configuration validation results

## Environment-Specific Configuration

### Development
```bash
# .env.development
OPENAI_MODEL=gpt-3.5-turbo
PRIMARY_DB_POOL_SIZE=5
LOG_LEVEL=DEBUG
```

### Production
```bash
# .env.production
OPENAI_MODEL=gpt-4
PRIMARY_DB_POOL_SIZE=20
LOG_LEVEL=INFO
MAX_QUERY_TIMEOUT=60
```

### Testing
```bash
# .env.test
PRIMARY_DB_URL=sqlite:///:memory:
LOG_LEVEL=ERROR
```

## Advanced Configuration

### Custom Business Terms
You can extend the business term mappings by creating a custom configuration:

```json
{
  "nlp": {
    "business_mappings": {
      "revenue": ["sales", "income", "earnings", "proceeds"],
      "clients": ["customers", "accounts", "users", "members"]
    }
  }
}
```

### Custom Intent Classification
Configure additional intents:

```json
{
  "nlp": {
    "custom_intents": {
      "forecasting": "Predict future trends and values",
      "comparison": "Compare different time periods or segments"
    }
  }
}
```

## Configuration Precedence

Configuration is loaded in this order (later values override earlier ones):

1. **Default values** (built into the system)
2. **Configuration file** (if specified with `--config`)
3. **Environment variables** (highest priority)

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check connection string format
PRIMARY_DB_URL=postgresql://user:password@host:port/database

# Verify database is accessible
ping your-database-host
telnet your-database-host 5432
```

**OpenAI API Errors**
```bash
# Verify API key is valid
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check API key permissions and billing
```

**Configuration Validation**
```bash
# Test configuration
nldb-query config

# Test database connections
nldb-query schema
```
