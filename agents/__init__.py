# __init__.py
"""Agents package"""
from .design_agent import DesignAgent, DesignAgentOutput, ArchitectureOption
from .compare_agent import CompareAgent, CompareAgentOutput, OptionComparison
from .diagram_agent import DiagramAgent  # Now uses Gateway integration
from .staffing_agent import StaffingAgent
from .supervisor_agent import SupervisorAgent

__all__ = [
    "DesignAgent", "DesignAgentOutput", "ArchitectureOption",
    "CompareAgent", "CompareAgentOutput", "OptionComparison",
    "DiagramAgent", "StaffingAgent", "SupervisorAgent"
]
