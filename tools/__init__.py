# tools/__init__.py
"""Tools package - Document processing, requirements extraction, and utilities.

MODIFIED FOR GATEWAY MIGRATION:
- Added gateway_client exports for Lambda-based tools
- Kept legacy classes for backward compatibility
"""

from .s3_utils import S3Manager
from .document_rag import DocumentRAG
from .refinement_engine import RefinementEngine
from .requirements_formatter import to_markdown as format_requirements_to_markdown
from .system_requirements import SystemRequirements

# NEW: Gateway client for Lambda-based tools
from .gateway_client import (
    get_gateway_client,
    list_tools,
    call_gateway_tool,
    extract_requirements,
    process_document,
    query_knowledge_base,
)

__all__ = [
    # Legacy classes (for backward compatibility)

    "S3Manager",
    "DocumentRAG",
    "RefinementEngine",
    "SystemRequirements",
    "format_requirements_to_markdown",
    # Gateway client (new)
    "get_gateway_client",
    "list_tools",
    "call_gateway_tool",
    "extract_requirements",
    "process_document",
    "query_knowledge_base",
]

