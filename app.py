import streamlit as st
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys
import os

# プロジェクトルートをパスに追加（Streamlit Cloud対策）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ページ設定
st.set_page_config(
    page_title="LPジェネレーター",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# メインコンテンツ
st.title("🚀 LPジェネレーター")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📋 製品管理
    - 新規製品作成
    - 製品一覧表示
    - 製品選択・編集
    """)

with col2:
    st.markdown("""
    ### 🎨 コンテンツ生成
    - モデル画像生成
    - ページ構成設計
    - 詳細コンテンツ作成
    """)

with col3:
    st.markdown("""
    ### ⚙️ 設定・出力
    - AI設定管理
    - プロンプト調整
    - 最終出力生成
    """)

st.markdown("---")

# クイックスタート
st.subheader("🚀 クイックスタート")

step_col1, step_col2, step_col3, step_col4 = st.columns(4)

with step_col1:
    if st.button("1️⃣ 製品作成", use_container_width=True):
        st.switch_page("pages/01_product_list.py")

with step_col2:
    if st.button("2️⃣ 情報入力", use_container_width=True):
        st.switch_page("pages/02_input.py")

with step_col3:
    if st.button("3️⃣ モデル設定", use_container_width=True):
        st.switch_page("pages/03_model.py")

with step_col4:
    if st.button("4️⃣ 構成設計", use_container_width=True):
        st.switch_page("pages/04_structure.py")

# 現在のプロジェクト状況
if 'current_product_id' in st.session_state:
    st.success(f"現在選択中: {st.session_state.get('current_product_name', 'プロジェクト')}")
else:
    st.info("製品を選択してください")

# フッター
st.markdown("---")
st.caption("LPジェネレーター v1.0 - AI駆動のランディングページ作成ツール")
# AIアシスタント
from modules.ai_sidebar import render_ai_sidebar
render_ai_sidebar()
