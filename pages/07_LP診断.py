import streamlit as st
import json
from modules.styles import apply_styles, page_header
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(page_title="LP Audit", layout="wide")

# スタイル適用
apply_styles()

# AIサイドバー表示
render_ai_sidebar()


from modules.page_guard import require_product
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.settings_manager import SettingsManager
from modules.prompt_manager import PromptManager

# 製品選択チェック
require_product()

def get_lp_content(product, target_index=None):
    """LPの構成とコンテンツを結合して文字列として返す"""
    lp_text = ""
    
    # 構成情報を取得
    raw_structure = product.get('structure', {})
    if isinstance(raw_structure, dict) and "result" in raw_structure:
        structure = raw_structure["result"]
    else:
        structure = raw_structure
    
    pages = structure.get('pages', []) if isinstance(structure, dict) else []
    page_contents = product.get('page_contents', {})
    
    # ターゲットが指定されている場合（"全ページ"以外）
    if target_index is not None and 0 <= target_index < len(pages):
        display_pages = [pages[target_index]]
        start_idx = target_index + 1
    else:
        display_pages = pages
        start_idx = 1
        
    for i, page in enumerate(display_pages):
        idx = start_idx + i if target_index is None else start_idx
        page_id = page.get('id', f"page_{idx}")
        title = page.get('title', '無題')
        role = page.get('role', page.get('summary', ''))
        
        lp_text += f"\n### P{idx}: {title}\n"
        lp_text += f"役割: {role}\n"
        
        # コンテンツを取得
        content_item = page_contents.get(page_id, {})
        if isinstance(content_item, dict) and "result" in content_item:
            result_data = content_item["result"]
            if isinstance(result_data, dict) and "display" in result_data:
                page_text = result_data["display"]
            else:
                page_text = str(result_data)
        else:
            page_text = content_item.get('content', '') if isinstance(content_item, dict) else ""
            
        if page_text:
            lp_text += f"内容:\n{page_text}\n"
        else:
            lp_text += "内容: (未生成)\n"
            
    return lp_text

def generate_personas(ai_provider, prompt_manager, product, exposure_type):
    """商品と露出先に応じたペルソナを生成"""
    
    variables = {
        "product_name": product.get('name', ''),
        "product_description": product.get('description', ''),
        "product_category": product.get('category', ''),
        "exposure_type": exposure_type
    }
    
    prompt = prompt_manager.get_prompt("persona_generation", variables)
    
    response = ai_provider.ask(prompt, "persona_generation")
    
    try:
        # JSON部分を抽出
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response
            
        data = json.loads(json_str.strip())
        return data.get('personas', [])
    except Exception as e:
        st.error(f"ペルソナ生成の解析に失敗しました: {e}")
        st.code(response)
        return []

def evaluate_by_persona(ai_provider, prompt_manager, product, exposure_type, persona, lp_content):
    """各ペルソナ視点でLPを評価"""
    
    # 競合情報を取得
    comp_v2 = product.get('competitor_analysis_v2', {})
    competitors = comp_v2.get('competitors', [])
    if not competitors:
        competitors = product.get('competitors', [])
    
    # 露出先別の評価重点
    exposure_focus_map = {
        "ECモール": """
- 競合商品と並んだ時に「これがいい」と思える差別化ポイントがあるか
- 比較検討中の人が「他より良さそう」と感じる根拠が明確か
- 「失敗したくない」心理に対する安心材料があるか
""",
        "クラファン": """
- 「こんなの初めて見た！」という新規性・驚きがあるか
- 開発者の想いやストーリーに共感できるか
- 「応援したい」と思えるか
- 早期支援者へのメリットが明確か
""",
        "自社EC": """
- ブランドの世界観・美意識が一貫しているか
- 「このブランドから買いたい」と思わせる魅力があるか
- 他のECサイトではなく自社ECで買う理由があるか
- ファンになりたくなる要素があるか
"""
    }
    
    variables = {
        "persona_name": persona['name'],
        "persona_age": persona['age'],
        "persona_occupation": persona['occupation'],
        "persona_motivation": persona['motivation'],
        "persona_concerns": persona['concerns'],
        "persona_decision_style": persona['decision_style'],
        "persona_budget_sensitivity": persona['budget_sensitivity'],
        "exposure_type": exposure_type,
        "exposure_focus": exposure_focus_map.get(exposure_type, ""),
        "lp_content": lp_content,
        "competitors": str(competitors)[:1000]
    }
    
    prompt = prompt_manager.get_prompt("persona_evaluation", variables)
    
    response = ai_provider.ask(prompt, "persona_evaluation")
    
    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response
            
        return json.loads(json_str.strip())
    except Exception as e:
        st.error(f"評価の解析に失敗しました: {e}")
        st.code(response)
        return None

def evaluate_by_employee(ai_provider, prompt_manager, data_store, product, exposure_type, employee, lp_content):
    """特定の従業員AIとしてLPを評価"""
    
    # 過去のフィードバックを取得
    past_feedback_list = data_store.get_employee_feedback(employee['id'], limit=20)
    
    # フィードバックを文字列に整形
    if past_feedback_list:
        feedback_msgs = []
        for f in reversed(past_feedback_list): # 古い順
            feedback_msgs.append(f"AI評価: {f['ai_evaluation']}\n修正指示: {f['user_feedback']}")
        past_feedback_str = "\n\n".join(feedback_msgs)
    else:
        past_feedback_str = "過去のフィードバックはありません。あなたの役割と性格に基づいて自由に評価してください。"

    variables = {
        "employee_name": employee['name'],
        "employee_role": employee['role'],
        "employee_expertise": employee['expertise'],
        "employee_evaluation_perspective": employee['evaluation_perspective'],
        "employee_personality_traits": employee['personality_traits'],
        "employee_lifestyle": employee.get('lifestyle', '未設定'),
        "employee_psychographic": employee.get('psychographic', '未設定'),
        "employee_demographic": employee.get('demographic', '未設定'),
        "employee_buying_behavior": employee.get('buying_behavior', '未設定'),
        "employee_ng_points": employee.get('ng_points', '未設定'),
        "past_feedback": past_feedback_str,
        "exposure_type": exposure_type,
        "lp_content": lp_content
    }
    
    prompt = prompt_manager.get_prompt("employee_evaluation", variables)
    
    response = ai_provider.ask(prompt, "employee_evaluation")
    
    # JSONパースを廃止し、Markdownテキストとして直接返す
    return {
        "evaluation_text": response,
        "raw_response": response
    }

def generate_summary(ai_provider, prompt_manager, evaluations, exposure_type):
    """全ペルソナの評価を総合分析"""
    
    variables = {
        "exposure_type": exposure_type,
        "evaluations_json": json.dumps(evaluations, ensure_ascii=False, indent=2)
    }
    
    prompt = prompt_manager.get_prompt("diagnosis_summary", variables)
    
    response = ai_provider.ask(prompt, "diagnosis_summary")
    
    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response
            
        return json.loads(json_str.strip())
    except Exception as e:
        st.error(f"総合分析の解析に失敗しました: {e}")
        st.code(response)
        return None

def generate_improvement_proposal(ai_provider, prompt_manager, product, improvement_text, pages_data):
    """改善提案から具体的な修正案を生成"""
    
    variables = {
        "improvement_text": improvement_text,
        "pages_data_json": json.dumps(pages_data, ensure_ascii=False, indent=2)
    }
    
    prompt = prompt_manager.get_prompt("improvement_proposal", variables)
    
    response = ai_provider.ask(prompt, "improvement_proposal")
    
    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response
            
        return json.loads(json_str.strip())
    except Exception as e:
        st.error(f"改善案のパースに失敗しました: {e}")
        return None

def apply_improvement(product_id, data_store, page_index, element_index, new_text):
    """改善案をページ詳細に反映"""
    product = data_store.get_product(product_id)
    if not product:
        return False
    
    # ページ情報を取得
    page_contents = product.get('page_contents', {})
    # インデックスからpage_idを特定する必要がある
    raw_structure = product.get('structure', {})
    if isinstance(raw_structure, dict) and "result" in raw_structure:
        structure = raw_structure["result"]
    else:
        structure = raw_structure
    
    pages = structure.get('pages', [])
    if page_index >= len(pages):
        return False
        
    target_page = pages[page_index]
    page_id = target_page.get('id')
    
    if not page_id or page_id not in page_contents:
        return False
        
    page_data = page_contents[page_id]
    if not isinstance(page_data, dict) or "result" not in page_data:
        return False
        
    result_data = page_data["result"]
    if not isinstance(result_data, dict) or "parsed" not in result_data:
        return False
        
    parsed = result_data["parsed"]
    elements = parsed.get("elements", [])
    
    if element_index < len(elements):
        elem = elements[element_index]
        elem['content'] = new_text
        elem['char_count'] = len(new_text)
        
        # displayも更新
        display_lines = []
        for e in elements:
            e_type = e.get("type", "")
            e_order = e.get("order", "")
            display_lines.append(f"## 要素{e_order}: {e_type}")
            if e_type in ["メインビジュアル", "サブビジュアル", "画像"]:
                display_lines.append(f"（画像指示）{e.get('description', '')}")
            else:
                display_lines.append(f"{e.get('content', '')}")
            display_lines.append("")
        result_data["display"] = "\n".join(display_lines)
        
        # 保存
        data_store.update_product(product_id, product)
        return True
        
    return False

def display_results(personas, evaluations, summary, exposure_type, key_suffix=""):
    """診断結果を表示"""
    
    st.markdown("---")
    st.subheader(f"🎯 {exposure_type}向け診断結果")
    
    # ペルソナ別評価
    st.markdown("### 👥 ペルソナ別評価")
    
    for persona, eval_res in zip(personas, evaluations):
        if not eval_res:
            continue
            
        with st.expander(f"**{persona['name']}** - {'⭐' * eval_res.get('overall_rating', 0)} {eval_res.get('purchase_decision', '')}", expanded=True):
            
            # 第一印象
            st.markdown(f"👀 **第一印象:** {eval_res.get('first_impression', '')}")
            
            # 生の声
            st.markdown(f"💬 **この人の声:**")
            st.info(eval_res.get('voice', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("✅ **響いた点**")
                for point in eval_res.get('resonated_points', []):
                    st.write(f"・{point}")
            with col2:
                st.markdown("❌ **不安な点**")
                for concern in eval_res.get('concerns', []):
                    st.write(f"・{concern}")
            
            st.caption(f"競合比較: {eval_res.get('vs_competitors', '')}")
            st.caption(f"改善希望: {eval_res.get('improvement_suggestion', '')}")
    
    # 総合分析
    if summary:
        st.markdown("---")
        st.markdown("### 📊 総合分析")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("購入検討率", summary.get('purchase_rate', ''))
        with col2:
             st.markdown(f"**🏎️ 競合比較:** {summary.get('competitor_comparison', '')}")
        
        st.markdown("**💪 強み**")
        for s in summary.get('strengths', []):
            st.write(f"・{s}")
        
        st.markdown("**⚠️ 弱み**")
        for w in summary.get('weaknesses', []):
            st.write(f"・{w}")
        
        st.markdown("**🔧 改善優先度**")
        for i, imp in enumerate(summary.get('improvements', [])):
            priority = imp.get('priority', '中')
            content = imp.get('content', '')
            priority_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(priority, "⚪")
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{priority_icon} [{priority}] {content}")
            with col2:
                if st.button("反映案を作成", key=f"improve_{key_suffix}_{i}"):
                    st.session_state['selected_improvement'] = {
                        'index': i,
                        'text': content
                    }
                    st.session_state['improvement_step'] = 'generating'
                    st.rerun()
        
        st.markdown("**💡 総合アドバイス**")
        st.success(summary.get('overall_advice', ''))

def run_diagnosis(product, exposure_type, diagnosis_target):
    """LP診断を実行"""
    
    data_store = DataStore()
    product_id = product.get('id')
    settings = SettingsManager().get_settings()
    ai_provider = AIProvider(settings)
    prompt_manager = PromptManager()
    
    # 診断対象のインデックスを特定
    target_index = None
    if diagnosis_target != "全ページ":
        try:
            # "P1 - タイトル" のような形式からインデックスを抽出
            target_index = int(diagnosis_target.split(' ')[0][1:]) - 1
        except:
            pass
            
    lp_content = get_lp_content(product, target_index)
    
    with st.spinner("ペルソナを生成中..."):
        personas = generate_personas(ai_provider, prompt_manager, product, exposure_type)
    
    if not personas:
        st.error("ペルソナの生成に失敗しました")
        return

    evaluations = []
    progress_bar = st.progress(0)
    for i, persona in enumerate(personas):
        with st.spinner(f"ペルソナ「{persona['name']}」視点で評価中..."):
            eval_result = evaluate_by_persona(ai_provider, prompt_manager, product, exposure_type, persona, lp_content)
            evaluations.append(eval_result)
        progress_bar.progress((i + 1) / len(personas))
    
    with st.spinner("総合分析中..."):
        summary = generate_summary(ai_provider, prompt_manager, evaluations, exposure_type)
    
    # 結果を表示
    display_results(personas, evaluations, summary, exposure_type, key_suffix="new")

    # 診断完了後、保存
    if product_id:
        diagnosis_res = data_store.save_diagnosis(
            product_id=product_id,
            exposure_type=exposure_type,
            personas=personas,
            evaluations=evaluations,
            summary=summary
        )
        if diagnosis_res:
            st.success("診断結果を保存しました")
        else:
            st.warning("診断結果の保存に失敗しました（Supabase接続を確認してください）")

def render_diagnosis_page():
    page_header("LP Audit", "AIペルソナによる客観的なLPの診断と分析")

    data_store = DataStore()
    product_id = st.session_state.get('current_product_id')
    
    if not product_id:
        st.warning("製品を選択してください")
        st.stop()
        
    product = data_store.get_product(product_id)
    if not product:
        st.error("製品情報が見つかりません")
        st.stop()

    # 最新の診断を表示
    latest = data_store.get_latest_diagnosis(product_id)
    if latest:
        st.info(f"最終診断: {latest['created_at'][:10]} - {latest['exposure_type']}")
        with st.expander("前回の診断結果を見る"):
            display_results(latest['personas'], latest['evaluations'], latest['summary'], latest['exposure_type'], key_suffix="latest")

    st.subheader("診断設定")

    # 露出先選択
    exposure_type = st.radio(
        "露出先を選択",
        ["ECモール", "クラファン", "自社EC"],
        horizontal=True,
        help="どこで販売するかによって評価基準が変わります"
    )

    # 露出先の説明
    exposure_descriptions = {
        "ECモール": "🛒 Amazon・楽天など。競合と比較されることが前提。「なぜこれを選ぶべきか」が重要。",
        "クラファン": "🚀 Makuake・CAMPFIREなど。新規性と応援したくなるストーリーが重要。",
        "自社EC": "🏠 自社サイト。ブランドの世界観とファン化が重要。"
    }
    st.info(exposure_descriptions[exposure_type])

    # 診断対象選択
    raw_structure = product.get('structure', {})
    if isinstance(raw_structure, dict) and "result" in raw_structure:
        structure = raw_structure["result"]
    else:
        structure = raw_structure
        
    pages = structure.get('pages', []) if isinstance(structure, dict) else []

    diagnosis_target = st.selectbox(
        "診断対象",
        ["全ページ"] + [f"P{p.get('order', i+1)} - {p.get('title', '無題')}" for i, p in enumerate(pages)]
    )

    # タブ分け
    tab_persona, tab_employee = st.tabs(["👥 消費者ペルソナ診断", "🏢 従業員AI診断"])

    with tab_persona:
        # 診断実行ボタン
        if st.button("消費者ペルソナ診断を実行", type="primary", use_container_width=True):
            run_diagnosis(product, exposure_type, diagnosis_target)

    with tab_employee:
        render_employee_diagnosis_tab(product, exposure_type, diagnosis_target)

    # 改善案の生成と表示フロー (これは消費者ペルソナ診断の結果から呼ばれることが多い)
    if st.session_state.get('improvement_step') == 'generating':
        improvement = st.session_state.get('selected_improvement')
        if improvement:
            render_improvement_generation(product)

    if st.session_state.get('improvement_step') == 'review':
        render_improvement_review(product_id, data_store)

def render_employee_diagnosis_tab(product, exposure_type, diagnosis_target):
    """従業員AI診断タブのレンダリング"""
    ds = DataStore()
    employees = ds.get_employee_personas()
    
    if not employees:
        st.warning("従業員が登録されていません。設定ページで従業員を登録してください。")
        return

    st.subheader("評価メンバーを選択")
    selected_employee_ids = []
    
    # 従業員をグリッド表示
    cols_per_row = 4
    for i in range(0, len(employees), cols_per_row):
        row_emps = employees[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for j, emp in enumerate(row_emps):
            with cols[j]:
                if emp.get('avatar_url'):
                    st.image(emp['avatar_url'], width=80)
                else:
                    st.info("No Avatar")
                
                is_selected = st.checkbox(f"{emp['name']}", key=f"sel_emp_{emp['id']}")
                if is_selected:
                    selected_employee_ids.append(emp['id'])
                st.caption(f"_{emp['role']}_")

    if st.button("選択したメンバーで診断を開始", type="primary", use_container_width=True):
        if not selected_employee_ids:
            st.error("評価を行うメンバーを少なくとも1人選択してください")
        else:
            run_employee_diagnosis(product, exposure_type, diagnosis_target, selected_employee_ids)

    # 保存された結果があれば表示
    if 'employee_diagnosis_results' in st.session_state:
        # Build LP content text from product data
        lp_content_text = ""
        page_contents = product.get('page_contents') or {}
        if isinstance(page_contents, dict):
            for page_key, content in page_contents.items():
                if isinstance(content, str):
                    lp_content_text += content + "\n"
                elif isinstance(content, dict):
                    # 各ページのパース済みテキストや元のレスポンスから抽出
                    page_results = content.get('result', {})
                    if isinstance(page_results, dict) and 'parsed' in page_results:
                        lp_content_text += str(page_results['parsed']) + "\n"
                    else:
                        lp_content_text += str(content) + "\n"
        
        if not lp_content_text:
            structure = product.get('structure') or {}
            lp_content_text = str(structure)

        results = st.session_state.employee_diagnosis_results
        display_employee_results(results, product['id'], employees, exposure_type, lp_content_text)

def run_employee_diagnosis(product, exposure_type, diagnosis_target, employee_ids):
    """従業員AI診断を実行"""
    ds = DataStore()
    settings = SettingsManager().get_settings()
    ai_provider = AIProvider(settings)
    prompt_manager = PromptManager()
    
    # 全従業員から選択された人を抽出
    all_employees = ds.get_employee_personas()
    selected_employees = [e for e in all_employees if e['id'] in employee_ids]
    
    target_index = None
    if diagnosis_target != "全ページ":
        try:
            target_index = int(diagnosis_target.split(' ')[0][1:]) - 1
        except:
            pass
    lp_content = get_lp_content(product, target_index)
    
    results = []
    progress_bar = st.progress(0)
    for i, emp in enumerate(selected_employees):
        with st.spinner(f"{emp['name']}（{emp['role']}）が評価中..."):
            eval_result = evaluate_by_employee(ai_provider, prompt_manager, ds, product, exposure_type, emp, lp_content)
            if eval_result:
                results.append({
                    "employee": emp,
                    "evaluation": eval_result
                })
        progress_bar.progress((i + 1) / len(selected_employees))
    
    st.session_state.employee_diagnosis_results = results
    st.rerun()

def display_employee_results(results, product_id, employees_list, exposure_type, lp_content_text):
    """従業員AIの診断結果を表示"""
    ds = DataStore()
    
    st.markdown("---")
    st.subheader("🏢 従業員AIによる評価結果")
    
    for i, item in enumerate(results):
        emp = item['employee']
        employee_id = emp['id']
        eval_res = item['evaluation']
        
        # evaluation_text または raw_response を取得
        if isinstance(eval_res, dict):
            evaluation_text = eval_res.get('evaluation_text', eval_res.get('raw_response', ''))
            # 互換性：古い辞書形式の場合
            if not evaluation_text and 'voice' in eval_res:
                evaluation_text = f"**第一印象:** {eval_res.get('first_impression', '')}\n\n{eval_res.get('voice', '')}"
        else:
            evaluation_text = str(eval_res)

        with st.expander(f"**{emp['name']}** ({emp['role']})", expanded=True):
            col1, col2 = st.columns([1, 4])
            with col1:
                if emp.get('avatar_url'):
                    st.image(emp['avatar_url'], use_container_width=True)
            
            with col2:
                # Markdownを直接表示
                st.markdown(evaluation_text)
            
            # フィードバック入力
            st.markdown("---")
            st.markdown("💬 **AIへのフィードバック（学習）**")
            st.caption("AIの回答に違和感がある場合や、実際のアドバイスを入力してください。")
            
            user_fb = st.text_input("「実際はこう思う」「この視点が足りない」等を入力", key=f"fb_input_{emp['id']}_{i}")
            if st.button("フィードバックを送信", key=f"btn_fb_{emp['id']}_{i}"):
                if user_fb:
                    ds.add_employee_feedback({
                        "employee_id": emp['id'],
                        "product_id": product_id,
                        "ai_evaluation": evaluation_text[:500] if evaluation_text else "Markdown評価",
                        "user_feedback": user_fb
                    })
                    st.session_state[f'show_reevaluate_{emp["id"]}'] = True
                    st.session_state[f'employee_feedback_text_{emp["id"]}'] = user_fb
                    st.session_state[f'employee_prev_eval_{emp["id"]}'] = evaluation_text
                    st.success("フィードバックを保存しました。下の「再評価」ボタンでフィードバックを反映した評価を確認できます。")
                else:
                    st.error("フィードバック内容を入力してください")

            # Profile update section
            if st.session_state.get(f'show_reevaluate_{employee_id}'):
                st.divider()
                st.markdown("🎓 **従業員AIの成長（プロフィール更新）**")
                st.caption(f"フィードバック内容: {st.session_state.get(f'employee_feedback_text_{employee_id}', '')}")
                
                # Check if we already have update suggestions
                update_key = f'employee_update_suggestion_{employee_id}'
                
                if not st.session_state.get(update_key):
                    if st.button("🔄 プロフィール更新を提案", key=f"suggest_update_{employee_id}"):
                        with st.spinner("フィードバックを分析中..."):
                            try:
                                employee = next((e for e in employees_list if e.get('id') == employee_id), {})
                                settings = SettingsManager().get_settings()
                                ai = AIProvider(settings)
                                pm = PromptManager()
                                prompt_template = pm.get_prompt("employee_profile_update")
                                
                                if prompt_template:
                                    prompt = prompt_template.format(
                                        employee_name=employee.get('name', ''),
                                        employee_role=employee.get('role', ''),
                                        employee_expertise=employee.get('expertise', ''),
                                        employee_evaluation_perspective=employee.get('evaluation_perspective', ''),
                                        employee_personality_traits=employee.get('personality_traits', ''),
                                        employee_lifestyle=employee.get('lifestyle', '未設定'),
                                        employee_psychographic=employee.get('psychographic', '未設定'),
                                        employee_demographic=employee.get('demographic', '未設定'),
                                        employee_buying_behavior=employee.get('buying_behavior', '未設定'),
                                        employee_ng_points=employee.get('ng_points', '未設定'),
                                        previous_evaluation=st.session_state.get(f'employee_prev_eval_{employee_id}', ''),
                                        feedback=st.session_state.get(f'employee_feedback_text_{employee_id}', '')
                                    )
                                    
                                    result = ai.ask(prompt, "employee_profile_update")
                                    
                                    if result:
                                        # Parse JSON response
                                        import json
                                        if isinstance(result, str):
                                            # Clean markdown code blocks if present
                                            clean = result.strip()
                                            if clean.startswith("```"):
                                                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                                            if clean.endswith("```"):
                                                clean = clean[:-3]
                                            clean = clean.strip()
                                            if clean.startswith("json"):
                                                clean = clean[4:].strip()
                                            suggestion = json.loads(clean)
                                        else:
                                            suggestion = result
                                        
                                        st.session_state[update_key] = suggestion
                                        st.session_state[f'employee_current_profile_{employee_id}'] = {
                                            "expertise": employee.get('expertise', ''),
                                            "evaluation_perspective": employee.get('evaluation_perspective', ''),
                                            "personality_traits": employee.get('personality_traits', ''),
                                            "lifestyle": employee.get('lifestyle', ''),
                                            "psychographic": employee.get('psychographic', ''),
                                            "demographic": employee.get('demographic', ''),
                                            "buying_behavior": employee.get('buying_behavior', ''),
                                            "ng_points": employee.get('ng_points', ''),
                                        }
                                        st.rerun()
                                    else:
                                        st.error("更新提案の生成に失敗しました")
                                else:
                                    st.error("employee_profile_update プロンプトが見つかりません。プロンプト管理ページで追加してください。")
                            except json.JSONDecodeError as e:
                                st.error(f"AIの応答をJSONとして解析できませんでした: {e}")
                                st.code(result if isinstance(result, str) else str(result))
                            except Exception as e:
                                import traceback
                                st.error(f"プロフィール更新提案に失敗しました: {e}")
                                st.code(traceback.format_exc())
                
                # Display update suggestions if available
                if st.session_state.get(update_key):
                    suggestion = st.session_state[update_key]
                    current_profile = st.session_state.get(f'employee_current_profile_{employee_id}', {})
                    updates = suggestion.get('updates', {})
                    reasoning = suggestion.get('reasoning', '')
                    
                    if reasoning:
                        st.info(f"💡 **更新理由:** {reasoning}")
                    
                    # Field name mapping for display
                    field_labels = {
                        "expertise": "専門分野",
                        "evaluation_perspective": "評価の重点",
                        "personality_traits": "性格・口調",
                        "lifestyle": "ライフスタイル",
                        "psychographic": "価値観・関心",
                        "demographic": "基本属性",
                        "buying_behavior": "購買行動パターン",
                        "ng_points": "NGポイント",
                    }
                    
                    if updates:
                        for field_key, new_value in updates.items():
                            label = field_labels.get(field_key, field_key)
                            old_value = current_profile.get(field_key, '未設定')
                            
                            st.markdown(f"**{label}**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("📝 **変更前**")
                                st.warning(old_value if old_value else "（未設定）")
                            with col2:
                                st.markdown("✅ **変更後**")
                                st.success(new_value)
                            st.markdown("")
                        
                        # Apply button
                        col_apply, col_cancel = st.columns(2)
                        with col_apply:
                            if st.button("✅ この更新を適用", key=f"apply_update_{employee_id}", type="primary"):
                                try:
                                    ds.update_employee_persona(employee_id, updates)
                                    st.success("プロフィールを更新しました！次回の評価に反映されます。")
                                    # Clean up session state
                                    del st.session_state[update_key]
                                    if f'employee_current_profile_{employee_id}' in st.session_state:
                                        del st.session_state[f'employee_current_profile_{employee_id}']
                                    if f'show_reevaluate_{employee_id}' in st.session_state:
                                        del st.session_state[f'show_reevaluate_{employee_id}']
                                except Exception as e:
                                    st.error(f"更新に失敗しました: {e}")
                        with col_cancel:
                            if st.button("❌ キャンセル", key=f"cancel_update_{employee_id}"):
                                del st.session_state[update_key]
                                if f'show_reevaluate_{employee_id}' in st.session_state:
                                    del st.session_state[f'show_reevaluate_{employee_id}']
                                st.rerun()
                    else:
                        st.info("このフィードバックではプロフィールの更新は不要と判断されました。")

def render_improvement_generation(product):
    """改善案の生成フロー"""
    improvement = st.session_state.get('selected_improvement')
    with st.spinner("AIが改善案を生成中..."):
        settings = SettingsManager().get_settings()
        ai_provider = AIProvider(settings)
        prompt_manager = PromptManager()
        
        # 全ページの内容を取得してコンテキストにする
        pages_data = []
        page_contents = product.get('page_contents', {})
        raw_structure = product.get('structure', {})
        structure = raw_structure.get("result", raw_structure) if isinstance(raw_structure, dict) else {}
        pages = structure.get('pages', [])
        
        for p in pages:
            p_id = p.get('id')
            content = page_contents.get(p_id, {}).get("result", {}).get("parsed", {})
            pages_data.append({
                "id": p_id,
                "title": p.get('title'),
                "content": content
            })
        
        proposal = generate_improvement_proposal(ai_provider, prompt_manager, product, improvement['text'], pages_data)
        if proposal:
            st.session_state['improvement_proposal'] = proposal
            st.session_state['improvement_step'] = 'review'
            st.rerun()
        else:
            st.error("改善案の生成に失敗しました")
            st.session_state['improvement_step'] = None

def render_improvement_review(product_id, data_store):
    """改善案のレビューフロー"""
    proposal = st.session_state.get('improvement_proposal')
    if proposal:
        st.markdown("---")
        st.markdown("### 📝 改善案")
        st.markdown(f"""
📍 **対象箇所**
- **ページ**: {proposal.get('target_page_index', 0) + 1}. {proposal.get('target_page_name', '不明')}
- **要素**: {proposal.get('target_element_type', '不明')}（{proposal.get('target_element_index', 0) + 1}番目）
""")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**修正前**")
            st.error(proposal.get('before_text', 'なし'))
        with col2:
            st.markdown("**修正後**")
            st.success(proposal.get('after_text', 'なし'))
        
        st.info(f"💡 {proposal.get('reason', '')}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("この内容で反映", type="primary"):
                success = apply_improvement(
                    product_id,
                    data_store,
                    proposal.get('target_page_index', 0),
                    proposal.get('target_element_index', 0),
                    proposal.get('after_text', '')
                )
                if success:
                    st.success("反映しました！")
                    # ステートをクリア
                    for k in ['selected_improvement', 'improvement_proposal', 'improvement_step']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()
                else:
                    st.error("反映に失敗しました。対象ページや構成が見つからない可能性があります。")
        
        with col2:
            if st.button("やり直し"):
                st.session_state['improvement_step'] = 'generating'
                st.rerun()
        
        with col3:
            if st.button("キャンセル"):
                for k in ['selected_improvement', 'improvement_proposal', 'improvement_step']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

if __name__ == "__main__":
    render_diagnosis_page()
