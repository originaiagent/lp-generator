import os
import streamlit as st

# ページ設定
st.set_page_config(
    page_title="LPジェネレーター",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS読み込み
css_file = "assets/style.css"
if os.path.exists(css_file):
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ページ定義（日本語名）
pages = {
    "メイン": [
        st.Page("pages/01_製品一覧.py", title="製品一覧", icon="📋"),
        st.Page("pages/02_情報入力.py", title="情報入力", icon="📝"),
        st.Page("pages/03_モデル設定.py", title="モデル設定", icon="🎨"),
        st.Page("pages/04_全体構成.py", title="全体構成", icon="🏗️"),
        st.Page("pages/05_ページ詳細.py", title="ページ詳細", icon="📄"),
        st.Page("pages/06_出力.py", title="出力", icon="📤"),
    ],
    "設定": [
        st.Page("pages/07_プロンプト管理.py", title="プロンプト管理", icon="💬"),
        st.Page("pages/08_設定.py", title="設定", icon="⚙️"),
    ]
}

# ナビゲーション設定
pg = st.navigation(pages)
pg.run()
