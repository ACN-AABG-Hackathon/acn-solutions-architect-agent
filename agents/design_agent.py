"""
Design Agent - Generate AWS architecture design options
Uses Strands SDK to create 3 architecture options: Cost-Optimized, Performance-Optimized, Balanced
"""

from typing import List, Dict
from pydantic import BaseModel, Field, ConfigDict
import json
import os
import structlog
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.prompt_utils import truncate_with_instructions

try:
    from strands import Agent
    from strands.session import SessionManager
    STRANDS_AVAILABLE = True
except ImportError:
    Agent = None
    SessionManager = None
    STRANDS_AVAILABLE = False
    import warnings
    warnings.warn(
        "Strands SDK not installed. Install with: pip install strands-agents",
        ImportWarning,
        stacklevel=2
    )

logger = structlog.get_logger(__name__)


class ArchitectureOption(BaseModel):
    """Single architecture design option"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = Field(description="Option name (e.g., Cost-Optimized)")
    description: str = Field(description="Brief description of the architecture approach")
    
    # AWS Services
    compute_services: List[str] = Field(description="Compute services (e.g., Lambda, ECS, EC2)")
    storage_services: List[str] = Field(description="Storage services (e.g., S3, EFS, EBS)")
    database_services: List[str] = Field(description="Database services (e.g., RDS, DynamoDB)")
    networking_services: List[str] = Field(description="Networking services (e.g., VPC, CloudFront, API Gateway)")
    security_services: List[str] = Field(description="Security services (e.g., IAM, KMS, WAF)")
    monitoring_services: List[str] = Field(description="Monitoring services (e.g., CloudWatch, X-Ray)")
    other_services: List[str] = Field(default_factory=list, description="Other AWS services")
    
    # Architecture Details
    architecture_description: str = Field(description="Detailed architecture description")
    data_flow: str = Field(description="How data flows through the system")
    
    # Cost Estimation
    estimated_monthly_cost: str = Field(description="Estimated monthly cost (e.g., $500-1000)")
    cost_breakdown: Dict[str, str] = Field(description="Cost breakdown by service")
    
    # Pros and Cons
    pros: List[str] = Field(description="Advantages of this option")
    cons: List[str] = Field(description="Disadvantages of this option")
    
    # Well-Architected Alignment
    operational_excellence_notes: str = Field(description="Operational excellence considerations")
    security_notes: str = Field(description="Security considerations")
    reliability_notes: str = Field(description="Reliability considerations")
    performance_notes: str = Field(description="Performance considerations")
    cost_optimization_notes: str = Field(description="Cost optimization considerations")
    sustainability_notes: str = Field(default="", description="Sustainability considerations")


class DesignAgentOutput(BaseModel):
    """Output from Design Agent"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    options: List[ArchitectureOption] = Field(description="List of 3 architecture options")


class DesignAgent:
    """
    AWS Solutions Architect Design Agent
    Generates 3 architecture options based on requirements
    """
    
    def __init__(
        self,
        session_manager: 'SessionManager' = None,
        model_id: str = None,
        aws_region: str = None,
        use_knowledge_base: bool = True
    ):
        """
        Initialize Design Agent
        
        Args:
            model_id: Bedrock model ID
            use_knowledge_base: Whether to use Knowledge Base for RAG
        """
        # Read model_id from environment variable if not provided
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID",
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.session_manager = session_manager
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.use_knowledge_base = use_knowledge_base
        
        # MODIFIED: Store KB ID for Gateway queries instead of initializing local KB
        self.use_knowledge_base = use_knowledge_base
        if use_knowledge_base:
            self.design_kb_id = os.getenv("DESIGN_KB_ID")
            if self.design_kb_id:
                logger.info("design_kb_configured", kb_id=self.design_kb_id)
            else:
                logger.warning("design_kb_not_configured")
                self.design_kb_id = None
        else:
            self.design_kb_id = None
        
        # Agent instructions with JSON schema (to prevent truncation)
        self.instructions = """You are an expert AWS Solutions Architect with deep knowledge of AWS services, 
best practices, and the Well-Architected Framework.

Your task is to analyze system requirements and generate 3 distinct AWS architecture design options:

1. **Cost-Optimized**: Minimize costs while meeting requirements
2. **Performance-Optimized**: Maximize performance and minimize latency
3. **Balanced**: Balance between cost and performance

You MUST respond in this exact JSON format:
{
  "options": [
    {
      "name": "Cost-Optimized",
      "description": "Brief description",
      "compute_services": ["Lambda", "Fargate"],
      "storage_services": ["S3"],
      "database_services": ["DynamoDB"],
      "networking_services": ["API Gateway", "VPC"],
      "security_services": ["IAM", "KMS"],
      "monitoring_services": ["CloudWatch"],
      "other_services": [],
      "architecture_description": "Detailed architecture description",
      "data_flow": "How data flows through the system",
      "estimated_monthly_cost": "$500-1000",
      "cost_breakdown": {"compute": "$300", "storage": "$100"},
      "pros": ["Low cost", "Serverless"],
      "cons": ["Cold starts"],
      "operational_excellence_notes": "How this supports operational excellence",
      "security_notes": "Security considerations",
      "reliability_notes": "Reliability considerations",
      "performance_notes": "Performance considerations",
      "cost_optimization_notes": "Cost optimization approach",
      "sustainability_notes": "Sustainability considerations"
    }
    // ... repeat for Performance-Optimized and Balanced
  ]
}

ALL fields are required. Do not omit any field.
"""
        
        # Initialize Strands Agent
        if Agent and STRANDS_AVAILABLE:
            try:
                # Generate unique agent ID and name to avoid conflicts
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                agent_id = f"aws_design_agent_{unique_id}"
                agent_name = f"AWS Design Agent {unique_id}"
                
                self.agent = Agent(
                    agent_id=agent_id,
                    name=agent_name,
                    model=self.model_id,
                    session_manager=session_manager
                )
                logger.info("Strands Agent initialized successfully", agent_id=agent_id, agent_name=agent_name)
            except Exception as e:
                self.agent = None
                logger.warning(f"Failed to initialize Strands Agent: {e}")
        else:
            self.agent = None
            logger.warning("Strands Agent not available - SDK not installed")
    
    async def generate_options(self, requirements: str) -> DesignAgentOutput:
        """
        Generate 3 architecture options based on requirements
        
        Args:
            requirements: System requirements (markdown format)
            
        Returns:
            DesignAgentOutput with 3 options
        """
        logger.info("generating_architecture_options")
        
        # Validate requirements parameter
        if not requirements or requirements is None:
            logger.error("requirements_is_none_or_empty")
            raise ValueError("Requirements parameter cannot be None or empty")
        
        # MODIFIED: Query Knowledge Base via Gateway
        kb_context = ""
        if self.use_knowledge_base and self.design_kb_id:
            try:
                from tools.gateway_client import query_knowledge_base
                
                logger.info("querying_design_kb_via_gateway", 
                           requirements_length=len(requirements),
                           requirements_preview=requirements[:200] + "..." if len(requirements) > 200 else requirements)
                
                # Get service recommendations via Gateway
                service_query = f"Recommend AWS services for these requirements: {requirements[:1000]}"
                service_result = query_knowledge_base(
                    query=service_query,
                    knowledge_base_id=self.design_kb_id,
                    max_results=5,
                    mode="retrieve_and_generate"
                )
                
                # Parse Lambda response
                service_body = json.loads(service_result["body"]) if isinstance(service_result.get("body"), str) else service_result
                service_answer = service_body.get("answer", "N/A")
                
                # Get architecture patterns via Gateway
                req_sample = requirements[:500] if requirements and len(requirements) > 500 else requirements
                patterns_query = f"What are the recommended AWS architecture patterns for: {req_sample}"
                patterns_result = query_knowledge_base(
                    query=patterns_query,
                    knowledge_base_id=self.design_kb_id,
                    max_results=3,
                    mode="retrieve_and_generate"
                )
                
                # Parse Lambda response
                patterns_body = json.loads(patterns_result["body"]) if isinstance(patterns_result.get("body"), str) else patterns_result
                patterns_answer = patterns_body.get("answer", "N/A")
                
                kb_context = f"""\n\n### Knowledge Base Insights\n\n**AWS Service Recommendations:**\n{service_answer}\n\n**Architecture Patterns:**\n{patterns_answer}\n\n"""
                
                logger.info("design_kb_query_completed_via_gateway")
            except Exception as e:
                logger.warning("design_kb_query_failed", error=str(e))
        
        # Create prompt with KB context
        prompt = self._create_prompt(requirements, kb_context)
        
        # Call agent
        if self.agent:
            # Truncate prompt if needed to avoid Memory search query limit (10,000 chars)
            # Strands Agent automatically searches Memory with the prompt
            full_prompt = truncate_with_instructions(
                instructions=self.instructions,
                prompt=prompt,
                truncation_note="[Note: Requirements truncated due to length. Focus on key requirements above.]"
            )
            
            response = self.agent(full_prompt)
            logger.info("agent_response_received", response_type=type(response).__name__)
            result_text = self._extract_text_from_response(response)
        else:
            # Fallback if Strands not available
            result_text = await self._fallback_generate(prompt)
        
        # Parse response
        output = self._parse_response(result_text)
        
        logger.info("architecture_options_generated", count=len(output.options))
        
        return output
    
    def _extract_text_from_response(self, response) -> str:
        """Extract text from various response formats"""
        
        logger.info("extracting_text_from_response", response_type=type(response).__name__)
        
        # Handle string response
        if isinstance(response, str):
            logger.info("response_is_string")
            return response
        
        # Handle dict response
        if isinstance(response, dict):
            logger.info("response_is_dict", keys=list(response.keys()))
            
            # Strands format: {'role': 'assistant', 'content': [...]}
            if 'role' in response and 'content' in response:
                content = response['content']
                logger.info("strands_format_detected", content_type=type(content).__name__)
                
                # Content is a list
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    logger.info("content_is_list", first_item_type=type(first_item).__name__)
                    
                    # First item is dict with 'text'
                    if isinstance(first_item, dict) and 'text' in first_item:
                        text = first_item['text']
                        logger.info("extracted_text_from_dict", length=len(text), preview=text[:100])
                        return text
                    else:
                        logger.warning("first_item_not_dict_with_text", first_item=str(first_item)[:100])
                        return str(first_item)
                
                # Content is string
                elif isinstance(content, str):
                    logger.info("content_is_string")
                    return content
                
                # Content is something else
                else:
                    logger.warning("content_unknown_type", content_type=type(content).__name__)
                    return str(content)
            
            # Direct message format: {'message': '...'}
            elif 'message' in response:
                logger.info("message_format_detected")
                return str(response['message'])
            
            # Unknown dict format
            else:
                logger.warning("unknown_dict_response_format", keys=list(response.keys()), response_preview=str(response)[:200])
                return str(response)
        
        # Handle object with message attribute
        if hasattr(response, 'message'):
            logger.info("response_has_message_attribute")
            message = response.message
            # message might be a dict, recursively extract
            if isinstance(message, dict):
                logger.info("message_is_dict", keys=list(message.keys()))
                return self._extract_text_from_response(message)
            else:
                return str(message)
        
        # Fallback: convert to string
        logger.warning("unknown_response_format_fallback", response_type=type(response).__name__)
        return str(response)
    
    def _create_prompt(self, requirements: str, kb_context: str = "") -> str:
        """Create prompt for architecture generation (schema is in instructions)"""
        
        prompt = f"""Based on the following system requirements, generate 3 AWS architecture design options:{kb_context}

Requirements:
{requirements}

Generate the 3 options (Cost-Optimized, Performance-Optimized, Balanced) in the JSON format specified in the instructions.
Be specific with AWS service names and realistic cost estimates.
"""
        return prompt
    
    async def _fallback_generate(self, prompt: str) -> str:
        """Fallback generation using Bedrock directly"""
        import boto3
        
        bedrock_client = boto3.client('bedrock-runtime', region_name=self.aws_region)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return (response_body.get('content', [{}])[0].get('text', '') if response_body.get('content') else '')
    
    def _parse_response(self, response_text) -> DesignAgentOutput:
        """Parse agent response into structured output"""
        
        try:
            # Check if response is already a dict
            if isinstance(response_text, dict):
                logger.info("response_already_parsed_as_dict")
                
                # Check if it's a Bedrock response structure with 'role' and 'content'
                if 'role' in response_text and 'content' in response_text:
                    logger.info("extracting_from_bedrock_response_structure")
                    # Extract text from content array
                    content = response_text['content']
                    if isinstance(content, list) and len(content) > 0:
                        json_text = content[0].get('text', '')
                    else:
                        json_text = str(content)
                    
                    # Extract JSON from markdown code block
                    if "```json" in json_text:
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_text:
                        json_text = json_text.split("```")[1].split("```")[0].strip()
                    
                    # Parse JSON
                    data = json.loads(json_text)
                else:
                    # Direct dict with options
                    data = response_text
            else:
                # Extract JSON from string response
                json_text = str(response_text)
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                data = json.loads(json_text)
            
            # Create output object
            output = DesignAgentOutput(**data)
            
            return output
            
        except Exception as e:
            response_preview = str(response_text)[:500] if response_text else "None"
            logger.error("response_parsing_failed", error=str(e), response=response_preview, response_type=type(response_text).__name__)
            
            # Return minimal output on parse failure
            return DesignAgentOutput(
                options=[
                    ArchitectureOption(
                        name="Error",
                        description="Failed to generate architecture options",
                        compute_services=[],
                        storage_services=[],
                        database_services=[],
                        networking_services=[],
                        security_services=[],
                        monitoring_services=[],
                        architecture_description="Error occurred during generation",
                        data_flow="N/A",
                        estimated_monthly_cost="N/A",
                        cost_breakdown={},
                        pros=[],
                        cons=["Generation failed"],
                        operational_excellence_notes="",
                        security_notes="",
                        reliability_notes="",
                        performance_notes="",
                        cost_optimization_notes=""
                    )
                ]
            )
    
    def to_markdown(self, output: DesignAgentOutput) -> str:
        """Convert output to markdown format"""
        
        md = "# AWS Architecture Design Options\n\n"
        
        for i, option in enumerate(output.options, 1):
            md += f"## Option {i}: {option.name}\n\n"
            md += f"**Description**: {option.description}\n\n"
            
            md += "### AWS Services\n\n"
            md += f"- **Compute**: {', '.join(option.compute_services)}\n"
            md += f"- **Storage**: {', '.join(option.storage_services)}\n"
            md += f"- **Database**: {', '.join(option.database_services)}\n"
            md += f"- **Networking**: {', '.join(option.networking_services)}\n"
            md += f"- **Security**: {', '.join(option.security_services)}\n"
            md += f"- **Monitoring**: {', '.join(option.monitoring_services)}\n"
            if option.other_services:
                md += f"- **Other**: {', '.join(option.other_services)}\n"
            md += "\n"
            
            md += "### Architecture\n\n"
            md += f"{option.architecture_description}\n\n"
            
            md += "### Data Flow\n\n"
            md += f"{option.data_flow}\n\n"
            
            md += "### Cost Estimation\n\n"
            md += f"**Estimated Monthly Cost**: {option.estimated_monthly_cost}\n\n"
            md += "**Cost Breakdown**:\n"
            for service, cost in option.cost_breakdown.items():
                md += f"- {service.title()}: {cost}\n"
            md += "\n"
            
            md += "### Pros\n\n"
            for pro in option.pros:
                md += f"- {pro}\n"
            md += "\n"
            
            md += "### Cons\n\n"
            for con in option.cons:
                md += f"- {con}\n"
            md += "\n"
            
            md += "### Well-Architected Framework Alignment\n\n"
            md += f"**Operational Excellence**: {option.operational_excellence_notes}\n\n"
            md += f"**Security**: {option.security_notes}\n\n"
            md += f"**Reliability**: {option.reliability_notes}\n\n"
            md += f"**Performance Efficiency**: {option.performance_notes}\n\n"
            md += f"**Cost Optimization**: {option.cost_optimization_notes}\n\n"
            if option.sustainability_notes:
                md += f"**Sustainability**: {option.sustainability_notes}\n\n"
            
            md += "---\n\n"
        
        md += "## Next Steps\n\n"
        md += "Use the Compare Agent to analyze these options and get a recommendation based on your priorities.\n"
        
        return md


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = DesignAgent()
        
        requirements = """
        # System Requirements
        
        ## Project Summary
        E-commerce web application with 10,000 concurrent users
        
        ## Performance Requirements
        - Latency: < 200ms
        - Throughput: 1,000 requests/sec
        
        ## Scalability Requirements
        - Users: 10,000 concurrent, 100,000 daily
        - Growth: 50% year-over-year
        """
        
        output = await agent.generate_options(requirements)
        print(agent.to_markdown(output))
    
    asyncio.run(test())