"""
Centralized AgentCore Memory Management
"""
from functools import lru_cache
import os

import structlog
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

logger = structlog.get_logger(__name__)

@lru_cache(maxsize=1)
def get_memory_id(region_name: str = "us-east-1") -> str:
    """Retrieve the AgentCore Memory ID from environment variables."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
    if not memory_id:
        raise ValueError(
            "AGENTCORE_MEMORY_ID environment variable not set. "
            "Please create a Memory resource in AWS Bedrock Console and set the ID in your .env file."
        )
    logger.info("retrieved_agentcore_memory_id", memory_id=memory_id)
    return memory_id

def create_session_manager(
    memory_id: str, 
    session_id: str, 
    actor_id: str, 
    region_name: str = "us-east-1"
) -> AgentCoreMemorySessionManager:
    """Create a session manager for a given session and user with retrieval config."""
    config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id,
        # Configure retrieval strategies from long-term memory
        retrieval_config={
            "/preferences/{actorId}": RetrievalConfig(top_k=3, relevance_score=0.7),
            "/facts/{actorId}": RetrievalConfig(top_k=5, relevance_score=0.5),
            "/summaries/{actorId}/{sessionId}": RetrievalConfig(top_k=1, relevance_score=0.5),
        }
    )
    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=region_name
    )

