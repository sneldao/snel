"""
Research services module.
Handles intelligent routing and orchestration of research tools.
"""
from app.services.research.router import ResearchRouter, RoutingDecision, Intent
from app.services.research.response_formatter import ResponseFormatter

__all__ = ["ResearchRouter", "RoutingDecision", "Intent", "ResponseFormatter"]
