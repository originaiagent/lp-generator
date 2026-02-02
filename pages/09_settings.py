import streamlit as st
from modules.styles import apply_styles, page_header
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(page_title="Settings", layout="wide")

# スタイル適用
apply_styles()

# AIサイドバー表示
render_ai_sidebar()


import json
import os
from modules.settings_manager import SettingsManager

MODELS_FILE = "data/models.json"

DOCS_LINKS = {
    "anthropic": "https://docs.anthropic.com/en/docs/about-claude/models",
    "openai": "https://platform.openai.com/docs/models",
    "gemini": "https://ai.google.dev/gemini-api/docs/models/gemini",
}

PRICING_LINKS = {
    "anthropic": "https://www.anthropic.com/pricing",
    "openai": "https://openai.com/api/pricing/",
    "gemini": "https://ai.google.dev/pricing",
}

def load_models():
    if os.path.exists(MODELS_FILE):
        with open(MODELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"llm": {}, "image": {}}


def render_usage_stats(settings_manager, settings):
    """API使用状況を表示"""
    from modules.usage_tracker import UsageTracker
    import json
    
    tracker = UsageTracker()
    
    # 料金データを読み込み
    try:
        with open("data/pricing.json", "r", encoding="utf-8") as f:
            pricing_data = json.load(f)
    except:
        pricing_data = {}
    
    st.subheader("📊 API使用状況")
    
    # 今日の使用量
    today = tracker.get_today_usage()
    total = today.get("total", {})
    image_gen = today.get("image_generation", {"count": 0, "cost_jpy": 0})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("入力トークン", f"{total.get('input_tokens', 0):,}")
    with col2:
        st.metric("出力トークン", f"{total.get('output_tokens', 0):,}")
    with col3:
        st.metric("画像生成", f"{image_gen.get('count', 0)}枚")
    with col4:
        st.metric("合計コスト", f"¥{total.get('cost_jpy', 0):.2f}")
    
    st.markdown("---")
    
    # プロバイダー別
    st.subheader("プロバイダー別内訳")
    by_provider = today.get("by_provider", {})
    if by_provider:
        cols = st.columns(len(by_provider))
        for i, (provider, data) in enumerate(by_provider.items()):
            with cols[i]:
                st.markdown(f"**{provider.upper()}**")
                st.caption(f"入力: {data.get('input', 0):,}")
                st.caption(f"出力: {data.get('output', 0):,}")
                st.caption(f"¥{data.get('cost', 0):.2f}")
    else:
        st.info("まだ使用データがありません")
    
    st.markdown("---")
    
    # 料金設定
    st.subheader("💰 料金設定")
    
    col1, col2 = st.columns([2, 1])
    with col2:
        usd_to_jpy = pricing_data.get("usd_to_jpy", 150)
        new_rate = st.number_input("為替レート (USD/JPY)", value=usd_to_jpy, min_value=100, max_value=200)
        if new_rate != usd_to_jpy:
            pricing_data["usd_to_jpy"] = new_rate
            with open("data/pricing.json", "w", encoding="utf-8") as f:
                json.dump(pricing_data, f, ensure_ascii=False, indent=2)
            st.success("為替レート更新")
            st.rerun()
        
        st.caption(f"最終更新: {pricing_data.get('last_updated', '不明')}")
    
    # テキスト生成料金（編集可能）
    with st.expander("📝 テキスト生成料金 ($/100万トークン)", expanded=False):
        text_pricing = pricing_data.get("text_generation", {})
        pricing_changed = False
        
        for provider, models in text_pricing.items():
            st.markdown(f"**{provider.upper()}**")
            for model, rates in models.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.caption(model)
                with col2:
                    new_input = st.number_input(
                        f"入力", 
                        value=float(rates.get('input', 0)), 
                        min_value=0.0, 
                        step=0.1,
                        key=f"price_in_{provider}_{model}",
                        label_visibility="collapsed"
                    )
                with col3:
                    new_output = st.number_input(
                        f"出力",
                        value=float(rates.get('output', 0)),
                        min_value=0.0,
                        step=0.1,
                        key=f"price_out_{provider}_{model}",
                        label_visibility="collapsed"
                    )
                if new_input != rates.get('input', 0) or new_output != rates.get('output', 0):
                    text_pricing[provider][model] = {"input": new_input, "output": new_output}
                    pricing_changed = True
        
        if pricing_changed:
            pricing_data["text_generation"] = text_pricing
            with open("data/pricing.json", "w", encoding="utf-8") as f:
                json.dump(pricing_data, f, ensure_ascii=False, indent=2)
            st.success("料金設定を更新しました")
            st.rerun()
    
    # 画像生成料金（編集可能）
    with st.expander("🖼️ 画像生成料金 ($/100万トークン)", expanded=False):
        st.caption("※ 最新APIはトークンベース料金です")
        image_pricing = pricing_data.get("image_generation", {})
        img_pricing_changed = False
        
        for model, rates in image_pricing.items():
            st.markdown(f"**{model}**")
            if isinstance(rates, dict):
                for rate_type, price in rates.items():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.caption(rate_type)
                    with col2:
                        new_price = st.number_input(
                            f"価格",
                            value=float(price),
                            min_value=0.0,
                            step=0.01,
                            key=f"img_price_{model}_{rate_type}",
                            label_visibility="collapsed"
                        )
                    if new_price != price:
                        image_pricing[model][rate_type] = new_price
                        img_pricing_changed = True
        
        if img_pricing_changed:
            pricing_data["image_generation"] = image_pricing
            with open("data/pricing.json", "w", encoding="utf-8") as f:
                json.dump(pricing_data, f, ensure_ascii=False, indent=2)
            st.success("画像生成料金を更新しました")
            st.rerun()
    
    # 料金ページリンク
    st.markdown("---")
    st.subheader("🔗 各社料金ページ")
    st.caption("最新料金はこちらで確認してください")
    
    urls = pricing_data.get("pricing_urls", {})
    cols = st.columns(3)
    with cols[0]:
        st.link_button("Anthropic", urls.get("anthropic", "#"))
    with cols[1]:
        st.link_button("OpenAI", urls.get("openai", "#"))
    with cols[2]:
        st.link_button("Google AI", urls.get("google", "#"))

def render_settings_page():
    page_header("Settings", "システム設定と従業員AIの管理")
    
    settings_manager = SettingsManager()
    settings = settings_manager.get_settings()
    models_config = load_models()
    
    # モデル更新ボタン（上部に配置）
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button('🔄 モデル一覧を更新', key='refresh_models'):
            refresh_models()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["LLM設定", "画像生成", "APIキー", "使用状況", "要素タイプ", "従業員AI"])
    
    with tab1:
        render_llm_settings(settings_manager, settings, models_config)
    
    with tab2:
        render_image_settings(settings_manager, settings, models_config)
    
    with tab3:
        render_api_key_status()
    
    with tab4:
        render_usage_stats(settings_manager, settings)
    
    with tab5:
        render_element_types()

    with tab6:
        render_employee_settings()

def render_employee_settings():
    """従業員AIの管理UI"""
    from modules.data_store import DataStore
    import uuid
    
    st.markdown('<div class="step-header">従業員AI管理</div>', unsafe_allow_html=True)
    st.caption("社内の各役割（営業、エンジニア、サポート等）をシミュレートするAI従業員を管理します")
    
    ds = DataStore()
    employees = ds.get_employee_personas()
    
    # 既存の従業員リスト
    st.subheader("登録済み従業員")
    if not employees:
        st.info("登録されている従業員はいません。")
    else:
        for emp in employees:
            with st.expander(f"{emp['name']} - {emp['role']}", expanded=False):
                col1, col2 = st.columns([1, 3])
                with col1:
                    if emp.get('avatar_url'):
                        st.image(emp['avatar_url'], width=100)
                    else:
                        st.info("No Avatar")
                
                with col2:
                    st.write(f"**専門分野:** {emp['expertise']}")
                    st.write(f"**評価の重点:** {emp['evaluation_perspective']}")
                    st.write(f"**性格・口調:** {emp['personality_traits']}")
                    
                    # フィードバック件数を取得（後で実装予定のメソッドを使用）
                    feedback = ds.get_employee_feedback(emp['id'], limit=100)
                    st.caption(f"フィードバック受領数: {len(feedback)}件")
                    
                    if st.button("編集", key=f"edit_emp_{emp['id']}"):
                        st.session_state.editing_employee = emp
                        st.rerun()
                    
                    if st.button("削除", key=f"del_emp_{emp['id']}", type="secondary"):
                        if ds.delete_employee_persona(emp['id']):
                            st.success(f"{emp['name']}を削除しました")
                            st.rerun()

    st.markdown("---")
    
    # 新規追加 / 編集フォーム
    is_editing = 'editing_employee' in st.session_state
    st.subheader("従業員の" + ("構成を編集" if is_editing else "新規登録"))
    
    with st.form("employee_form", clear_on_submit=not is_editing):
        emp_to_edit = st.session_state.get('editing_employee', {})
        
        name = st.text_input("名前", value=emp_to_edit.get('name', ''))
        role = st.text_input("役割・役職", value=emp_to_edit.get('role', ''), placeholder="例: ベテラン営業部長")
        expertise = st.text_area("専門分野", value=emp_to_edit.get('expertise', ''), placeholder="例: 法人営業、クロージング戦略")
        perspective = st.text_area("評価の重点", value=emp_to_edit.get('evaluation_perspective', ''), placeholder="例: 費用対効果、現実的な導入スケジュール、競合比較")
        personality = st.text_area("性格・口調", value=emp_to_edit.get('personality_traits', ''), placeholder="例: 歯に衣着せぬ物言い、論理的、語尾に「〜ですね」をつける")
        
        # アバターアップロード
        avatar_file = st.file_uploader("プロフィール画像", type=['jpg', 'jpeg', 'png'])
        
        submitted = st.form_submit_button("保存する")
        if submitted:
            if not name:
                st.error("名前は必須です")
            else:
                emp_id = emp_to_edit.get('id', str(uuid.uuid4()))
                avatar_url = emp_to_edit.get('avatar_url')
                
                # 画像アップロード処理
                if avatar_file:
                    file_bytes = avatar_file.read()
                    file_ext = avatar_file.name.split('.')[-1]
                    path = f"employees/{emp_id}/avatar.{file_ext}"
                    uploaded_url = ds.upload_image(file_bytes, path)
                    if uploaded_url:
                        avatar_url = uploaded_url
                
                new_emp_data = {
                    "id": emp_id,
                    "name": name,
                    "role": role,
                    "expertise": expertise,
                    "evaluation_perspective": perspective,
                    "personality_traits": personality,
                    "avatar_url": avatar_url,
                    "is_active": True
                }
                
                if ds.upsert_employee_persona(new_emp_data):
                    st.success("従業員情報を保存しました！")
                    if is_editing:
                        del st.session_state.editing_employee
                    st.rerun()
                else:
                    st.error("保存に失敗しました。")

    if is_editing:
        if st.button("キャンセル"):
            del st.session_state.editing_employee
            st.rerun()

def render_element_types():
    """要素タイプの管理UI"""
    from modules.element_types import ElementTypes
    
    st.markdown('<div class="step-header">要素タイプ管理</div>', unsafe_allow_html=True)
    st.caption("LP分析で使用する要素タイプのカテゴリ分けを管理します")
    
    elem_types = ElementTypes()
    categories = elem_types.get_categories_info()
    
    for cat_id, cat_data in categories.items():
        with st.expander(f"**{cat_data.get('name', cat_id)}** - {cat_data.get('description', '')}", expanded=False):
            types_list = cat_data.get('types', [])
            
            # 現在の要素タイプを表示
            for i, t in enumerate(types_list):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(t)
                with col2:
                    if st.button("🗑️", key=f"del_{cat_id}_{i}"):
                        elem_types.remove_type(cat_id, t)
                        st.rerun()
            
            # 新規追加
            col1, col2 = st.columns([3, 1])
            with col1:
                new_type = st.text_input("新しい要素タイプ", key=f"new_{cat_id}", label_visibility="collapsed", placeholder="新しい要素タイプ名")
            with col2:
                if st.button("➕ 追加", key=f"add_{cat_id}"):
                    if new_type:
                        elem_types.add_type(cat_id, new_type)
                        st.rerun()

def refresh_models():
    """APIからモデル一覧を取得して更新"""
    with st.spinner('最新モデル一覧を取得中...'):
        try:
            from modules.model_fetcher import ModelFetcher
            fetcher = ModelFetcher()
            models = fetcher.fetch_and_save()
            
            # 料金設定も同期
            sync_pricing_with_models(models)
            
            llm_count = sum(len(v) for v in models.get("llm", {}).values())
            image_count = sum(len(v) for v in models.get("image", {}).values())
            
            st.success(f'✅ 更新完了！ LLM: {llm_count}モデル, 画像: {image_count}モデル')
            st.rerun()
        except Exception as e:
            st.error(f'更新エラー: {str(e)}')

def sync_pricing_with_models(models):
    """models.jsonとpricing.jsonを同期"""
    from datetime import datetime
    
    try:
        with open("data/pricing.json", "r", encoding="utf-8") as f:
            pricing = json.load(f)
    except:
        pricing = {"text_generation": {}, "image_generation": {}, "usd_to_jpy": 150, "pricing_urls": {}}
    
    provider_map = {"anthropic": "claude", "openai": "gpt", "gemini": "gemini"}
    
    # テキスト生成モデルの同期
    for provider, model_list in models.get("llm", {}).items():
        pricing_key = provider_map.get(provider, provider)
        if pricing_key not in pricing.get("text_generation", {}):
            pricing["text_generation"][pricing_key] = {}
        
        for model in model_list:
            model_id = model["id"]
            if model_id not in pricing["text_generation"][pricing_key]:
                pricing["text_generation"][pricing_key][model_id] = {"input": 0.0, "output": 0.0}
    
    # 画像生成モデルの同期
    if "image_generation" not in pricing:
        pricing["image_generation"] = {}
    
    for provider, model_list in models.get("image", {}).items():
        for model in model_list:
            model_id = model["id"]
            if model_id not in pricing["image_generation"]:
                pricing["image_generation"][model_id] = {"input": 0.0, "output": 0.0}
    
    pricing["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    
    with open("data/pricing.json", "w", encoding="utf-8") as f:
        json.dump(pricing, f, ensure_ascii=False, indent=2)

def render_llm_settings(settings_manager, settings, models_config):
    st.subheader("LLM設定")
    
    providers = ["anthropic", "openai", "gemini"]
    provider_names = {
        "anthropic": "Anthropic (Claude)",
        "openai": "OpenAI (GPT)",
        "gemini": "Google (Gemini)"
    }
    
    current_provider = settings.get("llm_provider", "anthropic")
    if current_provider not in providers:
        current_provider = "anthropic"
    
    provider = st.selectbox(
        "プロバイダ",
        providers,
        index=providers.index(current_provider),
        format_func=lambda x: provider_names.get(x, x),
        key="llm_provider_select"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"[📖 モデル一覧]({DOCS_LINKS.get(provider, '#')})")
    with col2:
        st.markdown(f"[💰 料金表]({PRICING_LINKS.get(provider, '#')})")
    
    llm_models = models_config.get("llm", {}).get(provider, [])
    model_ids = [m["id"] for m in llm_models]
    model_names = {m["id"]: f"{m['name']} - {m['desc']}" for m in llm_models}
    
    current_model = settings.get("llm_model", "")
    
    use_custom = st.checkbox("カスタムモデルを使用", key="llm_custom_check", 
                             value=current_model not in model_ids and current_model != "")
    
    if use_custom:
        model = st.text_input(
            "モデルID（直接入力）",
            value=current_model,
            placeholder="例: claude-3-5-sonnet-20241022",
            key="llm_model_custom"
        )
        st.caption("↑ 上のリンクから最新モデルIDを確認できます")
    else:
        if not model_ids:
            st.warning("モデル一覧がありません。「モデル一覧を更新」ボタンを押してください。")
            model = ""
        else:
            if current_model in model_ids:
                default_idx = model_ids.index(current_model)
            else:
                default_idx = 0
            
            model = st.selectbox(
                "モデル",
                model_ids,
                index=default_idx,
                format_func=lambda x: model_names.get(x, x),
                key="llm_model_select"
            )
    
    if st.button("LLM設定を保存", key="save_llm", type="primary"):
        settings["llm_provider"] = provider
        settings["llm_model"] = model
        settings_manager.update_settings(settings)
        st.success("保存しました")
    
    st.markdown("---")
    st.caption(f"現在: {settings.get('llm_provider', 'なし')} / {settings.get('llm_model', 'なし')}")
    
    # タスク別モデル設定
    st.markdown("---")
    st.subheader("🎯 タスク別モデル設定")
    st.caption("特定のタスクに別のモデルを使用できます（画像認識には高精度モデル推奨）")
    
    task_models = settings.get("task_models", {})
    current_image_model = task_models.get("image_analysis", "")
    current_image_provider = task_models.get("image_analysis_provider", "")
    
    use_same = st.checkbox("画像分析もデフォルトモデルを使用", 
                           value=current_image_model == "",
                           key="use_same_model")
    
    if not use_same:
        task_providers = ["anthropic", "openai", "gemini"]
        task_provider_names = {
            "anthropic": "Anthropic (Claude)",
            "openai": "OpenAI (GPT)",
            "gemini": "Google (Gemini)"
        }
        
        if current_image_provider not in task_providers:
            current_image_provider = "gemini"
        
        task_provider = st.selectbox(
            "画像分析用プロバイダ",
            task_providers,
            index=task_providers.index(current_image_provider),
            format_func=lambda x: task_provider_names.get(x, x),
            key="task_provider_select"
        )
        
        task_llm_models = models_config.get("llm", {}).get(task_provider, [])
        task_model_ids = [m["id"] for m in task_llm_models]
        task_model_names = {m["id"]: f"{m['name']} - {m['desc']}" for m in task_llm_models}
        
        use_task_custom = st.checkbox("カスタムモデルを使用", key="task_custom_check",
                                      value=current_image_model not in task_model_ids and current_image_model != "")
        
        if use_task_custom:
            image_model = st.text_input(
                "モデルID（直接入力）",
                value=current_image_model,
                placeholder="例: gemini-1.5-pro",
                key="task_model_custom"
            )
        else:
            if not task_model_ids:
                st.warning("モデル一覧がありません")
                image_model = ""
            else:
                if current_image_model in task_model_ids:
                    default_idx = task_model_ids.index(current_image_model)
                else:
                    default_idx = 0
                
                image_model = st.selectbox(
                    "画像分析用モデル",
                    task_model_ids,
                    index=default_idx,
                    format_func=lambda x: task_model_names.get(x, x),
                    key="task_model_select"
                )
    else:
        image_model = ""
        task_provider = ""
    
    if st.button("タスク別設定を保存", key="save_task_models", type="primary"):
        if not use_same and image_model:
            task_models["image_analysis"] = image_model
            task_models["image_analysis_provider"] = task_provider
        else:
            task_models.pop("image_analysis", None)
            task_models.pop("image_analysis_provider", None)
        settings["task_models"] = task_models
        settings_manager.update_settings(settings)
        st.success("保存しました")
    
    if task_models.get("image_analysis"):
        st.caption(f"画像分析: {task_models.get('image_analysis_provider', '')} / {task_models.get('image_analysis')}")
    else:
        st.caption("画像分析: デフォルトモデルを使用")

def render_image_settings(settings_manager, settings, models_config):
    st.subheader("画像生成AI設定")
    
    providers = ["auto", "openai", "gemini"]
    provider_names = {
        "auto": "自動選択",
        "openai": "OpenAI (DALL-E)",
        "gemini": "Google (Imagen)"
    }
    
    current_provider = settings.get("image_provider", "auto")
    if current_provider not in providers:
        current_provider = "auto"
    
    image_provider = st.selectbox(
        "プロバイダ",
        providers,
        index=providers.index(current_provider),
        format_func=lambda x: provider_names.get(x, x),
        key="image_provider_select"
    )
    
    if image_provider != "auto":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"[📖 モデル一覧]({DOCS_LINKS.get(image_provider, '#')})")
        with col2:
            st.markdown(f"[💰 料金表]({PRICING_LINKS.get(image_provider, '#')})")
    
    image_model = None
    
    if image_provider != "auto":
        image_models = models_config.get("image", {}).get(image_provider, [])
        model_ids = [m["id"] for m in image_models]
        model_names = {m["id"]: f"{m['name']} - {m['desc']}" for m in image_models}
        
        current_model = settings.get("image_model", "")
        
        use_custom = st.checkbox("カスタムモデルを使用", key="image_custom_check",
                                 value=current_model not in model_ids and current_model != "")
        
        if use_custom:
            image_model = st.text_input(
                "モデルID（直接入力）",
                value=current_model,
                placeholder="例: nano-banana-pro-preview",
                key="image_model_custom"
            )
            st.caption("↑ 上のリンクから最新モデルIDを確認できます")
        else:
            if not model_ids:
                st.warning("モデル一覧がありません。「モデル一覧を更新」ボタンを押してください。")
                image_model = ""
            else:
                if current_model in model_ids:
                    default_idx = model_ids.index(current_model)
                else:
                    default_idx = 0
                
                image_model = st.selectbox(
                    "モデル",
                    model_ids,
                    index=default_idx,
                    format_func=lambda x: model_names.get(x, x),
                    key="image_model_select"
                )
    else:
        st.info("利用可能なAPIを自動で選択します")
    
    from modules.image_generator import ImageGenerator
    current_gen = ImageGenerator(image_provider)
    st.write(f"**現在使用中:** {current_gen.get_provider_name()}")
    
    if st.button("画像生成設定を保存", key="save_image", type="primary"):
        settings["image_provider"] = image_provider
        if image_model:
            settings["image_model"] = image_model
        settings_manager.update_settings(settings)
        st.success("保存しました")
    
    st.markdown("---")
    st.caption(f"現在: {settings.get('image_provider', 'auto')} / {settings.get('image_model', '自動')}")
    
    with st.expander("💰 画像生成コスト目安"):
        st.markdown("""
        | モデル | 1枚あたり |
        |--------|-----------|
        | DALL-E 3 | $0.04〜0.08 |
        | Imagen 4.0 | 従量課金 |
        | Nano Banana Pro | 従量課金 |
        """)

def render_api_key_status():
    st.subheader("APIキー状態")
    
    keys = {
        "OpenAI (GPT, DALL-E)": os.environ.get('OPENAI_API_KEY'),
        "Anthropic (Claude)": os.environ.get('ANTHROPIC_API_KEY'),
        "Google (Gemini, Imagen)": os.environ.get('GOOGLE_API_KEY')
    }
    
    for name, key in keys.items():
        if key:
            st.success(f"✅ {name}: 設定済み")
        else:
            st.warning(f"⚠️ {name}: 未設定")
    
    st.markdown("---")
    
    # Supabase接続状態チェック
    from modules.data_store import DataStore
    ds = DataStore()
    
    if ds.use_supabase:
        st.success("✅ Supabase設定: 有効 (REST APIモード)")
        # 通信テスト
        try:
            # count取得を試みる
            import requests
            headers = ds.headers
            url = f"{ds.base_url}/lp_products?select=id&limit=1"
            res = requests.get(url, headers=headers, timeout=5)
            
            if res.status_code == 200:
                st.success("✅ Supabase接続: 成功")
                st.caption(f"ステータスコード: {res.status_code}")
            else:
                st.error(f"❌ Supabase接続: エラー (Code: {res.status_code})")
                st.caption(res.text)
        except Exception as e:
            st.error(f"❌ Supabase接続: 通信エラー ({e})")
    else:
        st.error("❌ Supabase設定: 無効（環境変数が設定されていません）")
    
    st.markdown("---")
    st.info("APIキーはStreamlit CloudのSecretsで設定してください")
    
    with st.expander("💰 LLMコスト目安 (1Mトークンあたり)"):
        st.markdown("""
        | モデル | 入力 | 出力 |
        |--------|------|------|
        | Claude 3.5 Sonnet | $3 | $15 |
        | GPT-4o | $2.5 | $10 |
        | GPT-4o mini | $0.15 | $0.6 |
        | Gemini 1.5 Flash | $0.075 | $0.3 |
        """)



render_settings_page()
