"""Database handlers for MCP server operations."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect
import pandas as pd

from .protocol import (
    DatabaseConnectionConfig,
    QueryRequest,
    QueryResponse,
    SchemaInfo,
    TableInfo
)


logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Handler for database operations within MCP server."""
    
    def __init__(self, config: DatabaseConnectionConfig):
        """Initialize database handler.
        
        Args:
            config: Database connection configuration
        """
        self.config = config
        self.engine = None
        self.session_factory = None
        self._schema_cache = None
        self._setup_engine()
    
    def _setup_engine(self):
        """Setup SQLAlchemy async engine."""
        # Convert sync URL to async if needed
        url = self.config.url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+aiomysql://")
        elif url.startswith("sqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://")
        
        self.engine = create_async_engine(
            url,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            echo=False  # Set to True for SQL debugging
        )
        
        self.session_factory = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    
    async def process_nl_query(self, request: QueryRequest) -> Dict[str, Any]:
        """Process a natural language query request.
        
        This is a placeholder that will be implemented with the NL processing module.
        """
        # For now, return a mock response
        # TODO: Integrate with natural language processing module
        return {
            "sql_query": "-- Generated from NL processing",
            "results": [],
            "explanation": f"Processing question: {request.question}",
            "metadata": {
                "database": self.config.name,
                "processing_time": 0.1
            },
            "formatted_response": f"Query processed: {request.question}"
        }
    
    async def discover_schema(self) -> Dict[str, Any]:
        """Discover and cache database schema information."""
        if self._schema_cache:
            return self._schema_cache
        
        async with self.session_factory() as session:
            try:
                # Get table information
                tables = await self._get_table_info(session)
                
                # Get relationships
                relationships = await self._get_relationship_info(session)
                
                # Get indexes
                indexes = await self._get_index_info(session)
                
                schema_info = {
                    "database_name": self.config.name,
                    "tables": tables,
                    "relationships": relationships,
                    "indexes": indexes
                }
                
                self._schema_cache = schema_info
                return schema_info
                
            except Exception as e:
                logger.error(f"Error discovering schema for {self.config.name}: {e}")
                raise
    
    async def _get_table_info(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get table information from database."""
        tables = []
        
        try:
            # Use SQLAlchemy inspector for cross-database compatibility
            inspector = inspect(self.engine.sync_engine)
            
            for table_name in inspector.get_table_names():
                columns = []
                primary_keys = []
                foreign_keys = []
                
                # Get column information
                for column in inspector.get_columns(table_name):
                    columns.append({
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column["nullable"],
                        "default": str(column["default"]) if column["default"] else None
                    })
                
                # Get primary keys
                pk_constraint = inspector.get_pk_constraint(table_name)
                if pk_constraint:
                    primary_keys = pk_constraint["constrained_columns"]
                
                # Get foreign keys
                for fk in inspector.get_foreign_keys(table_name):
                    foreign_keys.append({
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    })
                
                tables.append({
                    "name": table_name,
                    "schema": inspector.default_schema_name or "public",
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys
                })
                
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            # Return empty list rather than failing completely
        
        return tables
    
    async def _get_relationship_info(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get relationship information between tables."""
        relationships = []
        
        try:
            inspector = inspect(self.engine.sync_engine)
            
            for table_name in inspector.get_table_names():
                for fk in inspector.get_foreign_keys(table_name):
                    relationships.append({
                        "source_table": table_name,
                        "target_table": fk["referred_table"],
                        "source_columns": fk["constrained_columns"],
                        "target_columns": fk["referred_columns"],
                        "constraint_name": fk.get("name")
                    })
                    
        except Exception as e:
            logger.error(f"Error getting relationship info: {e}")
        
        return relationships
    
    async def _get_index_info(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get index information from database."""
        indexes = []
        
        try:
            inspector = inspect(self.engine.sync_engine)
            
            for table_name in inspector.get_table_names():
                for index in inspector.get_indexes(table_name):
                    indexes.append({
                        "name": index["name"],
                        "table": table_name,
                        "columns": index["column_names"],
                        "unique": index["unique"]
                    })
                    
        except Exception as e:
            logger.error(f"Error getting index info: {e}")
        
        return indexes
    
    async def explain_query(self, sql_query: str) -> Dict[str, Any]:
        """Explain a SQL query execution plan."""
        async with self.session_factory() as session:
            try:
                # Use database-specific EXPLAIN syntax
                if self.config.driver == "postgresql":
                    explain_query = f"EXPLAIN (FORMAT JSON) {sql_query}"
                elif self.config.driver == "mysql":
                    explain_query = f"EXPLAIN FORMAT=JSON {sql_query}"
                else:
                    explain_query = f"EXPLAIN QUERY PLAN {sql_query}"
                
                result = await session.execute(text(explain_query))
                plan = result.fetchall()
                
                return {
                    "sql_query": sql_query,
                    "execution_plan": [dict(row._mapping) for row in plan],
                    "database": self.config.name
                }
                
            except Exception as e:
                logger.error(f"Error explaining query: {e}")
                return {
                    "sql_query": sql_query,
                    "error": str(e),
                    "database": self.config.name
                }
    
    async def validate_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate a SQL query without executing it."""
        async with self.session_factory() as session:
            try:
                # Prepare query to check syntax
                stmt = text(sql_query)
                compiled = stmt.compile(dialect=self.engine.dialect)
                
                return {
                    "sql_query": sql_query,
                    "valid": True,
                    "compiled_query": str(compiled),
                    "database": self.config.name
                }
                
            except Exception as e:
                return {
                    "sql_query": sql_query,
                    "valid": False,
                    "error": str(e),
                    "database": self.config.name
                }
    
    async def execute_query(
        self, 
        sql_query: str, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query and return results."""
        async with self.session_factory() as session:
            try:
                # Apply limit if specified
                if limit:
                    # Simple limit addition - could be enhanced for complex queries
                    if not sql_query.upper().strip().endswith(";"):
                        sql_query += ";"
                    sql_query = sql_query.rstrip(";") + f" LIMIT {limit};"
                
                result = await session.execute(text(sql_query))
                
                # Convert results to list of dictionaries
                rows = result.fetchall()
                columns = list(result.keys()) if rows else []
                data = [dict(row._mapping) for row in rows]
                
                return {
                    "sql_query": sql_query,
                    "results": data,
                    "columns": columns,
                    "row_count": len(data),
                    "database": self.config.name
                }
                
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                return {
                    "sql_query": sql_query,
                    "error": str(e),
                    "database": self.config.name
                }
    
    async def get_tables(self) -> Dict[str, Any]:
        """Get list of tables in the database."""
        schema_info = await self.discover_schema()
        return {
            "tables": [
                {"name": table["name"], "columns": len(table["columns"])} 
                for table in schema_info["tables"]
            ],
            "database": self.config.name
        }
    
    async def get_relationships(self) -> Dict[str, Any]:
        """Get relationships between tables."""
        schema_info = await self.discover_schema()
        return {
            "relationships": schema_info["relationships"],
            "database": self.config.name
        }
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
