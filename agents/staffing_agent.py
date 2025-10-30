"""
Staffing Agent - Generate project staffing and timeline
"""
from pydantic import BaseModel
from typing import List, Dict
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


def clean_json_string(json_str: str) -> str:
    """
    Clean and fix common JSON formatting issues from LLM responses
    """
    import re
    
    # Remove any leading/trailing whitespace
    json_str = json_str.strip()
    
    # Fix trailing commas before closing brackets/braces
    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
    
    # Fix missing commas between object properties
    json_str = re.sub(r'"\s*\n\s*"', r'",\n"', json_str)
    
    # Fix missing commas between array elements
    json_str = re.sub(r'\]\s*\n\s*\{', r'],\n{', json_str)
    json_str = re.sub(r'\}\s*\n\s*\{', r'},\n{', json_str)
    
    # Fix missing commas after closing brackets/braces
    json_str = re.sub(r'\]\s*\[', r'],[', json_str)
    json_str = re.sub(r'\}\s*\[', r'},[', json_str)
    
    # Fix missing commas after string values before keys
    json_str = re.sub(r'"\s*\n\s*"([^"]+)"\s*:', r'",\n"\1":', json_str)
    
    # Fix missing commas after ] before "key":
    json_str = re.sub(r'\]\s*\n\s*"([^"]+)"\s*:', r'],\n"\1":', json_str)
    
    # Fix missing commas after } before "key":
    json_str = re.sub(r'\}\s*\n\s*"([^"]+)"\s*:', r'},\n"\1":', json_str)
    
    return json_str


class Role(BaseModel):
    """Team role"""
    title: str
    count: int
    skills: List[str]
    responsibilities: str


class Phase(BaseModel):
    """Project phase"""
    name: str
    duration_weeks: int
    activities: List[str]
    deliverables: List[str]


class StaffingPlan(BaseModel):
    """Staffing and timeline plan"""
    team_size: int
    roles: List[Role]
    phases: List[Phase]
    total_duration_weeks: int
    estimated_cost: str


class StaffingAgent:
    """Agent for generating project staffing plans and timelines"""
    
    def __init__(self, session_manager: 'SessionManager' = None, model_id: str = None, aws_region: str = None):
        # Read model_id from environment variable if not provided

        self.model_id = model_id or os.getenv(

            "BEDROCK_MODEL_ID",

            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

        )
        self.session_manager = session_manager
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        # Agent instructions with JSON schema (to prevent truncation)
        self.instructions = """You are an AWS project staffing expert.
Generate detailed staffing plans and project timelines for AWS implementations.

Consider:
- Required AWS skills and certifications
- Team structure and roles
- Project phases and milestones
- Realistic timelines based on complexity
- Resource allocation

You MUST respond in this exact JSON format:
{
  "team_size": 5,
  "roles": [
    {
      "title": "Solutions Architect",
      "count": 1,
      "skills": ["AWS Certified Solutions Architect", "Infrastructure Design"],
      "responsibilities": "Overall architecture design and technical leadership"
    },
    {
      "title": "DevOps Engineer",
      "count": 2,
      "skills": ["AWS CDK/CloudFormation", "CI/CD", "Terraform"],
      "responsibilities": "Infrastructure as Code, deployment automation"
    }
  ],
  "phases": [
    {
      "name": "Planning & Design",
      "duration_weeks": 2,
      "activities": ["Requirements analysis", "Architecture design"],
      "deliverables": ["Architecture diagram", "Technical specification"]
    },
    {
      "name": "Implementation",
      "duration_weeks": 4,
      "activities": ["Infrastructure setup", "Service configuration"],
      "deliverables": ["Deployed infrastructure", "Documentation"]
    }
  ],
  "total_duration_weeks": 8,
  "estimated_cost": "$50,000 - $75,000"
}

ALL fields are required. Include realistic timelines and appropriate team composition."""
        
        # Initialize Strands Agent
        if Agent and STRANDS_AVAILABLE:
            try:
                # Generate unique agent ID and name to avoid conflicts
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                agent_id = f"aws_staffing_agent_{unique_id}"
                agent_name = f"Staffing Agent {unique_id}"
                
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
    
    async def generate_plan(self, architecture: Dict) -> StaffingPlan:
        """Generate staffing and timeline plan for architecture"""
        logger.info("generating_staffing_plan", architecture_name=architecture.get("name"))
        
        prompt = self._create_prompt(architecture)
        
        # Call agent
        if self.agent:
            # Truncate prompt if needed to avoid Memory search query limit
            full_prompt = truncate_with_instructions(
                instructions=self.instructions,
                prompt=prompt,
                truncation_note="[Note: Architecture details truncated due to length.]"
            )
            
            response = self.agent(full_prompt)
            logger.info("agent_response_received", response_type=type(response).__name__)
            result_text = self._extract_text_from_response(response)
        else:
            # Fallback
            result_text = await self._fallback_generate(architecture)
        
        # Parse response
        plan = self._parse_response(result_text)
        
        logger.info("staffing_plan_generated", team_size=plan.team_size)
        
        return plan
    
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
    
    def _create_prompt(self, architecture: Dict) -> str:
        """Create prompt for staffing plan generation (schema is in instructions)"""
        
        prompt = f"""Generate a detailed staffing and timeline plan for the following AWS architecture:

Architecture: {architecture.get('name', 'Unknown')}
Description: {architecture.get('description', '')}

Services:
- Compute: {', '.join(architecture.get('compute_services', []))}
- Storage: {', '.join(architecture.get('storage_services', []))}
- Database: {', '.join(architecture.get('database_services', []))}
- Networking: {', '.join(architecture.get('networking_services', []))}
- Security: {', '.join(architecture.get('security_services', []))}
- Monitoring: {', '.join(architecture.get('monitoring_services', []))}

Generate the staffing plan in the JSON format specified in the instructions.
Include realistic timelines and appropriate team composition for the complexity of the architecture.
"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> StaffingPlan:
        """Parse LLM response into StaffingPlan"""
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            
            # Clean JSON string
            json_text = clean_json_string(json_text)
            logger.info("json_cleaned", length=len(json_text), preview=json_text[:200])
            
            # Try to parse with fallback
            try:
                data = json.loads(json_text)
                return StaffingPlan(**data)
            except json.JSONDecodeError as e:
                logger.warning("json_parse_failed_trying_repair", error=str(e), position=f"line {e.lineno} col {e.colno}")
                # Try to repair JSON
                try:
                    from json_repair import repair_json
                    repaired = repair_json(json_text)
                    data = json.loads(repaired)
                    logger.info("json_repaired_successfully")
                    return StaffingPlan(**data)
                except Exception as repair_error:
                    logger.error("json_repair_failed", error=str(repair_error))
            except Exception as e:
                logger.warning("failed_to_parse_staffing_plan", error=str(e))
        
        # Fallback plan
        return StaffingPlan(
            team_size=5,
            roles=[
                Role(
                    title="Solutions Architect",
                    count=1,
                    skills=["AWS Certified Solutions Architect"],
                    responsibilities="Architecture design and oversight"
                ),
                Role(
                    title="DevOps Engineer",
                    count=2,
                    skills=["AWS", "Terraform", "CI/CD"],
                    responsibilities="Infrastructure deployment"
                ),
                Role(
                    title="Developer",
                    count=2,
                    skills=["Python", "AWS SDK"],
                    responsibilities="Application development"
                )
            ],
            phases=[
                Phase(
                    name="Planning",
                    duration_weeks=2,
                    activities=["Requirements", "Design"],
                    deliverables=["Architecture doc"]
                ),
                Phase(
                    name="Implementation",
                    duration_weeks=6,
                    activities=["Development", "Testing"],
                    deliverables=["Deployed system"]
                )
            ],
            total_duration_weeks=8,
            estimated_cost="$50,000 - $75,000"
        )
    
    async def _fallback_generate(self, architecture: Dict) -> str:
        """Fallback staffing plan generation"""
        import boto3
        
        bedrock = boto3.client('bedrock-runtime', region_name=self.aws_region)
        
        prompt = self._create_prompt(architecture)
        full_prompt = f"{self.instructions}\n\n{prompt}"
        
        response = bedrock.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": full_prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        return (result.get('content', [{}])[0].get('text', '') if result.get('content') else '')


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = StaffingAgent()
        
        architecture = {
            "name": "Serverless Web Application",
            "description": "Scalable serverless architecture",
            "compute_services": ["Lambda", "Fargate"],
            "storage_services": ["S3"],
            "database_services": ["DynamoDB"],
            "networking_services": ["CloudFront", "API Gateway"]
        }
        
        plan = await agent.generate_plan(architecture)
        
        print(f"Team Size: {plan.team_size}")
        print(f"Duration: {plan.total_duration_weeks} weeks")
        print(f"Cost: {plan.estimated_cost}")
        print(f"\nRoles ({len(plan.roles)}):")
        for role in plan.roles:
            print(f"  - {role.count}x {role.title}")
        print(f"\nPhases ({len(plan.phases)}):")
        for phase in plan.phases:
            print(f"  - {phase.name}: {phase.duration_weeks} weeks")
    
    asyncio.run(test())

