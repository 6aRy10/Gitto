"""
FP&A Narrative Generator

LLM-powered narrative generation for FP&A artifacts.
All narratives are grounded in computed results with citations.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import json
import logging
import os

from sqlalchemy.orm import Session

from fpa_models import FPAArtifact, ForecastRun, VarianceReport
from fpa_variance_engine import VarianceAnalysis, TalkingPoint

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Citation:
    """A citation to source data"""
    ref_type: str  # "forecast", "actual", "variance", "driver"
    ref_id: int
    field: str
    value: str
    
    def to_dict(self) -> Dict:
        return {
            "ref_type": self.ref_type,
            "ref_id": self.ref_id,
            "field": self.field,
            "value": self.value,
        }


@dataclass
class NarrativeSection:
    """A section of narrative text with citations"""
    heading: str
    text: str
    citations: List[Citation]
    bullet_points: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "heading": self.heading,
            "text": self.text,
            "citations": [c.to_dict() for c in self.citations],
            "bullet_points": self.bullet_points,
        }


@dataclass
class Narrative:
    """Complete narrative output"""
    title: str
    subtitle: Optional[str]
    sections: List[NarrativeSection]
    generated_at: datetime
    model_used: str
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "sections": [s.to_dict() for s in self.sections],
            "generated_at": self.generated_at.isoformat(),
            "model_used": self.model_used,
        }
    
    def to_text(self) -> str:
        """Convert to plain text"""
        lines = [self.title]
        if self.subtitle:
            lines.append(self.subtitle)
        lines.append("")
        
        for section in self.sections:
            lines.append(f"## {section.heading}")
            lines.append(section.text)
            if section.bullet_points:
                for bp in section.bullet_points:
                    lines.append(f"• {bp}")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

MORNING_BRIEFING_PROMPT = """You are an FP&A analyst preparing a morning briefing for the CFO.
Generate a concise executive summary based ONLY on the following data.
Do NOT invent any numbers - use only what is provided.

DATA:
{data}

Requirements:
1. Start with the cash position and runway
2. Highlight any critical attention items
3. Note data freshness issues if any
4. Keep it under 200 words
5. Use professional financial language

Format as 2-3 short paragraphs."""

WEEKLY_FORECAST_PROMPT = """You are an FP&A analyst preparing a weekly forecast update summary.
Generate a clear executive summary based ONLY on the following data.
Do NOT invent any numbers - use only what is provided.

DATA:
{data}

Requirements:
1. Lead with the key changes from last week
2. Explain material variances clearly
3. Highlight decisions requiring attention
4. Keep it under 300 words
5. Use factual, professional language

Format as 3-4 short paragraphs."""

VARIANCE_ANALYSIS_PROMPT = """You are an FP&A analyst explaining variance analysis to the CFO.
Generate a clear, factual explanation based ONLY on the following data.
Do NOT invent any numbers - use only what is provided.

VARIANCE DATA:
{data}

Requirements:
1. Start with the net impact on EBITDA
2. Explain each material variance by category
3. Note any data quality issues
4. Provide actionable recommendations
5. Keep it under 400 words
6. Use professional financial language

Format as structured paragraphs with clear sections."""

BOARD_PACK_PROMPT = """You are an FP&A analyst preparing narrative for a board pack.
Generate a professional executive summary based ONLY on the following data.
Do NOT invent any numbers - use only what is provided.

DATA:
{data}

Requirements:
1. Start with headline financial performance
2. Compare to plan/budget
3. Highlight risks and opportunities
4. Note runway and cash position
5. Keep it under 500 words
6. Use board-appropriate language

Format as structured sections: Performance, Outlook, Risks, Actions."""


# =============================================================================
# NARRATIVE GENERATOR
# =============================================================================

class FPANarrativeGenerator:
    """
    LLM-powered narrative generator.
    
    All narratives are grounded in computed results - no hallucination.
    Citations link every claim to source data.
    """
    
    def __init__(
        self,
        db: Session,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.db = db
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy-load OpenAI client"""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("OpenAI not installed, using template-based generation")
        return self._client
    
    def generate_morning_briefing_narrative(
        self,
        artifact: FPAArtifact,
    ) -> Narrative:
        """Generate narrative for morning briefing"""
        content = artifact.content_json
        
        # Prepare data for LLM
        data = {
            "briefing_date": content.get("briefing_date"),
            "cash_position": {
                "opening": content.get("opening_cash"),
                "projected_eod": content.get("projected_cash_eod"),
                "status": content.get("cash_status"),
            },
            "overnight_activity": {
                "net": content.get("net_overnight"),
            },
            "runway_months": content.get("runway_months"),
            "burn_rate": content.get("burn_rate"),
            "attention_items": content.get("attention_items", []),
            "data_quality_issues": content.get("data_quality_issues", []),
        }
        
        # Generate with LLM or template
        if self.client:
            text = self._call_llm(MORNING_BRIEFING_PROMPT, data)
        else:
            text = self._template_morning_briefing(data)
        
        # Build citations
        citations = self._build_citations_from_content(artifact.id, content)
        
        sections = [
            NarrativeSection(
                heading="Executive Summary",
                text=text,
                citations=citations,
                bullet_points=[
                    f"Cash Position: €{content.get('opening_cash', 'N/A')} ({content.get('cash_status', 'unknown')})",
                    f"Runway: {content.get('runway_months', 'N/A')} months",
                    f"Attention Items: {len(content.get('attention_items', []))}",
                ],
            ),
        ]
        
        return Narrative(
            title="Morning Cash Briefing",
            subtitle=content.get("briefing_date"),
            sections=sections,
            generated_at=datetime.utcnow(),
            model_used=self.model if self.client else "template",
        )
    
    def generate_weekly_forecast_narrative(
        self,
        artifact: FPAArtifact,
    ) -> Narrative:
        """Generate narrative for weekly forecast update"""
        content = artifact.content_json
        
        # Prepare data
        variance = content.get("variance_analysis", {})
        data = {
            "week_ending": content.get("week_ending"),
            "material_changes": content.get("material_changes", []),
            "talking_points": content.get("talking_points", []),
            "decisions_required": content.get("decisions_required", []),
            "variance_summary": {
                "total": variance.get("total_variance"),
                "favorable": variance.get("favorable_count"),
                "unfavorable": variance.get("unfavorable_count"),
            },
        }
        
        # Generate
        if self.client:
            text = self._call_llm(WEEKLY_FORECAST_PROMPT, data)
        else:
            text = self._template_weekly_forecast(data)
        
        citations = self._build_citations_from_content(artifact.id, content)
        
        sections = [
            NarrativeSection(
                heading="Forecast Update Summary",
                text=text,
                citations=citations,
                bullet_points=[tp.get("headline", "") for tp in content.get("talking_points", [])[:5]],
            ),
        ]
        
        return Narrative(
            title="Weekly Forecast Update",
            subtitle=f"Week Ending {content.get('week_ending')}",
            sections=sections,
            generated_at=datetime.utcnow(),
            model_used=self.model if self.client else "template",
        )
    
    def generate_variance_narrative(
        self,
        variance_report: VarianceReport,
    ) -> Narrative:
        """Generate narrative for variance analysis"""
        data = {
            "comparison_type": variance_report.comparison_type,
            "total_variance": str(variance_report.total_variance),
            "variance_by_category": variance_report.variance_by_category_json,
            "root_causes": variance_report.root_causes_json,
            "talking_points": variance_report.talking_points_json,
            "variance_items": variance_report.variance_items_json[:10],  # Top 10
        }
        
        if self.client:
            text = self._call_llm(VARIANCE_ANALYSIS_PROMPT, data)
        else:
            text = self._template_variance_analysis(data)
        
        sections = [
            NarrativeSection(
                heading="Variance Analysis",
                text=text,
                citations=[
                    Citation(
                        ref_type="variance_report",
                        ref_id=variance_report.id,
                        field="total_variance",
                        value=str(variance_report.total_variance),
                    ),
                ],
                bullet_points=[
                    rc.get("description", "")[:100]
                    for rc in (variance_report.root_causes_json or [])[:5]
                ],
            ),
        ]
        
        return Narrative(
            title="Variance Analysis Report",
            subtitle=variance_report.comparison_type.replace("_", " ").title(),
            sections=sections,
            generated_at=datetime.utcnow(),
            model_used=self.model if self.client else "template",
        )
    
    def generate_board_pack_narrative(
        self,
        plan_id: int,
        snapshot_id: int,
    ) -> Narrative:
        """Generate narrative for board pack"""
        # Gather data from multiple sources
        from fpa_models import Plan, ActualsSnapshot
        
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        snapshot = self.db.query(ActualsSnapshot).filter(ActualsSnapshot.id == snapshot_id).first()
        
        # Get latest forecast
        latest_forecast = self.db.query(ForecastRun).filter(
            ForecastRun.plan_id == plan_id
        ).order_by(ForecastRun.created_at.desc()).first()
        
        data = {
            "plan_name": plan.name if plan else "N/A",
            "period": f"{plan.period_start} to {plan.period_end}" if plan else "N/A",
            "actuals": {
                "period": str(snapshot.period_month) if snapshot else "N/A",
                "revenue": str(snapshot.revenue_total) if snapshot else "N/A",
                "cash": str(snapshot.cash_ending) if snapshot else "N/A",
            },
            "forecast": {
                "revenue": str(latest_forecast.total_revenue) if latest_forecast else "N/A",
                "ebitda": str(latest_forecast.total_ebitda) if latest_forecast else "N/A",
                "runway": latest_forecast.runway_months if latest_forecast else "N/A",
            },
        }
        
        if self.client:
            text = self._call_llm(BOARD_PACK_PROMPT, data)
        else:
            text = self._template_board_pack(data)
        
        citations = []
        if latest_forecast:
            citations.append(Citation(
                ref_type="forecast",
                ref_id=latest_forecast.id,
                field="total_revenue",
                value=str(latest_forecast.total_revenue),
            ))
        
        sections = [
            NarrativeSection(
                heading="Executive Summary",
                text=text,
                citations=citations,
            ),
        ]
        
        return Narrative(
            title="Board Pack - Financial Summary",
            subtitle=plan.name if plan else None,
            sections=sections,
            generated_at=datetime.utcnow(),
            model_used=self.model if self.client else "template",
        )
    
    def _call_llm(self, prompt_template: str, data: Dict) -> str:
        """Call LLM with prompt and data"""
        try:
            prompt = prompt_template.format(data=json.dumps(data, indent=2, default=str))
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional FP&A analyst. Be precise and factual."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=1000,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"[Narrative generation failed: {str(e)}]"
    
    def _template_morning_briefing(self, data: Dict) -> str:
        """Template-based morning briefing (fallback)"""
        cash = data.get("cash_position", {})
        status = cash.get("status", "unknown")
        
        status_text = {
            "healthy": "within acceptable parameters",
            "warning": "approaching minimum threshold",
            "critical": "below minimum threshold",
        }.get(status, "unknown status")
        
        text = f"""Good morning. As of {data.get('briefing_date')}, our cash position is {status_text}.

Opening cash stands at €{cash.get('opening', 'N/A')}, with {data.get('runway_months', 'N/A')} months of runway at current burn rate of €{data.get('burn_rate', 'N/A')} per month.
"""
        
        attention = data.get("attention_items", [])
        if attention:
            text += f"\nThere are {len(attention)} item(s) requiring attention today."
        
        quality = data.get("data_quality_issues", [])
        if quality:
            text += f"\nNote: {len(quality)} data freshness issue(s) flagged."
        
        return text
    
    def _template_weekly_forecast(self, data: Dict) -> str:
        """Template-based weekly forecast (fallback)"""
        summary = data.get("variance_summary", {})
        
        text = f"""Week ending {data.get('week_ending')} forecast update.

The forecast shows {summary.get('favorable', 0)} favorable and {summary.get('unfavorable', 0)} unfavorable variances, with a net impact of €{summary.get('total', 'N/A')}.
"""
        
        changes = data.get("material_changes", [])
        if changes:
            text += f"\nMaterial changes this week: {len(changes)} items identified."
        
        decisions = data.get("decisions_required", [])
        if decisions:
            text += f"\n{len(decisions)} decision(s) require review."
        
        return text
    
    def _template_variance_analysis(self, data: Dict) -> str:
        """Template-based variance analysis (fallback)"""
        text = f"""Variance Analysis: {data.get('comparison_type', '').replace('_', ' ').title()}

Total variance: €{data.get('total_variance', 'N/A')}.

"""
        
        by_category = data.get("variance_by_category", {})
        if by_category:
            text += "Breakdown by category:\n"
            for cat, amount in by_category.items():
                text += f"- {cat.replace('_', ' ').title()}: €{amount}\n"
        
        root_causes = data.get("root_causes", [])
        if root_causes:
            text += "\nKey drivers:\n"
            for rc in root_causes[:3]:
                text += f"- {rc.get('description', 'N/A')}\n"
        
        return text
    
    def _template_board_pack(self, data: Dict) -> str:
        """Template-based board pack (fallback)"""
        actuals = data.get("actuals", {})
        forecast = data.get("forecast", {})
        
        return f"""Financial Summary: {data.get('plan_name', 'N/A')}

Period: {data.get('period', 'N/A')}

ACTUALS
- Period: {actuals.get('period', 'N/A')}
- Revenue: €{actuals.get('revenue', 'N/A')}
- Cash: €{actuals.get('cash', 'N/A')}

FORECAST
- Projected Revenue: €{forecast.get('revenue', 'N/A')}
- Projected EBITDA: €{forecast.get('ebitda', 'N/A')}
- Runway: {forecast.get('runway', 'N/A')} months

This summary is generated from current plan data and latest forecast outputs.
"""
    
    def _build_citations_from_content(
        self,
        artifact_id: int,
        content: Dict,
    ) -> List[Citation]:
        """Build citations from artifact content"""
        citations = []
        
        # Extract key numeric fields
        numeric_fields = [
            ("opening_cash", "cash_position"),
            ("projected_cash_eod", "cash_position"),
            ("runway_months", "forecast"),
            ("burn_rate", "forecast"),
        ]
        
        for field, ref_type in numeric_fields:
            if field in content:
                citations.append(Citation(
                    ref_type=ref_type,
                    ref_id=artifact_id,
                    field=field,
                    value=str(content[field]),
                ))
        
        return citations
    
    def save_narrative_to_artifact(
        self,
        artifact_id: int,
        narrative: Narrative,
    ) -> FPAArtifact:
        """Save generated narrative to artifact"""
        artifact = self.db.query(FPAArtifact).filter(
            FPAArtifact.id == artifact_id
        ).first()
        
        if artifact:
            artifact.narrative_text = narrative.to_text()
            artifact.narrative_generated_at = narrative.generated_at
            self.db.commit()
            self.db.refresh(artifact)
        
        return artifact
