class AiService
  PYTHON_SERVICE_URL = ENV.fetch('PYTHON_SERVICE_URL', 'http://localhost:8000')
  TIMEOUT = 60.seconds

  class << self
    def ask_question(store:, question:, context: nil)
      start_time = Time.current

      response = HTTParty.post(
        "#{PYTHON_SERVICE_URL}/api/v1/analyze",
        headers: {
          'Content-Type' => 'application/json',
          'Accept' => 'application/json'
        },
        body: {
          store_id: store.shop_domain,
          access_token: store.access_token,
          question: question,
          context: context
        }.to_json,
        timeout: TIMEOUT
      )

      processing_time = ((Time.current - start_time) * 1000).round(2)

      if response.success?
        parse_success_response(response, processing_time)
      else
        parse_error_response(response)
      end
    rescue HTTParty::Error, Net::ReadTimeout, Errno::ECONNREFUSED => e
      handle_connection_error(e)
    rescue StandardError => e
      handle_unexpected_error(e)
    end

    private

    def parse_success_response(response, processing_time)
      body = response.parsed_response

      {
        success: true,
        answer: body['answer'],
        confidence: body['confidence'] || 'medium',
        query_used: body['query_used'],
        data_source: body['data_source'],
        raw_data: body['raw_data'],
        processing_time_ms: processing_time
      }
    end

    def parse_error_response(response)
      body = response.parsed_response

      {
        success: false,
        error: body['error'] || 'Unknown error from AI service',
        suggestions: body['suggestions'] || []
      }
    end

    def handle_connection_error(error)
      Rails.logger.error("AI Service connection error: #{error.message}")

      {
        success: false,
        error: 'Unable to connect to AI service',
        suggestions: [
          'Please try again in a few moments',
          'Check if the AI service is running'
        ]
      }
    end

    def handle_unexpected_error(error)
      Rails.logger.error("AI Service unexpected error: #{error.class} - #{error.message}")
      Rails.logger.error(error.backtrace.join("\n"))

      {
        success: false,
        error: 'An unexpected error occurred',
        suggestions: ['Please try again or contact support']
      }
    end
  end
end
