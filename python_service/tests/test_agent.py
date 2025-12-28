"""
Agent component tests
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agent.llm_client import LLMClient
from app.agent.query_generator import ShopifyQLGenerator
from app.models.schemas import QuestionIntent, DataSource


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = LLMClient()
    client.provider = "mock"
    return client


@pytest.mark.asyncio
async def test_llm_client_mock_intent():
    """Test mock LLM client intent analysis"""
    client = LLMClient()
    client.provider = "mock"

    result = await client.generate(
        "Analyze this question: What are my top selling products?",
        response_format="json"
    )

    assert "primary_intent" in result
    assert "data_sources" in result


@pytest.mark.asyncio
async def test_llm_client_mock_explanation():
    """Test mock LLM client text generation"""
    client = LLMClient()
    client.provider = "mock"

    result = await client.generate(
        "Explain top selling products",
        response_format="text"
    )

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_query_generator_basic():
    """Test ShopifyQL query generation"""
    mock_client = MagicMock()
    mock_client.generate = AsyncMock(return_value="""
FROM sales
SHOW product_title, SUM(ordered_item_quantity) AS units
GROUP BY product_title
SINCE -7d
ORDER BY units DESC
LIMIT 5
""")

    generator = ShopifyQLGenerator(mock_client)

    intent = QuestionIntent(
        primary_intent="sales_analysis",
        data_sources=[DataSource.ORDERS],
        time_period="last 7 days",
        metrics=["units_sold"],
        filters={},
        aggregation="sum"
    )

    result = await generator.generate(intent, [])

    assert "query" in result
    assert result["query_type"] == "shopifyql"


def test_intent_model():
    """Test QuestionIntent model"""
    intent = QuestionIntent(
        primary_intent="inventory_forecast",
        data_sources=[DataSource.INVENTORY, DataSource.ORDERS],
        time_period="last 30 days",
        metrics=["units_sold", "current_stock"],
        filters={"product_name": "Blue T-Shirt"},
        aggregation="sum"
    )

    assert intent.primary_intent == "inventory_forecast"
    assert len(intent.data_sources) == 2
    assert DataSource.INVENTORY in intent.data_sources
