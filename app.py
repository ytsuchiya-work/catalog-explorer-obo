import os
import time
import base64

import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.sql import StatementState
import pandas as pd

st.set_page_config(
    page_title="Unity Catalog Explorer (OBO)",
    page_icon="🔍",
    layout="wide"
)

# ─────────────────────────────────────────────
# OBO認証
# ─────────────────────────────────────────────

def get_user_token() -> str | None:
    """X-Forwarded-Access-TokenヘッダーからOBOトークンを取得"""
    try:
        return st.context.headers.get("X-Forwarded-Access-Token")
    except AttributeError:
        return None


def _make_client(token: str | None) -> WorkspaceClient:
    """指定トークン（またはデフォルト認証）のWorkspaceClientを作成"""
    host = os.environ.get("DATABRICKS_HOST")
    if token and host:
        return WorkspaceClient(config=Config(host=host, token=token))
    return WorkspaceClient()


def get_workspace_client() -> WorkspaceClient:
    """OBOトークンでWorkspaceClientを初期化（セッション内でキャッシュ）"""
    token = get_user_token()
    token_hash = hash(token or "")

    if st.session_state.get("_wc_hash") != token_hash:
        st.session_state._workspace_client = _make_client(token)
        st.session_state._wc_hash = token_hash

    return st.session_state._workspace_client


def get_current_user_info() -> dict:
    """現在のログインユーザー情報を取得（セッション内でキャッシュ）"""
    wc_hash = st.session_state.get("_wc_hash")
    if "_user_info" not in st.session_state or st.session_state.get("_user_wc_hash") != wc_hash:
        try:
            w = get_workspace_client()
            me = w.current_user.me()
            display = getattr(me, "display_name", None) or getattr(me, "user_name", None) or "Unknown"
            email = getattr(me, "user_name", None) or display
            st.session_state._user_info = {"display_name": display, "email": email}
        except Exception:
            st.session_state._user_info = {"display_name": "Unknown", "email": "Unknown"}
        st.session_state._user_wc_hash = wc_hash
    return st.session_state._user_info


# ─────────────────────────────────────────────
# キャッシュ付きデータ取得（トークンでユーザー識別）
# ─────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_warehouses(user_token: str | None):
    """SQLウェアハウス一覧を取得"""
    w = _make_client(user_token)
    warehouses = list(w.warehouses.list())
    return [(wh.id, wh.name) for wh in warehouses]


@st.cache_data(ttl=300, show_spinner=False)
def get_catalogs(user_token: str | None):
    w = _make_client(user_token)
    catalogs = list(w.catalogs.list())
    return [c.name for c in catalogs]


@st.cache_data(ttl=300, show_spinner=False)
def get_schemas(user_token: str | None, catalog_name: str):
    w = _make_client(user_token)
    schemas = list(w.schemas.list(catalog_name=catalog_name))
    return [s.name for s in schemas]


@st.cache_data(ttl=300, show_spinner=False)
def get_tables(user_token: str | None, catalog_name: str, schema_name: str):
    w = _make_client(user_token)
    tables = list(w.tables.list(catalog_name=catalog_name, schema_name=schema_name))
    return tables


@st.cache_data(ttl=300, show_spinner=False)
def get_table_lineage(user_token: str | None, table_full_name: str):
    w = _make_client(user_token)
    endpoint = "/api/2.0/lineage-tracking/table-lineage"
    payload = {
        "table_name": table_full_name,
        "include_entity_lineage": True,
    }

    def to_full_name(node: dict) -> str | None:
        ti = (node or {}).get("tableInfo")
        if not ti or ti.get("table_type") != "TABLE":
            return None
        return f"{ti['catalog_name']}.{ti['schema_name']}.{ti['name']}"

    try:
        resp = w.api_client.do(method="GET", path=endpoint, body=payload)
        upstream = sorted({to_full_name(n) for n in resp.get("upstreams", []) if to_full_name(n)})
        downstream = sorted({to_full_name(n) for n in resp.get("downstreams", []) if to_full_name(n)})
        return {"upstream": upstream, "downstream": downstream, "raw": resp, "endpoint": endpoint, "params": payload}
    except Exception as e:
        return {"upstream": [], "downstream": [], "error": str(e), "raw": None, "endpoint": endpoint, "params": payload}


@st.cache_data(ttl=60, show_spinner=False)
def get_table_info(user_token: str | None, full_name: str):
    w = _make_client(user_token)
    return w.tables.get(full_name=full_name)


@st.cache_data(ttl=300, show_spinner=False)
def get_genie_spaces(user_token: str | None):
    """利用可能なGenieスペース一覧をREST APIで取得"""
    w = _make_client(user_token)
    resp = w.api_client.do(method="GET", path="/api/2.0/genie/spaces")
    spaces = resp.get("spaces", [])
    return [
        (s["space_id"], s.get("title", s["space_id"]), s.get("description", ""))
        for s in spaces
    ]


# ─────────────────────────────────────────────
# サンプルデータ取得
# ─────────────────────────────────────────────

def get_sample_data(warehouse_id: str, table_name: str, limit: int = 100, exclude_binary: bool = True):
    """テーブルのサンプルデータをOBOクライアントで取得"""
    from databricks.sdk.service.sql import Disposition, Format
    import requests
    import pyarrow.ipc as ipc
    import io

    w = get_workspace_client()
    token = get_user_token()

    parts = table_name.split(".")
    escaped_name = ".".join([f"`{part}`" for part in parts])

    if exclude_binary:
        table_info = get_table_info(token, table_name)
        if table_info.columns:
            non_binary_cols = [
                f"`{col.name}`"
                for col in table_info.columns
                if "BINARY" not in (col.type_text or "").upper()
            ]
            columns_str = ", ".join(non_binary_cols) if non_binary_cols else "*"
            query = f"SELECT {columns_str} FROM {escaped_name} LIMIT {limit}"
        else:
            query = f"SELECT * FROM {escaped_name} LIMIT {limit}"
    else:
        query = f"SELECT * FROM {escaped_name} LIMIT {limit}"

    statement = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=query,
        wait_timeout="30s",
        disposition=Disposition.EXTERNAL_LINKS,
        format=Format.ARROW_STREAM
    )

    while statement.status.state in [StatementState.PENDING, StatementState.RUNNING]:
        time.sleep(0.5)
        statement = w.statement_execution.get_statement(statement.statement_id)

    if statement.status.state != StatementState.SUCCEEDED:
        raise Exception(f"クエリ失敗: {statement.status.error.message if statement.status.error else 'Unknown error'}")

    if statement.result and statement.result.external_links:
        all_tables = []
        for link in statement.result.external_links:
            response = requests.get(link.external_link)
            if response.status_code == 200:
                reader = ipc.open_stream(io.BytesIO(response.content))
                all_tables.append(reader.read_all())

        if all_tables:
            import pyarrow as pa
            combined = pa.concat_tables(all_tables)
            df = combined.to_pandas()
            for col in df.columns:
                if df[col].dtype == object:
                    def convert_value(x):
                        if x is None:
                            return None
                        if isinstance(x, bytes):
                            return base64.b64encode(x).decode('utf-8')
                        if isinstance(x, dict):
                            return str(x)
                        return x
                    df[col] = df[col].apply(convert_value)
            return df

    if statement.result and statement.result.data_array:
        columns = [col.name for col in statement.manifest.schema.columns]
        return pd.DataFrame(statement.result.data_array, columns=columns)

    return pd.DataFrame()


# ─────────────────────────────────────────────
# ページ1: Unity Catalog テーブル検索
# ─────────────────────────────────────────────

DEFAULT_CATALOG = "ytcy_azure_east2classic_stable"
DEFAULT_SCHEMA = "catalog_app"


def search_tables(tables, search_term: str):
    if not search_term:
        return tables
    search_lower = search_term.lower()
    return [t for t in tables if search_lower in t.name.lower()]


def page_catalog_explorer():
    """ページ1: Unity Catalog テーブル検索"""
    st.title("Unity Catalog テーブル検索")

    token = get_user_token()

    with st.sidebar:
        st.header("フィルター設定")
        try:
            warehouses = get_warehouses(token)
            if warehouses:
                selected_warehouse = st.selectbox(
                    "SQLウェアハウスを選択",
                    options=warehouses,
                    format_func=lambda x: x[1],
                    index=0,
                    key="uc_warehouse"
                )
                warehouse_id = selected_warehouse[0] if selected_warehouse else None
            else:
                st.warning("利用可能なSQLウェアハウスがありません")
                warehouse_id = None

            st.divider()

            catalogs = get_catalogs(token)
            default_cat_idx = catalogs.index(DEFAULT_CATALOG) if DEFAULT_CATALOG in catalogs else 0
            selected_catalog = st.selectbox(
                "カタログを選択",
                options=catalogs,
                index=default_cat_idx if catalogs else None
            )

            if selected_catalog:
                schemas = get_schemas(token, selected_catalog)
                default_schema_idx = schemas.index(DEFAULT_SCHEMA) if DEFAULT_SCHEMA in schemas else 0
                selected_schema = st.selectbox(
                    "スキーマを選択",
                    options=schemas,
                    index=default_schema_idx if schemas else None
                )
            else:
                selected_schema = None

        except Exception as e:
            st.error(f"接続エラー: {str(e)}")
            selected_catalog = None
            selected_schema = None
            warehouse_id = None

    if selected_catalog and selected_schema:
        search_term = st.text_input(
            "テーブル名で検索",
            placeholder="テーブル名を入力...",
            key="search_input"
        )

        try:
            tables = get_tables(token, selected_catalog, selected_schema)
            filtered_tables = search_tables(tables, search_term)

            st.subheader(f"テーブル一覧 ({len(filtered_tables)}件)")

            if filtered_tables:
                table_data = [
                    {
                        "テーブル名": t.name,
                        "タイプ": t.table_type.value if t.table_type else "UNKNOWN",
                        "コメント": t.comment or "",
                        "フルネーム": t.full_name
                    }
                    for t in filtered_tables
                ]

                df = pd.DataFrame(table_data)

                selected_table = st.selectbox(
                    "詳細を表示するテーブルを選択",
                    options=[t.full_name for t in filtered_tables],
                    format_func=lambda x: x.split(".")[-1]
                )

                st.dataframe(
                    df[["テーブル名", "タイプ", "コメント"]],
                    use_container_width=True,
                    hide_index=True
                )

                if selected_table:
                    st.divider()
                    st.subheader(f"テーブル詳細: {selected_table}")

                    table_info = get_table_info(token, selected_table)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**基本情報**")
                        st.write(f"- フルネーム: `{table_info.full_name}`")
                        st.write(f"- タイプ: {table_info.table_type.value if table_info.table_type else 'N/A'}")
                        st.write(f"- データソース形式: {table_info.data_source_format.value if table_info.data_source_format else 'N/A'}")
                        if table_info.storage_location:
                            st.write(f"- ストレージ: `{table_info.storage_location}`")

                    with col2:
                        st.markdown("**メタデータ**")
                        st.write(f"- 作成者: {table_info.created_by or 'N/A'}")
                        st.write(f"- 更新者: {table_info.updated_by or 'N/A'}")
                        if table_info.comment:
                            st.write(f"- コメント: {table_info.comment}")

                    if table_info.columns:
                        st.markdown("**カラム一覧**")
                        columns_data = [
                            {
                                "カラム名": col.name,
                                "データ型": col.type_text,
                                "Nullable": "Yes" if col.nullable else "No",
                                "コメント": col.comment or ""
                            }
                            for col in table_info.columns
                        ]
                        st.dataframe(pd.DataFrame(columns_data), use_container_width=True, hide_index=True)

                    st.divider()
                    st.markdown("**テーブルLineage**")
                    lineage = get_table_lineage(token, selected_table)
                    if lineage.get("error"):
                        st.error(f"Lineage取得に失敗しました: {lineage['error']}")
                    else:
                        col_u, col_d = st.columns(2)
                        with col_u:
                            st.markdown("**上流テーブル (Upstream)**")
                            if lineage["upstream"]:
                                st.dataframe(pd.DataFrame({"テーブル名": lineage["upstream"]}), use_container_width=True, hide_index=True)
                            else:
                                st.write("なし")
                        with col_d:
                            st.markdown("**下流テーブル (Downstream)**")
                            if lineage["downstream"]:
                                st.dataframe(pd.DataFrame({"テーブル名": lineage["downstream"]}), use_container_width=True, hide_index=True)
                            else:
                                st.write("なし")
                        if not lineage["upstream"] and not lineage["downstream"]:
                            with st.expander("Lineageレスポンスの詳細"):
                                st.write("- エンドポイント:", lineage.get("endpoint") or "不明")
                                st.write("- パラメータ:", lineage.get("params") or {})
                                st.write("- 生レスポンス:")
                                st.write(lineage.get("raw") or {})

                    st.divider()
                    st.markdown("**サンプルデータ**")

                    if warehouse_id:
                        sample_limit = st.slider("表示行数", min_value=10, max_value=500, value=10, step=10)

                        if st.button("サンプルデータを取得", type="primary"):
                            with st.spinner("データを取得中..."):
                                try:
                                    sample_df = get_sample_data(warehouse_id, selected_table, sample_limit)
                                    if not sample_df.empty:
                                        st.dataframe(sample_df, use_container_width=True, hide_index=True)
                                        st.caption(f"{len(sample_df)}行を表示")
                                    else:
                                        st.info("データがありません")
                                except Exception as e:
                                    st.error(f"サンプルデータの取得に失敗しました: {str(e)}")
                    else:
                        st.warning("サンプルデータを表示するにはSQLウェアハウスを選択してください")
            else:
                st.info("該当するテーブルが見つかりませんでした。")

        except Exception as e:
            st.error(f"テーブル情報の取得に失敗しました: {str(e)}")

    else:
        st.info("サイドバーからカタログとスキーマを選択してください。")


# ─────────────────────────────────────────────
# ページ2: Genie 問い合わせ
# ─────────────────────────────────────────────

def _poll_genie_message(w, space_id, conversation_id, message_id, initial_msg):
    """メッセージが完了するまでポーリングし、最終的なメッセージdictを返す"""
    terminal_statuses = {"COMPLETED", "FAILED", "CANCELLED"}
    msg = initial_msg
    for _ in range(120):
        status = msg.get("status", "")
        if status in terminal_statuses:
            break
        time.sleep(5)
        msg = w.api_client.do(
            method="GET",
            path=f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}",
        )
    msg["conversation_id"] = conversation_id
    return msg


def query_genie(space_id: str, question: str, conversation_id: str | None = None):
    """GenieにOBOクライアントで問い合わせを送信し、完了を待って結果を返す"""
    w = get_workspace_client()

    if conversation_id:
        resp = w.api_client.do(
            method="POST",
            path=f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages",
            body={"content": question},
        )
        msg_data = resp.get("message", resp)
        conv_id = msg_data.get("conversation_id", conversation_id)
    else:
        resp = w.api_client.do(
            method="POST",
            path=f"/api/2.0/genie/spaces/{space_id}/start-conversation",
            body={"content": question},
        )
        msg_data = resp["message"]
        conv_id = resp["conversation"]["id"]

    msg = _poll_genie_message(w, space_id, conv_id, msg_data["id"], msg_data)

    result = {
        "message_id": msg.get("id", ""),
        "conversation_id": msg.get("conversation_id", conv_id),
        "status": msg.get("status", "UNKNOWN"),
        "text_responses": [],
        "sql_query": None,
        "query_description": None,
        "attachment_id": None,
        "error": None,
    }

    error = msg.get("error")
    if error:
        result["error"] = error.get("message", str(error)) if isinstance(error, dict) else str(error)

    for att in msg.get("attachments", []) or []:
        text_data = att.get("text")
        if text_data and text_data.get("content"):
            result["text_responses"].append(text_data["content"])
        query_data = att.get("query")
        if query_data:
            result["sql_query"] = query_data.get("query")
            result["query_description"] = query_data.get("description")
            result["attachment_id"] = query_data.get("id") or att.get("attachment_id")

    return result


def get_genie_query_result(space_id: str, conversation_id: str, message_id: str, attachment_id: str | None = None):
    """GenieのクエリをOBOクライアントで取得しDataFrameとして返す"""
    w = get_workspace_client()

    if attachment_id:
        path = f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}/attachments/{attachment_id}/query-result"
    else:
        path = f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}/query-result"

    resp = w.api_client.do(method="GET", path=path)
    stmt = resp.get("statement_response", {})
    result_data = stmt.get("result", {})
    data_array = result_data.get("data_array", [])

    if data_array:
        manifest = stmt.get("manifest", {})
        schema = manifest.get("schema", {})
        col_list = schema.get("columns", [])
        columns = [c.get("name", f"col_{i}") for i, c in enumerate(col_list)]
        return pd.DataFrame(data_array, columns=columns)

    return pd.DataFrame()


def page_genie():
    """ページ2: Genie 問い合わせ"""
    st.title("Genie 問い合わせ")

    token = get_user_token()

    if "genie_history" not in st.session_state:
        st.session_state.genie_history = []
    if "genie_conversation_id" not in st.session_state:
        st.session_state.genie_conversation_id = None

    with st.sidebar:
        st.header("Genie 設定")
        try:
            spaces = get_genie_spaces(token)
            if spaces:
                selected_space = st.selectbox(
                    "Genieスペースを選択",
                    options=spaces,
                    format_func=lambda x: x[1],
                    key="genie_space"
                )
                space_id = selected_space[0] if selected_space else None
                if selected_space and selected_space[2]:
                    st.caption(selected_space[2])
            else:
                st.warning("利用可能なGenieスペースがありません")
                space_id = None

            st.divider()
            if st.button("会話をリセット", key="reset_conversation"):
                st.session_state.genie_history = []
                st.session_state.genie_conversation_id = None
                st.rerun()

        except Exception as e:
            st.error(f"Genieスペースの取得に失敗: {str(e)}")
            space_id = None

    if not space_id:
        st.info("サイドバーからGenieスペースを選択してください。")
        return

    for entry in st.session_state.genie_history:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            if entry.get("error"):
                st.error(entry["error"])
            else:
                for text in entry.get("text_responses", []):
                    st.write(text)
                if entry.get("sql_query"):
                    with st.expander("生成されたSQL"):
                        st.code(entry["sql_query"], language="sql")
                if entry.get("query_result") is not None and not entry["query_result"].empty:
                    st.dataframe(entry["query_result"], use_container_width=True, hide_index=True)
                    st.caption(f"{len(entry['query_result'])}行")
                elif entry.get("query_result_error"):
                    st.warning(f"クエリ結果の取得に失敗: {entry['query_result_error']}")

    question = st.chat_input("Genieに質問を入力...")

    if question:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Genieが回答を生成中..."):
                try:
                    result = query_genie(
                        space_id=space_id,
                        question=question,
                        conversation_id=st.session_state.genie_conversation_id,
                    )

                    st.session_state.genie_conversation_id = result["conversation_id"]

                    history_entry = {
                        "question": question,
                        "text_responses": result["text_responses"],
                        "sql_query": result["sql_query"],
                        "query_description": result["query_description"],
                        "error": result["error"],
                        "query_result": None,
                        "query_result_error": None,
                    }

                    if result["error"]:
                        st.error(result["error"])
                    else:
                        for text in result["text_responses"]:
                            st.write(text)

                        if result["sql_query"]:
                            with st.expander("生成されたSQL"):
                                st.code(result["sql_query"], language="sql")

                            try:
                                query_df = get_genie_query_result(
                                    space_id=space_id,
                                    conversation_id=result["conversation_id"],
                                    message_id=result["message_id"],
                                    attachment_id=result["attachment_id"],
                                )
                                if not query_df.empty:
                                    st.dataframe(query_df, use_container_width=True, hide_index=True)
                                    st.caption(f"{len(query_df)}行")
                                    history_entry["query_result"] = query_df
                                else:
                                    st.info("クエリ結果は空です")
                                    history_entry["query_result"] = pd.DataFrame()
                            except Exception as qe:
                                st.warning(f"クエリ結果の取得に失敗: {str(qe)}")
                                history_entry["query_result_error"] = str(qe)

                    st.session_state.genie_history.append(history_entry)

                except Exception as e:
                    error_msg = f"Genieへの問い合わせに失敗しました: {str(e)}"
                    st.error(error_msg)
                    st.session_state.genie_history.append({
                        "question": question,
                        "error": error_msg,
                        "text_responses": [],
                        "sql_query": None,
                        "query_result": None,
                        "query_result_error": None,
                    })


# ─────────────────────────────────────────────
# サイドバー共通: ユーザー情報・認証ステータス
# ─────────────────────────────────────────────

with st.sidebar:
    user_info = get_current_user_info()
    token = get_user_token()

    st.markdown(f"**👤 {user_info['display_name']}**")
    if user_info["email"] != user_info["display_name"]:
        st.caption(user_info["email"])

    if token:
        st.success("🔐 ユーザー認証 (OBO)")
    else:
        st.warning("⚠️ ローカル開発モード")

    st.divider()
    selected_page = st.radio(
        "ページ選択",
        ["📊 テーブル検索", "🤖 Genie 問い合わせ"],
        key="page_selector"
    )

# ─────────────────────────────────────────────
# ページ描画
# ─────────────────────────────────────────────

if selected_page == "📊 テーブル検索":
    page_catalog_explorer()
else:
    page_genie()

st.divider()
st.caption("Unity Catalog Explorer - Powered by Databricks Apps (OBO認証)")
