"""Data models for the natural language database query system."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Result of a successful natural language query."""
    
    sql_query: str = Field(description="Generated SQL query")
    explanation: str = Field(description="Human-readable explanation of the query")
    confidence: float = Field(description="Confidence score (0-1) for the query")
    intent: str = Field(description="Classified intent of the query")
    relevant_tables: List[str] = Field(default=[], description="Tables used in the query")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Query execution results (populated after execution)
    results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Query execution results")
    row_count: Optional[int] = Field(default=None, description="Number of rows returned")
    execution_time: Optional[float] = Field(default=None, description="Query execution time in seconds")
    formatted_response: Optional[str] = Field(default=None, description="Formatted response for end users")


class QueryError(BaseModel):
    """Error that occurred during query processing."""
    
    error_message: str = Field(description="Error message")
    error_type: str = Field(description="Type of error")
    original_question: str = Field(description="Original natural language question")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Additional error context
    sql_query: Optional[str] = Field(default=None, description="SQL query that caused the error")
    suggestions: List[str] = Field(default=[], description="Suggestions to fix the error")
    metadata: Dict[str, Any] = Field(default={}, description="Additional error metadata")


class DatabaseSchema(BaseModel):
    """Database schema information."""
    
    database_name: str = Field(description="Name of the database")
    tables: List[Dict[str, Any]] = Field(description="List of tables with metadata")
    relationships: List[Dict[str, Any]] = Field(description="Table relationships")
    indexes: List[Dict[str, Any]] = Field(description="Database indexes")
    last_updated: datetime = Field(default_factory=datetime.now)


class QueryAnalysis(BaseModel):
    """Analysis results for a natural language question."""
    
    original_question: str = Field(description="Original question")
    keywords: List[str] = Field(description="Extracted keywords")
    entities: List[str] = Field(description="Named entities")
    intent: str = Field(description="Classified intent")
    complexity: str = Field(description="Query complexity level")
    business_concepts: Dict[str, List[str]] = Field(description="Business concepts identified")
    time_references: Dict[str, Any] = Field(description="Temporal references")
    aggregations: List[Dict[str, str]] = Field(description="Required aggregations")
    comparisons: List[Dict[str, str]] = Field(description="Comparison operators")
    confidence: float = Field(description="Analysis confidence score")


class UserFeedback(BaseModel):
    """User feedback on query results."""
    
    query_id: str = Field(description="ID of the original query")
    rating: int = Field(description="Rating 1-5", ge=1, le=5)
    feedback_text: Optional[str] = Field(default=None, description="Additional feedback")
    is_correct: bool = Field(description="Whether the result was correct")
    suggested_improvement: Optional[str] = Field(default=None, description="Suggested improvement")
    timestamp: datetime = Field(default_factory=datetime.now)


class QuerySession(BaseModel):
    """Session for tracking multiple related queries."""
    
    session_id: str = Field(description="Unique session ID")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    queries: List[Union[QueryResult, QueryError]] = Field(default=[], description="Queries in this session")
    context: Dict[str, Any] = Field(default={}, description="Session context")
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)


class SystemMetrics(BaseModel):
    """System performance and usage metrics."""
    
    total_queries: int = Field(default=0, description="Total queries processed")
    successful_queries: int = Field(default=0, description="Successful queries")
    failed_queries: int = Field(default=0, description="Failed queries")
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    average_execution_time: float = Field(default=0.0, description="Average execution time")
    most_common_intents: Dict[str, int] = Field(default={}, description="Intent frequency")
    error_types: Dict[str, int] = Field(default={}, description="Error type frequency")
    last_updated: datetime = Field(default_factory=datetime.now)


# Response models for API endpoints
class QueryRequest(BaseModel):
    """Request model for natural language queries."""
    
    question: str = Field(description="Natural language question")
    database: Optional[str] = Field(default=None, description="Target database name")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    execute: bool = Field(default=True, description="Whether to execute the query")
    format_results: bool = Field(default=True, description="Whether to format results")
    session_id: Optional[str] = Field(default=None, description="Session ID for context")


class QueryResponse(BaseModel):
    """Response model for natural language queries."""
    
    success: bool = Field(description="Whether the query was successful")
    result: Optional[QueryResult] = Field(default=None, description="Query result if successful")
    error: Optional[QueryError] = Field(default=None, description="Error if unsuccessful")
    query_id: str = Field(description="Unique query identifier")
    processing_time: float = Field(description="Total processing time")


class SchemaDiscoveryResponse(BaseModel):
    """Response model for schema discovery."""
    
    schemas: Dict[str, DatabaseSchema] = Field(description="Database schemas")
    total_tables: int = Field(description="Total number of tables")
    total_relationships: int = Field(description="Total number of relationships")
    discovery_time: float = Field(description="Time taken for discovery")


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""
    
    status: str = Field(description="Health status")
    databases: List[str] = Field(description="Available databases")
    uptime: float = Field(description="System uptime in seconds")
    version: str = Field(description="System version")
    metrics: Optional[SystemMetrics] = Field(default=None, description="System metrics")
