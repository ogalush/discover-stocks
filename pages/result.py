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
        """
        SELECT v.stock_code, COUNT(*) as vote_count, m.stock_name
        FROM vote v
        LEFT JOIN stock_master m ON v.stock_code = m.stock_code
        WHERE v.vote_date = ?
        GROUP BY v.stock_code
        ORDER BY vote_count DESC
        """,
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
        # ヘッダー行をSJISで書き込み
        headers = ['銘柄コード', '投票数', '銘柄名', 'TradingView URL']
        csv_data = [(row[0], row[1], row[2] or row[0], f'https://www.tradingview.com/chart/?symbol={row[0]}') for row in results]
        
        # SJISでエンコードしたバイトデータを作成
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(csv_data)
        csv_str = output.getvalue()
        csv_bytes = csv_str.encode('shift-jis', errors='replace')
        
        csv_filename = selected_date.strftime("%Y%m%d") + "投票結果.csv"
        st.download_button(
            "投票結果CSV Export",
            data=csv_bytes,
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
        header_cols = st.columns([0.5, 1, 2, 1])
        header_cols[0].write("No.")
        header_cols[1].write("銘柄コード")
        header_cols[2].write("銘柄名")
        header_cols[3].write("投票数")
        
        for index, row in enumerate(results, 1):
            stock_code, vote_count, stock_name = row
            display_name = stock_name or stock_code  # stock_nameがNoneの場合はstock_codeを使用
            url = f"https://www.tradingview.com/chart/?symbol={stock_code}"
            stock_name_link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{display_name}</a>'
            
            cols = st.columns([0.5, 1, 2, 1])
            cols[0].write(f"{index}")
            cols[1].write(stock_code)
            cols[2].markdown(stock_name_link, unsafe_allow_html=True)
            cols[3].write(vote_count)
    else:
        st.write("対象日の投票結果はまだありません。") 