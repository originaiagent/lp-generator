import streamlit as st
from modules.styles import apply_styles, page_header
from modules.ai_sidebar import render_ai_sidebar
import os
from modules.prompt_manager import PromptManager

# ページ設定
st.set_page_config(page_title="Prompt Management", layout="wide")

# スタイル適用
apply_styles()

# AIサイドバー表示
render_ai_sidebar()

# カスタムCSS: テキストエリアのサイズ調整のみ残す
st.markdown("""
<style>
    .stTextArea textarea {
        min-height: 500px;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

page_header("Prompt Management", "各タスクで使用されるAIプロンプトを確認・編集できます")

prompt_manager = PromptManager()

# プロンプト一覧を取得
prompts_data = prompt_manager.list_prompts_with_names()
prompt_ids = [p["id"] for p in prompts_data]
prompt_names = [p["name"] for p in prompts_data]

if not prompts_data:
    st.warning("プロンプトが見つかりません。")
    st.stop()

# セッション状態の初期化
if 'selected_prompt_id' not in st.session_state:
    st.session_state.selected_prompt_id = prompt_ids[0]

# 現在選択されているIDのインデックスを取得
try:
    current_index = prompt_ids.index(st.session_state.selected_prompt_id)
except ValueError:
    current_index = 0

# プロンプト選択（selectbox）
selected_index = st.selectbox(
    "プロンプトを選択",
    range(len(prompt_names)),
    format_func=lambda i: f"{prompt_names[i]} ({prompt_ids[i]})",
    index=current_index
)

# 選択されたIDを更新
selected_prompt_id = prompt_ids[selected_index]
if selected_prompt_id != st.session_state.selected_prompt_id:
    st.session_state.selected_prompt_id = selected_prompt_id
    st.rerun()

st.markdown("---")

# エディタエリア
p_id = st.session_state.selected_prompt_id
template = prompt_manager.get_prompt(p_id)
p_data = prompt_manager.get_prompt_data(p_id)
p_name = p_data.get("name", p_id)
p_desc = p_data.get("description", "")

st.subheader(f"編集: {p_name}")
if p_desc:
    st.info(p_desc)
st.caption(f"プロンプトID: {p_id}")

new_template = st.text_area("テンプレート", value=template, key=f"tmpl_{p_id}")

col1, col2, _ = st.columns([1, 1, 2])
with col1:
    if st.button("保存する", type="primary", use_container_width=True):
        if prompt_manager.update_prompt(p_id, new_template):
            st.success("保存しました！")
            st.rerun()
        else:
            st.error("保存に失敗しました。")

with col2:
    if st.button("デフォルトに戻す", use_container_width=True):
        if prompt_manager.reset_to_default(p_id):
            st.success("デフォルト設定に戻しました。")
            st.rerun()
        else:
            st.error("リセットに失敗しました。")

