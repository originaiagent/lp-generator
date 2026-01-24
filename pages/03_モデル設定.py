import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

from modules.page_guard import require_product

# 製品選択チェック（製品一覧以外で必須）
require_product()


import base64
from modules.model_generator import ModelGenerator
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.settings_manager import SettingsManager

def render_model_page():
    st.title('👤 モデル設定')
    
    # AIサイドバー表示
    
    # 初期化
    settings_manager = SettingsManager()
    settings = settings_manager.get_settings()
    ai_provider = AIProvider(settings)
    prompt_manager = PromptManager()
    model_generator = ModelGenerator(ai_provider, prompt_manager)
    
    # セッション状態初期化
    if 'model_images' not in st.session_state:
        st.session_state.model_images = [None] * 5
    if 'model_prompts' not in st.session_state:
        st.session_state.model_prompts = [None] * 5
    
    # モデル数選択
    num_models = st.slider('モデル人数', 1, 5, 3)
    
    st.markdown("---")
    
    # 各モデルの設定
    tabs = st.tabs([f"モデル{i+1}" for i in range(num_models)])
    
    options = model_generator.get_attribute_options()
    
    for i, tab in enumerate(tabs):
        with tab:
            render_model_config(i, options, model_generator)
    
    st.markdown("---")
    
    # 一括生成ボタン
    if st.button('🎨 選択中のモデルを全て生成', type='primary', key='generate_all_btn'):
        generate_all_models(model_generator, num_models)
    
    # プロンプト確認セクション
    with st.expander("🔍 生成プロンプト確認（AIが最適化）", expanded=False):
        for i in range(num_models):
            if st.session_state.model_prompts[i]:
                st.markdown(f"**モデル{i+1}:**")
                st.code(st.session_state.model_prompts[i], language=None)
                st.markdown("---")

def render_model_config(index: int, options: dict, model_generator):
    """各モデルの設定UI"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"モデル{index+1} 属性設定")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            age = st.selectbox('年齢', options.get('age', []), key=f'model_age_{index}')
            ethnicity = st.selectbox('人種', options.get('ethnicity', []), key=f'model_eth_{index}')
        
        with c2:
            gender = st.selectbox('性別', options.get('gender', []), key=f'model_gender_{index}')
            atmosphere = st.selectbox('雰囲気', options.get('atmosphere', []), key=f'model_atm_{index}')
        
        with c3:
            clothing = st.selectbox('服装', options.get('clothing', []), key=f'model_cloth_{index}')
        
        # カスタム指示
        custom_prompt = st.text_area(
            '📝 追加指示・備考（AIがプロンプトに反映）',
            placeholder='例: 笑顔で親しみやすい、眼鏡をかけている、短髪、白い背景',
            key=f'model_custom_{index}',
            height=100
        )
        
        # 画像アップロード
        uploaded_file = st.file_uploader(
            '既存画像をアップロード（オプション）',
            type=['png', 'jpg', 'jpeg'],
            key=f'model_upload_{index}'
        )
        
        if uploaded_file:
            image_bytes = uploaded_file.read()
            st.session_state.model_images[index] = base64.b64encode(image_bytes).decode()
            st.success('画像をアップロードしました')
        
        # ボタン
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button('🎨 生成', key=f'model_generate_btn_{index}', type='primary'):
                generate_single_model(model_generator, index, {
                    'age': age,
                    'ethnicity': ethnicity,
                    'gender': gender,
                    'atmosphere': atmosphere,
                    'clothing': clothing
                }, custom_prompt)
        with bc2:
            if st.button('📋 プロンプト確認', key=f'model_preview_btn_{index}'):
                preview_prompt(model_generator, index, {
                    'age': age,
                    'ethnicity': ethnicity,
                    'gender': gender,
                    'atmosphere': atmosphere,
                    'clothing': clothing
                }, custom_prompt)
        with bc3:
            if st.button('🗑️ クリア', key=f'model_clear_btn_{index}'):
                st.session_state.model_images[index] = None
                st.session_state.model_prompts[index] = None
                st.rerun()
    
    with col2:
        st.subheader("プレビュー")
        if st.session_state.model_images[index]:
            try:
                image_bytes = base64.b64decode(st.session_state.model_images[index])
                st.image(image_bytes, use_container_width=True)
            except:
                st.info("画像を生成してください")
        else:
            st.info("画像を生成してください")
        
        if st.session_state.model_prompts[index]:
            with st.expander("プロンプト", expanded=False):
                st.code(st.session_state.model_prompts[index], language=None)

def preview_prompt(model_generator, index: int, attributes: dict, custom_notes: str):
    """プロンプトのみをプレビュー（AIで最適化）"""
    with st.spinner('AIがプロンプトを最適化中...'):
        try:
            # ModelGeneratorのgenerate_optimized_promptを使用（内部でPromptOptimizerを呼ぶ）
            prompt = model_generator.generate_optimized_prompt(attributes, custom_notes)
            st.session_state.model_prompts[index] = prompt
            st.success('プロンプト生成完了')
            st.rerun()
        except Exception as e:
            st.error(f'エラー: {str(e)}')

def generate_single_model(model_generator, index: int, attributes: dict, custom_notes: str):
    """単一モデル生成（AIでプロンプト最適化 + 画像生成）"""
    with st.spinner(f'モデル{index+1}を生成中... (AIプロンプト最適化 + 画像生成で1-2分)'):
        try:
            # AIでプロンプトを最適化
            prompt = model_generator.generate_optimized_prompt(attributes, custom_notes)
            st.session_state.model_prompts[index] = prompt
            
            # 画像生成
            from modules.image_generator import ImageGenerator
            image_gen = ImageGenerator()
            image_data = image_gen.generate(prompt)
            
            if image_data:
                st.session_state.model_images[index] = image_data
                st.success(f'モデル{index+1}を生成しました')
                st.rerun()
            else:
                st.error('画像生成に失敗しました')
        except Exception as e:
            st.error(f'エラー: {str(e)}')

def generate_all_models(model_generator, num_models: int):
    """全モデル一括生成"""
    progress = st.progress(0)
    
    for i in range(num_models):
        progress.progress((i) / num_models, f'モデル{i+1}を生成中...')
        
        attributes = {
            'age': st.session_state.get(f'model_age_{i}', '30代'),
            'ethnicity': st.session_state.get(f'model_eth_{i}', 'アジア系'),
            'gender': st.session_state.get(f'model_gender_{i}', '男性'),
            'atmosphere': st.session_state.get(f'model_atm_{i}', 'ナチュラル'),
            'clothing': st.session_state.get(f'model_cloth_{i}', 'ビジネス')
        }
        custom_notes = st.session_state.get(f'model_custom_{i}', '')
        
        # 既存画像がなければ生成
        if not st.session_state.model_images[i]:
            try:
                # AIでプロンプト最適化
                prompt = model_generator.generate_optimized_prompt(attributes, custom_notes)
                st.session_state.model_prompts[i] = prompt
                
                # 画像生成
                from modules.image_generator import ImageGenerator
                image_gen = ImageGenerator()
                image_data = image_gen.generate(prompt)
                
                if image_data:
                    st.session_state.model_images[i] = image_data
            except Exception as e:
                st.error(f'モデル{i+1}生成エラー: {str(e)}')
    
    progress.progress(1.0, '完了!')
    st.success('全モデルの生成が完了しました')
    st.rerun()

render_model_page()
