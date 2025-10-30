"""
Requirements Formatter - Format SystemRequirements to Markdown

Extracted from RequirementsExtractor for use after Gateway migration.
This module provides formatting utilities for SystemRequirements objects.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .system_requirements import SystemRequirements


def to_markdown(requirements: 'SystemRequirements') -> str:
    """
    Convert SystemRequirements to markdown format
    
    Args:
        requirements: SystemRequirements object (Pydantic model)
        
    Returns:
        Markdown-formatted string representation of requirements
        
    Example:
        >>> from tools import SystemRequirements
        >>> from tools.requirements_formatter import to_markdown
        >>> 
        >>> requirements = SystemRequirements(
        ...     functional_requirements=["User authentication", "Payment processing"],
        ...     project_summary="E-commerce platform"
        ... )
        >>> markdown = to_markdown(requirements)
        >>> print(markdown)
    """
    
    md = f"""# System Requirements

## Project Summary
{requirements.project_summary}

## Functional Requirements
"""
    
    # Functional Requirements
    for i, req in enumerate(requirements.functional_requirements, 1):
        md += f"{i}. {req}\n"
    
    # Performance Requirements
    md += "\n## Performance Requirements\n"
    if requirements.performance_requirements:
        for key, value in requirements.performance_requirements.items():
            md += f"- **{key.title()}**: {value}\n"
    else:
        md += "_No specific performance requirements specified._\n"
    
    # Scalability Requirements
    md += "\n## Scalability Requirements\n"
    if requirements.scalability_requirements:
        for key, value in requirements.scalability_requirements.items():
            md += f"- **{key.title()}**: {value}\n"
    else:
        md += "_No specific scalability requirements specified._\n"
    
    # Security Requirements
    if requirements.security_requirements:
        md += "\n## Security Requirements\n"
        for i, req in enumerate(requirements.security_requirements, 1):
            md += f"{i}. {req}\n"
    
    # Availability Requirements
    md += "\n## Availability Requirements\n"
    if requirements.availability_requirements:
        for key, value in requirements.availability_requirements.items():
            md += f"- **{key.upper()}**: {value}\n"
    else:
        md += "_No specific availability requirements specified._\n"
    
    # Technical Constraints
    if requirements.technical_constraints:
        md += "\n## Technical Constraints\n"
        for i, constraint in enumerate(requirements.technical_constraints, 1):
            md += f"{i}. {constraint}\n"
    
    # Budget Constraints
    if requirements.budget_constraints:
        md += f"\n## Budget Constraints\n{requirements.budget_constraints}\n"
    
    # Integration Requirements
    if requirements.integration_requirements:
        md += "\n## Integration Requirements\n"
        for i, req in enumerate(requirements.integration_requirements, 1):
            md += f"{i}. {req}\n"
    
    # Data Requirements
    md += "\n## Data Requirements\n"
    if requirements.data_requirements:
        for key, value in requirements.data_requirements.items():
            md += f"- **{key.title()}**: {value}\n"
    else:
        md += "_No specific data requirements specified._\n"
    
    # Compliance Requirements
    if requirements.compliance_requirements:
        md += "\n## Compliance Requirements\n"
        for i, req in enumerate(requirements.compliance_requirements, 1):
            md += f"{i}. {req}\n"
    
    return md


def to_summary(requirements: 'SystemRequirements') -> str:
    """
    Generate a brief summary of requirements
    
    Args:
        requirements: SystemRequirements object
        
    Returns:
        Brief text summary
        
    Example:
        >>> summary = to_summary(requirements)
        >>> print(summary)
    """
    summary_parts = []
    
    # Project summary
    summary_parts.append(f"Project: {requirements.project_summary}")
    
    # Functional requirements count
    func_count = len(requirements.functional_requirements)
    summary_parts.append(f"Functional Requirements: {func_count}")
    
    # Security
    if requirements.security_requirements:
        summary_parts.append(f"Security Requirements: {len(requirements.security_requirements)}")
    
    # Compliance
    if requirements.compliance_requirements:
        compliance_list = ", ".join(requirements.compliance_requirements)
        summary_parts.append(f"Compliance: {compliance_list}")
    
    # Budget
    if requirements.budget_constraints:
        summary_parts.append(f"Budget: {requirements.budget_constraints}")
    
    return " | ".join(summary_parts)


def to_dict(requirements: 'SystemRequirements') -> dict:
    """
    Convert SystemRequirements to dictionary
    
    Args:
        requirements: SystemRequirements object
        
    Returns:
        Dictionary representation
        
    Example:
        >>> req_dict = to_dict(requirements)
        >>> print(req_dict.keys())
    """
    return requirements.model_dump()


def to_json(requirements: 'SystemRequirements', indent: int = 2) -> str:
    """
    Convert SystemRequirements to JSON string
    
    Args:
        requirements: SystemRequirements object
        indent: JSON indentation (default: 2)
        
    Returns:
        JSON string
        
    Example:
        >>> json_str = to_json(requirements)
        >>> print(json_str)
    """
    import json
    return json.dumps(requirements.model_dump(), indent=indent)


# Example usage
if __name__ == "__main__":
    # This is just for demonstration
    # In real usage, SystemRequirements comes from Gateway's requirementsExtractor
    
    print("Requirements Formatter Utility")
    print("=" * 50)
    print()
    print("Usage:")
    print()
    print("1. Import the formatter:")
    print("   from tools.requirements_formatter import to_markdown")
    print()
    print("2. Format requirements:")
    print("   markdown = to_markdown(requirements)")
    print()
    print("3. Use in your code:")
    print("   # In streamlit_app.py")
    print("   from tools.requirements_formatter import to_markdown")
    print("   req_md = to_markdown(req)")
    print()
    print("=" * 50)

