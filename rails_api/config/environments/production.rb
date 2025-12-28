require 'active_support/core_ext/integer/time'

Rails.application.configure do
  config.enable_reloading = false
  config.eager_load = true
  config.consider_all_requests_local = false

  # Caching
  config.action_controller.perform_caching = true
  config.cache_store = :redis_cache_store, { url: ENV['REDIS_URL'] }

  # Logging
  config.log_level = ENV.fetch('RAILS_LOG_LEVEL', 'info')
  config.log_tags = [:request_id]

  # Active Support
  config.active_support.deprecation = :notify

  # Active Record
  config.active_record.dump_schema_after_migration = false

  # Force SSL
  config.force_ssl = true
  config.assume_ssl = true

  # Logging
  if ENV['RAILS_LOG_TO_STDOUT'].present?
    logger = ActiveSupport::Logger.new(STDOUT)
    logger.formatter = config.log_formatter
    config.logger = ActiveSupport::TaggedLogging.new(logger)
  end
end
