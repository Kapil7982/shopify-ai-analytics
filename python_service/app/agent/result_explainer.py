"""
Result Explainer - Converts raw Shopify data into human-friendly insights

This component takes the raw data from Shopify queries and generates
business-friendly explanations that non-technical users can understand.
"""
import structlog
from typing import Dict, Any, List, Optional

from app.models.schemas import QuestionIntent, DataSource

logger = structlog.get_logger()


class ResultExplainer:
    """
    Converts technical query results into simple, business-friendly language.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def explain(
        self,
        question: str,
        intent: QuestionIntent,
        data: Dict[str, Any],
        query_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a human-friendly explanation of the query results.

        Args:
            question: Original user question
            intent: Parsed intent
            data: Raw data from Shopify
            query_used: The query that was executed

        Returns:
            Dictionary with answer, confidence, and metadata
        """

        # Handle empty or error data
        if data.get("is_empty"):
            return self._handle_empty_data(question, intent)

        if data.get("is_error"):
            return self._handle_error_data(question, data)

        # Process the data
        processed_data = self._process_data(data, intent)

        # Generate explanation using LLM
        explanation = await self._generate_explanation(
            question=question,
            intent=intent,
            processed_data=processed_data
        )

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(processed_data, intent)

        return {
            "answer": explanation,
            "confidence": confidence,
            "query_used": query_used,
            "data_source": intent.data_sources[0].value if intent.data_sources else None,
            "raw_data": processed_data.get("summary")
        }

    def _handle_empty_data(
        self,
        question: str,
        intent: QuestionIntent
    ) -> Dict[str, Any]:
        """Handle case when no data is found"""

        suggestions = [
            "Try a broader time range",
            "Check if your store has data for this metric",
            "Verify the product or category name"
        ]

        return {
            "answer": f"I couldn't find any data to answer your question: \"{question}\". "
                      f"This could mean there's no matching data for the specified criteria, "
                      f"or the time period you're asking about doesn't have any activity.",
            "confidence": "low",
            "query_used": None,
            "data_source": intent.data_sources[0].value if intent.data_sources else None,
            "suggestions": suggestions
        }

    def _handle_error_data(
        self,
        question: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle case when query resulted in an error"""

        errors = data.get("errors", [])
        error_messages = [e.get("message", str(e)) for e in errors]

        return {
            "answer": f"I encountered an issue while trying to answer your question. "
                      f"Please try rephrasing your question or asking about a different metric.",
            "confidence": "low",
            "query_used": None,
            "data_source": None,
            "errors": error_messages
        }

    def _process_data(
        self,
        data: Dict[str, Any],
        intent: QuestionIntent
    ) -> Dict[str, Any]:
        """Process raw data into a more useful format"""

        processed = {
            "raw": data.get("data", data),
            "summary": {},
            "insights": []
        }

        raw_data = processed["raw"]

        # Process ShopifyQL table response
        if isinstance(raw_data, dict) and "tableData" in raw_data:
            table_data = raw_data["tableData"]
            columns = [col["name"] for col in table_data.get("columns", [])]
            rows = table_data.get("rowData", [])

            processed["table"] = {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }

            # Generate summary statistics
            if rows:
                processed["summary"] = self._generate_summary(columns, rows, intent)

        # Process GraphQL response
        elif isinstance(raw_data, dict):
            for key in ["orders", "products", "customers", "inventoryItems"]:
                if key in raw_data:
                    edges = raw_data[key].get("edges", [])
                    processed[key] = [edge["node"] for edge in edges]
                    processed["summary"][key + "_count"] = len(processed[key])

        return processed

    def _generate_summary(
        self,
        columns: List[str],
        rows: List[List[Any]],
        intent: QuestionIntent
    ) -> Dict[str, Any]:
        """Generate summary statistics from table data"""

        summary = {
            "total_rows": len(rows),
            "columns": columns
        }

        # Calculate totals and averages for numeric columns
        for i, col in enumerate(columns):
            col_lower = col.lower()
            if any(metric in col_lower for metric in ["revenue", "sales", "total", "quantity", "units", "sold"]):
                try:
                    values = [float(row[i]) for row in rows if row[i] is not None]
                    if values:
                        summary[f"{col}_total"] = sum(values)
                        summary[f"{col}_average"] = sum(values) / len(values)
                        summary[f"{col}_max"] = max(values)
                        summary[f"{col}_min"] = min(values)
                except (ValueError, TypeError):
                    pass

        return summary

    async def _generate_explanation(
        self,
        question: str,
        intent: QuestionIntent,
        processed_data: Dict[str, Any]
    ) -> str:
        """Generate a natural language explanation using LLM"""

        # Build context for the LLM
        data_summary = processed_data.get("summary", {})
        table_data = processed_data.get("table", {})

        prompt = f"""You are a helpful Shopify analytics assistant. Based on the data below,
provide a clear, business-friendly answer to the user's question.

User Question: {question}

Data Summary:
{self._format_summary(data_summary)}

{self._format_table_preview(table_data)}

Guidelines:
- Use simple, non-technical language
- Include specific numbers from the data
- Provide actionable recommendations when appropriate
- Be concise but thorough
- If the question is about forecasting or projections, explain your calculation method
- Format numbers with appropriate units (e.g., "$1,234" for currency, "150 units")

Provide your answer in 2-4 short paragraphs."""

        response = await self.llm_client.generate(prompt, response_format="text")
        return response.strip()

    def _format_summary(self, summary: Dict[str, Any]) -> str:
        """Format summary data for the LLM prompt"""

        lines = []
        for key, value in summary.items():
            if isinstance(value, float):
                lines.append(f"- {key}: {value:,.2f}")
            elif isinstance(value, int):
                lines.append(f"- {key}: {value:,}")
            else:
                lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "No summary data available"

    def _format_table_preview(self, table_data: Dict[str, Any]) -> str:
        """Format a preview of table data for the LLM prompt"""

        if not table_data or not table_data.get("rows"):
            return ""

        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])[:10]  # Limit to first 10 rows

        lines = ["Table Preview (first 10 rows):"]
        lines.append(" | ".join(columns))
        lines.append("-" * 50)

        for row in rows:
            lines.append(" | ".join(str(v) for v in row))

        return "\n".join(lines)

    def _calculate_confidence(
        self,
        processed_data: Dict[str, Any],
        intent: QuestionIntent
    ) -> str:
        """Calculate confidence level based on data quality and completeness"""

        score = 0

        # Check data availability
        if processed_data.get("table", {}).get("row_count", 0) > 0:
            score += 3
        elif any(processed_data.get(k) for k in ["orders", "products", "customers"]):
            score += 2

        # Check if we have enough data points
        row_count = processed_data.get("table", {}).get("row_count", 0)
        if row_count >= 30:
            score += 2
        elif row_count >= 7:
            score += 1

        # Check summary completeness
        summary = processed_data.get("summary", {})
        if len(summary) >= 3:
            score += 1

        # Forecasting queries are inherently less certain
        if intent.primary_intent in ["inventory_forecast", "sales_forecast"]:
            score -= 1

        # Map score to confidence level
        if score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
