"""Query analyzer for extracting information from natural language questions."""

import re
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Analyzer for extracting key information from natural language queries."""
    
    def __init__(self):
        """Initialize query analyzer."""
        # Common business terms and their database equivalents
        self.business_mappings = {
            "customers": ["customer", "client", "user", "account"],
            "sales": ["sale", "order", "purchase", "transaction", "revenue"],
            "products": ["product", "item", "sku", "inventory"],
            "employees": ["employee", "staff", "worker", "person"],
            "time": ["date", "time", "period", "month", "quarter", "year"],
            "amount": ["amount", "price", "cost", "value", "total", "sum"],
            "count": ["count", "number", "quantity", "how many"]
        }
        
        # Temporal patterns
        self.time_patterns = {
            "today": 0,
            "yesterday": 1,
            "this week": 7,
            "last week": 14,
            "this month": 30,
            "last month": 60,
            "this quarter": 90,
            "last quarter": 180,
            "this year": 365,
            "last year": 730
        }
        
        # Aggregation patterns
        self.aggregation_patterns = {
            "total": "SUM",
            "sum": "SUM", 
            "average": "AVG",
            "avg": "AVG",
            "mean": "AVG",
            "count": "COUNT",
            "number of": "COUNT",
            "how many": "COUNT",
            "maximum": "MAX",
            "max": "MAX",
            "minimum": "MIN",
            "min": "MIN",
            "highest": "MAX",
            "lowest": "MIN"
        }
        
        # Comparison patterns
        self.comparison_patterns = {
            "greater than": ">",
            "more than": ">",
            "above": ">",
            "over": ">",
            "less than": "<",
            "below": "<",
            "under": "<",
            "equal to": "=",
            "equals": "=",
            "is": "=",
            "between": "BETWEEN",
            "from": "BETWEEN",
            "to": "BETWEEN"
        }
    
    async def analyze_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a natural language question.
        
        Args:
            question: The natural language question
            context: Additional context for analysis
            
        Returns:
            Dictionary with extracted information
        """
        question_lower = question.lower().strip()
        
        analysis = {
            "original_question": question,
            "keywords": self._extract_keywords(question_lower),
            "entities": self._extract_entities(question_lower),
            "time_references": self._extract_time_references(question_lower),
            "aggregations": self._extract_aggregations(question_lower),
            "comparisons": self._extract_comparisons(question_lower),
            "numbers": self._extract_numbers(question_lower),
            "business_concepts": self._map_business_concepts(question_lower),
            "question_type": self._classify_question_type(question_lower),
            "complexity": self._assess_complexity(question_lower),
            "potential_joins": self._identify_potential_joins(question_lower)
        }
        
        # Add context if provided
        if context:
            analysis["context"] = context
            
        return analysis
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract important keywords from the question."""
        # Remove common stop words
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "will", "with", "the", "this", "these", "those",
            "what", "when", "where", "who", "why", "how", "can", "could",
            "would", "should", "do", "does", "did", "have", "had", "having"
        }
        
        # Split into words and filter
        words = re.findall(r'\b\w+\b', question)
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def _extract_entities(self, question: str) -> List[str]:
        """Extract named entities and important business terms."""
        entities = []
        
        # Look for capitalized words (potential proper nouns)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', question)
        entities.extend(capitalized)
        
        # Look for quoted strings
        quoted = re.findall(r'"([^"]*)"', question)
        entities.extend(quoted)
        
        # Look for business-specific terms
        for category, terms in self.business_mappings.items():
            for term in terms:
                if term in question:
                    entities.append(term)
        
        return list(set(entities))  # Remove duplicates
    
    def _extract_time_references(self, question: str) -> Dict[str, Any]:
        """Extract temporal references from the question."""
        time_refs = {
            "has_time_reference": False,
            "time_expressions": [],
            "relative_time": None,
            "specific_dates": []
        }
        
        # Check for relative time expressions
        for expr, days_ago in self.time_patterns.items():
            if expr in question:
                time_refs["has_time_reference"] = True
                time_refs["time_expressions"].append(expr)
                time_refs["relative_time"] = {
                    "expression": expr,
                    "days_ago": days_ago,
                    "date": (datetime.now() - timedelta(days=days_ago)).date()
                }
        
        # Look for specific date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            if matches:
                time_refs["has_time_reference"] = True
                time_refs["specific_dates"].extend(matches)
        
        return time_refs
    
    def _extract_aggregations(self, question: str) -> List[str]:
        """Extract aggregation functions needed."""
        aggregations = []
        
        for phrase, sql_func in self.aggregation_patterns.items():
            if phrase in question:
                aggregations.append({
                    "phrase": phrase,
                    "sql_function": sql_func
                })
        
        return aggregations
    
    def _extract_comparisons(self, question: str) -> List[str]:
        """Extract comparison operators needed."""
        comparisons = []
        
        for phrase, operator in self.comparison_patterns.items():
            if phrase in question:
                comparisons.append({
                    "phrase": phrase,
                    "operator": operator
                })
        
        return comparisons
    
    def _extract_numbers(self, question: str) -> List[Dict[str, Any]]:
        """Extract numerical values from the question."""
        numbers = []
        
        # Look for integers and decimals
        number_patterns = [
            r'\\b\\d+\\.\\d+\\b',  # Decimals
            r'\\b\\d+\\b'          # Integers
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, question)
            for match in matches:
                try:
                    value = float(match) if '.' in match else int(match)
                    numbers.append({
                        "text": match,
                        "value": value,
                        "type": "decimal" if '.' in match else "integer"
                    })
                except ValueError:
                    continue
        
        # Look for spelled-out numbers
        spelled_numbers = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "twenty": 20, "thirty": 30, "fifty": 50, "hundred": 100
        }
        
        for word, value in spelled_numbers.items():
            if word in question:
                numbers.append({
                    "text": word,
                    "value": value,
                    "type": "spelled"
                })
        
        return numbers
    
    def _map_business_concepts(self, question: str) -> Dict[str, List[str]]:
        """Map business concepts mentioned in the question."""
        concepts = {}
        
        for concept, terms in self.business_mappings.items():
            found_terms = []
            for term in terms:
                if term in question:
                    found_terms.append(term)
            
            if found_terms:
                concepts[concept] = found_terms
        
        return concepts
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question being asked."""
        question_words = question.split()
        
        if any(word in question for word in ["what", "which", "who"]):
            return "selection"
        elif any(word in question for word in ["how many", "count", "number"]):
            return "counting"
        elif any(word in question for word in ["total", "sum", "average", "mean"]):
            return "aggregation"
        elif any(word in question for word in ["when", "time", "date"]):
            return "temporal"
        elif any(word in question for word in ["where", "location"]):
            return "spatial"
        elif any(word in question for word in ["why", "how", "explain"]):
            return "explanatory"
        elif "?" in question:
            return "inquiry"
        else:
            return "statement"
    
    def _assess_complexity(self, question: str) -> str:
        """Assess the complexity of the question."""
        complexity_score = 0
        
        # Check for multiple concepts
        concept_count = sum(1 for concept in self.business_mappings.keys() 
                          if any(term in question for term in self.business_mappings[concept]))
        complexity_score += concept_count
        
        # Check for time references
        if any(expr in question for expr in self.time_patterns.keys()):
            complexity_score += 1
        
        # Check for aggregations
        if any(phrase in question for phrase in self.aggregation_patterns.keys()):
            complexity_score += 1
        
        # Check for comparisons
        if any(phrase in question for phrase in self.comparison_patterns.keys()):
            complexity_score += 1
        
        # Check for question length
        word_count = len(question.split())
        if word_count > 15:
            complexity_score += 1
        
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 4:
            return "moderate"
        else:
            return "complex"
    
    def _identify_potential_joins(self, question: str) -> List[str]:
        """Identify potential table joins needed based on business concepts."""
        joins = []
        
        concepts_found = []
        for concept, terms in self.business_mappings.items():
            if any(term in question for term in terms):
                concepts_found.append(concept)
        
        # Common join patterns
        join_patterns = {
            ("customers", "sales"): "customer_orders",
            ("customers", "products"): "customer_purchases", 
            ("sales", "products"): "order_items",
            ("employees", "sales"): "sales_rep",
            ("products", "inventory"): "product_stock"
        }
        
        # Check for join patterns
        for (concept1, concept2), join_type in join_patterns.items():
            if concept1 in concepts_found and concept2 in concepts_found:
                joins.append(join_type)
        
        return joins
