"""Result formatters for user-friendly output."""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from tabulate import tabulate
from datetime import datetime
import json

from .models import QueryResult


logger = logging.getLogger(__name__)


class ResultFormatter:
    """Formatter for query results to create user-friendly output."""
    
    def __init__(self):
        """Initialize result formatter."""
        self.max_display_rows = 100
        self.max_column_width = 50
    
    async def format_results(
        self, 
        query_result: QueryResult,
        original_question: str
    ) -> str:
        """Format query results for end users.
        
        Args:
            query_result: Query result object
            original_question: Original natural language question
            
        Returns:
            Formatted string response
        """
        try:
            if not query_result.results:
                return self._format_no_results(query_result, original_question)
            
            # Create base response
            response_parts = []
            
            # Add explanation
            if query_result.explanation:
                response_parts.append(f"**Answer:** {query_result.explanation}")
                response_parts.append("")
            
            # Add summary statistics
            if query_result.row_count is not None:
                summary = self._format_summary(query_result)
                response_parts.append(summary)
                response_parts.append("")
            
            # Format the data table
            table = self._format_data_table(query_result.results)
            response_parts.append("**Results:**")
            response_parts.append(table)
            
            # Add additional insights if applicable
            insights = self._generate_insights(query_result)
            if insights:
                response_parts.append("")
                response_parts.append("**Key Insights:**")
                response_parts.extend(insights)
            
            # Add technical details if confidence is low
            if query_result.confidence < 0.7:
                response_parts.append("")
                response_parts.append("*Note: This query has moderate confidence. Please verify the results.*")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error formatting results: {e}")
            return self._format_fallback_response(query_result, original_question)
    
    def _format_no_results(self, query_result: QueryResult, question: str) -> str:
        """Format response when no results are found."""
        response = f"**No results found for:** {question}\n\n"
        
        if query_result.explanation:
            response += f"**Explanation:** {query_result.explanation}\n\n"
        
        response += "**Possible reasons:**\n"
        response += "- The filters might be too restrictive\n"
        response += "- The data might not exist in the database\n"
        response += "- The query might need adjustment\n\n"
        
        if query_result.sql_query:
            response += f"**SQL Query Used:**\n```sql\n{query_result.sql_query}\n```"
        
        return response
    
    def _format_summary(self, query_result: QueryResult) -> str:
        """Format summary statistics."""
        summary_parts = []
        
        if query_result.row_count is not None:
            if query_result.row_count == 1:
                summary_parts.append("Found 1 result")
            else:
                summary_parts.append(f"Found {query_result.row_count:,} results")
        
        if query_result.execution_time is not None:
            exec_time = query_result.execution_time
            if exec_time < 1:
                summary_parts.append(f"(executed in {exec_time*1000:.0f}ms)")
            else:
                summary_parts.append(f"(executed in {exec_time:.2f}s)")
        
        return f"**Summary:** {' '.join(summary_parts)}"
    
    def _format_data_table(self, results: List[Dict[str, Any]]) -> str:
        """Format results as a table."""
        if not results:
            return "No data to display"
        
        # Limit rows for display
        display_results = results[:self.max_display_rows]
        
        # Convert to DataFrame for easier handling
        try:
            df = pd.DataFrame(display_results)
            
            # Format columns
            formatted_df = self._format_dataframe_columns(df)
            
            # Create table
            table = tabulate(
                formatted_df,
                headers=formatted_df.columns,
                tablefmt="grid",
                showindex=False,
                maxcolwidths=self.max_column_width
            )
            
            # Add truncation notice if needed
            if len(results) > self.max_display_rows:
                table += f"\n\n*Showing first {self.max_display_rows} of {len(results)} results*"
            
            return table
            
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return self._format_simple_list(display_results)
    
    def _format_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format DataFrame columns for better display."""
        formatted_df = df.copy()
        
        for column in formatted_df.columns:
            # Handle different data types
            if formatted_df[column].dtype == 'object':
                # String columns - truncate if too long
                formatted_df[column] = formatted_df[column].astype(str).apply(
                    lambda x: x[:47] + "..." if len(str(x)) > 50 else x
                )
            elif 'datetime' in str(formatted_df[column].dtype):
                # Format datetime columns
                formatted_df[column] = pd.to_datetime(formatted_df[column]).dt.strftime('%Y-%m-%d %H:%M')
            elif 'float' in str(formatted_df[column].dtype):
                # Format float columns
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A"
                )
            elif 'int' in str(formatted_df[column].dtype):
                # Format integer columns
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: f"{x:,}" if pd.notna(x) else "N/A"
                )
        
        return formatted_df
    
    def _format_simple_list(self, results: List[Dict[str, Any]]) -> str:
        """Fallback simple list format."""
        formatted_results = []
        
        for i, row in enumerate(results, 1):
            row_parts = []
            for key, value in row.items():
                row_parts.append(f"{key}: {value}")
            formatted_results.append(f"{i}. {', '.join(row_parts)}")
        
        return "\n".join(formatted_results)
    
    def _generate_insights(self, query_result: QueryResult) -> List[str]:
        """Generate additional insights from the results."""
        insights = []
        
        if not query_result.results:
            return insights
        
        try:
            # Basic insights based on result patterns
            row_count = len(query_result.results)
            
            # Check for numeric aggregations
            numeric_columns = []
            for row in query_result.results[:1]:  # Check first row
                for key, value in row.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        numeric_columns.append(key)
            
            # Generate insights for aggregated results
            if row_count == 1 and numeric_columns:
                for col in numeric_columns:
                    value = query_result.results[0][col]
                    if isinstance(value, (int, float)):
                        if col.lower() in ['total', 'sum', 'count']:
                            insights.append(f"• Total {col.lower()}: {value:,}")
                        elif col.lower() in ['average', 'avg', 'mean']:
                            insights.append(f"• Average {col.lower()}: {value:,.2f}")
            
            # Generate insights for multiple records
            elif row_count > 1:
                insights.append(f"• Dataset contains {row_count} records")
                
                # Check for date ranges
                date_columns = [k for k in query_result.results[0].keys() 
                              if 'date' in k.lower() or 'time' in k.lower()]
                
                if date_columns and row_count > 1:
                    date_col = date_columns[0]
                    try:
                        dates = [row[date_col] for row in query_result.results if row.get(date_col)]
                        if dates:
                            insights.append(f"• Date range: {min(dates)} to {max(dates)}")
                    except:
                        pass
            
            # Add confidence insight
            if query_result.confidence >= 0.9:
                insights.append("• High confidence result")
            elif query_result.confidence < 0.7:
                insights.append("• Moderate confidence - please verify")
                
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
        
        return insights
    
    def _format_fallback_response(
        self, 
        query_result: QueryResult, 
        question: str
    ) -> str:
        """Fallback response format when main formatting fails."""
        response = f"**Question:** {question}\n\n"
        
        if query_result.explanation:
            response += f"**Answer:** {query_result.explanation}\n\n"
        
        if query_result.results:
            response += f"**Results:** Found {len(query_result.results)} records\n"
            response += "```json\n"
            response += json.dumps(query_result.results[:5], indent=2, default=str)
            if len(query_result.results) > 5:
                response += f"\n... and {len(query_result.results) - 5} more records"
            response += "\n```\n"
        
        if query_result.sql_query:
            response += f"\n**SQL Query:**\n```sql\n{query_result.sql_query}\n```"
        
        return response
    
    def format_error(self, error_message: str, suggestions: List[str] = None) -> str:
        """Format error messages for users."""
        response = f"**Error:** {error_message}\n"
        
        if suggestions:
            response += "\n**Suggestions:**\n"
            for suggestion in suggestions:
                response += f"• {suggestion}\n"
        
        return response
    
    def format_explanation(self, explanation_data: Dict[str, Any]) -> str:
        """Format query explanation for users."""
        parts = []
        
        if explanation_data.get("explanation"):
            parts.append(f"**How this query works:**\n{explanation_data['explanation']}")
        
        if explanation_data.get("sql_query"):
            parts.append(f"\n**SQL Query:**\n```sql\n{explanation_data['sql_query']}\n```")
        
        if explanation_data.get("confidence"):
            confidence = explanation_data["confidence"]
            conf_text = "High" if confidence >= 0.8 else "Moderate" if confidence >= 0.6 else "Low"
            parts.append(f"\n**Confidence:** {conf_text} ({confidence:.1%})")
        
        if explanation_data.get("relevant_tables"):
            tables = ", ".join(explanation_data["relevant_tables"])
            parts.append(f"\n**Tables used:** {tables}")
        
        return "\n".join(parts)
