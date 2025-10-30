"""
Diagram Agent v6.31 - Generate diagrams via AgentCore Gateway
Uses Strands Agent + MCP Client to call Gateway's diagramRenderer tool
"""

import structlog
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if Strands and MCP dependencies are available
try:
    from strands import Agent
    from strands.models import BedrockModel
    from strands.tools.mcp.mcp_client import MCPClient
    from mcp.client.streamable_http import streamablehttp_client
    STRANDS_AVAILABLE = True
except ImportError as e:
    STRANDS_AVAILABLE = False
    IMPORT_ERROR = str(e)

logger = structlog.get_logger(__name__)


def create_streamable_http_transport(mcp_url: str, access_token: str):
    """Create streamable HTTP transport for MCP client."""
    return streamablehttp_client(
        mcp_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )


def get_full_tools_list(mcp_client: 'MCPClient') -> list:
    """Get all tools from Gateway with pagination support."""
    more_tools = True
    tools = []
    pagination_token = None
    
    while more_tools:
        tmp_tools = mcp_client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            pagination_token = tmp_tools.pagination_token
    
    return tools


class DiagramAgent:
    """
    AWS Solutions Architect Diagram Agent
    
    Generates Mermaid diagrams and renders them to PNG via AgentCore Gateway.
    
    Architecture:
        Diagram Agent → Strands Agent → MCP Client → Gateway → Lambda → S3
    """
    
    def __init__(
        self,
        gateway_url: str = None,
        access_token: str = None,
        model_id: str = None,
        aws_region: str = None,
        session_id: str = None
    ):
        """
        Initialize Diagram Agent with Gateway integration.
        
        Args:
            gateway_url: AgentCore Gateway MCP endpoint URL
            access_token: OAuth access token for Gateway
            model_id: Bedrock model ID
            aws_region: AWS region
            session_id: Session ID for tracking
        """
        if not STRANDS_AVAILABLE:
            raise ImportError(
                f"Strands dependencies not available: {IMPORT_ERROR}\n"
                "Install with: pip install strands-agents mcp"
            )
        
        # Configuration
        self.gateway_url = gateway_url or os.getenv('AGENTCORE_GATEWAY_URL')
        self.access_token = access_token or os.getenv('AGENTCORE_ACCESS_TOKEN')
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-7-sonnet-20250219-v1:0"
        )
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.session_id = session_id or "default_session"
        
        # S3 bucket configuration
        self.s3_bucket = os.getenv('S3_RESULT_BUCKET_NAME', 'aws-architect-agent-results')
        self.s3_diagram_prefix = os.getenv('S3_DIAGRAM_PREFIX', 'architecture-diagrams/')
        
        # Validate configuration
        if not self.gateway_url:
            raise ValueError("AGENTCORE_GATEWAY_URL not set")
        if not self.access_token:
            raise ValueError("AGENTCORE_ACCESS_TOKEN not set")
        
        logger.info(
            "diagram_agent_initialized",
            gateway_url=self.gateway_url,
            model_id=self.model_id,
            session_id=self.session_id
        )
        
        # Instructions for Mermaid generation
        self.mermaid_instructions = """You are an AWS Solutions Architect specialized in creating beautiful, color-coded architecture diagrams.

Your task is to generate valid Mermaid diagram code for AWS architectures with proper styling and color themes.

## Mermaid Syntax Guidelines

### Basic Structure
- Use 'graph TB' for top-to-bottom flowcharts (recommended)
- Use 'graph LR' for left-to-right flowcharts
- Use descriptive labels with square brackets: [API Gateway], [Lambda Function]
- Use database notation for databases: [(DynamoDB)]
- Use arrows for connections: -->
- Use subgraphs to group related components: subgraph VPC ... end

### Color Themes by Layer
Define these color classes at the START of your diagram (after 'graph TB'):

```
classDef computeClass    fill:#81A1C1,stroke:#4C566A,stroke-width:2px,color:#1F2937;  %% steel blue
classDef storageClass    fill:#A3BE8C,stroke:#4C566A,stroke-width:2px,color:#1F2937;  %% sage
classDef databaseClass   fill:#B48EAD,stroke:#4C566A,stroke-width:2px,color:#1F2937;  %% mauve
classDef networkClass    fill:#88C0D0,stroke:#4C566A,stroke-width:2px,color:#1F2937;  %% cyan
classDef securityClass   fill:#BF616A,stroke:#4C566A,stroke-width:2px,color:#F8FAFC;  %% muted red (light text)
classDef integrationClass fill:#EBCB8B,stroke:#4C566A,stroke-width:2px,color:#1F2937; %% honey
classDef analyticsClass  fill:#D08770,stroke:#4C566A,stroke-width:2px,color:#F8FAFC;  %% terracotta (light text)
classDef userClass       fill:#2E3440,stroke:#88C0D0,stroke-width:3px,color:#ECEFF4;  %% charcoal w/ cyan accent

```

### Service Classification

**Compute Layer** (Orange #FF9900):
- Lambda, ECS, EKS, EC2, Fargate, App Runner, Batch

**Storage Layer** (Green #3F8624):
- S3, EFS, EBS, FSx, Glacier, Storage Gateway

**Database Layer** (Blue #3B48CC):
- DynamoDB, RDS, Aurora, DocumentDB, ElastiCache, Neptune, Redshift

**Networking Layer** (Purple #8C4FFF):
- VPC, API Gateway, CloudFront, Route 53, Load Balancer, Direct Connect

**Security Layer** (Red #DD344C):
- IAM, Cognito, KMS, Secrets Manager, WAF, Shield, GuardDuty

**Integration Layer** (Orange #FF9900):
- SQS, SNS, EventBridge, Step Functions, SES, Kinesis

**Analytics Layer** (Orange #FF9900):
- Athena, Glue, EMR, QuickSight, Kinesis Analytics

**User/External** (Dark Gray #232F3E):
- Users, External Systems, Internet

### Applying Classes

After defining nodes, apply classes using the `:::` syntax:
```
Lambda[AWS Lambda]:::computeClass
S3[S3 Bucket]:::storageClass
DB[(DynamoDB)]:::databaseClass
```

### Complete Example

```mermaid
graph TB
    %% Define color classes
    classDef computeClass fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#FFFFFF
    classDef storageClass fill:#3F8624,stroke:#232F3E,stroke-width:2px,color:#FFFFFF
    classDef databaseClass fill:#3B48CC,stroke:#232F3E,stroke-width:2px,color:#FFFFFF
    classDef networkClass fill:#8C4FFF,stroke:#232F3E,stroke-width:2px,color:#FFFFFF
    classDef securityClass fill:#DD344C,stroke:#232F3E,stroke-width:2px,color:#FFFFFF
    classDef userClass fill:#232F3E,stroke:#FF9900,stroke-width:3px,color:#FFFFFF
    
    %% Define nodes with classes
    User[User]:::userClass
    CF[CloudFront]:::networkClass
    S3[S3 Bucket]:::storageClass
    API[API Gateway]:::networkClass
    Lambda[Lambda Function]:::computeClass
    DB[(DynamoDB)]:::databaseClass
    Cognito[AWS Cognito]:::securityClass
    
    %% Define connections
    User --> CF
    CF --> S3
    CF --> API
    API --> Lambda
    Lambda --> DB
    User --> Cognito
    Cognito --> API
```

## IMPORTANT Rules

1. **ALWAYS define classDef** at the start (after 'graph TB')
2. **ALWAYS apply classes** to ALL nodes using `:::className`
3. **Use proper AWS service names** (e.g., "AWS Lambda", not just "Lambda")
4. **Group by layer** when possible using subgraphs
5. **Return ONLY the Mermaid code** - no markdown blocks, no explanations
6. **Start with 'graph TB'** and classDef definitions
7. **Ensure all node IDs are unique**
8. **Use proper arrow syntax** (-->)

## Service-to-Class Mapping

When you see these services, use these classes:

- **Compute**: Lambda, ECS, EKS, EC2, Fargate → `computeClass`
- **Storage**: S3, EFS, EBS → `storageClass`
- **Database**: DynamoDB, RDS, Aurora → `databaseClass`
- **Network**: API Gateway, CloudFront, VPC, ALB → `networkClass`
- **Security**: IAM, Cognito, KMS, WAF → `securityClass`
- **Integration**: SQS, SNS, EventBridge, Step Functions → `integrationClass`
- **User/External**: Users, External Systems → `userClass`"""
    
    async def generate_diagram(
        self,
        architecture_json: str,
        architecture_name: str = None
    ) -> dict:
        """
        Generate Mermaid diagram and render to PNG via Gateway.
        
        This method:
        1. Generates Mermaid code from architecture JSON
        2. Uses Strands Agent + MCP Client to call Gateway
        3. Gateway invokes Lambda to render diagram
        4. Returns S3 URL of the rendered PNG
        
        Args:
            architecture_json: JSON string of architecture details
            architecture_name: Name for the diagram file
            
        Returns:
            Dict with:
                - success: bool
                - mermaid_code: str (the generated Mermaid code)
                - s3_url: str (S3 URL of rendered PNG)
                - s3_key: str (S3 key)
                - error: str (if failed)
        """
        logger.info(
            "generating_diagram_via_gateway",
            architecture_name=architecture_name,
            session_id=self.session_id
        )
        
        try:
            # Step 1: Generate Mermaid code
            mermaid_code = await self._generate_mermaid_code(architecture_json)
            
            logger.info(
                "mermaid_code_generated",
                length=len(mermaid_code),
                preview=mermaid_code[:100]
            )
            
            # Step 2: Render diagram via Gateway
            render_result = await self._render_via_gateway(
                mermaid_code=mermaid_code,
                architecture_name=architecture_name or "architecture"
            )
            
            if not render_result.get('success'):
                return {
                    'success': False,
                    'mermaid_code': mermaid_code,
                    'error': render_result.get('error', 'Unknown rendering error')
                }
            
            logger.info(
                "diagram_generated_successfully",
                s3_url=render_result.get('s3_url')
            )
            
            return {
                'success': True,
                'mermaid_code': mermaid_code,
                's3_url': render_result.get('s3_url'),
                's3_key': render_result.get('s3_key'),
                'agent_response': render_result.get('agent_response')
            }
        
        except Exception as e:
            logger.error(
                "diagram_generation_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_mermaid_code(self, architecture_json: str) -> str:
        """
        Generate Mermaid code from architecture JSON.
        
        Uses a simple Bedrock model call (not via Gateway).
        """
        # Parse architecture
        try:
            arch_data = json.loads(architecture_json)
            arch_name = arch_data.get("name", "AWS Architecture")
        except Exception as e:
            logger.warning("failed_to_parse_architecture", error=str(e))
            arch_name = "AWS Architecture"
        
        # Create prompt
        prompt = f"""{self.mermaid_instructions}

### Architecture to Diagram

{architecture_json}

Generate a clear Mermaid diagram showing all AWS services and their connections.
Return ONLY the Mermaid code, starting with 'graph TB' or 'graph LR'."""
        
        # Use Bedrock model directly (not via Gateway)
        bedrock_model = BedrockModel(
            model_id=self.model_id,
            streaming=False
        )
        
        # Create simple agent for Mermaid generation
        agent = Agent(model=bedrock_model, tools=[])
        
        logger.info("invoking_bedrock_for_mermaid_generation")
        
        response = agent(prompt)
        
        # Extract text from response
        mermaid_code = self._extract_text_from_response(response)
        
        # Clean and validate
        mermaid_code = self._clean_mermaid_code(mermaid_code)
        
        return mermaid_code
    
    async def _render_via_gateway(
        self,
        mermaid_code: str,
        architecture_name: str
    ) -> dict:
        """
        Render Mermaid diagram via Gateway.
        
        Uses Strands Agent + MCP Client to call Gateway's diagramRenderer tool.
        """
        logger.info(
            "rendering_via_gateway",
            code_length=len(mermaid_code),
            architecture_name=architecture_name
        )
        
        try:
            # Setup Bedrock model
            bedrock_model = BedrockModel(
                model_id=self.model_id,
                streaming=False
            )
            
            logger.info("bedrock_model_initialized", model_id=self.model_id)
            
            # Setup MCP client
            mcp_client = MCPClient(
                lambda: create_streamable_http_transport(
                    self.gateway_url,
                    self.access_token
                )
            )
            
            logger.info("mcp_client_initialized")
            
            # Use MCP client context
            with mcp_client:
                # Get tools from Gateway
                tools = get_full_tools_list(mcp_client)
                tool_names = [tool.tool_name for tool in tools]
                
                logger.info(
                    "gateway_tools_loaded",
                    tool_count=len(tools),
                    tool_names=tool_names
                )
                
                # Check if diagramRenderer tool is available
                # Tool name might be 'diagramRenderer' or 'diagramRenderer___diagramRenderer'
                diagram_tool_found = False
                actual_tool_name = None
                for tool_name in tool_names:
                    if 'diagramRenderer' in tool_name:
                        diagram_tool_found = True
                        actual_tool_name = tool_name
                        break
                
                if not diagram_tool_found:
                    raise ValueError(
                        f"diagramRenderer tool not found in Gateway. "
                        f"Available tools: {tool_names}"
                    )
                
                logger.info("diagram_tool_found", tool_name=actual_tool_name)
                
                # Create Strands Agent with tools
                agent = Agent(model=bedrock_model, tools=tools)
                
                logger.info("strands_agent_created_with_gateway_tools")
                
                # Prepare prompt for agent (use actual tool name)
                prompt = (
                    f"Use the {actual_tool_name} tool to render this Mermaid diagram. "
                    f"The architecture name is '{architecture_name}' and session ID is '{self.session_id}'.\n\n"
                    f"Call the {actual_tool_name} tool with these exact parameters:\n"
                    f"- mermaid_code: {mermaid_code}\n"
                    f"- architecture_name: {architecture_name}\n"
                    f"- session_id: {self.session_id}\n"
                    f"- output_format: svg\n"  # ✅ ADD THIS LINE
                    f"- s3_bucket: {self.s3_bucket}\n"
                    f"- s3_diagram_prefix: {self.s3_diagram_prefix}\n\n"
                    f"You MUST call the tool and return the S3 URL from the tool's response."
                )
                
                logger.info(
                    "invoking_strands_agent_for_rendering",
                    prompt_length=len(prompt)
                )
                
                # Invoke agent
                response = agent(prompt)
                
                logger.info(
                    "agent_response_received",
                    response_type=type(response).__name__
                )
                
                # Extract S3 URL from response
                response_content = response.message.get('content', str(response))
                
                logger.info(
                    "agent_response_content",
                    content_preview=str(response_content)[:500]
                )
                
                # Parse S3 URL from response
                s3_url = None
                s3_key = None
                
                # Convert response_content to string for parsing
                response_text = ""
                
                if isinstance(response_content, list):
                    # Strands Agent returns list of content items
                    for item in response_content:
                        if isinstance(item, dict) and 'text' in item:
                            response_text += item['text'] + " "
                        else:
                            response_text += str(item) + " "
                elif isinstance(response_content, str):
                    response_text = response_content
                else:
                    response_text = str(response_content)
                
                # Look for S3 URL in response text
                import re
                # Match URLs, handling Markdown formatting like **URL**
                url_pattern = r'https://[^\s*]+'
                urls = re.findall(url_pattern, response_text)
                
                for url in urls:
                    # Clean up any trailing Markdown characters
                    url = url.rstrip('*').rstrip(')')
                    
                    if '.s3.' in url or '.s3-' in url:
                        s3_url = url
                        # Extract S3 key from URL (support both diagrams/ and architecture-diagrams/)
                        if '.amazonaws.com/' in url:
                            s3_key = url.split('.amazonaws.com/')[-1]
                        break
                
                if not s3_url:
                    logger.warning(
                        "s3_url_not_found_in_response",
                        response_content=str(response_content)
                    )
                    raise ValueError(
                        "Could not extract S3 URL from agent response. "
                        "The diagramRenderer tool may not have been called successfully."
                    )
                
                logger.info(
                    "diagram_rendered_successfully",
                    s3_url=s3_url,
                    s3_key=s3_key
                )
                
                return {
                    'success': True,
                    's3_url': s3_url,
                    's3_key': s3_key,
                    'agent_response': str(response_content)
                }
        
        except Exception as e:
            logger.error(
                "gateway_rendering_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_text_from_response(self, response) -> str:
        """Extract text from various response formats."""
        
        # Handle string response
        if isinstance(response, str):
            return response
        
        # Handle dict response
        if isinstance(response, dict):
            # Strands format: {'role': 'assistant', 'content': [...]}
            if 'role' in response and 'content' in response:
                content = response['content']
                
                # Content is a list
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    
                    # First item is dict with 'text'
                    if isinstance(first_item, dict) and 'text' in first_item:
                        return first_item['text']
                    else:
                        return str(first_item)
                
                # Content is string
                elif isinstance(content, str):
                    return content
                
                # Content is something else
                else:
                    return str(content)
            
            # Direct message format: {'message': '...'}
            elif 'message' in response:
                return str(response['message'])
            
            # Unknown dict format
            else:
                return str(response)
        
        # Handle object with message attribute
        if hasattr(response, 'message'):
            message = response.message
            # message might be a dict, recursively extract
            if isinstance(message, dict):
                return self._extract_text_from_response(message)
            else:
                return str(message)
        
        # Fallback: convert to string
        return str(response)
    
    def _clean_mermaid_code(self, text: str) -> str:
        """Clean and extract Mermaid code from text."""
        
        # Ensure text is string
        if not isinstance(text, str):
            text = str(text)
        
        # Remove markdown code blocks
        if "```mermaid" in text:
            parts = text.split("```mermaid")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0]
                text = code_part.strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1].strip()
        
        # Remove common prefixes
        text = text.replace("mermaid\n", "")
        text = text.replace("mermaid ", "")
        
        # Ensure it starts with graph
        text = text.strip()
        if not text.startswith("graph "):
            # Try to find graph declaration
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("graph "):
                    text = "\n".join(lines[i:])
                    break
        
        # If still no graph prefix, add it
        if not text.startswith("graph "):
            text = "graph TB\n" + text
        
        return text
