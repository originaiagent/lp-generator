import streamlit as st
from modules.styles import apply_styles, page_header
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(page_title="Information Input", layout="wide")

# スタイル適用
apply_styles()

# AIサイドバー表示
render_ai_sidebar()


import os
from modules.page_guard import require_product

# 製品選択チェック（製品一覧以外で必須）
require_product()


from modules.data_store import DataStore
from modules.file_parser import FileParser
from modules.image_analyzer import ImageAnalyzer
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.settings_manager import SettingsManager
import base64
import uuid
import requests
from pathlib import Path

# 有効な画像URLのみを返す
def get_valid_image_urls(urls):
    """有効な画像URLのみを返す"""
    if not urls:
        return []
    # 有効なURL（httpで始まる文字列）のみを抽出
    return [url for url in urls if url and isinstance(url, str) and (url.startswith('http') or url.startswith('/'))]

def render_images_with_bulk_delete(images, image_type, product_id, data_store):
    """画像表示と一括削除機能"""
    
    if not images:
        st.info("画像がありません")
        return
    
    # 既存の製品情報を取得
    product = data_store.get_product(product_id)
    if not product:
        st.error("製品情報が見つかりません")
        return

    # フィールド名のマッピング
    field_map = {
        "product": {"urls": "product_image_urls", "local": "product_images"},
        "reference_lp": {"urls": "reference_lp_image_urls", "local": "reference_lp_images"},
        "tone_manner": {"urls": "tone_manner_image_urls", "local": "tone_manner_images"}
    }
    fields = field_map.get(image_type)
    if not fields:
        st.error(f"不正な画像タイプです: {image_type}")
        return

    # 一括削除モードの切り替え
    bulk_mode = st.checkbox("一括削除モード", key=f"bulk_mode_{image_type}")
    
    if bulk_mode:
        # 選択状態を管理
        if f"selected_{image_type}" not in st.session_state:
            st.session_state[f"selected_{image_type}"] = []
        
        # 全選択/全解除ボタン
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("全選択", key=f"select_all_{image_type}"):
                st.session_state[f"selected_{image_type}"] = list(range(len(images)))
                st.rerun()
        with col2:
            if st.button("全解除", key=f"deselect_all_{image_type}"):
                st.session_state[f"selected_{image_type}"] = []
                st.rerun()
        
        # 画像をグリッド表示（チェックボックス付き）
        cols = st.columns(4)
        for i, img_info in enumerate(images):
            with cols[i % 4]:
                img_path = img_info["path"]
                # チェックボックス
                selected = st.checkbox(
                    "選択",
                    value=i in st.session_state[f"selected_{image_type}"],
                    key=f"check_{image_type}_{i}"
                )
                if selected and i not in st.session_state[f"selected_{image_type}"]:
                    st.session_state[f"selected_{image_type}"].append(i)
                elif not selected and i in st.session_state[f"selected_{image_type}"]:
                    st.session_state[f"selected_{image_type}"].remove(i)
                
                # 画像表示
                try:
                    st.image(img_path, width=100)
                except:
                    st.caption("⚠️ 読込失敗")
        
        # 一括削除ボタン
        selected_indices = st.session_state[f"selected_{image_type}"]
        selected_count = len(selected_indices)
        if selected_count > 0:
            if st.button(f"選択した {selected_count} 枚を削除", key=f"bulk_delete_{image_type}", type="primary", use_container_width=True):
                # 最新の製品情報を再取得
                current_product = data_store.get_product(product_id) or {}
                
                for idx in sorted(selected_indices, reverse=True):
                    img_info = images[idx]
                    path = img_info["path"]
                    filename = Path(path).name if img_info["type"] == "local" else path.split('/')[-1].split('?')[0]
                    
                    # Storageから削除
                    if img_info["type"] == "url":
                        data_store.delete_storage_file(path)
                        if fields["urls"] in current_product:
                            current_product[fields["urls"]].remove(path)
                    
                    # ローカルリストから削除
                    if fields["local"] in current_product:
                        current_product[fields["local"]] = [p for p in current_product[fields["local"]] if Path(p).name != filename]

                    # Reference LP 特有の処理（分析結果の削除）
                    if image_type == "reference_lp":
                        if "lp_analyses_dict" in current_product:
                            analyses_dict = current_product["lp_analyses_dict"] or {}
                            if filename in analyses_dict:
                                del analyses_dict[filename]
                            current_product["lp_analyses_dict"] = analyses_dict
                            
                            # lp_analyses リストも再構築
                            new_lp_analyses = []
                            for local_p in (current_product.get("reference_lp_images") or []):
                                fname = Path(local_p).name
                                if fname in analyses_dict:
                                    new_lp_analyses.append(analyses_dict[fname])
                            current_product["lp_analyses"] = new_lp_analyses
                
                data_store.update_product(product_id, current_product)
                # 選択状態をリセット
                st.session_state[f"selected_{image_type}"] = []
                st.success(f"{selected_count} 枚の画像を削除しました")
                st.rerun()
    else:
        # 通常モード（現状の表示）
        cols = st.columns(4)
        for i, img_info in enumerate(images):
            with cols[i % 4]:
                img_path = img_info["path"]
                filename = Path(img_path).name if img_info["type"] == "local" else img_path.split('/')[-1].split('?')[0]
                try:
                    st.image(img_path, width=100)
                except:
                    st.caption("⚠️ 読込失敗")
                
                if st.button("削除", key=f"delete_{image_type}_{i}", use_container_width=True):
                    # 最新の製品情報を再取得
                    current_product = data_store.get_product(product_id) or {}
                    
                    # Storageから削除
                    if img_info["type"] == "url":
                        data_store.delete_storage_file(img_path)
                        if fields["urls"] in current_product:
                            current_product[fields["urls"]].remove(img_path)
                    
                    # ローカルリストから削除
                    if fields["local"] in current_product:
                        current_product[fields["local"]] = [p for p in current_product[fields["local"]] if Path(p).name != filename]

                    # Reference LP 特有の処理
                    if image_type == "reference_lp":
                        if "lp_analyses_dict" in current_product:
                            analyses_dict = current_product["lp_analyses_dict"] or {}
                            if filename in analyses_dict:
                                del analyses_dict[filename]
                            current_product["lp_analyses_dict"] = analyses_dict
                            new_lp_analyses = []
                            for local_p in (current_product.get("reference_lp_images") or []):
                                fname = Path(local_p).name
                                if fname in analyses_dict:
                                    new_lp_analyses.append(analyses_dict[fname])
                            current_product["lp_analyses"] = new_lp_analyses
                    
                    data_store.update_product(product_id, current_product)
                    st.rerun()

def render_input_page():
    '''入力情報ページのメイン関数'''
    page_header("Information Input", "競合・製品情報の入力と分析")
    
    # STEP表示用スタイル
    st.markdown("""
    <style>
    .step-label {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
        display: inline-block;
    }
    .section-divider {
        border-top: 2px solid #E5E7EB;
        margin: 2rem 0 1rem 0;
        padding-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # AIサイドバー表示
    
    data_store = DataStore()
    
    # 現在の製品IDを取得
    if 'current_product_id' not in st.session_state:
        st.error("製品IDが設定されていません。")
        return
    
    product_id = st.session_state['current_product_id']
    
    # オートリペア: 壊れたURLをロード時にクリーンアップ
    product = data_store.get_product(product_id)
    if product:
        repaired = False
        for key in ['reference_lp_image_urls', 'tone_manner_image_urls', 'product_image_urls']:
            if key in product:
                original = product[key] or []
                filtered = get_valid_image_urls(original)
                if len(original) != len(filtered):
                    product[key] = filtered
                    repaired = True
        
        if repaired:
            data_store.update_product(product_id, product)
            # st.toast("不整合な画像データを自動修復しました", icon="🪄")

    # 各セクションをレンダリング
    render_product_images_upload(data_store, product_id)
    render_competitor_analysis(data_store, product_id)
    render_sheets_upload(data_store, product_id)
    render_reference_images_upload(data_store, product_id)

def render_product_images_upload(data_store, product_id):
    '''製品画像アップロード'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">製品画像</div>', unsafe_allow_html=True)
    
    # 先頭で product を取得
    product = data_store.get_product(product_id) or {}
    
    uploaded_files = st.file_uploader(
        "製品画像をアップロードしてください",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        key="product_images"
    )
    
    if uploaded_files:
        upload_dir = Path(f"data/uploads/{product_id}/product_images").resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        image_paths = []
        if not data_store.use_supabase:
            for uploaded_file in uploaded_files:
                file_path = upload_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_paths.append(str(file_path))  # 絶対パスとして保存
                st.success(f"アップロード完了: {uploaded_file.name}")
            
            # データを更新 (既に先頭で取得済み)
            
            # 既存リストとマージ
            existing_images = product.get('product_images') or []
            for path in image_paths:
                if path not in existing_images:
                    existing_images.append(path)
            product['product_images'] = existing_images
        
        # Supabaseへアップロード
        if data_store.use_supabase:
            remote_urls = product.get('product_image_urls') or []
            # 今回アップロードされたファイルをSync
            for uploaded_file in uploaded_files:
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    
                    # ファイル名をサニタイズ（UUID + 拡張子）
                    ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'jpg'
                    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                    remote_path = f"{product_id}/product_images/{safe_name}"
                    
                    # アップロード試行
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    
                    if url:
                        # 既存URLに含まれていなければ追加
                        if url and url not in remote_urls:
                            remote_urls.append(url)
                            st.toast(f"クラウド保存完了: {uploaded_file.name}", icon="☁️")
                    else:
                        st.error(f"アップロード失敗: URLが取得できませんでした ({uploaded_file.name})")
                        
                except Exception as e:
                    st.error(f"Upload failed for {uploaded_file.name}: {e}")
            
            # 保存前に重複を除去
            remote_urls = list(dict.fromkeys(remote_urls))
            product['product_image_urls'] = remote_urls

        # データベース更新
        if data_store.update_product(product_id, product):
            st.success("製品情報を更新しました")
        else:
            st.error("データベースの更新に失敗しました")
    
    # アップロード済み画像を表示
    product = data_store.get_product(product_id)
    
    # 表示用リストの構築
    display_images = []
    if product:
        # クラウドURL
        image_urls = get_valid_image_urls(product.get("product_image_urls") or [])
        display_images.extend([{"type": "url", "path": url} for url in image_urls])
        
        # ローカルパス（Supabase未使用時のみ）
        if not data_store.use_supabase:
            local_images = product.get("product_images") or []
            for path in local_images:
                if Path(path).exists():
                    display_images.append({"type": "local", "path": path})

    if display_images:
        st.markdown("**アップロード済み画像:**")
        render_images_with_bulk_delete(display_images, "product", product_id, data_store)


def delete_competitor(product_id, data_store, delete_idx):
    """競合を削除し、インデックスを詰め直す"""
    product = data_store.get_product(product_id) or {}
    current_data = product.get("competitor_analysis_v2") or {}
    competitors = current_data.get("competitors") or []
    
    if 0 <= delete_idx < len(competitors):
        # 1. DBデータから削除
        deleted = competitors.pop(delete_idx)
        
        # 1.5 Storageから実ファイルを削除
        for url in (deleted.get("file_urls") or []):
            data_store.delete_storage_file(url)
        
        if not competitors:
            # 競合が0になった場合は分析データ全体をクリア
            product["competitor_analysis_v2"] = {}
        else:
            # 削除後のリストに基づいて再集計（AI呼び出しなしで済みます）
            from modules.image_analyzer import ImageAnalyzer
            # summarize_all_competitorsはAIプロバイダを使用しないためNoneで初期化可
            analyzer = ImageAnalyzer(None, None) 
            new_summary = analyzer.summarize_all_competitors(competitors)
            current_data["summary"] = new_summary
            current_data["competitors"] = competitors
            product["competitor_analysis_v2"] = current_data
            
        data_store.update_product(product_id, product)
        
        st.toast(f"「{deleted.get('name', '競合')}」を削除しました", icon="🗑️")
    
    # 2. Session Stateの再構築（詰め直し）
    old_count = st.session_state.competitor_count
    new_count = old_count - 1
    
    # 削除対象より後ろの要素を前にずらす
    for i in range(delete_idx, new_count):
        next_i = i + 1
        st.session_state[f"comp_name_{i}"] = st.session_state.get(f"comp_name_{next_i}", f"競合{i+1}")
        st.session_state[f"comp_text_{i}"] = st.session_state.get(f"comp_text_{next_i}", "")
        st.session_state[f"comp_files_paths_{i}"] = st.session_state.get(f"comp_files_paths_{next_i}", [])
        st.session_state[f"comp_file_urls_{i}"] = st.session_state.get(f"comp_file_urls_{next_i}", [])
        # uploader_keyもリセットまたは移動させる方が安全だが、ここでは新規キー発行を促すため削除
        if f"uploader_key_comp_{next_i}" in st.session_state:
             st.session_state[f"uploader_key_comp_{i}"] = st.session_state[f"uploader_key_comp_{next_i}"]
    
    # 末尾の要素を削除
    last_idx = old_count - 1
    keys_to_remove = [
        f"comp_name_{last_idx}", f"comp_text_{last_idx}", 
        f"comp_files_paths_{last_idx}", f"comp_file_urls_{last_idx}",
        f"uploader_key_comp_{last_idx}"
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
            
    st.session_state.competitor_count = new_count
    st.rerun()


def handle_competitor_upload(product_id, data_store, comp_idx):
    """競合画像アップロード時のコールバック処理"""
    if f"uploader_key_comp_{comp_idx}" not in st.session_state:
        st.session_state[f"uploader_key_comp_{comp_idx}"] = 0
    
    key = f"comp_files_{comp_idx}_{st.session_state[f'uploader_key_comp_{comp_idx}']}"
    uploaded_files = st.session_state.get(key)
    
    if uploaded_files:
        upload_dir = Path(f"data/uploads/{product_id}/competitors/comp_{comp_idx}")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        image_paths = []
        if not data_store.use_supabase:
            for uf in uploaded_files:
                file_path = upload_dir / uf.name
                with open(file_path, "wb") as f:
                    f.write(uf.getbuffer())
                image_paths.append(str(file_path))
                st.toast(f"競合{comp_idx+1}: アップロード中... {uf.name}")
            
            # 最新の製品情報を取得
            product = data_store.get_product(product_id) or {}
            current_data = product.get("competitor_analysis_v2") or {}
            competitors = current_data.get("competitors") or []
            
            # 整合性確保（リストが短い場合は拡張）
            while len(competitors) <= comp_idx:
                competitors.append({})
            
            comp_data = competitors[comp_idx]
            
            # ローカルパス保存
            existing_files = (comp_data.get("files") or [])
            for path in image_paths:
                if path not in existing_files:
                    existing_files.append(path)
            comp_data["files"] = existing_files
        
        # Supabase保存
        if data_store.use_supabase:
            product = data_store.get_product(product_id) or {} # Re-fetch product if not already fetched for Supabase
            current_data = product.get("competitor_analysis_v2") or {}
            competitors = current_data.get("competitors") or []
            while len(competitors) <= comp_idx:
                competitors.append({})
            comp_data = competitors[comp_idx]

            remote_urls = (comp_data.get("file_urls") or [])
            for uf in uploaded_files:
                try:
                    uf.seek(0)
                    file_bytes = uf.read()
                    
                    # ファイル名をサニタイズ（UUID + 拡張子）
                    ext = uf.name.split('.')[-1].lower() if '.' in uf.name else 'jpg'
                    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                    remote_path = f"{product_id}/competitors/comp_{comp_idx}/{safe_name}"
                    
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    if url and url not in remote_urls:
                        remote_urls.append(url)
                except Exception as e:
                    st.error(f"Supabaseアップロード失敗: {e}")
            comp_data["file_urls"] = remote_urls
        
        competitors[comp_idx] = comp_data
        current_data["competitors"] = competitors
        product["competitor_analysis_v2"] = current_data
        
        # DB保存
        if data_store.update_product(product_id, product):
            # Session Stateの同期
            st.session_state[f"comp_files_paths_{comp_idx}"] = comp_data.get("files", [])
            st.session_state[f"comp_file_urls_{comp_idx}"] = comp_data.get("file_urls", [])
            
            # アップローダーをクリア
            st.session_state[f"uploader_key_comp_{comp_idx}"] += 1
            st.toast(f"競合{comp_idx+1}: すべての画像を保存しました", icon="✅")
            st.rerun()


def save_competitor_field(product_id, data_store, comp_idx, field_name):
    """特定の競合の特定フィールドだけをDBに保存"""
    # セッションから対応するキー名を取得
    session_key = f"comp_{field_name}_{comp_idx}"
    if field_name == "files":
        session_key = f"comp_files_paths_{comp_idx}"
    elif field_name == "file_urls":
        session_key = f"comp_file_urls_{comp_idx}"
        
    new_value = st.session_state.get(session_key)
    if new_value is None:
        return

    # DBから最新状態を取得してマージ
    product = data_store.get_product(product_id) or {}
    current_data = product.get("competitor_analysis_v2") or {}
    competitors = (current_data.get("competitors") or []).copy()

    # インデックスの整合性確保
    while len(competitors) <= comp_idx:
        competitors.append({
            "name": f"競合{len(competitors)+1}", 
            "text": "", 
            "files": [], 
            "file_urls": []
        })

    # 該当する競合の指定フィールドだけを更新
    competitors[comp_idx][field_name] = new_value

    current_data["competitors"] = competitors
    product["competitor_analysis_v2"] = current_data
    
    if data_store.update_product(product_id, product):
        st.toast(f"保存完了: {competitors[comp_idx].get('name', '競合')}")

def save_competitor_text(product_id, competitor_index, data_store):
    """競合テキストを自動保存"""
    key = f"comp_text_{competitor_index}"
    if key in st.session_state:
        text = st.session_state[key]
        product = data_store.get_product(product_id)
        if product:
            current_data = product.get("competitor_analysis_v2") or {}
            competitors = (current_data.get("competitors") or []).copy()
            
            # インデックスの整合性確保
            while len(competitors) <= competitor_index:
                competitors.append({
                    "name": f"競合{len(competitors)+1}", 
                    "text": "", 
                    "files": [], 
                    "file_urls": []
                })
            
            competitors[competitor_index]['text'] = text
            current_data["competitors"] = competitors
            product["competitor_analysis_v2"] = current_data
            
            if data_store.update_product(product_id, product):
                st.toast(f"テキストを保存しました: {competitors[competitor_index].get('name', '競合')}")

def render_competitor_analysis(data_store, product_id):
    '''競合情報分析セクション'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">競合情報</div>', unsafe_allow_html=True)
    st.caption("競合ごとに画像・テキストをアップロード → 訴求要素を自動抽出")
    
    # セッション初期化（保存データがあれば復元）
    # プロダクトIDが変わった場合も初期化を行う
    if "competitor_count" not in st.session_state or st.session_state.get("last_product_id") != product_id:
        st.session_state.last_product_id = product_id
        # DBから保存済みデータを取得
        product = data_store.get_product(product_id)
        saved_competitors = []
        if product:
            saved_competitors = (product.get("competitor_analysis_v2") or {}).get("competitors", [])
        
        if saved_competitors:
            st.session_state.competitor_count = len(saved_competitors)
            for i, comp in enumerate(saved_competitors):
                st.session_state[f"comp_name_{i}"] = comp.get("name", f"競合{i+1}")
                st.session_state[f"comp_text_{i}"] = comp.get("text", "")
                
                # ファイルパスの復元
                if "files" in comp:
                    st.session_state[f"comp_files_paths_{i}"] = (comp.get("files") or [])
                
                # Supabase URLの復元
                if "file_urls" in comp:
                    st.session_state[f"comp_file_urls_{i}"] = (comp.get("file_urls") or [])
        else:
            st.session_state.competitor_count = 1
    
    # 競合追加ボタン
    col_add, col_space = st.columns([1, 3])
    with col_add:
        if st.button("競合を追加", key="add_competitor"):
            if st.session_state.competitor_count < 10:
                st.session_state.competitor_count += 1
                st.rerun()
            else:
                st.warning("最大10社までです")
    
    st.markdown("---")
    
    # 各競合の入力エリア
    for i in range(st.session_state.competitor_count):
        with st.expander(f"競合{i+1}", expanded=False):
            # 削除ボタン（ヘッダー横には置けないのでexpander内）
            col_del_btn, _ = st.columns([1, 5])
            with col_del_btn:
                if st.button("この競合を削除", key=f"del_comp_{i}"):
                    delete_competitor(product_id, data_store, i)
            
            # キーとデフォルト値の準備
            name_key = f"comp_name_{i}"
            default_name = f"競合{i+1}"
            if name_key not in st.session_state:
                st.session_state[name_key] = default_name

            comp_name = st.text_input(
                "競合名",
                # value引数は削除（session_state優先）
                key=name_key,
                placeholder="例: A社、B社",
                on_change=save_competitor_field,
                args=(product_id, data_store, i, "name")
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**画像（最大30枚）**")
                
                # 保存済みファイルを確認
                # 1. URL優先
                saved_urls = st.session_state.get(f"comp_file_urls_{i}") or []
                # 2. ローカルパス（フォールバック）
                saved_local = st.session_state.get(f"comp_files_paths_{i}") or []

                # ダイナミックキーによるリセット対応
                if f"uploader_key_comp_{i}" not in st.session_state:
                    st.session_state[f"uploader_key_comp_{i}"] = 0
                
                uploader_key = f"comp_files_{i}_{st.session_state[f'uploader_key_comp_{i}']}"
                
                uploaded_files = st.file_uploader(
                    "LP画像をアップロード",
                    type=['png', 'jpg', 'jpeg'],
                    accept_multiple_files=True,
                    key=uploader_key,
                    label_visibility="collapsed",
                    on_change=handle_competitor_upload,
                    args=(product_id, data_store, i)
                )
                
                # 表示用リストの統合
                display_images = []
                # URLを優先
                for url in saved_urls:
                    display_images.append({"type": "url", "path": url})
                
                # Supabase未使用時のみローカルを表示
                if not data_store.use_supabase:
                    for lp in saved_local:
                        if Path(lp).exists():
                            display_images.append({"type": "local", "path": lp})
                
                # 表示
                if display_images:
                    st.caption(f"{len(display_images)}枚")
                    preview_cols = st.columns(6)
                    for idx, img in enumerate(display_images[:6]):
                        with preview_cols[idx % 6]:
                            st.image(img["path"], width=80)
                    if len(display_images) > 6:
                        st.caption(f"他 {len(display_images) - 6}枚")
            
                # キーの準備
                text_key = f"comp_text_{i}"
                if text_key not in st.session_state:
                    st.session_state[text_key] = ""

                comp_text = st.text_area(
                    "競合のLP情報をコピペ",
                    height=150,
                    key=text_key,
                    placeholder="競合商品ページから情報をコピー&ペースト...",
                    label_visibility="collapsed",
                    on_change=save_competitor_text,
                    args=(product_id, i, data_store)
                )
    
    st.markdown("---")
    
    # 一括分析ボタン
    if st.button("一括分析", type="primary", use_container_width=True, key="analyze_all_competitors"):
        analyze_all_competitors(product_id, data_store)
    
    # 分析結果表示
    product = data_store.get_product(product_id)
    if product and product.get("competitor_analysis_v2"):
        st.markdown("---")
        render_competitor_analysis_results(product["competitor_analysis_v2"])


def organize_keyword_data(product, data_store, product_id):
    """キーワードデータを重要度順に整理"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.trace_viewer import save_with_trace
    
    st.write("DEBUG: 関数開始")
    st.info("キーワード分析を開始します...")
    
    # ProductがNoneの場合のガード
    if not product:
        product = {}

    with st.spinner("キーワード重要度を分析中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # シートデータを文字列化
            sheet_data = product.get("review_sheet_data") or {}
            st.write(f"DEBUG: sheet_data = {str(sheet_data)[:100]}...")
            raw_text = ""
            if isinstance(sheet_data, dict):
                data_type = sheet_data.get("type", "")
                sheet_content = sheet_data.get("content", "")
                
                if data_type in ["pdf", "text"]:
                    raw_text = str(sheet_content)
                    
                    # PDFライブラリ未インストール時のエラー文字が入っている場合は再パースを試みる
                    if "PDFライブラリがインストールされていません" in raw_text:
                        st.write("DEBUG: PDF再パースを試行中...")
                        file_path = product.get("review_sheet")
                        if file_path and os.path.exists(file_path):
                            from modules.file_parser import FileParser
                            parsed = FileParser().parse(file_path)
                            if parsed.get("content") != "PDFライブラリがインストールされていません":
                                st.write("DEBUG: PDF再パース成功")
                                sheet_data = parsed
                                product["review_sheet_data"] = parsed
                                raw_text = str(parsed.get("content", ""))
                            else:
                                st.error("PDFライブラリ（pymupdfまたはpypdf）がまだ有効ではありません。環境を確認してください。")
                                return
                        else:
                            st.error("元のPDFファイルが見つかりません。再アップロードしてください。")
                            return
                elif isinstance(sheet_content, list):
                    for item in sheet_content:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if v and str(v) not in ['nan', 'NaN', 'None', '']:
                                    raw_text += f"{k}: {v}\n"
                else:
                    raw_text = str(sheet_content)
            else:
                raw_text = str(sheet_data)
            
            st.write(f"DEBUG: raw_text長さ = {len(raw_text)}")
            
            prompt = prompt_manager.get_prompt("keyword_organize", {
                "raw_data": raw_text[:3000]
            })
            st.write(f"DEBUG: prompt取得 = {bool(prompt)}")
            
            if not prompt:
                st.error("プロンプト 'keyword_organize' が見つかりません。設定を確認してください。")
                return

            st.write("DEBUG: AI結果取得中...")
            result = ai_provider.ask(prompt, "keyword_organize")
            st.write(f"DEBUG: AI結果 = {result[:100] if result else 'None'}")
            
            traced = save_with_trace(
                result=result,
                prompt_id="keyword_organize",
                prompt_used=prompt,
                input_refs={"ファイル": (product.get("review_sheet") or "")},
                model=settings.get("llm_model", "unknown")
            )
            
            product["keyword_organized"] = result
            product["keyword_organize_trace"] = traced

            st.write("DEBUG: DB保存開始")
            if data_store.update_product(product_id, product):
                st.success("キーワード分析完了！")
                import time
                time.sleep(5)
                st.rerun()
            else:
                error_detail = getattr(data_store, 'last_error', '不明なエラー')
                st.error(f"DB更新失敗: {error_detail}")
            
        except Exception as e:
            st.error(f"分析エラー: {e}")


def organize_sheet_data(product, data_store, product_id):
    """シートデータをAIで整理"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.trace_viewer import save_with_trace
    import time
    
    st.write("DEBUG: 関数開始")
    st.info("シート整理を開始します...")

    # ProductがNoneの場合のガード
    if not product:
        product = {}
    
    with st.spinner("シート内容を整理中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # シートデータを文字列化
            sheet_data = product.get("product_sheet_data") or {}
            st.write(f"DEBUG: sheet_data = {str(sheet_data)[:100]}...")
            raw_text = ""
            if isinstance(sheet_data, dict):
                data_type = sheet_data.get("type", "")
                content = sheet_data.get("content", "")
                
                if data_type in ["pdf", "text"]:
                    # PDF/テキストはそのまま
                    raw_text = str(content)
                    
                    # PDFライブラリ未インストール時のエラー文字が入っている場合は再パースを試みる
                    if "PDFライブラリがインストールされていません" in raw_text:
                        st.write("DEBUG: PDF再パースを試行中...")
                        file_path = product.get("product_sheet")
                        if file_path and os.path.exists(file_path):
                            from modules.file_parser import FileParser
                            parsed = FileParser().parse(file_path)
                            if parsed.get("content") != "PDFライブラリがインストールされていません":
                                st.write("DEBUG: PDF再パース成功")
                                sheet_data = parsed
                                product["product_sheet_data"] = parsed
                                raw_text = str(parsed.get("content", ""))
                            else:
                                st.error("PDFライブラリ（pymupdfまたはpypdf）がまだ有効ではありません。環境を確認してください。")
                                return
                        else:
                            st.error("元のPDFファイルが見つかりません。再アップロードしてください。")
                            return
                elif isinstance(content, list):
                    # CSV/Excelはリスト形式
                    for item in content:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if v and str(v) not in ['nan', 'NaN', 'None', '']:
                                    raw_text += f"{k}: {v}\n"
                else:
                    raw_text = str(content)
            else:
                raw_text = str(sheet_data)
            
            st.write(f"DEBUG: raw_text長さ = {len(raw_text)}")
            
            prompt = prompt_manager.get_prompt("sheet_organize", {
                "raw_data": raw_text[:3000]
            })
            st.write(f"DEBUG: prompt取得 = {bool(prompt)}")
            
            if not prompt:
                st.error("プロンプト 'sheet_organize' が見つかりません。設定を確認してください。")
                return

            result = ai_provider.ask(prompt, "sheet_organize")
            st.write(f"DEBUG: AI結果 = {result[:100] if result else 'None'}")
            
            # トレース付きで保存
            traced = save_with_trace(
                result=result,
                prompt_id="sheet_organize",
                prompt_used=prompt,
                input_refs={"ファイル": (product.get("product_sheet") or "")},
                model=settings.get("llm_model", "unknown")
            )
            
            product["product_sheet_organized"] = result
            product["product_sheet_organize_trace"] = traced
            
            st.write("DEBUG: DB保存開始")
            if data_store.update_product(product_id, product):
                 st.success("整理完了！")
                 time.sleep(5)
                 st.rerun()
            else:
                 error_detail = getattr(data_store, 'last_error', '不明なエラー')
                 st.error(f"DB更新失敗: {error_detail}")
            
        except Exception as e:
            st.error(f"整理エラー: {e}")


def analyze_competitor_text(text, product_id, data_store):
    '''競合テキストをAIで分析'''
    from modules.trace_viewer import save_with_trace
    with st.spinner('競合情報を分析中...'):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            prompt = prompt_manager.get_prompt("competitor_analysis", {
                "competitor_text": text
            })
            
            result = ai_provider.ask(prompt, "competitor_analysis")
            
            # トレース付きで保存
            traced_result = save_with_trace(
                result=result,
                prompt_id="competitor_analysis",
                prompt_used=prompt,
                input_refs={"競合テキスト": text[:200] + "..." if len(text) > 200 else text},
                model=settings.get("llm_model", settings.get("llm_provider", "unknown"))
            )
            
            product = data_store.get_product(product_id)
            if not product:
                product = {}
            product['competitor_analysis'] = traced_result
            data_store.update_product(product_id, product)
            
            st.success("分析完了！")
            st.rerun()
            
        except Exception as e:
            st.error(f"分析エラー: {e}")
        except Exception as e:
            st.error(f"分析エラー: {e}")

def analyze_competitor_files(file_paths, product_id, data_store):
    '''競合ファイル（PDF/画像）をAIで分析'''
    with st.spinner('ファイルを分析中...'):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            
            all_analysis = []
            
            for file_path in file_paths:
                if file_path.lower().endswith('.pdf'):
                    # PDFの場合はテキスト抽出
                    file_parser = FileParser()
                    text = file_parser.parse(file_path)
                    if text:
                        prompt = f"""以下のPDF文書の内容を分析して、競合商品の情報をまとめてください。

{text}

【出力形式】
- 製品の特徴
- 価格情報（あれば）
- ターゲット顧客
- 訴求ポイント"""
                        result = ai_provider.generate_text(prompt)
                        all_analysis.append(f"📄 {os.path.basename(file_path)}:\n{result}")
                
                elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    # 画像の場合はVision APIで分析
                    prompt_manager = PromptManager()
                    image_analyzer = ImageAnalyzer(ai_provider, prompt_manager)
                    result = image_analyzer.analyze_image(file_path)
                    all_analysis.append(f"🖼️ {os.path.basename(file_path)}:\n{result}")
            
            if all_analysis:
                combined_analysis = "\n\n---\n\n".join(all_analysis)
                
                # 結果を保存
                product = data_store.get_product(product_id)
                if not product:
                    product = {}
                product['competitor_analysis'] = combined_analysis
                data_store.update_product(product_id, product)
                
                st.success("分析完了！")
                st.rerun()
            else:
                st.warning("分析できるファイルがありませんでした")
                
        except Exception as e:
            st.error(f"分析エラー: {e}")

def analyze_all_competitors(product_id, data_store):
    """全競合を一括分析（プログレス表示付き）"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.image_analyzer import ImageAnalyzer
    
    try:
        settings_manager = SettingsManager()
        settings = settings_manager.get_settings()
        ai_provider = AIProvider(settings)
        prompt_manager = PromptManager()
        image_analyzer = ImageAnalyzer(ai_provider, prompt_manager)
        
        # 分析対象を収集
        targets = []
        for i in range(st.session_state.competitor_count):
            comp_name = st.session_state.get(f"comp_name_{i}", f"競合{i+1}")
            file_paths = st.session_state.get(f"comp_files_paths_{i}", [])
            file_urls = st.session_state.get(f"comp_file_urls_{i}", [])
            comp_text = st.session_state.get(f"comp_text_{i}", "")
            
            if file_paths or file_urls or comp_text.strip():
                targets.append({
                    "name": comp_name,
                    "files": file_paths,
                    "file_urls": file_urls,
                    "text": comp_text
                })
        
        if not targets:
            st.warning("分析するデータがありません")
            return
        
        # プログレス表示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        for idx, target in enumerate(targets):
            status_text.text(f"分析中: {target['name']} ({idx+1}/{len(targets)})")
            progress_bar.progress((idx) / len(targets))
            
            result = image_analyzer.analyze_competitor(
                target["name"], 
                target["files"], 
                target["text"]
            )
            # URLを書き戻し（分析結果に含まれないため）
            result["file_urls"] = target.get("file_urls", [])
            results.append(result)
        
        progress_bar.progress(1.0)
        status_text.text("集計中...")
        
        summary = image_analyzer.summarize_all_competitors(results)
        
        analysis_data = {
            "competitors": results,
            "summary": summary
        }
        
        product = data_store.get_product(product_id)
        if not product:
            product = {}
        product["competitor_analysis_v2"] = analysis_data
        data_store.update_product(product_id, product)
        
        status_text.empty()
        progress_bar.empty()
        st.success(f"{len(results)}社の競合を分析しました")
        st.rerun()
    
    except Exception as e:
        st.error(f"分析エラー: {e}")


def render_competitor_analysis_results(analysis_data):
    """競合分析結果を表示"""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">分析結果</div>', unsafe_allow_html=True)
    
    competitors = analysis_data.get("competitors", [])
    summary = analysis_data.get("summary", {})
    
    # 各競合の結果
    for comp in competitors:
        name = comp.get("name", "不明")
        img_count = comp.get("image_count", 0)
        has_text = comp.get("has_text", False)
        elements = comp.get("elements", [])
        
        source_info = []
        if img_count > 0:
            source_info.append(f"画像{img_count}枚")
        if has_text:
            source_info.append("テキスト")
        
        st.markdown(f"**■ {name}** ({', '.join(source_info)})")
        if elements:
            st.markdown(", ".join(elements))
        else:
            st.markdown("_要素なし_")
        st.markdown("")
    
    # 全体サマリー
    if summary.get("element_ranking"):
        st.markdown("---")
        st.subheader("全競合の訴求要素まとめ")
        
        total = summary.get("total_competitors", 1)
        
        col1, col2 = st.columns(2)
        for i, (elem, count) in enumerate(summary["element_ranking"]):
            target_col = col1 if i % 2 == 0 else col2
            with target_col:
                if count == total:
                    st.markdown(f"✅ **{elem}** ({count}/{total}社) ← 必須")
                elif count >= total * 0.5:
                    st.markdown(f"✓ {elem} ({count}/{total}社)")
                else:
                    st.markdown(f"・ {elem} ({count}/{total}社)")


def save_product_sheet(product_id, data_store):
    product = data_store.get_product(product_id)
    if product and "edit_organized" in st.session_state:
        product["product_sheet_organized"] = st.session_state.edit_organized
        if data_store.update_product(product_id, product):
            st.toast("製品シート情報を保存しました")

def save_keyword_sheet(product_id, data_store):
    product = data_store.get_product(product_id)
    if product and "edit_keyword" in st.session_state:
        product["keyword_organized"] = st.session_state.edit_keyword
        if data_store.update_product(product_id, product):
            st.toast("キーワード情報を保存しました")

def render_sheets_upload(data_store, product_id):
    '''各種シートアップロード'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">データシート</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        product_sheet = st.file_uploader(
            "製品情報シート",
            type=['xlsx', 'csv', 'pdf'],
            key="product_sheet"
        )
        
        if product_sheet:
            upload_dir = Path(f"data/uploads/{product_id}/sheets")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / f"product_sheet_{product_sheet.name}"
            with open(file_path, "wb") as f:
                f.write(product_sheet.getbuffer())
            
            file_parser = FileParser()
            try:
                parsed_data = file_parser.parse(str(file_path))
                
                product = data_store.get_product(product_id)
                if not product:
                    product = {}
                product['product_sheet'] = str(file_path)
                product['product_sheet_data'] = parsed_data
                data_store.update_product(product_id, product)
                
                st.success("製品情報シートをアップロードしました")
            except Exception as e:
                st.error(f"ファイル解析エラー: {e}")
        
        # アップロード済み表示
        product = data_store.get_product(product_id)
        if product and product.get('product_sheet'):
            col_info, col_del = st.columns([4, 1])
            with col_info:
                st.info(f"📄 {Path(product['product_sheet']).name}")
            with col_del:
                if st.button("削除", key="del_product_sheet"):
                    product['product_sheet'] = None
                    product['product_sheet_data'] = None
                    product['product_sheet_organized'] = None
                    data_store.update_product(product_id, product)
                    st.rerun()
            
            # 整理済みデータがあれば表示
            organized = product.get("product_sheet_organized") or ""
            if organized:
                st.success("整理済み")
                with st.expander("整理済み内容を確認・編集", expanded=False):
                    edited = st.text_area("内容", value=organized, height=300, key="edit_organized", on_change=save_product_sheet, args=(product_id, data_store))
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("変更を保存", key="save_organized"):
                            product["product_sheet_organized"] = edited
                            data_store.update_product(product_id, product)
                            st.success("保存しました")
                            st.rerun()
                    with col_b:
                        if st.button("再整理（AI）", key="reorganize_sheet"):
                            organize_sheet_data(product, data_store, product_id)
            else:
                if st.button("内容を整理（AI）", key="organize_sheet"):
                    organize_sheet_data(product, data_store, product_id)
    
    with col2:
        review_sheet = st.file_uploader(
            "競合レビューシート",
            type=['xlsx', 'csv', 'pdf'],
            key="review_sheet"
        )
        
        if review_sheet:
            upload_dir = Path(f"data/uploads/{product_id}/sheets")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / f"review_sheet_{review_sheet.name}"
            with open(file_path, "wb") as f:
                f.write(review_sheet.getbuffer())
            
            file_parser = FileParser()
            try:
                parsed_data = file_parser.parse(str(file_path))
                
                product = data_store.get_product(product_id)
                if not product:
                    product = {}
                product['review_sheet'] = str(file_path)
                product['review_sheet_data'] = parsed_data
                data_store.update_product(product_id, product)
                
                st.success("競合レビューシートをアップロードしました")
            except Exception as e:
                st.error(f"ファイル解析エラー: {e}")
        
        # アップロード済み表示
        product = data_store.get_product(product_id)
        if product and product.get("review_sheet"):
            col_info, col_del = st.columns([4, 1])
            with col_info:
                st.info(f"📄 {Path(product['review_sheet']).name}")
            with col_del:
                if st.button("削除", key="del_review_sheet"):
                    product['review_sheet'] = None
                    product['review_sheet_data'] = None
                    product['keyword_organized'] = None
                    data_store.update_product(product_id, product)
                    st.rerun()
            
            # キーワード整理済みデータがあれば表示
            keyword_org = product.get("keyword_organized") or ""
            if keyword_org:
                with st.expander("キーワード重要度（確認・編集）", expanded=False):
                    edited = st.text_area("内容", value=keyword_org, height=300, key="edit_keyword", on_change=save_keyword_sheet, args=(product_id, data_store))
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("変更を保存", key="save_keyword"):
                            product["keyword_organized"] = edited
                            data_store.update_product(product_id, product)
                            st.success("保存しました")
                            st.rerun()
                    with col_b:
                        if st.button("再分析", key="reanalyze_keyword"):
                            organize_keyword_data(product, data_store, product_id)
            else:
                if st.button("キーワード重要度を分析", key="analyze_keyword"):
                    organize_keyword_data(product, data_store, product_id)



def handle_lp_upload(product_id, data_store):
    """参考LP画像アップロード時のコールバック処理"""
    if "uploader_key_lp" not in st.session_state:
        st.session_state.uploader_key_lp = 0
    
    key = f"lp_images_{st.session_state.uploader_key_lp}"
    lp_images = st.session_state.get(key)
    
    if lp_images:
        image_paths = []
        # Supabase使用時はローカル保存を回避
        if not data_store.use_supabase:
            upload_dir = Path(f"data/uploads/{product_id}/reference_lp")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            for uploaded_file in lp_images:
                file_path = upload_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_paths.append(str(file_path))
                st.toast(f"アップロード完了: {uploaded_file.name}")
            
            # データを更新
            product = data_store.get_product(product_id) or {}
            existing = product.get('reference_lp_images') or []
            for path in image_paths:
                if path not in existing:
                    existing.append(path)
            product['reference_lp_images'] = existing
        
        # Supabase用の製品情報取得
        if data_store.use_supabase:
            product = data_store.get_product(product_id) or {}
        
        # Supabase Storageへアップロード
        if data_store.use_supabase:
            remote_urls = product.get('reference_lp_image_urls') or []
            uploaded_count = 0
            for uploaded_file in lp_images:
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    
                    # ファイル名をサニタイズ（UUID + 拡張子）
                    ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'jpg'
                    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                    remote_path = f"{product_id}/reference_lp/{safe_name}"
                    
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    
                    if url:
                        # 文字列であることを保証
                        if not isinstance(url, str) and hasattr(url, 'public_url'):
                            url = url.public_url
                        
                        # 重複チェック
                        if url and url not in remote_urls:
                            remote_urls.append(url)
                            uploaded_count += 1
                except Exception as e:
                    st.error(f"Supabaseへのアップロードに失敗しました ({uploaded_file.name}): {e}")
            
            if uploaded_count > 0:
                st.toast(f"{uploaded_count}枚の画像をクラウドに保存しました")
            
            # 保存前に重複を除去
            remote_urls = list(dict.fromkeys(remote_urls))
            product['reference_lp_image_urls'] = remote_urls
        

        if data_store.update_product(product_id, product):
            pass
        else:
            st.error("製品情報の更新に失敗しました")
        
        # 次回レンダリング時にフォームをクリアするためにキーを更新
        st.session_state.uploader_key_lp += 1


def handle_tone_upload(product_id, data_store):
    """トンマナ画像アップロード時のコールバック処理"""
    if "uploader_key_tone" not in st.session_state:
        st.session_state.uploader_key_tone = 0
        
    key = f"tone_images_{st.session_state.uploader_key_tone}"
    tone_images = st.session_state.get(key)
    
    if tone_images:
        # Supabase使用時はローカル保存を回避
        if not data_store.use_supabase:
            upload_dir = Path(f"data/uploads/{product_id}/tone_manner")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            image_paths = []
            for uploaded_file in tone_images:
                file_path = upload_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_paths.append(str(file_path))
                st.toast(f"アップロード完了: {uploaded_file.name}")
            
            product = data_store.get_product(product_id) or {}
            
            existing = product.get('tone_manner_images') or []
            for path in image_paths:
                if path not in existing:
                    existing.append(path)
            product['tone_manner_images'] = existing
        
        if data_store.use_supabase:
            product = data_store.get_product(product_id) or {} # Re-fetch product if not already fetched for Supabase
            remote_urls = product.get('tone_manner_image_urls') or []
            uploaded_count = 0
            for uploaded_file in tone_images:
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    
                    # ファイル名をサニタイズ（UUID + 拡張子）
                    ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'jpg'
                    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                    remote_path = f"{product_id}/tone_manner/{safe_name}"
                    
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    
                    if url:
                        # 文字列であることを保証
                        if not isinstance(url, str) and hasattr(url, 'public_url'):
                            url = url.public_url

                        # 重複チェック
                        if url and url not in remote_urls:
                            remote_urls.append(url)
                            uploaded_count += 1
                except Exception as e:
                    st.error(f"Supabaseへのアップロードに失敗しました ({uploaded_file.name}): {e}")
            
            if uploaded_count > 0:
                st.toast(f"{uploaded_count}枚の画像をクラウドに保存しました")
            
            # 保存前に重複を除去
            remote_urls = list(dict.fromkeys(remote_urls))
            product['tone_manner_image_urls'] = remote_urls
        
        if data_store.update_product(product_id, product):
            pass
        else:
            st.error("製品情報の更新に失敗しました")
        
        st.session_state.uploader_key_tone += 1

def render_reference_images_upload(data_store, product_id):
    '''参考画像アップロード'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">参考画像</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**参考LP画像**")
        
        # セッションステートでアップローダーのキーを管理
        if "uploader_key_lp" not in st.session_state:
            st.session_state.uploader_key_lp = 0
            
        lp_images = st.file_uploader(
            "参考LP画像をアップロードしてください",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            key=f"lp_images_{st.session_state.uploader_key_lp}",
            on_change=handle_lp_upload,
            args=(product_id, data_store)
        )

        # プリセット選択
        st.markdown("---")
        lp_presets = data_store.get_presets('reference_lp')
        lp_preset_options = ["なし"] + [p['name'] for p in lp_presets]
        selected_lp_preset = st.selectbox("プリセットから選択", lp_preset_options, key="ref_lp_preset")

        if selected_lp_preset != "なし":
            preset = next((p for p in lp_presets if p['name'] == selected_lp_preset), None)
            if preset:
                images = get_valid_image_urls(preset.get('images') or [])
                
                # プレビュー表示
                if images:
                    st.write(f"**プレビュー（{len(images)}枚）**")
                    preview_cols = st.columns(min(len(images), 5))
                    for i, img_url in enumerate(images[:5]):
                        with preview_cols[i]:
                            try:
                                st.image(img_url, width=100)
                            except:
                                st.write("⚠️ 読込エラー")
                    if len(images) > 5:
                        st.caption(f"他 {len(images) - 5} 枚...")
                
                # 適用ボタン
                if st.button("このプリセットを適用", key="apply_ref_preset", use_container_width=True):
                    product = data_store.get_product(product_id) or {}
                    product['reference_lp_image_urls'] = images
                    data_store.update_product(product_id, product)
                    st.success(f"プリセット「{selected_lp_preset}」を適用しました")
                    st.rerun()

        # プリセット管理
        if lp_presets:
            with st.expander("🗑️ プリセットを管理"):
                for p in lp_presets:
                    col_m1, col_m2 = st.columns([4, 1])
                    with col_m1:
                        st.write(f"📁 {p['name']}（{len(p.get('images', []))}枚）")
                    with col_m2:
                        if st.button("削除", key=f"del_ref_preset_{p['id']}"):
                            data_store.delete_preset_with_images(p['id'], p.get('images', []))
                            st.success(f"「{p['name']}」を削除しました")
                            st.rerun()

        # 現在の画像をプリセット保存
        current_lp_images = (data_store.get_product(product_id) or {}).get('reference_lp_image_urls') or []
        # 有効なURLのみフィルタ
        valid_lp_images = [url for url in current_lp_images if url and isinstance(url, str) and url.startswith('http')]

        if valid_lp_images:
            with st.expander("💾 現在の画像をプリセットとして保存"):
                new_lp_preset_name = st.text_input("プリセット名（必須）", key="new_ref_preset_name")
                if st.button("保存", key="save_ref_preset"):
                    if not new_lp_preset_name.strip():
                        st.error("プリセット名を入力してください")
                    else:
                        # 同名チェック
                        existing = [p for p in lp_presets if p['name'] == new_lp_preset_name.strip()]
                        if existing:
                            st.warning(f"「{new_lp_preset_name}」は既に存在します。別の名前を入力してください。")
                        else:
                            with st.spinner("画像をプリセット用フォルダにコピー中..."):
                                # プリセット用のフォルダを作成
                                preset_id_short = uuid.uuid4().hex[:12]
                                preset_folder = f"presets/{preset_id_short}"
                                
                                # 現在の画像をプリセットフォルダにコピー
                                copied_urls = []
                                for img_url in valid_lp_images:
                                    try:
                                        # 画像をダウンロード
                                        response = requests.get(img_url)
                                        if response.status_code == 200:
                                            # 新しいファイル名を生成
                                            extension = img_url.split('.')[-1].split('?')[0]
                                            if len(extension) > 5: extension = 'jpg' # 異常な拡張子対策
                                            new_filename = f"{uuid.uuid4().hex[:12]}.{extension}"
                                            new_path = f"{preset_folder}/{new_filename}"
                                            
                                            # プリセットフォルダにアップロード
                                            new_url = data_store.upload_image(
                                                response.content, 
                                                new_path, 
                                                bucket_name="lp-generator-images"
                                            )
                                            if new_url:
                                                copied_urls.append(new_url)
                                    except Exception as e:
                                        st.warning(f"画像のコピーに失敗: {e}")
                                
                                if copied_urls:
                                    # コピーしたURLでプリセットを保存
                                    data_store.save_preset(new_lp_preset_name.strip(), 'reference_lp', copied_urls)
                                    st.success(f"✅ プリセット「{new_lp_preset_name}」を保存しました！（{len(copied_urls)}枚）")
                                    st.rerun()
                                else:
                                    st.error("画像のコピーに失敗しました")

        st.markdown("---")

    
        
        # アップロード済み参考LP画像表示（クラウドURL優先）
        product = data_store.get_product(product_id)
        # URLリストとローカルパスリストを統合して表示対象にする
        display_images = []
        
        # URLがあればそれを優先
        if product and product.get("reference_lp_image_urls"):
            valid_urls = get_valid_image_urls(product["reference_lp_image_urls"])
            display_images.extend([{"type": "url", "path": url} for url in valid_urls])
        
        # Supabase未使用時のみローカルパスを表示
        if not data_store.use_supabase:
            if product and product.get("reference_lp_images"):
                for img in product["reference_lp_images"]:
                    if Path(img).exists():
                         display_images.append({"type": "local", "path": img})

        if display_images:
            st.markdown("**📁 アップロード済み:**")
            render_images_with_bulk_delete(display_images, "reference_lp", product_id, data_store)
        
        # LP分析結果表示
        from modules.trace_viewer import show_trace
        if product.get("lp_analyses"):
            st.markdown("**LP分析結果:**")
            for i, analysis in enumerate(product["lp_analyses"]):
                with st.expander(f"📄 {i+1}枚目の分析", expanded=False):
                    if isinstance(analysis, dict) and "result" in analysis:
                        from modules.trace_viewer import show_lp_analysis
                        show_lp_analysis(analysis)
                        
                        # 再分析ボタン
                        if st.button(f"🔄 再分析", key=f"reanalyze_lp_{i}"):
                            reanalyze_lp_image(product, data_store, product_id, i)
                        
                        # 編集モード
                        if st.checkbox("編集する", key=f"edit_lp_{i}"):
                            result = analysis["result"]
                            
                            # ページ種別
                            page_types = ["ファーストビュー", "機能説明", "比較表", "口コミ", "CTA", "その他"]
                            current_type = result.get("page_type", "その他")
                            idx = page_types.index(current_type) if current_type in page_types else 5
                            new_type = st.selectbox("ページ種別", page_types, index=idx, key=f"type_{i}")
                            result["page_type"] = new_type
                            
                            # テキスト要素編集
                            st.markdown("**テキスト要素**")
                            texts = result.get("texts", [])
                            for j, t in enumerate(texts):
                                cols = st.columns([2, 3, 1])
                                with cols[0]:
                                    t["type"] = st.text_input("種類", t.get("type", ""), key=f"tt_{i}_{j}")
                                with cols[1]:
                                    t["content"] = st.text_input("内容", t.get("content", ""), key=f"tc_{i}_{j}")
                                with cols[2]:
                                    if st.button("🗑️", key=f"del_t_{i}_{j}"):
                                        texts.pop(j)
                                        data_store.update_product(product_id, product)
                                        st.rerun()
                            
                            if st.button("➕ テキスト追加", key=f"add_t_{i}"):
                                texts.append({"type": "", "content": "", "char_count": 0, "position": "", "size": ""})
                                data_store.update_product(product_id, product)
                                st.rerun()
                            
                            if st.button("💾 保存", key=f"save_lp_{i}", type="primary"):
                                data_store.update_product(product_id, product)
                                st.success("保存しました")
                                st.rerun()
                        
                        show_trace(analysis, f"{i+1}枚目の生成情報")
                    else:
                        st.write(analysis)
    
    with col2:
        st.write("**トンマナ参考画像**")
        
        if "uploader_key_tone" not in st.session_state:
            st.session_state.uploader_key_tone = 0
            
        tone_images = st.file_uploader(
            "トンマナ参考画像をアップロードしてください",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            key=f"tone_images_{st.session_state.uploader_key_tone}",
            on_change=handle_tone_upload,
            args=(product_id, data_store)
        )

        # プリセット選択
        st.markdown("---")
        tm_presets = data_store.get_presets('tone_manner')
        tm_preset_options = ["なし"] + [p['name'] for p in tm_presets]
        selected_tm_preset = st.selectbox("プリセットから選択", tm_preset_options, key="tm_preset")

        if selected_tm_preset != "なし":
            preset = next((p for p in tm_presets if p['name'] == selected_tm_preset), None)
            if preset:
                images = get_valid_image_urls(preset.get('images') or [])
                
                # プレビュー表示
                if images:
                    st.write(f"**プレビュー（{len(images)}枚）**")
                    preview_cols = st.columns(min(len(images), 5))
                    for i, img_url in enumerate(images[:5]):
                        with preview_cols[i]:
                            try:
                                st.image(img_url, width=100)
                            except:
                                st.write("⚠️ 読込エラー")
                    if len(images) > 5:
                        st.caption(f"他 {len(images) - 5} 枚...")
                
                # 適用ボタン
                if st.button("このプリセットを適用", key="apply_tm_preset", use_container_width=True):
                    product = data_store.get_product(product_id) or {}
                    product['tone_manner_image_urls'] = images
                    data_store.update_product(product_id, product)
                    st.success(f"プリセット「{selected_tm_preset}」を適用しました")
                    st.rerun()

        # プリセット管理
        if tm_presets:
            with st.expander("🗑️ プリセットを管理"):
                for p in tm_presets:
                    col_tm1, col_tm2 = st.columns([4, 1])
                    with col_tm1:
                        st.write(f"📁 {p['name']}（{len(p.get('images', []))}枚）")
                    with col_tm2:
                        if st.button("削除", key=f"del_tm_preset_{p['id']}"):
                            data_store.delete_preset_with_images(p['id'], p.get('images', []))
                            st.success(f"「{p['name']}」を削除しました")
                            st.rerun()

        # 現在の画像をプリセット保存
        current_tm_images = (data_store.get_product(product_id) or {}).get('tone_manner_image_urls') or []
        # 有効なURLのみフィルタ
        valid_tm_images = [url for url in current_tm_images if url and isinstance(url, str) and url.startswith('http')]

        if valid_tm_images:
            with st.expander("💾 現在の画像をプリセットとして保存"):
                new_tm_preset_name = st.text_input("プリセット名（必須）", key="new_tm_preset_name")
                if st.button("保存", key="save_tm_preset"):
                    if not new_tm_preset_name.strip():
                        st.error("プリセット名を入力してください")
                    else:
                        # 同名チェック
                        existing = [p for p in tm_presets if p['name'] == new_tm_preset_name.strip()]
                        if existing:
                            st.warning(f"「{new_tm_preset_name}」は既に存在します。別の名前を入力してください。")
                        else:
                            with st.spinner("画像をプリセット用フォルダにコピー中..."):
                                # プリセット用のフォルダを作成
                                preset_id_short = uuid.uuid4().hex[:12]
                                preset_folder = f"presets/{preset_id_short}"
                                
                                # 現在の画像をプリセットフォルダにコピー
                                copied_urls = []
                                for img_url in valid_tm_images:
                                    try:
                                        # 画像をダウンロード
                                        response = requests.get(img_url)
                                        if response.status_code == 200:
                                            # 新しいファイル名を生成
                                            extension = img_url.split('.')[-1].split('?')[0]
                                            if len(extension) > 5: extension = 'jpg' # 異常な拡張子対策
                                            new_filename = f"{uuid.uuid4().hex[:12]}.{extension}"
                                            new_path = f"{preset_folder}/{new_filename}"
                                            
                                            # プリセットフォルダにアップロード
                                            new_url = data_store.upload_image(
                                                response.content, 
                                                new_path, 
                                                bucket_name="lp-generator-images"
                                            )
                                            if new_url:
                                                copied_urls.append(new_url)
                                    except Exception as e:
                                        st.warning(f"画像のコピーに失敗: {e}")
                                
                                if copied_urls:
                                    # コピーしたURLでプリセットを保存
                                    data_store.save_preset(new_tm_preset_name.strip(), 'tone_manner', copied_urls)
                                    st.success(f"プリセット「{new_tm_preset_name}」を保存しました！（{len(copied_urls)}枚）")
                                    st.rerun()
                                else:
                                    st.error("画像のコピーに失敗しました")

        st.markdown("---")

        
        # アップロード済みトンマナ画像表示（クラウドURL優先）
        product = data_store.get_product(product_id)
        tm_display_images = []
        
        if product and product.get("tone_manner_image_urls"):
            valid_urls = get_valid_image_urls(product["tone_manner_image_urls"])
            tm_display_images.extend([{"type": "url", "path": url} for url in valid_urls])
            
        # Supabase未使用時のみローカルを表示
        if not data_store.use_supabase:
            if product and product.get("tone_manner_images"):
                for img in product["tone_manner_images"]:
                    if Path(img).exists():
                         tm_display_images.append({"type": "local", "path": img})

        if tm_display_images:
            st.markdown("**📁 アップロード済み:**")
            render_images_with_bulk_delete(tm_display_images, "tone_manner", product_id, data_store)
        
        # トンマナ分析結果表示
        from modules.trace_viewer import show_trace
        if product and product.get("tone_manner"):
            st.markdown("**🎨 トンマナ分析結果:**")
            tone = product["tone_manner"]
            if isinstance(tone, dict) and "result" in tone:
                result = tone["result"]
                
                # カラー表示・編集
                colors = result.get("colors", {})
                if not colors: # colors辞書がない場合の初期化
                    colors = {
                        "main": tone.get("main_color", "#000000"),
                        "accent": tone.get("accent_color", "#000000"),
                        "background": tone.get("background_color", "#FFFFFF"),
                        "text": tone.get("text_color", "#000000")
                    }

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write("メイン")
                    main_color = st.color_picker("メイン色", colors.get("main", "#000000"), key="tm_main_edit", label_visibility="collapsed")
                    st.caption(main_color)
                with col2:
                    st.write("アクセント")
                    accent_color = st.color_picker("アクセント色", colors.get("accent", "#000000"), key="tm_accent_edit", label_visibility="collapsed")
                    st.caption(accent_color)
                with col3:
                    st.write("背景")
                    bg_color = st.color_picker("背景色", colors.get("background", "#FFFFFF"), key="tm_bg_edit", label_visibility="collapsed")
                    st.caption(bg_color)
                with col4:
                    st.write("テキスト")
                    text_color = st.color_picker("テキスト色", colors.get("text", "#000000"), key="tm_text_edit", label_visibility="collapsed")
                    st.caption(text_color)
                
                if st.button("🎨 カラー設定を保存", width="stretch"):
                    # 構造を維持して保存
                    new_colors = {
                        "main": main_color,
                        "accent": accent_color,
                        "background": bg_color,
                        "text": text_color
                    }
                    result["colors"] = new_colors
                    tone["result"] = result
                    
                    # トップレベルの互換性用キーも更新
                    tone["main_color"] = main_color
                    tone["accent_color"] = accent_color
                    tone["background_color"] = bg_color
                    tone["text_color"] = text_color
                    
                    product['tone_manner'] = tone
                    data_store.update_product(product_id, product)
                    st.success("カラー設定を保存しました！")
                    st.rerun()
                
                # フォント情報
                font = result.get("font", {})
                if font:
                    st.markdown(f"**フォント:** {font.get('type', '')} / {font.get('weight', '')} / {font.get('style', '')}")
                
                # 全体スタイル
                style = result.get("overall_style", {})
                if style:
                    st.markdown(f"**スタイル:** {style.get('impression', '')} / {style.get('target_gender', '')} / {style.get('target_age', '')}")
                
                show_trace(tone, "トンマナ生成情報")
            else:
                st.write(tone)
    
    
    if st.button("🎨 トンマナ画像を分析", type="primary", width="stretch"):
        product = data_store.get_product(product_id)
        
        # 画像ソースを統合（URL優先）
        tm_sources = []
        if product:
            # クラウド画像
            tm_urls = product.get("tone_manner_image_urls") or []
            tm_sources.extend(get_valid_image_urls(tm_urls))
            
            # ローカル画像（Supabase未使用時やバックアップ用）
            tm_locals = product.get("tone_manner_images") or []
            for path in tm_locals:
                if Path(path).exists() and path not in tm_sources:
                    tm_sources.append(path)
        
        if tm_sources:
            analyze_tone_manner_images(tm_sources, product_id, data_store)
        else:
            st.warning("トンマナ画像をアップロードしてください")
    # ボタンを押したら直接分析を実行
    if st.button('🔍 参考画像から構成を分析', type='primary', width="stretch", key="btn_analyze_structure"):
        import traceback
        
        st.info("分析プロセスを開始しました...")
        product = data_store.get_product(product_id)
        
        # 画像ソースの特定（URLとローカルを統合）
        urls = product.get('reference_lp_image_urls') or []
        local = product.get('reference_lp_images') or []
        
        # URL優先、ファイル名で重複排除（簡易的）
        seen_names = set()
        image_sources = []
        
        for url in urls:
            name = url.split('/')[-1].split('?')[0]
            if name not in seen_names:
                image_sources.append(url)
                seen_names.add(name)
        
        for path in local:
            name = Path(path).name
            if name not in seen_names:
                image_sources.append(path)
                seen_names.add(name)

        # デバッグ情報の表示
        with st.expander("🛠️ デバッグ情報", expanded=True):
            st.write(f"Product ID: {product_id}")
            st.write(f"Product Exists: {bool(product)}")
            st.write(f"URLs ({len(urls)}):", urls)
            st.write(f"Local ({len(local)}):", local)
            st.write(f"Final Sources ({len(image_sources)}):", image_sources)

        if not image_sources:
            st.error("❌ 分析対象の画像が見つかりません。画像をアップロードしてください。")
            st.stop()
        
        try:
            # 依存オブジェクトの初期化
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            image_analyzer = ImageAnalyzer(ai_provider, prompt_manager)
            
            # 分析実行
            st.write(f"対象画像: {len(image_sources)}枚 - 分析中...")
            analyze_reference_images(image_analyzer, image_sources, product_id, data_store)
            
        except Exception as e:
            st.error(f"分析中にエラーが発生しました: {e}")
            st.code(traceback.format_exc())


def analyze_tone_manner_images(image_paths, product_id, data_store):
    """トンマナ画像を分析（色・フォント・スタイル）"""
    from modules.trace_viewer import save_with_trace
    from modules.prompt_manager import PromptManager
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    import json
    
    with st.spinner('トンマナを分析中...'):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # 最初の1枚を代表として分析
            image_path = image_paths[0]
            prompt = prompt_manager.get_prompt("tone_manner_analysis", {})
            
            result = ai_provider.analyze_image(image_path, prompt)
            
            # JSON抽出
            try:
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0]
                parsed = json.loads(result.strip())
            except:
                parsed = {"raw": result, "parse_error": True}
            
            # 実際に使用したモデル名を取得（画像分析用）
            task_models = settings.get("task_models", {})
            used_model = task_models.get("image_analysis", settings.get("llm_model", "unknown"))
            
            traced = save_with_trace(
                result=parsed,
                prompt_id="tone_manner_analysis",
                prompt_used=prompt,
                input_refs={"画像": Path(image_path).name},
                model=used_model
            )
            
            product = data_store.get_product(product_id)
            if not product:
                product = {}
            product['tone_manner'] = traced
            data_store.update_product(product_id, product)
            
            st.success("トンマナ分析完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"分析エラー: {e}")


def reanalyze_lp_image(product, data_store, product_id, index):
    """特定のLP画像を再分析"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.trace_viewer import save_with_trace
    import base64
    import json
    
    with st.spinner(f'{index+1}枚目を再分析中...'):
        try:
            lp_images = product.get('reference_lp_images') or []
            if index >= len(lp_images):
                st.error("画像が見つかりません")
                return
            
            img_path = lp_images[index]
            
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            prompt = prompt_manager.get_prompt("lp_image_analysis", {})
            
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            
            result = ai_provider.ask(prompt, "lp_image_analysis", images=[img_data])
            
            if isinstance(result, str):
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("```")[1]
                    if result.startswith("json"):
                        result = result[4:]
                result = json.loads(result)
            
            # 実際に使用したモデル名を取得
            task_models = settings.get("task_models", {})
            used_model = task_models.get("image_analysis", settings.get("llm_model", "unknown"))
            
            traced = save_with_trace(
                result=result,
                prompt_id="lp_image_analysis",
                prompt_used=prompt,
                input_refs={"画像": img_path},
                model=used_model
            )
            
            # 更新
            lp_analyses = product.get('lp_analyses') or []
            while len(lp_analyses) <= index:
                lp_analyses.append({})
            lp_analyses[index] = traced
            product['lp_analyses'] = lp_analyses
            data_store.update_product(product_id, product)
            
            st.success("再分析完了！")
            st.rerun()
            
        except Exception as e:
            st.error(f"再分析エラー: {e}")

def analyze_reference_images(image_analyzer, image_paths, product_id, data_store):
    """参考LP画像を1枚ずつ詳細分析"""
    from modules.trace_viewer import save_with_trace
    from modules.prompt_manager import PromptManager
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    import json
    
    with st.spinner('参考LP画像を分析中...'):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # 既存の分析結果を取得
            product = data_store.get_product(product_id)
            existing_analyses = (product.get('lp_analyses_dict') or {}) if product else {}
            
            analyses = []
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            for i, image_path in enumerate(image_paths):
                file_name = image_path.split('/')[-1].split('?')[0] if image_path.startswith('http') else Path(image_path).name
                
                # 既に分析済みならスキップ
                if file_name in existing_analyses:
                    st.write(f"✅ 分析済み（スキップ）: {file_name}")
                    analyses.append(existing_analyses[file_name])
                    progress_bar.progress((i + 1) / len(image_paths))
                    continue

                status_text.text(f"分析中: {i+1}/{len(image_paths)}枚目... ({file_name})")
                progress_bar.progress((i) / len(image_paths))
                
                # パスによる存在確認（URLでない、かつローカルファイルが存在しない場合）
                if not image_path.startswith("http") and not os.path.exists(image_path):
                    st.error(f"画像ファイルが見つかりません: {Path(image_path).name}")
                    st.warning("クラウド環境では過去のアップロードファイルが保持されない場合があります。お手数ですが、再度画像をアップロードし直してください。")
                    continue
                
                try:
                    # プロンプト取得
                    prompt = prompt_manager.get_prompt("lp_image_analysis", {})
                    
                    target_path = image_path
                    is_temp = False
                    
                    # URLの場合は一時ファイルにダウンロード
                    if image_path.startswith("http"):
                        try:
                            import requests
                            import tempfile
                            
                            response = requests.get(image_path, timeout=30)
                            if response.status_code == 200:
                                suffix = "." + image_path.split("/")[-1].split("?")[0].split(".")[-1]
                                if len(suffix) > 5 or "/" in suffix: # 拡張子取得失敗時のフォールバック
                                    suffix = ".jpg"
                                    
                                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                    tmp.write(response.content)
                                    target_path = tmp.name
                                    is_temp = True
                            else:
                                st.warning(f"画像ダウンロード失敗（Status {response.status_code}）: {file_name}")
                                continue
                        except Exception as dl_err:
                            st.warning(f"画像ダウンロードエラー: {dl_err}")
                            continue

                    # 画像分析（Vision API）
                    # 画像分析（Vision API）
                    result = ai_provider.analyze_image(target_path, prompt)
                    
                    # 一時ファイルの削除
                    if is_temp and os.path.exists(target_path):
                        try:
                            os.unlink(target_path)
                        except:
                            pass

                    # 結果チェック
                    if not result:
                        st.warning(f"画像分析に失敗しました（結果なし）: {file_name}")
                        continue
                    
                    # JSON抽出
                    try:
                        if "```json" in result:
                            result = result.split("```json")[1].split("```")[0]
                        elif "```" in result:
                            result = result.split("```")[1].split("```")[0]
                        parsed = json.loads(result.strip())
                    except Exception as e:
                        st.warning(f"JSON解析エラー: {file_name} - {e}")
                        parsed = {"raw": result, "parse_error": True}
                    
                    # トレース付きで保存
                    traced = save_with_trace(
                        result=parsed,
                        prompt_id="lp_image_analysis",
                        prompt_used=prompt,
                        input_refs={"画像": Path(image_path).name, "順番": i+1},
                        model=settings.get("llm_model", "unknown")
                    )
                    
                    # メモリ上のリストに追加
                    analyses.append(traced)
                    
                    # 【重要】1枚ごとに即時保存
                    product = data_store.get_product(product_id)
                    if product is None:
                        product = {}

                    current_dict = product.get('lp_analyses_dict') or {}
                    if current_dict is None:
                        current_dict = {}

                    current_dict[file_name] = traced
                    
                    product['lp_analyses_dict'] = current_dict
                    product['lp_analyses'] = list(current_dict.values())
                    
                    if data_store.update_product(product_id, product):
                         existing_analyses[file_name] = traced # ループ内キャッシュも更新
                    else:
                         # 保存失敗時もエラーを出さず続行（ログ出力等は検討）
                         pass
                         
                except Exception as e:
                    st.warning(f"画像分析スキップ（{Path(image_path).name}）: {e}")
                    # エラー時も一時ファイルがあれば削除
                    if 'is_temp' in locals() and is_temp and 'target_path' in locals() and os.path.exists(target_path):
                        try:
                            os.unlink(target_path)
                        except:
                            pass

            # 最終的な完了処理
            st.session_state.processing_reference_analysis = False
            st.success(f"全{len(image_paths)}枚の処理が完了しました")
            st.rerun()
                
        except Exception as e:
            st.session_state.processing_reference_analysis = False
            st.error(f"分析エラー: {e}")

# ページ実行
render_input_page()
