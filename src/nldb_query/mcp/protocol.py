"""MCP protocol message definitions and types."""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class MCPMessageType(str, Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPMethod(str, Enum):
    """MCP method names."""
    INITIALIZE = "initialize"
    QUERY = "query" 
    SCHEMA_DISCOVERY = "schema/discovery"
    EXPLAIN_QUERY = "query/explain"
    VALIDATE_QUERY = "query/validate"
    EXECUTE_QUERY = "query/execute"
    GET_TABLES = "schema/tables"
    GET_RELATIONSHIPS = "schema/relationships"


class MCPMessage(BaseModel):
    """Base MCP message."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(default=None, description="Message ID")
    method: Optional[str] = Field(default=None, description="Method name")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Parameters")


class MCPRequest(MCPMessage):
    """MCP request message."""
    method: str = Field(description="Method name")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Request parameters")


class MCPResponse(MCPMessage):
    """MCP response message."""
    result: Optional[Any] = Field(default=None, description="Response result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")


class MCPError(BaseModel):
    """MCP error information."""
    code: int = Field(description="Error code")
    message: str = Field(description="Error message")
    data: Optional[Any] = Field(default=None, description="Additional error data")


class DatabaseConnectionConfig(BaseModel):
    """Database connection configuration."""
    name: str = Field(description="Database connection name")
    url: str = Field(description="Database connection URL")
    driver: str = Field(description="Database driver (postgresql, mysql, sqlite)")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max pool overflow")
    timeout: int = Field(default=30, description="Query timeout in seconds")


class QueryRequest(BaseModel):
    """Natural language query request."""
    question: str = Field(description="Natural language question")
    database: Optional[str] = Field(default=None, description="Target database name")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    format_results: bool = Field(default=True, description="Format results for end users")


class QueryResponse(BaseModel):
    """Query execution response."""
    sql_query: str = Field(description="Generated SQL query")
    results: List[Dict[str, Any]] = Field(description="Query results")
    explanation: str = Field(description="Human-readable explanation")
    metadata: Dict[str, Any] = Field(description="Query execution metadata")
    formatted_response: str = Field(description="Formatted response for end users")


class SchemaInfo(BaseModel):
    """Database schema information."""
    database_name: str = Field(description="Database name")
    tables: List[Dict[str, Any]] = Field(description="Table information")
    relationships: List[Dict[str, Any]] = Field(description="Table relationships")
    indexes: List[Dict[str, Any]] = Field(description="Index information")


class TableInfo(BaseModel):
    """Database table information."""
    name: str = Field(description="Table name")
    schema: str = Field(description="Schema name")
    columns: List[Dict[str, str]] = Field(description="Column information")
    primary_keys: List[str] = Field(description="Primary key columns")
    foreign_keys: List[Dict[str, str]] = Field(description="Foreign key relationships")
