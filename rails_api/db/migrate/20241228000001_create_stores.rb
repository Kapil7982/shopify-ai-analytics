class CreateStores < ActiveRecord::Migration[7.1]
  def change
    create_table :stores do |t|
      t.string :shop_domain, null: false, index: { unique: true }
      t.text :access_token
      t.string :scope
      t.datetime :connected_at

      t.timestamps
    end
  end
end
