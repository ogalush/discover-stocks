import streamlit as st
from utils.db import get_connection
import csv
from io import StringIO

def show(selected_date):
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    
    st.title("投票結果確認")
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
        # テキストファイルExportボタン
        codes = [row[0] for row in results]
        file_content = "\n".join(codes)
        filename = selected_date.strftime("%Y%m%d") + "投票結果.txt"
        st.download_button("銘柄コードExport", data=file_content, file_name=filename, mime="text/plain")
        
        # CSVファイルExportボタン
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['code', 'Number of votes', 'TradingView URL'])  # ヘッダー行
        # データ行にTradingView URLを追加
        csv_data = [(row[0], row[1], f'https://www.tradingview.com/chart/?symbol={row[0]}') for row in results]
        csv_writer.writerows(csv_data)
        
        csv_filename = selected_date.strftime("%Y%m%d") + "投票結果.csv"
        st.download_button(
            "投票結果CSV Export",
            data=csv_buffer.getvalue(),
            file_name=csv_filename,
            mime="text/csv"
        )
        
        st.markdown("---")

        # ワードクラウドの表示
        vote_dict = {row[0]: row[1] for row in results}
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            wc = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(vote_dict)
            plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis("off")
            st.pyplot(plt)
        except ImportError:
            st.error("wordcloudおよびmatplotlibライブラリが必要です。'pip install wordcloud matplotlib'でインストールしてください。")
        
        st.markdown("---")
        st.write("投票結果")
        header_cols = st.columns([0.5, 1, 2, 1])  # カラム幅を調整
        header_cols[0].write("No.")
        header_cols[1].write("銘柄コード")
        header_cols[2].write("銘柄名")
        header_cols[3].write("投票数")
        
        for index, row in enumerate(results, 1):  # enumerate関数で順番を付与
            stock_code, vote_count = row
            url = f"https://www.tradingview.com/chart/?symbol={stock_code}"
            stock_name_link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{stock_code}</a>'
            cols = st.columns([0.5, 1, 2, 1])  # カラム幅を調整
            cols[0].write(f"{index}")  # 順位を表示
            cols[1].write(stock_code)
            cols[2].markdown(stock_name_link, unsafe_allow_html=True)
            cols[3].write(vote_count)
    else:
        st.write("対象日の投票結果はまだありません。") 