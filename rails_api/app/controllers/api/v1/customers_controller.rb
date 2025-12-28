module Api
  module V1
    class CustomersController < ApplicationController
      before_action :authenticate_store!

      def index
        customers = ShopifyService.fetch_customers(
          store: @current_store,
          limit: params[:limit] || 50
        )

        render json: { customers: customers }
      end

      def show
        customer = ShopifyService.fetch_customer(
          store: @current_store,
          customer_id: params[:id]
        )

        render json: { customer: customer }
      end
    end
  end
end
