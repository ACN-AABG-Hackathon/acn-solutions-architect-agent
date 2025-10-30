"""
Supervisor Agent - Orchestrate multi-agent workflow
"""
from typing import Dict, Any
import structlog

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


class SupervisorAgent:
    """Supervisor agent that orchestrates the multi-agent workflow"""
    
    def __init__(self, session_manager: 'SessionManager' = None, model_id: str = None):
        # Read model_id from environment variable if not provided

        self.model_id = model_id or os.getenv(

            "BEDROCK_MODEL_ID",

            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

        )
        self.session_manager = session_manager
        self.instructions = """You are the AWS Solutions Architect Supervisor.

Your role is to orchestrate the multi-agent workflow:

1. Extract requirements from document
2. Generate 3 architecture options (Design Agent)
3. Compare and evaluate options (Compare Agent)
4. Wait for user selection
5. Generate architecture diagram (Diagram Agent)
6. Create staffing and timeline plan (Staffing Agent)
7. Compile final comprehensive report

Coordinate between agents, manage state, and ensure smooth workflow execution."""
        
        # Initialize Strands Agent
        if Agent and STRANDS_AVAILABLE:
            try:
                # Generate unique agent ID and name to avoid conflicts
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                agent_id = f"aws_supervisor_agent_{unique_id}"
                agent_name = f"Supervisor Agent {unique_id}"
                
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
    
    async def orchestrate(self, requirements: str) -> Dict[str, Any]:
        """Orchestrate the complete workflow"""
        logger.info("supervisor_orchestrating_workflow")
        
        # This is a placeholder - actual orchestration is done by LangGraph workflow
        # The supervisor agent can be used for decision-making and coordination
        
        return {
            "status": "orchestrating",
            "requirements": requirements,
            "next_step": "generate_design_options"
        }
    
    async def decide_next_step(self, current_state: Dict[str, Any]) -> str:
        """Decide the next step in the workflow based on current state"""
        
        if not current_state.get("requirements"):
            return "extract_requirements"
        elif not current_state.get("design_options"):
            return "generate_design_options"
        elif not current_state.get("comparison"):
            return "compare_options"
        elif not current_state.get("selected_option"):
            return "wait_for_user_selection"
        elif not current_state.get("diagram"):
            return "generate_diagram"
        elif not current_state.get("staffing_plan"):
            return "generate_staffing_plan"
        else:
            return "compile_final_report"
    
    async def validate_workflow_state(self, state: Dict[str, Any]) -> Dict[str, bool]:
        """Validate the current workflow state"""
        
        validation = {
            "requirements_extracted": bool(state.get("requirements")),
            "options_generated": bool(state.get("design_options")),
            "options_compared": bool(state.get("comparison")),
            "option_selected": bool(state.get("selected_option")),
            "diagram_generated": bool(state.get("diagram")),
            "staffing_plan_created": bool(state.get("staffing_plan")),
            "workflow_complete": all([
                state.get("requirements"),
                state.get("design_options"),
                state.get("comparison"),
                state.get("selected_option"),
                state.get("diagram"),
                state.get("staffing_plan")
            ])
        }
        
        logger.info("workflow_state_validated", validation=validation)
        
        return validation


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        supervisor = SupervisorAgent()
        
        # Test orchestration
        result = await supervisor.orchestrate("Build a serverless web application")
        print(f"Orchestration result: {result}")
        
        # Test state validation
        test_state = {
            "requirements": "Some requirements",
            "design_options": ["option1", "option2", "option3"],
            "comparison": {"recommended": "option2"}
        }
        
        validation = await supervisor.validate_workflow_state(test_state)
        print(f"\nWorkflow validation: {validation}")
        
        # Test next step decision
        next_step = await supervisor.decide_next_step(test_state)
        print(f"\nNext step: {next_step}")
    
    asyncio.run(test())

