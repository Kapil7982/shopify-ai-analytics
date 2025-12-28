module Api
  module V1
    class InventoryController < ApplicationController
      before_action :authenticate_store!

      def index
        inventory = ShopifyService.fetch_inventory(
          store: @current_store,
          location_id: params[:location_id]
        )

        render json: { inventory: inventory }
      end
    end
  end
end
