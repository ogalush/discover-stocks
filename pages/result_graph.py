#coding: utf_8
import streamlit as st
import datetime
import re
import plotly.express as px
import plotly.graph_objects as go
from utils.db import get_connection

# 取得・表示の最大日数 (DB負荷考慮)
MAX_DAYS=365
DEFAULT_DAYS=90

def show(selected_date):
    selected_date_str = selected_date.strftime("%Y-%m-%d")

    st.title("投票結果の推移")
    st.write(f"【投票日】{selected_date_str}")

    # REGEXPを使うための関数を定義
    def regexp(pattern, string):
        return bool(re.match(pattern, string))

    sql_template = """
        SELECT a.vote_date, a.stock_code || ' ' || COALESCE(b.stock_name, ''), count(a.stock_code) AS vote_count
         FROM vote AS a LEFT OUTER JOIN stock_master AS b ON a.stock_code = b.stock_code WHERE a.vote_date BETWEEN ? AND ? 
         AND a.stock_code REGEXP ?
         GROUP BY a.vote_date, a.stock_code;
    """

    # voteテーブルから、各投票回の投票数を取得する
    conn = get_connection()

    # REGEXP関数をSQLiteに登録
    conn.create_function('REGEXP', 2, regexp)

    # 日本株 (数字始まり)
    c = conn.cursor()
    c.execute(
        sql_template,
        ((selected_date - datetime.timedelta(days=MAX_DAYS)).strftime("%Y-%m-%d"),
         selected_date_str,
         "^[0-9]+"
        )
    )
    results_jp = c.fetchall()

    # 米国株 (英字始まり)
    c = conn.cursor()
    c.execute(
        sql_template,
        ((selected_date - datetime.timedelta(days=MAX_DAYS)).strftime("%Y-%m-%d"),
         selected_date_str,
         "^[A-Z]+"
        )
    )
    results_us = c.fetchall()

    # 投票数の合計と投票ボタンが押された回数を取得 (#13の追従)
    sql_template = """
        SELECT a.vote_date, COUNT(a.id) as total_votes, COUNT(DISTINCT a.created_at) as vote_sessions
         FROM vote AS a
         WHERE a.vote_date BETWEEN ? AND ?
         GROUP BY a.vote_date ORDER BY a.vote_date ASC;
    """
    c = conn.cursor()
    c.execute(
        sql_template,
        ((selected_date - datetime.timedelta(days=MAX_DAYS)).strftime("%Y-%m-%d"),
         selected_date_str
        )
    )
    results_vote_count = c.fetchall()
    conn.close()

    if results_jp or results_us:
        # グラフ表示
        try:
            import matplotlib
            import pandas as pd

            # 投票結果をキャッシュキーとして使用
            @st.cache_data(ttl=None)  # TTLなし（投票結果が変わるまでキャッシュ有効）

            # DataFrameに変換
            def convert_to_df(vote_results):
                df = pd.DataFrame(vote_results, columns=["日付", "銘柄", "投票数"])
                df["日付"] = pd.to_datetime(df["日付"])  # 日付をDatetime型に変換
                return df

            # スライダーで日付範囲を選択
            dates = pd.date_range(start = (selected_date - datetime.timedelta(days=MAX_DAYS)).strftime("%Y-%m-%d"), end = selected_date_str, freq = "D")
            default_start_date = max(dates.min(), pd.Timestamp(selected_date) - pd.Timedelta(days=DEFAULT_DAYS))

            # スライダー用意
            start_date, end_date = st.slider(
                "表示期間を選択してください:", 
                min_value=dates.min().to_pydatetime(),
                max_value=dates.max().to_pydatetime(),
                value=(default_start_date.to_pydatetime(), dates.max().to_pydatetime()),
                format="YYYY-MM-DD"
            )

            result_list = [
                {"result_key": "日本株", "result_value": results_jp},
                {"result_key": "米国株", "result_value": results_us}
            ]

            # 投票推移を線で結んだ折線グラフを準備する
            df = None
            for label, result in [("日本株", results_jp), ("米国株", results_us)]:
                st.subheader(label)
                df = convert_to_df(result)
                filtered_df = df[(df["日付"] >= pd.to_datetime(start_date)) & (df["日付"] <= pd.to_datetime(end_date))]
                filtered_df = filtered_df.sort_values("日付")

                # マルチセレクトで銘柄選択
                options = st.multiselect("銘柄を選択してください:", sorted(filtered_df["銘柄"].unique().tolist()), default=[])

                # 銘柄コードがない日付に NaN（欠損値）を入れる対応
                df_pivot = filtered_df.pivot(index="日付", columns="銘柄", values="投票数")
                df_selected = df_pivot.reindex()  # 存在しない場合は NaN になる
                if options:
                    df_selected = df_pivot.reindex(columns=options) # 存在しない場合は NaN になる

                # 日付毎に描画する
                fig = go.Figure()
                df_selected = df_selected.sort_values(by="日付")
                for stock_code in df_selected.columns:
                    fig.add_trace(go.Scatter(
                        x=df_selected.index,
                        y=df_selected[stock_code],
                        mode='lines+markers',
                        name=stock_code,
                        customdata=[[stock_code]] * len(df_selected),  # 銘柄名を customdata として渡す
                        hovertemplate='<extra>◆</extra>%{x|%Y-%m-%d} %{y} 票<br>%{customdata[0]}',
                        connectgaps=True  # 欠損があっても線を繋げる
                    ))

                # 標準だとフォントが小さいので少しだけ大きくする
                fontsize=dict(size=13)

                # X軸の形式を "YYYY-MM-DD" に設定
                fig.update_xaxes(tickformat="%Y-%m-%d", tickfont=fontsize)

                # Y軸の最小値を0に設定
                fig.update_yaxes(range=[0, df["投票数"].max()], tickfont=fontsize)

                fig.update_layout(
                    xaxis=dict(fixedrange=False),                   # スケール変更を許可
                    yaxis=dict(range=[0, None], fixedrange=False),  # Y軸最小値を0にしつつ、スケール変更を許可
                    xaxis_title="日付",
                    yaxis_title="投票数",
                    legend=dict(font=fontsize),     # 凡例のフォントサイズ
                    hoverlabel=dict(font=fontsize), # グラフの値のフォントサイズ
                    template="plotly_dark",
                    hovermode="closest",            # マウスオーバー時の凡例をその銘柄だけに絞る
                    dragmode="pan",                 # ドラッグ時に画面移動させる
                    width=1500,                     # グラフ本体(幅)
                    height=600,                     # グラフ本体(高さ)
                    showlegend=False                # 凡例を非表示化
                )
                st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True, "staticPlot": False})

            # 投票数の合計と投票ボタンが押された回数の表示 (#13の追従)
            # SQLの結果をDataFrameに変換
            df_vote = pd.DataFrame(results_vote_count, columns=["日付", "投票数の合計", "投票ボタンが押された回数"])
            df_vote["日付"] = pd.to_datetime(df_vote["日付"])  # 日付をDatetime型に変換

            # スライダーに従って日付フィルタ
            filtered_df_vote = df_vote[(df_vote["日付"] >= pd.to_datetime(start_date)) & (df_vote["日付"] <= pd.to_datetime(end_date))].copy()
            filtered_df_vote["日付"] = filtered_df_vote["日付"].dt.strftime("%m月%d日")

            # 投票数のグラフ
            st.subheader("投票数の合計の推移")
            st.line_chart(filtered_df_vote.set_index("日付")[["投票数の合計"]], use_container_width=True)

            # 投票セッション数のグラフ
            st.subheader("投票ボタンが押された回数の推移")
            st.line_chart(filtered_df_vote.set_index("日付")[["投票ボタンが押された回数"]], use_container_width=True)

        except ImportError:
            st.error("matplotlib, pandas ライブラリが必要です。'pip3 install matplotlib, pandas'でインストールしてください。")

    else:
        st.write("対象日の投票結果はまだありません。")