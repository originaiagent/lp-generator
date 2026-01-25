import streamlit as st

def require_product():
    """製品選択を必須にするガード"""
    if 'current_product_id' not in st.session_state:
        st.warning("⚠️ 先に製品を選択してください")
        st.info("「製品一覧」から製品を選択または新規作成してください")
        if st.button("製品一覧へ移動", width="stretch"):
            st.switch_page("pages/01_製品一覧.py")
        st.stop()
    return st.session_state['current_product_id']
