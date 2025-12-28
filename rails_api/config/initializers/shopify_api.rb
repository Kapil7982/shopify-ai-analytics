# Shopify API configuration

ShopifyAPI::Context.setup(
  api_key: ENV['SHOPIFY_API_KEY'],
  api_secret_key: ENV['SHOPIFY_API_SECRET'],
  host: ENV.fetch('HOST', 'http://localhost:3000'),
  scope: 'read_orders,read_products,read_inventory,read_customers,read_analytics',
  is_embedded: false,
  api_version: '2024-01',
  is_private: false
) if defined?(ShopifyAPI)
