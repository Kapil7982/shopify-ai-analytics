module Api
  module V1
    class StoresController < ApplicationController
      before_action :set_store, only: [:show, :status]

      def index
        stores = Store.all.select(:id, :shop_domain, :connected_at, :created_at)

        render json: {
          stores: stores.map { |s| store_summary(s) }
        }
      end

      def show
        render json: {
          store: store_details(@store)
        }
      end

      def status
        render json: {
          store_id: @store.shop_domain,
          connected: @store.access_token.present?,
          connected_at: @store.connected_at,
          scope: @store.scope
        }
      end

      private

      def set_store
        @store = Store.find_by!(shop_domain: params[:id])
      end

      def store_summary(store)
        {
          id: store.shop_domain,
          connected: store.access_token.present?,
          connected_at: store.connected_at
        }
      end

      def store_details(store)
        {
          id: store.shop_domain,
          connected: store.access_token.present?,
          connected_at: store.connected_at,
          scope: store.scope,
          created_at: store.created_at
        }
      end
    end
  end
end
