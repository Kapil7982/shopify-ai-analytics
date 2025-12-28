module Api
  module V1
    class ProductsController < ApplicationController
      before_action :authenticate_store!

      def index
        products = ShopifyService.fetch_products(
          store: @current_store,
          limit: params[:limit] || 50
        )

        render json: { products: products }
      end

      def show
        product = ShopifyService.fetch_product(
          store: @current_store,
          product_id: params[:id]
        )

        render json: { product: product }
      end
    end
  end
end
