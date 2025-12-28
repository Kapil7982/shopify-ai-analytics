"""
ShopifyQL Query Generator - Generates ShopifyQL queries using LLM

ShopifyQL is Shopify's analytics query language that allows querying
sales, orders, inventory, and other store metrics.
"""
import structlog
from typing import Dict, Any, List

from app.models.schemas import QuestionIntent, DataSource, ShopifyQLQuery

logger = structlog.get_logger()


# ShopifyQL schema reference for the LLM
SHOPIFYQL_SCHEMA = """
ShopifyQL Schema Reference:

## Available Tables:
1. sales - Sales data with revenue, discounts, taxes
2. orders - Order information
3. products - Product catalog
4. customers - Customer data

## Common Fields:

### sales table:
- day, week, month, year (time dimensions)
- product_title, product_id, product_type, product_vendor
- variant_title, variant_sku
- gross_sales, discounts, returns, net_sales, taxes, total_sales
- ordered_item_quantity
- billing_country, billing_region, billing_city

### orders table:
- order_id, order_name
- created_at, processed_at
- total_price, subtotal_price
- financial_status, fulfillment_status

### products table:
- product_id, product_title, product_type, product_vendor
- variant_id, variant_title, variant_sku
- inventory_quantity

### customers table:
- customer_id, customer_email
- orders_count, total_spent
- created_at

## Syntax:
FROM <table>
SHOW <fields>
GROUP BY <dimensions>
WHERE <conditions>
SINCE <date> UNTIL <date>
ORDER BY <field> DESC/ASC
LIMIT <number>

## Date Functions:
- SINCE -30d (last 30 days)
- SINCE -7d (last 7 days)
- SINCE -90d (last 90 days)
- SINCE 2024-01-01 (specific date)

## Aggregation Functions:
- SUM(), COUNT(), AVG(), MIN(), MAX()

## Examples:
1. Top selling products last week:
   FROM sales
   SHOW product_title, SUM(ordered_item_quantity) AS units_sold, SUM(net_sales) AS revenue
   GROUP BY product_title
   SINCE -7d
   ORDER BY units_sold DESC
   LIMIT 5

2. Daily sales for last 30 days:
   FROM sales
   SHOW day, SUM(net_sales) AS daily_revenue
   GROUP BY day
   SINCE -30d
   ORDER BY day ASC

3. Inventory levels:
   FROM products
   SHOW product_title, variant_sku, inventory_quantity
   ORDER BY inventory_quantity ASC
   LIMIT 20
"""


class ShopifyQLGenerator:
    """
    Generates ShopifyQL queries based on user intent using LLM.
    Includes validation and fallback to GraphQL when needed.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def generate(
        self,
        intent: QuestionIntent,
        plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a ShopifyQL query based on the intent.

        Args:
            intent: Parsed user intent
            plan: Execution plan

        Returns:
            Dictionary with query and metadata
        """

        # Check if ShopifyQL can handle this query type
        if self._should_use_graphql(intent):
            return {
                "query": None,
                "query_type": "graphql",
                "reason": "Query requires data not available in ShopifyQL"
            }

        # Generate ShopifyQL using LLM
        query = await self._generate_with_llm(intent)

        # Validate the query
        validation = self._validate_query(query)

        if not validation["is_valid"]:
            # Try to fix the query
            query = await self._fix_query(query, validation["errors"])
            validation = self._validate_query(query)

        return {
            "query": query,
            "query_type": "shopifyql",
            "is_valid": validation["is_valid"],
            "validation_errors": validation.get("errors", []),
            "description": self._describe_query(intent)
        }

    def _should_use_graphql(self, intent: QuestionIntent) -> bool:
        """Determine if GraphQL should be used instead of ShopifyQL"""

        # ShopifyQL is best for aggregated analytics
        # Use GraphQL for detailed entity queries
        graphql_intents = [
            "customer_details",
            "order_details",
            "product_details"
        ]

        return intent.primary_intent in graphql_intents

    async def _generate_with_llm(self, intent: QuestionIntent) -> str:
        """Generate ShopifyQL query using LLM"""

        prompt = f"""Generate a ShopifyQL query based on this intent.

{SHOPIFYQL_SCHEMA}

User Intent:
- Primary intent: {intent.primary_intent}
- Data sources needed: {[s.value for s in intent.data_sources]}
- Time period: {intent.time_period or 'last 30 days'}
- Metrics to calculate: {intent.metrics}
- Filters: {intent.filters}
- Aggregation type: {intent.aggregation}

Generate ONLY the ShopifyQL query, no explanation. The query must be syntactically correct.
If asking about inventory projections or reordering, calculate daily average sales and project forward.
"""

        response = await self.llm_client.generate(prompt, response_format="text", temperature=0.3)

        # Clean up the response
        query = response.strip()
        if query.startswith("```"):
            query = query.split("```")[1]
            if query.startswith("sql") or query.startswith("shopifyql"):
                query = query[query.index("\n")+1:]

        return query.strip()

    def _validate_query(self, query: str) -> Dict[str, Any]:
        """Basic validation of ShopifyQL syntax"""

        errors = []

        if not query:
            return {"is_valid": False, "errors": ["Query is empty"]}

        query_upper = query.upper()

        # Check for required FROM clause
        if "FROM" not in query_upper:
            errors.append("Missing FROM clause")

        # Check for valid table names
        valid_tables = ["SALES", "ORDERS", "PRODUCTS", "CUSTOMERS"]
        has_valid_table = any(table in query_upper for table in valid_tables)
        if not has_valid_table:
            errors.append("Invalid or missing table name")

        # Check for SHOW clause (required in ShopifyQL)
        if "SHOW" not in query_upper:
            errors.append("Missing SHOW clause")

        # Check for common syntax errors
        if query_upper.count("(") != query_upper.count(")"):
            errors.append("Unmatched parentheses")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    async def _fix_query(self, query: str, errors: List[str]) -> str:
        """Attempt to fix a query with validation errors"""

        prompt = f"""Fix this ShopifyQL query. It has the following errors: {errors}

Original query:
{query}

{SHOPIFYQL_SCHEMA}

Return ONLY the corrected query, no explanation."""

        response = await self.llm_client.generate(prompt, response_format="text", temperature=0.2)
        return response.strip()

    def _describe_query(self, intent: QuestionIntent) -> str:
        """Generate a human-readable description of what the query does"""

        descriptions = {
            "inventory_forecast": "Analyzing sales velocity and current inventory to project future needs",
            "sales_analysis": "Aggregating sales data to identify top performers and trends",
            "customer_analysis": "Analyzing customer purchase patterns and loyalty metrics",
            "product_performance": "Evaluating product performance metrics",
            "general_analysis": "Retrieving relevant store analytics"
        }

        return descriptions.get(intent.primary_intent, "Analyzing store data")


class QueryTemplates:
    """Pre-built query templates for common use cases"""

    @staticmethod
    def top_selling_products(days: int = 7, limit: int = 5) -> str:
        return f"""
FROM sales
SHOW product_title, SUM(ordered_item_quantity) AS units_sold, SUM(net_sales) AS revenue
GROUP BY product_title
SINCE -{days}d
ORDER BY units_sold DESC
LIMIT {limit}
"""

    @staticmethod
    def daily_sales(days: int = 30) -> str:
        return f"""
FROM sales
SHOW day, SUM(net_sales) AS daily_revenue, SUM(ordered_item_quantity) AS units
GROUP BY day
SINCE -{days}d
ORDER BY day ASC
"""

    @staticmethod
    def product_inventory() -> str:
        return """
FROM products
SHOW product_title, variant_sku, inventory_quantity
WHERE inventory_quantity > 0
ORDER BY inventory_quantity ASC
"""

    @staticmethod
    def low_stock_alert(threshold: int = 10) -> str:
        return f"""
FROM products
SHOW product_title, variant_sku, inventory_quantity
WHERE inventory_quantity <= {threshold}
ORDER BY inventory_quantity ASC
"""

    @staticmethod
    def sales_by_product(days: int = 30) -> str:
        return f"""
FROM sales
SHOW product_title, SUM(ordered_item_quantity) AS total_sold, SUM(net_sales) AS total_revenue
GROUP BY product_title
SINCE -{days}d
ORDER BY total_sold DESC
"""
