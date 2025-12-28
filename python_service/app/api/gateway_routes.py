"""
Gateway API Routes - Simulates the Rails API for testing without Ruby

This module provides the same API interface as the Rails backend,
allowing end-to-end testing of the Shopify AI Analytics system.
"""
import os
import time
import structlog
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
import httpx

logger = structlog.get_logger()

router = APIRouter()

# In-memory store database for testing
stores_db: Dict[str, Dict[str, Any]] = {}
request_logs: List[Dict[str, Any]] = []


class StoreConnectRequest(BaseModel):
    """Request to connect a Shopify store"""
    shop_domain: str = Field(..., description="Shopify store domain (e.g., mystore.myshopify.com)")
    access_token: str = Field(..., description="Shopify Admin API access token")


class QuestionRequest(BaseModel):
    """Request model matching the Rails API"""
    store_id: str = Field(..., description="Shopify store domain")
    question: str = Field(..., description="Natural language question")
    context: Optional[str] = Field(None, description="Additional context")


class QuestionResponse(BaseModel):
    """Response model matching the Rails API"""
    answer: str
    confidence: str
    query_used: Optional[str] = None
    data_source: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ============= Store Management =============

@router.post("/gateway/stores/connect")
async def connect_store(request: StoreConnectRequest):
    """
    Connect a Shopify store (simulates OAuth flow result).

    In production, this would be done via OAuth. For testing,
    you can directly provide your store's Admin API access token.

    To get an access token:
    1. Go to your Shopify Admin > Settings > Apps and sales channels
    2. Click "Develop apps" > Create an app
    3. Configure Admin API scopes: read_orders, read_products, read_inventory, read_customers
    4. Install the app and copy the Admin API access token
    """
    shop_domain = request.shop_domain
    if not shop_domain.endswith('.myshopify.com'):
        shop_domain = f"{shop_domain}.myshopify.com"

    # Verify the token works by making a test request
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{shop_domain}/admin/api/2024-01/shop.json",
                headers={"X-Shopify-Access-Token": request.access_token},
                timeout=10.0
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid access token. Please check your Shopify Admin API token."
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to connect to Shopify: {response.text}"
                )

            shop_info = response.json().get("shop", {})
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")

    # Store the connection
    stores_db[shop_domain] = {
        "shop_domain": shop_domain,
        "access_token": request.access_token,
        "connected_at": datetime.utcnow().isoformat(),
        "shop_name": shop_info.get("name"),
        "email": shop_info.get("email"),
        "currency": shop_info.get("currency")
    }

    logger.info("Store connected", shop_domain=shop_domain)

    return {
        "message": "Successfully connected to Shopify store",
        "store_id": shop_domain,
        "shop_name": shop_info.get("name"),
        "currency": shop_info.get("currency")
    }


@router.get("/gateway/stores")
async def list_stores():
    """List all connected stores"""
    return {
        "stores": [
            {
                "store_id": domain,
                "shop_name": info.get("shop_name"),
                "connected_at": info.get("connected_at"),
                "connected": True
            }
            for domain, info in stores_db.items()
        ]
    }


@router.get("/gateway/stores/{store_id}/status")
async def get_store_status(store_id: str):
    """Get store connection status"""
    if store_id not in stores_db:
        raise HTTPException(status_code=404, detail="Store not found")

    store = stores_db[store_id]
    return {
        "store_id": store_id,
        "connected": True,
        "shop_name": store.get("shop_name"),
        "connected_at": store.get("connected_at")
    }


# ============= Questions API (Main Endpoint) =============

@router.post("/gateway/questions", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a natural language question about your Shopify store.

    This is the main API endpoint that:
    1. Validates the store is connected
    2. Forwards the question to the AI service
    3. Returns the answer in business-friendly language

    Example questions:
    - "What were my top 5 selling products last week?"
    - "How much inventory should I reorder based on last 30 days sales?"
    - "Which customers placed repeat orders in the last 90 days?"
    """
    start_time = time.time()

    # Check if store is connected
    store_id = request.store_id
    if not store_id.endswith('.myshopify.com'):
        store_id = f"{store_id}.myshopify.com"

    if store_id not in stores_db:
        raise HTTPException(
            status_code=401,
            detail=f"Store '{store_id}' not connected. Use POST /api/v1/gateway/stores/connect first."
        )

    store = stores_db[store_id]

    # Log the request
    log_entry = {
        "store_id": store_id,
        "question": request.question,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Call the AI service (internal call to /api/v1/analyze)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/analyze",
                json={
                    "store_id": store_id,
                    "access_token": store["access_token"],
                    "question": request.question,
                    "context": request.context
                },
                timeout=60.0
            )

            if response.status_code != 200:
                error_detail = response.json() if response.headers.get("content-type") == "application/json" else response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )

            result = response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    processing_time = (time.time() - start_time) * 1000

    # Update log with response
    log_entry["answer"] = result.get("answer")
    log_entry["confidence"] = result.get("confidence")
    log_entry["processing_time_ms"] = processing_time
    request_logs.append(log_entry)

    return QuestionResponse(
        answer=result.get("answer", "Unable to process question"),
        confidence=result.get("confidence", "low"),
        query_used=result.get("query_used"),
        data_source=result.get("data_source"),
        metadata={
            "processing_time_ms": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============= Demo with Real Shopify Data =============

@router.post("/gateway/demo/with-store")
async def demo_with_real_store(store_id: str, question: str):
    """
    Demo endpoint that uses real Shopify data if store is connected,
    otherwise falls back to demo data.
    """
    # Normalize store_id
    if not store_id.endswith('.myshopify.com'):
        store_id = f"{store_id}.myshopify.com"

    if store_id in stores_db:
        # Use real store
        return await ask_question(QuestionRequest(
            store_id=store_id,
            question=question
        ))
    else:
        # Fall back to demo
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/demo/analyze",
                json={"question": question},
                timeout=30.0
            )
            return response.json()


# ============= Request Logs =============

@router.get("/gateway/logs")
async def get_request_logs(limit: int = 50):
    """Get recent request logs"""
    return {
        "logs": request_logs[-limit:][::-1]  # Most recent first
    }


# ============= Instructions =============

@router.get("/gateway/setup-instructions")
async def get_setup_instructions():
    """Get instructions for connecting a real Shopify store"""
    return {
        "title": "How to Connect Your Shopify Store",
        "steps": [
            {
                "step": 1,
                "title": "Create a Custom App in Shopify",
                "instructions": [
                    "Log in to your Shopify Admin dashboard",
                    "Go to Settings > Apps and sales channels",
                    "Click 'Develop apps' (you may need to enable custom app development first)",
                    "Click 'Create an app' and give it a name like 'AI Analytics'"
                ]
            },
            {
                "step": 2,
                "title": "Configure API Scopes",
                "instructions": [
                    "In your app, go to 'Configuration'",
                    "Under 'Admin API integration', click 'Configure'",
                    "Select these scopes: read_orders, read_products, read_inventory, read_customers",
                    "Click 'Save'"
                ]
            },
            {
                "step": 3,
                "title": "Install and Get Access Token",
                "instructions": [
                    "Go to the 'API credentials' tab",
                    "Click 'Install app'",
                    "After installation, reveal and copy the 'Admin API access token'",
                    "IMPORTANT: Save this token securely - you can only see it once!"
                ]
            },
            {
                "step": 4,
                "title": "Connect to AI Analytics",
                "instructions": [
                    "Use the POST /api/v1/gateway/stores/connect endpoint",
                    "Provide your shop domain and access token",
                    "Example: {'shop_domain': 'mystore', 'access_token': 'shpat_xxx...'}"
                ]
            }
        ],
        "example_curl": """curl -X POST http://localhost:8000/api/v1/gateway/stores/connect \\
  -H "Content-Type: application/json" \\
  -d '{"shop_domain": "your-store-name", "access_token": "shpat_your_access_token"}'""",
        "note": "The access token starts with 'shpat_' for Admin API tokens"
    }
