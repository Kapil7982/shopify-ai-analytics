class Store < ApplicationRecord
  has_many :request_logs, dependent: :destroy

  validates :shop_domain, presence: true, uniqueness: true

  # encrypts :access_token  # Uncomment in production with Rails credentials

  scope :connected, -> { where.not(access_token: nil) }

  def connected?
    access_token.present?
  end

  def shopify_session
    return nil unless connected?

    ShopifyAPI::Auth::Session.new(
      shop: shop_domain,
      access_token: access_token
    )
  end
end
