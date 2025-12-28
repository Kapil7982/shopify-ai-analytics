class RequestLog < ApplicationRecord
  belongs_to :store

  validates :question, presence: true

  scope :recent, -> { order(created_at: :desc) }
  scope :successful, -> { where.not(answer: nil) }

  def successful?
    answer.present?
  end

  def processing_time
    return nil unless responded_at && created_at
    ((responded_at - created_at) * 1000).round(2)
  end
end
