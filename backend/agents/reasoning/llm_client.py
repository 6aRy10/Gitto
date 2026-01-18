"""
LLM Client

OpenAI GPT-4o wrapper with retry logic, token tracking, and structured outputs.
"""

import os
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List, TypeVar, Type
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.3  # Lower for more consistent outputs
    max_tokens: int = 2000
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.model:
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")


@dataclass
class LLMResponse:
    """Response from LLM"""
    text: str
    tokens_used: int
    model: str
    finish_reason: str
    latency_ms: int
    raw_response: Optional[Dict] = None


@dataclass
class TokenUsage:
    """Token usage tracking"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


class FPALLMClient:
    """
    OpenAI GPT-4o client for FP&A reasoning.
    
    Features:
    - Async API calls
    - Retry with exponential backoff
    - Token usage tracking
    - Structured output parsing
    - Financial context injection
    """
    
    # System prompt for FP&A context
    SYSTEM_PROMPT = """You are an expert FP&A (Financial Planning & Analysis) analyst assistant.
Your role is to analyze financial data and provide clear, actionable insights.

Guidelines:
1. Be precise with numbers - always use proper formatting (€1,234.56)
2. When explaining variances, categorize them as: Timing, Volume, Price/Rate, Mix, One-time, or Error
3. Provide specific, actionable recommendations
4. Reference specific data points and evidence
5. Be concise but thorough
6. Flag risks and uncertainties clearly
7. Use professional financial language

When analyzing cash flow:
- Inflows are positive, outflows are negative
- Always consider timing of payments
- Note currency considerations if multiple currencies involved
"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.usage = TokenUsage()
        self._client = None
        self._initialized = False
    
    async def _ensure_client(self):
        """Lazy initialization of OpenAI client"""
        if self._initialized:
            return
        
        try:
            import openai
            
            if not self.config.api_key:
                logger.warning("No OpenAI API key configured - LLM features disabled")
                self._client = None
            else:
                self._client = openai.AsyncOpenAI(api_key=self.config.api_key)
            
            self._initialized = True
        except ImportError:
            logger.warning("OpenAI package not installed - LLM features disabled")
            self._client = None
            self._initialized = True
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Get a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Override system prompt
            temperature: Override temperature
            max_tokens: Override max tokens
        
        Returns:
            LLMResponse with text and metadata
        """
        await self._ensure_client()
        
        if not self._client:
            # Return mock response when LLM not available
            return LLMResponse(
                text="[LLM not configured - using template response]",
                tokens_used=0,
                model="mock",
                finish_reason="mock",
                latency_ms=0,
            )
        
        messages = [
            {"role": "system", "content": system_prompt or self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        start_time = datetime.utcnow()
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature or self.config.temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    timeout=self.config.timeout,
                )
                
                latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Track usage
                usage = response.usage
                self.usage.add(usage.prompt_tokens, usage.completion_tokens)
                
                return LLMResponse(
                    text=response.choices[0].message.content,
                    tokens_used=usage.total_tokens,
                    model=response.model,
                    finish_reason=response.choices[0].finish_reason,
                    latency_ms=latency_ms,
                )
                
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"LLM call failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM call failed after {self.config.max_retries} attempts: {e}")
                    raise
    
    async def analyze_variance(
        self,
        variance_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze a variance and provide explanation.
        
        Args:
            variance_data: Variance details (amount, period, etc.)
            context: Additional context (historical data, etc.)
        
        Returns:
            Analysis with categorization and explanation
        """
        prompt = f"""Analyze this financial variance:

Variance: €{variance_data.get('amount', 0):,.2f}
Period: {variance_data.get('period', 'unknown')}
Expected: €{variance_data.get('expected', 0):,.2f}
Actual: €{variance_data.get('actual', 0):,.2f}

Additional context:
{json.dumps(context, indent=2, default=str)}

Provide:
1. Root cause categorization (Timing/Volume/Price/Mix/One-time/Error)
2. Detailed explanation of what drove this variance
3. Recommended actions
4. Confidence level (high/medium/low)

Format your response as JSON with keys: categories, explanation, actions, confidence"""
        
        response = await self.complete(prompt)
        
        # Parse response
        try:
            # Try to extract JSON from response
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text)
        except json.JSONDecodeError:
            # Return structured response from text
            result = {
                "categories": ["unknown"],
                "explanation": response.text,
                "actions": [],
                "confidence": "low",
            }
        
        result["tokens_used"] = response.tokens_used
        result["latency_ms"] = response.latency_ms
        
        return result
    
    async def generate_narrative(
        self,
        data: Dict[str, Any],
        narrative_type: str = "summary",
        max_length: int = 500,
    ) -> str:
        """
        Generate narrative text from financial data.
        
        Args:
            data: Financial data to summarize
            narrative_type: Type of narrative (summary, briefing, board_pack)
            max_length: Maximum words
        
        Returns:
            Generated narrative text
        """
        type_instructions = {
            "summary": "Write a brief executive summary.",
            "briefing": "Write a morning briefing for the CFO.",
            "board_pack": "Write a formal board pack narrative section.",
            "talking_points": "Generate bullet-point talking points for a meeting.",
        }
        
        prompt = f"""{type_instructions.get(narrative_type, 'Summarize the following data.')}

Financial Data:
{json.dumps(data, indent=2, default=str)}

Requirements:
- Maximum {max_length} words
- Use professional financial language
- Highlight key metrics and trends
- Note any concerns or risks
- Be specific with numbers"""
        
        response = await self.complete(prompt, max_tokens=max_length * 2)
        return response.text
    
    async def generate_recommendations(
        self,
        situation: Dict[str, Any],
        constraints: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations.
        
        Args:
            situation: Current situation and context
            constraints: Business constraints to consider
        
        Returns:
            List of recommendations with risk assessment
        """
        prompt = f"""Given this financial situation, provide actionable recommendations:

Situation:
{json.dumps(situation, indent=2, default=str)}

Constraints:
{chr(10).join(f'- {c}' for c in constraints)}

For each recommendation provide:
1. Action to take
2. Expected impact (quantify if possible)
3. Risk level (low/medium/high)
4. Implementation timeline
5. Prerequisites

Format as JSON array of recommendations."""
        
        response = await self.complete(prompt)
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            recommendations = json.loads(text)
            if not isinstance(recommendations, list):
                recommendations = [recommendations]
        except json.JSONDecodeError:
            recommendations = [{
                "action": response.text,
                "risk": "unknown",
            }]
        
        return recommendations
    
    async def answer_question(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Answer an FP&A question with context.
        
        Args:
            question: User question
            context: Relevant financial data
        
        Returns:
            Answer with sources and confidence
        """
        prompt = f"""Answer this FP&A question based on the provided data:

Question: {question}

Available Data:
{json.dumps(context, indent=2, default=str)}

Provide:
1. Direct answer to the question
2. Supporting data points used
3. Any caveats or limitations
4. Follow-up questions the user might have

Format as JSON with keys: answer, sources, caveats, follow_ups"""
        
        response = await self.complete(prompt)
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {
                "answer": response.text,
                "sources": [],
                "caveats": [],
                "follow_ups": [],
            }
        
        return result
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        return {
            "prompt_tokens": self.usage.prompt_tokens,
            "completion_tokens": self.usage.completion_tokens,
            "total_tokens": self.usage.total_tokens,
            "estimated_cost_usd": self.usage.total_tokens * 0.00001,  # Rough estimate
        }
