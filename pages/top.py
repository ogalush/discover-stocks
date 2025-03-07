import streamlit as st
from datetime import date

def show(selected_date):
    st.title("銘柄投票システム")
    
    # 日付選択（URLパラメータの日付を初期値として使用）
    selected_date = st.date_input("対象日を選択してください", value=selected_date)
    date_str = selected_date.strftime("%Y%m%d")
    
    st.markdown("---")
    st.subheader("各ページへのリンク")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'<a href="./?page=survey&date={date_str}" target="_self">銘柄コード登録</a>', unsafe_allow_html=True)
        st.write("銘柄コードを登録します")
    
    with col2:
        st.markdown(f'<a href="./?page=vote&date={date_str}" target="_self">銘柄投票</a>', unsafe_allow_html=True)
        st.write("登録された銘柄に投票します")
    
    with col3:
        st.markdown(f'<a href="./?page=result&date={date_str}" target="_self">投票結果確認</a>', unsafe_allow_html=True)
        st.write("投票結果を確認します") 

    with col4:
        st.markdown(f'<a href="./?page=result_graph&date={date_str}" target="_self">投票結果の推移</a>', unsafe_allow_html=True)
        st.write("投票結果の推移を確認します") 