"""
Analytics Agent - Core AI agent for processing Shopify analytics questions

This agent implements an agentic workflow that:
1. Understands the user's intent
2. Plans which data sources are needed
3. Generates ShopifyQL queries
4. Executes queries and validates results
5. Explains results in business-friendly language
"""
import structlog
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.agent.llm_client import LLMClient
from app.agent.shopify_client import ShopifyClient
from app.agent.query_generator import ShopifyQLGenerator
from app.agent.result_explainer import ResultExplainer
from app.models.schemas import QuestionIntent, DataSource

logger = structlog.get_logger()


class AnalyticsAgent:
    """
    AI Agent for analyzing Shopify store data using natural language questions.

    The agent follows this workflow:
    1. Parse and understand the question (intent classification)
    2. Plan the data retrieval strategy
    3. Generate appropriate ShopifyQL queries
    4. Execute queries against Shopify API
    5. Process and validate the results
    6. Generate human-friendly explanations
    """

    def __init__(self, store_id: str, access_token: str):
        self.store_id = store_id
        self.access_token = access_token

        # Initialize components
        self.llm_client = LLMClient()
        self.shopify_client = ShopifyClient(store_id, access_token)
        self.query_generator = ShopifyQLGenerator(self.llm_client)
        self.result_explainer = ResultExplainer(self.llm_client)

    async def process_question(
        self,
        question: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language question and return insights.

        Args:
            question: The user's question in natural language
            context: Optional additional context

        Returns:
            Dictionary containing answer, confidence, and metadata
        """
        logger.info("Processing question", question=question[:100])

        # Step 1: Understand the intent
        intent = await self._understand_intent(question, context)
        logger.info("Intent understood", intent=intent.primary_intent, sources=intent.data_sources)

        # Step 2: Plan the data retrieval
        plan = await self._create_plan(intent)
        logger.info("Plan created", steps=len(plan))

        # Step 3: Generate ShopifyQL query
        query_result = await self._generate_query(intent, plan)
        logger.info("Query generated", query=query_result.get("query", "")[:100])

        # Step 4: Execute the query
        data = await self._execute_query(query_result, intent)
        logger.info("Query executed", has_data=bool(data))

        # Step 5: Generate explanation
        result = await self._explain_results(question, intent, data, query_result)
        logger.info("Explanation generated", confidence=result["confidence"])

        return result

    async def _understand_intent(
        self,
        question: str,
        context: Optional[str]
    ) -> QuestionIntent:
        """Parse the user's question to understand intent and required data"""

        prompt = f"""Analyze this question about a Shopify store and extract the intent.

Question: {question}
{f'Additional context: {context}' if context else ''}

Identify:
1. Primary intent (e.g., inventory_forecast, sales_analysis, customer_analysis, product_performance)
2. Required data sources (orders, products, inventory, customers)
3. Time period (if mentioned)
4. Specific metrics needed
5. Any filters (product names, categories, etc.)
6. Type of aggregation (sum, average, count, etc.)

Respond in JSON format:
{{
    "primary_intent": "string",
    "data_sources": ["orders", "products", "inventory", "customers"],
    "time_period": "last 30 days" or null,
    "metrics": ["revenue", "units_sold"],
    "filters": {{"product_name": "value"}},
    "aggregation": "sum" or null
}}"""

        response = await self.llm_client.generate(prompt, response_format="json")

        return QuestionIntent(
            primary_intent=response.get("primary_intent", "general_analysis"),
            data_sources=[DataSource(s) for s in response.get("data_sources", ["orders"])],
            time_period=response.get("time_period"),
            metrics=response.get("metrics", []),
            filters=response.get("filters", {}),
            aggregation=response.get("aggregation")
        )

    async def _create_plan(self, intent: QuestionIntent) -> list:
        """Create an execution plan based on the intent"""

        plan = []

        # Determine which queries are needed based on intent
        if DataSource.INVENTORY in intent.data_sources:
            plan.append({
                "step": "fetch_inventory",
                "description": "Get current inventory levels",
                "priority": 1
            })

        if DataSource.ORDERS in intent.data_sources or DataSource.SALES in intent.data_sources:
            plan.append({
                "step": "fetch_sales_data",
                "description": "Get sales/order data for the specified period",
                "priority": 1
            })

        if DataSource.CUSTOMERS in intent.data_sources:
            plan.append({
                "step": "fetch_customer_data",
                "description": "Get customer information",
                "priority": 2
            })

        if DataSource.PRODUCTS in intent.data_sources:
            plan.append({
                "step": "fetch_product_data",
                "description": "Get product information",
                "priority": 2
            })

        # Add analysis step
        plan.append({
            "step": "analyze_data",
            "description": "Calculate metrics and generate insights",
            "priority": 3
        })

        return sorted(plan, key=lambda x: x["priority"])

    async def _generate_query(
        self,
        intent: QuestionIntent,
        plan: list
    ) -> Dict[str, Any]:
        """Generate the appropriate ShopifyQL query"""

        return await self.query_generator.generate(intent, plan)

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _execute_query(
        self,
        query_result: Dict[str, Any],
        intent: QuestionIntent
    ) -> Dict[str, Any]:
        """Execute the query against Shopify API"""

        query = query_result.get("query")
        query_type = query_result.get("query_type", "shopifyql")

        if query_type == "shopifyql" and query:
            # Execute ShopifyQL query
            data = await self.shopify_client.execute_shopifyql(query)
        else:
            # Fall back to GraphQL for data that ShopifyQL doesn't support well
            data = await self.shopify_client.execute_graphql(intent)

        return self._validate_and_process_data(data, intent)

    def _validate_and_process_data(
        self,
        data: Dict[str, Any],
        intent: QuestionIntent
    ) -> Dict[str, Any]:
        """Validate and pre-process the raw data"""

        if not data:
            return {
                "is_empty": True,
                "message": "No data found for the specified criteria"
            }

        # Handle Shopify API errors
        if "errors" in data:
            return {
                "is_error": True,
                "errors": data["errors"]
            }

        return {
            "is_empty": False,
            "data": data
        }

    async def _explain_results(
        self,
        question: str,
        intent: QuestionIntent,
        data: Dict[str, Any],
        query_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a human-friendly explanation of the results"""

        return await self.result_explainer.explain(
            question=question,
            intent=intent,
            data=data,
            query_used=query_result.get("query")
        )
