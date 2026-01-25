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


from modules.data_store import DataStore
from modules.file_parser import FileParser
from modules.image_analyzer import ImageAnalyzer
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.settings_manager import SettingsManager
import os
from pathlib import Path
import base64

def render_input_page():
    '''入力情報ページのメイン関数'''
    st.title('📥 入力情報')
    
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
    
    # 各セクションをレンダリング
    render_product_images_upload(data_store, product_id)
    render_competitor_analysis(data_store, product_id)
    render_sheets_upload(data_store, product_id)
    render_reference_images_upload(data_store, product_id)

def render_product_images_upload(data_store, product_id):
    '''製品画像アップロード'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">📷 製品画像</div>', unsafe_allow_html=True)
    
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
        for uploaded_file in uploaded_files:
            file_path = upload_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(str(file_path))  # 絶対パスとして保存
            st.success(f"アップロード完了: {uploaded_file.name}")
        
        # データを更新
        product = data_store.get_product(product_id)
        if not product:
            product = {}
        
        # 既存リストとマージ
        existing_images = product.get('product_images', [])
        for path in image_paths:
            if path not in existing_images:
                existing_images.append(path)
        product['product_images'] = existing_images
        
        # Supabaseへアップロード
        if data_store.use_supabase:
            remote_urls = product.get('product_image_urls', [])
            # 今回アップロードされたファイルをSync
            for uploaded_file in uploaded_files:
                try:
                    # ファイルポインタを戻す
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    remote_path = f"{product_id}/product_images/{uploaded_file.name}"
                    
                    # アップロード試行
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    
                    if url:
                        if url not in remote_urls:
                            remote_urls.append(url)
                            st.toast(f"クラウド保存完了: {uploaded_file.name}", icon="☁️")
                    else:
                        st.error(f"アップロード失敗: URLが取得できませんでした ({uploaded_file.name})")
                        
                except Exception as e:
                    st.error(f"Upload failed for {uploaded_file.name}: {e}")
            
            product['product_image_urls'] = remote_urls

        # データベース更新
        if data_store.update_product(product_id, product):
            st.success("製品情報を更新しました")
        else:
            st.error("データベースの更新に失敗しました")
    
    # アップロード済み画像を表示
    product = data_store.get_product(product_id)
    
    
    # Supabase Storage URLを優先して表示（Streamlit Cloud対応）
    image_urls = product.get("product_image_urls", []) if product else []
    local_images = product.get("product_images", []) if product else []
    
    if image_urls:
        st.markdown("**📁 アップロード済み画像 (クラウド):**")
        cols = st.columns(4)
        for i, img_url in enumerate(image_urls):
            with cols[i % 4]:
                # 画像表示（失敗しても警告のみ）
                try:
                    st.image(img_url, caption=f"Image {i+1}", width="stretch")
                except Exception as e:
                    st.warning(f"読込失敗: {e}")
                
                # 削除ボタンは常に表示
                if st.button("🗑️", key=f"del_prod_img_url_{i}"):
                    if img_url in product.get("product_image_urls", []):
                        product["product_image_urls"].remove(img_url)
                        data_store.update_product(product_id, product)
                        st.rerun()

    elif local_images:
        # フォールバック：ローカルファイル（ローカル開発時用）
        st.markdown("**📁 アップロード済み画像 (ローカル):**")
        cols = st.columns(4)
        for i, img_path in enumerate(local_images):
            with cols[i % 4]:
                resolved_path = Path(img_path)
                if not resolved_path.is_absolute():
                    resolved_path = Path.cwd() / img_path
                
                if resolved_path.exists():
                    st.image(str(resolved_path), caption=resolved_path.name, width="stretch")
                else:
                    st.warning(f"ファイルなし: {img_path}")
                
                # 削除ボタンは常に表示
                if st.button("🗑️", key=f"del_prod_img_{i}"):
                    if img_path in product.get("product_images", []):
                        product["product_images"].remove(img_path)
                        data_store.update_product(product_id, product)
                        st.rerun()


def save_competitor_data(product_id, data_store):
    """入力中の競合データをDBに保存（分析前の一時保存）"""
    product = data_store.get_product(product_id) or {}
    current_data = product.get("competitor_analysis_v2", {})
    competitors = current_data.get("competitors", [])
    
    # セッションステートからデータを収集して更新
    count = st.session_state.get("competitor_count", 1)
    
    # 既存リストと新しいカウントの整合性を取る
    new_competitors = []
    for i in range(count):
        # 既存データがあれば引き継ぐ
        comp_data = competitors[i] if i < len(competitors) else {}
        
        # セッションの最新値で上書き
        comp_data["name"] = st.session_state.get(f"comp_name_{i}", f"競合{i+1}")
        comp_data["text"] = st.session_state.get(f"comp_text_{i}", "")
        comp_data["files"] = st.session_state.get(f"comp_files_paths_{i}", [])
        
        new_competitors.append(comp_data)
            
    current_data["competitors"] = new_competitors
    product["competitor_analysis_v2"] = current_data
    if data_store.update_product(product_id, product):
        st.toast("競合情報を保存しました", icon="💾")

def render_competitor_analysis(data_store, product_id):
    '''競合情報分析セクション'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">🔍 競合情報</div>', unsafe_allow_html=True)
    st.caption("競合ごとに画像・テキストをアップロード → 訴求要素を自動抽出")
    
    # セッション初期化（保存データがあれば復元）
    if "competitor_count" not in st.session_state:
        # DBから保存済みデータを取得
        product = data_store.get_product(product_id)
        saved_competitors = []
        if product and "competitor_analysis_v2" in product:
            saved_competitors = product["competitor_analysis_v2"].get("competitors", [])
        
        if saved_competitors:
            st.session_state.competitor_count = len(saved_competitors)
            for i, comp in enumerate(saved_competitors):
                st.session_state[f"comp_name_{i}"] = comp.get("name", f"競合{i+1}")
                st.session_state[f"comp_text_{i}"] = comp.get("text", "")
                
                # ファイルパスの復元（注意: ローカルパスなので環境またぎでは見えないが、同一環境なら見える）
                if "files" in comp:
                    st.session_state[f"comp_files_paths_{i}"] = comp["files"]
        else:
            st.session_state.competitor_count = 1
    
    # 競合追加ボタン
    col_add, col_space = st.columns([1, 3])
    with col_add:
        if st.button("➕ 競合を追加", key="add_competitor"):
            if st.session_state.competitor_count < 10:
                st.session_state.competitor_count += 1
                st.rerun()
            else:
                st.warning("最大10社までです")
    
    st.markdown("---")
    
    # 各競合の入力エリア
    for i in range(st.session_state.competitor_count):
        with st.expander(f"🏢 競合{i+1}", expanded=False):
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
                on_change=save_competitor_data,
                args=(product_id, data_store)
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📁 画像（最大30枚）**")
                
                # 保存済みファイルを確認
                saved_dir = Path(f"data/uploads/{product_id}/competitors/comp_{i}")
                saved_files = []
                if saved_dir.exists():
                    saved_files = list(saved_dir.glob("*.jpg")) + list(saved_dir.glob("*.jpeg")) + list(saved_dir.glob("*.png"))
                    saved_files = [str(f) for f in saved_files]
                
                uploaded_files = st.file_uploader(
                    "LP画像をアップロード",
                    type=['png', 'jpg', 'jpeg'],
                    accept_multiple_files=True,
                    key=f"comp_files_{i}",
                    label_visibility="collapsed"
                )
                
                if uploaded_files:
                    if len(uploaded_files) > 30:
                        st.warning("最大30枚までです")
                        uploaded_files = uploaded_files[:30]
                    
                    upload_dir = Path(f"data/uploads/{product_id}/competitors/comp_{i}")
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    
                    file_paths = []
                    for uf in uploaded_files:
                        file_path = upload_dir / uf.name
                        with open(file_path, "wb") as f:
                            f.write(uf.getbuffer())
                        file_paths.append(str(file_path))
                    
                    st.success(f"{len(file_paths)}枚アップロード済み")
                    st.session_state[f"comp_files_paths_{i}"] = file_paths
                    saved_files = file_paths  # 新規アップロード優先
                
                # 保存済み or 新規アップロードを表示
                if saved_files:
                    st.session_state[f"comp_files_paths_{i}"] = saved_files
                    st.caption(f"📷 {len(saved_files)}枚")
                    preview_cols = st.columns(6)
                    for idx, fp in enumerate(saved_files[:6]):
                        with preview_cols[idx % 6]:
                            st.image(fp, width=80)
                    if len(saved_files) > 6:
                        st.caption(f"他 {len(saved_files) - 6}枚")
            
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
                    on_change=save_competitor_data,
                    args=(product_id, data_store)
                )
    
    st.markdown("---")
    
    # 一括分析ボタン
    if st.button("🔍 一括分析", type="primary", width="stretch", key="analyze_all_competitors"):
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
    
    with st.spinner("キーワード重要度を分析中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # シートデータを文字列化
            sheet_data = product.get("review_sheet_data", {})
            raw_text = ""
            if isinstance(sheet_data, dict):
                data_type = sheet_data.get("type", "")
                sheet_content = sheet_data.get("content", "")
                
                if data_type in ["pdf", "text"]:
                    raw_text = str(sheet_content)
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
            
            prompt = prompt_manager.get_prompt("keyword_organize", {
                "raw_data": raw_text[:3000]
            })
            
            result = ai_provider.ask(prompt, "keyword_organize")
            
            traced = save_with_trace(
                result=result,
                prompt_id="keyword_organize",
                prompt_used=prompt,
                input_refs={"ファイル": product.get("review_sheet", "")},
                model=settings.get("llm_model", "unknown")
            )
            
            product["keyword_organized"] = result
            product["keyword_organize_trace"] = traced
            data_store.update_product(product_id, product)
            
            st.success("キーワード分析完了！")
            st.rerun()
            
        except Exception as e:
            st.error(f"分析エラー: {e}")


def organize_sheet_data(product, data_store, product_id):
    """シートデータをAIで整理"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.trace_viewer import save_with_trace
    
    with st.spinner("シート内容を整理中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # シートデータを文字列化
            sheet_data = product.get("product_sheet_data", {})
            raw_text = ""
            if isinstance(sheet_data, dict):
                data_type = sheet_data.get("type", "")
                content = sheet_data.get("content", "")
                
                if data_type in ["pdf", "text"]:
                    # PDF/テキストはそのまま
                    raw_text = str(content)
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
            
            prompt = prompt_manager.get_prompt("sheet_organize", {
                "raw_data": raw_text[:3000]
            })
            
            result = ai_provider.ask(prompt, "sheet_organize")
            
            # トレース付きで保存
            traced = save_with_trace(
                result=result,
                prompt_id="sheet_organize",
                prompt_used=prompt,
                input_refs={"ファイル": product.get("product_sheet", "")},
                model=settings.get("llm_model", "unknown")
            )
            
            product["product_sheet_organized"] = result
            product["product_sheet_organize_trace"] = traced
            data_store.update_product(product_id, product)
            
            st.success("整理完了！")
            st.rerun()
            
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
            comp_text = st.session_state.get(f"comp_text_{i}", "")
            
            if file_paths or comp_text.strip():
                targets.append({
                    "name": comp_name,
                    "files": file_paths,
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
    st.markdown('<div class="step-header">📊 分析結果</div>', unsafe_allow_html=True)
    
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
        st.subheader("🏆 全競合の訴求要素まとめ")
        
        total = summary.get("total_competitors", 1)
        
        for elem, count in summary["element_ranking"]:
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
            st.toast("製品シート情報を保存しました", icon="💾")

def save_keyword_sheet(product_id, data_store):
    product = data_store.get_product(product_id)
    if product and "edit_keyword" in st.session_state:
        product["keyword_organized"] = st.session_state.edit_keyword
        if data_store.update_product(product_id, product):
            st.toast("キーワード情報を保存しました", icon="💾")

def render_sheets_upload(data_store, product_id):
    '''各種シートアップロード'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">📄 データシート</div>', unsafe_allow_html=True)
    
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
                if st.button("🗑️", key="del_product_sheet", help="削除"):
                    product['product_sheet'] = None
                    product['product_sheet_data'] = None
                    product['product_sheet_organized'] = None
                    data_store.update_product(product_id, product)
                    st.rerun()
            
            # 整理済みデータがあれば表示
            organized = product.get("product_sheet_organized", "")
            if organized:
                st.success("✅ 整理済み")
                with st.expander("📋 整理済み内容を確認・編集", expanded=False):
                    edited = st.text_area("内容", value=organized, height=300, key="edit_organized", on_change=save_product_sheet, args=(product_id, data_store))
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("💾 変更を保存", key="save_organized"):
                            product["product_sheet_organized"] = edited
                            data_store.update_product(product_id, product)
                            st.success("保存しました")
                            st.rerun()
                    with col_b:
                        if st.button("🔄 再整理（AI）", key="reorganize_sheet"):
                            organize_sheet_data(product, data_store, product_id)
            else:
                # 整理ボタン
                if st.button("📋 内容を整理（AI）", key="organize_sheet"):
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
                if st.button("🗑️", key="del_review_sheet", help="削除"):
                    product['review_sheet'] = None
                    product['review_sheet_data'] = None
                    product['keyword_organized'] = None
                    data_store.update_product(product_id, product)
                    st.rerun()
            
            # キーワード整理済みデータがあれば表示
            keyword_org = product.get("keyword_organized", "")
            if keyword_org:
                st.success("✅ キーワード整理済み")
                with st.expander("📊 キーワード重要度（確認・編集）", expanded=False):
                    edited = st.text_area("内容", value=keyword_org, height=300, key="edit_keyword", on_change=save_keyword_sheet, args=(product_id, data_store))
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("💾 保存", key="save_keyword"):
                            product["keyword_organized"] = edited
                            data_store.update_product(product_id, product)
                            st.success("保存しました")
                            st.rerun()
                    with col_b:
                        if st.button("🔄 再分析", key="reanalyze_keyword"):
                            organize_keyword_data(product, data_store, product_id)
            else:
                if st.button("📊 キーワード重要度を分析", key="analyze_keyword"):
                    organize_keyword_data(product, data_store, product_id)



def handle_lp_upload(product_id, data_store):
    """参考LP画像アップロード時のコールバック処理"""
    if "uploader_key_lp" not in st.session_state:
        st.session_state.uploader_key_lp = 0
    
    key = f"lp_images_{st.session_state.uploader_key_lp}"
    lp_images = st.session_state.get(key)
    
    if lp_images:
        upload_dir = Path(f"data/uploads/{product_id}/reference_lp")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        image_paths = []
        for uploaded_file in lp_images:
            file_path = upload_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(str(file_path))
            # コールバック内でのst.success等は次回レンダリング時に消える可能性があるためtoastを使用
            st.toast(f"アップロード完了: {uploaded_file.name}")
        
        # 最新の製品情報を取得
        product = data_store.get_product(product_id) or {}
        
        # 既存の画像リストに追加
        existing = product.get('reference_lp_images', [])
        for path in image_paths:
            if path not in existing:
                existing.append(path)
        product['reference_lp_images'] = existing
        
        # Supabaseへアップロード
        if data_store.use_supabase:
            remote_urls = product.get('reference_lp_image_urls', [])
            for uploaded_file in lp_images:
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    remote_path = f"{product_id}/reference_lp/{uploaded_file.name}"
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    if url and url not in remote_urls:
                        remote_urls.append(url)
                except Exception as e:
                    print(f"Ref Upload failed: {e}")
            product['reference_lp_image_urls'] = remote_urls

        data_store.update_product(product_id, product)
        
        # 次回レンダリング時にフォームをクリアするためにキーを更新
        st.session_state.uploader_key_lp += 1


def handle_tone_upload(product_id, data_store):
    """トンマナ画像アップロード時のコールバック処理"""
    if "uploader_key_tone" not in st.session_state:
        st.session_state.uploader_key_tone = 0
        
    key = f"tone_images_{st.session_state.uploader_key_tone}"
    tone_images = st.session_state.get(key)
    
    if tone_images:
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
        
        existing = product.get('tone_manner_images', [])
        for path in image_paths:
            if path not in existing:
                existing.append(path)
        product['tone_manner_images'] = existing
        
        if data_store.use_supabase:
            remote_urls = product.get('tone_manner_image_urls', [])
            for uploaded_file in tone_images:
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    remote_path = f"{product_id}/tone_manner/{uploaded_file.name}"
                    url = data_store.upload_image(file_bytes, remote_path, bucket_name="lp-generator-images")
                    if url and url not in remote_urls:
                        remote_urls.append(url)
                except Exception as e:
                    print(f"Tone Upload failed: {e}")
            product['tone_manner_image_urls'] = remote_urls
        
        data_store.update_product(product_id, product)
        
        st.session_state.uploader_key_tone += 1

def render_reference_images_upload(data_store, product_id):
    '''参考画像アップロード'''
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">🖼️ 参考画像</div>', unsafe_allow_html=True)
    
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

    
        
        # アップロード済み参考LP画像表示（クラウドURL優先）
        product = data_store.get_product(product_id)
        # URLリストとローカルパスリストを統合して表示対象にする
        display_images = []
        
        # URLがあればそれを優先
        if product and product.get("reference_lp_image_urls"):
            display_images.extend([{"type": "url", "path": url} for url in product["reference_lp_image_urls"]])
        
        # ローカルパスも（URLに含まれていないものがあれば）
        if product and product.get("reference_lp_images"):
            # URLのファイル名と比較して重複を除く簡易ロジック
            url_filenames = [u.split("/")[-1] for u in product.get("reference_lp_image_urls", [])]
            for img in product["reference_lp_images"]:
                if Path(img).name not in url_filenames and Path(img).exists():
                     display_images.append({"type": "local", "path": img})

        if display_images:
            st.markdown("**📁 アップロード済み:**")
            cols = st.columns(4)
            for i, img_info in enumerate(display_images):
                with cols[i % 4]:
                    img_path = img_info["path"]
                    caption_text = Path(img_path).name if img_info["type"] == "local" else img_path.split('/')[-1].split('?')[0]
                    
                    # 画像表示（失敗してもエラー表示のみ）
                    try:
                        st.image(img_path, caption=caption_text, width=100)
                    except Exception as e:
                        st.warning(f"読込失敗: {caption_text}")
                    
                    # 削除ボタンは常に表示（画像表示の成否に関わらず）
                    if st.button("🗑️", key=f"del_lp_{i}"):
                        # 最新の製品情報を再取得して削除処理を行う
                        current_product = data_store.get_product(product_id) or {}
                        target_filename = caption_text
                        
                        # URLリストから削除
                        if "reference_lp_image_urls" in current_product:
                            current_product["reference_lp_image_urls"] = [
                                u for u in current_product["reference_lp_image_urls"] 
                                if u.split('/')[-1].split('?')[0] != target_filename
                            ]
                        
                        # ローカルリストから削除
                        if "reference_lp_images" in current_product:
                            current_product["reference_lp_images"] = [
                                p for p in current_product["reference_lp_images"] 
                                if Path(p).name != target_filename
                            ]
                        
                        data_store.update_product(product_id, current_product)
                        st.rerun()
        
        # LP分析結果表示
        from modules.trace_viewer import show_trace
        if product.get("lp_analyses"):
            st.markdown("**📊 LP分析結果:**")
            for i, analysis in enumerate(product["lp_analyses"]):
                with st.expander(f"📄 {i+1}枚目の分析", expanded=False):
                    if isinstance(analysis, dict) and "result" in analysis:
                        from modules.trace_viewer import show_lp_analysis
                        show_lp_analysis(analysis)
                        
                        # 再分析ボタン
                        if st.button(f"🔄 再分析", key=f"reanalyze_lp_{i}"):
                            reanalyze_lp_image(product, data_store, product_id, i)
                        
                        # 編集モード
                        if st.checkbox(f"✏️ 編集する", key=f"edit_lp_{i}"):
                            result = analysis["result"]
                            
                            # ページ種別
                            page_types = ["ファーストビュー", "機能説明", "比較表", "口コミ", "CTA", "その他"]
                            current_type = result.get("page_type", "その他")
                            idx = page_types.index(current_type) if current_type in page_types else 5
                            new_type = st.selectbox("ページ種別", page_types, index=idx, key=f"type_{i}")
                            result["page_type"] = new_type
                            
                            # テキスト要素編集
                            st.markdown("**📝 テキスト要素**")
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

        
        # アップロード済みトンマナ画像表示（クラウドURL優先）
        product = data_store.get_product(product_id)
        tm_display_images = []
        
        if product and product.get("tone_manner_image_urls"):
            tm_display_images.extend([{"type": "url", "path": url} for url in product["tone_manner_image_urls"]])
            
        if product and product.get("tone_manner_images"):
            url_filenames = [u.split("/")[-1] for u in product.get("tone_manner_image_urls", [])]
            for img in product["tone_manner_images"]:
                if Path(img).name not in url_filenames and Path(img).exists():
                     tm_display_images.append({"type": "local", "path": img})

        if tm_display_images:
            st.markdown("**📁 アップロード済み:**")
            cols = st.columns(4)
            for i, img_info in enumerate(tm_display_images):
                with cols[i % 4]:
                    img_path = img_info["path"]
                    caption_text = Path(img_path).name if img_info["type"] == "local" else img_path.split('/')[-1].split('?')[0]
                    
                    # 画像表示（失敗してもエラー表示のみ）
                    try:
                        st.image(img_path, caption=caption_text, width=100)
                    except Exception as e:
                        st.warning(f"読込失敗: {caption_text}")
                    
                    # 削除ボタンは常に表示（画像表示の成否に関わらず）
                    if st.button("🗑️", key=f"del_tone_{i}"):
                        # 最新の製品情報を再取得して削除処理を行う
                        current_product = data_store.get_product(product_id) or {}
                        target_filename = caption_text
                        
                        if "tone_manner_image_urls" in current_product:
                            current_product["tone_manner_image_urls"] = [
                                u for u in current_product["tone_manner_image_urls"] 
                                if u.split('/')[-1].split('?')[0] != target_filename
                            ]
                            
                        if "tone_manner_images" in current_product:
                            current_product["tone_manner_images"] = [
                                p for p in current_product["tone_manner_images"] 
                                if Path(p).name != target_filename
                            ]
                            
                        data_store.update_product(product_id, current_product)
                        st.rerun()
        
        # トンマナ分析結果表示
        from modules.trace_viewer import show_trace
        if product and product.get("tone_manner"):
            st.markdown("**🎨 トンマナ分析結果:**")
            tone = product["tone_manner"]
            if isinstance(tone, dict) and "result" in tone:
                result = tone["result"]
                
                # カラー表示
                colors = result.get("colors", {})
                if colors:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.color_picker("メイン", colors.get("main", "#000000"), disabled=True, key="tm_main")
                        st.caption(colors.get("main", ""))
                    with col2:
                        st.color_picker("アクセント", colors.get("accent", "#000000"), disabled=True, key="tm_accent")
                        st.caption(colors.get("accent", ""))
                    with col3:
                        st.color_picker("背景", colors.get("background", "#FFFFFF"), disabled=True, key="tm_bg")
                        st.caption(colors.get("background", ""))
                    with col4:
                        st.color_picker("テキスト", colors.get("text", "#000000"), disabled=True, key="tm_text")
                        st.caption(colors.get("text", ""))
                
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
        if product and product.get("tone_manner_images"):
            analyze_tone_manner_images(product["tone_manner_images"], product_id, data_store)
        else:
            st.warning("トンマナ画像をアップロードしてください")
    # ボタンを押したら直接分析を実行
    if st.button('🔍 参考画像から構成を分析', type='primary', width="stretch", key="btn_analyze_structure"):
        import traceback
        
        st.info("分析プロセスを開始しました...")
        product = data_store.get_product(product_id)
        
        # 画像ソースの特定（URLとローカルを統合）
        urls = product.get('reference_lp_image_urls', [])
        local = product.get('reference_lp_images', [])
        
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
            lp_images = product.get('reference_lp_images', [])
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
            existing_analyses = product.get('lp_analyses_dict', {}) if product else {}
            
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

                    current_dict = product.get('lp_analyses_dict')
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
