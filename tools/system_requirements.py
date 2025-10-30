"""
System Requirements - Data model for structured requirements

This module contains the SystemRequirements Pydantic model used across the application.
The actual extraction logic has been migrated to Lambda (requirementsExtractor).

Usage:
    from tools import SystemRequirements
    
    # Create from Gateway response
    requirements = SystemRequirements(**gateway_response)
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class SystemRequirements(BaseModel):
    """
    Structured system requirements data model
    
    This Pydantic model defines the structure for system requirements.
    Requirements are extracted by the Lambda function (requirementsExtractor)
    and returned as JSON that matches this schema.
    
    Attributes:
        functional_requirements: List of functional requirements
        performance_requirements: Performance metrics (latency, throughput, etc.)
        scalability_requirements: Scalability targets (users, requests/sec, etc.)
        security_requirements: Security and compliance requirements
        availability_requirements: Availability metrics (SLA, RTO, RPO, etc.)
        technical_constraints: Technical constraints and limitations
        budget_constraints: Budget limitations
        integration_requirements: External system integrations
        data_requirements: Data storage and processing requirements
        compliance_requirements: Compliance standards (HIPAA, GDPR, etc.)
        project_summary: Brief project description
    """
    
    # Functional Requirements
    functional_requirements: List[str] = Field(
        description="List of functional requirements"
    )
    
    # Non-Functional Requirements
    performance_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="Performance requirements (e.g., latency, throughput)"
    )
    
    scalability_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="Scalability requirements (e.g., users, requests/sec)"
    )
    
    security_requirements: List[str] = Field(
        default_factory=list,
        description="Security and compliance requirements"
    )
    
    availability_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="Availability and reliability requirements (e.g., SLA, RTO, RPO)"
    )
    
    # Technical Constraints
    technical_constraints: List[str] = Field(
        default_factory=list,
        description="Technical constraints (e.g., must use specific AWS services)"
    )
    
    budget_constraints: Optional[str] = Field(
        None,
        description="Budget constraints"
    )
    
    # Integration Requirements
    integration_requirements: List[str] = Field(
        default_factory=list,
        description="Integration with external systems"
    )
    
    # Data Requirements
    data_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="Data storage, retention, and processing requirements"
    )
    
    # Compliance
    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Compliance requirements (e.g., HIPAA, GDPR, SOC2)"
    )
    
    # Summary
    project_summary: str = Field(
        description="Brief summary of the project"
    )
    
    @field_validator(
        'performance_requirements',
        'scalability_requirements',
        'availability_requirements',
        'data_requirements',
        mode='before'
    )
    @classmethod
    def clean_dict_fields(cls, v: Any) -> Dict[str, str]:
        """
        Clean dictionary fields to ensure all values are strings
        
        This validator:
        1. Converts non-dict values to empty dict
        2. Removes empty string values
        3. Converts non-string values to strings
        4. Removes empty dict values
        
        Args:
            v: Input value to clean
            
        Returns:
            Cleaned dictionary with string values
        """
        if not isinstance(v, dict):
            return {}
        
        cleaned = {}
        for key, value in v.items():
            if isinstance(value, str):
                # Only keep non-empty strings (after stripping whitespace)
                if value.strip():
                    cleaned[key] = value
            elif isinstance(value, dict):
                # Skip empty dicts, convert non-empty dicts to string
                if value:  # Non-empty dict, convert to string
                    cleaned[key] = str(value)
                # Empty dict is skipped, not added to cleaned
            elif value is not None:
                # Other non-None values, convert to string
                cleaned[key] = str(value)
        
        return cleaned


# Example usage
if __name__ == "__main__":
    print("SystemRequirements Data Model")
    print("=" * 60)
    print()
    print("This module defines the SystemRequirements Pydantic model.")
    print("Requirements are extracted by Lambda (requirementsExtractor).")
    print()
    print("Usage:")
    print()
    print("1. Import the model:")
    print("   from tools import SystemRequirements")
    print()
    print("2. Create from Gateway response:")
    print("   requirements = SystemRequirements(**gateway_response)")
    print()
    print("3. Access fields:")
    print("   print(requirements.functional_requirements)")
    print("   print(requirements.project_summary)")
    print()
    print("=" * 60)
    print()
    print("Example:")
    print()
    
    # Create example
    req = SystemRequirements(
        functional_requirements=[
            "User authentication and authorization",
            "Payment processing with multiple payment methods",
            "Real-time inventory management"
        ],
        performance_requirements={
            "latency": "< 200ms for API responses",
            "throughput": "1000 requests/second"
        },
        scalability_requirements={
            "concurrent_users": "10,000",
            "peak_traffic": "5x normal load"
        },
        security_requirements=[
            "Encryption at rest and in transit",
            "PCI-DSS compliance for payment data",
            "Multi-factor authentication"
        ],
        availability_requirements={
            "sla": "99.9% uptime",
            "rto": "1 hour",
            "rpo": "15 minutes"
        },
        technical_constraints=[
            "Must use AWS services only",
            "Serverless architecture preferred"
        ],
        budget_constraints="$5,000/month for AWS infrastructure",
        integration_requirements=[
            "REST API integration with inventory system",
            "Webhook integration with payment gateway"
        ],
        data_requirements={
            "retention": "7 years for financial records",
            "backup": "Daily automated backups"
        },
        compliance_requirements=[
            "PCI-DSS",
            "GDPR"
        ],
        project_summary="E-commerce platform with real-time inventory and payment processing"
    )
    
    print(f"✅ Created SystemRequirements with:")
    print(f"   - {len(req.functional_requirements)} functional requirements")
    print(f"   - {len(req.performance_requirements)} performance metrics")
    print(f"   - {len(req.security_requirements)} security requirements")
    print(f"   - {len(req.compliance_requirements)} compliance standards")
    print()
    print(f"Project: {req.project_summary}")
    print()
    print("=" * 60)

