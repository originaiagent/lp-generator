import streamlit as st
from modules.styles import apply_styles, page_header
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(page_title="Page Details", layout="wide")

# スタイル適用
apply_styles()

# AIサイドバー表示
render_ai_sidebar()


import os
from modules.page_guard import require_product

require_product()

from modules.data_store import DataStore
from modules.page_generator import PageGenerator
from modules.ai_provider import AIProvider
from modules.settings_manager import SettingsManager
from modules.prompt_manager import PromptManager
from modules.element_types import ElementTypes

def generate_page_content(product_id, product, selected_page):
    """
    指定されたページのコンテンツをAIで生成し、DBを更新する
    """
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.element_types import ElementTypes
    import json as json_module
    from modules.trace_viewer import save_with_trace
    
    page_id = selected_page.get('id', 'unknown')
    data_store = DataStore()

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
    return True

def clear_brushup_state():
    """ブラッシュアップ関連のセッション状態をクリア"""
    for k in ['brushup_target', 'brushup_original', 'brushup_candidates', 'brushup_direction', 'brushup_phase']:
        if k in st.session_state:
            del st.session_state[k]

def generate_brushup_query(original_text, product, direction=None):
    """AIにブラッシュアップ案を依頼"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    import json as json_module

    settings = SettingsManager().get_settings()
    ai_provider = AIProvider(settings)
    prompt_manager = PromptManager()
    
    product_info = f"製品名: {product.get('name', '')}\n説明: {product.get('description', '')}"
    
    if not direction:
        instruction = "以下の3つの方向性で、それぞれブラッシュアップ案を1つずつ提案してください。\n\nインパクト重視: 目を引く、記憶に残る表現\n信頼感重視: 安心感、品質の高さを感じる表現\n簡潔・シンプル: 無駄を削ぎ落とした本質的な表現"
    else:
        instruction = f"「{direction}」の方向性で、さらに3つのバリエーションを提案してください。それぞれ異なるアプローチで、選択肢を広げてください。"
    
    prompt = prompt_manager.get_prompt("brushup_copy", {
        "original_text": original_text,
        "product_info": product_info,
        "instruction": instruction
    })
    
    result = ai_provider.ask(prompt, "brushup_copy")
    
    try:
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            json_str = result.split("```")[1].split("```")[0]
        else:
            json_str = result
        
        parsed = json_module.loads(json_str.strip())
        return parsed.get("candidates", [])
    except Exception as e:
        st.error(f"AI提案のパースに失敗しました: {e}")
        return []

page_header("Page Details", "各ページの詳細なコピーと構成の作成")

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

# 一括生成ボタン
st.markdown("### 一括操作")
if st.button("全ページを一括生成", type="primary", use_container_width=True):
    progress_bar = st.progress(0)
    for i, page in enumerate(pages_sorted):
        with st.spinner(f"P{i+1} を生成中..."):
            try:
                generate_page_content(product_id, product, page)
            except Exception as e:
                st.error(f"P{i+1} 生成エラー: {e}")
        progress_bar.progress((i + 1) / len(pages_sorted))
    st.success("全ページの生成が完了しました！")
    st.rerun()

st.markdown("---")

page_options = {f"P{p.get('order', '?')} - {p.get('title', '未設定')}": p for p in pages_sorted}

selected_page_name = st.selectbox("編集するページを選択", list(page_options.keys()))
selected_page = page_options[selected_page_name]
page_id = selected_page.get('id', 'unknown')

st.markdown("---")

# ページ情報表示

# 詳細生成ボタン
btn_c1, btn_c2 = st.columns([6, 1])
with btn_c1:
    gen_content = st.button("AIでコンテンツ生成", type="primary", use_container_width=True)
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
            generate_page_content(product_id, product, selected_page)
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
st.markdown('<div class="step-header">コンテンツ編集</div>', unsafe_allow_html=True)

# parsed構造を取得
parsed_data = None
text_elements = []
visual_elements = []

if isinstance(raw_detail, dict) and "result" in raw_detail:
    result_data = raw_detail["result"]
    if isinstance(result_data, dict) and "parsed" in result_data:
        parsed_data = result_data["parsed"]

if parsed_data and isinstance(parsed_data, dict) and "elements" in parsed_data:
    elements = parsed_data.get("elements", [])
    
    # テキスト要素とビジュアル要素を分離
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
                    item_key = f"item_{page_id}_{i}_{j}"
                    
                    # 採用された値があればそれを使う
                    adopted_key = f"{item_key}_adopted"
                    if adopted_key in st.session_state:
                        default_value = st.session_state[adopted_key]
                        del st.session_state[adopted_key]
                    else:
                        default_value = item

                    col_input, col_brush = st.columns([10, 1])
                    with col_input:
                        new_item = st.text_input(
                            f"項目{j+1}",
                            value=default_value,
                            key=item_key,
                            label_visibility="collapsed"
                        )
                    with col_brush:
                        if st.button("✨", key=f"brush_{item_key}", help="AIでブラッシュアップ"):
                            st.session_state['brushup_target'] = item_key
                            st.session_state['brushup_original'] = item
                            st.session_state['brushup_phase'] = 'initial'
                            with st.spinner("案を生成中..."):
                                st.session_state['brushup_candidates'] = generate_brushup_query(item, product)
                            st.rerun()
                    
                    # ブラッシュアップ候補の表示
                    if st.session_state.get('brushup_target') == item_key:
                        st.markdown(f"> **💡 ブラッシュアップ案 ({st.session_state.get('brushup_phase', 'initial')})**")
                        candidates = st.session_state.get('brushup_candidates', [])
                        
                        for c_idx, candidate in enumerate(candidates):
                            c_col_text, c_col_ref, c_col_adopt = st.columns([6, 2, 2])
                            with c_col_text:
                                st.info(f"**【{candidate['direction']}】**\n\n{candidate['text']}")
                            with c_col_ref:
                                # 初期段階なら「この方向で」
                                if st.session_state.get('brushup_phase') == 'initial':
                                    if st.button("この方向で", key=f"refine_{item_key}_{c_idx}"):
                                        st.session_state['brushup_direction'] = candidate['direction']
                                        st.session_state['brushup_phase'] = 'refine'
                                        with st.spinner("バリエーションを生成中..."):
                                            st.session_state['brushup_candidates'] = generate_brushup_query(
                                                st.session_state['brushup_original'], product, direction=candidate['direction']
                                            )
                                        st.rerun()
                            with c_col_adopt:
                                if st.button("採用", key=f"adopt_{item_key}_{c_idx}", type="primary"):
                                    # 橋渡し用キーに保存（ウィジェット用）
                                    st.session_state[f"{item_key}_adopted"] = candidate['text']
                                    # 内部データを更新
                                    elem["items"][j] = candidate['text']
                                    
                                    # DBへ即時保存（既存の保存ロジックと同期）
                                    if 'page_contents' not in product:
                                        product['page_contents'] = {}
                                    
                                    if page_id in product['page_contents'] and isinstance(product['page_contents'][page_id], dict):
                                        existing = product['page_contents'][page_id]
                                        if "result" in existing:
                                            existing["result"]["parsed"] = parsed_data
                                            # displayも更新
                                            display_lines = []
                                            for e in parsed_data.get("elements", []):
                                                e_type = e.get("type", "")
                                                e_order = e.get("order", "")
                                                display_lines.append(f"## 要素{e_order}: {e_type}")
                                                if e_type in ["表", "チェックリスト"]:
                                                    its = e.get("items", [])
                                                    for idx_it, it in enumerate(its, 1):
                                                        display_lines.append(f"- 項目{idx_it}: {it}")
                                                elif e_type in ["メインビジュアル", "サブビジュアル", "画像"]:
                                                    display_lines.append(f"（画像指示）{e.get('description', '')}")
                                                else:
                                                    display_lines.append(f"{e.get('content', '')}")
                                                display_lines.append("")
                                            existing["result"]["display"] = "\n".join(display_lines)
                                        product['page_contents'][page_id] = existing
                                    data_store.update_product(product_id, product)
                                    
                                    clear_brushup_state()
                                    st.rerun()
                                    
                        # キャンセルボタンは候補ループの外に配置
                        if st.button("❌ キャンセル", key=f"cancel_btn_{item_key}"):
                            clear_brushup_state()
                            st.rerun()

                    new_items.append(new_item)
                
                if new_items != items:
                    elem["items"] = new_items
                    elem["item_count"] = len(new_items)
            else:
                # 単一テキスト形式
                text_key = f"text_elem_{page_id}_{i}"
                
                # 採用された値があればそれを使う
                adopted_key = f"{text_key}_adopted"
                if adopted_key in st.session_state:
                    default_value = st.session_state[adopted_key]
                    del st.session_state[adopted_key]
                else:
                    default_value = elem_content

                col1, col2, col3 = st.columns([8, 2, 1])
                with col1:
                    new_content = st.text_input(
                        f"{elem_type}",
                        value=default_value,
                        key=text_key
                    )
                with col2:
                    if char_count:
                        st.caption(f"{char_count}文字")
                    else:
                        st.caption(f"{len(new_content)}文字")
                with col3:
                    st.write("") # 調整
                    st.write("")
                    if st.button("✨", key=f"brush_{text_key}", help="AIでブラッシュアップ"):
                        st.session_state['brushup_target'] = text_key
                        st.session_state['brushup_original'] = elem_content
                        st.session_state['brushup_phase'] = 'initial'
                        with st.spinner("案を生成中..."):
                            st.session_state['brushup_candidates'] = generate_brushup_query(elem_content, product)
                        st.rerun()
                
                # ブラッシュアップ候補の表示
                if st.session_state.get('brushup_target') == text_key:
                    st.markdown(f"> **💡 ブラッシュアップ案 ({st.session_state.get('brushup_phase', 'initial')})**")
                    candidates = st.session_state.get('brushup_candidates', [])
                    
                    for c_idx, candidate in enumerate(candidates):
                        c_col_text, c_col_ref, c_col_adopt = st.columns([6, 2, 2])
                        with c_col_text:
                            st.info(f"**【{candidate['direction']}】**\n\n{candidate['text']}")
                        with c_col_ref:
                            if st.session_state.get('brushup_phase') == 'initial':
                                if st.button("この方向で", key=f"refine_{text_key}_{c_idx}"):
                                    st.session_state['brushup_direction'] = candidate['direction']
                                    st.session_state['brushup_phase'] = 'refine'
                                    with st.spinner("バリエーションを生成中..."):
                                        st.session_state['brushup_candidates'] = generate_brushup_query(
                                            st.session_state['brushup_original'], product, direction=candidate['direction']
                                        )
                                    st.rerun()
                        with c_col_adopt:
                            if st.button("採用", key=f"adopt_{text_key}_{c_idx}", type="primary"):
                                # 橋渡し用キーに保存（ウィジェット用）
                                st.session_state[f"{text_key}_adopted"] = candidate['text']
                                # 内部データを更新
                                elem["content"] = candidate['text']
                                # 文字数も更新
                                elem["char_count"] = len(candidate['text'])
                                
                                # DBへ即時保存（既存の保存ロジックと同期）
                                if 'page_contents' not in product:
                                    product['page_contents'] = {}
                                
                                if page_id in product['page_contents'] and isinstance(product['page_contents'][page_id], dict):
                                    existing = product['page_contents'][page_id]
                                    if "result" in existing:
                                        existing["result"]["parsed"] = parsed_data
                                        # displayも更新
                                        display_lines = []
                                        for e in parsed_data.get("elements", []):
                                            e_type = e.get("type", "")
                                            e_order = e.get("order", "")
                                            display_lines.append(f"## 要素{e_order}: {e_type}")
                                            if e_type in ["メインビジュアル", "サブビジュアル", "画像"]:
                                                display_lines.append(f"（画像指示）{e.get('description', '')}")
                                            else:
                                                display_lines.append(f"{e.get('content', '')}")
                                            display_lines.append("")
                                        existing["result"]["display"] = "\n".join(display_lines)
                                    product['page_contents'][page_id] = existing
                                data_store.update_product(product_id, product)
                                
                                clear_brushup_state()
                                st.rerun()
                                
                    # キャンセルボタンは候補ループの外に配置
                    if st.button("❌ キャンセル", key=f"cancel_btn_{text_key}"):
                        clear_brushup_state()
                        st.rerun()
                
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
if st.button("保存", use_container_width=True, key="save_parsed", type="primary"):
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
    
    if st.button("保存", use_container_width=True, key="save_legacy", type="primary"):
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

