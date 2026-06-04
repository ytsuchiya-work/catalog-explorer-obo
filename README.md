# Catalog Explorer (OBO認証版)

Unity Catalog のテーブル探索と Genie 問い合わせを、**ユーザー認証（OBO: On-Behalf-Of）** で動作させる Databricks Apps アプリです。

## OBO認証とは

OBO (On-Behalf-Of) 認証では、アプリがサービスプリンシパルではなく**アクセスしたユーザー自身の権限**でDatabricksリソースにアクセスします。

| 認証方式 | アクセス権限 | 用途 |
|---------|------------|------|
| サービスプリンシパル（旧版） | アプリのSPが持つ固定の権限 | 全ユーザーが同一権限でアクセス |
| **OBO（本版）** | ログインユーザー自身の権限 | UCポリシー・行フィルタ・列マスキングが適用される |

仕組み：Databricks Apps プロキシがユーザーのアクセストークンを `X-Forwarded-Access-Token` ヘッダーでアプリに転送し、アプリはそのトークンを使用してDatabricks APIを呼び出します。

> **重要**: OBOトークンはデフォルトでは基本的なスコープのみ持ちます。Unity Catalog・SQL・Genie APIを利用するには、アプリの「ユーザー認証」設定で追加スコープを明示的に設定する必要があります。

## アーキテクチャ

```
ユーザー (ブラウザ)
    ↓  ログイン
Databricks Apps プロキシ
    ↓  X-Forwarded-Access-Token ヘッダーを付与
Streamlit アプリ (app.py)
    ↓  OBOトークンでWorkspaceClient作成
Databricks API (Unity Catalog / SQL / Genie)
    ↓  ユーザー権限でフィルタリング
データ返却
```

## 実行手順

### 1. データの準備

`setup_catalog_app.py` ノートブックを Databricks 上で実行して、デモ用テーブルを作成します。

```
ytcy_azure_east2classic_stable.catalog_app
├── products             # 製品カタログ
├── sales_transactions   # 売上トランザクション
└── customer_segments    # 顧客セグメント
```

### 2. Genie スペースの作成

1. Databricks UI で「Genie」を開く
2. 「スペースを作成」をクリック
3. 上記3テーブルを追加
4. スペースを保存

### 3. Databricks Apps でアプリを作成

Databricks Apps の設定:

1. **アプリを作成** → カスタムアプリを作成
2. **Gitリポジトリ設定**: このリポジトリを指定
3. **アプリのリソース（重要）**:
   - SQLウェアハウス: 「使用可能」権限を追加
   - UCカタログ: 「使用可能」権限を追加（任意）
   - Genieスペース: 「実行可能」権限を追加
   - **「ユーザー認証」セクションで以下のOAuthスコープを追加**:
     | スコープ | 説明 |
     |---------|------|
     | `catalog.catalogs:read` | Unity Catalog内のカタログ一覧を読み取る |
     | `catalog.schemas:read` | Unity Catalog内のスキーマ一覧を読み取る |
     | `catalog.tables:read` | Unity Catalog内のテーブル情報を読み取る |
     | `sql` | SQLの実行とSQL関連リソースの管理 |
     | `genie` | Databricks Genieへのアクセス |
4. **コンピュート**: M以上を推奨

> **重要**: サービスプリンシパル方式（旧版）と異なり、OBO方式ではアプリのリソース設定で「ユーザー認証」を有効にし、必要なOAuthスコープを追加する必要があります。スコープが不足していると `Provided OAuth token does not have required scopes` エラーが発生します。

### 4. デプロイ

- 「Gitから」デプロイ → このリポジトリの `main` ブランチを指定
- デプロイ完了後、アプリURLにアクセス
- 初回アクセス時に同意画面が表示される場合があります（「このアプリはあなたの認証情報を使用してリソースにアクセスします」）

## アプリを使用する際の権限設定

OBO認証では、**各ユーザーが自身のUC権限**でデータにアクセスします。
サービスプリンシパルへの権限付与は不要になりますが、代わりにユーザー/グループへの権限付与が必要です。

```sql
-- アカウント全ユーザーへの基本権限
GRANT BROWSE ON CATALOG ytcy_azure_east2classic_stable TO `account users`;
GRANT USE SCHEMA ON SCHEMA ytcy_azure_east2classic_stable.catalog_app TO `account users`;
GRANT SELECT ON TABLE ytcy_azure_east2classic_stable.catalog_app.products TO `account users`;
GRANT SELECT ON TABLE ytcy_azure_east2classic_stable.catalog_app.sales_transactions TO `account users`;
GRANT SELECT ON TABLE ytcy_azure_east2classic_stable.catalog_app.customer_segments TO `account users`;

-- Genieスペースへのアクセス権（スペースIDを実際の値に置換）
GRANT CAN_USE ON GENIE_SPACE <genie_space_id> TO `account users`;
```

## 使い方

サイドバー下部の **ページ選択** で機能を切り替えます。

### 📊 テーブル検索

1. **SQLウェアハウスを選択** — サンプルデータ取得に使用（ユーザーが権限を持つもののみ表示）
2. **カタログ・スキーマを選択** — デフォルトは `ytcy_azure_east2classic_stable.catalog_app`
3. **テーブルを検索** — ユーザーが `SELECT` 権限を持つテーブルのみ操作可能
4. **テーブル詳細を確認** — メタデータ・カラム定義・Lineage・サンプルデータ

> OBO認証では、列マスキングポリシーや行フィルタポリシーが自動的にユーザー権限に基づいて適用されます。

### 🤖 Genie 問い合わせ

1. **Genieスペースを選択** — ユーザーがアクセス権を持つスペースのみ表示
2. **質問を入力** — 例:「月別の売上推移を見せて」「売れ筋製品トップ5は？」
3. **回答を確認** — テキスト・生成SQL・クエリ結果

## 権限モデルについて：BROWSE 権限とデータアクセスの違い

### BROWSE 権限とは

- Catalog Explorer（UI）で作成されたカタログには、デフォルトで **All account users** グループに `BROWSE` 権限が付与されます。
- `BROWSE` 権限があれば、カタログ・スキーマ・テーブルの **名前やメタデータを閲覧** できます。
- 対象範囲：REST API、information_schema、リネージグラフ、検索結果など。

### BROWSE だけではデータは読めない

| 操作 | 必要な権限 |
|------|-----------|
| カタログ・スキーマ・テーブル一覧の表示 | `BROWSE`（デフォルトで付与される場合あり） |
| テーブルのデータ取得（SELECT） | `USE CATALOG` + `USE SCHEMA` + `SELECT` |
| テーブルへのデータ書き込み | `USE CATALOG` + `USE SCHEMA` + `MODIFY` |

### 注意事項

SQL文やCLIで作成されたカタログには `BROWSE` がデフォルトで付与されません：

```sql
GRANT BROWSE ON CATALOG <catalog_name> TO `account users`;
```

---

## 実装時に発生したエラーと解決策

### 1. `st.context` が存在しない (AttributeError)

**エラー内容:**
```
AttributeError: module 'streamlit' has no attribute 'context'
```

**原因:** Streamlit 1.37.0 未満のバージョンでは `st.context` が利用できない。

**解決策:** `requirements.txt` に `streamlit>=1.37.0` を指定する。また、コード上でも `AttributeError` をキャッチしてフォールバック処理を実装する:
```python
def get_user_token():
    try:
        return st.context.headers.get("X-Forwarded-Access-Token")
    except AttributeError:
        return None  # ローカル開発時はNoneを返す
```

---

### 2. OBOトークンのスコープ不足（`Provided OAuth token does not have required scopes`）

**エラー内容:**
```
接続エラー: Provided OAuth token does not have required scopes: unity-catalog
接続エラー: Provided OAuth token does not have required scopes: sql
```

**原因:** Databricks Apps の `X-Forwarded-Access-Token` はデフォルトスコープのみ持ち、Unity Catalog API や SQL API への呼び出しに必要なスコープが含まれていない。

**解決策:** アプリの「ユーザー認証」設定で必要なOAuthスコープを追加する（`catalog.catalogs:read`、`catalog.schemas:read`、`catalog.tables:read`、`sql`、`genie`）。

---

### 3. Databricks SDK の多重認証エラー（`more than one authorization method configured`）

**エラー内容:**
```
validate: more than one authorization method configured: oauth and pat
```

**原因:** Databricks Apps ランタイムは `DATABRICKS_CLIENT_ID`（M2M OAuth）と `DATABRICKS_TOKEN` を環境変数に注入する。`Config(host=host, token=obo_token)` で OBOトークンを渡しても、SDKが環境変数の `DATABRICKS_CLIENT_ID` も読み込み、PAT + OAuth の2つが「設定済み」と判定されて競合する。

**解決策:** `Config` に `auth_type="pat"` を明示的に渡すことで `Config._validate()` の多重認証チェックをバイパスし、`DefaultCredentials` が PAT のみを使うよう強制する:
```python
cfg = Config(host=host, token=obo_token, auth_type="pat")
return WorkspaceClient(config=cfg)
```

---

### 4. `@st.cache_resource` でOBOトークンが共有されてしまう

**問題:** 旧実装の `@st.cache_resource` では全ユーザーが同一の `WorkspaceClient` を共有してしまい、OBOが機能しない。

**解決策:** `st.session_state` に `WorkspaceClient` をキャッシュし、セッションごとに個別のクライアントを持つ。トークンのハッシュ値で変更を検知して再生成する:
```python
def get_workspace_client():
    token = get_user_token()
    token_hash = hash(token or "")
    if st.session_state.get("_wc_hash") != token_hash:
        st.session_state._workspace_client = _make_client(token)
        st.session_state._wc_hash = token_hash
    return st.session_state._workspace_client
```

---

### 5. `@st.cache_data` が複数ユーザー間でデータを共有してしまう

**問題:** `@st.cache_data` はグローバルキャッシュであり、ユーザーAのデータがユーザーBに返される可能性がある。

**解決策:** キャッシュ対象関数の第一引数に `user_token` を追加することで、ユーザーごとに別のキャッシュエントリを使用する:
```python
@st.cache_data(ttl=300, show_spinner=False)
def get_catalogs(user_token: str | None):
    w = _make_client(user_token)
    return [c.name for c in w.catalogs.list()]

# 呼び出し時
catalogs = get_catalogs(get_user_token())
```

---

### 6. OBOトークンが None (ローカル開発時)

**問題:** ローカル開発環境では `X-Forwarded-Access-Token` ヘッダーが存在しないため、`get_user_token()` が `None` を返す。

**解決策:** `_make_client(None)` は Databricks SDK のデフォルト認証（`~/.databrickscfg` や環境変数）にフォールバックするよう実装する。サイドバーに「ローカル開発モード」の警告を表示する。

---

### 7. app.yaml に `service-principal-token` が残っているとOBO認証が機能しない

**問題:** `app.yaml` に `DATABRICKS_TOKEN: service-principal-token` が設定されていると、環境変数 `DATABRICKS_TOKEN` が設定され、意図しないSP認証が有効になる可能性がある。

**解決策:** `app.yaml` から `DATABRICKS_TOKEN` 行を削除し、`DATABRICKS_HOST: workspace-url` のみ残す。OBOトークンはHTTPヘッダー経由で受け取る。

---

### 8. Genieスペースが表示されない

**問題:** OBOモードでGenieスペース一覧が空になる。

**原因と解決策:**
1. ユーザーにGenieスペースへのアクセス権がない → スペースの「権限」でユーザー/グループを追加する
2. アプリのリソース設定でGenieスペースを追加していない → Databricks Apps のUI でリソースにGenieスペースを追加する

---

### 9. サンプルデータ取得時に権限エラー

**エラー内容:**
```
クエリ失敗: User does not have SELECT privilege on table ...
```

**原因:** OBOモードではユーザー自身のUC権限が使われるため、SELECT権限がないテーブルのデータは取得できない（これは想定通りの動作）。

**解決策:** 必要なユーザー/グループに SELECT 権限を付与する:
```sql
GRANT SELECT ON TABLE <catalog>.<schema>.<table> TO `<user_or_group>`;
```

---

### 10. Lineage API で `unity-catalog` スコープエラー（根本原因と2方式の比較）

**エラー内容:**
```
Provided OAuth token does not have required scopes: unity-catalog
```

**根本原因:**

`/api/2.0/lineage-tracking/table-lineage` REST API は legacy スコープ `unity-catalog` を要求する。
`catalog.catalogs:read` などの細粒度スコープは `unity-catalog` を **満たさない**（内部的に別のスコープ体系）。

**方式①: Account Admin による恒久対応（REST API を使う場合）**

Apps UI の「ユーザー認証」設定では `unity-catalog` を追加できない場合がある。
Account レベルの custom OAuth app integration を CLI/SDK/API で更新する必要がある:

```bash
# account-level CLI で custom OAuth app integration に unity-catalog を追加
databricks account custom-app-integrations update <integration_id> \
  --scopes "catalog.catalogs:read,catalog.schemas:read,catalog.tables:read,sql,genie,unity-catalog"
```

スコープ追加後は Cookie クリアまたはシークレットウィンドウで再アクセスして再同意が必要。

**方式②: system tables を SQL 経由で参照（`unity-catalog` スコープ不要・本アプリの実装）**

REST API を使わず `system.access.table_lineage` を SQL Warehouse 経由で照会することで、`sql` スコープのみで動作する:

```sql
-- Upstream（このテーブルに書き込んでいるテーブル）
SELECT DISTINCT source_table_full_name AS tbl
FROM system.access.table_lineage
WHERE target_table_full_name = '<catalog>.<schema>.<table>'
  AND source_table_full_name IS NOT NULL
ORDER BY tbl LIMIT 100;

-- Downstream（このテーブルからデータを読んでいるテーブル）
SELECT DISTINCT target_table_full_name AS tbl
FROM system.access.table_lineage
WHERE source_table_full_name = '<catalog>.<schema>.<table>'
  AND target_table_full_name IS NOT NULL
ORDER BY tbl LIMIT 100;
```

前提: 管理者が `system.access` スキーマを有効化していること。

**本アプリのUI:**

Lineage セクションに2つのタブを設けて両方式を並べて表示し、スコープ差異を視覚的に確認できるようにしている:

| タブ | 使用API | 必要スコープ | 期待動作 |
|-----|---------|------------|---------|
| 🔗 Lineage API (REST) | `/api/2.0/lineage-tracking/table-lineage` | `unity-catalog`（legacy） | スコープ未追加時はエラー表示 |
| 📊 System Tables (SQL) | `system.access.table_lineage` | `sql` | エラーなく結果を返す |

---

## ファイル構成

```
catalog-explorer-obo/
├── app.py                  # メインアプリ（OBO認証実装）
├── app.yaml                # Databricks Apps 設定
├── requirements.txt        # Python依存パッケージ
├── setup_catalog_app.py    # データ準備ノートブック（Databricks上で実行）
└── README.md               # このファイル
```
