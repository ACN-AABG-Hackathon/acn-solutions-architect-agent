"""Enhanced Streamlit UI for AWS Solutions Architect Agent
Includes: Interactive Document Querying, Real-time Refinement, Diagram Generation
"""
import streamlit as st
import asyncio
import os
import sys
from pathlib import Path
import json
import tempfile
import structlog
import boto3

# Load environment variables from .env file or Streamlit secrets
try:
    # Try Streamlit secrets first (for Streamlit Cloud)
    if hasattr(st, 'secrets') and len(st.secrets) > 0:
        print("✅ Using Streamlit secrets")
        # Streamlit secrets are automatically available as environment variables
    else:
        # Fallback to .env file for local development
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment variables from {env_path}")
        else:
            print(f"⚠️  .env file not found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables only")

# Add current directory to path (for module imports)
sys.path.insert(0, str(Path(__file__).parent))

from auth import CognitoAuth, StreamlitAuth

from tools import (
    S3Manager, DocumentRAG, RefinementEngine
)

from tools.memory import create_session_manager
from agents import DesignAgent, CompareAgent, DiagramAgent, StaffingAgent

# Initialize logger
logger = structlog.get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="AWS Solutions Architect Agent",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- AWS Cognito Authentication Setup ---
@st.cache_resource
def get_cognito_auth():
    """Initialize Cognito authentication (cached)"""
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
    client_id = os.getenv("COGNITO_CLIENT_ID")
    client_secret = os.getenv("COGNITO_CLIENT_SECRET")  # Optional
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not user_pool_id or not client_id:
        st.error("⚠️ Cognito configuration missing. Please set COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID in .env")
        st.stop()
    
    return CognitoAuth(
        user_pool_id=user_pool_id,
        client_id=client_id,
        client_secret=client_secret,
        region=region
    )
# Initialize authentication
cognito_auth = get_cognito_auth()
streamlit_auth = StreamlitAuth(cognito_auth)
# --- Authentication Guard ---
# This will show login page if not authenticated
streamlit_auth.require_auth()
# If we reach here, user is authenticated
# Continue with the rest of the application

# --- Environment Variable Check ---
if not os.getenv("AGENTCORE_MEMORY_ID"):
    st.error("⚠️ AGENTCORE_MEMORY_ID environment variable is not set.")
    st.info("Please create a Memory resource in AWS Bedrock Console and set the ID in your .env file.")
    st.stop()

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #FF9900;
    font-weight: bold;
    margin-bottom: 1rem;
}
.sub-header {
    font-size: 1.5rem;
    color: #232F3E;
    margin-top: 2rem;
    margin-bottom: 1rem;
}
.stButton>button {
    background-color: #FF9900;
    color: white;
    font-weight: bold;
}
.chat-message {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
}
.user-message {
    background-color: #E8F4F8;
}
.assistant-message {
    background-color: #F0F0F0;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
# --- Session Management for AgentCore Memory ---
from datetime import datetime
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if 'actor_id' not in st.session_state:
    st.session_state.actor_id = streamlit_auth.get_username()

if 'requirements' not in st.session_state:
    st.session_state.requirements = None
if 'design_options' not in st.session_state:
    st.session_state.design_options = None
if 'comparison' not in st.session_state:
    st.session_state.comparison = None
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None
if 'diagram_path' not in st.session_state:
    st.session_state.diagram_path = None
if 'diagram_s3_url' not in st.session_state:
    st.session_state.diagram_s3_url = None
if 'diagram_s3_key' not in st.session_state:
    st.session_state.diagram_s3_key = None
if 'mermaid_code' not in st.session_state:
    st.session_state.mermaid_code = None
if 'staffing_plan' not in st.session_state:
    st.session_state.staffing_plan = None
if 'rag_system' not in st.session_state:
    st.session_state.rag_system = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'refinement_history' not in st.session_state:
    st.session_state.refinement_history = []

# --- Create separate session_managers for each agent ---
# AgentCore限制: 每个session只能有一个Agent
# 因此为每个Agent创建独立的session_manager

def get_agent_session_manager(agent_type: str):
    """Get or create session_manager for specific agent type"""
    session_key = f'session_manager_{agent_type}'
    
    if session_key not in st.session_state:
        memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        if memory_id:
            # Create unique session_id for this agent
            agent_session_id = f"{st.session_state.session_id}_{agent_type}"
            st.session_state[session_key] = create_session_manager(
                memory_id=memory_id,
                session_id=agent_session_id,
                actor_id=st.session_state.actor_id
            )
        else:
            st.session_state[session_key] = None
    
    return st.session_state[session_key]

# Header
st.markdown('<div class="main-header">☁️ AWS Solutions Architect Agent</div>', unsafe_allow_html=True)
st.markdown("**Multi-Agent System with Interactive Querying & Real-time Refinement**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    aws_region = st.selectbox(
        "AWS Region",
        ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
        index=0
    )
    
    s3_bucket = st.text_input(
        "S3 Bucket Name",
        value=os.getenv("S3_BUCKET_NAME", ""),
        help="S3 bucket for document storage"
    )
    
    model_id = st.selectbox(
        "Bedrock Model",
        ["us.anthropic.claude-3-5-sonnet-20241022-v2:0", "us.anthropic.claude-haiku-4-5-20251001-v1:0"],
        index=0
    )
    
    
    st.divider()
    st.header("🔐 Session Info")
    st.caption(f"Session: {st.session_state.session_id}")
    st.caption(f"User: {st.session_state.actor_id}")
    st.info("Each session has persistent memory across interactions.")
    
    st.divider()
    st.header("📊 Workflow Status")
    status_placeholder = st.empty()
    
    # Progress tracker
    st.header("✅ Progress")
    progress_items = {
        "Document Uploaded": st.session_state.requirements is not None,
        "Requirements Extracted": st.session_state.requirements is not None,
        "Options Generated": st.session_state.design_options is not None,
        "Comparison Done": st.session_state.comparison is not None,
        "Option Selected": st.session_state.selected_option is not None,
        "Diagram Generated": st.session_state.diagram_path is not None,
    }
    
    for item, done in progress_items.items():
        if done:
            st.success(f"✅ {item}")
        else:
            st.info(f"⏳ {item}")

# Main content - Enhanced with new tabs
tabs = st.tabs([
    "📄 Upload & Query",
    "📋 Requirements",
    "🏗️ Design Options",
    "🔄 Refine Architecture",
    "📊 Comparison",
    "📦 Final Solution"
])

# Tab 1: Upload & Interactive Query
with tabs[0]:
    st.markdown('<div class="sub-header">Step 1: Upload & Query Document</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "docx", "txt"],
            help="Upload your system requirements document"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            if st.button("🚀 Process Document", key="process_btn"):
                with st.spinner("Processing document..."):
                    status_placeholder.info("⏳ Processing document...")
                    
                    try:
                        # Save uploaded file to temp directory (cross-platform)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            temp_path = tmp_file.name
                        
                        s3_key = None

                        # Upload to S3
                        if s3_bucket:
                            s3_manager = S3Manager(bucket_name=s3_bucket, aws_region=aws_region)
                            s3_key = s3_manager.upload_file(temp_path)
                            st.success(f"✅ Uploaded to S3: {s3_key}")
                        
                        # MODIFIED: Process document via Gateway (if uploaded to S3)
                        if s3_key:
                            from tools.gateway_client import process_document as gateway_process_document
                            import json
                            
                            st.info("📄 Processing document via Gateway...")
                            doc_result_raw = gateway_process_document(
                                s3_bucket=s3_bucket,
                                s3_key=s3_key,
                                session_id=st.session_state.session_id
                            )
                            
                            # Parse Lambda response
                            doc_body = json.loads(doc_result_raw["body"]) if isinstance(doc_result_raw.get("body"), str) else doc_result_raw
                            doc_result = {
                                "markdown": doc_body.get("document_text", ""),
                                "metadata": doc_body.get("metadata", {})
                            }
                            st.success("✅ Document processed via Gateway")
                        else:
                            # Fallback to local processing if not uploaded to S3
                            doc_processor = DocumentProcessor(s3_bucket=s3_bucket, aws_region=aws_region)
                            doc_result = asyncio.run(doc_processor.process_local_file(temp_path))
                        
                        # MODIFIED: Extract requirements via Gateway
                        from tools.gateway_client import extract_requirements as gateway_extract_requirements
                        from tools import SystemRequirements
                        import json
                        
                        st.info("🔍 Extracting requirements via Gateway...")
                        req_result = gateway_extract_requirements(
                            document_text=doc_result["markdown"],
                            session_id=st.session_state.session_id
                        )
                        
                        # Parse Lambda response
                        req_body = json.loads(req_result["body"]) if isinstance(req_result.get("body"), str) else req_result
                        requirements_dict = req_body.get("requirements")
                        requirements = SystemRequirements(**requirements_dict)
                        st.session_state.requirements = requirements
                        st.success("✅ Requirements extracted via Gateway")
                        
                        # Initialize RAG system
                        rag = DocumentRAG(model_id=model_id, aws_region=aws_region)
                        rag.index_document(doc_result["markdown"], metadata=doc_result.get("metadata"))
                        st.session_state.rag_system = rag
                        
                        status_placeholder.success("✅ Document processed & indexed!")
                        st.success("✅ Requirements extracted! You can now query the document.")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        status_placeholder.error("❌ Processing failed")
    
    with col2:
        st.markdown("### 💬 Interactive Document Query")
        
        if st.session_state.rag_system:
            # Display document summary
            summary = st.session_state.rag_system.get_document_summary()
            st.info(f"📄 Document indexed: {summary['chunks']} chunks, {summary['total_characters']:,} characters")
            
            # Chat interface
            st.markdown("**Ask questions about your document:**")
            
            # Display chat history
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
            
            # Query input
            query = st.text_input("Your question:", key="doc_query", placeholder="e.g., What are the performance requirements?")
            
            if st.button("Ask", key="ask_btn") and query:
                with st.spinner("Searching document..."):
                    try:
                        result = asyncio.run(st.session_state.rag_system.query(query))
                        
                        # Add to chat history
                        st.session_state.chat_history.append({"role": "user", "content": query})
                        st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.info("👆 Please upload and process a document first to enable interactive querying.")

# Tab 2: Requirements
with tabs[1]:
    st.markdown('<div class="sub-header">Step 2: Review Extracted Requirements</div>', unsafe_allow_html=True)
    
    if st.session_state.requirements:
        req = st.session_state.requirements
        
        st.markdown(f"### {req.project_summary}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Functional Requirements")
            for i, r in enumerate(req.functional_requirements, 1):
                st.markdown(f"{i}. {r}")
            
            st.markdown("#### Security Requirements")
            for i, r in enumerate(req.security_requirements, 1):
                st.markdown(f"{i}. {r}")
        
        with col2:
            st.markdown("#### Performance Requirements")
            for k, v in req.performance_requirements.items():
                st.markdown(f"- **{k.title()}**: {v}")
            
            st.markdown("#### Scalability Requirements")
            for k, v in req.scalability_requirements.items():
                st.markdown(f"- **{k.title()}**: {v}")
        
        if st.button("➡️ Generate Architecture Options", key="generate_btn"):
            with st.spinner("Generating architecture options..."):
                status_placeholder.info("⏳ Generating architecture options...")
                
                try:
                    # Use separate session_manager for Design Agent
                    design_agent = DesignAgent(session_manager=get_agent_session_manager('design'), model_id=model_id)
                    from tools import format_requirements_to_markdown
                    req_md = format_requirements_to_markdown(req)
                    
                    design_output = asyncio.run(design_agent.generate_options(req_md))
                    st.session_state.design_options = design_output
                    
                    status_placeholder.success("✅ Architecture options generated!")
                    st.success("✅ Options generated! Go to the Design Options tab.")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    status_placeholder.error("❌ Generation failed")
    else:
        st.info("👆 Please upload and process a document first.")

# Tab 3: Design Options
with tabs[2]:
    st.markdown('<div class="sub-header">Step 3: Review Architecture Options</div>', unsafe_allow_html=True)
    
    if st.session_state.design_options:
        design_output = st.session_state.design_options
        
        for i, option in enumerate(design_output.options):
            with st.expander(f"🏗️ Option {i+1}: {option.name}", expanded=(i==0)):
                st.markdown(f"**Description**: {option.description}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**AWS Services**")
                    st.markdown(f"- Compute: {', '.join(option.compute_services)}")
                    st.markdown(f"- Storage: {', '.join(option.storage_services)}")
                    st.markdown(f"- Database: {', '.join(option.database_services)}")
                    st.markdown(f"- Networking: {', '.join(option.networking_services)}")
                    st.markdown(f"- Security: {', '.join(option.security_services)}")
                    st.markdown(f"- Monitoring: {', '.join(option.monitoring_services)}")
                    st.markdown(f"- Others: {', '.join(option.other_services)}")
                
                with col2:
                    st.markdown("**Cost Estimation**")
                    st.markdown(f"**Monthly Cost**: {option.estimated_monthly_cost}")
                
                st.markdown("**Architecture Description**")
                st.markdown(option.architecture_description)
                
                col3, col4 = st.columns(2)
                with col3:
                    st.markdown("**Pros**")
                    for pro in option.pros:
                        st.markdown(f"✅ {pro}")
                
                with col4:
                    st.markdown("**Cons**")
                    for con in option.cons:
                        st.markdown(f"❌ {con}")
        
        st.markdown("---")
        st.info("💡 Click 'Compare Options' below to get a detailed comparison and recommendation")
        
        if st.button("📊 Compare Options", key="compare_btn"):
            with st.spinner("Comparing options..."):
                status_placeholder.info("⏳ Comparing options...")
                
                try:
                    # Use separate session_manager for Compare Agent
                    compare_agent = CompareAgent(session_manager=get_agent_session_manager('compare'), model_id=model_id)
                    options_json = json.dumps([opt.model_dump() for opt in design_output.options], indent=2)
                    
                    comparison = asyncio.run(compare_agent.compare_options(options_json))
                    st.session_state.comparison = comparison
                    
                    status_placeholder.success("✅ Comparison completed!")
                    st.success("✅ Comparison completed! Go to the Comparison tab.")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    status_placeholder.error("❌ Comparison failed")
    else:
        st.info("👆 Please generate architecture options first.")

# Tab 4: Refine Architecture (NEW!)
with tabs[3]:
    st.markdown('<div class="sub-header">Step 3.5: Refine Architecture (Real-time)</div>', unsafe_allow_html=True)
    
    if st.session_state.design_options:
        st.markdown("### 🔄 Real-time Recommendation Refinement")
        
        # Select option to refine
        option_names = [opt.name for opt in st.session_state.design_options.options]
        selected_to_refine = st.selectbox(
            "Select option to refine:",
            option_names,
            key="refine_select"
        )
        
        # Get selected option
        selected_option_obj = next(
            opt for opt in st.session_state.design_options.options 
            if opt.name == selected_to_refine
        )
        
        # Refinement interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            feedback = st.text_area(
                "What would you like to change?",
                placeholder="e.g., I need better security, or reduce costs by 30%, or improve performance",
                height=100
            )
        
        with col2:
            focus_area = st.selectbox(
                "Focus Area (optional)",
                ["None", "Cost", "Performance", "Security", "Reliability"],
                key="focus_area"
            )
        
        if st.button("🔄 Refine Architecture", key="refine_btn") and feedback:
            with st.spinner("Refining architecture..."):
                try:
                    refinement_engine = RefinementEngine(model_id=model_id, aws_region=aws_region)
                    
                    result = asyncio.run(refinement_engine.refine(
                        current_architecture=selected_option_obj.model_dump(),
                        feedback=feedback,
                        focus_area=focus_area.lower() if focus_area != "None" else None
                    ))
                    
                    # Add to refinement history
                    st.session_state.refinement_history.append({
                        "feedback": feedback,
                        "result": result
                    })
                    
                    st.success("✅ Architecture refined!")
                    
                    # Display refinement results
                    st.markdown("### 📝 Refinement Summary")
                    st.info(result["summary"])
                    
                    st.markdown("### 🔧 Changes Made")
                    for change in result.get("changes", []):
                        st.markdown(f"**{change['type'].upper()}**: {change['service']}")
                        st.markdown(f"- Reason: {change['reason']}")
                        st.markdown(f"- Impact: {change['impact']}")
                    
                    if result.get("trade_offs"):
                        st.markdown("### ⚖️ Trade-offs")
                        st.warning(result["trade_offs"])
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Display refinement history
        if st.session_state.refinement_history:
            st.markdown("### 📜 Refinement History")
            for i, ref in enumerate(st.session_state.refinement_history, 1):
                # Handle both dict and non-dict ref
                if isinstance(ref, dict):
                    feedback = ref.get('feedback', '')
                    feedback_preview = feedback[:50] if isinstance(feedback, str) else str(feedback)[:50]
                else:
                    feedback_preview = str(ref)[:50]
                with st.expander(f"Refinement {i}: {feedback_preview}..."):
                    st.markdown(f"**Feedback**: {ref['feedback']}")
                    st.markdown(f"**Summary**: {ref['result']['summary']}")
    else:
        st.info("👆 Please generate architecture options first.")

# Tab 5: Comparison
with tabs[4]:
    st.markdown('<div class="sub-header">Step 4: Compare & Select</div>', unsafe_allow_html=True)
    
    if st.session_state.comparison:
        comparison = st.session_state.comparison
        
        st.markdown(f"### Recommended: {comparison.recommended_option}")
        st.info(comparison.recommendation_rationale)
        
        # Check if comparisons list is empty
        if not comparison.comparisons:
            st.error("❌ No comparison data available. The comparison may have failed. Please try again.")
            st.info("💡 Check the logs for more details about the error.")
        else:
            # Display radar charts for each option
            st.markdown("### 📊 Architecture Comparison")
            
            # Well-Architected Framework pillars
            pillars = [
                "Operational Excellence",
                "Security",
                "Reliability",
                "Performance Efficiency",
                "Cost Optimization",
                "Sustainability"
            ]
            
            # Create columns for each option
            cols = st.columns(len(comparison.comparisons))
            
            for idx, comp in enumerate(comparison.comparisons):
                with cols[idx]:
                    # Check if this is the recommended option
                    recommended_option = comparison.recommended_option
                    is_recommended = (comp.option_name == recommended_option)
                    
                    # Add container with consistent styling for all options
                    if is_recommended:
                        # Recommended option: green border and background
                        st.markdown(
                            f'<div style="border: 4px solid #4CAF50; border-radius: 10px; padding: 11px; background-color: #F1F8F4; margin-bottom: 10px;">'
                            f'<h4 style="color: #4CAF50; margin: 0;">⭐ {comp.option_name} (Recommended)</h4>'
                            f'</div>',  # Close immediately - only contains title
                            unsafe_allow_html=True
                        )
                    else:
                        # Non-recommended: transparent border to maintain alignment
                        st.markdown(
                            f'<div style="border: 4px solid transparent; border-radius: 10px; padding: 11px; margin-bottom: 10px;">'
                            f'<h4 style="margin: 0;">{comp.option_name}</h4>'
                            f'</div>',  # Close immediately - only contains title
                            unsafe_allow_html=True
                        )
                    
                    # Extract pillar scores
                    pillar_scores_dict = {ps.pillar: ps.score for ps in comp.pillar_scores}
                    scores = [pillar_scores_dict.get(pillar, 0) for pillar in pillars]
                    
                    # Calculate overall score if it's 0 (fallback)
                    overall_score = comp.overall_score
                    if overall_score == 0 and scores:
                        overall_score = int(sum(scores) / len(scores))
                    
                    st.markdown(f"**Overall Score: {overall_score}/100**")
                    
                    # Create modern gradient style radar chart
                    import plotly.graph_objects as go
                    
                    # Unified color for all radar charts (professional blue)
                    RADAR_COLOR = '#4A90E2'  # Professional blue
                    RADAR_FILL = 'rgba(74, 144, 226, 0.2)'
                    
                    recommended_option = comparison.recommended_option
                    is_recommended = (comp.option_name == recommended_option)
                    
                    # Add first value at the end to close the polygon
                    scores_closed = scores + [scores[0]]
                    pillars_closed = pillars + [pillars[0]]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=scores_closed,
                        theta=pillars_closed,
                        name=comp.option_name,
                        fill='toself',
                        fillcolor=RADAR_FILL,
                        line=dict(
                            color=RADAR_COLOR,
                            width=2.5
                        ),
                        marker=dict(
                            size=8,
                            color=RADAR_COLOR
                        ),
                        mode='lines+markers'
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            bgcolor='#FFFFFF',  # White background
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100],
                                showticklabels=True,
                                tickfont=dict(size=12, color='#666666', family='Arial'),
                                gridcolor='#E0E0E0',  # Light gray grid
                                gridwidth=1
                            ),
                            angularaxis=dict(
                                tickfont=dict(
                                    size=13,
                                    color='#333333',
                                    family='Arial'
                                ),
                                gridcolor='#E0E0E0',
                                gridwidth=1
                            )
                        ),
                        paper_bgcolor='#FFFFFF',  # White paper background
                        plot_bgcolor='#FFFFFF',
                        font=dict(color='#333333', size=13),
                        showlegend=False,
                        height=400,
                        margin=dict(l=80, r=80, t=50, b=50)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display individual scores in a table
                    st.markdown("**Pillar Scores:**")
                    score_data = []
                    for pillar, score in zip(pillars, scores):
                        score_data.append({"Pillar": pillar, "Score": f"{score}/100"})
                    import pandas as pd
                    st.dataframe(pd.DataFrame(score_data), hide_index=True)
                    
                    # Show strengths and weaknesses
                    with st.expander("View Details"):
                        st.markdown("**✅ Strengths:**")
                        for strength in comp.strengths:
                            st.markdown(f"- {strength}")
                        
                        st.markdown("**⚠️ Weaknesses:**")
                        for weakness in comp.weaknesses:
                            st.markdown(f"- {weakness}")
            
            # Selection radio buttons
            selected = st.radio(
                "Select your preferred option:",
                options=[comp.option_name for comp in comparison.comparisons],
                index=0
            )
            
            st.session_state.selected_option = selected
            
            if st.button("✅ Confirm Selection & Generate Final Solution", key="final_btn"):
                with st.spinner("Generating diagram and staffing plan..."):
                    try:
                        # Get selected architecture
                        selected_arch = next(
                            opt for opt in st.session_state.design_options.options 
                            if opt.name == selected
                        )
                        
                        # Generate diagram and render via Gateway
                        # DiagramAgent now handles both Mermaid generation and rendering
                        logger.info("generating_and_rendering_diagram", selected_option=selected)
                        
                        try:
                            # Check if Gateway is configured
                            GATEWAY_URL = os.getenv('AGENTCORE_GATEWAY_URL')
                            ACCESS_TOKEN = os.getenv('AGENTCORE_ACCESS_TOKEN')
                            
                            if not GATEWAY_URL:
                                raise ValueError("AGENTCORE_GATEWAY_URL not set in environment")
                            if not ACCESS_TOKEN:
                                raise ValueError("AGENTCORE_ACCESS_TOKEN not set in environment")
                            
                            # Initialize DiagramAgent with Gateway integration
                            diagram_agent = DiagramAgent(
                                gateway_url=GATEWAY_URL,
                                access_token=ACCESS_TOKEN,
                                model_id=model_id,
                                session_id=st.session_state.session_id
                            )
                            
                            # Generate diagram (returns both Mermaid code and S3 URL)
                            result = asyncio.run(diagram_agent.generate_diagram(
                                architecture_json=json.dumps(selected_arch.model_dump()),
                                architecture_name=selected
                            ))
                            
                            if not result.get('success'):
                                error_msg = result.get('error', 'Unknown error')
                                raise Exception(f"Diagram generation failed: {error_msg}")
                            
                            # Save results to session state
                            st.session_state.diagram_s3_url = result.get('s3_url', '')
                            st.session_state.diagram_s3_key = result.get('s3_key', '')
                            st.session_state.mermaid_code = result.get('mermaid_code', '')
                            
                            logger.info("diagram_rendered_successfully", 
                                       s3_url=st.session_state.diagram_s3_url,
                                       s3_key=st.session_state.diagram_s3_key)
                        
                        except Exception as e:
                            logger.error("diagram_generation_failed", error=str(e))
                            st.error(f"❌ Failed to generate diagram: {str(e)}")
                            # Continue anyway to generate staffing plan
                            st.session_state.diagram_s3_url = ''
                            st.session_state.diagram_s3_key = ''
                            st.session_state.mermaid_code = ''
                        
                        # Generate staffing plan
                        # Use separate session_manager for Staffing Agent
                        staffing_agent = StaffingAgent(session_manager=get_agent_session_manager('staffing'), model_id=model_id)
                        staffing_plan = asyncio.run(staffing_agent.generate_plan(
                            selected_arch.model_dump()  # Pass dict, not JSON string
                        ))
                        # Convert Pydantic model to dict for display
                        if hasattr(staffing_plan, 'model_dump'):
                            st.session_state.staffing_plan = staffing_plan.model_dump()
                        elif hasattr(staffing_plan, 'dict'):
                            st.session_state.staffing_plan = staffing_plan.dict()
                        else:
                            st.session_state.staffing_plan = staffing_plan
                        
                        st.success(f"✅ Selected: {selected}")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    else:
        st.info("👆 Please compare options first.")

# Tab 6: Final Solution
with tabs[5]:
    st.markdown('<div class="sub-header">Step 5: Final Solution Report</div>', unsafe_allow_html=True)
    
    if st.session_state.selected_option:
        st.success(f"✅ Selected Architecture: {st.session_state.selected_option}")
        
        # Display diagram from S3
        # Lambda has already rendered and uploaded the diagram
        if st.session_state.diagram_s3_url:
            st.markdown("### 📐 Architecture Diagram")
            st.success("✅ Diagram rendered successfully")
            st.session_state.diagram_path = st.session_state.diagram_s3_url  # after success

            if st.session_state.diagram_s3_url.endswith('.svg'):
                # Display SVG with HTML for best quality
                import requests
                try:
                    svg_content = requests.get(st.session_state.diagram_s3_url).text
                    st.components.v1.html(f'<div style="width:100%; overflow-x:auto;">{svg_content}</div>',height=800,scrolling=True)
                    st.caption("AWS Architecture Diagram (SVG - Vector Graphics)")
                except:
                    # Fallback to image
                    st.image(st.session_state.diagram_s3_url, caption="AWS Architecture Diagram", use_container_width=True)
            else:
                # PNG
                st.image(st.session_state.diagram_s3_url, caption="AWS Architecture Diagram", use_container_width=True)

            st.info(f"📍 Diagram stored in S3: {st.session_state.diagram_s3_key}")
        elif hasattr(st.session_state, 'diagram_s3_url'):  # Check if we attempted to render
            st.markdown("### 📐 Architecture Diagram")
            st.warning("⚠️ Diagram rendering failed or is still in progress")
        
        # Display staffing plan
        if st.session_state.staffing_plan:
            st.markdown("### 👥 Staffing & Timeline Plan")
            
            # Parse staffing plan
            staffing = st.session_state.staffing_plan
            
            # Display project summary
            if isinstance(staffing, dict):
                # Display team size and duration
                col1, col2, col3 = st.columns(3)
                with col1:
                    team_size = staffing.get('team_size', 'N/A')
                    st.metric("Team Size", team_size)
                with col2:
                    duration = staffing.get('total_duration_weeks', 'N/A')
                    st.metric("Duration", f"{duration} weeks" if isinstance(duration, int) else duration)
                with col3:
                    cost = staffing.get('estimated_cost', 'N/A')
                    st.metric("Estimated Cost", cost)
                
                # Display team structure/roles
                if 'roles' in staffing:
                    st.markdown("#### 👥 Team Structure")
                    roles = staffing.get('roles', [])
                    if isinstance(roles, list):
                        for role in roles:
                            if isinstance(role, dict):
                                title = role.get('title', 'Role')
                                count = role.get('count', 1)
                                skills = role.get('skills', [])
                                responsibilities = role.get('responsibilities', '')
                                
                                with st.expander(f"**{title}** ({count} person{'s' if count > 1 else ''})"):
                                    if skills:
                                        st.markdown("**Required Skills:**")
                                        for skill in skills:
                                            st.markdown(f"- {skill}")
                                    if responsibilities:
                                        st.markdown(f"**Responsibilities:** {responsibilities}")
                            else:
                                st.markdown(f"- {role}")
                    else:
                        st.markdown(str(roles))
                
                # Display project timeline/phases
                if 'phases' in staffing:
                    st.markdown("#### 📅 Project Timeline")
                    phases = staffing.get('phases', [])
                    if isinstance(phases, list):
                        for phase in phases:
                            if isinstance(phase, dict):
                                phase_name = phase.get('name', 'Phase')
                                duration_weeks = phase.get('duration_weeks', 'N/A')
                                activities = phase.get('activities', [])
                                deliverables = phase.get('deliverables', [])
                                
                                with st.expander(f"**{phase_name}** ({duration_weeks} weeks)"):
                                    if activities:
                                        st.markdown("**Activities:**")
                                        for activity in activities:
                                            st.markdown(f"- {activity}")
                                    if deliverables:
                                        st.markdown("**Deliverables:**")
                                        for deliverable in deliverables:
                                            st.markdown(f"- {deliverable}")
                            else:
                                st.markdown(f"- {phase}")
                    else:
                        st.markdown(str(phases))
                
                # Show full JSON in expander
                with st.expander("📋 View Complete Staffing Plan (JSON)"):
                    st.json(staffing)
            else:
                # Fallback: display as text
                st.markdown(str(staffing))
        
        st.markdown("### 📦 Deliverables")
        st.markdown("- ✅ Architecture Design Document")
        st.markdown("- ✅ Well-Architected Framework Assessment")
        st.markdown("- ✅ Cost Estimation")
        st.markdown("- ✅ Architecture Diagram (PNG)")
        st.markdown("- ✅ Implementation Timeline")
        st.markdown("- ✅ Staffing Plan")
        
        if st.button("📥 Generate Complete Report", key="download_report_btn"):
            with st.spinner("Generating complete report..."):
                try:
                    import io
                    from datetime import datetime
                    
                    # Create report content
                    report_content = f"""# AWS Solutions Architect Report

## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Selected Architecture: {st.session_state.selected_option}

### Architecture Details

"""
                    
                    # Add selected architecture details
                    selected_arch = next(
                        opt for opt in st.session_state.design_options.options 
                        if opt.name == st.session_state.selected_option
                    )
                    
                    report_content += f"""**Description**: {selected_arch.description}\n\n"""
                    
                    # Add services
                    if hasattr(selected_arch, 'compute_services'):
                        report_content += f"""\n#### Compute Services\n"""
                        for service in selected_arch.compute_services:
                            report_content += f"- {service}\n"
                    
                    if hasattr(selected_arch, 'storage_services'):
                        report_content += f"""\n#### Storage Services\n"""
                        for service in selected_arch.storage_services:
                            report_content += f"- {service}\n"
                    
                    if hasattr(selected_arch, 'database_services'):
                        report_content += f"""\n#### Database Services\n"""
                        for service in selected_arch.database_services:
                            report_content += f"- {service}\n"
                    
                    if hasattr(selected_arch, 'networking_services'):
                        report_content += f"""\n#### Networking Services\n"""
                        for service in selected_arch.networking_services:
                            report_content += f"- {service}\n"
                    
                    # Add Well-Architected scores
                    if hasattr(selected_arch, 'well_architected_scores'):
                        report_content += f"""\n### Well-Architected Framework Scores\n\n"""
                        scores = selected_arch.well_architected_scores
                        for pillar, score in scores.items():
                            report_content += f"- **{pillar}**: {score}/100\n"
                    
                    # Add staffing plan
                    if st.session_state.staffing_plan:
                        report_content += f"""\n### Staffing & Timeline Plan\n\n"""
                        report_content += f"```json\n{json.dumps(st.session_state.staffing_plan, indent=2)}\n```\n"
                    
                    # Add deliverables
                    report_content += f"""\n### Deliverables\n\n"""
                    report_content += "- Architecture Design Document\n"
                    report_content += "- Well-Architected Framework Assessment\n"
                    report_content += "- Cost Estimation\n"
                    report_content += "- Architecture Diagram (PNG)\n"
                    report_content += "- Implementation Timeline\n"
                    report_content += "- Staffing Plan\n"
                    
                    # Create download button
                    st.download_button(
                        label="📥 Download Report (Markdown)",
                        data=report_content,
                        file_name=f"aws_architecture_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown"
                    )
                    
                    st.success("✅ Complete report generated!")
                    st.info("Report includes all architecture details, diagrams, and staffing plans.")
                    
                except Exception as e:
                    st.error(f"❌ Error generating report: {str(e)}")
    else:
        st.info("👆 Please complete all previous steps.")

# Footer
st.divider()
st.markdown("**AWS Solutions Architect Agent** | Powered by Amazon Bedrock AgentCore | Built with Streamlit")
st.markdown("**Features**: Interactive Document Querying (RAG) • Real-time Refinement • Diagram Generation")