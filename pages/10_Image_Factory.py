import streamlit as st
from modules.data_store import DataStore
from modules.image_factory_manager import ImageFactoryManager

st.set_page_config(page_title="Image Factory", page_icon="🎨", layout="wide")

# 初期化
if 'data_store' not in st.session_state:
    st.session_state['data_store'] = DataStore()

data_store = st.session_state['data_store']
if_manager = ImageFactoryManager(data_store)

st.title("🎨 Image Factory - サムネ・FV生成")

# タブ
tab1, tab2 = st.tabs(["生成", "プリセット一覧"])

with tab1:
    st.subheader("サムネイル生成")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📐 見本選択")
        
        # カテゴリフィルター
        thumb_categories = if_manager.get_categories('thumbnail')
        selected_thumb_cat = st.selectbox("カテゴリ", thumb_categories, key='thumb_cat')
        
        # サムネ一覧
        thumbnails = if_manager.get_reference_thumbnails(
            None if selected_thumb_cat == 'すべて' else selected_thumb_cat
        )
        
        if thumbnails:
            for preset in thumbnails:
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{preset['name']}**")
                        st.caption(f"📂 {preset.get('category', 'N/A')}")
                    with col_b:
                        if st.button("選択", key=f"thumb_{preset['id']}"):
                            st.session_state['selected_thumbnail_id'] = preset['id']
                            st.rerun()
                    
                    # 選択状態表示
                    if st.session_state.get('selected_thumbnail_id') == preset['id']:
                        st.success("✓ 選択中")
                    
                    st.divider()
        else:
            st.warning("プリセットが見つかりません")
        
        st.markdown("### 🎨 トンマナ選択")
        
        # カテゴリフィルター
        tonmana_categories = if_manager.get_categories('tonmana')
        selected_tonmana_cat = st.selectbox("カテゴリ", tonmana_categories, key='tonmana_cat')
        
        # トンマナ一覧
        tonmanas = if_manager.get_tonmana_presets(
            None if selected_tonmana_cat == 'すべて' else selected_tonmana_cat
        )
        
        if tonmanas:
            for preset in tonmanas:
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{preset['name']}**")
                        analysis = preset.get('analysis', {})
                        if analysis and isinstance(analysis, dict):
                            mood = analysis.get('mood', 'N/A')
                            st.caption(f"🎭 {mood}")
                    with col_b:
                        if st.button("選択", key=f"tonmana_{preset['id']}"):
                            st.session_state['selected_tonmana_id'] = preset['id']
                            st.rerun()
                    
                    # 選択状態表示
                    if st.session_state.get('selected_tonmana_id') == preset['id']:
                        st.success("✓ 選択中")
                    
                    st.divider()
        else:
            st.warning("トンマナプリセットが見つかりません")
    
    with col2:
        st.markdown("### プレビュー")
        
        selected_thumb_id = st.session_state.get('selected_thumbnail_id')
        selected_tonmana_id = st.session_state.get('selected_tonmana_id')
        
        # 選択中のサムネ表示
        if selected_thumb_id:
            thumb_data = if_manager.get_thumbnail_by_id(selected_thumb_id)
            if thumb_data:
                st.info(f"📐 見本: **{thumb_data['name']}**")
                
                structure = thumb_data.get('structure', {})
                if structure:
                    with st.expander("レイアウト情報", expanded=True):
                        st.json(structure)
        
        # 選択中のトンマナ表示
        if selected_tonmana_id:
            tonmana_data = if_manager.get_tonmana_by_id(selected_tonmana_id)
            if tonmana_data:
                st.info(f"🎨 トンマナ: **{tonmana_data['name']}**")
                
                analysis = tonmana_data.get('analysis', {})
                if analysis:
                    with st.expander("スタイル情報", expanded=True):
                        st.json(analysis)
        
        # 生成ボタン（Phase 4で実装）
        st.markdown("---")
        if selected_thumb_id and selected_tonmana_id:
            st.success("✅ 生成準備完了")
            
            # 製品選択
            products = data_store.list_products()
            if products:
                product_options = {p['id']: p['name'] for p in products}
                selected_product_id = st.selectbox(
                    "対象製品",
                    options=list(product_options.keys()),
                    format_func=lambda x: product_options[x],
                    key='target_product'
                )
                
                # コピーテキスト入力
                copy_text = st.text_area(
                    "キャッチコピー",
                    placeholder="例：美肌成分3倍配合",
                    height=80
                )
                
                if st.button("🎨 生成実行", type="primary", disabled=True):
                    st.info("生成機能はPhase 4で実装予定")
            else:
                st.warning("製品データがありません。先に「製品一覧」で製品を登録してください。")
        else:
            st.warning("見本とトンマナを両方選択してください")

with tab2:
    st.subheader("プリセット一覧")
    
    preset_type = st.radio("表示タイプ", ["参考サムネ", "トンマナ"], horizontal=True)
    
    if preset_type == "参考サムネ":
        thumbnails = if_manager.get_reference_thumbnails()
        if thumbnails:
            for preset in thumbnails:
                with st.expander(f"{preset['name']} ({preset.get('category', 'N/A')})"):
                    st.json(preset)
        else:
            st.info("プリセットがありません")
    
    else:  # トンマナ
        tonmanas = if_manager.get_tonmana_presets()
        if tonmanas:
            for preset in tonmanas:
                with st.expander(f"{preset['name']} ({preset.get('category', 'N/A')})"):
                    st.json(preset)
        else:
            st.info("プリセットがありません")
