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

def generate_personas(ai_provider, product, exposure_type):
    """商品と露出先に応じたペルソナを生成"""
    
    prompt = f"""
あなたはマーケティングリサーチの専門家です。

【商品情報】
製品名: {product.get('name', '')}
説明: {product.get('description', '')}
カテゴリ: {product.get('category', '')}

【露出先】
{exposure_type}

【指示】
この商品を{exposure_type}で見る可能性のある、異なるタイプの購買検討者を3〜4人設定してください。

以下の多様性を考慮：
- 購買意欲: 高/中/低
- 重視点: 価格/品質/時短/デザイン/新しさ
- 商品への態度: 積極的/慎重/懐疑的

【出力形式】JSONのみ
{{
  "personas": [
    {{
      "name": "ペルソナの短い説明（例：30代主婦・時短重視）",
      "age": "年代",
      "occupation": "職業・状況",
      "motivation": "この商品を見ている理由",
      "concerns": "購入にあたっての不安・懸念",
      "decision_style": "購買決定スタイル（即決/比較検討/慎重）",
      "budget_sensitivity": "価格感度（高/中/低）"
    }}
  ]
}}
"""
    
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

def evaluate_by_persona(ai_provider, product, exposure_type, persona, lp_content):
    """各ペルソナ視点でLPを評価"""
    
    # 競合情報を取得
    comp_v2 = product.get('competitor_analysis_v2', {})
    competitors = comp_v2.get('competitors', [])
    if not competitors:
        competitors = product.get('competitors', [])
    
    # 露出先別の評価重点
    exposure_focus = {
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
    
    prompt = f"""
あなたは以下のペルソナになりきって、このLPを見た感想を述べてください。

【あなたのプロフィール】
{persona['name']}
年代: {persona['age']}
職業: {persona['occupation']}
この商品を見ている理由: {persona['motivation']}
購入にあたっての不安: {persona['concerns']}
購買スタイル: {persona['decision_style']}
価格感度: {persona['budget_sensitivity']}

【露出先】
{exposure_type}

【この露出先で特に重要な評価ポイント】
{exposure_focus.get(exposure_type, "")}

【LP内容】
{lp_content}

【競合情報】
{str(competitors)[:1000]}

【指示】
このLPを見た率直な感想を、このペルソナの口調で述べてください。

【出力形式】JSONのみ
{{
  "overall_rating": 5段階評価（1-5）,
  "purchase_decision": "買う / 迷う / 買わない",
  "first_impression": "第一印象（3秒で感じたこと）",
  "voice": "このペルソナの生の声（2-3文で自然な口語体で）",
  "resonated_points": ["響いたポイント1", "響いたポイント2"],
  "concerns": ["不安・懸念1", "不安・懸念2"],
  "vs_competitors": "競合と比べた印象（1文）",
  "improvement_suggestion": "こうなってたら買うのに（1文）"
}}
"""
    
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

def generate_summary(ai_provider, evaluations, exposure_type):
    """全ペルソナの評価を総合分析"""
    
    prompt = f"""
以下は複数のペルソナによるLP評価結果です。

【露出先】
{exposure_type}

【各ペルソナの評価】
{json.dumps(evaluations, ensure_ascii=False, indent=2)}

【指示】
これらの評価を総合して、LPの改善点を分析してください。

【出力形式】JSONのみ
{{
  "purchase_rate": "購入検討率（〇人中〇人）",
  "strengths": ["強み1", "強み2"],
  "weaknesses": ["弱み1", "弱み2"],
  "competitor_comparison": "競合との比較での印象",
  "improvements": [
    {{"priority": "高", "content": "改善点1"}},
    {{"priority": "中", "content": "改善点2"}},
    {{"priority": "低", "content": "改善点3"}}
  ],
  "overall_advice": "総合アドバイス（2-3文）"
}}
"""
    
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

def display_results(personas, evaluations, summary, exposure_type):
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
        for imp in summary.get('improvements', []):
            priority_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(imp.get('priority'), "⚪")
            st.write(f"{priority_icon} [{imp.get('priority', '')}] {imp.get('content', '')}")
        
        st.markdown("**💡 総合アドバイス**")
        st.success(summary.get('overall_advice', ''))

def run_diagnosis(product, exposure_type, diagnosis_target):
    """LP診断を実行"""
    
    data_store = DataStore()
    product_id = product.get('id')
    settings = SettingsManager().get_settings()
    ai_provider = AIProvider(settings)
    
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
        personas = generate_personas(ai_provider, product, exposure_type)
    
    if not personas:
        st.error("ペルソナの生成に失敗しました")
        return

    evaluations = []
    progress_bar = st.progress(0)
    for i, persona in enumerate(personas):
        with st.spinner(f"ペルソナ「{persona['name']}」視点で評価中..."):
            eval_result = evaluate_by_persona(ai_provider, product, exposure_type, persona, lp_content)
            evaluations.append(eval_result)
        progress_bar.progress((i + 1) / len(personas))
    
    with st.spinner("総合分析中..."):
        summary = generate_summary(ai_provider, evaluations, exposure_type)
    
    # 結果を表示
    display_results(personas, evaluations, summary, exposure_type)

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
            display_results(latest['personas'], latest['evaluations'], latest['summary'], latest['exposure_type'])

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

    # 診断実行ボタン
    if st.button("診断を実行", type="primary", use_container_width=True):
        run_diagnosis(product, exposure_type, diagnosis_target)

if __name__ == "__main__":
    render_diagnosis_page()
