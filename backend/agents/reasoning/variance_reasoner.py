"""
Variance Reasoner

Uses LLM to explain variances in natural language with proper categorization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

from .llm_client import FPALLMClient, LLMConfig
from ..models.variance import (
    VarianceItem, CategorizedVariance, RootCause, VarianceCategory
)

logger = logging.getLogger(__name__)


class VarianceReasoner:
    """
    Uses GPT-4o to explain variances in natural language.
    
    Takes structured variance data from the VarianceWorker and generates
    human-readable explanations with proper categorization.
    """
    
    def __init__(self, llm_client: Optional[FPALLMClient] = None):
        self.llm = llm_client or FPALLMClient()
    
    async def categorize_variance(
        self,
        variance: VarianceItem,
        context: Dict[str, Any],
    ) -> CategorizedVariance:
        """
        Categorize a variance into root causes using LLM.
        
        Args:
            variance: The variance to analyze
            context: Additional context (transactions, history, etc.)
        
        Returns:
            CategorizedVariance with root causes
        """
        # Prepare data for LLM
        variance_data = {
            "amount": float(variance.variance_amount),
            "expected": float(variance.expected_amount),
            "actual": float(variance.actual_amount),
            "period": variance.period,
            "variance_pct": variance.variance_pct,
            "category": variance.category,
        }
        
        # Call LLM for analysis
        analysis = await self.llm.analyze_variance(variance_data, context)
        
        # Convert LLM response to root causes
        root_causes = []
        category_totals = {
            VarianceCategory.TIMING: Decimal("0"),
            VarianceCategory.VOLUME: Decimal("0"),
            VarianceCategory.PRICE_RATE: Decimal("0"),
            VarianceCategory.MIX: Decimal("0"),
            VarianceCategory.ONE_TIME: Decimal("0"),
            VarianceCategory.ERROR: Decimal("0"),
        }
        
        # Parse categories from LLM response
        llm_categories = analysis.get("categories", [])
        explanation = analysis.get("explanation", "")
        
        # Distribute variance across categories
        # This is a simplified allocation - in production, would use more sophisticated logic
        if llm_categories:
            per_category = variance.variance_amount / len(llm_categories)
            
            for cat_str in llm_categories:
                try:
                    category = VarianceCategory(cat_str.lower())
                except ValueError:
                    category = VarianceCategory.ERROR
                
                category_totals[category] += per_category
                
                root_causes.append(RootCause(
                    category=category,
                    amount=per_category,
                    currency=variance.currency,
                    description=f"LLM-identified {category.value} variance",
                ))
        
        # Add explanation to variance item
        variance.explanation = explanation
        
        return CategorizedVariance(
            variance_item=variance,
            timing_total=category_totals[VarianceCategory.TIMING],
            volume_total=category_totals[VarianceCategory.VOLUME],
            price_rate_total=category_totals[VarianceCategory.PRICE_RATE],
            mix_total=category_totals[VarianceCategory.MIX],
            one_time_total=category_totals[VarianceCategory.ONE_TIME],
            error_total=category_totals[VarianceCategory.ERROR],
            root_causes=root_causes,
        )
    
    async def explain_variance(
        self,
        categorized: CategorizedVariance,
    ) -> str:
        """
        Generate natural language explanation of a variance.
        
        Args:
            categorized: Categorized variance with root causes
        
        Returns:
            Human-readable explanation
        """
        # If we already have an explanation from categorization, enhance it
        if categorized.variance_item.explanation:
            return categorized.variance_item.explanation
        
        # Otherwise, generate new explanation
        variance = categorized.variance_item
        
        # Build context from root causes
        context = {
            "variance_amount": str(variance.variance_amount),
            "root_causes": [
                {
                    "category": rc.category.value,
                    "amount": str(rc.amount),
                    "description": rc.description,
                }
                for rc in categorized.root_causes
            ],
            "timing_total": str(categorized.timing_total),
            "volume_total": str(categorized.volume_total),
            "price_rate_total": str(categorized.price_rate_total),
        }
        
        # Generate explanation via LLM
        explanation = await self.llm.generate_narrative(
            data=context,
            narrative_type="summary",
            max_length=200,
        )
        
        return explanation
    
    async def explain_forecast_drift(
        self,
        previous_forecast: Dict[str, Any],
        current_forecast: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Explain why the forecast changed week-over-week.
        
        Args:
            previous_forecast: Last week's forecast
            current_forecast: This week's forecast
            context: Additional context
        
        Returns:
            Explanation with categorized drivers
        """
        drift_data = {
            "previous": previous_forecast,
            "current": current_forecast,
            "difference": {
                k: float(current_forecast.get(k, 0)) - float(previous_forecast.get(k, 0))
                for k in set(previous_forecast.keys()) | set(current_forecast.keys())
                if isinstance(previous_forecast.get(k), (int, float, Decimal))
            },
        }
        
        analysis = await self.llm.analyze_variance(drift_data, context)
        
        return {
            "explanation": analysis.get("explanation", ""),
            "drivers": analysis.get("categories", []),
            "actions": analysis.get("actions", []),
            "confidence": analysis.get("confidence", "medium"),
        }
    
    async def generate_variance_summary(
        self,
        variances: List[CategorizedVariance],
    ) -> str:
        """
        Generate executive summary of multiple variances.
        
        Args:
            variances: List of categorized variances
        
        Returns:
            Executive summary text
        """
        if not variances:
            return "No significant variances to report."
        
        # Aggregate by category
        by_category = {}
        total = Decimal("0")
        
        for v in variances:
            total += v.variance_item.variance_amount
            for rc in v.root_causes:
                cat = rc.category.value
                if cat not in by_category:
                    by_category[cat] = Decimal("0")
                by_category[cat] += rc.amount
        
        data = {
            "total_variance": str(total),
            "variance_count": len(variances),
            "by_category": {k: str(v) for k, v in by_category.items()},
            "material_items": [
                v.variance_item.to_dict()
                for v in variances
                if v.variance_item.is_material
            ][:5],  # Top 5 material
        }
        
        summary = await self.llm.generate_narrative(
            data=data,
            narrative_type="summary",
            max_length=300,
        )
        
        return summary
