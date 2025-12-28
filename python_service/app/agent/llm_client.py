"""
LLM Client - Handles communication with LLM providers (OpenAI, Anthropic, or Mock)
"""
import json
import structlog
from typing import Dict, Any, Optional

from app.core.config import settings

logger = structlog.get_logger()


class LLMClient:
    """
    Client for interacting with Large Language Models.
    Supports OpenAI, Anthropic (Claude), and a mock mode for testing.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client based on configuration"""

        if self.provider == "openai":
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                self.model = settings.OPENAI_MODEL
                logger.info("Initialized OpenAI client", model=self.model)
            except ImportError:
                logger.warning("OpenAI not available, falling back to mock")
                self.provider = "mock"

        elif self.provider == "anthropic":
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                self.model = settings.ANTHROPIC_MODEL
                logger.info("Initialized Anthropic client", model=self.model)
            except ImportError:
                logger.warning("Anthropic not available, falling back to mock")
                self.provider = "mock"

        else:
            self.provider = "mock"
            logger.info("Using mock LLM client")

    async def generate(
        self,
        prompt: str,
        response_format: str = "text",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Any:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            response_format: Expected format ("text" or "json")
            temperature: Creativity parameter (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            Generated response (string or dict depending on format)
        """

        if self.provider == "openai":
            return await self._generate_openai(prompt, response_format, temperature, max_tokens)
        elif self.provider == "anthropic":
            return await self._generate_anthropic(prompt, response_format, temperature, max_tokens)
        else:
            return await self._generate_mock(prompt, response_format)

    async def _generate_openai(
        self,
        prompt: str,
        response_format: str,
        temperature: float,
        max_tokens: int
    ) -> Any:
        """Generate response using OpenAI"""

        messages = [
            {"role": "system", "content": "You are an expert Shopify analytics assistant. Provide accurate, data-driven insights."},
            {"role": "user", "content": prompt}
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        if response_format == "json":
            return json.loads(content)
        return content

    async def _generate_anthropic(
        self,
        prompt: str,
        response_format: str,
        temperature: float,
        max_tokens: int
    ) -> Any:
        """Generate response using Anthropic Claude"""

        system_prompt = "You are an expert Shopify analytics assistant. Provide accurate, data-driven insights."

        if response_format == "json":
            system_prompt += " Always respond with valid JSON only, no additional text."

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        if response_format == "json":
            return json.loads(content)
        return content

    async def _generate_mock(
        self,
        prompt: str,
        response_format: str
    ) -> Any:
        """Generate mock response for testing without API keys"""

        logger.debug("Using mock LLM response")

        # Detect intent from prompt keywords
        prompt_lower = prompt.lower()

        if response_format == "json":
            if "analyze this question" in prompt_lower:
                # Intent analysis response
                if "inventory" in prompt_lower or "stock" in prompt_lower or "reorder" in prompt_lower:
                    return {
                        "primary_intent": "inventory_forecast",
                        "data_sources": ["inventory", "orders"],
                        "time_period": "last 30 days",
                        "metrics": ["units_sold", "current_stock", "daily_average"],
                        "filters": {},
                        "aggregation": "sum"
                    }
                elif "top" in prompt_lower and ("selling" in prompt_lower or "product" in prompt_lower):
                    return {
                        "primary_intent": "sales_analysis",
                        "data_sources": ["orders", "products"],
                        "time_period": "last 7 days",
                        "metrics": ["units_sold", "revenue"],
                        "filters": {},
                        "aggregation": "sum"
                    }
                elif "customer" in prompt_lower or "repeat" in prompt_lower:
                    return {
                        "primary_intent": "customer_analysis",
                        "data_sources": ["customers", "orders"],
                        "time_period": "last 90 days",
                        "metrics": ["order_count", "customer_count"],
                        "filters": {},
                        "aggregation": "count"
                    }
                else:
                    return {
                        "primary_intent": "general_analysis",
                        "data_sources": ["orders"],
                        "time_period": "last 30 days",
                        "metrics": ["revenue"],
                        "filters": {},
                        "aggregation": "sum"
                    }
            else:
                return {"status": "ok"}
        else:
            # Text response for explanations
            if "inventory" in prompt_lower or "reorder" in prompt_lower:
                return """Based on your sales data from the last 30 days, you're selling approximately 10 units per day on average.

To avoid stockouts for the next week, I recommend reordering at least 70 units (10 units/day x 7 days).

If you want to maintain a safety buffer, consider ordering 85-100 units to account for potential demand spikes."""

            elif "top" in prompt_lower and "selling" in prompt_lower:
                return """Here are your top 5 selling products from the last week:

1. Product A - 150 units sold ($2,250 revenue)
2. Product B - 120 units sold ($1,800 revenue)
3. Product C - 95 units sold ($1,425 revenue)
4. Product D - 80 units sold ($1,200 revenue)
5. Product E - 65 units sold ($975 revenue)

Product A is clearly your best performer, generating 29% of the total revenue from these top products."""

            elif "customer" in prompt_lower or "repeat" in prompt_lower:
                return """In the last 90 days, you had 45 customers who placed repeat orders.

These repeat customers represent 23% of your total customer base but contributed to 41% of your revenue. This shows strong customer loyalty among your returning shoppers.

Consider implementing a loyalty program to encourage even more repeat purchases."""

            else:
                return """Based on your store data, here's what I found:

Your store is performing steadily with consistent order volumes. Total revenue for the period analyzed shows healthy growth patterns.

For more specific insights, try asking about particular products, time periods, or customer segments."""
