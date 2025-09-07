"""MCP server implementation for handling database queries."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .protocol import (
    MCPRequest, 
    MCPResponse, 
    MCPError, 
    MCPMethod,
    DatabaseConnectionConfig,
    QueryRequest,
    QueryResponse
)
from .handlers import DatabaseHandler


logger = logging.getLogger(__name__)


class MCPServer:
    """Model Context Protocol server for database queries."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize MCP server.
        
        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="NL Database Query MCP Server")
        self.database_handlers: Dict[str, DatabaseHandler] = {}
        self.method_handlers: Dict[str, Callable] = {}
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        self._setup_method_handlers()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.post("/mcp")
        async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
            """Handle MCP requests."""
            try:
                return await self._process_request(request)
            except Exception as e:
                logger.error(f"Error processing MCP request: {e}")
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    }
                )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "databases": list(self.database_handlers.keys())}
    
    def _setup_method_handlers(self):
        """Setup method handlers for different MCP methods."""
        self.method_handlers = {
            MCPMethod.INITIALIZE: self._handle_initialize,
            MCPMethod.QUERY: self._handle_query,
            MCPMethod.SCHEMA_DISCOVERY: self._handle_schema_discovery,
            MCPMethod.EXPLAIN_QUERY: self._handle_explain_query,
            MCPMethod.VALIDATE_QUERY: self._handle_validate_query,
            MCPMethod.EXECUTE_QUERY: self._handle_execute_query,
            MCPMethod.GET_TABLES: self._handle_get_tables,
            MCPMethod.GET_RELATIONSHIPS: self._handle_get_relationships,
        }
    
    async def _process_request(self, request: MCPRequest) -> MCPResponse:
        """Process an MCP request."""
        if request.method not in self.method_handlers:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            )
        
        handler = self.method_handlers[request.method]
        try:
            result = await handler(request.params or {})
            return MCPResponse(id=request.id, result=result)
        except Exception as e:
            logger.error(f"Error handling method {request.method}: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32000,
                    "message": f"Handler error: {str(e)}"
                }
            )
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "server": "nldb-query-mcp",
            "version": "0.1.0",
            "capabilities": {
                "query": True,
                "schema_discovery": True,
                "cross_database_queries": True,
                "explain_queries": True,
                "validate_queries": True
            }
        }
    
    async def _handle_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural language query request."""
        query_req = QueryRequest(**params)
        
        # Determine which database(s) to use
        if query_req.database:
            if query_req.database not in self.database_handlers:
                raise ValueError(f"Database '{query_req.database}' not found")
            handler = self.database_handlers[query_req.database]
        else:
            # Use primary database by default or determine from context
            handler = self._get_primary_handler()
        
        # Process the natural language query
        return await handler.process_nl_query(query_req)
    
    async def _handle_schema_discovery(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle schema discovery request."""
        database = params.get("database")
        if database and database in self.database_handlers:
            return await self.database_handlers[database].discover_schema()
        
        # Return schema info for all databases
        schemas = {}
        for name, handler in self.database_handlers.items():
            schemas[name] = await handler.discover_schema()
        return schemas
    
    async def _handle_explain_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle query explanation request."""
        sql_query = params.get("sql_query")
        database = params.get("database")
        
        if not sql_query:
            raise ValueError("sql_query parameter is required")
        
        handler = self._get_handler_for_database(database)
        return await handler.explain_query(sql_query)
    
    async def _handle_validate_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle query validation request."""
        sql_query = params.get("sql_query")
        database = params.get("database")
        
        if not sql_query:
            raise ValueError("sql_query parameter is required")
        
        handler = self._get_handler_for_database(database)
        return await handler.validate_query(sql_query)
    
    async def _handle_execute_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direct SQL query execution."""
        sql_query = params.get("sql_query")
        database = params.get("database")
        
        if not sql_query:
            raise ValueError("sql_query parameter is required")
        
        handler = self._get_handler_for_database(database)
        return await handler.execute_query(sql_query)
    
    async def _handle_get_tables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get tables request."""
        database = params.get("database")
        handler = self._get_handler_for_database(database)
        return await handler.get_tables()
    
    async def _handle_get_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get relationships request.""" 
        database = params.get("database")
        handler = self._get_handler_for_database(database)
        return await handler.get_relationships()
    
    def _get_handler_for_database(self, database: Optional[str]) -> DatabaseHandler:
        """Get handler for specified database or primary handler."""
        if database:
            if database not in self.database_handlers:
                raise ValueError(f"Database '{database}' not found")
            return self.database_handlers[database]
        return self._get_primary_handler()
    
    def _get_primary_handler(self) -> DatabaseHandler:
        """Get the primary database handler."""
        if "primary" in self.database_handlers:
            return self.database_handlers["primary"]
        if self.database_handlers:
            return next(iter(self.database_handlers.values()))
        raise ValueError("No database handlers configured")
    
    def add_database(self, config: DatabaseConnectionConfig) -> None:
        """Add a database connection to the server."""
        handler = DatabaseHandler(config)
        self.database_handlers[config.name] = handler
        logger.info(f"Added database connection: {config.name}")
    
    async def start(self) -> None:
        """Start the MCP server."""
        logger.info(f"Starting MCP server on {self.host}:{self.port}")
        config = uvicorn.Config(
            self.app, 
            host=self.host, 
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run(self) -> None:
        """Run the MCP server (blocking)."""
        asyncio.run(self.start())
