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

from modules.styles import apply_styles, page_header

# ページ設定
st.set_page_config(
    page_title="LP Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# スタイル適用
apply_styles()

# メインコンテンツ
page_header("LP Generator", "AI-Powered Landing Page Creator")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 製品管理
    - 新規製品作成
    - 製品一覧表示
    - 製品選択・編集
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    ### コンテンツ生成
    - モデル画像生成
    - ページ構成設計
    - 詳細コンテンツ作成
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    ### 設定・出力
    - AI設定管理
    - プロンプト調整
    - 最終出力生成
    """, unsafe_allow_html=True)

st.markdown("---")

# クイックスタート
st.subheader("クイックスタート")

step_col1, step_col2, step_col3, step_col4 = st.columns(4)

with step_col1:
    if st.button("1. 製品作成", use_container_width=True):
        st.switch_page("pages/01_製品一覧.py")

with step_col2:
    if st.button("2. 情報入力", use_container_width=True):
        st.switch_page("pages/02_情報入力.py")

with step_col3:
    if st.button("3. モデル設定", use_container_width=True):
        st.switch_page("pages/03_モデル設定.py")

with step_col4:
    if st.button("4. 構成設計", use_container_width=True):
        st.switch_page("pages/04_全体構成.py")

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
