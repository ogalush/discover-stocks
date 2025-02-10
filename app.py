import streamlit as st
import sqlite3
from datetime import datetime, date
import re
import streamlit.components.v1 as components

# ---------- クエリパラメータから対象日を取得 ----------
query_params = st.query_params
if 'date' in query_params:
    date_raw = query_params['date']
    date_param = date_raw.strip()  # 前後の余分な空白を除去
    try:
        # yyyymmdd 形式から date オブジェクトに変換
        selected_date = datetime.strptime(date_param, "%Y%m%d").date()
    except ValueError:
        st.error("URLのdateパラメータが正しい形式ではありません。YYYYMMDD形式で指定してください。")
        selected_date = date.today()
else:
    selected_date = date.today()

# 選択した日付を文字列（例："2025-02-09"）に変換
selected_date_str = selected_date.strftime("%Y-%m-%d")

# ---------- DB 初期化 ----------
def get_connection():
    # SQLite の DB ファイル（survey.db）に接続（マルチスレッド対応のため check_same_thread=False）
    return sqlite3.connect("survey.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 銘柄発掘アンケートの回答を保存するテーブルに、survey_date（対象日）を追加
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS survey (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# ---------- 定数 ----------
# 入力セットの最大数（デフォルト 6、後で変更可能）
MAX_SETS = 6

# ---------- サイドバー：日付入力・ページ選択 ----------
st.sidebar.header("【対象日選択】")
# URLで指定された日付を初期値に設定（ユーザーが変更可能）
date_input_value = st.sidebar.date_input("対象日を入力してください", value=selected_date)
# ユーザーがウィジェットで変更した場合、その値を採用
selected_date = date_input_value
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.sidebar.write(f"選択中の日付: {selected_date_str}")

st.sidebar.markdown("---")
st.sidebar.title("ページ選択")
page = st.sidebar.radio("メニュー", ("銘柄発掘アンケート", "集計"))

# ---------- ページ：銘柄発掘アンケート ----------
def survey_page():
    st.title("銘柄発掘アンケート")
    st.write(f"【対象日】{selected_date_str}")
    st.write("以下の入力欄に、半角英数字・大文字のみの銘柄コードを入力してください。")
    
    # 各入力セットを1行として作成：左側にテキスト入力＋「確定」ボタン、右側にTradingViewリンクを表示
    for i in range(MAX_SETS):
        # 行全体を左右2カラムに分割（左：入力、右：リンク）
        row = st.columns([3, 3])
        
        # 左側：テキスト入力と確定ボタンを横並びに配置
        with row[0]:
            inner_cols = st.columns([3, 1])
            code_input = inner_cols[0].text_input(f"銘柄コード {i+1}", key=f"code_{i}")
            if inner_cols[1].button("確定", key=f"confirm_button_{i}"):
                # 入力値の検証（半角英数字・大文字のみ）
                if re.match(r'^[A-Z0-9]+$', code_input):
                    st.session_state[f"confirmed_{i}"] = code_input
                    st.success(f"銘柄コード {code_input} を確定しました。右側の『{code_input}のチャートを表示する』リンクをクリックして、銘柄コードが正しいか確認してください。")
                else:
                    st.error("入力が不正です。半角英数字・大文字のみを使用してください。")
        
        # 右側：該当行のTradingViewリンクを表示（未確定の場合は空白のプレースホルダー）
        with row[1]:
            if f"confirmed_{i}" in st.session_state:
                confirmed_code = st.session_state[f"confirmed_{i}"]
                url = f"https://www.tradingview.com/chart/?symbol={confirmed_code}"
                st.markdown(f"[{confirmed_code}のチャートを表示する]({url})", unsafe_allow_html=True)
            else:
                st.write("")  # 空白で高さを合わせる

    st.markdown("---")
    if st.button("Send"):
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 各入力行の確定された銘柄コードを対象日とともにDBへ保存
        for i in range(MAX_SETS):
            if f"confirmed_{i}" in st.session_state:
                code = st.session_state[f"confirmed_{i}"]
                c.execute(
                    "INSERT INTO survey (survey_date, stock_code, created_at) VALUES (?, ?, ?)",
                    (selected_date_str, code, now)
                )
        conn.commit()
        conn.close()
        st.success("入力内容をデータベースに保存しました。")

# ---------- ページ：集計 ----------
def aggregation_page():
    st.title("銘柄発掘アンケート 集計")
    st.write(f"【対象日】{selected_date_str}")
    
    # DBから、対象日の銘柄コードごとに投票数をカウントして取得（多い順にソート）
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT stock_code, COUNT(*) as vote_count FROM survey WHERE survey_date = ? GROUP BY stock_code ORDER BY vote_count DESC",
        (selected_date_str,)
    )
    results = c.fetchall()
    conn.close()

    if results:
        st.write("最新の集計結果")
        # ヘッダー行の表示
        header_cols = st.columns([1, 2, 1, 1])
        header_cols[0].write("銘柄コード")
        header_cols[1].write("銘柄名")
        header_cols[2].write("投票数")
        header_cols[3].write("選択")
        
        # 各銘柄の情報を表示（銘柄名は TradingView へのリンクとして設定）
        for row in results:
            stock_code, vote_count = row
            url = f"https://www.tradingview.com/chart/?symbol={stock_code}"
            stock_name_link = f"[{stock_code}]({url})"
            cols = st.columns([1, 2, 1, 1])
            cols[0].write(stock_code)
            cols[1].markdown(stock_name_link, unsafe_allow_html=True)
            cols[2].write(vote_count)
            cols[3].checkbox("Good", key=f"checkbox_{stock_code}")
    else:
        st.write("対象日のデータはまだありません。")
    
    st.markdown("---")
    # Export ボタンで、対象日の銘柄コード一覧を TXT ファイルとして出力
    codes = [row[0] for row in results]
    file_content = "\n".join(codes)
    filename = selected_date.strftime("%Y%m%d") + "銘柄発掘.txt"
    st.download_button("Export", data=file_content, file_name=filename, mime="text/plain")

# ---------- ページ切り替え ----------
if page == "銘柄発掘アンケート":
    survey_page()
elif page == "集計":
    aggregation_page()
