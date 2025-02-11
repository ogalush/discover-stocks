import streamlit as st
import sqlite3
from datetime import datetime, date
import re
import streamlit.components.v1 as components

# ======================
# URLパラメータから対象日を取得（yyyymmdd形式）
# ======================
query_params = st.query_params
if 'date' in query_params:
    date_param = query_params['date'].strip()  # 前後の空白を除去
    try:
        # yyyymmdd形式からdateオブジェクトに変換
        selected_date = datetime.strptime(date_param, "%Y%m%d").date()
    except ValueError:
        st.error("URLのdateパラメータが正しい形式ではありません。YYYYMMDD形式で指定してください。")
        selected_date = date.today()
else:
    selected_date = date.today()

selected_date_str = selected_date.strftime("%Y-%m-%d")  # "2025-02-09"形式

# ======================
# DB 初期化
# ======================
def get_connection():
    # SQLite の DB ファイル (survey.db) に接続（マルチスレッド対応のため check_same_thread=False）
    return sqlite3.connect("survey.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 銘柄発掘アンケートの回答保存テーブル（survey_date: 対象日、stock_code: 銘柄コード）
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
    # 投票結果を保存するテーブル（vote_date: 対象日、stock_code: 銘柄コード）
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS vote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# ======================
# 定数
# ======================
MAX_SETS = 7  # 銘柄発掘アンケートの入力セット数（後で変更可能）
MAX_VOTE_SELECTION = 10  # 集計ページでのチェックボックスの最大選択数（後で変更可能、default:10）

# ======================
# サイドバー：日付入力・ページ選択
# ======================
st.sidebar.header("【対象日選択】")
# URLで指定された日付を初期値に設定（ユーザーは変更可能）
date_input_value = st.sidebar.date_input("対象日を入力してください", value=selected_date)
selected_date = date_input_value
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.sidebar.write(f"選択中の日付: {selected_date_str}")

st.sidebar.markdown("---")
st.sidebar.title("ページ選択")
# ページ選択：銘柄発掘アンケート / 集計 / 投票ページ
page = st.sidebar.radio("メニュー", ("① 銘柄コード登録", "② 銘柄投票", "③ 投票結果確認"))

# ======================
# ページ：銘柄発掘アンケート
# ======================
def survey_page():
    st.title("① 銘柄コード登録")
    st.write(f"【対象日】{selected_date_str}")
    st.write("以下の入力欄に、半角英数字・大文字のみの銘柄コードを入力してください。")
    
    # 各入力セットを1行として作成：左側にテキスト入力＋「確定」ボタン、右側にTradingViewリンクを表示
    for i in range(MAX_SETS):
        row = st.columns([3, 3])
        with row[0]:
            inner_cols = st.columns([3, 1])
            code_input = inner_cols[0].text_input(f"銘柄コード {i+1}", key=f"code_{i}")
            if inner_cols[1].button("確定", key=f"confirm_button_{i}"):
                # 入力値の検証（半角英数字・大文字のみ）
                if re.match(r'^[A-Z0-9]+$', code_input):
                    st.session_state[f"confirmed_{i}"] = code_input
                    st.success(f"銘柄コード {code_input} を確定しました。リンクをクリックして確認してください。（アプリが開く場合は長押しでプレビュー画面で確認してください。）")
                else:
                    st.error("入力が不正です。半角英数字・大文字のみを使用してください。")
        with row[1]:
            if f"confirmed_{i}" in st.session_state:
                confirmed_code = st.session_state[f"confirmed_{i}"]
                url = f"https://www.tradingview.com/chart/?symbol={confirmed_code}"
                # HTMLのアンカー要素でtarget="_blank"を指定して新規タブで開くようにする
                st.markdown(
                    f'<a href="{url}" target="_blank" rel="noopener noreferrer">{confirmed_code}のチャートを表示する</a>',
                    unsafe_allow_html=True
                )
            else:
                st.write("")  # 空白で高さを合わせる
    
    st.markdown("---")
    if st.button("送信"):
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 各入力行の確定済み銘柄コードを対象日とともにDBへ保存
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

# ======================
# ページ：集計（投票用）
# ======================
def aggregation_page():
    st.title("② 銘柄投票")
    st.write(f"【対象日】{selected_date_str}")
    
    # surveyテーブルから、対象日の銘柄コードごとの件数を集計（多い順）
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT stock_code, COUNT(*) as survey_count FROM survey WHERE survey_date = ? GROUP BY stock_code ORDER BY survey_count DESC",
        (selected_date_str,)
    )
    results = c.fetchall()
    conn.close()
    
    if results:
        st.write("最新の集計結果（投票前のアンケート集計）")
        # カラムの幅比率を調整
        header_cols = st.columns([1, 1, 2, 1])
        header_cols[0].write("銘柄コード")
        header_cols[1].write("投票")  # チェックボックス用カラム
        header_cols[2].write("銘柄名")
        header_cols[3].write("アンケート票数")
        
        # 結果表示と同時にチェックボックスを配置
        for row in results:
            stock_code, survey_count = row
            url = f"https://www.tradingview.com/chart/?symbol={stock_code}"
            stock_name_link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{stock_code}</a>'
            cols = st.columns([1, 1, 2, 1])
            cols[0].write(stock_code)
            # チェックボックスを銘柄名の左に配置
            cols[1].checkbox("", key=f"checkbox_{stock_code}")
            cols[2].markdown(stock_name_link, unsafe_allow_html=True)
            cols[3].write(survey_count)
        
        st.markdown("---")
        # [投票] ボタン：チェックボックスで選択した行の銘柄コードを vote テーブルに保存する
        if st.button("投票"):
            # チェックされた銘柄コードを収集
            selected_codes = []
            for row in results:
                stock_code = row[0]
                if st.session_state.get(f"checkbox_{stock_code}"):
                    selected_codes.append(stock_code)
            if len(selected_codes) > MAX_VOTE_SELECTION:
                st.error(f"投票は最大{MAX_VOTE_SELECTION}件まで選択可能です。現在 {len(selected_codes)} 件選択されています。")
            elif len(selected_codes) == 0:
                st.warning("1件以上選択してください。")
            else:
                conn = get_connection()
                c = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for code in selected_codes:
                    c.execute(
                        "INSERT INTO vote (vote_date, stock_code, created_at) VALUES (?, ?, ?)",
                        (selected_date_str, code, now)
                    )
                conn.commit()
                conn.close()
                st.success("投票が保存されました。")
    else:
        st.write("対象日のデータはまだありません。")

    # 既存のExportボタン（アンケート結果のエクスポート用）
    st.markdown("---")
    if results:
        codes = [row[0] for row in results]
        file_content = "\n".join(codes)
        filename = selected_date.strftime("%Y%m%d") + "銘柄発掘.txt"
        st.download_button("銘柄コードExport", data=file_content, file_name=filename, mime="text/plain")

# ======================
# ページ：投票ページ
# ======================
def vote_page():
    st.title("③ 投票結果確認")
    st.write(f"【対象日】{selected_date_str}")
    
    # voteテーブルから、対象日の各銘柄の投票数を集計（多い順）
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT stock_code, COUNT(*) as vote_count FROM vote WHERE vote_date = ? GROUP BY stock_code ORDER BY vote_count DESC",
        (selected_date_str,)
    )
    results = c.fetchall()
    conn.close()
    
    if results:
        st.write("投票結果")
        header_cols = st.columns([1, 2, 1])
        header_cols[0].write("銘柄コード")
        header_cols[1].write("銘柄名")
        header_cols[2].write("投票数")
        for row in results:
            stock_code, vote_count = row
            url = f"https://www.tradingview.com/chart/?symbol={stock_code}"
            stock_name_link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{stock_code}</a>'
            cols = st.columns([1, 2, 1])
            cols[0].write(stock_code)
            cols[1].markdown(stock_name_link, unsafe_allow_html=True)
            cols[2].write(vote_count)
    else:
        st.write("対象日の投票結果はまだありません。")
    
    st.markdown("---")
    # [Export] ボタン：投票結果の銘柄コード一覧をTXTファイルとして出力
    if results:
        codes = [row[0] for row in results]
        file_content = "\n".join(codes)
        filename = selected_date.strftime("%Y%m%d") + "銘柄投票結果.txt"
        st.download_button("銘柄コードExport", data=file_content, file_name=filename, mime="text/plain")

# ======================
# ページ切り替え
# ======================
if page == "① 銘柄コード登録":
    survey_page()
elif page == "② 銘柄投票":
    aggregation_page()
elif page == "③ 投票結果確認":
    vote_page()
