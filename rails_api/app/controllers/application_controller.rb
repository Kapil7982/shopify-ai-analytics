class ApplicationController < ActionController::API
  include ActionController::HttpAuthentication::Token::ControllerMethods

  before_action :set_default_format

  rescue_from StandardError, with: :handle_standard_error
  rescue_from ActiveRecord::RecordNotFound, with: :handle_not_found
  rescue_from ActionController::ParameterMissing, with: :handle_bad_request

  private

  def set_default_format
    request.format = :json
  end

  def handle_standard_error(exception)
    Rails.logger.error("#{exception.class}: #{exception.message}")
    Rails.logger.error(exception.backtrace.join("\n"))

    render json: {
      error: 'Internal server error',
      message: Rails.env.development? ? exception.message : 'Something went wrong'
    }, status: :internal_server_error
  end

  def handle_not_found(exception)
    render json: {
      error: 'Not found',
      message: exception.message
    }, status: :not_found
  end

  def handle_bad_request(exception)
    render json: {
      error: 'Bad request',
      message: exception.message
    }, status: :bad_request
  end

  def authenticate_store!
    @current_store = Store.find_by(shop_domain: params[:store_id] || request.headers['X-Shop-Domain'])

    unless @current_store&.access_token.present?
      render json: {
        error: 'Unauthorized',
        message: 'Store not authenticated. Please complete OAuth flow first.'
      }, status: :unauthorized
    end
  end
end
