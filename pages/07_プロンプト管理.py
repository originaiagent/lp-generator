from modules.ai_sidebar import render_ai_sidebar
from modules.styles import apply_styles, page_header
render_ai_sidebar()


import streamlit as st
import os
# スタイル適用
apply_styles()

from modules.prompt_manager import PromptManager

st.set_page_config(page_title="Prompt Management", layout="wide")
page_header("Prompt Management", "各タスクで使用されるAIプロンプトを確認・編集できます")

prompt_manager = PromptManager()

col_list, col_edit = st.columns([1, 2])

with col_list:
    st.subheader("タスク一覧")
    prompts_data = prompt_manager.list_prompts_with_names()
    
    # IDリストを作成
    prompt_ids = [p["id"] for p in prompts_data]
    
    if 'selected_prompt_id' not in st.session_state:
        st.session_state.selected_prompt_id = prompt_ids[0] if prompt_ids else None
    
    for p_data in prompts_data:
        p_id = p_data["id"]
        p_name = p_data["name"]
        
        is_selected = st.session_state.selected_prompt_id == p_id
        btn_type = "primary" if is_selected else "secondary"
        
        if st.button(p_name, key=f"btn_{p_id}", use_container_width=True, type=btn_type):
            st.session_state.selected_prompt_id = p_id
            st.rerun()
        st.markdown("---")

with col_edit:
    if st.session_state.selected_prompt_id:
        p_id = st.session_state.selected_prompt_id
        template = prompt_manager.get_prompt(p_id)
        p_data = prompt_manager.get_prompt_data(p_id)
        p_name = p_data.get("name", p_id)
        p_desc = p_data.get("description", "")
        
        st.subheader(p_name)
        if p_desc:
            st.caption(p_desc)
        if p_id != p_name:
            st.caption(f"ID: {p_id}")
        
        new_template = st.text_area("テンプレート", value=template, height=300, key=f"tmpl_{p_id}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("保存", type="primary", use_container_width=True):
                prompt_manager.update_prompt(p_id, new_template)
                st.success("保存しました！")
                st.rerun()
        with col2:
            if st.button("デフォルトに戻す", use_container_width=True):
                prompt_manager.reset_to_default(p_id)
                st.success("リセットしました！")
                st.rerun()

