# Usage Guide

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd natural-language-db-query

# Install the package
pip install -e .
```

### 2. Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Edit the `.env` file with your settings:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here
PRIMARY_DB_URL=postgresql://user:pass@localhost:5432/database

# Optional
ANALYTICS_DB_URL=postgresql://user:pass@localhost:5432/analytics
```

### 3. Test the Installation

```bash
# Check configuration
nldb-query config

# View database schema
nldb-query schema

# Ask your first question
nldb-query query "What tables are available?"
```

## Command Line Usage

### Basic Queries

```bash
# Simple query
nldb-query query "How many customers do we have?"

# Query specific database
nldb-query query --database analytics "What's our total revenue this month?"

# Explain without executing
nldb-query query --explain "Show me top 10 customers by sales"
```

### Interactive Mode

```bash
# Start interactive session
nldb-query interactive

# In interactive mode:
Query> What are our top products by revenue?
Query> Show me customer growth over time
Query> help
Query> schema
Query> metrics
Query> exit
```

### Server Mode

```bash
# Start MCP server
nldb-query server --host localhost --port 8000

# Server with custom config
nldb-query server --config /path/to/config.json
```

## Python API Usage

### Basic Usage

```python
from nldb_query import NLDBQuerySystem

# Initialize the system
system = NLDBQuerySystem()

# Ask a question
response = await system.query("What are our top 10 customers by revenue?")

if response.success:
    result = response.result
    print(f"SQL: {result.sql_query}")
    print(f"Results: {len(result.results)} rows")
    print(result.formatted_response)
else:
    print(f"Error: {response.error.error_message}")

# Clean up
await system.close()
```

### Advanced Usage

```python
import asyncio
from nldb_query import NLDBQuerySystem

async def main():
    # Initialize with custom config
    system = NLDBQuerySystem(config_path="config.json")
    
    # Get database info
    db_info = await system.get_database_info()
    print(f"Available databases: {list(db_info['databases'].keys())}")
    
    # Query with context
    response = await system.query(
        question="Show me sales for Q4",
        database="analytics",
        context={"fiscal_year": 2024, "department": "sales"},
        execute=True,
        format_results=True
    )
    
    if response.success:
        # Access detailed results
        result = response.result
        print(f"Intent: {result.intent}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Tables used: {result.relevant_tables}")
        print(f"Execution time: {result.execution_time:.2f}s")
        
        # Formatted output
        print(result.formatted_response)
    
    # Explain a query without executing
    explanation = await system.explain_query(
        "What's the average order value by customer segment?"
    )
    print(f"Generated SQL: {explanation['sql_query']}")
    print(f"Explanation: {explanation['explanation']}")
    
    # Get system metrics
    metrics = system.get_metrics()
    print(f"Total queries: {metrics.total_queries}")
    print(f"Success rate: {metrics.successful_queries/metrics.total_queries:.1%}")
    
    await system.close()

# Run the async function
asyncio.run(main())
```

## Query Examples

### Data Retrieval

```bash
# Simple data queries
nldb-query query "Show me all customers"
nldb-query query "List products in electronics category"
nldb-query query "Get orders from last week"
```

### Aggregation Queries

```bash
# Counting
nldb-query query "How many orders were placed today?"
nldb-query query "Count customers by region"

# Summation
nldb-query query "What's our total revenue this month?"
nldb-query query "Sum of sales by product category"

# Averages
nldb-query query "What's the average order value?"
nldb-query query "Average customer age by segment"
```

### Time-Based Queries

```bash
# Recent data
nldb-query query "Show me sales from yesterday"
nldb-query query "Orders placed this week"
nldb-query query "Revenue for last quarter"

# Specific dates
nldb-query query "Sales on 2024-01-15"
nldb-query query "Orders between January 1 and March 31"
```

### Comparison Queries

```bash
# Top/bottom lists
nldb-query query "Top 5 customers by revenue"
nldb-query query "Bottom 10 products by sales"
nldb-query query "Highest grossing stores"

# Comparisons
nldb-query query "Compare sales this month vs last month"
nldb-query query "Which region has the most customers?"
```

### Complex Queries

```bash
# Multiple conditions
nldb-query query "Show customers in California with orders over $1000"
nldb-query query "Products launched this year with sales above average"

# Cross-table queries
nldb-query query "Customer names and their total order values"
nldb-query query "Sales rep performance by region"
```

## Best Practices

### Writing Effective Questions

**✅ Good Questions:**
- "What are our top 10 customers by total revenue?"
- "Show me monthly sales trends for the past year"
- "How many new customers did we acquire last quarter?"
- "Which products have the highest profit margins?"

**❌ Avoid:**
- "Show me data" (too vague)
- "All information about everything" (too broad)
- "Delete all customers" (dangerous operation)
- Very long, complex questions with multiple sub-questions

### Query Optimization

1. **Be Specific**: Include time ranges, limits, and specific criteria
2. **Use Business Terms**: The system understands "customers", "revenue", "orders"
3. **Start Simple**: Begin with basic queries and add complexity gradually
4. **Check Schema**: Use `nldb-query schema` to understand available data

### Error Handling

When queries fail, the system provides helpful suggestions:

```bash
nldb-query query "invalid question"
# Output:
# Error: Question doesn't appear to be a data query
# Suggestions:
# • Please ask a question about your data
# • Examples: 'What are our top customers?' or 'Show me sales this month'
```

## Integration Examples

### With Jupyter Notebooks

```python
# In a Jupyter cell
import asyncio
from nldb_query import NLDBQuerySystem

system = NLDBQuerySystem()

# Use this helper for Jupyter
def query(question, **kwargs):
    return asyncio.run(system.query(question, **kwargs))

# Now you can use it easily
response = query("What are our top products?")
if response.success:
    import pandas as pd
    df = pd.DataFrame(response.result.results)
    display(df)
```

### With Flask Web App

```python
from flask import Flask, request, jsonify
from nldb_query import NLDBQuerySystem
import asyncio

app = Flask(__name__)
system = NLDBQuerySystem()

@app.route('/query', methods=['POST'])
def query_endpoint():
    question = request.json.get('question')
    response = asyncio.run(system.query(question))
    
    if response.success:
        return jsonify({
            'success': True,
            'sql_query': response.result.sql_query,
            'results': response.result.results,
            'formatted_response': response.result.formatted_response
        })
    else:
        return jsonify({
            'success': False,
            'error': response.error.error_message,
            'suggestions': response.error.suggestions
        }), 400

if __name__ == '__main__':
    app.run(debug=True)
```

### With Slack Bot

```python
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from nldb_query import NLDBQuerySystem
import asyncio

system = NLDBQuerySystem()

def process_query(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        event = req.payload["event"]
        if event["type"] == "message" and "text" in event:
            question = event["text"]
            
            # Query the database
            response = asyncio.run(system.query(question))
            
            if response.success:
                result = response.result.formatted_response
            else:
                result = f"Error: {response.error.error_message}"
            
            # Send response
            client.web_client.chat_postMessage(
                channel=event["channel"],
                text=result
            )
    
    response = SocketModeResponse(envelope_id=req.envelope_id)
    client.send_socket_mode_response(response)

# Initialize Slack client
client = SocketModeClient(
    app_token="your_app_token",
    web_client=WebClient(token="your_bot_token")
)
client.socket_mode_request_listeners.append(process_query)
client.connect()
```

## Troubleshooting

### Common Issues

1. **"No database connections configured"**
   - Check your `.env` file has valid database URLs
   - Verify database server is running and accessible

2. **"OpenAI API key not found"**
   - Set `OPENAI_API_KEY` in your environment
   - Verify the API key is valid and has sufficient credits

3. **"No relevant tables found"**
   - Check if your question uses business terms that match your data
   - Use `nldb-query schema` to see available tables
   - Try rephrasing your question

4. **"Query timeout"**
   - Your query might be too complex or data too large
   - Add more specific filters to reduce data volume
   - Increase `MAX_QUERY_TIMEOUT` in configuration

### Getting Help

```bash
# Check system status
nldb-query config

# View available data
nldb-query schema

# Test with simple query
nldb-query query "Show me table names"

# Use interactive mode for experimentation
nldb-query interactive
```
