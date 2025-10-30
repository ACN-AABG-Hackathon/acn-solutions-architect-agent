"""
Gateway Client - Unified interface for calling AgentCore Gateway tools
Provides a simple interface for agents to call Lambda functions via Gateway

Based on official Strands documentation:
https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/
https://strandsagents.com/latest/documentation/docs/examples/python/mcp_calculator/

FIXED: Enhanced response parsing to handle Gateway's nested JSON format
"""

import os
import uuid
from typing import Dict, Any, Optional, List
import structlog
import json

try:
    from strands.tools.mcp.mcp_client import MCPClient
    from mcp.client.streamable_http import streamablehttp_client
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

logger = structlog.get_logger(__name__)


class GatewayClient:
    """
    Client for calling AgentCore Gateway tools
    
    Provides a unified interface to call Lambda functions through the Gateway.
    Uses MCP Client with proper lambda wrapper for transport.
    
    Example:
        client = GatewayClient()
        result = client.call_tool("documentProcessor", {"s3_key": "..."})
    """
    
    def __init__(
        self,
        gateway_url: str = None,
        access_token: str = None
    ):
        """
        Initialize Gateway Client
        
        Args:
            gateway_url: Gateway MCP endpoint URL
            access_token: OAuth access token for Gateway
        """
        if not STRANDS_AVAILABLE:
            raise ImportError("Strands SDK not available. Install with: pip install strands-agents")
        
        self.gateway_url = gateway_url or os.getenv("AGENTCORE_GATEWAY_URL")
        self.access_token = access_token or os.getenv("AGENTCORE_ACCESS_TOKEN")
        
        if not self.gateway_url:
            raise ValueError("gateway_url or AGENTCORE_GATEWAY_URL environment variable is required")
        
        if not self.access_token:
            raise ValueError("access_token or AGENTCORE_ACCESS_TOKEN environment variable is required")
        
        logger.info("gateway_client_initialized", gateway_url=self.gateway_url)
    
    def _create_mcp_client(self) -> MCPClient:
        """
        Create MCP Client with proper lambda wrapper
        
        According to Strands documentation, streamablehttp_client must be wrapped in a lambda.
        See: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/
        
        Returns:
            MCPClient instance
        
        Example from docs:
            streamable_http_mcp_client = MCPClient(lambda: streamablehttp_client("http://localhost:8000/mcp"))
        """
        # CORRECT: Wrap streamablehttp_client in a lambda as per Strands documentation
        return MCPClient(
            lambda: streamablehttp_client(
                self.gateway_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        )
    
    def list_tools(self) -> List:
        """
        List all available tools from the Gateway
        
        Returns:
            List of tool objects
        
        Example:
            tools = client.list_tools()
            for tool in tools:
                print(tool.name)
        """
        mcp_client = self._create_mcp_client()
        
        with mcp_client:
            tools = []
            pagination_token = None
            more_tools = True
            
            while more_tools:
                tmp_tools = mcp_client.list_tools_sync(pagination_token=pagination_token)
                tools.extend(tmp_tools)
                
                if tmp_tools.pagination_token is None:
                    more_tools = False
                else:
                    pagination_token = tmp_tools.pagination_token
            
            logger.info("tools_listed", count=len(tools))
            return tools
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """
        Call a Gateway tool
        
        Args:
            tool_name: Name of the tool to call (e.g., "documentProcessor")
            arguments: Tool arguments as a dictionary
        
        Returns:
            Tool response as a dictionary
        
        Example:
            result = client.call_tool(
                "documentProcessor",
                {"s3_key": "documents/test.docx", "s3_bucket": "my-bucket"}
            )
        """
        # WORKAROUND: Gateway tools are configured with format "toolName___toolName"
        # Convert simple name to Gateway format
        gateway_tool_name = f"{tool_name}___{tool_name}"
        
        logger.info("calling_tool", tool_name=tool_name, gateway_tool_name=gateway_tool_name, arguments_keys=list(arguments.keys()))
        
        try:
            mcp_client = self._create_mcp_client()
            
            with mcp_client:
                # Generate a unique tool_use_id (required by Strands API)
                # See: https://strandsagents.com/latest/documentation/docs/examples/python/mcp_calculator/
                tool_use_id = f"tool_use_{uuid.uuid4().hex[:16]}"
                
                # Call tool using MCP client with correct signature:
                # call_tool_sync(tool_use_id, name, arguments)
                # Use gateway_tool_name (with ___ format) instead of tool_name
                result = mcp_client.call_tool_sync(
                    tool_use_id=tool_use_id,
                    name=gateway_tool_name,
                    arguments=arguments
                )
                logger.info("tool_call_completed", tool_name=tool_name, tool_use_id=tool_use_id)
                
                # Extract content from MCP response
                # MCP returns: MCPToolResult with content array
                if hasattr(result, 'content') and len(result.content) > 0:
                    content_item = result.content[0]
                    if hasattr(content_item, 'text'):
                        # Parse the text content as JSON (Lambda response)
                        response_data = json.loads(content_item.text)
                        logger.info("tool_response_parsed", status_code=response_data.get("statusCode"))
                        return response_data
                
                # Handle dict response (Gateway returns dict format)
                if isinstance(result, dict):
                    logger.info("handling_dict_response", result_keys=list(result.keys()))
                    
                    # Gateway returns: {'status': 'success', 'toolUseId': '...', 'content': [{'text': '...'}]}
                    if 'content' in result and isinstance(result['content'], list) and len(result['content']) > 0:
                        content_item = result['content'][0]
                        if isinstance(content_item, dict) and 'text' in content_item:
                            # Parse the nested JSON string
                            response_text = content_item['text']
                            logger.info("parsing_nested_json", text_preview=response_text[:100])
                            
                            try:
                                response_data = json.loads(response_text)
                                logger.info("tool_response_parsed", status_code=response_data.get("statusCode"))
                                return response_data
                            except json.JSONDecodeError as e:
                                logger.error("json_parse_error", error=str(e), text=response_text[:200])
                                return {"error": "Failed to parse response JSON", "raw_text": response_text}
                    
                    # If it's a dict with error info
                    if 'error' in result:
                        logger.error("mcp_error_response", error=result.get('error'))
                        return result
                    
                    # Return the dict as-is if we can't parse it
                    logger.warning("unexpected_dict_format", result_sample=str(result)[:200])
                    return result
                
                # Fallback: return raw result
                logger.warning("unexpected_response_format", result_type=type(result).__name__, result_str=str(result)[:200])
                return {"error": "Unexpected response format", "raw_result": str(result)}
                
        except Exception as e:
            logger.error("tool_call_failed", tool_name=tool_name, error=str(e), error_type=type(e).__name__)
            raise


# Singleton instance
_gateway_client: Optional[GatewayClient] = None


def get_gateway_client(
    gateway_url: str = None,
    access_token: str = None
) -> GatewayClient:
    """
    Get or create a singleton Gateway Client instance
    
    Args:
        gateway_url: Gateway MCP endpoint URL (optional if set in env)
        access_token: OAuth access token (optional if set in env)
    
    Returns:
        GatewayClient instance
    
    Example:
        client = get_gateway_client()
        tools = client.list_tools()
    """
    global _gateway_client
    
    if _gateway_client is None:
        _gateway_client = GatewayClient(gateway_url, access_token)
    
    return _gateway_client


def list_tools() -> List:
    """
    List all available tools from the Gateway
    
    Returns:
        List of tool objects
    
    Example:
        tools = list_tools()
        print([tool.name for tool in tools])
    """
    client = get_gateway_client()
    return client.list_tools()


def call_gateway_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict:
    """
    Convenience function to call a Gateway tool
    
    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments as a dictionary
    
    Returns:
        Tool response as a dictionary
    
    Example:
        result = call_gateway_tool("documentProcessor", {"s3_key": "..."})
    """
    client = get_gateway_client()
    return client.call_tool(tool_name, arguments)


# Convenience functions for each tool

def extract_requirements(document_text: str, session_id: str = None) -> Dict:
    """
    Extract requirements from document text via Gateway
    
    Args:
        document_text: Document text to extract requirements from
        session_id: Optional session ID for tracking
    
    Returns:
        Dict with requirements in Lambda response format:
        {
            "statusCode": 200,
            "body": {
                "requirements": {
                    "functional": [...],
                    "non_functional": [...],
                    ...
                }
            }
        }
    
    Example:
        result = extract_requirements("Build a web app with user auth...")
        requirements = json.loads(result["body"])["requirements"]
    """
    return call_gateway_tool(
        "requirementsExtractor",
        {
            "document_text": document_text,
            "session_id": session_id
        }
    )


def process_document(s3_bucket: str = None, s3_key: str = None, session_id: str = None) -> Dict:
    """
    Process a document from S3 via Gateway
    
    Args:
        s3_bucket: S3 bucket name (optional if set in env)
        s3_key: S3 object key
        session_id: Optional session ID for tracking
    
    Returns:
        Dict with extracted text and metadata in Lambda response format:
        {
            "statusCode": 200,
            "body": {
                "text": "...",
                "metadata": {...}
            }
        }
    
    Example:
        result = process_document(
            s3_bucket="my-bucket",
            s3_key="documents/requirements.docx"
        )
        text = json.loads(result["body"])["text"]
    """
    arguments = {
        "s3_key": s3_key,
        "session_id": session_id
    }
    
    if s3_bucket:
        arguments["s3_bucket"] = s3_bucket
    
    return call_gateway_tool("documentProcessor", arguments)


def query_knowledge_base(
    query: str,
    knowledge_base_id: str,
    max_results: int = 5,
    mode: str = "retrieve_and_generate"
) -> Dict:
    """
    Query a Bedrock Knowledge Base via Gateway
    
    Args:
        query: Query text
        knowledge_base_id: Knowledge Base ID
        max_results: Maximum number of results (default: 5)
        mode: "retrieve" or "retrieve_and_generate" (default: "retrieve_and_generate")
    
    Returns:
        Dict with answer and sources in Lambda response format:
        {
            "statusCode": 200,
            "body": {
                "answer": "...",
                "sources": [...]
            }
        }
    
    Example:
        result = query_knowledge_base(
            query="What is AWS Lambda?",
            knowledge_base_id="KB123456"
        )
        answer = json.loads(result["body"])["answer"]
    """
    return call_gateway_tool(
        "knowledgeBaseQuery",
        {
            "query": query,
            "knowledge_base_id": knowledge_base_id,
            "max_results": max_results,
            "mode": mode
        }
    )