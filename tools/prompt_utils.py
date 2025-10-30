"""
Prompt Utilities - Helper functions for managing prompt length
Prevents Memory search query limit errors (10,000 chars max)
"""

import structlog

logger = structlog.get_logger(__name__)

# Memory search query limit is 10,000 characters
# We use 8,000 as safe limit to leave buffer for formatting
MAX_PROMPT_LENGTH = 8000


def truncate_prompt_safely(
    prompt: str,
    max_length: int = MAX_PROMPT_LENGTH,
    truncation_note: str = "[Note: Content truncated due to length constraints.]"
) -> str:
    """
    Safely truncate prompt to avoid Memory search query limit
    
    Args:
        prompt: The full prompt text
        max_length: Maximum allowed length (default: 8000)
        truncation_note: Note to append when truncating
        
    Returns:
        Truncated prompt if needed, original prompt otherwise
    """
    if len(prompt) <= max_length:
        return prompt
    
    logger.warning(
        "prompt_truncated",
        original_length=len(prompt),
        max_length=max_length,
        truncated_chars=len(prompt) - max_length
    )
    
    # Truncate and add note
    truncated = prompt[:max_length - len(truncation_note) - 10]
    return f"{truncated}\n\n{truncation_note}"


def truncate_with_instructions(
    instructions: str,
    prompt: str,
    max_total_length: int = MAX_PROMPT_LENGTH,
    truncation_note: str = "[Note: Content truncated due to length constraints.]"
) -> str:
    """
    Truncate prompt while preserving instructions
    
    Args:
        instructions: System instructions (always preserved)
        prompt: User prompt (may be truncated)
        max_total_length: Maximum total length
        truncation_note: Note to append when truncating
        
    Returns:
        Full prompt with instructions + (possibly truncated) prompt
    """
    full_prompt = f"{instructions}\n\n{prompt}"
    
    if len(full_prompt) <= max_total_length:
        return full_prompt
    
    logger.warning(
        "prompt_with_instructions_truncated",
        instructions_length=len(instructions),
        prompt_length=len(prompt),
        total_length=len(full_prompt),
        max_length=max_total_length
    )
    
    # Calculate available space for prompt
    available_for_prompt = max_total_length - len(instructions) - len(truncation_note) - 20
    
    if available_for_prompt < 100:
        logger.error(
            "instructions_too_long",
            instructions_length=len(instructions),
            max_length=max_total_length
        )
        raise ValueError(f"Instructions too long ({len(instructions)} chars), cannot fit prompt")
    
    # Truncate prompt
    truncated_prompt = prompt[:available_for_prompt]
    return f"{instructions}\n\n{truncated_prompt}\n\n{truncation_note}"


def estimate_token_count(text: str) -> int:
    """
    Rough estimate of token count (1 token ≈ 4 characters)
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def check_prompt_length(prompt: str, context: str = "") -> None:
    """
    Check and log prompt length for debugging
    
    Args:
        prompt: The prompt to check
        context: Context description for logging
    """
    length = len(prompt)
    tokens = estimate_token_count(prompt)
    
    if length > MAX_PROMPT_LENGTH:
        logger.warning(
            "prompt_exceeds_limit",
            context=context,
            length=length,
            max_length=MAX_PROMPT_LENGTH,
            estimated_tokens=tokens,
            over_limit_by=length - MAX_PROMPT_LENGTH
        )
    else:
        logger.info(
            "prompt_length_ok",
            context=context,
            length=length,
            max_length=MAX_PROMPT_LENGTH,
            estimated_tokens=tokens
        )

