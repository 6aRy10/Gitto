"""
Recommendation Engine

Uses LLM to generate actionable recommendations based on financial situations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

from .llm_client import FPALLMClient
from ..models.decisions import DecisionOption

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Uses GPT-4o to generate actionable recommendations.
    
    Takes financial situations and constraints, produces prioritized
    recommendations with risk assessment.
    """
    
    def __init__(self, llm_client: Optional[FPALLMClient] = None):
        self.llm = llm_client or FPALLMClient()
    
    async def generate_options(
        self,
        situation: Dict[str, Any],
        constraints: List[str],
    ) -> List[DecisionOption]:
        """
        Generate possible actions for a situation.
        
        Args:
            situation: Current situation description
            constraints: Business constraints to consider
        
        Returns:
            List of DecisionOption objects
        """
        recommendations = await self.llm.generate_recommendations(situation, constraints)
        
        options = []
        for i, rec in enumerate(recommendations):
            option_id = f"option_{chr(65 + i)}"  # A, B, C, etc.
            
            # Parse risk level
            risk = rec.get("risk", rec.get("risk_level", "medium")).lower()
            if risk not in ["low", "medium", "high"]:
                risk = "medium"
            
            # Parse impact amount
            impact = rec.get("impact", rec.get("expected_impact", "0"))
            try:
                if isinstance(impact, str):
                    # Extract number from string like "€50,000"
                    import re
                    numbers = re.findall(r'[\d,]+\.?\d*', impact.replace(',', ''))
                    impact_amount = Decimal(numbers[0]) if numbers else Decimal("0")
                else:
                    impact_amount = Decimal(str(impact))
            except:
                impact_amount = Decimal("0")
            
            options.append(DecisionOption(
                id=option_id,
                label=f"{chr(65 + i)}) {rec.get('action', 'Unknown action')}",
                description=rec.get("description", rec.get("action", "")),
                risk_level=risk,
                risk_explanation=rec.get("risk_explanation", f"{risk.title()} risk"),
                impact_amount=impact_amount,
                impact_description=rec.get("impact_description", str(rec.get("impact", ""))),
                recommended=i == 0,  # First option is usually recommended
                auto_executable=risk == "low",
                metadata={
                    "timeline": rec.get("timeline", "immediate"),
                    "prerequisites": rec.get("prerequisites", []),
                },
            ))
        
        return options
    
    async def recommend(
        self,
        options: List[DecisionOption],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Select best option(s) with reasoning.
        
        Args:
            options: Available options
            context: Financial context for decision
        
        Returns:
            Recommendation with reasoning
        """
        # Format options for LLM
        options_text = "\n".join([
            f"{o.label}: {o.description} (Risk: {o.risk_level}, Impact: €{o.impact_amount:,.0f})"
            for o in options
        ])
        
        situation = {
            "options": options_text,
            "context": context,
        }
        
        constraints = [
            "Minimize risk while addressing the issue",
            "Consider cash flow timing",
            "Maintain vendor/customer relationships",
        ]
        
        recommendations = await self.llm.generate_recommendations(situation, constraints)
        
        # Find recommended option IDs
        recommended_ids = []
        reasoning = ""
        
        if recommendations:
            rec = recommendations[0]
            reasoning = rec.get("action", "")
            
            # Match to our options
            for opt in options:
                if opt.recommended or opt.risk_level == "low":
                    recommended_ids.append(opt.id)
                    break
        
        if not recommended_ids and options:
            recommended_ids = [options[0].id]
        
        return {
            "recommended_option_ids": recommended_ids,
            "reasoning": reasoning,
            "confidence": "medium",
        }
    
    async def generate_cash_shortfall_options(
        self,
        shortfall_amount: Decimal,
        shortfall_week: int,
        available_actions: Dict[str, Any],
    ) -> List[DecisionOption]:
        """
        Generate options specifically for cash shortfall situations.
        
        Args:
            shortfall_amount: Amount of shortfall
            shortfall_week: Week number with shortfall
            available_actions: Available levers (vendor delays, AR acceleration, etc.)
        
        Returns:
            List of decision options
        """
        situation = {
            "problem": "cash_shortfall",
            "shortfall_amount": float(shortfall_amount),
            "shortfall_week": shortfall_week,
            "available_actions": available_actions,
        }
        
        constraints = [
            f"Need to close €{shortfall_amount:,.0f} gap by week {shortfall_week}",
            "Prefer actions that don't damage vendor/customer relationships",
            "Avoid interest costs if possible",
            "Consider combining multiple actions",
        ]
        
        return await self.generate_options(situation, constraints)
    
    async def generate_reconciliation_options(
        self,
        unmatched_count: int,
        total_amount: Decimal,
        days_aged: int,
    ) -> List[DecisionOption]:
        """
        Generate options for reconciliation issues.
        """
        situation = {
            "problem": "aged_reconciliation_items",
            "unmatched_count": unmatched_count,
            "total_amount": float(total_amount),
            "days_aged": days_aged,
        }
        
        constraints = [
            "Items should not remain unmatched at period close",
            "Prefer investigation over write-off",
            "Consider materiality thresholds",
        ]
        
        return await self.generate_options(situation, constraints)
    
    async def prioritize_actions(
        self,
        actions: List[Dict[str, Any]],
        available_resources: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Prioritize a list of potential actions.
        
        Args:
            actions: List of possible actions
            available_resources: Time, money, people available
        
        Returns:
            Prioritized and filtered action list
        """
        situation = {
            "actions": actions,
            "resources": available_resources,
        }
        
        constraints = [
            "Prioritize by impact/effort ratio",
            "Consider dependencies between actions",
            "Account for resource constraints",
        ]
        
        recommendations = await self.llm.generate_recommendations(situation, constraints)
        
        # Return in priority order
        return recommendations
