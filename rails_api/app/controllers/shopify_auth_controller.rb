class ShopifyAuthController < ApplicationController
  SHOPIFY_SCOPES = 'read_orders,read_products,read_inventory,read_customers,read_analytics'

  def init
    shop = params[:shop]

    unless shop.present?
      render json: { error: 'Shop parameter is required' }, status: :bad_request
      return
    end

    shop = sanitize_shop_domain(shop)
    state = SecureRandom.hex(24)

    # Store state in cache for CSRF protection
    Rails.cache.write("shopify_oauth_state:#{state}", shop, expires_in: 10.minutes)

    auth_url = build_auth_url(shop, state)
    redirect_to auth_url, allow_other_host: true
  end

  def callback
    shop = params[:shop]
    code = params[:code]
    state = params[:state]

    # Verify state for CSRF protection
    cached_shop = Rails.cache.read("shopify_oauth_state:#{state}")
    unless cached_shop == shop
      render json: { error: 'Invalid state parameter' }, status: :unauthorized
      return
    end

    Rails.cache.delete("shopify_oauth_state:#{state}")

    # Exchange code for access token
    token_response = exchange_code_for_token(shop, code)

    if token_response[:access_token]
      store = Store.find_or_initialize_by(shop_domain: shop)
      store.update!(
        access_token: token_response[:access_token],
        scope: token_response[:scope],
        connected_at: Time.current
      )

      render json: {
        message: 'Successfully connected to Shopify',
        store_id: shop,
        scope: token_response[:scope]
      }
    else
      render json: {
        error: 'Failed to authenticate',
        message: token_response[:error_description] || 'Unknown error'
      }, status: :unauthorized
    end
  end

  def logout
    shop = params[:shop]
    store = Store.find_by(shop_domain: shop)

    if store
      store.update!(access_token: nil, scope: nil)
      render json: { message: 'Successfully disconnected' }
    else
      render json: { error: 'Store not found' }, status: :not_found
    end
  end

  private

  def sanitize_shop_domain(shop)
    shop = shop.strip.downcase
    shop = "#{shop}.myshopify.com" unless shop.include?('.myshopify.com')
    shop
  end

  def build_auth_url(shop, state)
    params = {
      client_id: ENV['SHOPIFY_API_KEY'],
      scope: SHOPIFY_SCOPES,
      redirect_uri: ENV['SHOPIFY_REDIRECT_URI'],
      state: state
    }

    "https://#{shop}/admin/oauth/authorize?#{params.to_query}"
  end

  def exchange_code_for_token(shop, code)
    response = HTTParty.post(
      "https://#{shop}/admin/oauth/access_token",
      body: {
        client_id: ENV['SHOPIFY_API_KEY'],
        client_secret: ENV['SHOPIFY_API_SECRET'],
        code: code
      }
    )

    if response.success?
      {
        access_token: response['access_token'],
        scope: response['scope']
      }
    else
      {
        error: response['error'],
        error_description: response['error_description']
      }
    end
  end
end
