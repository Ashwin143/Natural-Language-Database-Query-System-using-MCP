"""Core system for natural language database queries."""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import time

from .mcp.server import MCPServer
from .mcp.protocol import DatabaseConnectionConfig, QueryRequest as MCPQueryRequest
from .nlp.processor import NLQueryProcessor
from .models import (
    QueryResult, 
    QueryError, 
    QueryRequest,
    QueryResponse,
    DatabaseSchema,
    SystemMetrics
)
from .formatters import ResultFormatter
from .validators import QueryValidator
from .utils.config import ConfigManager


logger = logging.getLogger(__name__)


class NLDBQuerySystem:
    """Main system for natural language database queries."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the NLDB query system.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = ConfigManager(config_path)
        
        # Initialize components
        self.mcp_server = None
        self.nl_processor = None
        self.result_formatter = None
        self.query_validator = None
        
        # System state
        self.is_initialized = False
        self.start_time = time.time()
        self.metrics = SystemMetrics()
        
        # Database schemas cache
        self.schemas_cache: Dict[str, DatabaseSchema] = {}
        
        logger.info("NLDB Query System initialized")
    
    async def initialize(self) -> None:
        """Initialize all system components."""
        if self.is_initialized:
            return
        
        try:
            # Initialize MCP server
            await self._initialize_mcp_server()
            
            # Initialize NL processor
            await self._initialize_nl_processor()
            
            # Initialize other components
            self.result_formatter = ResultFormatter()
            self.query_validator = QueryValidator()
            
            # Discover and cache database schemas
            await self._discover_schemas()
            
            self.is_initialized = True
            logger.info("NLDB Query System fully initialized")
            
        except Exception as e:
            logger.error(f"Error initializing NLDB Query System: {e}")
            raise
    
    async def _initialize_mcp_server(self) -> None:
        """Initialize MCP server with database connections."""
        host = self.config.get("mcp.host", "localhost")
        port = self.config.get("mcp.port", 8000)
        
        self.mcp_server = MCPServer(host=host, port=port)
        
        # Add database connections
        primary_db = self.config.get("databases.primary")
        analytics_db = self.config.get("databases.analytics")
        
        if primary_db:
            config = DatabaseConnectionConfig(
                name="primary",
                url=primary_db["url"],
                driver=primary_db.get("driver", "postgresql"),
                pool_size=primary_db.get("pool_size", 10),
                timeout=primary_db.get("timeout", 30)
            )
            self.mcp_server.add_database(config)
        
        if analytics_db:
            config = DatabaseConnectionConfig(
                name="analytics",
                url=analytics_db["url"],
                driver=analytics_db.get("driver", "postgresql"),
                pool_size=analytics_db.get("pool_size", 10),
                timeout=analytics_db.get("timeout", 30)
            )
            self.mcp_server.add_database(config)
        
        logger.info("MCP server initialized with database connections")
    
    async def _initialize_nl_processor(self) -> None:
        """Initialize natural language processor."""
        openai_api_key = self.config.get("openai.api_key")
        if not openai_api_key:
            raise ValueError("OpenAI API key not found in configuration")
        
        model = self.config.get("openai.model", "gpt-4")
        temperature = self.config.get("openai.temperature", 0.1)
        
        self.nl_processor = NLQueryProcessor(
            openai_api_key=openai_api_key,
            model=model,
            temperature=temperature
        )
        
        logger.info("Natural language processor initialized")
    
    async def _discover_schemas(self) -> None:
        """Discover and cache database schemas."""
        if not self.mcp_server:
            return
        
        for db_name, handler in self.mcp_server.database_handlers.items():
            try:
                schema_info = await handler.discover_schema()
                self.schemas_cache[db_name] = DatabaseSchema(
                    database_name=db_name,
                    **schema_info
                )
                logger.info(f"Discovered schema for database: {db_name}")
            except Exception as e:
                logger.error(f"Error discovering schema for {db_name}: {e}")
    
    async def query(
        self,
        question: str,
        database: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        execute: bool = True,
        format_results: bool = True,
        session_id: Optional[str] = None
    ) -> QueryResponse:
        """Process a natural language query.
        
        Args:
            question: Natural language question
            database: Target database name
            context: Additional context
            execute: Whether to execute the query
            format_results: Whether to format results
            session_id: Session ID for context
            
        Returns:
            QueryResponse with results or error
        """
        if not self.is_initialized:
            await self.initialize()
        
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            self.metrics.total_queries += 1
            
            # Validate inputs
            validation_result = await self.query_validator.validate_input(
                question, database, context
            )
            
            if not validation_result["is_valid"]:
                error = QueryError(
                    error_message=validation_result["error_message"],
                    error_type="validation_error",
                    original_question=question,
                    suggestions=validation_result.get("suggestions", [])
                )
                self.metrics.failed_queries += 1
                return QueryResponse(
                    success=False,
                    error=error,
                    query_id=query_id,
                    processing_time=time.time() - start_time
                )
            
            # Get schema for the target database
            schema_info = self._get_schema_for_database(database)
            
            # Process the natural language query
            query_result = await self.nl_processor.process_query(
                question=question,
                schema_info=schema_info,
                context=context
            )
            
            if isinstance(query_result, QueryError):
                self.metrics.failed_queries += 1
                return QueryResponse(
                    success=False,
                    error=query_result,
                    query_id=query_id,
                    processing_time=time.time() - start_time
                )
            
            # Execute the query if requested
            if execute and isinstance(query_result, QueryResult):
                execution_result = await self._execute_query(
                    query_result.sql_query,
                    database or "primary"
                )
                
                if "error" not in execution_result:
                    query_result.results = execution_result["results"]
                    query_result.row_count = execution_result["row_count"]
                    query_result.execution_time = execution_result.get("execution_time")
                    
                    # Format results if requested
                    if format_results:
                        formatted_response = await self.result_formatter.format_results(
                            query_result,
                            question
                        )
                        query_result.formatted_response = formatted_response
                else:
                    # Execution error
                    error = QueryError(
                        error_message=execution_result["error"],
                        error_type="execution_error",
                        original_question=question,
                        sql_query=query_result.sql_query
                    )
                    self.metrics.failed_queries += 1
                    return QueryResponse(
                        success=False,
                        error=error,
                        query_id=query_id,
                        processing_time=time.time() - start_time
                    )
            
            # Update metrics
            self.metrics.successful_queries += 1
            self.metrics.average_confidence = (
                (self.metrics.average_confidence * (self.metrics.successful_queries - 1) + 
                 query_result.confidence) / self.metrics.successful_queries
            )
            
            # Track intent
            intent = query_result.intent
            if intent in self.metrics.most_common_intents:
                self.metrics.most_common_intents[intent] += 1
            else:
                self.metrics.most_common_intents[intent] = 1
            
            processing_time = time.time() - start_time
            self.metrics.average_execution_time = (
                (self.metrics.average_execution_time * (self.metrics.total_queries - 1) + 
                 processing_time) / self.metrics.total_queries
            )
            
            return QueryResponse(
                success=True,
                result=query_result,
                query_id=query_id,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing query '{question}': {e}")
            self.metrics.failed_queries += 1
            
            error = QueryError(
                error_message=f"System error: {str(e)}",
                error_type="system_error",
                original_question=question
            )
            
            return QueryResponse(
                success=False,
                error=error,
                query_id=query_id,
                processing_time=time.time() - start_time
            )
    
    def _get_schema_for_database(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get schema information for the specified database."""
        if database and database in self.schemas_cache:
            return self.schemas_cache[database].dict()
        elif "primary" in self.schemas_cache:
            return self.schemas_cache["primary"].dict()
        elif self.schemas_cache:
            # Return first available schema
            return next(iter(self.schemas_cache.values())).dict()
        else:
            return {"tables": [], "relationships": [], "indexes": []}
    
    async def _execute_query(
        self, 
        sql_query: str, 
        database: str
    ) -> Dict[str, Any]:
        """Execute SQL query using MCP server."""
        if not self.mcp_server:
            return {"error": "MCP server not initialized"}
        
        if database not in self.mcp_server.database_handlers:
            return {"error": f"Database '{database}' not found"}
        
        handler = self.mcp_server.database_handlers[database]
        
        try:
            start_time = time.time()
            result = await handler.execute_query(sql_query)
            execution_time = time.time() - start_time
            
            if "error" not in result:
                result["execution_time"] = execution_time
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def explain_query(
        self,
        question: str,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """Explain how a natural language question would be processed."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Get schema for the database
            schema_info = self._get_schema_for_database(database)
            
            # Process the query without executing
            query_result = await self.nl_processor.process_query(
                question=question,
                schema_info=schema_info,
                context=None
            )
            
            if isinstance(query_result, QueryError):
                return {"error": query_result.error_message}
            
            return {
                "sql_query": query_result.sql_query,
                "explanation": query_result.explanation,
                "confidence": query_result.confidence,
                "intent": query_result.intent,
                "relevant_tables": query_result.relevant_tables,
                "processing_steps": query_result.metadata.get("processing_steps", [])
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get information about available databases."""
        if not self.is_initialized:
            await self.initialize()
        
        info = {
            "databases": {},
            "total_tables": 0,
            "total_relationships": 0
        }
        
        for db_name, schema in self.schemas_cache.items():
            info["databases"][db_name] = {
                "name": schema.database_name,
                "tables": len(schema.tables),
                "relationships": len(schema.relationships),
                "indexes": len(schema.indexes),
                "last_updated": schema.last_updated.isoformat()
            }
            info["total_tables"] += len(schema.tables)
            info["total_relationships"] += len(schema.relationships)
        
        return info
    
    def get_metrics(self) -> SystemMetrics:
        """Get system performance metrics."""
        self.metrics.last_updated = datetime.now()
        return self.metrics
    
    async def start_server(self) -> None:
        """Start the MCP server."""
        if not self.is_initialized:
            await self.initialize()
        
        if self.mcp_server:
            await self.mcp_server.start()
    
    def run_server(self) -> None:
        """Run the MCP server (blocking)."""
        asyncio.run(self.start_server())
    
    async def close(self) -> None:
        """Close all connections and cleanup."""
        if self.mcp_server:
            for handler in self.mcp_server.database_handlers.values():
                await handler.close()
        
        logger.info("NLDB Query System closed")
