"""
Real Data Routes - Direct Shopify API queries for testing
Works without ShopifyQL (which may not be available on trial stores)
"""
import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter()

# Store connections (shared with gateway)
from app.api.gateway_routes import stores_db


class QuestionRequest(BaseModel):
    store_id: str
    question: str


async def fetch_shopify_data(store_id: str, endpoint: str) -> Dict[str, Any]:
    """Fetch data directly from Shopify REST API"""
    if store_id not in stores_db:
        raise HTTPException(status_code=401, detail="Store not connected")

    store = stores_db[store_id]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{store_id}/admin/api/2024-01/{endpoint}",
            headers={"X-Shopify-Access-Token": store["access_token"]},
            timeout=30.0
        )

        if response.status_code != 200:
            return {"error": response.text}

        return response.json()


@router.post("/real/ask")
async def ask_real_question(request: QuestionRequest):
    """
    Ask questions using real Shopify data via REST API
    (Bypasses ShopifyQL which may not work on trial stores)
    """
    store_id = request.store_id
    if not store_id.endswith('.myshopify.com'):
        store_id = f"{store_id}.myshopify.com"

    question = request.question.lower()

    # Determine what data to fetch based on question
    if any(word in question for word in ["product", "inventory", "stock", "item"]):
        return await analyze_products(store_id, request.question)
    elif any(word in question for word in ["order", "sale", "revenue", "selling"]):
        return await analyze_orders(store_id, request.question)
    elif any(word in question for word in ["customer", "buyer", "repeat"]):
        return await analyze_customers(store_id, request.question)
    else:
        # Default to products
        return await analyze_products(store_id, request.question)


async def analyze_products(store_id: str, question: str) -> Dict[str, Any]:
    """Analyze products and inventory"""
    data = await fetch_shopify_data(store_id, "products.json?limit=50")

    if "error" in data:
        return {"answer": f"Error fetching data: {data['error']}", "confidence": "low"}

    products = data.get("products", [])

    if not products:
        return {
            "answer": "Your store doesn't have any products yet. Add some products in Shopify Admin > Products to see analytics.",
            "confidence": "high",
            "data_source": "products",
            "raw_data": {"product_count": 0}
        }

    # Build analysis
    total_products = len(products)
    active_products = len([p for p in products if p.get("status") == "active"])
    draft_products = len([p for p in products if p.get("status") == "draft"])

    total_inventory = 0
    product_details = []

    for product in products:
        variants = product.get("variants", [])
        product_inventory = sum(v.get("inventory_quantity", 0) for v in variants)
        total_inventory += product_inventory

        price = variants[0].get("price", "0") if variants else "0"

        product_details.append({
            "title": product.get("title"),
            "status": product.get("status"),
            "price": f"Rs. {price}",
            "inventory": product_inventory
        })

    # Generate answer
    answer = f"""**Your Store Inventory Summary:**

**Total Products:** {total_products}
- Active: {active_products}
- Draft: {draft_products}

**Total Inventory:** {total_inventory} units

**Product Details:**
"""

    for i, p in enumerate(product_details, 1):
        status_icon = "✅" if p["status"] == "active" else "📝"
        answer += f"\n{i}. **{p['title']}** {status_icon}\n   - Price: {p['price']}\n   - Stock: {p['inventory']} units"

    return {
        "answer": answer,
        "confidence": "high",
        "data_source": "products",
        "query_used": "GET /admin/api/2024-01/products.json",
        "raw_data": {
            "total_products": total_products,
            "total_inventory": total_inventory,
            "products": product_details
        }
    }


async def analyze_orders(store_id: str, question: str) -> Dict[str, Any]:
    """Analyze orders and sales"""
    data = await fetch_shopify_data(store_id, "orders.json?limit=50&status=any")

    if "error" in data:
        return {"answer": f"Error fetching data: {data['error']}", "confidence": "low"}

    orders = data.get("orders", [])

    if not orders:
        return {
            "answer": """**No orders found in your store yet.**

This is expected for a new/trial store. To see sales analytics:
1. Create test orders through Shopify Admin > Orders > Create order
2. Or enable a payment method and complete a checkout

Since your store is on a trial plan, checkout may be disabled. You can create draft orders directly from the admin panel.""",
            "confidence": "high",
            "data_source": "orders",
            "raw_data": {"order_count": 0}
        }

    # Analyze orders
    total_orders = len(orders)
    total_revenue = sum(float(o.get("total_price", 0)) for o in orders)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    answer = f"""**Sales Summary:**

**Total Orders:** {total_orders}
**Total Revenue:** Rs. {total_revenue:,.2f}
**Average Order Value:** Rs. {avg_order_value:,.2f}
"""

    return {
        "answer": answer,
        "confidence": "high",
        "data_source": "orders",
        "query_used": "GET /admin/api/2024-01/orders.json",
        "raw_data": {
            "total_orders": total_orders,
            "total_revenue": total_revenue
        }
    }


async def analyze_customers(store_id: str, question: str) -> Dict[str, Any]:
    """Analyze customers"""
    data = await fetch_shopify_data(store_id, "customers.json?limit=50")

    if "error" in data:
        return {"answer": f"Error fetching data: {data['error']}", "confidence": "low"}

    customers = data.get("customers", [])

    if not customers:
        return {
            "answer": """**No customers found in your store yet.**

Customers are created when orders are placed. Since your store is new, there are no customers yet.

To get customer analytics, you'll need some orders first.""",
            "confidence": "high",
            "data_source": "customers",
            "raw_data": {"customer_count": 0}
        }

    total_customers = len(customers)

    answer = f"""**Customer Summary:**

**Total Customers:** {total_customers}
"""

    return {
        "answer": answer,
        "confidence": "high",
        "data_source": "customers",
        "raw_data": {"total_customers": total_customers}
    }


@router.get("/real/products/{store_id}")
async def get_products(store_id: str):
    """Get all products from store"""
    if not store_id.endswith('.myshopify.com'):
        store_id = f"{store_id}.myshopify.com"

    data = await fetch_shopify_data(store_id, "products.json?limit=50")
    return data


@router.get("/real/orders/{store_id}")
async def get_orders(store_id: str):
    """Get all orders from store"""
    if not store_id.endswith('.myshopify.com'):
        store_id = f"{store_id}.myshopify.com"

    data = await fetch_shopify_data(store_id, "orders.json?limit=50&status=any")
    return data


@router.get("/real/inventory/{store_id}")
async def get_inventory(store_id: str):
    """Get inventory levels from store"""
    if not store_id.endswith('.myshopify.com'):
        store_id = f"{store_id}.myshopify.com"

    data = await fetch_shopify_data(store_id, "inventory_levels.json")
    return data
