"""Main natural language query processor."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
import openai
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from .analyzer import QueryAnalyzer
from .translator import SQLTranslator  
from .intent import IntentClassifier
from ..models import QueryResult, QueryError


logger = logging.getLogger(__name__)


class NLQueryProcessor:
    """Main processor for converting natural language to SQL queries."""
    
    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.1
    ):
        """Initialize NL query processor.
        
        Args:
            openai_api_key: OpenAI API key
            model: OpenAI model to use
            temperature: Model temperature for generation
        """
        self.openai_api_key = openai_api_key
        self.model = model
        self.temperature = temperature
        
        # Initialize components
        self.analyzer = QueryAnalyzer()
        self.translator = SQLTranslator(openai_api_key, model, temperature)
        self.intent_classifier = IntentClassifier(openai_api_key, model)
        
        # Setup OpenAI client
        openai.api_key = openai_api_key
    
    async def process_query(
        self,
        question: str,
        schema_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Process a natural language query.
        
        Args:
            question: Natural language question
            schema_info: Database schema information
            context: Additional context for query processing
            
        Returns:
            QueryResult with SQL query and metadata
        """
        try:
            # Step 1: Analyze the question
            analysis = await self.analyzer.analyze_question(question, context)
            logger.info(f"Question analysis: {analysis}")
            
            # Step 2: Classify intent
            intent = await self.intent_classifier.classify_intent(question)
            logger.info(f"Classified intent: {intent}")
            
            # Step 3: Find relevant tables and columns
            relevant_schema = await self._find_relevant_schema(
                question, schema_info, analysis, intent
            )
            
            # Step 4: Translate to SQL
            sql_result = await self.translator.translate_to_sql(
                question, relevant_schema, analysis, intent
            )
            
            # Step 5: Generate explanation
            explanation = await self._generate_explanation(
                question, sql_result["sql_query"], relevant_schema
            )
            
            return QueryResult(
                sql_query=sql_result["sql_query"],
                explanation=explanation,
                confidence=sql_result.get("confidence", 0.8),
                intent=intent,
                relevant_tables=relevant_schema.get("tables", []),
                metadata={
                    "analysis": analysis,
                    "schema_elements_used": relevant_schema,
                    "processing_steps": [
                        "question_analysis",
                        "intent_classification", 
                        "schema_matching",
                        "sql_translation",
                        "explanation_generation"
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing query '{question}': {e}")
            return QueryError(
                error_message=f"Failed to process query: {str(e)}",
                error_type="processing_error",
                original_question=question
            )
    
    async def _find_relevant_schema(
        self,
        question: str,
        schema_info: Dict[str, Any],
        analysis: Dict[str, Any],
        intent: str
    ) -> Dict[str, Any]:
        """Find relevant schema elements for the question."""
        
        # Extract keywords and entities from analysis
        keywords = analysis.get("keywords", [])
        entities = analysis.get("entities", [])
        
        # Find matching tables
        relevant_tables = []
        relevant_columns = []
        
        for table in schema_info.get("tables", []):
            table_name = table["name"].lower()
            table_score = 0
            
            # Check if table name matches keywords/entities
            for keyword in keywords + entities:
                if keyword.lower() in table_name or table_name in keyword.lower():
                    table_score += 2
            
            # Check column names for matches
            matching_columns = []
            for column in table["columns"]:
                col_name = column["name"].lower()
                for keyword in keywords + entities:
                    if keyword.lower() in col_name or col_name in keyword.lower():
                        table_score += 1
                        matching_columns.append(column)
            
            # Include table if it has a reasonable score
            if table_score > 0:
                relevant_tables.append({
                    **table,
                    "relevance_score": table_score,
                    "matching_columns": matching_columns
                })
        
        # Sort by relevance score
        relevant_tables.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Include relationships between relevant tables
        relevant_relationships = []
        table_names = [t["name"] for t in relevant_tables]
        
        for relationship in schema_info.get("relationships", []):
            if (relationship["source_table"] in table_names and 
                relationship["target_table"] in table_names):
                relevant_relationships.append(relationship)
        
        return {
            "tables": relevant_tables[:5],  # Limit to top 5 tables
            "relationships": relevant_relationships,
            "total_tables_in_db": len(schema_info.get("tables", [])),
            "schema_confidence": min(1.0, len(relevant_tables) / 3.0)
        }
    
    async def _generate_explanation(
        self,
        question: str,
        sql_query: str,
        schema_info: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of the SQL query."""
        
        prompt = f"""
        Explain this SQL query in simple, business-friendly language:
        
        Original Question: {question}
        SQL Query: {sql_query}
        
        Tables used: {[t['name'] for t in schema_info.get('tables', [])]}
        
        Provide a clear explanation of:
        1. What data is being retrieved
        2. From which tables
        3. Any filtering or aggregation being done
        4. How the results answer the original question
        
        Keep the explanation concise and avoid technical jargon.
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return f"This query retrieves data related to: {question}"
    
    async def validate_query_intent(
        self,
        question: str,
        expected_intent: str
    ) -> bool:
        """Validate that the question matches the expected intent."""
        classified_intent = await self.intent_classifier.classify_intent(question)
        return classified_intent == expected_intent
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported query intents."""
        return self.intent_classifier.get_supported_intents()
