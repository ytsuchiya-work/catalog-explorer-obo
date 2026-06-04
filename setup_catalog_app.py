# Databricks notebook source
# MAGIC %md
# MAGIC # catalog_app スキーマ セットアップノートブック
# MAGIC
# MAGIC このノートブックは `ytcy_azure_east2classic_stable.catalog_app` スキーマに
# MAGIC Unity Catalog Explorer (OBO版) のデモ用テーブルを作成します。
# MAGIC
# MAGIC **実行前の確認事項:**
# MAGIC - `ytcy_azure_east2classic_stable` カタログへの CREATE SCHEMA 権限
# MAGIC - スキーマ・テーブルの CREATE 権限

# COMMAND ----------

CATALOG = "ytcy_azure_east2classic_stable"
SCHEMA = "catalog_app"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA} COMMENT 'Catalog Explorer OBOデモ用スキーマ'")
print(f"スキーマ作成完了: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. 製品カタログテーブル

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.products")

spark.sql(f"""
CREATE TABLE {CATALOG}.{SCHEMA}.products (
  product_id    INT         COMMENT '製品ID',
  product_name  STRING      COMMENT '製品名',
  category      STRING      COMMENT 'カテゴリ',
  unit_price    DOUBLE      COMMENT '単価（円）',
  stock_qty     INT         COMMENT '在庫数',
  supplier      STRING      COMMENT 'サプライヤー',
  launch_date   DATE        COMMENT '発売日'
)
COMMENT '製品カタログ'
""")

spark.sql(f"""
INSERT INTO {CATALOG}.{SCHEMA}.products VALUES
  (1,  'ノートPC Pro 15',        'PC・周辺機器',   148000.0, 120,  '東京テック株式会社',    '2023-04-01'),
  (2,  'ワイヤレスマウス',        'PC・周辺機器',     3200.0, 580,  '大阪電子工業',          '2022-10-15'),
  (3,  'メカニカルキーボード',    'PC・周辺機器',    12800.0, 230,  '大阪電子工業',          '2023-01-20'),
  (4,  '4K モニター 27インチ',   'ディスプレイ',    54800.0,  95,  '東京テック株式会社',    '2023-06-01'),
  (5,  'USBハブ 7ポート',        'PC・周辺機器',     4500.0, 410,  '名古屋パーツ',          '2022-08-10'),
  (6,  'Webカメラ HD',           '映像機器',         8900.0, 175,  '名古屋パーツ',          '2022-11-01'),
  (7,  'ヘッドセット ノイキャン', '音響機器',        22000.0, 140,  'ソニック音響',          '2023-03-15'),
  (8,  '外付けSSD 1TB',          'ストレージ',      15800.0, 320,  '東京テック株式会社',    '2023-05-20'),
  (9,  'スマートスピーカー',      'スマートデバイス', 9800.0, 200,  'ホームAI',              '2023-02-28'),
  (10, 'タブレットスタンド',      'アクセサリ',       2800.0, 650,  '大阪電子工業',          '2022-09-05'),
  (11, 'ノートPC Air 13',        'PC・周辺機器',   118000.0,  80,  '東京テック株式会社',    '2023-07-01'),
  (12, 'ゲーミングヘッドセット', '音響機器',        18500.0,  90,  'ソニック音響',          '2023-08-10'),
  (13, 'ポータブルバッテリー',    'アクセサリ',       6200.0, 450,  '名古屋パーツ',          '2022-12-01'),
  (14, 'プロジェクター HD',       '映像機器',        68000.0,  45,  '東京テック株式会社',    '2023-09-15'),
  (15, 'スマートウォッチ',        'スマートデバイス', 32000.0, 160,  'ホームAI',              '2023-10-01')
""")

print("製品カタログテーブル作成完了")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. 売上トランザクションテーブル

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.sales_transactions")

spark.sql(f"""
CREATE TABLE {CATALOG}.{SCHEMA}.sales_transactions (
  transaction_id INT     COMMENT '取引ID',
  product_id     INT     COMMENT '製品ID',
  sale_date      DATE    COMMENT '売上日',
  quantity       INT     COMMENT '販売数量',
  unit_price     DOUBLE  COMMENT '販売単価（円）',
  amount         DOUBLE  COMMENT '売上金額（円）',
  region         STRING  COMMENT '地域',
  sales_rep      STRING  COMMENT '担当者',
  channel        STRING  COMMENT '販売チャネル'
)
COMMENT '売上トランザクション履歴'
""")

spark.sql(f"""
INSERT INTO {CATALOG}.{SCHEMA}.sales_transactions VALUES
  (1,   1, '2024-01-05',  2, 148000.0,  296000.0, '東京',  '田中太郎',   'オンライン'),
  (2,   3, '2024-01-08',  5,  12800.0,   64000.0, '大阪',  '鈴木花子',   '店舗'),
  (3,   4, '2024-01-12',  1,  54800.0,   54800.0, '名古屋','佐藤次郎',   '法人'),
  (4,   2, '2024-01-15', 10,   3200.0,   32000.0, '東京',  '田中太郎',   'オンライン'),
  (5,   7, '2024-01-18',  3,  22000.0,   66000.0, '福岡',  '山田一郎',   '店舗'),
  (6,   8, '2024-01-22',  4,  15800.0,   63200.0, '大阪',  '鈴木花子',   'オンライン'),
  (7,  11, '2024-01-25',  1, 118000.0,  118000.0, '東京',  '田中太郎',   '法人'),
  (8,   5, '2024-01-28', 15,   4500.0,   67500.0, '名古屋','佐藤次郎',   '店舗'),
  (9,   1, '2024-02-03',  3, 148000.0,  444000.0, '大阪',  '鈴木花子',   '法人'),
  (10,  6, '2024-02-07',  7,   8900.0,   62300.0, '東京',  '田中太郎',   'オンライン'),
  (11,  9, '2024-02-10',  5,   9800.0,   49000.0, '福岡',  '山田一郎',   'オンライン'),
  (12, 14, '2024-02-14',  1,  68000.0,   68000.0, '東京',  '田中太郎',   '法人'),
  (13,  3, '2024-02-18',  8,  12800.0,  102400.0, '大阪',  '鈴木花子',   '店舗'),
  (14, 15, '2024-02-21',  2,  32000.0,   64000.0, '名古屋','佐藤次郎',   'オンライン'),
  (15,  4, '2024-02-25',  2,  54800.0,  109600.0, '東京',  '田中太郎',   '法人'),
  (16,  2, '2024-03-01', 20,   3200.0,   64000.0, '大阪',  '鈴木花子',   '店舗'),
  (17,  7, '2024-03-05',  4,  22000.0,   88000.0, '東京',  '田中太郎',   'オンライン'),
  (18, 12, '2024-03-08',  3,  18500.0,   55500.0, '福岡',  '山田一郎',   '店舗'),
  (19,  1, '2024-03-12',  5, 148000.0,  740000.0, '名古屋','佐藤次郎',   '法人'),
  (20,  8, '2024-03-15',  6,  15800.0,   94800.0, '東京',  '田中太郎',   'オンライン'),
  (21, 10, '2024-03-19', 25,   2800.0,   70000.0, '大阪',  '鈴木花子',   '店舗'),
  (22,  6, '2024-03-22',  9,   8900.0,   80100.0, '東京',  '田中太郎',   'オンライン'),
  (23, 11, '2024-03-26',  2, 118000.0,  236000.0, '大阪',  '鈴木花子',   '法人'),
  (24,  5, '2024-04-01', 12,   4500.0,   54000.0, '名古屋','佐藤次郎',   '店舗'),
  (25,  3, '2024-04-05',  6,  12800.0,   76800.0, '東京',  '田中太郎',   'オンライン'),
  (26,  9, '2024-04-08',  8,   9800.0,   78400.0, '福岡',  '山田一郎',   'オンライン'),
  (27,  4, '2024-04-12',  3,  54800.0,  164400.0, '大阪',  '鈴木花子',   '法人'),
  (28, 13, '2024-04-15', 10,   6200.0,   62000.0, '東京',  '田中太郎',   'オンライン'),
  (29,  1, '2024-04-19',  4, 148000.0,  592000.0, '名古屋','佐藤次郎',   '法人'),
  (30,  7, '2024-04-22',  5,  22000.0,  110000.0, '大阪',  '鈴木花子',   '店舗'),
  (31,  2, '2024-05-02', 15,   3200.0,   48000.0, '東京',  '田中太郎',   'オンライン'),
  (32, 15, '2024-05-06',  3,  32000.0,   96000.0, '福岡',  '山田一郎',   'オンライン'),
  (33, 14, '2024-05-10',  2,  68000.0,  136000.0, '東京',  '田中太郎',   '法人'),
  (34,  8, '2024-05-14',  7,  15800.0,  110600.0, '大阪',  '鈴木花子',   'オンライン'),
  (35, 12, '2024-05-17',  4,  18500.0,   74000.0, '名古屋','佐藤次郎',   '店舗'),
  (36,  6, '2024-05-21', 11,   8900.0,   97900.0, '東京',  '田中太郎',   'オンライン'),
  (37,  1, '2024-05-24',  2, 148000.0,  296000.0, '大阪',  '鈴木花子',   '法人'),
  (38, 10, '2024-05-28', 30,   2800.0,   84000.0, '名古屋','佐藤次郎',   '店舗'),
  (39,  3, '2024-06-03',  9,  12800.0,  115200.0, '東京',  '田中太郎',   'オンライン'),
  (40,  9, '2024-06-07',  6,   9800.0,   58800.0, '福岡',  '山田一郎',   'オンライン'),
  (41,  4, '2024-06-11',  4,  54800.0,  219200.0, '東京',  '田中太郎',   '法人'),
  (42,  5, '2024-06-14', 18,   4500.0,   81000.0, '大阪',  '鈴木花子',   '店舗'),
  (43, 11, '2024-06-18',  3, 118000.0,  354000.0, '名古屋','佐藤次郎',   '法人'),
  (44,  7, '2024-06-21',  6,  22000.0,  132000.0, '東京',  '田中太郎',   'オンライン'),
  (45, 13, '2024-06-25', 12,   6200.0,   74400.0, '大阪',  '鈴木花子',   'オンライン')
""")

print("売上トランザクションテーブル作成完了")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. 顧客セグメントテーブル

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.customer_segments")

spark.sql(f"""
CREATE TABLE {CATALOG}.{SCHEMA}.customer_segments (
  customer_id      INT     COMMENT '顧客ID',
  company_name     STRING  COMMENT '会社名',
  segment          STRING  COMMENT '顧客セグメント',
  region           STRING  COMMENT '地域',
  annual_revenue   DOUBLE  COMMENT '年間売上高（万円）',
  employee_count   INT     COMMENT '従業員数',
  since_year       INT     COMMENT '取引開始年'
)
COMMENT '顧客セグメント情報'
""")

spark.sql(f"""
INSERT INTO {CATALOG}.{SCHEMA}.customer_segments VALUES
  (1, '株式会社ABC商事',    'エンタープライズ', '東京',   8500.0, 1200, 2018),
  (2, '山田製作所',         'SMB',              '大阪',   1200.0,  85,  2020),
  (3, 'ナカムラ技術',       'SMB',              '名古屋',  980.0,  62,  2021),
  (4, '東京メディア株式会社','エンタープライズ', '東京',  15000.0, 3200, 2016),
  (5, '南風商会',           'スタートアップ',   '福岡',    350.0,  28,  2022),
  (6, '大阪ロジスティクス',  'ミッドマーケット', '大阪',   3200.0, 420, 2019),
  (7, 'ITソリューションズ', 'エンタープライズ', '東京',  12000.0, 2500, 2015),
  (8, 'タナカ医療機器',     'SMB',              '神戸',   1800.0, 130, 2021),
  (9, '日本フード株式会社', 'ミッドマーケット', '東京',   4500.0, 680, 2018),
  (10,'さくら教育',         'スタートアップ',   '京都',    280.0,  22, 2023)
""")

print("顧客セグメントテーブル作成完了")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. 集計テーブル（リネージデモ用）
# MAGIC
# MAGIC 上記3テーブルを元に集計・加工したテーブルを作成します。
# MAGIC `CREATE TABLE AS SELECT` によってリネージが `system.access.table_lineage` に記録されます。
# MAGIC
# MAGIC | テーブル名 | ソーステーブル | 内容 |
# MAGIC |-----------|--------------|------|
# MAGIC | `monthly_sales_summary` | `sales_transactions` | 月次・地域・チャネル別売上集計 |
# MAGIC | `product_sales_ranking` | `sales_transactions` + `products` | 製品別売上ランキング |
# MAGIC | `customer_segment_performance` | `sales_transactions` + `customer_segments` | セグメント別売上パフォーマンス |
# MAGIC | `channel_category_analysis` | `sales_transactions` + `products` | チャネル×カテゴリ別分析 |

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4-1. 月次売上サマリー

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.monthly_sales_summary
COMMENT '月次・地域・チャネル別売上集計 — ソース: sales_transactions'
AS
SELECT
  DATE_FORMAT(sale_date, 'yyyy-MM')  AS year_month,
  region,
  channel,
  COUNT(transaction_id)              AS transaction_count,
  SUM(quantity)                      AS total_quantity,
  SUM(amount)                        AS total_revenue,
  AVG(amount)                        AS avg_transaction_value
FROM {CATALOG}.{SCHEMA}.sales_transactions
GROUP BY DATE_FORMAT(sale_date, 'yyyy-MM'), region, channel
ORDER BY year_month, region, channel
""")

print("monthly_sales_summary 作成完了")
display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.monthly_sales_summary ORDER BY year_month LIMIT 10"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4-2. 製品別売上ランキング

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.product_sales_ranking
COMMENT '製品別累計売上ランキング — ソース: sales_transactions + products'
AS
SELECT
  p.product_id,
  p.product_name,
  p.category,
  p.supplier,
  COUNT(s.transaction_id)                            AS transaction_count,
  SUM(s.quantity)                                    AS total_quantity_sold,
  SUM(s.amount)                                      AS total_revenue,
  RANK() OVER (ORDER BY SUM(s.amount) DESC)          AS revenue_rank
FROM {CATALOG}.{SCHEMA}.sales_transactions s
JOIN {CATALOG}.{SCHEMA}.products p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.supplier
ORDER BY revenue_rank
""")

print("product_sales_ranking 作成完了")
display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.product_sales_ranking ORDER BY revenue_rank LIMIT 10"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4-3. 顧客セグメント別パフォーマンス

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.customer_segment_performance
COMMENT 'セグメント×チャネル別売上パフォーマンス — ソース: sales_transactions + customer_segments'
AS
SELECT
  cs.segment,
  s.channel,
  COUNT(DISTINCT cs.customer_id)  AS customer_count,
  COUNT(s.transaction_id)         AS transaction_count,
  SUM(s.amount)                   AS total_revenue,
  AVG(s.amount)                   AS avg_order_value
FROM {CATALOG}.{SCHEMA}.sales_transactions s
JOIN {CATALOG}.{SCHEMA}.customer_segments cs ON s.region = cs.region
GROUP BY cs.segment, s.channel
ORDER BY total_revenue DESC
""")

print("customer_segment_performance 作成完了")
display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.customer_segment_performance ORDER BY total_revenue DESC"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4-4. チャネル×カテゴリ別分析

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.channel_category_analysis
COMMENT 'チャネル×カテゴリ別売上分析 — ソース: sales_transactions + products'
AS
SELECT
  s.channel,
  p.category,
  COUNT(s.transaction_id)  AS transaction_count,
  SUM(s.quantity)          AS total_quantity,
  SUM(s.amount)            AS total_revenue,
  AVG(s.unit_price)        AS avg_unit_price
FROM {CATALOG}.{SCHEMA}.sales_transactions s
JOIN {CATALOG}.{SCHEMA}.products p ON s.product_id = p.product_id
GROUP BY s.channel, p.category
ORDER BY total_revenue DESC
""")

print("channel_category_analysis 作成完了")
display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.channel_category_analysis ORDER BY total_revenue DESC"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 権限付与
# MAGIC
# MAGIC アプリのサービスプリンシパル（OBOモードでは不要）およびユーザーへの権限付与例。
# MAGIC OBOモードでは、各ユーザーが自身の権限でデータにアクセスするため、
# MAGIC ユーザー/グループへの権限付与が重要です。

# COMMAND ----------

# アカウント全ユーザーにBROWSE権限を付与（カタログ・スキーマの一覧表示用）
spark.sql(f"GRANT BROWSE ON CATALOG {CATALOG} TO `account users`")
spark.sql(f"GRANT USE SCHEMA ON SCHEMA {CATALOG}.{SCHEMA} TO `account users`")

BASE_TABLES = ["products", "sales_transactions", "customer_segments"]
AGG_TABLES  = ["monthly_sales_summary", "product_sales_ranking",
               "customer_segment_performance", "channel_category_analysis"]

for tbl in BASE_TABLES + AGG_TABLES:
    spark.sql(f"GRANT SELECT ON TABLE {CATALOG}.{SCHEMA}.{tbl} TO `account users`")
    print(f"  SELECT 付与: {tbl}")

print("\n権限付与完了")

# COMMAND ----------

# 作成確認
display(spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}"))

# COMMAND ----------

# 件数確認
for tbl in BASE_TABLES + AGG_TABLES:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {CATALOG}.{SCHEMA}.{tbl}").collect()[0]["cnt"]
    print(f"  {tbl}: {count}件")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 期待されるリネージグラフ
# MAGIC
# MAGIC ```
# MAGIC products ──────────────────┬──→ product_sales_ranking
# MAGIC                            └──→ channel_category_analysis
# MAGIC
# MAGIC sales_transactions ────────┬──→ monthly_sales_summary
# MAGIC                            ├──→ product_sales_ranking
# MAGIC                            ├──→ customer_segment_performance
# MAGIC                            └──→ channel_category_analysis
# MAGIC
# MAGIC customer_segments ─────────└──→ customer_segment_performance
# MAGIC ```
# MAGIC
# MAGIC `system.access.table_lineage` に反映されるまで数分かかる場合があります。

# COMMAND ----------

print("セットアップ完了!")
print(f"\nGenieスペースの作成手順:")
print(f"1. Databricks UIで「Genie」を開く")
print(f"2. 「スペースを作成」をクリック")
print(f"3. テーブルとして以下を追加:")
for tbl in BASE_TABLES + AGG_TABLES:
    print(f"   - {CATALOG}.{SCHEMA}.{tbl}")
print(f"4. Genieスペースを作成したら、アプリから利用可能になります")
