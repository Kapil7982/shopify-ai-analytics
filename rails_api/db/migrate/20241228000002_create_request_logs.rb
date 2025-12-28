class CreateRequestLogs < ActiveRecord::Migration[7.1]
  def change
    create_table :request_logs do |t|
      t.references :store, null: false, foreign_key: true
      t.text :question, null: false
      t.text :context
      t.text :answer
      t.string :confidence
      t.float :processing_time_ms
      t.string :ip_address
      t.string :user_agent
      t.datetime :responded_at

      t.timestamps
    end

    add_index :request_logs, :created_at
  end
end
