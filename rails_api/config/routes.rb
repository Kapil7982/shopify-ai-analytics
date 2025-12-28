Rails.application.routes.draw do
  # Health check endpoint
  get 'health', to: 'health#show'

  # Shopify OAuth routes
  get '/auth/shopify', to: 'shopify_auth#init'
  get '/auth/shopify/callback', to: 'shopify_auth#callback'
  delete '/auth/logout', to: 'shopify_auth#logout'

  # API routes
  namespace :api do
    namespace :v1 do
      # Main question endpoint
      post 'questions', to: 'questions#create'

      # Store management
      resources :stores, only: [:index, :show] do
        member do
          get 'status'
        end
      end

      # Direct Shopify data endpoints (optional)
      resources :orders, only: [:index, :show]
      resources :products, only: [:index, :show]
      resources :inventory, only: [:index]
      resources :customers, only: [:index, :show]
    end
  end
end
