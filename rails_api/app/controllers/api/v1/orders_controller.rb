module Api
  module V1
    class OrdersController < ApplicationController
      before_action :authenticate_store!

      def index
        orders = ShopifyService.fetch_orders(
          store: @current_store,
          limit: params[:limit] || 50,
          status: params[:status],
          created_at_min: params[:created_at_min],
          created_at_max: params[:created_at_max]
        )

        render json: { orders: orders }
      end

      def show
        order = ShopifyService.fetch_order(
          store: @current_store,
          order_id: params[:id]
        )

        render json: { order: order }
      end
    end
  end
end
