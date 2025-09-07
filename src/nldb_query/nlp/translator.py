"""SQL translator for converting natural language to SQL queries."""

import logging
from typing import Any, Dict, List, Optional
import openai
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


logger = logging.getLogger(__name__)


class SQLTranslator:
    """Translator for converting natural language to SQL queries."""
    
    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.1
    ):
        """Initialize SQL translator.
        
        Args:
            openai_api_key: OpenAI API key
            model: OpenAI model to use
            temperature: Model temperature
        """
        self.openai_api_key = openai_api_key
        self.model = model
        self.temperature = temperature
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model,
            temperature=temperature
        )
        
        # SQL generation prompt template
        self.sql_prompt = PromptTemplate(
            input_variables=["question", "schema", "analysis", "intent"],
            template=\"\"\"
            You are an expert SQL developer. Convert the natural language question into a precise SQL query.
            
            QUESTION: {question}
            
            INTENT: {intent}
            
            ANALYSIS: {analysis}
            
            DATABASE SCHEMA:
            {schema}
            
            GUIDELINES:
            1. Generate syntactically correct SQL
            2. Use appropriate table and column names from the schema
            3. Include necessary JOINs based on foreign key relationships
            4. Apply appropriate WHERE clauses for filtering
            5. Use aggregation functions when needed (COUNT, SUM, AVG, etc.)
            6. Include ORDER BY and LIMIT when appropriate
            7. Handle date/time filtering correctly
            8. Use aliases for readability
            9. Ensure the query answers the original question
            
            IMPORTANT: Only return the SQL query, no explanation or additional text.
            
            SQL Query:
            \"\"\"
        )
        
        self.sql_chain = LLMChain(llm=self.llm, prompt=self.sql_prompt)
    
    async def translate_to_sql(
        self,
        question: str,
        schema_info: Dict[str, Any],
        analysis: Dict[str, Any],
        intent: str
    ) -> Dict[str, Any]:
        """Translate natural language question to SQL.
        
        Args:
            question: Natural language question
            schema_info: Database schema information
            analysis: Question analysis results
            intent: Classified intent
            
        Returns:
            Dictionary with SQL query and metadata
        """
        try:
            # Format schema information for the prompt
            schema_text = self._format_schema_for_prompt(schema_info)
            
            # Format analysis for the prompt
            analysis_text = self._format_analysis_for_prompt(analysis)
            
            # Generate SQL query
            result = await self.sql_chain.arun(
                question=question,
                schema=schema_text,
                analysis=analysis_text,
                intent=intent
            )
            
            # Clean up the result
            sql_query = self._clean_sql_query(result)
            
            # Validate the generated SQL
            validation = self._validate_sql_syntax(sql_query)
            
            return {
                "sql_query": sql_query,
                "confidence": validation.get("confidence", 0.8),
                "validation": validation,
                "intent": intent,
                "schema_elements_used": self._extract_used_elements(sql_query, schema_info)
            }
            
        except Exception as e:
            logger.error(f"Error translating question to SQL: {e}")
            return {
                "sql_query": "-- Error generating SQL query",
                "confidence": 0.0,
                "error": str(e),
                "intent": intent
            }
    
    def _format_schema_for_prompt(self, schema_info: Dict[str, Any]) -> str:
        """Format schema information for the LLM prompt."""
        schema_text = ""
        
        tables = schema_info.get("tables", [])
        relationships = schema_info.get("relationships", [])
        
        # Format tables
        for table in tables:
            table_name = table["name"]
            schema_text += f"\nTable: {table_name}\n"
            
            # Add columns
            for column in table["columns"]:
                col_info = f"  - {column['name']} ({column['type']})"
                if not column.get("nullable", True):
                    col_info += " NOT NULL"
                if column.get("default"):
                    col_info += f" DEFAULT {column['default']}"
                schema_text += col_info + "\n"
            
            # Add primary keys
            if table.get("primary_keys"):
                schema_text += f"  Primary Key: {', '.join(table['primary_keys'])}\n"
            
            # Add foreign keys
            for fk in table.get("foreign_keys", []):
                schema_text += f"  Foreign Key: {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}({', '.join(fk['referred_columns'])})\n"
            
            schema_text += "\n"
        
        # Format relationships
        if relationships:
            schema_text += "\\nTable Relationships:\\n"
            for rel in relationships:
                schema_text += f"  {rel['source_table']}.{', '.join(rel['source_columns'])} -> {rel['target_table']}.{', '.join(rel['target_columns'])}\\n"
        
        return schema_text
    
    def _format_analysis_for_prompt(self, analysis: Dict[str, Any]) -> str:
        """Format analysis information for the LLM prompt."""
        analysis_text = ""
        
        # Add key insights
        if analysis.get("business_concepts"):
            analysis_text += f"Business Concepts: {list(analysis['business_concepts'].keys())}\\n"
        
        if analysis.get("aggregations"):
            agg_functions = [agg["sql_function"] for agg in analysis["aggregations"]]
            analysis_text += f"Aggregations Needed: {', '.join(agg_functions)}\\n"
        
        if analysis.get("time_references", {}).get("has_time_reference"):
            time_info = analysis["time_references"]
            analysis_text += f"Time Filter: {time_info.get('time_expressions', [])}\\n"
        
        if analysis.get("comparisons"):
            operators = [comp["operator"] for comp in analysis["comparisons"]]
            analysis_text += f"Comparison Operators: {', '.join(operators)}\\n"
        
        if analysis.get("numbers"):
            numbers = [str(num["value"]) for num in analysis["numbers"]]
            analysis_text += f"Numbers Mentioned: {', '.join(numbers)}\\n"
        
        if analysis.get("potential_joins"):
            analysis_text += f"Potential Joins: {', '.join(analysis['potential_joins'])}\\n"
        
        analysis_text += f"Question Type: {analysis.get('question_type', 'unknown')}\\n"
        analysis_text += f"Complexity: {analysis.get('complexity', 'unknown')}\\n"
        
        return analysis_text
    
    def _clean_sql_query(self, raw_sql: str) -> str:
        """Clean and format the generated SQL query."""
        # Remove common prefixes/suffixes from LLM output
        sql = raw_sql.strip()
        
        # Remove markdown code blocks
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        # Remove extra whitespace and normalize
        lines = [line.strip() for line in sql.split("\\n") if line.strip()]
        sql = " ".join(lines)
        
        # Ensure it ends with semicolon
        if not sql.endswith(";"):
            sql += ";"
        
        return sql
    
    def _validate_sql_syntax(self, sql_query: str) -> Dict[str, Any]:
        """Basic validation of SQL syntax."""
        validation = {
            "is_valid": True,
            "confidence": 1.0,
            "issues": []
        }
        
        # Basic syntax checks
        sql_lower = sql_query.lower()
        
        # Check for required keywords
        if not sql_lower.startswith("select"):
            validation["is_valid"] = False
            validation["issues"].append("Query must start with SELECT")
        
        # Check for balanced parentheses
        if sql_query.count("(") != sql_query.count(")"):
            validation["is_valid"] = False
            validation["issues"].append("Unbalanced parentheses")
        
        # Check for FROM clause (unless it's a simple SELECT)
        if "from" not in sql_lower and not sql_lower.startswith("select "):
            validation["issues"].append("Missing FROM clause")
            validation["confidence"] -= 0.2
        
        # Check for common SQL keywords
        sql_keywords = ["select", "from", "where", "join", "group by", "having", "order by", "limit"]
        found_keywords = sum(1 for keyword in sql_keywords if keyword in sql_lower)
        
        # Adjust confidence based on query complexity
        if found_keywords < 2:
            validation["confidence"] -= 0.1
        elif found_keywords > 5:
            validation["confidence"] = min(1.0, validation["confidence"] + 0.1)
        
        # Final validation
        if validation["issues"]:
            validation["confidence"] = max(0.3, validation["confidence"] - 0.3)
        
        return validation
    
    def _extract_used_elements(
        self, 
        sql_query: str, 
        schema_info: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Extract schema elements used in the generated SQL."""
        used_elements = {
            "tables": [],
            "columns": [],
            "relationships": []
        }
        
        sql_lower = sql_query.lower()
        
        # Extract tables mentioned in the query
        for table in schema_info.get("tables", []):
            table_name = table["name"].lower()
            if table_name in sql_lower:
                used_elements["tables"].append(table["name"])
                
                # Extract columns from this table
                for column in table["columns"]:
                    col_name = column["name"].lower()
                    if col_name in sql_lower:
                        used_elements["columns"].append(f"{table['name']}.{column['name']}")
        
        # Extract relationships (JOINs)
        for relationship in schema_info.get("relationships", []):
            source_table = relationship["source_table"].lower()
            target_table = relationship["target_table"].lower()
            
            if (source_table in sql_lower and target_table in sql_lower and 
                "join" in sql_lower):
                used_elements["relationships"].append(relationship)
        
        return used_elements
    
    async def explain_sql_query(self, sql_query: str, question: str) -> str:
        """Generate an explanation of the SQL query."""
        explain_prompt = PromptTemplate(
            input_variables=["sql_query", "question"],
            template=\"\"\"
            Explain this SQL query in simple business terms:
            
            Original Question: {question}
            SQL Query: {sql_query}
            
            Provide a clear, non-technical explanation of:
            1. What data is being retrieved
            2. From which tables
            3. Any filtering or conditions
            4. Any calculations or aggregations
            5. How the results are organized
            
            Keep it concise and business-friendly.
            \"\"\"
        )
        
        explain_chain = LLMChain(llm=self.llm, prompt=explain_prompt)
        
        try:
            explanation = await explain_chain.arun(
                sql_query=sql_query,
                question=question
            )
            return explanation.strip()
        except Exception as e:
            logger.error(f"Error explaining SQL query: {e}")
            return f"This query retrieves data to answer: {question}"
