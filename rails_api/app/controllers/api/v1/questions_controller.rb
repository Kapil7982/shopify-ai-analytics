module Api
  module V1
    class QuestionsController < ApplicationController
      before_action :authenticate_store!
      before_action :validate_question_params, only: [:create]

      def create
        # Log the request (bonus feature)
        log_request

        # Forward question to Python AI service
        ai_response = AiService.ask_question(
          store: @current_store,
          question: question_params[:question],
          context: question_params[:context]
        )

        if ai_response[:success]
          # Log successful response
          log_response(ai_response)

          render json: {
            answer: ai_response[:answer],
            confidence: ai_response[:confidence],
            query_used: ai_response[:query_used],
            data_source: ai_response[:data_source],
            metadata: {
              processing_time_ms: ai_response[:processing_time_ms],
              timestamp: Time.current.iso8601
            }
          }
        else
          render json: {
            error: 'Failed to process question',
            message: ai_response[:error],
            suggestions: ai_response[:suggestions]
          }, status: :unprocessable_entity
        end
      end

      private

      def question_params
        params.permit(:store_id, :question, :context)
      end

      def validate_question_params
        unless question_params[:question].present?
          render json: {
            error: 'Bad request',
            message: 'Question parameter is required'
          }, status: :bad_request
        end
      end

      def log_request
        RequestLog.create(
          store: @current_store,
          question: question_params[:question],
          context: question_params[:context],
          ip_address: request.remote_ip,
          user_agent: request.user_agent
        )
      rescue StandardError => e
        Rails.logger.warn("Failed to log request: #{e.message}")
      end

      def log_response(ai_response)
        RequestLog.where(
          store: @current_store,
          question: question_params[:question]
        ).last&.update(
          answer: ai_response[:answer],
          confidence: ai_response[:confidence],
          processing_time_ms: ai_response[:processing_time_ms],
          responded_at: Time.current
        )
      rescue StandardError => e
        Rails.logger.warn("Failed to log response: #{e.message}")
      end
    end
  end
end
