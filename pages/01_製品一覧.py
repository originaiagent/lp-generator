from modules.ai_sidebar import render_ai_sidebar
render_ai_sidebar()


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import os
# カスタムCSS読み込み
def load_css():
    css_file = "assets/style.css"
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

import os
import json
from datetime import datetime
from modules.data_store import DataStore

st.set_page_config(page_title="製品一覧", page_icon="📋", layout="wide")

st.title("📋 製品一覧")

# データストア初期化
data_store = DataStore()

# 新規製品作成セクション
st.subheader("➕ 新規製品作成")

with st.form("new_product_form"):
    product_name = st.text_input("製品名", placeholder="例: 新商品A")
    product_description = st.text_area("製品概要", placeholder="製品の簡単な説明を入力")
    submitted = st.form_submit_button("作成", width="stretch")
    
    if submitted and product_name:
        product = data_store.create_product(product_name)
        # 説明を追加
        if product_description:
            product['description'] = product_description
            data_store.update_product(product['id'], product)
        st.success(f"製品「{product_name}」を作成しました！")
        st.session_state['current_product_id'] = product['id']
        st.session_state['current_product_name'] = product_name
        st.rerun()

st.markdown("---")

# 既存製品一覧
st.subheader("📦 既存製品一覧")

products = [p for p in data_store.list_products() if p.get('id') and p.get('name')]

if products:
    for idx, product in enumerate(products):
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{product.get('name', '名称未設定')}**")
                desc = product.get('description') or ''
                if desc:
                    st.caption(desc[:100] + "..." if len(desc) > 100 else desc)
                else:
                    st.caption("説明なし")
            
            with col2:
                product_id = product.get('id', product.get('name', f'unknown_{idx}'))
                if st.button("選択", key=f"select_{idx}_{product_id}", width="stretch"):
                    st.session_state['current_product_id'] = product_id
                    st.session_state['current_product_name'] = product.get('name', '名称未設定')
                    st.success(f"「{product.get('name')}」を選択しました")
                    st.rerun()
            
            with col3:
                delete_key = f"delete_{idx}_{product_id}"
                confirm_key = f"confirm_delete_{product_id}"
                
                # 削除確認状態をチェック
                if st.session_state.get(confirm_key):
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("はい", key=f"yes_{delete_key}", type="primary"):
                            data_store.delete_product(product_id)
                            st.session_state[confirm_key] = False
                            st.warning(f"「{product.get('name', '名称未設定')}」を削除しました")
                            st.rerun()
                    with col_no:
                        if st.button("いいえ", key=f"no_{delete_key}"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                else:
                    if st.button("削除", key=delete_key, width="stretch"):
                        st.session_state[confirm_key] = True
                        st.rerun()
            
            st.markdown("---")
else:
    st.info("製品がまだありません。上のフォームから新規作成してください。")

# 現在選択中の製品
if 'current_product_id' in st.session_state:
    st.sidebar.success(f"選択中: {st.session_state.get('current_product_name', '不明')}")

