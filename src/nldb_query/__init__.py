"""Natural Language Database Query System.

A Python-based system that transforms natural language questions into database queries
using Model Context Protocol (MCP) servers.
"""

from .core import NLDBQuerySystem
from .models import QueryResult, QueryError
from .version import __version__

__all__ = ["NLDBQuerySystem", "QueryResult", "QueryError", "__version__"]
