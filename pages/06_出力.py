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

require_product()

from modules.data_store import DataStore
from modules.output_generator import OutputGenerator
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.settings_manager import SettingsManager
from pathlib import Path

def get_element_guide(elem_type):
    """要素タイプごとの説明と入力例を返す"""
    guides = {
        'ソーシャルプルーフ': {
            'description': '実績や信頼性を示す情報（販売数、メディア掲載、レビュー評価など）',
            'example': '累計販売10万個突破 / Amazon評価★4.5 / 雑誌○○掲載'
        },
        '権威付け': {
            'description': '品質や安全性を保証する情報（認証、資格、監修など）',
            'example': '日本製 / ISO認証取得 / 専門家監修 / 特許取得'
        },
        'トラストバッジ': {
            'description': '信頼を示すマークや保証',
            'example': '30日間返金保証 / 送料無料 / 公式ストア限定'
        },
        'メインキャッチコピー': {
            'description': '最も伝えたい一言（短く印象的に）',
            'example': '驚きの吸着力 / これ1枚で安心'
        },
        'リードコピー': {
            'description': 'メインキャッチの補足・導入',
            'example': '毎日の暮らしに安心を / 大切な食器を守る'
        },
        'タグライン': {
            'description': 'ブランドや商品のスローガン',
            'example': '○○（ブランド名） - 暮らしを支える'
        }
    }
    return guides.get(elem_type)

def detect_content_issues(parsed, lp_analyses, reference_page):
    """コンテンツの問題点を検出"""
    issues = []
    elements = parsed.get('elements', []) if isinstance(parsed, dict) else []
    
    # 1. （未確定）を含む要素を検出
    for i, elem in enumerate(elements):
        elem_type = elem.get('type', '')
        content = elem.get('content', '')
        items = elem.get('items', [])
        
        if '（未確定）' in str(content) or '入力してください' in str(content):
            issues.append({
                'id': f'undecided_{i}',
                'type': '未確定項目',
                'element_index': i,
                'element_type': elem_type,
                'message': f'{elem_type}に未確定の内容があります',
                'suggestions': ['手動で入力', 'この要素をスキップ', '製品情報から自動補完']
            })
        
        # itemsの中にも未確定があるかチェック
        for j, item in enumerate(items):
            if '（未確定）' in str(item):
                issues.append({
                    'id': f'undecided_{i}_{j}',
                    'type': '未確定項目',
                    'element_index': i,
                    'item_index': j,
                    'element_type': elem_type,
                    'message': f'{elem_type}の項目{j+1}に未確定の内容があります',
                    'suggestions': ['手動で入力', 'この項目を削除']
                })
    
    # 2. 参照LPとの要素数比較
    if lp_analyses and reference_page <= len(lp_analyses):
        ref_analysis = lp_analyses[reference_page - 1]
        if isinstance(ref_analysis, dict) and 'result' in ref_analysis:
            ref_result = ref_analysis['result']
            ref_elements = ref_result.get('elements', [])
            
            if len(elements) != len(ref_elements):
                issues.append({
                    'id': 'element_count',
                    'type': '要素数の不一致',
                    'message': f'参照LP: {len(ref_elements)}要素 → 生成: {len(elements)}要素',
                    'suggestions': ['そのまま続行', '再生成する']
                })
    
    # 3. 重複する内容の検出
    contents = [elem.get('content', '') for elem in elements if elem.get('content')]
    seen = set()
    for i, c in enumerate(contents):
        if c and len(c) > 5:  # 短すぎるものは除外
            # 部分一致チェック
            for seen_content in seen:
                if c in seen_content or seen_content in c:
                    issues.append({
                        'id': f'duplicate_{i}',
                        'type': '重複の可能性',
                        'message': f'類似した内容が複数あります: "{c[:20]}..."',
                        'suggestions': ['そのまま続行', '内容を変更']
                    })
                    break
            seen.add(c)
    
    return issues

def apply_fix(parsed, issue, new_value, page_contents, page_id, data_store, product_id, product_data):
    """修正を適用"""
    elements = parsed.get('elements', [])
    elem_idx = issue.get('element_index')
    item_idx = issue.get('item_index')
    
    if elem_idx is not None and elem_idx < len(elements):
        if item_idx is not None:
            # items内の修正
            items = elements[elem_idx].get('items', [])
            if item_idx < len(items):
                items[item_idx] = new_value
        else:
            # content自体の修正
            elements[elem_idx]['content'] = new_value
        
        # 保存
        page_contents[page_id]['result']['parsed'] = parsed
        product_data['page_contents'] = page_contents
        data_store.update_product(product_id, product_data)
        st.success("修正を適用しました")
        st.rerun()



def render_output_page():
    st.title('📤 出力')
    
    data_store = DataStore()
    product_id = st.session_state["current_product_id"]
    settings_manager = SettingsManager()
    settings = settings_manager.get_settings()
    ai_provider = AIProvider(settings)
    prompt_manager = PromptManager()
    
    output_generator = OutputGenerator(
        ai_provider=ai_provider,
        prompt_manager=prompt_manager
    )
    
    product_data = data_store.get_product(product_id)
    
    if not product_data:
        st.warning("商品データが入力されていません。")
        return
    
    tab1, tab2, tab3 = st.tabs(["🖼️ LP画像生成", "📋 指示書", "📥 ダウンロード"])
    
    with tab1:
        render_lp_generation_section(output_generator, ai_provider, prompt_manager, product_data, data_store, product_id, settings)
    
    with tab2:
        render_design_instruction_section(output_generator, product_data)
    
    with tab3:
        render_download_section(output_generator, product_data)

def render_lp_generation_section(output_generator, ai_provider, prompt_manager, product_data, data_store, product_id, settings):
    st.markdown('<div class="step-header">🖼️ LP画像生成</div>', unsafe_allow_html=True)
    
    # 必要データの確認
    tone_manner = output_generator.get_tone_manner(product_data)
    lp_analyses = product_data.get('lp_analyses', [])
    page_contents = product_data.get('page_contents', {})
    structure = product_data.get('structure', {})
    if isinstance(structure, dict) and 'result' in structure:
        structure = structure['result']
    pages = structure.get('pages', []) if isinstance(structure, dict) else []
    
    # ステータス表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("参照LP", f"{len(lp_analyses)}枚")
    with col2:
        st.metric("トンマナ", "✓" if tone_manner else "未設定")
    with col3:
        st.metric("コンテンツ", f"{len(page_contents)}ページ")
    
    if not page_contents:
        st.warning("ページ詳細でコンテンツを生成してください")
        return
    
    # トンマナ表示
    if tone_manner:
        with st.expander("🎨 トンマナ設定", expanded=False):
            colors = tone_manner.get('colors', {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.color_picker("メイン", colors.get('main', '#000000'), disabled=True, key="out_main")
            with col2:
                st.color_picker("アクセント", colors.get('accent', '#000000'), disabled=True, key="out_accent")
            with col3:
                st.color_picker("背景", colors.get('background', '#FFFFFF'), disabled=True, key="out_bg")
            with col4:
                st.color_picker("テキスト", colors.get('text', '#000000'), disabled=True, key="out_text")
    
    st.divider()
    
    # ページごとに生成
    generated_lp_images = product_data.get('generated_lp_images', {})
    
    for page in pages:
        page_id = page.get('id', 'unknown')
        page_title = page.get('title', '無題')
        page_order = page.get('order', 1)
        reference_page = page.get('reference_page', 1)
        
        # ページヘッダー
        st.markdown(f"---")
        st.markdown(f"## P{page_order}: {page_title}")
        
        # コンテンツ取得
        content_data = page_contents.get(page_id, {})
        if isinstance(content_data, dict) and 'result' in content_data:
            result = content_data['result']
            if isinstance(result, dict):
                parsed = result.get('parsed', result)
                display = result.get('display', '')
            else:
                parsed = {}
                display = str(result)
        else:
            parsed = {}
            display = ""
        
        # 参照LP画像パス
        ref_image_path = None
        if lp_analyses and reference_page <= len(lp_analyses):
            ref_images = product_data.get('reference_lp_images', [])
            if ref_images and reference_page <= len(ref_images):
                ref_image_path = ref_images[reference_page - 1]
        
        # ========== 決定事項・参照情報セクション ==========
        with st.expander("📋 決定事項・参照情報", expanded=True):
            info_col1, info_col2 = st.columns([2, 1])
            
            with info_col1:
                # コンテンツ表示
                st.markdown("**📝 コンテンツ**")
                if display:
                    st.text_area("", value=display[:500], height=150, disabled=True, key=f"content_{page_id}")
                    
                    # 問題検出
                    issues = detect_content_issues(parsed, lp_analyses, reference_page)
                    if issues:
                        with st.expander(f"⚠️ {len(issues)}件の確認事項", expanded=True):
                            for issue in issues:
                                elem_type = issue.get('element_type', '')
                                guide = get_element_guide(elem_type)
                                st.warning(f"**{issue['type']}**: {issue['message']}")
                                if guide:
                                    st.caption(f"💡 {guide['description']}")
                                if issue.get('suggestions'):
                                    selected = st.selectbox(
                                        "対応策", issue['suggestions'],
                                        key=f"fix_{page_id}_{issue['id']}"
                                    )
                                    if selected == "手動で入力":
                                        placeholder = guide.get('example', '') if guide else ''
                                        new_val = st.text_input("入力", placeholder=placeholder, key=f"input_{page_id}_{issue['id']}")
                                        if new_val and st.button("適用", key=f"apply_{page_id}_{issue['id']}"):
                                            apply_fix(parsed, issue, new_val, page_contents, page_id, data_store, product_id, product_data)
                else:
                    st.info("コンテンツ未生成 → ページ詳細で生成してください")
                
                # 画像生成プロンプト（編集可能）
                st.markdown("**🎨 画像生成プロンプト**")
                custom_prompts = product_data.get('custom_prompts', {})
                current_custom = custom_prompts.get(page_id, {}).get('image_prompt', '')
                
                # デフォルトプロンプトを生成
                default_prompt = build_image_prompt(prompt_manager, page, parsed, tone_manner)
                
                prompt_to_show = current_custom if current_custom else default_prompt
                edited_prompt = st.text_area(
                    "プロンプトを編集可能",
                    value=prompt_to_show,
                    height=120,
                    key=f"edit_prompt_{page_id}"
                )
                
                prompt_col1, prompt_col2 = st.columns(2)
                with prompt_col1:
                    if st.button("💾 プロンプト保存", key=f"save_prompt_{page_id}"):
                        if 'custom_prompts' not in product_data:
                            product_data['custom_prompts'] = {}
                        product_data['custom_prompts'][page_id] = {
                            'image_prompt': edited_prompt,
                            'is_custom': True
                        }
                        data_store.update_product(product_id, product_data)
                        st.success("保存しました")
                with prompt_col2:
                    if current_custom:
                        if st.button("↩️ デフォルトに戻す", key=f"reset_prompt_{page_id}"):
                            product_data['custom_prompts'].pop(page_id, None)
                            data_store.update_product(product_id, product_data)
                            st.rerun()
            
            with info_col2:
                # 参照LP
                if ref_image_path and Path(ref_image_path).exists():
                    st.markdown("**📷 参照LP**")
                    st.image(ref_image_path, width="stretch")
                
                # トーンマナー簡易表示
                if tone_manner:
                    st.markdown("**🎨 トーンマナー**")
                    st.caption(f"メイン: {tone_manner.get('main_color', 'N/A')}")
                    st.caption(f"フォント: {tone_manner.get('font', 'N/A')}")
        
        # ========== パターン一覧セクション ==========
        st.markdown("**🖼️ 生成パターン**")
        
        versions_data = product_data.get('generated_versions', {}).get(page_id, {})
        versions = versions_data.get('versions', [])
        
        if versions:
            for v_idx, version in enumerate(versions):
                v_id = version.get('id', '')
                v_path = version.get('path', '')
                v_created = version.get('created_at', '')
                is_selected = version.get('is_selected', False)
                
                # パターンカード
                pattern_label = f"⭐ パターン {v_idx + 1} （採用中）" if is_selected else f"☆ パターン {v_idx + 1}"
                with st.container():
                    st.markdown(f"#### {pattern_label}")
                    st.caption(f"生成日時: {v_created}")
                    
                    img_col, btn_col = st.columns([3, 1])
                    
                    with img_col:
                        if v_path and Path(v_path).exists():
                            st.image(v_path, width="stretch")
                        else:
                            st.warning("画像ファイルが見つかりません")
                    
                    with btn_col:
                        # 再生成ボタン
                        if st.button("🔄 再生成", key=f"regen_{page_id}_{v_id}", width="stretch"):
                            # カスタムプロンプトがあれば使用
                            custom_prompt = product_data.get('custom_prompts', {}).get(page_id, {}).get('image_prompt')
                            regenerate_pattern(
                                ai_provider, product_data, data_store, product_id,
                                page_id, v_id, page, parsed, tone_manner, ref_image_path,
                                prompt_manager, custom_prompt
                            )
                        
                        # 採用ボタン
                        if not is_selected:
                            if st.button("⭐ 採用", key=f"select_{page_id}_{v_id}", width="stretch"):
                                for v in versions:
                                    v['is_selected'] = (v['id'] == v_id)
                                versions_data['selected'] = v_id
                                if 'generated_lp_images' not in product_data:
                                    product_data['generated_lp_images'] = {}
                                product_data['generated_lp_images'][page_id] = v_path
                                data_store.update_product(product_id, product_data)
                                st.rerun()
                        
                        # プロンプト確認
                        if st.button("🔍 プロンプト", key=f"view_prompt_{page_id}_{v_id}", width="stretch"):
                            st.session_state[f'show_prompt_{page_id}_{v_id}'] = True
                        
                        # 削除ボタン
                        if st.button("🗑️ 削除", key=f"delete_{page_id}_{v_id}", width="stretch"):
                            versions.remove(version)
                            if is_selected and versions:
                                versions[0]['is_selected'] = True
                                versions_data['selected'] = versions[0]['id']
                                product_data['generated_lp_images'][page_id] = versions[0]['path']
                            elif not versions:
                                product_data.get('generated_lp_images', {}).pop(page_id, None)
                            data_store.update_product(product_id, product_data)
                            st.rerun()
                    
                    # プロンプト表示（トグル）
                    if st.session_state.get(f'show_prompt_{page_id}_{v_id}'):
                        with st.expander("使用したプロンプト", expanded=True):
                            st.code(version.get('prompt', 'プロンプト情報なし'), language=None)
                            if st.button("閉じる", key=f"close_prompt_{page_id}_{v_id}"):
                                st.session_state[f'show_prompt_{page_id}_{v_id}'] = False
                                st.rerun()
                    
                    st.divider()
        else:
            st.info("まだパターンがありません")
        
        # 新規パターン追加
        new_pattern_key = f"new_pattern_{page_id}"
        
        # 新規パターン作成モード
        if st.session_state.get(new_pattern_key):
            st.markdown("#### ➕ 新規パターン作成")
            
            # デフォルトプロンプトを取得
            default_prompt = build_image_prompt(prompt_manager, page, parsed, tone_manner)
            custom_prompts = product_data.get('custom_prompts', {})
            base_prompt = custom_prompts.get(page_id, {}).get('image_prompt', default_prompt)
            
            # プロンプト編集エリア
            new_pattern_prompt = st.text_area(
                "このパターン用のプロンプト（編集可能）",
                value=base_prompt,
                height=150,
                key=f"new_pattern_prompt_{page_id}"
            )
            
            np_col1, np_col2, np_col3 = st.columns([2, 2, 1])
            with np_col1:
                if st.button("🚀 生成開始", key=f"start_gen_{page_id}", width="stretch", type="primary"):
                    st.session_state[new_pattern_key] = False
                    generate_lp_page(
                        ai_provider, prompt_manager,
                        page, parsed, tone_manner, ref_image_path,
                        product_data, data_store, product_id,
                        custom_prompt=new_pattern_prompt
                    )
            with np_col2:
                if st.button("🗑️ キャンセル", key=f"cancel_new_{page_id}", width="stretch"):
                    st.session_state[new_pattern_key] = False
                    st.rerun()
            with np_col3:
                if st.button("💰", key=f"cost_{page_id}", help="直前の生成コスト"):
                    if 'last_api_usage' in st.session_state and st.session_state.last_api_usage:
                        u = st.session_state.last_api_usage
                        st.toast(f"入力: {u.get('input_tokens', 0):,} / 出力: {u.get('output_tokens', 0):,} / ¥{u.get('cost_jpy', 0):.2f}")
                    else:
                        st.toast("まだ生成していません")
        else:
            # 新規パターン追加ボタン
            add_col1, add_col2, add_col3 = st.columns([2, 1, 1])
            with add_col1:
                if st.button("➕ 新規パターン追加", key=f"add_pattern_{page_id}", width="stretch"):
                    st.session_state[new_pattern_key] = True
                    st.rerun()
            with add_col3:
                if st.button("💰", key=f"cost2_{page_id}", help="直前の生成コスト"):
                    if 'last_api_usage' in st.session_state and st.session_state.last_api_usage:
                        u = st.session_state.last_api_usage
                        st.toast(f"入力: {u.get('input_tokens', 0):,} / 出力: {u.get('output_tokens', 0):,} / ¥{u.get('cost_jpy', 0):.2f}")
                    else:
                        st.toast("まだ生成していません")

def build_image_prompt(prompt_manager, page, parsed_content, tone_manner):
    """画像生成用のデフォルトプロンプトを構築"""
    # コンテンツテキストを構築
    content_lines = []
    elements = parsed_content.get('elements', []) if isinstance(parsed_content, dict) else []
    
    for elem in elements:
        elem_type = elem.get('type', '')
        elem_content = elem.get('content', '')
        items = elem.get('items', [])
        description = elem.get('description', '')
        char_count = elem.get('char_count', '')
        
        if items:
            content_lines.append(f"【{elem_type}】{len(items)}項目")
            for item in items:
                content_lines.append(f"  - {item}")
        elif description:
            content_lines.append(f"【{elem_type}】{description}")
        elif elem_content:
            char_str = f"（{char_count}文字）" if char_count else ""
            content_lines.append(f"【{elem_type}】{elem_content} {char_str}")
        else:
            content_lines.append(f"【{elem_type}】")
    
    content_text = '\n'.join(content_lines)
    
    # トンマナ情報
    colors = tone_manner.get('colors', {}) if tone_manner else {}
    font = tone_manner.get('font', {}) if tone_manner else {}
    style = tone_manner.get('overall_style', {}) if tone_manner else {}
    
    # レイアウト指示
    layout_instructions = []
    for elem in elements:
        elem_type = elem.get('type', '')
        layout = elem.get('layout', '')
        if layout:
            layout_instructions.append(f"{elem_type}: {layout}")
    
    prompt = prompt_manager.get_prompt("lp_image_generation", {
        "main_color": colors.get('main', '#68A949'),
        "accent_color": colors.get('accent', '#FFB911'),
        "background_color": colors.get('background', '#FFFFFF'),
        "text_color": colors.get('text', '#181950'),
        "font_type": font.get('type', '丸ゴシック'),
        "font_weight": font.get('weight', '太い'),
        "impression": style.get('impression', 'カジュアル'),
        "content_text": content_text,
        "layout_instructions": '\n'.join(layout_instructions) if layout_instructions else "参照画像のレイアウトに従う"
    })
    
    return prompt


def regenerate_pattern(ai_provider, product_data, data_store, product_id, page_id, version_id, page, parsed_content, tone_manner, ref_image_path, prompt_manager, custom_prompt=None):
    """既存パターンを再生成（上書き）"""
    import uuid
    from datetime import datetime
    
    with st.spinner("再生成中..."):
        try:
            # プロンプト生成
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = build_image_prompt(prompt_manager, page, parsed_content, tone_manner)
            
            # 画像生成
            result = ai_provider.generate_image(prompt, reference_image_path=ref_image_path)
            
            if result and 'path' in result:
                # 既存バージョンを更新
                versions_data = product_data.get('generated_versions', {}).get(page_id, {})
                versions = versions_data.get('versions', [])
                
                for v in versions:
                    if v['id'] == version_id:
                        v['path'] = result['path']
                        v['prompt'] = prompt
                        v['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 選択中なら generated_lp_images も更新
                        if v.get('is_selected'):
                            if 'generated_lp_images' not in product_data:
                                product_data['generated_lp_images'] = {}
                            product_data['generated_lp_images'][page_id] = result['path']
                        break
                
                data_store.update_product(product_id, product_data)
                st.success("再生成完了！")
                st.rerun()
            else:
                st.error(f"生成失敗: {result.get('error', '不明なエラー')}")
        
        except Exception as e:
            st.error(f"エラー: {e}")


def show_generation_prompt(prompt_manager, page, parsed_content, tone_manner):
    """生成プロンプトを表示"""
    # コンテンツテキストを構築
    content_lines = []
    elements = parsed_content.get('elements', []) if isinstance(parsed_content, dict) else []
    
    for elem in elements:
        elem_type = elem.get('type', '')
        elem_content = elem.get('content', '')
        items = elem.get('items', [])
        description = elem.get('description', '')
        char_count = elem.get('char_count', '')
        
        # 汎用処理（要素タイプに依存しない）
        if items:
            content_lines.append(f"【{elem_type}】{len(items)}項目")
            for item in items:
                content_lines.append(f"  - {item}")
        elif description:
            content_lines.append(f"【{elem_type}】{description}")
        elif elem_content:
            char_str = f"（{char_count}文字）" if char_count else ""
            content_lines.append(f"【{elem_type}】{elem_content} {char_str}")
        else:
            content_lines.append(f"【{elem_type}】")
    
    content_text = '\n'.join(content_lines)
    
    # トンマナ情報
    colors = tone_manner.get('colors', {}) if tone_manner else {}
    font = tone_manner.get('font', {}) if tone_manner else {}
    style = tone_manner.get('overall_style', {}) if tone_manner else {}
    
    # レイアウト指示
    layout_instructions = []
    for elem in elements:
        elem_type = elem.get('type', '')
        layout = elem.get('layout', '')
        if layout:
            layout_instructions.append(f"{elem_type}: {layout}")
    
    # プロンプト生成
    prompt = prompt_manager.get_prompt("lp_image_generation", {
        "main_color": colors.get('main', '#68A949'),
        "accent_color": colors.get('accent', '#FFB911'),
        "background_color": colors.get('background', '#FFFFFF'),
        "text_color": colors.get('text', '#181950'),
        "font_type": font.get('type', '丸ゴシック'),
        "font_weight": font.get('weight', '太い'),
        "impression": style.get('impression', 'カジュアル'),
        "content_text": content_text,
        "layout_instructions": '\n'.join(layout_instructions) if layout_instructions else "参照画像のレイアウトに従う"
    })
    
    st.info(f"📝 P{page.get('order', 1)} 生成プロンプト")
    st.code(prompt, language=None)

def generate_lp_page(ai_provider, prompt_manager, page, parsed_content, tone_manner, ref_image_path, product_data, data_store, product_id, variation_of=None, custom_prompt=None):
    """LP1ページを画像生成"""
    with st.spinner(f"P{page.get('order', 1)} を生成中..."):
        try:
            # コンテンツテキストを構築
            content_lines = []
            elements = parsed_content.get('elements', []) if isinstance(parsed_content, dict) else []
            
            for elem in elements:
                elem_type = elem.get('type', '')
                elem_content = elem.get('content', '')
                items = elem.get('items', [])
                description = elem.get('description', '')
                char_count = elem.get('char_count', '')
                
                # 汎用処理（要素タイプに依存しない）
                if items:
                    content_lines.append(f"【{elem_type}】{len(items)}項目")
                    for item in items:
                        content_lines.append(f"  - {item}")
                elif description:
                    content_lines.append(f"【{elem_type}】{description}")
                elif elem_content:
                    char_str = f"（{char_count}文字）" if char_count else ""
                    content_lines.append(f"【{elem_type}】{elem_content} {char_str}")
                else:
                    content_lines.append(f"【{elem_type}】")
            
            content_text = '\n'.join(content_lines)
            
            # トンマナ情報
            colors = tone_manner.get('colors', {}) if tone_manner else {}
            font = tone_manner.get('font', {}) if tone_manner else {}
            style = tone_manner.get('overall_style', {}) if tone_manner else {}
            
            # レイアウト指示を構築
            layout_instructions = []
            for elem in elements:
                elem_type = elem.get('type', '')
                layout = elem.get('layout', '')
                if layout:
                    layout_instructions.append(f"{elem_type}: {layout}")
            
            # プロンプト生成
            # カスタムプロンプトがあれば使用、なければ自動生成
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = prompt_manager.get_prompt("lp_image_generation", {
                    "main_color": colors.get('main', '#68A949'),
                    "accent_color": colors.get('accent', '#FFB911'),
                    "background_color": colors.get('background', '#FFFFFF'),
                    "text_color": colors.get('text', '#181950'),
                    "font_type": font.get('type', '丸ゴシック'),
                    "font_weight": font.get('weight', '太い'),
                    "impression": style.get('impression', 'カジュアル'),
                    "content_text": content_text,
                    "layout_instructions": '\n'.join(layout_instructions) if layout_instructions else "参照画像のレイアウトに従う"
                })
            
            # 画像生成
            result = ai_provider.generate_image(prompt, reference_image_path=ref_image_path)
            
            if result and 'path' in result:
                import uuid
                from datetime import datetime
                
                page_id = page.get('id', f"page_{page.get('order', 1)}")
                
                # 複数バージョン対応のデータ構造
                if 'generated_versions' not in product_data:
                    product_data['generated_versions'] = {}
                if page_id not in product_data['generated_versions']:
                    product_data['generated_versions'][page_id] = {"versions": [], "selected": None}
                
                # 新しいバージョンを追加
                version_id = f"v_{uuid.uuid4().hex[:8]}"
                new_version = {
                    "id": version_id,
                    "path": result['path'],
                    "prompt": prompt,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "is_selected": False,
                    "variation_of": variation_of
                }
                product_data['generated_versions'][page_id]['versions'].append(new_version)
                
                # 最初のバージョンは自動選択
                if len(product_data['generated_versions'][page_id]['versions']) == 1:
                    new_version['is_selected'] = True
                    product_data['generated_versions'][page_id]['selected'] = version_id
                
                # 旧形式との互換性のため、選択中の画像をgenerated_lp_imagesにも保存
                if 'generated_lp_images' not in product_data:
                    product_data['generated_lp_images'] = {}
                product_data['generated_lp_images'][page_id] = result['path']
                
                data_store.update_product(product_id, product_data)
                st.success("生成完了！")
                st.rerun()
            else:
                st.error(f"生成失敗: {result.get('error', '不明なエラー')}")
        
        except Exception as e:
            st.error(f"エラー: {e}")

def render_design_instruction_section(output_generator, product_data):
    st.markdown('<div class="step-header">📋 デザイナー向け指示書</div>', unsafe_allow_html=True)
    
    instr_col1, instr_col2 = st.columns([6, 1])
    with instr_col1:
        instr_clicked = st.button("📝 指示書を生成", width="stretch")
    with instr_col2:
        if st.button("💰", key="cost_instruction", help="直前の生成コスト"):
            if 'last_api_usage' in st.session_state and st.session_state.last_api_usage:
                u = st.session_state.last_api_usage
                st.toast(f"入力: {u.get('input_tokens', 0):,} / 出力: {u.get('output_tokens', 0):,} / ¥{u.get('cost_jpy', 0):.2f}")
            else:
                st.toast("まだ生成していません")
    if instr_clicked:
        instruction = output_generator.generate_design_instruction(product_data)
        st.session_state['generated_instruction'] = instruction
    
    if 'generated_instruction' in st.session_state:
        st.text_area(
            "指示書プレビュー",
            value=st.session_state['generated_instruction'],
            height=400
        )

def render_download_section(output_generator, product_data):
    st.markdown('<div class="step-header">📥 ダウンロード</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'generated_instruction' in st.session_state:
            st.download_button(
                "📋 指示書 (TXT)",
                data=st.session_state['generated_instruction'],
                file_name=f"{product_data.get('name', 'product')}_instruction.txt",
                mime="text/plain",
                width="stretch"
            )
        else:
            st.info("指示書を生成してください")
    
    with col2:
        generated_lp_images = product_data.get('generated_lp_images', {})
        image_count = len(generated_lp_images)
        if image_count > 0:
            st.info(f"生成済みLP画像: {image_count}枚")
        else:
            st.info("LP画像を生成してください")

render_output_page()

