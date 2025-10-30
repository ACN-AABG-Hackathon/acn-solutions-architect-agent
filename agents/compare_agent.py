"""
Compare Agent - Evaluate architecture options using AWS Well-Architected Framework
Rewritten for simplicity and reliability
"""

from typing import List, Dict
from pydantic import BaseModel, Field
import json
import os
import structlog
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.prompt_utils import truncate_prompt_safely, MAX_PROMPT_LENGTH

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


class WellArchitectedScore(BaseModel):
    """Score for a Well-Architected pillar"""
    pillar: str
    score: int = Field(ge=0, le=100)
    notes: str


class OptionComparison(BaseModel):
    """Comparison results for one option"""
    option_name: str
    overall_score: int = Field(ge=0, le=100)
    pillar_scores: List[WellArchitectedScore]
    strengths: List[str]
    weaknesses: List[str]
    risk_assessment: str


class CompareAgentOutput(BaseModel):
    """Output from Compare Agent"""
    comparisons: List[OptionComparison]
    recommended_option: str
    recommendation_rationale: str


class CompareAgent:
    """
    AWS Solutions Architect Compare Agent
    Evaluates options using Well-Architected Framework
    """
    
    def __init__(self, session_manager: 'SessionManager' = None, model_id: str = None, aws_region: str = None, use_knowledge_base: bool = True):
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
            self.architecture_kb_id = os.getenv("ARCHITECTURE_KB_ID")
            if self.architecture_kb_id:
                logger.info("architecture_kb_configured", kb_id=self.architecture_kb_id)
            else:
                logger.warning("architecture_kb_not_configured")
                self.architecture_kb_id = None
        else:
            self.architecture_kb_id = None
        
        # Simple, clear instructions
        self.instructions = """You are an AWS Solutions Architect Expert specializing in comparative architecture evaluation.

Inputs

You will receive 3 design options plus optional business priorities and pillar weights.

Goal

Score relatively so differences are clear. Do not treat options independently—compare them against each other for every pillar and overall.

Pillars & Rubric (0–100 raw per pillar)

Evaluate each option against the AWS Well-Architected pillars using these sub-criteria (equal weight within pillar unless weights are provided):

Operational Excellence: IaC & automation; observability (logs/metrics/tracing); deployment strategy (blue/green, canary); runbooks & ops readiness.

Security: IAM least privilege; data protection (encryption at rest/in transit, KMS); network controls (private subnets, WAF, SGs/NACLs); detection & response.

Reliability: Multi-AZ/region; fault tolerance & graceful degradation; backups & DR (RPO/RTO); retries, throttling, quotas.

Performance Efficiency: Right-sizing & autoscaling; caching; data/store selection; latency/throughput considerations.

Cost Optimization: Demand-based scaling; cost visibility & guardrails; storage/compute efficiency; commitment/spot strategy.

Sustainability: Serverless/managed preference; utilization efficiency; data lifecycle; region & hardware efficiency.

Relative Scoring Method (to force differentiation)

Raw scoring: Score each pillar per option (0–100). Apply hard penalties for red flags (e.g., public S3, no encryption, single-AZ prod, no backup/DR): cap pillar at 60.

Normalize across options (per pillar):

Rank the three raw scores.

Map worst→65, middle→75–85, best→90–95 (choose 75–85 for middle based on closeness).

Ensure ≥6-point spread between best and worst for each pillar unless they are genuinely equivalent (then use 2–3 points spread and state why in weaknesses).

Overall score: Weighted average of normalized pillar scores (use provided pillar weights or equal weights).

Enforce unique ranks overall; if two options are within ≤1 point, break ties by business priorities (e.g., if cost is priority, higher cost score wins the tie).

Strengths/Weaknesses: Provide 3–5 concrete points per option. Avoid generic phrasing; reference specifics (e.g., “Private ALB + WAF + Shield Advanced” rather than “secure network”).

Output rules

Use the full 0–100 range after normalization.

Keep integers (no decimals).

Return JSON only in the exact schema below.

recommended_option must be one of the provided option_name values.

recommendation_rationale ≤ 120 words, pointing to the decisive pillars and trade-offs.
IMPORTANT: You MUST return ONLY valid JSON in this EXACT format:
{
  "evaluations": [
    {
      "option_name": "Cost-Optimized",
      "pillar_scores": {
        "operational_excellence": 85,
        "security": 90,
        "reliability": 85,
        "performance_efficiency": 75,
        "cost_optimization": 95,
        "sustainability": 90
      },
      "overall_score": 87,
      "strengths": [
        "Excellent cost control with pay-per-use model",
        "Strong security with fine-grained IAM",
        "High sustainability due to serverless architecture"
      ],
      "weaknesses": [
        "Cold start latency impacts",
        "Limited customization options"
      ]
    }
  ],
  "recommended_option": "Balanced",
  "recommendation_rationale": "The Balanced architecture provides the best trade-offs across all pillars..."
}

Do NOT include any text before or after the JSON. Return ONLY the JSON object."""
        
        # Initialize Strands Agent
        if Agent and STRANDS_AVAILABLE:
            try:
                # Generate unique agent ID and name to avoid conflicts
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                agent_id = f"aws_compare_agent_{unique_id}"
                agent_name = f"Compare Agent {unique_id}"
                
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
    
    async def compare_options(self, options_json: str) -> CompareAgentOutput:
        """Compare architecture options"""
        logger.info("comparing_architecture_options")
        
        # Query Knowledge Base for Well-Architected best practices
        kb_context = ""
        # MODIFIED: Query Knowledge Base via Gateway
        if self.use_knowledge_base and self.architecture_kb_id:
            try:
                from tools.gateway_client import query_knowledge_base
                import json
                
                logger.info("querying_architecture_kb_via_gateway")
                
                # Get Well-Architected Framework best practices via Gateway
                wa_query = "What are the AWS Well-Architected Framework best practices for evaluating architecture options across all six pillars?"
                wa_result = query_knowledge_base(
                    query=wa_query,
                    knowledge_base_id=self.architecture_kb_id,
                    max_results=5,
                    mode="retrieve_and_generate"
                )
                
                # Parse Lambda response
                wa_body = json.loads(wa_result["body"]) if isinstance(wa_result.get("body"), str) else wa_result
                wa_answer = wa_body.get("answer", "N/A")
                
                kb_context = f"\n\n### AWS Well-Architected Framework Best Practices\n\n{wa_answer}\n\n"
                
                logger.info("architecture_kb_query_completed_via_gateway")
            except Exception as e:
                logger.warning("architecture_kb_query_failed", error=str(e))
        
        # Build prompt with smart summarization for long inputs
        # Memory API has 10,000 character limit for search queries
        # Use shared MAX_PROMPT_LENGTH from prompt_utils
        
        # Try to parse and summarize options if too long
        import json
        try:
            options_list = json.loads(options_json)
            if isinstance(options_list, list):
                # Calculate if we need to summarize
                test_prompt = f"""{self.instructions}

### Knowledge Base Context
{kb_context}

### Architecture Options to Evaluate
{options_json}

Evaluate each option and return the JSON response."""
                
                if len(test_prompt) > MAX_PROMPT_LENGTH:
                    logger.warning("prompt_too_long_summarizing",
                                  original_length=len(test_prompt),
                                  options_count=len(options_list))
                    
                    # Summarize each option - keep only essential fields
                    summarized_options = []
                    for opt in options_list:
                        summarized = {
                            "name": opt.get("name", "Unknown"),
                            "description": opt.get("description", "")[:300],  # Limit description
                            "compute_services": opt.get("compute_services", []),
                            "storage_services": opt.get("storage_services", []),
                            "database_services": opt.get("database_services", []),
                            "networking_services": opt.get("networking_services", []),
                            "key_features": opt.get("key_features", [])[:5],  # Top 5 features
                        }
                        summarized_options.append(summarized)
                    
                    options_json = json.dumps(summarized_options, indent=2)
                    logger.info("options_summarized", new_length=len(options_json))
        except Exception as e:
            logger.warning("failed_to_summarize_options", error=str(e))
            # If summarization fails, fall back to simple truncation
            pass
        
        # Build final prompt
        prompt = f"""{self.instructions}

### Knowledge Base Context
{kb_context}

### Architecture Options to Evaluate
{options_json}

Evaluate each option and return the JSON response."""
        
        # Final safety check - if still too long, truncate using utility
        prompt = truncate_prompt_safely(
            prompt=prompt,
            max_length=MAX_PROMPT_LENGTH,
            truncation_note="[Note: Content truncated after summarization. Please reduce input size if quality is affected.]"
        )
        
        # Get response from agent
        if self.agent:
            response = self.agent(prompt)
            logger.info("agent_response_received", response_type=type(response).__name__)
            result_text = self._extract_text_from_response(response)
        else:
            result_text = await self._fallback_compare(prompt)
        
        # Parse response
        output = self._parse_response(result_text)
        logger.info("comparison_completed", comparisons_count=len(output.comparisons))
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
    
    async def _fallback_compare(self, prompt: str) -> str:
        """Fallback to direct Bedrock API call"""
        import boto3
        bedrock = boto3.client('bedrock-runtime', region_name=self.aws_region)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 6000,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = bedrock.invoke_model(modelId=self.model_id, body=json.dumps(body))
        try:
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            if content and len(content) > 0:
                return content[0].get('text', '')
            return ''
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("bedrock_response_parse_failed", error=str(e))
            return ''
    
    def _parse_response(self, text: str) -> CompareAgentOutput:
        """Parse LLM response - simplified version"""
        try:
            # Handle different response types
            if isinstance(text, dict):
                # Already a dict - check if it's Strands format
                if 'role' in text and 'content' in text:
                    logger.info("parsing_strands_format")
                    content = text['content']
                    if isinstance(content, list) and len(content) > 0:
                        if isinstance(content[0], dict) and 'text' in content[0]:
                            text = content[0]['text']
                        else:
                            text = str(content[0])
                    else:
                        text = str(content)
                else:
                    # Direct dict response
                    data = text
                    logger.info("response_is_dict")
                    return self._convert_to_output(data)
            
            # Extract JSON from text
            json_text = text
            if "```json" in text:
                json_text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_text = text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            data = json.loads(json_text)
            logger.info("json_parsed_successfully")
            
            # Convert to output
            return self._convert_to_output(data)
            
        except json.JSONDecodeError as e:
            logger.error("json_parse_failed", error=str(e), text_preview=text[:200])
            return self._create_fallback_output("Failed to parse JSON response")
        except Exception as e:
            logger.error("response_parse_failed", error=str(e), error_type=type(e).__name__)
            return self._create_fallback_output(f"Error: {str(e)}")
    
    def _convert_to_output(self, data: Dict) -> CompareAgentOutput:
        """Convert parsed data to CompareAgentOutput - simple and direct"""
        
        # Check if we have the expected format
        if "evaluations" in data:
            evaluations = data["evaluations"]
            recommended_option = data.get("recommended_option", "Unknown")
            recommendation_rationale = data.get("recommendation_rationale", "No rationale provided")
        else:
            # Try to handle other formats
            logger.warning("unexpected_format", keys=list(data.keys()))
            return self._create_fallback_output("Unexpected response format")
        
        comparisons = []
        
        # Pillar name mapping
        pillar_display_names = {
            "operational_excellence": "Operational Excellence",
            "security": "Security",
            "reliability": "Reliability",
            "performance_efficiency": "Performance Efficiency",
            "cost_optimization": "Cost Optimization",
            "sustainability": "Sustainability"
        }
        
        for eval_data in evaluations:
            option_name = eval_data.get("option_name", "Unknown")
            pillar_scores_dict = eval_data.get("pillar_scores", {})
            overall_score = eval_data.get("overall_score", 0)
            strengths = eval_data.get("strengths", [])
            weaknesses = eval_data.get("weaknesses", [])
            
            # Convert pillar scores to list
            pillar_scores = []
            for pillar_key, score in pillar_scores_dict.items():
                pillar_name = pillar_display_names.get(pillar_key, pillar_key.replace("_", " ").title())
                pillar_scores.append(
                    WellArchitectedScore(
                        pillar=pillar_name,
                        score=int(score),
                        notes=f"Score: {score}/100"
                    )
                )
            
            # Calculate overall score if not provided
            if overall_score == 0 and pillar_scores:
                overall_score = sum(ps.score for ps in pillar_scores) // len(pillar_scores)
            
            # Ensure lists
            if not isinstance(strengths, list):
                strengths = [str(strengths)]
            if not isinstance(weaknesses, list):
                weaknesses = [str(weaknesses)]
            
            # Create comparison
            comparison = OptionComparison(
                option_name=option_name,
                overall_score=int(overall_score),
                pillar_scores=pillar_scores,
                strengths=list(strengths),
                weaknesses=list(weaknesses),
                risk_assessment=f"Overall score: {int(overall_score)}/100"
            )
            comparisons.append(comparison)
        
        # Create output
        return CompareAgentOutput(
            comparisons=comparisons,
            recommended_option=recommended_option,
            recommendation_rationale=recommendation_rationale
        )
    
    def _create_fallback_output(self, error_msg: str) -> CompareAgentOutput:
        """Create fallback output when parsing fails"""
        logger.error("creating_fallback_output", error=error_msg)
        return CompareAgentOutput(
            comparisons=[],
            recommended_option="Error",
            recommendation_rationale=f"{error_msg}. Please try again."
        )