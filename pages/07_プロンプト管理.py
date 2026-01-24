from modules.ai_sidebar import render_ai_sidebar
render_ai_sidebar()


import streamlit as st
import os
# カスタムCSS読み込み
def load_css():
    css_file = "assets/style.css"
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

from modules.prompt_manager import PromptManager

st.set_page_config(page_title="プロンプト管理", page_icon="💬", layout="wide")
st.title('💬 プロンプト管理')
st.caption('各タスクで使用されるAIプロンプトを確認・編集できます')

prompt_manager = PromptManager()

col_list, col_edit = st.columns([1, 2])

with col_list:
    st.subheader("📋 タスク一覧")
    prompts = prompt_manager.list_prompts()
    
    if 'selected_prompt_id' not in st.session_state:
        st.session_state.selected_prompt_id = prompts[0] if prompts else None
    
    for p_id in prompts:
        is_selected = st.session_state.selected_prompt_id == p_id
        btn_type = "primary" if is_selected else "secondary"
        if st.button(f"{'✅ ' if is_selected else ''}{p_id}", key=f"btn_{p_id}", use_container_width=True, type=btn_type):
            st.session_state.selected_prompt_id = p_id
            st.rerun()
        st.markdown("---")

with col_edit:
    if st.session_state.selected_prompt_id:
        p_id = st.session_state.selected_prompt_id
        template = prompt_manager.get_prompt(p_id)
        
        st.subheader(f"✏️ {p_id}")
        
        new_template = st.text_area("テンプレート", value=template, height=300, key=f"tmpl_{p_id}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存", type="primary", use_container_width=True):
                prompt_manager.update_prompt(p_id, new_template)
                st.success("保存しました！")
                st.rerun()
        with col2:
            if st.button("🔄 デフォルトに戻す", use_container_width=True):
                prompt_manager.reset_to_default(p_id)
                st.success("リセットしました！")
                st.rerun()

