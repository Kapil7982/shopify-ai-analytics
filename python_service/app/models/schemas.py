"""
Data models and schemas for the AI Analytics Service
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DataSource(str, Enum):
    """Available data sources in Shopify"""
    ORDERS = "orders"
    PRODUCTS = "products"
    INVENTORY = "inventory"
    CUSTOMERS = "customers"
    SALES = "sales"


class QuestionIntent(BaseModel):
    """Parsed intent from a user question"""
    primary_intent: str = Field(..., description="Main intent of the question")
    data_sources: List[DataSource] = Field(..., description="Required data sources")
    time_period: Optional[str] = Field(None, description="Time period mentioned")
    metrics: List[str] = Field(default_factory=list, description="Metrics to calculate")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters to apply")
    aggregation: Optional[str] = Field(None, description="Type of aggregation needed")


class ShopifyQLQuery(BaseModel):
    """Generated ShopifyQL query"""
    query: str = Field(..., description="The ShopifyQL query string")
    data_source: DataSource = Field(..., description="Primary data source")
    description: str = Field(..., description="Human-readable description of what the query does")
    is_valid: bool = Field(True, description="Whether the query is syntactically valid")
    validation_errors: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Result of analyzing Shopify data"""
    answer: str = Field(..., description="Human-friendly answer")
    confidence: str = Field(..., description="Confidence level: low, medium, high")
    query_used: Optional[str] = Field(None, description="ShopifyQL query used")
    data_source: Optional[str] = Field(None, description="Data source used")
    raw_data: Optional[Any] = Field(None, description="Raw data from Shopify")
    insights: List[str] = Field(default_factory=list, description="Additional insights")
    warnings: List[str] = Field(default_factory=list, description="Warnings about data quality")
