# Shopify AI Analytics

An AI-powered analytics application that connects to Shopify stores, reads customer/order/inventory data, and allows users to ask natural language questions. The system translates questions into ShopifyQL, fetches data from Shopify, and returns answers in simple, business-friendly language.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Shopify       │◄────│   Rails API     │◄────│   Python AI     │
│   Store         │     │   (Gateway)     │     │   Service       │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       │                       │
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                          OAuth + API Calls
```

### Components

1. **Rails API Backend** (`rails_api/`)
   - Handles Shopify OAuth authentication
   - Exposes REST API endpoints
   - Validates requests and manages store connections
   - Forwards questions to Python AI service

2. **Python AI Service** (`python_service/`)
   - Receives questions from Rails API
   - Uses LLM to understand intent and generate ShopifyQL
   - Executes queries against Shopify APIs
   - Converts results to human-friendly explanations

## Agent Flow

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    ANALYTICS AGENT                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. UNDERSTAND INTENT                                       │
│     ├── Parse natural language question                     │
│     ├── Identify data sources (orders, inventory, etc.)     │
│     ├── Extract time period, metrics, filters               │
│     └── Classify intent type                                │
│                                                             │
│  2. PLAN                                                    │
│     ├── Determine required queries                          │
│     ├── Prioritize data fetching steps                      │
│     └── Choose ShopifyQL vs GraphQL                         │
│                                                             │
│  3. GENERATE SHOPIFYQL                                      │
│     ├── Build query using LLM                               │
│     ├── Validate syntax                                     │
│     └── Fix errors if needed                                │
│                                                             │
│  4. EXECUTE & VALIDATE                                      │
│     ├── Run query against Shopify API                       │
│     ├── Handle errors and retries                           │
│     └── Process raw results                                 │
│                                                             │
│  5. EXPLAIN RESULTS                                         │
│     ├── Calculate metrics and insights                      │
│     ├── Generate business-friendly explanation              │
│     └── Assign confidence level                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
Human-Friendly Answer
```

## Setup Instructions

### Prerequisites

- Ruby 3.2+
- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)
- Docker & Docker Compose (optional)

### Quick Start with Docker

```bash
# Clone the repository
cd shopify-ai-analytics

# Copy environment files
cp rails_api/.env.example rails_api/.env
cp python_service/.env.example python_service/.env

# Set your Shopify API credentials in rails_api/.env
# Set your LLM API key in python_service/.env

# Start all services
docker-compose up -d

# Rails API will be available at http://localhost:3000
# Python AI Service will be available at http://localhost:8000
```

### Manual Setup

#### Rails API

```bash
cd rails_api

# Install dependencies
bundle install

# Setup database
rails db:create db:migrate

# Copy and configure environment
cp .env.example .env
# Edit .env with your Shopify credentials

# Start server
rails server -p 3000
```

#### Python AI Service

```bash
cd python_service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your LLM API key

# Start server
uvicorn main:app --reload --port 8000
```

### Environment Variables

#### Rails API (`rails_api/.env`)

```env
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_api_secret
SHOPIFY_REDIRECT_URI=http://localhost:3000/auth/shopify/callback
PYTHON_SERVICE_URL=http://localhost:8000
```

#### Python Service (`python_service/.env`)

```env
LLM_PROVIDER=openai  # or "anthropic" or "mock"
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## API Documentation

### Authentication

#### Initiate Shopify OAuth

```http
GET /auth/shopify?shop=mystore.myshopify.com
```

Redirects to Shopify OAuth authorization page.

#### OAuth Callback

```http
GET /auth/shopify/callback
```

Handles OAuth callback and stores access token.

### Main Endpoints

#### Ask a Question

```http
POST /api/v1/questions
Content-Type: application/json

{
  "store_id": "mystore.myshopify.com",
  "question": "What were my top 5 selling products last week?"
}
```

**Response:**

```json
{
  "answer": "Here are your top 5 selling products from the last week:\n\n1. Blue T-Shirt - 150 units sold ($2,250 revenue)\n2. Red Hoodie - 120 units sold ($3,600 revenue)\n3. Black Jeans - 95 units sold ($4,750 revenue)\n4. White Sneakers - 80 units sold ($6,400 revenue)\n5. Gray Cap - 65 units sold ($975 revenue)\n\nYour best performer by units is the Blue T-Shirt, while White Sneakers generated the most revenue.",
  "confidence": "high",
  "query_used": "FROM sales\nSHOW product_title, SUM(ordered_item_quantity) AS units_sold, SUM(net_sales) AS revenue\nGROUP BY product_title\nSINCE -7d\nORDER BY units_sold DESC\nLIMIT 5",
  "data_source": "sales",
  "metadata": {
    "processing_time_ms": 1234,
    "timestamp": "2024-12-28T10:30:00Z"
  }
}
```

#### Get Supported Questions

```http
GET /api/v1/supported-questions
```

Returns examples of questions the system can answer.

### Additional Endpoints

```http
GET /api/v1/stores              # List connected stores
GET /api/v1/stores/:id          # Get store details
GET /api/v1/stores/:id/status   # Check store connection status
GET /api/v1/orders              # List orders (requires store_id header)
GET /api/v1/products            # List products
GET /api/v1/inventory           # List inventory
GET /api/v1/customers           # List customers
GET /health                     # Health check
```

## Example Questions

### Inventory Management

- "How many units of Product X will I need next month?"
- "Which products are likely to go out of stock in 7 days?"
- "How much inventory should I reorder based on last 30 days sales?"
- "What is my current stock level for all products?"

### Sales Analysis

- "What were my top 5 selling products last week?"
- "What is my total revenue for this month?"
- "What is the average order value?"
- "Which day of the week has the most sales?"

### Customer Insights

- "Which customers placed repeat orders in the last 90 days?"
- "Who are my top 10 customers by total spend?"
- "How many new customers did I get this month?"
- "What is my customer retention rate?"

### Trends & Forecasting

- "What is my sales trend for the last 3 months?"
- "Which product category is growing the fastest?"
- "Are my sales increasing or decreasing?"

## ShopifyQL Reference

ShopifyQL is Shopify's analytics query language. Here are some examples:

### Top Selling Products

```sql
FROM sales
SHOW product_title, SUM(ordered_item_quantity) AS units_sold, SUM(net_sales) AS revenue
GROUP BY product_title
SINCE -7d
ORDER BY units_sold DESC
LIMIT 5
```

### Daily Sales Trend

```sql
FROM sales
SHOW day, SUM(net_sales) AS daily_revenue
GROUP BY day
SINCE -30d
ORDER BY day ASC
```

### Low Stock Alert

```sql
FROM products
SHOW product_title, variant_sku, inventory_quantity
WHERE inventory_quantity <= 10
ORDER BY inventory_quantity ASC
```

## Project Structure

```
shopify-ai-analytics/
├── rails_api/                    # Rails API Backend
│   ├── app/
│   │   ├── controllers/
│   │   │   ├── api/v1/
│   │   │   │   ├── questions_controller.rb
│   │   │   │   ├── stores_controller.rb
│   │   │   │   ├── orders_controller.rb
│   │   │   │   ├── products_controller.rb
│   │   │   │   ├── inventory_controller.rb
│   │   │   │   └── customers_controller.rb
│   │   │   ├── shopify_auth_controller.rb
│   │   │   └── health_controller.rb
│   │   ├── models/
│   │   │   ├── store.rb
│   │   │   └── request_log.rb
│   │   └── services/
│   │       ├── ai_service.rb
│   │       └── shopify_service.rb
│   ├── config/
│   │   ├── routes.rb
│   │   └── database.yml
│   ├── db/migrate/
│   ├── Gemfile
│   └── Dockerfile
│
├── python_service/               # Python AI Service
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── agent/
│   │   │   ├── analytics_agent.py
│   │   │   ├── llm_client.py
│   │   │   ├── shopify_client.py
│   │   │   ├── query_generator.py
│   │   │   └── result_explainer.py
│   │   ├── core/
│   │   │   └── config.py
│   │   └── models/
│   │       └── schemas.py
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

## Testing

### Running Tests

```bash
# Rails API tests
cd rails_api
bundle exec rspec

# Python service tests
cd python_service
pytest
```

### Mock Mode

The Python service can run in "mock" mode without LLM API keys:

```env
LLM_PROVIDER=mock
```

This returns pre-configured responses for testing and development.

## Error Handling

The system handles various error scenarios:

1. **Invalid store connection** - Returns 401 with OAuth instructions
2. **Query errors** - Retries with exponential backoff
3. **Empty data** - Returns helpful suggestions
4. **LLM failures** - Falls back to template responses

## Security Considerations

- Shopify access tokens are encrypted at rest
- OAuth state parameter prevents CSRF attacks
- Input validation on all endpoints
- Rate limiting (can be configured)
- Secure token handling in environment variables

## Future Enhancements

- [ ] Conversation memory for follow-up questions
- [ ] Query caching layer
- [ ] Metrics dashboard
- [ ] Advanced retry and fallback logic
- [ ] Multi-store support
- [ ] Webhook integration for real-time updates

## License

MIT License
