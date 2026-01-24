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
from modules.page_generator import PageGenerator
from modules.ai_provider import AIProvider
from modules.settings_manager import SettingsManager
from modules.prompt_manager import PromptManager
from modules.element_types import ElementTypes

st.title('📄 ページ詳細')

data_store = DataStore()
product_id = st.session_state['current_product_id']
product = data_store.get_product(product_id)

if not product:
    st.error("製品データが見つかりません")
    st.stop()

# 構成データ取得（トレース形式対応）
raw_structure = product.get('structure', {})
if isinstance(raw_structure, dict) and "result" in raw_structure:
    structure = raw_structure["result"]
else:
    structure = raw_structure
pages = structure.get('pages', []) if isinstance(structure, dict) else []

if not pages:
    st.warning("ページ構成がまだ設定されていません。「全体構成」ページで構成を生成してください。")
    if st.button("全体構成へ移動"):
        st.switch_page("pages/04_全体構成.py")
    st.stop()

# ページ選択
pages_sorted = sorted(pages, key=lambda x: x.get('order', 0))
page_options = {f"P{p.get('order', '?')} - {p.get('title', '未設定')}": p for p in pages_sorted}

selected_page_name = st.selectbox("編集するページを選択", list(page_options.keys()))
selected_page = page_options[selected_page_name]
page_id = selected_page.get('id', 'unknown')

st.markdown("---")

# ページ情報表示

# 詳細生成ボタン
btn_c1, btn_c2 = st.columns([6, 1])
with btn_c1:
    gen_content = st.button("🤖 AIでコンテンツ生成", type="primary", use_container_width=True)
with btn_c2:
    if st.button("💰", key="cost_content", help="直前の生成コスト"):
        if 'last_api_usage' in st.session_state and st.session_state.last_api_usage:
            u = st.session_state.last_api_usage
            st.toast(f"入力: {u.get('input_tokens', 0):,} / 出力: {u.get('output_tokens', 0):,} / ¥{u.get('cost_jpy', 0):.2f}")
        else:
            st.toast("まだ生成していません")
if gen_content:
    with st.spinner("コンテンツを生成中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # LP分析結果を取得（新形式対応）
            lp_analyses = product.get('lp_analyses', [])
            ref_page = selected_page.get('reference_page', 1)
            lp_analysis = ""
            output_format = ""
            element_num = 1
            if ref_page and ref_page <= len(lp_analyses):
                analysis = lp_analyses[ref_page - 1]
                if isinstance(analysis, dict) and "result" in analysis:
                    result = analysis["result"]
                    # 新形式（elements）と旧形式（texts）両対応
                    elements = result.get("elements", result.get("texts", []))
                    for elem in elements:
                        elem_type = elem.get('element_type', elem.get('type', ''))
                        aim = elem.get('aim', '')
                        effect = elem.get('effect', '')
                        items = elem.get('items', [])
                        item_count = elem.get('item_count', len(items) if items else 0)
                        char_count = elem.get('char_count', 20)
                        char_per_item = elem.get('char_per_item', '')
                        layout = elem.get('layout', '')
                        has_icon = elem.get('has_icon', False)
                        
                        min_chars = max(5, int(char_count * 0.7))
                        max_chars = int(char_count * 1.3)
                        
                        lp_analysis += f"\n{element_num}. [{elem_type}]"
                        if item_count > 0:
                            lp_analysis += f" {item_count}項目"
                            if char_per_item:
                                lp_analysis += f"（各{char_per_item}）"
                        else:
                            lp_analysis += f" {min_chars}-{max_chars}文字"
                        if layout:
                            lp_analysis += f" [{layout}]"
                        if has_icon:
                            lp_analysis += f" [アイコン有]"
                        lp_analysis += f"\n   狙い: {aim} → 効果: {effect}"
                        
                        # 出力形式を生成
                        if ElementTypes().is_multiple_items(elem_type) or items:
                            char_info = f"各{char_per_item}文字程度" if char_per_item else ""
                            layout_info = f" {layout}" if layout else ""
                            output_format += f"\n## 要素{element_num}: {elem_type}（{item_count}項目{layout_info}）{char_info}\n"
                            for i in range(item_count):
                                char_hint = f"（約{char_per_item}文字）" if char_per_item else ""
                                output_format += f"- 項目{i+1}: {char_hint}\n"
                        else:
                            output_format += f"\n## 要素{element_num}: {elem_type}（{min_chars}-{max_chars}文字）\n（ここに{elem_type}を記入）\n"
                        element_num += 1
            
            # トンマナ取得
            tone = product.get('tone_manner', {})
            tone_str = ""
            if isinstance(tone, dict) and "result" in tone:
                t = tone["result"]
                tone_str = f"スタイル: {t.get('overall_style', {}).get('impression', '')}"
            
            # 整理済み製品情報を取得
            organized_info = product.get('product_sheet_organized', '')
            product_info = f"製品名: {product.get('name', '')}\n説明: {product.get('description', '')}"
            if organized_info:
                product_info += f"\n\n【整理済み製品情報】\n{organized_info[:1000]}"
            
            # 訴求ポイントを取得
            appeals = selected_page.get('appeals', [])
            appeals_str = ', '.join(appeals) if appeals else "未設定"
            
            # プロンプトを取得
            prompt = prompt_manager.get_prompt("page_detail_generation", {
                "page_title": selected_page.get('title', ''),
                "page_summary": selected_page.get('summary', selected_page.get('role', '')),
                "page_elements": appeals_str,
                "lp_analysis": lp_analysis if lp_analysis else "なし",
                "output_format": output_format if output_format else "",
                "tone_manner": tone_str if tone_str else "未設定",
                "product_info": product_info
            })
            
            result = ai_provider.ask(prompt, "page_content")
            
            # JSON形式の場合はパース
            import json as json_module
            parsed_content = result
            display_content = result
            
            try:
                if "```json" in result:
                    json_str = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    json_str = result.split("```")[1].split("```")[0]
                else:
                    json_str = result
                
                parsed = json_module.loads(json_str.strip())
                parsed_content = parsed
                
                # 表示用にMarkdown形式に変換
                display_lines = []
                for elem in parsed.get("elements", []):
                    elem_type = elem.get("type", "")
                    order = elem.get("order", "")
                    display_lines.append(f"## 要素{order}: {elem_type}")
                    
                    if elem_type in ["表", "チェックリスト"]:
                        items = elem.get("items", [])
                        for i, item in enumerate(items, 1):
                            display_lines.append(f"- 項目{i}: {item}")
                    elif elem_type == "画像":
                        display_lines.append(f"（画像指示）{elem.get('description', '')}")
                    elif elem_type == "矢印":
                        display_lines.append(f"{elem.get('content', '↓')}")
                    else:
                        display_lines.append(f"{elem.get('content', '')}")
                        char_count = elem.get("char_count", "")
                        if char_count:
                            display_lines.append(f"（{char_count}文字）")
                    display_lines.append("")
                
                display_content = "\n".join(display_lines)
            except:
                pass
            
            # トレース付きで保存
            from modules.trace_viewer import save_with_trace
            traced = save_with_trace(
                result={"parsed": parsed_content, "display": display_content},
                prompt_id="page_detail_generation",
                prompt_used=prompt,
                input_refs={
                    "ページ": selected_page.get('title', ''),
                    "製品名": product.get('name', '')
                },
                model=settings.get("llm_model", "unknown")
            )
            
            if 'page_contents' not in product:
                product['page_contents'] = {}
            product['page_contents'][page_id] = traced
            data_store.update_product(product_id, product)
            st.success("生成完了！")
            st.rerun()
            
        except Exception as e:
            st.error(f"生成エラー: {e}")

st.markdown("---")

from modules.trace_viewer import show_trace
page_contents = product.get("page_contents", {})
raw_detail = page_contents.get(page_id, {})
if isinstance(raw_detail, dict) and "result" in raw_detail:
    result_data = raw_detail["result"]
    # 新形式（parsed/display）か旧形式かを判定
    if isinstance(result_data, dict) and "display" in result_data:
        page_content = result_data["display"]
    else:
        page_content = result_data
    show_trace(raw_detail, "コンテンツ生成の生成情報")
else:
    page_content = raw_detail.get("content", "") if isinstance(raw_detail, dict) else ""
st.markdown('<div class="step-header">✏️ コンテンツ編集</div>', unsafe_allow_html=True)

# parsed構造を取得
parsed_data = None
if isinstance(raw_detail, dict) and "result" in raw_detail:
    result_data = raw_detail["result"]
    if isinstance(result_data, dict) and "parsed" in result_data:
        parsed_data = result_data["parsed"]

if parsed_data and isinstance(parsed_data, dict) and "elements" in parsed_data:
    elements = parsed_data.get("elements", [])
    
    # テキスト要素とビジュアル要素を分離
    text_elements = []
    visual_elements = []
    for elem in elements:
        elem_type = elem.get("type", "")
        if elem_type in ["メインビジュアル", "サブビジュアル", "画像"]:
            visual_elements.append(elem)
        else:
            text_elements.append(elem)
    
    # テキスト要素の編集
    if text_elements:
        st.markdown("**📝 テキスト要素**")
        elem_types = ElementTypes()
        for i, elem in enumerate(text_elements):
            elem_type = elem.get("type", f"要素{i+1}")
            items = elem.get("items", [])
            elem_content = elem.get("content", "")
            char_count = elem.get("char_count", "")
            
            # items形式（ブレット、キーワード群など）
            if items or elem_types.is_multiple_items(elem_type):
                st.markdown(f"**{elem_type}**")
                item_count = elem.get("item_count", len(items))
                char_per_item = elem.get("char_per_item", "")
                if char_per_item:
                    st.caption(f"{item_count}項目 / 各約{char_per_item}文字")
                else:
                    st.caption(f"{item_count}項目")
                
                new_items = []
                for j, item in enumerate(items):
                    new_item = st.text_input(
                        f"項目{j+1}",
                        value=item,
                        key=f"item_{page_id}_{i}_{j}",
                        label_visibility="collapsed"
                    )
                    new_items.append(new_item)
                
                if new_items != items:
                    elem["items"] = new_items
                    elem["item_count"] = len(new_items)
            else:
                # 単一テキスト形式
                col1, col2 = st.columns([4, 1])
                with col1:
                    new_content = st.text_input(
                        f"{elem_type}",
                        value=elem_content,
                        key=f"text_elem_{page_id}_{i}"
                    )
                with col2:
                    if char_count:
                        st.caption(f"{char_count}文字")
                    else:
                        st.caption(f"{len(new_content)}文字")
                
                if new_content != elem_content:
                    elem["content"] = new_content
                    elem["char_count"] = len(new_content)

# ビジュアル要素の編集
if visual_elements:
    st.markdown("**🖼️ ビジュアル指示**")
    for i, elem in enumerate(visual_elements):
        elem_type = elem.get("type", f"ビジュアル{i+1}")
        description = elem.get("description", elem.get("content", ""))
        
        new_desc = st.text_area(
            f"{elem_type}",
            value=description,
            height=80,
            key=f"visual_elem_{page_id}_{i}"
        )
        
        if new_desc != description:
            elem["description"] = new_desc

# 保存ボタン
if st.button("💾 保存", use_container_width=True, key="save_parsed", type="primary"):
    if 'page_contents' not in product:
        product['page_contents'] = {}
    
    # 既存のトレース情報を維持して更新
    if page_id in product['page_contents'] and isinstance(product['page_contents'][page_id], dict):
        existing = product['page_contents'][page_id]
        if "result" in existing:
            existing["result"]["parsed"] = parsed_data
            # displayも更新
            display_lines = []
            for elem in parsed_data.get("elements", []):
                elem_type = elem.get("type", "")
                order = elem.get("order", "")
                display_lines.append(f"## 要素{order}: {elem_type}")
                if elem_type in ["メインビジュアル", "サブビジュアル", "画像"]:
                    display_lines.append(f"（画像指示）{elem.get('description', '')}")
                else:
                    display_lines.append(f"{elem.get('content', '')}")
                    char_count = elem.get("char_count", "")
                    if char_count:
                        display_lines.append(f"（{char_count}文字）")
                display_lines.append("")
            existing["result"]["display"] = "\n".join(display_lines)
        product['page_contents'][page_id] = existing
    
    data_store.update_product(product_id, product)
    st.success("保存しました！")
    st.rerun()

elif page_content and not parsed_data:
    # 旧形式の場合のみテキストエリアで編集（parsed構造がない場合）
    content = st.text_area(
        "生成されたコンテンツ",
        value=page_content,
        height=300,
        key=f"content_{page_id}"
    )
    
    if st.button("💾 保存", use_container_width=True, key="save_legacy", type="primary"):
        if 'page_contents' not in product:
            product['page_contents'] = {}
        product['page_contents'][page_id] = {
            'content': content,
            'generated': True
        }
        data_store.update_product(product_id, product)
        st.success("保存しました！")
else:
    st.info("上の「AIでコンテンツ生成」ボタンでコンテンツを生成してください")

