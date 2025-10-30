"""
Recommendation Refinement Engine
Real-time architecture recommendation refinement based on user feedback
"""

from typing import Dict, List, Optional
import json
import structlog
import boto3
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class RefinementRequest(BaseModel):
    """User's refinement request"""
    feedback: str
    focus_area: Optional[str] = None  # "cost", "performance", "security", "reliability"
    current_architecture: Dict


class RefinementEngine:
    """
    Real-time recommendation refinement engine
    Allows users to iteratively improve architecture recommendations
    """
    
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        aws_region: str = "us-east-1"
    ):
        """
        Initialize refinement engine
        
        Args:
            model_id: Bedrock model ID
            aws_region: AWS region
        """
        self.model_id = model_id
        self.aws_region = aws_region
        
        # Initialize Bedrock client
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)
        
        logger.info("refinement_engine_initialized")
    
    async def refine(
        self,
        current_architecture: Dict,
        feedback: str,
        focus_area: Optional[str] = None
    ) -> Dict:
        """
        Refine architecture based on user feedback
        
        Args:
            current_architecture: Current architecture design
            feedback: User's feedback/request
            focus_area: Optional focus area (cost, performance, security, reliability)
            
        Returns:
            Refined architecture with changes highlighted
        """
        logger.info("refining_architecture", feedback=feedback, focus_area=focus_area)
        
        # Create refinement prompt
        prompt = self._create_refinement_prompt(
            current_architecture,
            feedback,
            focus_area
        )
        
        # Call LLM
        refined_architecture = await self._call_llm(prompt)
        
        # Parse and structure response
        result = self._parse_refinement(refined_architecture, current_architecture)
        
        logger.info("architecture_refined", changes=len(result.get("changes", [])))
        
        return result
    
    def _create_refinement_prompt(
        self,
        current_architecture: Dict,
        feedback: str,
        focus_area: Optional[str]
    ) -> str:
        """Create prompt for architecture refinement"""
        
        focus_guidance = ""
        if focus_area:
            focus_map = {
                "cost": "Focus on reducing costs while maintaining functionality. Consider serverless, spot instances, and cost-optimized services.",
                "performance": "Focus on improving performance. Consider caching, CDN, managed services with better performance, and multi-AZ deployment.",
                "security": "Focus on enhancing security. Consider encryption, WAF, security groups, IAM policies, and compliance requirements.",
                "reliability": "Focus on improving reliability. Consider multi-AZ, auto-scaling, backup strategies, and disaster recovery."
            }
            focus_guidance = f"\n\nPRIORITY FOCUS: {focus_map.get(focus_area, '')}"
        
        prompt = f"""You are an AWS Solutions Architect expert. Refine the following AWS architecture based on user feedback.

CURRENT ARCHITECTURE:
{json.dumps(current_architecture, indent=2)}

USER FEEDBACK:
{feedback}
{focus_guidance}

INSTRUCTIONS:
1. Analyze the current architecture
2. Understand the user's feedback and requirements
3. Propose specific changes to address the feedback
4. Maintain compatibility with existing requirements
5. Explain the rationale for each change
6. Provide updated cost estimation if relevant

Return your response in JSON format:
{{
  "refined_architecture": {{
    "name": "...",
    "description": "...",
    "compute_services": [...],
    "storage_services": [...],
    "database_services": [...],
    "networking_services": [...],
    "security_services": [...],
    "monitoring_services": [...],
    "other_services": [...],
    "architecture_description": "...",
    "estimated_monthly_cost": "...",
    "cost_breakdown": {{...}}
  }},
  "changes": [
    {{
      "type": "added|removed|modified",
      "service": "Service name",
      "reason": "Why this change was made",
      "impact": "Expected impact"
    }}
  ],
  "summary": "Brief summary of refinements",
  "trade_offs": "Any trade-offs made"
}}

Be specific and practical. Only suggest changes that directly address the user's feedback.
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call Bedrock LLM"""
        
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.3,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            raise
    
    def _parse_refinement(self, llm_response: str, original_architecture: Dict) -> Dict:
        """Parse LLM response into structured refinement"""
        
        try:
            # Extract JSON from response
            json_text = llm_response
            if "```json" in llm_response:
                json_text = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_text = llm_response.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            result = json.loads(json_text)
            
            # Add original for comparison
            result["original_architecture"] = original_architecture
            
            return result
            
        except Exception as e:
            logger.error("refinement_parsing_failed", error=str(e))
            
            # Return minimal result on parse failure
            return {
                "refined_architecture": original_architecture,
                "changes": [],
                "summary": "Failed to parse refinement. Please try again.",
                "trade_offs": "",
                "original_architecture": original_architecture
            }
    
    async def suggest_improvements(self, architecture: Dict) -> List[Dict]:
        """
        Suggest potential improvements to an architecture
        
        Args:
            architecture: Current architecture design
            
        Returns:
            List of improvement suggestions
        """
        logger.info("suggesting_improvements")
        
        prompt = f"""Analyze this AWS architecture and suggest 3-5 potential improvements:

ARCHITECTURE:
{json.dumps(architecture, indent=2)}

Return JSON array of suggestions:
[
  {{
    "category": "cost|performance|security|reliability|sustainability",
    "suggestion": "Specific improvement suggestion",
    "benefit": "Expected benefit",
    "effort": "low|medium|high"
  }}
]

Focus on practical, high-impact improvements.
"""
        
        response = await self._call_llm(prompt)
        
        try:
            # Extract JSON
            json_text = response
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_text = response.split("```")[1].split("```")[0].strip()
            
            suggestions = json.loads(json_text)
            return suggestions
            
        except Exception as e:
            logger.error("suggestion_parsing_failed", error=str(e))
            return []
    
    async def compare_refinements(
        self,
        original: Dict,
        refined: Dict
    ) -> Dict:
        """
        Compare original and refined architectures
        
        Args:
            original: Original architecture
            refined: Refined architecture
            
        Returns:
            Comparison results
        """
        logger.info("comparing_refinements")
        
        # Simple comparison (can be enhanced)
        differences = {
            "services_added": [],
            "services_removed": [],
            "services_modified": [],
            "cost_change": None,
            "complexity_change": None
        }
        
        # Compare services
        original_services = set(
            original.get("compute_services", []) +
            original.get("storage_services", []) +
            original.get("database_services", [])
        )
        
        refined_services = set(
            refined.get("compute_services", []) +
            refined.get("storage_services", []) +
            refined.get("database_services", [])
        )
        
        differences["services_added"] = list(refined_services - original_services)
        differences["services_removed"] = list(original_services - refined_services)
        
        # Cost comparison
        original_cost = original.get("estimated_monthly_cost", "")
        refined_cost = refined.get("estimated_monthly_cost", "")
        
        if original_cost and refined_cost:
            differences["cost_change"] = f"{original_cost} → {refined_cost}"
        
        return differences


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        engine = RefinementEngine()
        
        # Sample architecture
        current_arch = {
            "name": "Cost-Optimized",
            "compute_services": ["Lambda", "Fargate"],
            "storage_services": ["S3"],
            "database_services": ["DynamoDB"],
            "estimated_monthly_cost": "$500-1000"
        }
        
        # Refine
        result = await engine.refine(
            current_architecture=current_arch,
            feedback="I need better performance, willing to pay more",
            focus_area="performance"
        )
        
        print(f"Refined: {result['refined_architecture']['name']}")
        print(f"Changes: {len(result['changes'])}")
        print(f"Summary: {result['summary']}")
    
    asyncio.run(test())

