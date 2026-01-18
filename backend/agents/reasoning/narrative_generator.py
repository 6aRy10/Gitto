"""
Narrative Generator

Generates human-readable narratives for financial reports.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

from .llm_client import FPALLMClient
from ..models.briefings import MorningBriefing, WeeklyPack

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """
    Generates professional narratives for financial reports.
    
    Used for:
    - Morning briefing summaries
    - Weekly pack executive summaries
    - Board pack narratives
    - CFO talking points
    """
    
    def __init__(self, llm_client: Optional[FPALLMClient] = None):
        self.llm = llm_client or FPALLMClient()
    
    async def generate_morning_briefing_summary(
        self,
        briefing: MorningBriefing,
    ) -> str:
        """
        Generate executive summary for morning briefing.
        
        Args:
            briefing: MorningBriefing data
        
        Returns:
            Executive summary text
        """
        data = {
            "date": briefing.briefing_date.isoformat(),
            "cash_position": {
                "current": str(briefing.cash_position.current_balance),
                "expected": str(briefing.cash_position.expected_balance),
                "variance": str(briefing.cash_position.variance_from_expected),
            },
            "overnight_activity": {
                "inflows_count": len(briefing.overnight_inflows),
                "inflows_total": str(sum(m.amount for m in briefing.overnight_inflows)),
                "outflows_count": len(briefing.overnight_outflows),
                "outflows_total": str(sum(m.amount for m in briefing.overnight_outflows)),
            },
            "surprises_count": len(briefing.surprises),
            "attention_items_count": len(briefing.attention_items),
            "expected_today": {
                "inflows": str(briefing.total_expected_inflows),
                "outflows": str(briefing.total_expected_outflows),
            },
        }
        
        narrative = await self.llm.generate_narrative(
            data=data,
            narrative_type="briefing",
            max_length=200,
        )
        
        return narrative
    
    async def generate_weekly_pack_summary(
        self,
        pack: WeeklyPack,
    ) -> str:
        """
        Generate executive summary for weekly pack.
        
        Args:
            pack: WeeklyPack data
        
        Returns:
            Executive summary text
        """
        data = {
            "date": pack.pack_date.isoformat(),
            "current_cash": str(pack.current_cash),
            "runway_weeks": pack.runway_weeks,
            "min_cash_week": pack.min_cash_week,
            "min_cash_amount": str(pack.min_cash_amount),
            "forecast_accuracy": pack.forecast_accuracy_pct,
            "accuracy_trend": pack.accuracy_trend,
            "forecast_changes": [
                {
                    "week": fc.week_number,
                    "previous": str(fc.previous_forecast),
                    "current": str(fc.current_forecast),
                    "variance": str(fc.variance),
                }
                for fc in pack.forecast_comparisons[:3]  # Top 3 changes
            ],
            "decisions_pending": len(pack.decisions_pending),
            "key_risks": pack.key_risks,
        }
        
        narrative = await self.llm.generate_narrative(
            data=data,
            narrative_type="summary",
            max_length=300,
        )
        
        return narrative
    
    async def generate_talking_points(
        self,
        data: Dict[str, Any],
        audience: str = "cfo",
    ) -> List[str]:
        """
        Generate talking points for a meeting.
        
        Args:
            data: Financial data to summarize
            audience: Target audience (cfo, board, team)
        
        Returns:
            List of talking point strings
        """
        narrative = await self.llm.generate_narrative(
            data={
                "financial_data": data,
                "audience": audience,
            },
            narrative_type="talking_points",
            max_length=400,
        )
        
        # Parse bullet points from narrative
        lines = narrative.strip().split("\n")
        points = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                points.append(line.lstrip("-•* "))
            elif line and not line.endswith(":"):
                points.append(line)
        
        return points[:10]  # Max 10 points
    
    async def generate_board_pack_narrative(
        self,
        section: str,
        data: Dict[str, Any],
    ) -> str:
        """
        Generate formal narrative for board pack.
        
        Args:
            section: Section name (highlights, risks, forecast, etc.)
            data: Section-specific data
        
        Returns:
            Formal narrative text
        """
        section_prompts = {
            "highlights": "Summarize the key financial highlights for board review.",
            "risks": "Outline the key financial risks and mitigation strategies.",
            "forecast": "Describe the cash forecast outlook and key assumptions.",
            "variance": "Explain significant variances from budget/plan.",
            "actions": "Describe management actions taken and planned.",
        }
        
        prompt_context = section_prompts.get(section, "Provide a summary for the board.")
        
        narrative = await self.llm.generate_narrative(
            data={
                "section": section,
                "context": prompt_context,
                "data": data,
            },
            narrative_type="board_pack",
            max_length=400,
        )
        
        return narrative
    
    async def generate_variance_explanation(
        self,
        variance_data: Dict[str, Any],
    ) -> str:
        """
        Generate plain-English explanation of a variance.
        
        Args:
            variance_data: Variance details
        
        Returns:
            Human-readable explanation
        """
        analysis = await self.llm.analyze_variance(
            variance_data,
            context={"request": "Explain this variance in plain English for a CFO."},
        )
        
        return analysis.get("explanation", "Variance analysis not available.")
    
    async def generate_recommendation_narrative(
        self,
        situation: str,
        options: List[Dict[str, Any]],
        recommended: List[str],
        reasoning: str,
    ) -> str:
        """
        Generate narrative explaining recommendations.
        
        Args:
            situation: Description of the situation
            options: Available options
            recommended: Recommended option IDs
            reasoning: Why these are recommended
        
        Returns:
            Narrative explaining the recommendation
        """
        data = {
            "situation": situation,
            "options": options,
            "recommended": recommended,
            "reasoning": reasoning,
        }
        
        narrative = await self.llm.generate_narrative(
            data=data,
            narrative_type="summary",
            max_length=250,
        )
        
        return narrative
