#!/usr/bin/env python3
"""
Simple example of using the Natural Language Database Query System.

This script demonstrates basic usage of the system for querying databases
with natural language questions.
"""

import asyncio
import os
from dotenv import load_dotenv

from nldb_query import NLDBQuerySystem


async def main():
    """Main example function."""
    # Load environment variables
    load_dotenv()
    
    # Check if required environment variables are set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required")
        print("Please set it in your .env file or environment")
        return
    
    if not os.getenv("PRIMARY_DB_URL"):
        print("Error: PRIMARY_DB_URL environment variable is required")
        print("Please set it in your .env file or environment")
        return
    
    print("🚀 Natural Language Database Query System Example")
    print("=" * 50)
    
    # Initialize the system
    print("Initializing system...")
    system = NLDBQuerySystem()
    
    try:
        # Get database information
        print("\\n📊 Database Information:")
        db_info = await system.get_database_info()
        for db_name, db_data in db_info["databases"].items():
            print(f"  • {db_name}: {db_data['tables']} tables, {db_data['relationships']} relationships")
        
        # Example queries to try
        example_questions = [
            "What tables are available in the database?",
            "How many records are in each table?",
            "What are the column names for the main tables?",
            # Add your own business-specific questions here
        ]
        
        print("\\n🤖 Example Queries:")
        print("-" * 30)
        
        for i, question in enumerate(example_questions, 1):
            print(f"\\n{i}. Question: {question}")
            
            # Process the query
            response = await system.query(
                question=question,
                execute=True,
                format_results=True
            )
            
            if response.success:
                result = response.result
                print(f"   ✅ Intent: {result.intent}")
                print(f"   ✅ Confidence: {result.confidence:.1%}")
                print(f"   ✅ SQL: {result.sql_query}")
                
                if result.results:
                    print(f"   ✅ Results: {len(result.results)} rows")
                    # Show first few results
                    if len(result.results) <= 3:
                        for row in result.results:
                            print(f"      {row}")
                    else:
                        for row in result.results[:2]:
                            print(f"      {row}")
                        print(f"      ... and {len(result.results) - 2} more rows")
                else:
                    print("   ✅ No results returned")
            else:
                error = response.error
                print(f"   ❌ Error: {error.error_message}")
                if error.suggestions:
                    print("   💡 Suggestions:")
                    for suggestion in error.suggestions:
                        print(f"      • {suggestion}")
        
        # Interactive example
        print("\\n🎯 Interactive Example:")
        print("-" * 25)
        print("You can now ask your own questions!")
        print("Type 'quit' to exit, 'help' for examples")
        
        while True:
            try:
                question = input("\\nQuestion: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    break
                elif question.lower() == 'help':
                    print("Example questions you can ask:")
                    print("• What are our top customers?")
                    print("• Show me sales data for this month")
                    print("• How many orders were placed yesterday?")
                    print("• What's the average order value?")
                    continue
                elif not question:
                    continue
                
                # Process the question
                response = await system.query(
                    question=question,
                    execute=True,
                    format_results=True
                )
                
                if response.success:
                    result = response.result
                    if result.formatted_response:
                        print(f"\\n{result.formatted_response}")
                    else:
                        print(f"\\nSQL: {result.sql_query}")
                        print(f"Results: {len(result.results or [])} rows")
                else:
                    error = response.error
                    print(f"\\n❌ {error.error_message}")
                    if error.suggestions:
                        print("💡 Try:")
                        for suggestion in error.suggestions:
                            print(f"  • {suggestion}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        # Show system metrics
        print("\\n📈 System Metrics:")
        print("-" * 20)
        metrics = system.get_metrics()
        print(f"Total queries: {metrics.total_queries}")
        print(f"Successful queries: {metrics.successful_queries}")
        print(f"Failed queries: {metrics.failed_queries}")
        
        if metrics.total_queries > 0:
            success_rate = (metrics.successful_queries / metrics.total_queries) * 100
            print(f"Success rate: {success_rate:.1f}%")
            print(f"Average confidence: {metrics.average_confidence:.1%}")
        
        print("\\n👋 Thanks for trying the Natural Language Database Query System!")
        
    except Exception as e:
        print(f"\\n❌ Error: {e}")
        print("\\nTroubleshooting tips:")
        print("• Check your .env file configuration")
        print("• Verify database connection")
        print("• Ensure OpenAI API key is valid")
        
    finally:
        # Clean up
        await system.close()


if __name__ == "__main__":
    asyncio.run(main())
