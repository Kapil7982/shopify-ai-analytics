class ShopifyService
  SHOPIFY_API_VERSION = '2024-01'

  class << self
    def fetch_orders(store:, limit: 50, status: nil, created_at_min: nil, created_at_max: nil)
      with_session(store) do
        query = build_orders_query(limit, status, created_at_min, created_at_max)
        execute_graphql(store, query)
      end
    end

    def fetch_order(store:, order_id:)
      with_session(store) do
        query = <<~GRAPHQL
          query {
            order(id: "gid://shopify/Order/#{order_id}") {
              id
              name
              createdAt
              totalPriceSet { shopMoney { amount currencyCode } }
              lineItems(first: 50) {
                edges {
                  node {
                    title
                    quantity
                    variant { id sku }
                  }
                }
              }
              customer { id email displayName }
            }
          }
        GRAPHQL
        execute_graphql(store, query)
      end
    end

    def fetch_products(store:, limit: 50)
      with_session(store) do
        query = <<~GRAPHQL
          query {
            products(first: #{limit}) {
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
                        sku
                        price
                        inventoryQuantity
                      }
                    }
                  }
                }
              }
            }
          }
        GRAPHQL
        execute_graphql(store, query)
      end
    end

    def fetch_product(store:, product_id:)
      with_session(store) do
        query = <<~GRAPHQL
          query {
            product(id: "gid://shopify/Product/#{product_id}") {
              id
              title
              status
              totalInventory
              variants(first: 100) {
                edges {
                  node {
                    id
                    title
                    sku
                    price
                    inventoryQuantity
                    inventoryItem {
                      id
                      tracked
                    }
                  }
                }
              }
            }
          }
        GRAPHQL
        execute_graphql(store, query)
      end
    end

    def fetch_inventory(store:, location_id: nil)
      with_session(store) do
        query = <<~GRAPHQL
          query {
            inventoryItems(first: 100) {
              edges {
                node {
                  id
                  sku
                  tracked
                  inventoryLevels(first: 10) {
                    edges {
                      node {
                        id
                        available
                        location { id name }
                      }
                    }
                  }
                }
              }
            }
          }
        GRAPHQL
        execute_graphql(store, query)
      end
    end

    def fetch_customers(store:, limit: 50)
      with_session(store) do
        query = <<~GRAPHQL
          query {
            customers(first: #{limit}) {
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
          }
        GRAPHQL
        execute_graphql(store, query)
      end
    end

    def fetch_customer(store:, customer_id:)
      with_session(store) do
        query = <<~GRAPHQL
          query {
            customer(id: "gid://shopify/Customer/#{customer_id}") {
              id
              displayName
              email
              ordersCount
              totalSpent
              orders(first: 10) {
                edges {
                  node {
                    id
                    name
                    createdAt
                    totalPriceSet { shopMoney { amount } }
                  }
                }
              }
            }
          }
        GRAPHQL
        execute_graphql(store, query)
      end
    end

    def execute_shopify_ql(store:, query:)
      with_session(store) do
        graphql_query = <<~GRAPHQL
          query {
            shopifyqlQuery(query: "#{query.gsub('"', '\\"')}") {
              __typename
              ... on TableResponse {
                tableData {
                  columns { name dataType }
                  rowData
                }
              }
              parseErrors {
                code
                message
                range { start { line character } end { line character } }
              }
            }
          }
        GRAPHQL
        execute_graphql(store, graphql_query)
      end
    end

    private

    def with_session(store)
      raise 'Store not connected' unless store.connected?
      yield
    end

    def execute_graphql(store, query)
      response = HTTParty.post(
        "https://#{store.shop_domain}/admin/api/#{SHOPIFY_API_VERSION}/graphql.json",
        headers: {
          'Content-Type' => 'application/json',
          'X-Shopify-Access-Token' => store.access_token
        },
        body: { query: query }.to_json
      )

      if response.success?
        response.parsed_response['data']
      else
        Rails.logger.error("Shopify GraphQL error: #{response.body}")
        { error: response.parsed_response['errors'] }
      end
    end

    def build_orders_query(limit, status, created_at_min, created_at_max)
      filters = []
      filters << "status:#{status}" if status
      filters << "created_at:>=#{created_at_min}" if created_at_min
      filters << "created_at:<=#{created_at_max}" if created_at_max

      query_filter = filters.any? ? "(query: \"#{filters.join(' AND ')}\")" : ""

      <<~GRAPHQL
        query {
          orders(first: #{limit}#{query_filter.empty? ? '' : ", #{query_filter}"}) {
            edges {
              node {
                id
                name
                createdAt
                totalPriceSet { shopMoney { amount currencyCode } }
                lineItems(first: 10) {
                  edges {
                    node {
                      title
                      quantity
                    }
                  }
                }
              }
            }
          }
        }
      GRAPHQL
    end
  end
end
