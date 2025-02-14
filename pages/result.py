import streamlit as st
from utils.db import get_connection

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
        # Exportボタン
        codes = [row[0] for row in results]
        file_content = "\n".join(codes)
        filename = selected_date.strftime("%Y%m%d") + "投票結果.txt"
        st.download_button("銘柄コードExport", data=file_content, file_name=filename, mime="text/plain")
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