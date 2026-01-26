from modules.ai_sidebar import render_ai_sidebar
from modules.styles import apply_styles, page_header
render_ai_sidebar()


import streamlit as st
import os
import time
# スタイル適用
apply_styles()

from modules.page_guard import require_product

# 製品選択チェック（製品一覧以外で必須）
require_product()


import base64
from modules.model_generator import ModelGenerator
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.settings_manager import SettingsManager
from modules.data_store import DataStore

    page_header("Model Settings", "AIによるモデル画像の生成と設定")
    
    # AIサイドバー表示
    
    # 初期化
    settings_manager = SettingsManager()
    settings = settings_manager.get_settings()
    ai_provider = AIProvider(settings)
    prompt_manager = PromptManager()
    model_generator = ModelGenerator(ai_provider, prompt_manager)
    data_store = DataStore()
    
    # 製品情報のロード
    product_id = st.session_state.get('current_product_id')
    product = data_store.get_product(product_id)
    if not product:
        st.error("製品データが見つかりません")
        st.stop()
        
    # セッション状態初期化（製品データがあればそこから復元）
    if 'model_images' not in st.session_state or all(x is None for x in st.session_state.model_images):
        saved_images = product.get('model_images', [])
        # 5枠確保
        if len(saved_images) < 5:
            saved_images.extend([None] * (5 - len(saved_images)))
        st.session_state.model_images = saved_images

    if 'model_prompts' not in st.session_state or all(x is None for x in st.session_state.model_prompts):
        saved_prompts = product.get('model_prompts', [])
        if len(saved_prompts) < 5:
            saved_prompts.extend([None] * (5 - len(saved_prompts)))
        st.session_state.model_prompts = saved_prompts
    
    # モデル数選択
    num_models = st.slider('モデル人数', 1, 5, 3)
    
    st.markdown("---")
    
    # 各モデルの設定
    tabs = st.tabs([f"モデル{i+1}" for i in range(num_models)])
    
    options = model_generator.get_attribute_options()
    
    for i, tab in enumerate(tabs):
        with tab:
            render_model_config(i, options, model_generator, data_store, product_id)
    
    st.markdown("---")
    
    # 一括生成ボタン
    if st.button('選択中のモデルを全て生成', type='primary', key='generate_all_btn', use_container_width=True):
        generate_all_models(model_generator, num_models, data_store, product_id)
    
    # プロンプト確認セクション
    with st.expander("🔍 生成プロンプト確認（AIが最適化）", expanded=False):
        for i in range(num_models):
            if st.session_state.model_prompts[i]:
                st.markdown(f"**モデル{i+1}:**")
                st.code(st.session_state.model_prompts[i], language=None)
                st.markdown("---")

def render_model_config(index: int, options: dict, model_generator, data_store, product_id):
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
        
        custom_prompt = st.text_area(
            '追加指示・備考（AIがプロンプトに反映）',
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
            # 手動アップロード処理
            try:
                file_bytes = uploaded_file.read()
                ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'png'
                import uuid
                safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                filename = f"{product_id}/models/{safe_name}"
                if data_store.use_supabase:
                    url = data_store.upload_image(file_bytes, filename)
                    if url:
                        update_product_model(index, url, None, data_store, product_id)
                        st.success('画像をアップロード・保存しました')
                        st.rerun()
                else:
                    # ローカルのみ (Base64で一時保持...しかし永続化のためにはファイルに保存すべきだが、今回はSupabase優先)
                    # フォールバック: セッションステートのみ
                     st.session_state.model_images[index] = base64.b64encode(file_bytes).decode()
                     st.warning("Supabase未接続のため、画像は一時的な保存となります。")
            except Exception as e:
                st.error(f"アップロードエラー: {e}")
        
        # ボタン
        bc1, bc2, bc3 = st.columns(3)
            if st.button('生成', key=f'model_generate_btn_{index}', type='primary', use_container_width=True):
                generate_single_model(model_generator, index, {
                    'age': age,
                    'ethnicity': ethnicity,
                    'gender': gender,
                    'atmosphere': atmosphere,
                    'clothing': clothing
                }, custom_prompt, data_store, product_id)
        with bc2:
            if st.button('プロンプト確認', key=f'model_preview_btn_{index}', use_container_width=True):
                preview_prompt(model_generator, index, {
                    'age': age,
                    'ethnicity': ethnicity,
                    'gender': gender,
                    'atmosphere': atmosphere,
                    'clothing': clothing
                }, custom_prompt)
        with bc3:
            if st.button('クリア', key=f'model_clear_btn_{index}', use_container_width=True):
                img_url = st.session_state.model_images[index]
                if img_url and isinstance(img_url, str) and img_url.startswith("http"):
                    data_store.delete_storage_file(img_url)
                st.session_state.model_images[index] = None
                st.session_state.model_prompts[index] = None
                # DBからも削除（None更新）
                update_product_model(index, None, None, data_store, product_id)
                st.rerun()
    
    with col2:
        st.subheader("プレビュー")
        img_data = st.session_state.model_images[index]
        if img_data:
            try:
                if img_data.startswith("http"):
                    st.image(img_data, width="stretch")
                else:
                    # Base64 legacy support
                    image_bytes = base64.b64decode(img_data)
                    st.image(image_bytes, width="stretch")
            except:
                st.info("画像の読み込みに失敗しました")
        else:
            st.info("画像を生成してください")
        
        if st.session_state.model_prompts[index]:
            with st.expander("プロンプト", expanded=False):
                st.code(st.session_state.model_prompts[index], language=None)

def update_product_model(index, image_url, prompt, data_store, product_id):
    """製品データのモデル情報を更新して保存"""
    product = data_store.get_product(product_id)
    if not product:
        return
    
    if 'model_images' not in product:
        product['model_images'] = [None] * 5
    if 'model_prompts' not in product:
        product['model_prompts'] = [None] * 5
    
    # 配列サイズ確保
    while len(product['model_images']) <= index:
        product['model_images'].append(None)
    while len(product['model_prompts']) <= index:
        product['model_prompts'].append(None)
        
    if image_url is not None: # Noneを渡した場合はクリア
        product['model_images'][index] = image_url
    else:
        product['model_images'][index] = None
        
    if prompt is not None:
        product['model_prompts'][index] = prompt
    elif image_url is None: # 画像クリア時はプロンプトもクリアするか? 引数依存
        pass

    data_store.update_product(product_id, product)
    
    # セッションステートも同期
    st.session_state.model_images[index] = product['model_images'][index]
    if prompt:
        st.session_state.model_prompts[index] = prompt


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

def generate_single_model(model_generator, index: int, attributes: dict, custom_notes: str, data_store, product_id):
    """単一モデル生成（AIでプロンプト最適化 + 画像生成 + 保存）"""
    with st.spinner(f'モデル{index+1}を生成中... (AIプロンプト最適化 + 画像生成で1-2分)'):
        try:
            # AIでプロンプトを最適化
            prompt = model_generator.generate_optimized_prompt(attributes, custom_notes)
            st.session_state.model_prompts[index] = prompt
            
            # 画像生成
            from modules.image_generator import ImageGenerator
            image_gen = ImageGenerator()
            image_base64 = image_gen.generate(prompt)
            
            if image_base64:
                # クラウドに保存
                if data_store.use_supabase:
                    try:
                        img_bytes = base64.b64decode(image_base64)
                        filename = f"{product_id}/models/model_{index}_{int(time.time())}.png"
                        url = data_store.upload_image(img_bytes, filename)
                        if url:
                            update_product_model(index, url, prompt, data_store, product_id)
                            st.success(f'モデル{index+1}を生成・保存しました')
                            st.rerun()
                            return
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
                
                # フォールバック（Base64のままセッションへ）
                st.session_state.model_images[index] = image_base64
                st.warning("生成されましたが、クラウドへの保存に失敗しました。")
                st.rerun()
            else:
                st.error('画像生成に失敗しました')
        except Exception as e:
            st.error(f'エラー: {str(e)}')

def generate_all_models(model_generator, num_models: int, data_store, product_id):
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
                # プロンプト
                prompt = model_generator.generate_optimized_prompt(attributes, custom_notes)
                
                # 生成
                from modules.image_generator import ImageGenerator
                image_gen = ImageGenerator()
                image_base64 = image_gen.generate(prompt)
                
                if image_base64:
                    # 保存
                    if data_store.use_supabase:
                        try:
                            img_bytes = base64.b64decode(image_base64)
                            filename = f"{product_id}/models/model_{i}_{int(time.time())}.png"
                            url = data_store.upload_image(img_bytes, filename)
                            if url:
                                update_product_model(i, url, prompt, data_store, product_id)
                                continue
                        except:
                            pass
                    
                    # フォールバック
                    st.session_state.model_images[i] = image_base64
                    st.session_state.model_prompts[i] = prompt

            except Exception as e:
                st.error(f'モデル{i+1}生成エラー: {str(e)}')
    
    progress.progress(1.0, '完了!')
    st.success('全モデルの生成が完了しました')
    st.rerun()

render_model_page()
