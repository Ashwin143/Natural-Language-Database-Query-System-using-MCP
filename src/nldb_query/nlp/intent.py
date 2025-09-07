"""Intent classifier for natural language database queries."""

import logging
from typing import List, Dict, Any
import openai
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifier for determining the intent of natural language queries."""
    
    def __init__(
        self, 
        openai_api_key: str,
        model: str = "gpt-4"
    ):
        """Initialize intent classifier.
        
        Args:
            openai_api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.openai_api_key = openai_api_key
        self.model = model
        
        # Define supported intents
        self.supported_intents = {
            "data_retrieval": "Retrieve specific data records or information",
            "aggregation": "Calculate sums, averages, counts, or other aggregations", 
            "comparison": "Compare values, find top/bottom results, or rankings",
            "trend_analysis": "Analyze trends over time or periods",
            "filtering": "Filter data based on specific criteria",
            "joining": "Combine data from multiple related tables",
            "reporting": "Generate business reports or summaries",
            "analytics": "Perform analytical queries for insights",
            "metadata": "Query about database structure or schema information"
        }
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model,
            temperature=0.1  # Low temperature for consistent classification
        )
        
        # Intent classification prompt
        self.intent_prompt = PromptTemplate(
            input_variables=["question", "intents"],
            template="""
            Classify the intent of this database query question.
            
            QUESTION: {question}
            
            AVAILABLE INTENTS:
            {intents}
            
            GUIDELINES:
            1. Choose the most specific intent that matches the question
            2. Consider the primary goal of the question
            3. If multiple intents apply, choose the most dominant one
            4. Return only the intent name, no explanation
            
            INTENT:
            """
        )
        
        self.classification_chain = LLMChain(
            llm=self.llm, 
            prompt=self.intent_prompt
        )
    
    async def classify_intent(self, question: str) -> str:
        """Classify the intent of a natural language question.
        
        Args:
            question: Natural language question
            
        Returns:
            Classified intent string
        """
        try:
            # Format intent descriptions for the prompt
            intents_text = self._format_intents_for_prompt()
            
            # Classify the intent
            result = await self.classification_chain.arun(
                question=question,
                intents=intents_text
            )
            
            # Clean up the result
            intent = result.strip().lower()
            
            # Validate the intent is supported
            if intent in self.supported_intents:
                return intent
            else:
                # Fallback to rule-based classification
                return self._fallback_classification(question)
                
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return self._fallback_classification(question)
    
    def _format_intents_for_prompt(self) -> str:
        """Format intent descriptions for the LLM prompt."""
        intents_text = ""
        for intent, description in self.supported_intents.items():
            intents_text += f"- {intent}: {description}\n"
        return intents_text
    
    def _fallback_classification(self, question: str) -> str:
        """Fallback rule-based intent classification."""
        question_lower = question.lower()
        
        # Rule-based patterns for intent classification
        intent_patterns = {
            "aggregation": [
                "total", "sum", "average", "count", "how many",
                "maximum", "minimum", "avg", "max", "min"
            ],
            "comparison": [
                "top", "bottom", "highest", "lowest", "best", "worst",
                "greater than", "less than", "compare", "versus"
            ],
            "trend_analysis": [
                "over time", "trend", "growth", "change", "increase",
                "decrease", "by month", "by year", "quarterly"
            ],
            "filtering": [
                "where", "filter", "specific", "only", "exclude",
                "between", "during", "within"
            ],
            "joining": [
                "customers and orders", "products and sales",
                "related", "associated with", "linked to"
            ],
            "reporting": [
                "report", "summary", "overview", "dashboard",
                "breakdown", "analysis by"
            ],
            "metadata": [
                "tables", "columns", "schema", "structure",
                "what data", "available", "database"
            ]
        }
        
        # Score each intent based on pattern matches
        intent_scores = {}
        for intent, patterns in intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in question_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return the highest scoring intent
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        # Default fallback
        return "data_retrieval"
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return list(self.supported_intents.keys())
    
    def get_intent_description(self, intent: str) -> str:
        """Get description for a specific intent."""
        return self.supported_intents.get(intent, "Unknown intent")
    
    async def classify_with_confidence(self, question: str) -> Dict[str, Any]:
        """Classify intent with confidence score.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with intent and confidence score
        """
        try:
            # Get primary classification
            primary_intent = await self.classify_intent(question)
            
            # Get fallback classification for comparison
            fallback_intent = self._fallback_classification(question)
            
            # Calculate confidence based on agreement
            confidence = 1.0 if primary_intent == fallback_intent else 0.7
            
            # Additional confidence adjustments
            question_lower = question.lower()
            
            # Increase confidence for clear patterns
            clear_patterns = {
                "aggregation": ["total", "sum", "count", "average"],
                "comparison": ["top", "best", "highest", "maximum"],
                "trend_analysis": ["over time", "trend", "monthly", "yearly"],
                "filtering": ["where", "specific", "only", "between"]
            }
            
            if primary_intent in clear_patterns:
                pattern_matches = sum(
                    1 for pattern in clear_patterns[primary_intent] 
                    if pattern in question_lower
                )
                if pattern_matches > 0:
                    confidence = min(1.0, confidence + 0.1 * pattern_matches)
            
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "fallback_intent": fallback_intent,
                "alternative_intents": self._get_alternative_intents(question)
            }
            
        except Exception as e:
            logger.error(f"Error in detailed intent classification: {e}")
            return {
                "intent": "data_retrieval",
                "confidence": 0.5,
                "error": str(e)
            }
    
    def _get_alternative_intents(self, question: str) -> List[str]:
        """Get alternative possible intents for the question."""
        question_lower = question.lower()
        alternatives = []
        
        # Check each intent for partial matches
        intent_keywords = {
            "data_retrieval": ["show", "get", "find", "list", "display"],
            "aggregation": ["total", "sum", "count", "average", "aggregate"],
            "comparison": ["compare", "versus", "top", "bottom", "rank"],
            "trend_analysis": ["trend", "over time", "change", "growth"],
            "filtering": ["where", "filter", "specific", "criteria"],
            "reporting": ["report", "summary", "analysis", "breakdown"],
            "analytics": ["insight", "pattern", "correlation", "analysis"]
        }
        
        for intent, keywords in intent_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in question_lower)
            if matches > 0:
                alternatives.append((intent, matches))
        
        # Sort by match count and return top alternatives
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return [intent for intent, _ in alternatives[:3]]
