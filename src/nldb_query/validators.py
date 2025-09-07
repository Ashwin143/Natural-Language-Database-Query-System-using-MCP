"""Query validators and error handling."""

import logging
import re
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class QueryValidator:
    """Validator for query inputs and error handling."""
    
    def __init__(self):
        """Initialize query validator."""
        self.min_question_length = 3
        self.max_question_length = 1000
        self.forbidden_patterns = [
            r'\bdrop\s+table\b',
            r'\bdrop\s+database\b', 
            r'\btruncate\b',
            r'\bdelete\s+from\b',
            r'\binsert\s+into\b',
            r'\bupdate\s+.+set\b',
            r'\balter\s+table\b',
            r'\bcreate\s+table\b',
            r'\bcreate\s+database\b'
        ]
    
    async def validate_input(
        self,
        question: str,
        database: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate query input parameters.
        
        Args:
            question: Natural language question
            database: Target database name
            context: Additional context
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            "is_valid": True,
            "error_message": "",
            "suggestions": []
        }
        
        try:
            # Validate question
            question_validation = self._validate_question(question)
            if not question_validation["is_valid"]:
                return question_validation
            
            # Validate database name
            if database:
                db_validation = self._validate_database_name(database)
                if not db_validation["is_valid"]:
                    return db_validation
            
            # Validate context
            if context:
                context_validation = self._validate_context(context)
                if not context_validation["is_valid"]:
                    return context_validation
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating input: {e}")
            return {
                "is_valid": False,
                "error_message": f"Validation error: {str(e)}",
                "suggestions": ["Please check your input and try again"]
            }
    
    def _validate_question(self, question: str) -> Dict[str, Any]:
        """Validate the natural language question."""
        if not question or not isinstance(question, str):
            return {
                "is_valid": False,
                "error_message": "Question cannot be empty",
                "suggestions": ["Please provide a natural language question"]
            }
        
        question = question.strip()
        
        # Check length
        if len(question) < self.min_question_length:
            return {
                "is_valid": False,
                "error_message": f"Question is too short (minimum {self.min_question_length} characters)",
                "suggestions": ["Please provide a more detailed question"]
            }
        
        if len(question) > self.max_question_length:
            return {
                "is_valid": False,
                "error_message": f"Question is too long (maximum {self.max_question_length} characters)",
                "suggestions": ["Please shorten your question"]
            }
        
        # Check for forbidden SQL operations
        question_lower = question.lower()
        for pattern in self.forbidden_patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                return {
                    "is_valid": False,
                    "error_message": "Question contains potentially dangerous SQL operations",
                    "suggestions": [
                        "This system is for data retrieval only",
                        "Please rephrase your question to focus on querying data"
                    ]
                }
        
        # Check for meaningful content
        if self._is_question_meaningful(question):
            return {"is_valid": True}
        else:
            return {
                "is_valid": False,
                "error_message": "Question doesn't appear to be a data query",
                "suggestions": [
                    "Please ask a question about your data",
                    "Examples: 'What are our top customers?' or 'Show me sales this month'"
                ]
            }
    
    def _is_question_meaningful(self, question: str) -> bool:
        """Check if the question appears to be a meaningful data query."""
        question_lower = question.lower()
        
        # Question words that indicate data queries
        query_indicators = [
            "what", "how many", "how much", "which", "when", "where",
            "who", "show", "list", "find", "get", "retrieve", "display",
            "count", "total", "sum", "average", "max", "min", "top", "bottom"
        ]
        
        # Business/data terms that suggest a valid query
        business_terms = [
            "sales", "revenue", "customer", "order", "product", "employee",
            "user", "account", "transaction", "invoice", "payment", "data",
            "record", "table", "database", "report", "analysis"
        ]
        
        # Check for query indicators
        has_query_indicator = any(indicator in question_lower for indicator in query_indicators)
        
        # Check for business terms
        has_business_term = any(term in question_lower for term in business_terms)
        
        # Should have at least one of each, or be a clear question
        return (has_query_indicator or has_business_term or 
                question.strip().endswith('?') or
                len(question.split()) >= 4)
    
    def _validate_database_name(self, database: str) -> Dict[str, Any]:
        """Validate database name."""
        if not isinstance(database, str):
            return {
                "is_valid": False,
                "error_message": "Database name must be a string",
                "suggestions": ["Provide a valid database name"]
            }
        
        database = database.strip()
        
        if not database:
            return {
                "is_valid": False,
                "error_message": "Database name cannot be empty",
                "suggestions": ["Provide a valid database name"]
            }
        
        # Check for valid database name format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', database):
            return {
                "is_valid": False,
                "error_message": "Invalid database name format",
                "suggestions": [
                    "Database name should start with a letter",
                    "Use only letters, numbers, and underscores"
                ]
            }
        
        return {"is_valid": True}
    
    def _validate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate context dictionary."""
        if not isinstance(context, dict):
            return {
                "is_valid": False,
                "error_message": "Context must be a dictionary",
                "suggestions": ["Provide context as key-value pairs"]
            }
        
        # Check for reasonable context size
        if len(str(context)) > 10000:
            return {
                "is_valid": False,
                "error_message": "Context is too large",
                "suggestions": ["Reduce the amount of context information"]
            }
        
        return {"is_valid": True}
    
    def validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate generated SQL query for safety."""
        validation_result = {
            "is_valid": True,
            "is_safe": True,
            "warnings": [],
            "errors": []
        }
        
        if not sql_query or not isinstance(sql_query, str):
            validation_result["is_valid"] = False
            validation_result["errors"].append("SQL query is empty or invalid")
            return validation_result
        
        sql_lower = sql_query.lower().strip()
        
        # Check for dangerous operations
        dangerous_operations = [
            'drop', 'truncate', 'delete', 'insert', 'update', 
            'alter', 'create', 'grant', 'revoke', 'exec'
        ]
        
        for op in dangerous_operations:
            if re.search(rf'\\b{op}\\b', sql_lower):
                validation_result["is_safe"] = False
                validation_result["errors"].append(f"Dangerous operation detected: {op.upper()}")
        
        # Must start with SELECT for safety
        if not sql_lower.startswith('select'):
            validation_result["is_safe"] = False
            validation_result["errors"].append("Query must be a SELECT statement")
        
        # Check for basic SQL structure
        if 'select' in sql_lower and 'from' not in sql_lower:
            validation_result["warnings"].append("Query may be missing FROM clause")
        
        # Check for unbalanced parentheses
        if sql_query.count('(') != sql_query.count(')'):
            validation_result["is_valid"] = False
            validation_result["errors"].append("Unbalanced parentheses in query")
        
        # Check for unbalanced quotes
        single_quotes = sql_query.count("'") - sql_query.count("\\'")
        double_quotes = sql_query.count('"') - sql_query.count('\\"')
        
        if single_quotes % 2 != 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Unbalanced single quotes in query")
        
        if double_quotes % 2 != 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Unbalanced double quotes in query")
        
        # Set overall validity
        if validation_result["errors"]:
            validation_result["is_valid"] = False
        
        return validation_result
    
    def suggest_improvements(
        self,
        question: str,
        error_type: str
    ) -> List[str]:
        """Suggest improvements for failed queries."""
        suggestions = []
        
        if error_type == "ambiguous_question":
            suggestions.extend([
                "Be more specific about what data you want to see",
                "Mention specific time periods, categories, or filters",
                "Use concrete business terms like 'customers', 'sales', 'products'"
            ])
        
        elif error_type == "no_relevant_tables":
            suggestions.extend([
                "Check if you're using the correct business terms",
                "Try different synonyms for your data entities",
                "Ask about available data first: 'What tables are available?'"
            ])
        
        elif error_type == "complex_query":
            suggestions.extend([
                "Break down your question into smaller, simpler queries",
                "Focus on one main question at a time",
                "Start with basic queries and build up complexity"
            ])
        
        elif error_type == "execution_error":
            suggestions.extend([
                "The generated query had technical issues",
                "Try rephrasing your question with simpler terms",
                "Check if the data you're asking about exists"
            ])
        
        elif error_type == "timeout_error":
            suggestions.extend([
                "Your query is taking too long to execute",
                "Try adding more specific filters to reduce data volume",
                "Ask for smaller date ranges or specific categories"
            ])
        
        else:
            # General suggestions
            suggestions.extend([
                "Try rephrasing your question more clearly",
                "Use specific business terms and avoid technical jargon",
                "Be more specific about what you want to see"
            ])
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def classify_error_type(self, error_message: str, context: Dict[str, Any] = None) -> str:
        """Classify error type based on error message and context."""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower or "time" in error_lower:
            return "timeout_error"
        elif "table" in error_lower and ("not found" in error_lower or "exist" in error_lower):
            return "no_relevant_tables"
        elif "syntax" in error_lower or "parse" in error_lower:
            return "sql_syntax_error"
        elif "ambiguous" in error_lower or "unclear" in error_lower:
            return "ambiguous_question"
        elif "complex" in error_lower or "complicated" in error_lower:
            return "complex_query"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission_error"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection_error"
        else:
            return "general_error"
