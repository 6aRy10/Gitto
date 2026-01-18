"""
LLM Reasoning Layer

GPT-4o powered reasoning for:
- Variance explanation
- Recommendation generation
- Narrative generation
"""

from .llm_client import FPALLMClient, LLMConfig
from .variance_reasoner import VarianceReasoner
from .recommendation_engine import RecommendationEngine
from .narrative_generator import NarrativeGenerator

__all__ = [
    'FPALLMClient',
    'LLMConfig',
    'VarianceReasoner',
    'RecommendationEngine',
    'NarrativeGenerator',
]
