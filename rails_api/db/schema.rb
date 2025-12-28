ActiveRecord::Schema[7.1].define(version: 2024_12_28_000002) do

  create_table "request_logs", force: :cascade do |t|
    t.bigint "store_id", null: false
    t.text "question", null: false
    t.text "context"
    t.text "answer"
    t.string "confidence"
    t.float "processing_time_ms"
    t.string "ip_address"
    t.string "user_agent"
    t.datetime "responded_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["created_at"], name: "index_request_logs_on_created_at"
    t.index ["store_id"], name: "index_request_logs_on_store_id"
  end

  create_table "stores", force: :cascade do |t|
    t.string "shop_domain", null: false
    t.text "access_token"
    t.string "scope"
    t.datetime "connected_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["shop_domain"], name: "index_stores_on_shop_domain", unique: true
  end

  add_foreign_key "request_logs", "stores"
end
