class HealthController < ApplicationController
  def show
    render json: {
      status: 'healthy',
      timestamp: Time.current.iso8601,
      version: '1.0.0',
      services: {
        database: database_healthy?,
        python_service: python_service_healthy?
      }
    }
  end

  private

  def database_healthy?
    ActiveRecord::Base.connection.active?
  rescue StandardError
    false
  end

  def python_service_healthy?
    response = HTTParty.get(
      "#{ENV['PYTHON_SERVICE_URL']}/health",
      timeout: 5
    )
    response.success?
  rescue StandardError
    false
  end
end
