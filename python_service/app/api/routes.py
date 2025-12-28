"""
API Routes for the AI Analytics Service
"""
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Any

from app.agent.analytics_agent import AnalyticsAgent
from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request model for the analyze endpoint"""
    store_id: str = Field(..., description="Shopify store domain (e.g., mystore.myshopify.com)")
    access_token: str = Field(..., description="Shopify access token")
    question: str = Field(..., description="Natural language question from the user")
    context: Optional[str] = Field(None, description="Additional context for the question")


class AnalyzeResponse(BaseModel):
    """Response model for the analyze endpoint"""
    answer: str = Field(..., description="Human-friendly answer to the question")
    confidence: str = Field(..., description="Confidence level: low, medium, high")
    query_used: Optional[str] = Field(None, description="ShopifyQL query that was executed")
    data_source: Optional[str] = Field(None, description="Data source used (orders, products, inventory, customers)")
    raw_data: Optional[Any] = Field(None, description="Raw data from Shopify (if requested)")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    suggestions: List[str] = []


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_question(request: AnalyzeRequest):
    """
    Analyze a natural language question about Shopify store data.

    This endpoint:
    1. Receives a question from the Rails API
    2. Uses an LLM to understand the intent
    3. Generates appropriate ShopifyQL queries
    4. Executes queries against Shopify
    5. Returns human-friendly insights
    """
    logger.info(
        "Received analyze request",
        store_id=request.store_id,
        question=request.question[:100]
    )

    try:
        # Initialize the analytics agent
        agent = AnalyticsAgent(
            store_id=request.store_id,
            access_token=request.access_token
        )

        # Process the question
        result = await agent.process_question(
            question=request.question,
            context=request.context
        )

        logger.info(
            "Analysis complete",
            store_id=request.store_id,
            confidence=result.get("confidence")
        )

        return AnalyzeResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            query_used=result.get("query_used"),
            data_source=result.get("data_source"),
            raw_data=result.get("raw_data")
        )

    except ValueError as e:
        logger.warning("Invalid request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Analysis failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to process question",
                "suggestions": [
                    "Try rephrasing your question",
                    "Ensure you're asking about orders, products, inventory, or customers",
                    "Check if your store has the required data"
                ]
            }
        )


@router.get("/supported-questions")
async def get_supported_questions():
    """
    Returns examples of supported question types
    """
    return {
        "categories": {
            "inventory": [
                "How many units of Product X will I need next month?",
                "Which products are likely to go out of stock in 7 days?",
                "How much inventory should I reorder based on last 30 days sales?",
                "What is my current stock level for all products?"
            ],
            "sales": [
                "What were my top 5 selling products last week?",
                "What is my total revenue for this month?",
                "What is the average order value?",
                "Which day of the week has the most sales?"
            ],
            "customers": [
                "Which customers placed repeat orders in the last 90 days?",
                "Who are my top 10 customers by total spend?",
                "How many new customers did I get this month?",
                "What is my customer retention rate?"
            ],
            "trends": [
                "What is my sales trend for the last 3 months?",
                "Which product category is growing the fastest?",
                "Are my sales increasing or decreasing?"
            ]
        }
    }
