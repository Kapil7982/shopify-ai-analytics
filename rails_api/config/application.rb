require_relative 'boot'

require 'rails'
require 'active_model/railtie'
require 'active_job/railtie'
require 'active_record/railtie'
require 'action_controller/railtie'
require 'action_view/railtie'

Bundler.require(*Rails.groups)

module ShopifyAnalyticsApi
  class Application < Rails::Application
    config.load_defaults 7.1
    config.api_only = true

    # TimeZone
    config.time_zone = 'UTC'

    # Auto-load lib directory
    config.autoload_lib(ignore: %w[assets tasks])

    # CORS configuration
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*',
          headers: :any,
          methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end
