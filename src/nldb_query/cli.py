"""Command-line interface for the NLDB query system."""

import asyncio
import logging
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown

from .core import NLDBQuerySystem
from .version import __version__


# Initialize Rich console
console = Console()

# Initialize Typer app
app = typer.Typer(
    name="nldb-query",
    help="Natural Language Database Query System",
    add_completion=False
)


@app.command()
def query(
    question: str = typer.Argument(..., help="Natural language question"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Target database"),
    explain: bool = typer.Option(False, "--explain", "-e", help="Explain the query without executing"),
    format_output: bool = typer.Option(True, "--format/--no-format", help="Format output for readability"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """Ask a natural language question about your data."""
    asyncio.run(_query_command(question, database, explain, format_output, config_path))


@app.command()
def server(
    host: str = typer.Option("localhost", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """Start the MCP server."""
    console.print(f"[green]Starting NLDB Query Server on {host}:{port}[/green]")
    
    try:
        system = NLDBQuerySystem(config_path)
        # Override MCP server settings
        system.config.set("mcp.host", host)
        system.config.set("mcp.port", port)
        
        system.run_server()
    except KeyboardInterrupt:
        console.print("[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def interactive(
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Target database"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """Start interactive query session."""
    asyncio.run(_interactive_session(database, config_path))


@app.command()
def schema(
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Target database"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """Show database schema information."""
    asyncio.run(_schema_command(database, config_path))


@app.command()
def config(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """Show configuration information."""
    _config_command(config_path)


@app.command()
def version():
    """Show version information."""
    console.print(f"NLDB Query System version {__version__}")


async def _query_command(
    question: str,
    database: Optional[str],
    explain: bool,
    format_output: bool,
    config_path: Optional[str]
):
    """Execute a single query command."""
    try:
        system = NLDBQuerySystem(config_path)
        
        if explain:
            # Just explain the query
            result = await system.explain_query(question, database)
            if "error" in result:
                console.print(f"[red]Error: {result['error']}[/red]")
            else:
                console.print("[green]Query Explanation:[/green]")
                console.print(Markdown(f"**SQL Query:**\n```sql\n{result['sql_query']}\n```"))
                console.print(f"**Explanation:** {result['explanation']}")
                console.print(f"**Confidence:** {result['confidence']:.1%}")
        else:
            # Execute the query
            response = await system.query(
                question=question,
                database=database,
                execute=True,
                format_results=format_output
            )
            
            if response.success:
                result = response.result
                if format_output and result.formatted_response:
                    console.print(Markdown(result.formatted_response))
                else:
                    console.print(f"[green]SQL Query:[/green] {result.sql_query}")
                    if result.results:
                        console.print(f"[green]Results:[/green] {len(result.results)} rows")
                        # Display results in a table
                        if result.results:
                            _display_results_table(result.results)
            else:
                error = response.error
                console.print(f"[red]Error: {error.error_message}[/red]")
                if error.suggestions:
                    console.print("[yellow]Suggestions:[/yellow]")
                    for suggestion in error.suggestions:
                        console.print(f"  • {suggestion}")
        
        await system.close()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _interactive_session(database: Optional[str], config_path: Optional[str]):
    """Run interactive query session."""
    console.print("[green]Welcome to NLDB Interactive Query Session![/green]")
    console.print("Type 'exit' or 'quit' to end the session.")
    console.print("Type 'help' for available commands.")
    console.print()
    
    try:
        system = NLDBQuerySystem(config_path)
        await system.initialize()
        
        # Show available databases
        db_info = await system.get_database_info()
        if db_info["databases"]:
            console.print("[blue]Available databases:[/blue]")
            for db_name in db_info["databases"].keys():
                console.print(f"  • {db_name}")
            console.print()
        
        while True:
            try:
                # Get user input
                question = Prompt.ask("[bold green]Query[/bold green]")
                
                if question.lower() in ['exit', 'quit']:
                    break
                elif question.lower() == 'help':
                    _show_interactive_help()
                    continue
                elif question.lower() == 'schema':
                    await _show_schema_interactive(system, database)
                    continue
                elif question.lower() == 'metrics':
                    _show_metrics(system)
                    continue
                elif question.strip() == '':
                    continue
                
                # Process the query
                response = await system.query(
                    question=question,
                    database=database,
                    execute=True,
                    format_results=True
                )
                
                if response.success:
                    result = response.result
                    if result.formatted_response:
                        console.print(Markdown(result.formatted_response))
                    else:
                        console.print(f"[green]Results:[/green] {len(result.results or [])} rows")
                        if result.results:
                            _display_results_table(result.results[:10])  # Show first 10 rows
                else:
                    error = response.error
                    console.print(f"[red]Error: {error.error_message}[/red]")
                    if error.suggestions:
                        console.print("[yellow]Suggestions:[/yellow]")
                        for suggestion in error.suggestions:
                            console.print(f"  • {suggestion}")
                
                console.print()
                
            except KeyboardInterrupt:
                console.print("\\n[yellow]Use 'exit' or 'quit' to end the session[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        console.print("[green]Goodbye![/green]")
        await system.close()
        
    except Exception as e:
        console.print(f"[red]Error starting interactive session: {e}[/red]")
        raise typer.Exit(1)


async def _schema_command(database: Optional[str], config_path: Optional[str]):
    """Show schema information."""
    try:
        system = NLDBQuerySystem(config_path)
        db_info = await system.get_database_info()
        
        if not db_info["databases"]:
            console.print("[yellow]No databases configured[/yellow]")
            return
        
        if database:
            # Show specific database schema
            if database in db_info["databases"]:
                db_data = db_info["databases"][database]
                console.print(f"[green]Schema for database: {database}[/green]")
                console.print(f"Tables: {db_data['tables']}")
                console.print(f"Relationships: {db_data['relationships']}")
                console.print(f"Indexes: {db_data['indexes']}")
            else:
                console.print(f"[red]Database '{database}' not found[/red]")
        else:
            # Show all databases
            table = Table(title="Database Schema Summary")
            table.add_column("Database", style="cyan")
            table.add_column("Tables", justify="right")
            table.add_column("Relationships", justify="right")
            table.add_column("Indexes", justify="right")
            
            for db_name, db_data in db_info["databases"].items():
                table.add_row(
                    db_name,
                    str(db_data["tables"]),
                    str(db_data["relationships"]),
                    str(db_data["indexes"])
                )
            
            console.print(table)
        
        await system.close()
        
    except Exception as e:
        console.print(f"[red]Error retrieving schema: {e}[/red]")
        raise typer.Exit(1)


def _config_command(config_path: Optional[str]):
    """Show configuration information."""
    try:
        system = NLDBQuerySystem(config_path)
        config = system.config.get_all()
        
        console.print("[green]Configuration:[/green]")
        
        # Show database connections
        if "databases" in config:
            console.print("[blue]Databases:[/blue]")
            for db_name, db_config in config["databases"].items():
                if db_config:
                    console.print(f"  {db_name}: {db_config.get('url', 'Not configured')}")
        
        # Show OpenAI configuration
        if "openai" in config:
            openai_config = config["openai"]
            console.print("[blue]OpenAI:[/blue]")
            console.print(f"  Model: {openai_config.get('model', 'Not configured')}")
            console.print(f"  API Key: {'Configured' if openai_config.get('api_key') else 'Not configured'}")
        
        # Show MCP configuration
        if "mcp" in config:
            mcp_config = config["mcp"]
            console.print("[blue]MCP Server:[/blue]")
            console.print(f"  Host: {mcp_config.get('host', 'localhost')}")
            console.print(f"  Port: {mcp_config.get('port', 8000)}")
        
        # Show validation status
        is_valid = system.config.is_valid()
        status = "[green]Valid[/green]" if is_valid else "[red]Invalid[/red]"
        console.print(f"Configuration Status: {status}")
        
    except Exception as e:
        console.print(f"[red]Error reading configuration: {e}[/red]")
        raise typer.Exit(1)


def _display_results_table(results):
    """Display query results in a table."""
    if not results:
        return
    
    # Get column names from first row
    columns = list(results[0].keys())
    
    # Create table
    table = Table(title="Query Results")
    for col in columns:
        table.add_column(col, overflow="fold")
    
    # Add rows (limit to prevent overwhelming output)
    for row in results[:20]:  # Show first 20 rows
        values = [str(row.get(col, "")) for col in columns]
        table.add_row(*values)
    
    console.print(table)
    
    if len(results) > 20:
        console.print(f"[dim]... and {len(results) - 20} more rows[/dim]")


def _show_interactive_help():
    """Show help for interactive mode."""
    console.print("[blue]Available commands:[/blue]")
    console.print("  help      - Show this help")
    console.print("  schema    - Show database schema")
    console.print("  metrics   - Show system metrics")
    console.print("  exit/quit - Exit interactive mode")
    console.print()
    console.print("[blue]Example queries:[/blue]")
    console.print("  What are our top 10 customers by revenue?")
    console.print("  Show me sales data for this month")
    console.print("  How many orders were placed yesterday?")


async def _show_schema_interactive(system: NLDBQuerySystem, database: Optional[str]):
    """Show schema in interactive mode."""
    db_info = await system.get_database_info()
    
    if database and database in db_info["databases"]:
        db_data = db_info["databases"][database]
        console.print(f"[green]Schema for {database}:[/green]")
        console.print(f"  Tables: {db_data['tables']}")
        console.print(f"  Relationships: {db_data['relationships']}")
    else:
        console.print("[green]Available databases:[/green]")
        for db_name, db_data in db_info["databases"].items():
            console.print(f"  {db_name}: {db_data['tables']} tables, {db_data['relationships']} relationships")


def _show_metrics(system: NLDBQuerySystem):
    """Show system metrics."""
    metrics = system.get_metrics()
    
    console.print("[green]System Metrics:[/green]")
    console.print(f"  Total Queries: {metrics.total_queries}")
    console.print(f"  Successful: {metrics.successful_queries}")
    console.print(f"  Failed: {metrics.failed_queries}")
    
    if metrics.total_queries > 0:
        success_rate = (metrics.successful_queries / metrics.total_queries) * 100
        console.print(f"  Success Rate: {success_rate:.1f}%")
        console.print(f"  Average Confidence: {metrics.average_confidence:.1%}")


def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
