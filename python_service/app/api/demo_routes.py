"""
Demo API Routes - For testing without real Shopify credentials
"""
import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

logger = structlog.get_logger()

router = APIRouter()


class DemoAnalyzeRequest(BaseModel):
    """Request model for demo analyze endpoint"""
    question: str = Field(..., description="Natural language question from the user")


class DemoAnalyzeResponse(BaseModel):
    """Response model for demo analyze endpoint"""
    answer: str
    confidence: str
    query_used: Optional[str] = None
    data_source: Optional[str] = None
    intent: Optional[dict] = None


# Sample responses for different question types
DEMO_RESPONSES = {
    "top_selling": {
        "answer": """Here are your top 5 selling products from the last week:

1. **Blue T-Shirt** - 150 units sold ($2,250 revenue)
2. **Red Hoodie** - 120 units sold ($3,600 revenue)
3. **Black Jeans** - 95 units sold ($4,750 revenue)
4. **White Sneakers** - 80 units sold ($6,400 revenue)
5. **Gray Cap** - 65 units sold ($975 revenue)

Your best performer by units is the Blue T-Shirt, while White Sneakers generated the highest revenue due to its higher price point.""",
        "confidence": "high",
        "query_used": """FROM sales
SHOW product_title, SUM(ordered_item_quantity) AS units_sold, SUM(net_sales) AS revenue
GROUP BY product_title
SINCE -7d
ORDER BY units_sold DESC
LIMIT 5""",
        "data_source": "sales",
        "intent": {
            "primary_intent": "sales_analysis",
            "data_sources": ["orders", "products"],
            "time_period": "last 7 days",
            "metrics": ["units_sold", "revenue"]
        }
    },
    "inventory_reorder": {
        "answer": """Based on your sales data from the last 30 days, here's my inventory reorder recommendation:

**Daily Sales Average:** 10 units/day
**Current Stock:** 45 units
**Days Until Stockout:** ~4.5 days

**Recommendation:** You should reorder at least **70 units** to cover the next week and avoid stockouts.

For a safer buffer (2 weeks supply), consider ordering **140-150 units**.

Note: This projection assumes consistent demand. Consider ordering more if you have promotions planned.""",
        "confidence": "medium",
        "query_used": """FROM sales
SHOW product_title, SUM(ordered_item_quantity) AS total_sold,
     SUM(ordered_item_quantity)/30 AS daily_average
GROUP BY product_title
SINCE -30d""",
        "data_source": "sales",
        "intent": {
            "primary_intent": "inventory_forecast",
            "data_sources": ["inventory", "orders"],
            "time_period": "last 30 days",
            "metrics": ["units_sold", "daily_average", "current_stock"]
        }
    },
    "low_stock": {
        "answer": """Based on current inventory levels and sales velocity, these products are at risk of stockout within 7 days:

**Critical (< 3 days):**
1. Blue T-Shirt (Size M) - 8 units left, selling 3/day
2. Red Hoodie (Size L) - 5 units left, selling 2/day

**Warning (3-7 days):**
3. Black Jeans (32W) - 15 units left, selling 3/day
4. White Sneakers (Size 10) - 20 units left, selling 4/day
5. Gray Cap - 12 units left, selling 2/day

**Action Required:** Place reorders immediately for the critical items to avoid lost sales.""",
        "confidence": "high",
        "query_used": """FROM products
SHOW product_title, variant_sku, inventory_quantity
WHERE inventory_quantity <= 20
ORDER BY inventory_quantity ASC""",
        "data_source": "inventory",
        "intent": {
            "primary_intent": "inventory_forecast",
            "data_sources": ["inventory", "orders"],
            "time_period": "next 7 days",
            "metrics": ["current_stock", "sales_velocity"]
        }
    },
    "repeat_customers": {
        "answer": """In the last 90 days, you had **45 customers** who placed repeat orders.

**Key Insights:**
- Repeat customers represent **23%** of your total customer base
- They contributed to **41%** of your total revenue ($12,450)
- Average orders per repeat customer: **2.8 orders**
- Average spend per repeat customer: **$276.67**

**Top Repeat Customers:**
1. John Smith - 5 orders ($890 total)
2. Sarah Johnson - 4 orders ($650 total)
3. Mike Williams - 4 orders ($520 total)

**Recommendation:** Consider implementing a loyalty program to encourage more repeat purchases from your engaged customer base.""",
        "confidence": "high",
        "query_used": """FROM customers
SHOW customer_email, COUNT(order_id) AS order_count, SUM(total_price) AS total_spent
GROUP BY customer_email
HAVING order_count > 1
SINCE -90d
ORDER BY order_count DESC""",
        "data_source": "customers",
        "intent": {
            "primary_intent": "customer_analysis",
            "data_sources": ["customers", "orders"],
            "time_period": "last 90 days",
            "metrics": ["repeat_orders", "customer_count"]
        }
    },
    "revenue": {
        "answer": """Here's your revenue summary for this month:

**Total Revenue:** $28,450
**Total Orders:** 342
**Average Order Value:** $83.19

**Revenue Breakdown:**
- Week 1: $6,200 (78 orders)
- Week 2: $7,800 (92 orders)
- Week 3: $8,100 (98 orders)
- Week 4 (so far): $6,350 (74 orders)

**Trend:** Your revenue is showing steady growth week-over-week, with a 12% increase from Week 1 to Week 3. You're on track to exceed last month's revenue by approximately 8%.""",
        "confidence": "high",
        "query_used": """FROM sales
SHOW week, SUM(net_sales) AS weekly_revenue, COUNT(order_id) AS orders
GROUP BY week
SINCE -30d
ORDER BY week ASC""",
        "data_source": "sales",
        "intent": {
            "primary_intent": "sales_analysis",
            "data_sources": ["orders"],
            "time_period": "this month",
            "metrics": ["revenue", "order_count", "aov"]
        }
    }
}


def classify_question(question: str) -> str:
    """Simple keyword-based question classification for demo"""
    question_lower = question.lower()

    if any(word in question_lower for word in ["top", "best", "selling", "popular"]):
        return "top_selling"
    elif any(word in question_lower for word in ["reorder", "need", "order", "forecast"]) and "inventory" in question_lower:
        return "inventory_reorder"
    elif any(word in question_lower for word in ["stock", "out of stock", "low stock", "stockout"]):
        return "low_stock"
    elif any(word in question_lower for word in ["repeat", "loyal", "returning"]) and "customer" in question_lower:
        return "repeat_customers"
    elif any(word in question_lower for word in ["revenue", "sales", "money", "earnings", "total"]):
        return "revenue"
    elif "how much inventory" in question_lower or "reorder" in question_lower:
        return "inventory_reorder"
    else:
        return "top_selling"  # Default


@router.post("/demo/analyze", response_model=DemoAnalyzeResponse)
async def demo_analyze_question(request: DemoAnalyzeRequest):
    """
    Demo endpoint that returns sample responses without connecting to Shopify.
    Use this to test the API structure and see example outputs.
    """
    logger.info("Demo analyze request", question=request.question[:100])

    question_type = classify_question(request.question)
    response_data = DEMO_RESPONSES.get(question_type, DEMO_RESPONSES["top_selling"])

    return DemoAnalyzeResponse(
        answer=response_data["answer"],
        confidence=response_data["confidence"],
        query_used=response_data["query_used"],
        data_source=response_data["data_source"],
        intent=response_data["intent"]
    )


@router.get("/demo/sample-questions")
async def get_sample_questions():
    """Get sample questions that work with the demo endpoint"""
    return {
        "sample_questions": [
            {
                "question": "What were my top 5 selling products last week?",
                "type": "top_selling",
                "expected_data_source": "sales"
            },
            {
                "question": "How much inventory should I reorder based on last 30 days sales?",
                "type": "inventory_reorder",
                "expected_data_source": "sales"
            },
            {
                "question": "Which products are likely to go out of stock in 7 days?",
                "type": "low_stock",
                "expected_data_source": "inventory"
            },
            {
                "question": "Which customers placed repeat orders in the last 90 days?",
                "type": "repeat_customers",
                "expected_data_source": "customers"
            },
            {
                "question": "What is my total revenue for this month?",
                "type": "revenue",
                "expected_data_source": "sales"
            }
        ]
    }
