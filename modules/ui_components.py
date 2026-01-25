"""共通UIコンポーネント"""
import streamlit as st
import os

def load_custom_css():
    """カスタムCSSを読み込む"""
    css_file = "assets/style.css"
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def section_header(title: str, icon: str = ""):
    """セクションヘッダー"""
    st.markdown(f"### {icon} {title}" if icon else f"### {title}")

def info_card(content: str):
    """情報カード（確認用）"""
    st.markdown(f"""
    <div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;">
        {content}
    </div>
    """, unsafe_allow_html=True)

def primary_button(label: str, key: str = None, use_container_width: bool = True):
    """目立つボタン（必須アクション用）"""
    return st.button(label, key=key, type="primary", width="stretch" if use_container_width else "content")

def secondary_button(label: str, key: str = None, use_container_width: bool = True):
    """控えめボタン（確認用）"""
    return st.button(label, key=key, type="secondary", width="stretch" if use_container_width else "content")
