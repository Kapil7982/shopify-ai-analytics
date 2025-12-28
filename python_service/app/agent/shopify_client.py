"""
Shopify Client - Handles communication with Shopify APIs
"""
import httpx
import structlog
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.models.schemas import QuestionIntent, DataSource

logger = structlog.get_logger()


class ShopifyClient:
    """
    Client for interacting with Shopify GraphQL and ShopifyQL APIs.
    """

    def __init__(self, store_id: str, access_token: str):
        self.store_id = store_id
        self.access_token = access_token
        self.api_version = settings.SHOPIFY_API_VERSION
        self.base_url = f"https://{store_id}/admin/api/{self.api_version}"

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Shopify API requests"""
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

    async def execute_shopifyql(self, query: str) -> Dict[str, Any]:
        """
        Execute a ShopifyQL query against the Shopify API.

        ShopifyQL is Shopify's query language for analytics, similar to SQL.

        Args:
            query: The ShopifyQL query string

        Returns:
            Query results as a dictionary
        """
        logger.info("Executing ShopifyQL", query=query[:100])

        graphql_query = """
        query shopifyQL($query: String!) {
            shopifyqlQuery(query: $query) {
                __typename
                ... on TableResponse {
                    tableData {
                        columns {
                            name
                            dataType
                        }
                        rowData
                    }
                }
                parseErrors {
                    code
                    message
                    range {
                        start { line character }
                        end { line character }
                    }
                }
            }
        }
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/graphql.json",
                headers=self._get_headers(),
                json={
                    "query": graphql_query,
                    "variables": {"query": query}
                },
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error("ShopifyQL request failed", status=response.status_code)
                return {"errors": [{"message": f"HTTP {response.status_code}"}]}

            data = response.json()

            # Check for parse errors
            if data.get("data", {}).get("shopifyqlQuery", {}).get("parseErrors"):
                errors = data["data"]["shopifyqlQuery"]["parseErrors"]
                logger.warning("ShopifyQL parse errors", errors=errors)
                return {"errors": errors}

            return data.get("data", {}).get("shopifyqlQuery", {})

    async def execute_graphql(self, intent: QuestionIntent) -> Dict[str, Any]:
        """
        Execute a GraphQL query based on the intent.
        Used as fallback when ShopifyQL isn't suitable.
        """
        logger.info("Executing GraphQL query", intent=intent.primary_intent)

        query = self._build_graphql_query(intent)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/graphql.json",
                headers=self._get_headers(),
                json={"query": query},
                timeout=30.0
            )

            if response.status_code != 200:
                return {"errors": [{"message": f"HTTP {response.status_code}"}]}

            return response.json().get("data", {})

    def _build_graphql_query(self, intent: QuestionIntent) -> str:
        """Build a GraphQL query based on the intent"""

        queries = []

        if DataSource.ORDERS in intent.data_sources or DataSource.SALES in intent.data_sources:
            queries.append(self._orders_query(intent))

        if DataSource.PRODUCTS in intent.data_sources:
            queries.append(self._products_query(intent))

        if DataSource.INVENTORY in intent.data_sources:
            queries.append(self._inventory_query(intent))

        if DataSource.CUSTOMERS in intent.data_sources:
            queries.append(self._customers_query(intent))

        return f"query {{ {' '.join(queries)} }}"

    def _orders_query(self, intent: QuestionIntent) -> str:
        """Build orders GraphQL query fragment"""
        time_filter = self._get_time_filter(intent.time_period) if intent.time_period else ""

        return f"""
        orders(first: 100{time_filter}) {{
            edges {{
                node {{
                    id
                    name
                    createdAt
                    totalPriceSet {{
                        shopMoney {{
                            amount
                            currencyCode
                        }}
                    }}
                    lineItems(first: 20) {{
                        edges {{
                            node {{
                                title
                                quantity
                                variant {{
                                    id
                                    sku
                                    price
                                }}
                            }}
                        }}
                    }}
                    customer {{
                        id
                        email
                    }}
                }}
            }}
        }}
        """

    def _products_query(self, intent: QuestionIntent) -> str:
        """Build products GraphQL query fragment"""
        return """
        products(first: 100) {
            edges {
                node {
                    id
                    title
                    status
                    totalInventory
                    variants(first: 10) {
                        edges {
                            node {
                                id
                                title
                                sku
                                price
                                inventoryQuantity
                            }
                        }
                    }
                }
            }
        }
        """

    def _inventory_query(self, intent: QuestionIntent) -> str:
        """Build inventory GraphQL query fragment"""
        return """
        inventoryItems(first: 100) {
            edges {
                node {
                    id
                    sku
                    tracked
                    inventoryLevels(first: 5) {
                        edges {
                            node {
                                available
                                location {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """

    def _customers_query(self, intent: QuestionIntent) -> str:
        """Build customers GraphQL query fragment"""
        return """
        customers(first: 100) {
            edges {
                node {
                    id
                    displayName
                    email
                    ordersCount
                    totalSpent
                    createdAt
                }
            }
        }
        """

    def _get_time_filter(self, time_period: str) -> str:
        """Convert time period to GraphQL filter"""
        from datetime import datetime, timedelta

        today = datetime.now()

        if "7 days" in time_period or "week" in time_period:
            start_date = today - timedelta(days=7)
        elif "30 days" in time_period or "month" in time_period:
            start_date = today - timedelta(days=30)
        elif "90 days" in time_period or "3 months" in time_period:
            start_date = today - timedelta(days=90)
        else:
            start_date = today - timedelta(days=30)  # Default to 30 days

        return f', query: "created_at:>={start_date.strftime("%Y-%m-%d")}"'

    async def get_store_info(self) -> Dict[str, Any]:
        """Get basic store information"""
        query = """
        query {
            shop {
                name
                email
                currencyCode
                timezoneAbbreviation
            }
        }
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/graphql.json",
                headers=self._get_headers(),
                json={"query": query},
                timeout=30.0
            )

            return response.json().get("data", {}).get("shop", {})
