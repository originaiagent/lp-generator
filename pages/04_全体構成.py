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

# 製品選択チェック
require_product()

from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.settings_manager import SettingsManager
import json

def render_structure_page():
    st.title('🏗️ 全体構成')
    
    data_store = DataStore()
    product_id = st.session_state['current_product_id']
    product = data_store.get_product(product_id)
    
    if not product:
        st.error("商品データが見つかりません。")
        return
    
    # AIサイドバー表示
    
    # 入力情報サマリー（折りたたみ）
    render_input_summary(product)
    
    st.markdown("---")
    
    # 要素分析セクション
    render_appeal_analysis(product, data_store, product_id)
    
    st.markdown("---")
    
    # ページ構成セクション
    render_page_structure(product, data_store, product_id)

def render_input_summary(product):
    """入力情報サマリー（折りたたみ）"""
    with st.expander("📋 入力情報サマリー（クリックで展開）", expanded=False):
        # LP分析結果サマリー
        lp_analyses = product.get('lp_analyses') or []
        if lp_analyses:
            st.markdown(f"**📊 LP分析:** {len(lp_analyses)}枚分析済み")
            for i, analysis in enumerate(lp_analyses):
                if isinstance(analysis, dict) and "result" in analysis:
                    result = analysis["result"]
                    page_type = result.get("page_type", "不明")
                    text_count = len(result.get("texts", []))
                    st.write(f"  - {i+1}枚目: {page_type}（テキスト{text_count}個）")
        
        # トンマナ分析結果サマリー
        tone = product.get('tone_manner') or {}
        if isinstance(tone, dict) and "result" in tone:
            tone_result = tone["result"]
            style = tone_result.get("overall_style", {}).get("impression", "未分析")
            st.markdown(f"**🎨 トンマナ:** {style}")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="step-header">📦 製品情報</div>', unsafe_allow_html=True)
            st.write(f"**製品名:** {product.get('name', '未設定')}")
            st.write(f"**説明:** {product.get('description', '未設定')[:100] if product.get('description') else '未設定'}")
            
            images = product.get('product_images') or []
            st.write(f"**製品画像:** {len(images)}枚")
            
            if product.get('product_sheet_data'):
                st.write("**製品シート:** ✅ アップロード済み")
                st.caption("📊 根拠: 製品情報シート")
            else:
                st.write("**製品シート:** ❌ 未設定")
        
        with col2:
            st.markdown('<div class="step-header">🔍 競合分析</div>', unsafe_allow_html=True)
            # v2を優先して確認
            comp_v2 = product.get('competitor_analysis_v2') or {}
            if comp_v2:
                st.write("**分析状況:** ✅ 完了")
                summary = comp_v2.get("summary", {})
                ranking = summary.get("element_ranking", [])
                if ranking:
                    ranking_str = "\n".join([f"- {k} ({v}社)" for k, v in ranking[:5]])
                    st.text_area("主要な訴求要素", f"上位5件:\n{ranking_str}", height=150, disabled=True)
                else:
                    st.text_area("分析結果", "分析済みデータがあります", height=150, disabled=True)
                st.caption("📊 根拠: 競合情報分析 v2")
            elif product.get('competitor_analysis'):
                st.write("**分析状況:** ✅ 完了")
                st.text_area("分析結果", product["competitor_analysis"]["result"][:500] if isinstance(product.get("competitor_analysis"), dict) else str(product.get("competitor_analysis", ""))[:500], height=150, disabled=True)
                st.caption("📊 根拠: 競合情報分析")
            else:
                st.write("**分析状況:** ❌ 未実施")
                st.info("「情報入力」ページで競合分析を実行してください")
        
        st.markdown('<div class="step-header">🎨 参考LP分析</div>', unsafe_allow_html=True)
        ref_images = product.get('reference_lp_images') or []
        lp_analyses = product.get("lp_analyses") or []
        
        st.write(f"**参考画像:** {len(ref_images)}枚")
        st.write(f"**分析済み:** {len(lp_analyses)}件")
        
        if lp_analyses:
            st.caption("📊 根拠: 参考LP画像分析")

def render_appeal_analysis(product, data_store, product_id):
    """訴求ポイント確認セクション"""
    st.markdown('<div class="step-header">🎯 訴求ポイント確認</div>', unsafe_allow_html=True)
    st.caption("製品情報と競合分析から、この商材の訴求ポイントを抽出します")
    
    # 分析実行ボタン
    col_btn, col_cost = st.columns([6, 1])
    with col_btn:
        if st.button("🔍 訴求ポイントを抽出", type="primary", width="stretch"):
            extract_appeal_points(product, data_store, product_id)
    with col_cost:
        if st.button("💰", key="cost_appeal", help="直前の生成コスト"):
            if 'last_api_usage' in st.session_state and st.session_state.last_api_usage:
                usage = st.session_state.last_api_usage
                st.toast(f"入力: {usage.get('input_tokens', 0):,} / 出力: {usage.get('output_tokens', 0):,} / ¥{usage.get('cost_jpy', 0):.2f}")
            else:
                st.toast("まだ生成していません")
    
    # 分析結果表示
    from modules.trace_viewer import show_trace
    raw_appeals = product.get("appeal_points") or {}
    
    if isinstance(raw_appeals, dict) and "result" in raw_appeals:
        appeals = raw_appeals["result"]
        show_trace(raw_appeals, "訴求ポイント抽出の生成情報")
    else:
        appeals = raw_appeals
    
    if appeals:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**💪 自社の訴求ポイント**")
            st.caption("製品情報シートから抽出")
            selected = product.get('selected_appeals') or []
            own_appeals = appeals.get('own_appeals') or []
            
            for i, item in enumerate(own_appeals):
                name = item.get('name', '')
                desc = item.get('description', '')
                checked = name in selected
                
                if st.checkbox(f"**{name}**", value=checked, key=f"own_{i}"):
                    if name not in selected:
                        selected.append(name)
                else:
                    if name in selected:
                        selected.remove(name)
                st.caption(f"　{desc}")
            
            product['selected_appeals'] = selected
            data_store.update_product(product_id, product)
        
        with col2:
            st.markdown("**🔍 競合の訴求ポイント**")
            st.caption("競合分析から抽出（参考にする場合はチェック）")
            competitor_appeals = appeals.get('competitor_appeals') or []
            for i, item in enumerate(competitor_appeals):
                name = item.get('name', '')
                desc = item.get('description', '')
                checked = name in selected
                if st.checkbox(f"**{name}**", value=checked, key=f"comp_{i}"):
                    if name not in selected:
                        selected.append(name)
                else:
                    if name in selected:
                        selected.remove(name)
                st.caption(f"　{desc}")
            
            st.markdown("**✨ 差別化ポイント**")
            diff_appeals = appeals.get('differentiation') or []
            for i, item in enumerate(diff_appeals):
                name = item.get('name', '')
                reason = item.get('reason', '')
                checked = name in selected
                if st.checkbox(f"**{name}**", value=checked, key=f"diff_{i}"):
                    if name not in selected:
                        selected.append(name)
                else:
                    if name in selected:
                        selected.remove(name)
                st.caption(f"　{reason}")
            
            # 保存
            product['selected_appeals'] = selected
            data_store.update_product(product_id, product)
    else:
        st.info("「訴求ポイントを抽出」ボタンを押して分析を開始してください")


def extract_appeal_points(product, data_store, product_id):
    """訴求ポイントを抽出"""
    from modules.settings_manager import SettingsManager
    from modules.ai_provider import AIProvider
    from modules.prompt_manager import PromptManager
    from modules.trace_viewer import save_with_trace
    import json as json_module
    
    with st.spinner("訴求ポイントを抽出中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            # 製品情報を取得
            product_info = f"製品名: {product.get('name', '')}\n"
            product_info += f"説明: {product.get('description', '')}\n"
            
            # 整理済みシートデータを優先使用
            organized = product.get('product_sheet_organized', '')
            if organized:
                product_info += f"\n【製品情報（整理済み）】\n{organized[:1500]}"
            else:
                sheet_data = product.get('product_sheet_data', '')
                if sheet_data:
                    if isinstance(sheet_data, str):
                        product_info += f"製品シート: {sheet_data[:500]}"
                    else:
                        product_info += f"製品シート: {str(sheet_data)[:500]}"
            
            # LP分析結果から訴求情報を抽出（新旧形式両対応）
            lp_analyses = product.get('lp_analyses', [])
            lp_info = ""
            for i, analysis in enumerate(lp_analyses):
                if isinstance(analysis, dict) and "result" in analysis:
                    result = analysis["result"]
                    lp_info += f"\n【{i+1}枚目】"
                    # 新形式（elements）と旧形式（texts）両対応
                    elements = result.get("elements", result.get("texts", []))
                    for elem in elements:
                        aim = elem.get("aim", "")
                        effect = elem.get("effect", "")
                        content_text = str(elem.get("content", ""))[:30]
                        elem_type = elem.get("element_type", elem.get("type", ""))
                        items = elem.get("items") or []
                        if aim:
                            if items:
                                lp_info += f"\n- [{elem_type}] {len(items)}項目 (狙い:{aim}, 効果:{effect})"
                            else:
                                lp_info += f"\n- [{elem_type}] {content_text}... (狙い:{aim}, 効果:{effect})"
            if lp_info:
                product_info += f"\n\n【参考LP分析の訴求情報】{lp_info}"
            
            # 競合分析結果を取得（新旧形式両対応）
            comp_v2 = product.get('competitor_analysis_v2') or {}
            if comp_v2:
                summary = comp_v2.get("summary", {})
                ranking = summary.get("element_ranking", [])
                competitor_text = f"全競合の数: {summary.get('total_competitors', 0)}\n"
                competitor_text += "訴求要素ランキング:\n" + "\n".join([f"- {k}: {v}社" for k, v in ranking])
            else:
                competitor = product.get('competitor_analysis', {})
                if isinstance(competitor, dict) and "result" in competitor:
                    result = competitor["result"]
                    if isinstance(result, str):
                        competitor_text = result[:500]
                    else:
                        competitor_text = str(result)[:500]
                else:
                    competitor_text = str(competitor)[:500] if competitor else "なし"
            
            prompt = prompt_manager.get_prompt("appeal_point_extraction", {
                "product_info": product_info,
                "competitor_analysis": competitor_text
            })
            
            result = ai_provider.ask(prompt, "appeal_extraction")
            
            # JSON抽出
            try:
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0]
                parsed = json_module.loads(result.strip())
            except:
                parsed = {"raw": result, "parse_error": True}
            
            traced = save_with_trace(
                result=parsed,
                prompt_id="appeal_point_extraction",
                prompt_used=prompt,
                input_refs={"製品名": product.get('name', '')},
                model=settings.get("llm_model", "unknown")
            )
            
            product['appeal_points'] = traced
            data_store.update_product(product_id, product)
            st.success("訴求ポイント抽出完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"抽出エラー: {e}")


def render_page_structure(product, data_store, product_id):
    """ページ構成セクション"""
    st.markdown('<div class="step-header">📄 ページ構成</div>', unsafe_allow_html=True)
    
    # 全体の流れを表示
    raw_structure = product.get('structure') or {}
    if isinstance(raw_structure, dict) and "result" in raw_structure:
        structure = raw_structure["result"]
        overview = structure.get("overview", "")
        if overview:
            st.info(f"📋 **全体の流れ:** {overview}")
    
    # 構成自動生成ボタン
    selected = product.get('selected_appeals') or []
    lp_analyses = product.get('lp_analyses') or []
    
    if lp_analyses:
        st.success(f"✅ 参考LP {len(lp_analyses)}枚 / 訴求ポイント {len(selected)}個選択済み")
        
        # 訴求ポイント数とページ数のバランスチェック
        lp_count = len(lp_analyses)
        appeal_count = len(selected)
        recommended_min = (appeal_count + 2) // 3  # 3ポイントで1ページ目安
        
        if appeal_count > 0 and lp_count < recommended_min:
            st.warning(f"""⚠️ **訴求ポイントが多すぎる可能性があります**
            
- 選択した訴求ポイント: **{appeal_count}個**
- 参考LP枚数: **{lp_count}枚**
- 推奨ページ数: **{recommended_min}〜{recommended_min + 1}枚**

**対応案:**
1. 訴求ポイントを **{lp_count * 3}個以下** に絞る
2. 参考LPを追加して **{recommended_min}枚以上** にする
""")
        
        col_btn2, col_cost2 = st.columns([6, 1])
        with col_btn2:
            if st.button("🚀 構成を自動生成", width="stretch", type="primary"):
                generate_structure_from_elements(product, data_store, product_id)
        with col_cost2:
            if st.button("💰", key="cost_structure", help="直前の生成コスト"):
                if 'last_api_usage' in st.session_state and st.session_state.last_api_usage:
                    usage = st.session_state.last_api_usage
                    st.toast(f"入力: {usage.get('input_tokens', 0):,} / 出力: {usage.get('output_tokens', 0):,} / ¥{usage.get('cost_jpy', 0):.2f}")
                else:
                    st.toast("まだ生成していません")
    else:
        st.info("情報入力ページでLP画像を分析してください")
    
    # 現在の構成表示
    from modules.trace_viewer import show_trace
    raw_structure = product.get('structure') or {}
    
    # トレース形式対応
    if isinstance(raw_structure, dict) and "result" in raw_structure:
        structure = raw_structure["result"]
        show_trace(raw_structure, "構成生成の生成情報")
    else:
        structure = raw_structure
    
    pages = structure.get('pages', []) if isinstance(structure, dict) else []
    
    structure_changed = False
    
    if pages:
        for page in pages:
            page_id = page.get('id', f"page_{page.get('order', 1)}")
            order = page.get('order', '')
            title = page.get('title', '')
            role = page.get('role', page.get('summary', ''))
            appeals = page.get('appeals', [])
            appeals_str = ', '.join(appeals) if appeals else ''
            
            with st.expander(f"P{order} - {title}", expanded=False):
                # タイトル編集
                new_title = st.text_input("タイトル", value=title, key=f"edit_title_{page_id}")
                if new_title != title:
                    page['title'] = new_title
                    structure_changed = True
                
                # 役割編集
                new_role = st.text_area("役割", value=role, height=80, key=f"edit_role_{page_id}")
                if new_role != role:
                    page['role'] = new_role
                    page['summary'] = new_role  # summaryも更新
                    structure_changed = True
                
                if appeals_str:
                    st.write(f"**訴求:** {appeals_str}")
                
                # 参照LP編集
                ref_page = page.get('reference_page', 1)
                new_ref = st.number_input("参照LP（枚目）", value=ref_page, min_value=1, key=f"edit_ref_{page_id}")
                if new_ref != ref_page:
                    page['reference_page'] = new_ref
                    structure_changed = True


        # 変更があれば保存
        if structure_changed:
            if isinstance(raw_structure, dict) and "result" in raw_structure:
                raw_structure["result"] = structure
                product['structure'] = raw_structure
            else:
                product['structure'] = structure
            data_store.update_product(product_id, product)
            st.success("構成を更新しました")
            st.rerun()

def generate_structure_from_elements(product, data_store, product_id):
    """確定要素から構成を自動生成"""
    from modules.trace_viewer import save_with_trace
    from modules.prompt_manager import PromptManager
    
    with st.spinner("構成を生成中..."):
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            ai_provider = AIProvider(settings)
            prompt_manager = PromptManager()
            
            confirmed = product.get('confirmed_elements', [])
            
            # LP分析結果からページ構成情報を抽出
            lp_analyses = product.get('lp_analyses') or []
            
            # 選択された訴求ポイント
            selected_appeals = product.get('selected_appeals') or []
            
            input_refs = {
                "製品名": product.get('name', '未設定'),
                "整理済み情報": "あり" if product.get('product_sheet_organized') else "なし",
                "訴求ポイント": f"{len(selected_appeals)}個",
                "参考LP": f"{len(lp_analyses)}枚"
            }
            page_count = len(lp_analyses)
            lp_summary = ""
            for i, analysis in enumerate(lp_analyses):
                if isinstance(analysis, dict) and "result" in analysis:
                    result = analysis["result"]
                    lp_summary += f"\n\n【{i+1}枚目】種別: {result.get('page_type', '不明')}"
                    if result.get('main_message'):
                        lp_summary += f"\nメッセージ: {result.get('main_message')}"
                    if result.get('page_role'):
                        lp_summary += f"\n役割: {result.get('page_role')}"
                    texts = result.get("texts", [])
                    if texts:
                        lp_summary += f"\nテキスト要素:"
                        for t in texts[:5]:
                            lp_summary += f"\n  - {t.get('type')}: {t.get('content', '')[:50]}"
                            if t.get('aim'):
                                lp_summary += f" → {t.get('aim')}"
            
            # 選択された訴求ポイント
            selected_appeals = product.get('selected_appeals', [])
            appeals_str = ', '.join(selected_appeals) if selected_appeals else "未選択"
            
            prompt = prompt_manager.get_prompt("structure_generation", {
                "page_count": page_count,
                "product_name": product.get('name', ''),
                "product_description": product.get('description', ''),
                "lp_analysis_summary": lp_summary if lp_summary else "なし",
                "selected_appeals": appeals_str
            })
            
            result = ai_provider.ask(prompt, "structure_generation")
            
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            
            structure = json.loads(result.strip())
            
            # システム側でページIDを確定的に付与（UUIDベース）
            import uuid
            if 'pages' in structure:
                for i, page in enumerate(structure['pages']):
                    page['id'] = f"pg_{uuid.uuid4().hex[:8]}"
                    page['order'] = i + 1
                    page['reference_page'] = i + 1
            
            traced = save_with_trace(
                result=structure,
                prompt_id="structure_generation",
                prompt_used=prompt,
                input_refs=input_refs,
                model=settings.get("llm_model", "unknown")
            )
            
            product['structure'] = traced
            
            # 構成再生成時は関連データをクリア
            product['page_details'] = {}
            product['page_contents'] = {}
            product['generated_lp_images'] = {}
            product['generated_versions'] = {}
            product['custom_prompts'] = {}
            
            data_store.update_product(product_id, product)
            st.success("構成を生成しました！")
            st.rerun()
            
        except json.JSONDecodeError as e:
            st.error(f"JSON解析エラー: {e}")
        except Exception as e:
            st.error(f"生成エラー: {e}")

# メイン実行
render_structure_page()
