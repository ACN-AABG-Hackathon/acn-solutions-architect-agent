"""
LangGraph Workflow Orchestrator with AgentCore Memory
Manages the state and flow of the multi-agent architecture design process
"""

from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
import structlog
import json

from tools.memory import get_memory_id, create_session_manager

logger = structlog.get_logger(__name__)


class WorkflowState(TypedDict):
    """
    Simplified state object for the workflow, relying on AgentCore Memory for persistence.
    Only essential identifiers and control flow data are kept in the graph state.
    """
    # Session identifiers
    session_id: str
    actor_id: str
    memory_id: str
    
    # Initial input (not persisted to memory, only used for first step)
    document_text: Optional[str]
    document_metadata: Optional[Dict]
    
    # Workflow control
    current_step: str
    errors: List[str]
    messages: List[str]
    
    # User interaction flags
    user_selection_made: bool
    refinement_requested: bool


class ArchitectureWorkflowOrchestrator:
    """
    LangGraph-based workflow orchestrator using AgentCore Memory for state persistence
    """
    
    def __init__(self):
        """Initialize the workflow orchestrator and get the memory resource ID"""
        try:
            self.memory_id = get_memory_id()
            logger.info("workflow_orchestrator_initialized", memory_id=self.memory_id)
        except ValueError as e:
            logger.error("memory_id_not_configured", error=str(e))
            raise
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("extract_requirements", self._extract_requirements)
        workflow.add_node("generate_designs", self._generate_designs)
        workflow.add_node("compare_options", self._compare_options)
        workflow.add_node("wait_for_selection", self._wait_for_selection)
        workflow.add_node("apply_refinements", self._apply_refinements)
        workflow.add_node("generate_diagram", self._generate_diagram)
        workflow.add_node("generate_staffing", self._generate_staffing)
        workflow.add_node("finalize", self._finalize)
        
        # Define edges
        workflow.set_entry_point("extract_requirements")
        workflow.add_edge("extract_requirements", "generate_designs")
        workflow.add_edge("generate_designs", "compare_options")
        workflow.add_edge("compare_options", "wait_for_selection")
        
        # Conditional edge for refinement
        workflow.add_conditional_edges(
            "wait_for_selection",
            self._should_refine,
            {
                "refine": "apply_refinements",
                "proceed": "generate_diagram"
            }
        )
        
        workflow.add_edge("apply_refinements", "wait_for_selection")
        workflow.add_edge("generate_diagram", "generate_staffing")
        workflow.add_edge("generate_staffing", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def _extract_requirements(self, state: WorkflowState) -> WorkflowState:
        """Step 1: Extract requirements from document"""
        logger.info("workflow_step", step="extract_requirements")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            # MODIFIED: Use Gateway for requirements extraction
            from tools.gateway_client import extract_requirements as gateway_extract_requirements
            from tools import RequirementsExtractor, SystemRequirements
            
            # Call Gateway tool
            result = gateway_extract_requirements(
                document_text=state["document_text"],
                session_id=state["session_id"]
            )
            
            # Parse Lambda response
            response_body = json.loads(result["body"]) if isinstance(result.get("body"), str) else result
            requirements_dict = response_body.get("requirements")
            
            # Convert to SystemRequirements object for compatibility
            requirements = SystemRequirements(**requirements_dict)
            
            # Save to AgentCore Memory
            await session_manager.save("requirements", requirements.dict())
            
            # Generate markdown using local extractor (for formatting only)
            from tools import SystemRequirements, format_requirements_to_markdown
            await session_manager.save("requirements_markdown", format_requirements_to_markdown(requirements))
            
            state["current_step"] = "extract_requirements"
            state["messages"].append("Requirements extracted via Gateway and saved to memory")
            
        except Exception as e:
            logger.error("requirements_extraction_failed", error=str(e))
            state["errors"].append(f"Requirements extraction failed: {str(e)}")
        
        return state
    
    async def _generate_designs(self, state: WorkflowState) -> WorkflowState:
        """Step 2: Generate architecture options"""
        logger.info("workflow_step", step="generate_designs")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            from agents import DesignAgent
            
            # Load requirements from memory
            requirements_markdown = await session_manager.load("requirements_markdown")
            
            # Create agent with session_manager
            agent = DesignAgent(session_manager=session_manager)
            design_output = await agent.generate_options(requirements_markdown)
            
            # Save to memory
            options_list = [opt.dict() for opt in design_output.options]
            await session_manager.save("design_options", options_list)
            await session_manager.save("design_options_json", json.dumps(options_list, indent=2))
            
            state["current_step"] = "generate_designs"
            state["messages"].append(f"Generated {len(options_list)} architecture options")
            
        except Exception as e:
            logger.error("design_generation_failed", error=str(e))
            state["errors"].append(f"Design generation failed: {str(e)}")
        
        return state
    
    async def _compare_options(self, state: WorkflowState) -> WorkflowState:
        """Step 3: Compare and evaluate options"""
        logger.info("workflow_step", step="compare_options")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            from agents import CompareAgent
            
            # Load design options from memory
            design_options_json = await session_manager.load("design_options_json")
            
            # Create agent with session_manager
            agent = CompareAgent(session_manager=session_manager)
            comparison = await agent.compare_options(design_options_json)
            
            # Save to memory
            await session_manager.save("comparison_results", comparison.dict())
            await session_manager.save("recommended_option", comparison.recommended_option)
            
            state["current_step"] = "compare_options"
            state["messages"].append(f"Recommended: {comparison.recommended_option}")
            
        except Exception as e:
            logger.error("comparison_failed", error=str(e))
            state["errors"].append(f"Comparison failed: {str(e)}")
        
        return state
    
    async def _wait_for_selection(self, state: WorkflowState) -> WorkflowState:
        """Step 4: Wait for user selection (or use recommended option)"""
        logger.info("workflow_step", step="wait_for_selection")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            # Check if user has made a selection
            selected_option = await session_manager.load("selected_option")
            
            if not selected_option:
                # Use recommended option by default
                recommended = await session_manager.load("recommended_option")
                await session_manager.save("selected_option", recommended)
                selected_option = recommended
                state["messages"].append(f"Auto-selected recommended option: {selected_option}")
            
            # Load the full option data
            design_options = await session_manager.load("design_options")
            selected_option_data = next(
                (opt for opt in design_options if opt["name"] == selected_option),
                None
            )
            
            if selected_option_data:
                await session_manager.save("selected_option_data", selected_option_data)
            
            state["current_step"] = "wait_for_selection"
            state["user_selection_made"] = True
            
        except Exception as e:
            logger.error("selection_failed", error=str(e))
            state["errors"].append(f"Selection failed: {str(e)}")
        
        return state
    
    def _should_refine(self, state: WorkflowState) -> str:
        """Determine if refinement is needed"""
        if state.get("refinement_requested", False):
            return "refine"
        return "proceed"
    
    async def _apply_refinements(self, state: WorkflowState) -> WorkflowState:
        """Step 5: Apply user-requested refinements"""
        logger.info("workflow_step", step="apply_refinements")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            from tools import RefinementEngine
            
            # Load refinement request and selected option from memory
            refinement_request = await session_manager.load("refinement_request")
            selected_option_data = await session_manager.load("selected_option_data")
            
            if refinement_request and not refinement_request.get("processed"):
                engine = RefinementEngine()
                result = await engine.refine(
                    selected_option_data,
                    refinement_request["feedback"],
                    refinement_request.get("focus_area")
                )
                
                # Update selected option with refined version
                await session_manager.save("selected_option_data", result["refined_architecture"])
                await session_manager.save("refinement_result", result)
                
                # Mark as processed
                refinement_request["processed"] = True
                await session_manager.save("refinement_request", refinement_request)
                
                state["messages"].append(f"Refinement applied: {result['summary']}")
                state["refinement_requested"] = False
            
            state["current_step"] = "apply_refinements"
            
        except Exception as e:
            logger.error("refinement_failed", error=str(e))
            state["errors"].append(f"Refinement failed: {str(e)}")
        
        return state
    
    async def _generate_diagram(self, state: WorkflowState) -> WorkflowState:
        """Step 6: Generate architecture diagram"""
        logger.info("workflow_step", step="generate_diagram")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            from agents import DiagramAgent
            from tools import DiagramRenderer
            
            # Load selected option from memory
            selected_option_data = await session_manager.load("selected_option_data")
            
            # Create agent with session_manager
            agent = DiagramAgent(session_manager=session_manager)
            mermaid_code = await agent.generate_diagram(json.dumps(selected_option_data))
            
            # Save diagram code to memory
            await session_manager.save("diagram_code", mermaid_code)
            
            # Try to render diagram
            try:
                renderer = DiagramRenderer()
                selected_option = await session_manager.load("selected_option")
                diagram_path = renderer.create_aws_architecture_diagram(
                    selected_option_data,
                    f"{selected_option.replace(' ', '_').lower()}_diagram.png"
                )
                await session_manager.save("diagram_path", diagram_path)
            except Exception as render_error:
                logger.warning("diagram_rendering_failed", error=str(render_error))
            
            state["current_step"] = "generate_diagram"
            state["messages"].append("Diagram generated")
            
        except Exception as e:
            logger.error("diagram_generation_failed", error=str(e))
            state["errors"].append(f"Diagram generation failed: {str(e)}")
        
        return state
    
    async def _generate_staffing(self, state: WorkflowState) -> WorkflowState:
        """Step 7: Generate staffing and timeline plan"""
        logger.info("workflow_step", step="generate_staffing")
        session_manager = create_session_manager(state["memory_id"], state["session_id"], state["actor_id"])
        
        try:
            from agents import StaffingAgent
            
            # Load selected option from memory
            selected_option_data = await session_manager.load("selected_option_data")
            
            # Create agent with session_manager
            agent = StaffingAgent(session_manager=session_manager)
            staffing_plan = await agent.generate_plan(json.dumps(selected_option_data))
            
            # Save to memory
            await session_manager.save("staffing_plan", staffing_plan.dict() if hasattr(staffing_plan, 'dict') else staffing_plan)
            
            state["current_step"] = "generate_staffing"
            state["messages"].append("Staffing plan generated")
            
        except Exception as e:
            logger.error("staffing_generation_failed", error=str(e))
            state["errors"].append(f"Staffing generation failed: {str(e)}")
        
        return state
    
    async def _finalize(self, state: WorkflowState) -> WorkflowState:
        """Step 8: Finalize workflow"""
        logger.info("workflow_step", step="finalize")
        
        state["current_step"] = "finalize"
        state["messages"].append("Workflow completed successfully")
        
        return state
    
    async def run(
        self, 
        document_text: str, 
        session_id: str, 
        actor_id: str,
        document_metadata: Optional[Dict] = None
    ) -> WorkflowState:
        """
        Run the complete workflow with AgentCore Memory persistence
        
        Args:
            document_text: The input requirements document text
            session_id: Unique session identifier
            actor_id: Unique user/actor identifier
            document_metadata: Optional metadata about the document
            
        Returns:
            Final workflow state
        """
        initial_state: WorkflowState = {
            "session_id": session_id,
            "actor_id": actor_id,
            "memory_id": self.memory_id,
            "document_text": document_text,
            "document_metadata": document_metadata,
            "current_step": "start",
            "errors": [],
            "messages": [],
            "user_selection_made": False,
            "refinement_requested": False,
        }
        
        return await self.graph.ainvoke(initial_state)

