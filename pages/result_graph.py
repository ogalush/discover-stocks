#coding: utf_8
import streamlit as st
import re
from utils.db import get_connection

def show(selected_date):
    selected_month_str = selected_date.strftime("%Y-%m")

    st.title("投票結果の推移")
    st.write(f"【投票月】{selected_month_str}")

    # REGEXPを使うための関数を定義
    def regexp(pattern, string):
        return bool(re.match(pattern, string))

    # voteテーブルから、各投票回の投票数を取得する
    conn = get_connection()

    # REGEXP関数をSQLiteに登録
    conn.create_function('REGEXP', 2, regexp)

    # 日本株 (数字始まり)
    c = conn.cursor()
    c.execute(
        """
        SELECT vote_date,stock_code,count(stock_code) AS vote_count
         FROM vote WHERE vote_date LIKE ? AND stock_code REGEXP '^[0-9]+'
         GROUP BY vote_date, stock_code;
        """,
        (selected_month_str + '-%',)
    )
    results_jp = c.fetchall()

    # 米国株 (英字始まり)
    c = conn.cursor()
    c.execute(
        """
        SELECT vote_date,stock_code,count(stock_code) AS vote_count
         FROM vote WHERE vote_date LIKE ? AND stock_code REGEXP '^[A-Z]+'
         GROUP BY vote_date, stock_code;
        """,
        (selected_month_str + '-%',)
    )
    results_us = c.fetchall()

    conn.close()

    if results_jp or results_us:
        # グラフ表示
        try:
            import matplotlib
            import plotly.graph_objects as go
            import pandas as pd
            import datetime

            # 投票結果をキャッシュキーとして使用
            @st.cache_data(ttl=None)  # TTLなし（投票結果が変わるまでキャッシュ有効）
            def generate_votegraph(kinds, vote_results):

                # DataFrameに変換
                df = pd.DataFrame(vote_results, columns=["日付", "銘柄コード", "投票数"])
                df["日付"] = pd.to_datetime(df["日付"])  # 日付をDatetime型に変換

                # 投票推移を線で結んだ折線グラフを準備する
                # 銘柄コードごとにデータを整理
                fig = go.Figure()
                for stock_code in sorted(df["銘柄コード"].unique()):
                    stock_data = df[df["銘柄コード"] == stock_code]

                    # 日付毎に描画する
                    stock_data = stock_data.sort_values(by="日付")
                    fig.add_trace(go.Scatter(
                        x=stock_data["日付"],
                        y=stock_data["投票数"],
                        mode='lines+markers',  # 線とマーカーを両方表示
                        name=f'{stock_code}',
                        hovertemplate='%{y}'
                    ))

                # 標準だとフォントが小さいので少しだけ大きくする
                fontsize=dict(size=16)

                # X軸の形式を "YYYY-MM-DD" に設定
                fig.update_xaxes(tickformat="%Y-%m-%d", tickfont=fontsize)

                # Y軸の最小値を0に設定
                fig.update_yaxes(range=[0, df["投票数"].max() + 5], tickfont=fontsize)  # 上限は少し余裕を持たせる

                # グラフのレイアウト設定
                fig.update_layout(
                    title= kinds,
                    xaxis_title="日付",
                    yaxis_title="投票数",
                    legend_title="銘柄コード",
                    template="plotly_dark",
                    legend=dict(font=fontsize),     # 凡例のフォントサイズ
                    hoverlabel=dict(font=fontsize), # グラフの値のフォントサイズ
                    width=1000,                     # グラフ本体(幅)
                    height=600                      # グラフ本体(高さ)
                )

                return fig

            # 投票データを文字列化してキャッシュキーとして使用
            vote_data_str = str(results_jp + results_us)

            # 日本株描画
            fig = generate_votegraph('日本株', results_jp)
            st.plotly_chart(fig)

            # 米国株描画
            fig = generate_votegraph('米国株', results_us)
            st.plotly_chart(fig)

        except ImportError:
            st.error("matplotlib, plotly, pandas ライブラリが必要です。'pip3 install matplotlib, plotly, pandas'でインストールしてください。")

    else:
        st.write("対象日の投票結果はまだありません。") 
