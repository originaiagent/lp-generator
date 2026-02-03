import streamlit as st
from datetime import datetime

def save_with_trace(result, prompt_id, prompt_used=None, input_refs=None, model="unknown"):
    """生成結果にトレース情報を付与して返す"""
    return {
        "result": result,
        "trace": {
            "prompt_id": prompt_id,
            "input_refs": input_refs,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": model
        }
    }

def show_trace(data, label="生成情報"):
    """トレース情報を折りたたみで表示"""
    if not data or "trace" not in data:
        return
    
    trace = data["trace"]
    
    with st.expander(f"📝 {label}を確認", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**プロンプトID:** `{trace.get('prompt_id', '不明')}`")
            st.write(f"**生成日時:** {trace.get('generated_at', '不明')}")
        with col2:
            st.write(f"**使用モデル:** {trace.get('model', '不明')}")
        
        st.markdown("**📊 参照データ:**")
        input_refs = trace.get("input_refs", {})
        for key, value in input_refs.items():
            if isinstance(value, str) and len(value) > 100:
                st.write(f"- **{key}:** {value[:100]}...")
            else:
                st.write(f"- **{key}:** {value}")
        
        # プロンプト全文の表示は廃止（DBサイズ削減のため）
        pass


def show_lp_analysis(data):
    """LP分析結果を人間が読みやすい形式で表示（専門用語対応）"""
    if not data:
        return
    
    result = data.get("result", data) if isinstance(data, dict) else data
    if not isinstance(result, dict):
        st.write(result)
        return
    
    # ページ種別
    page_type = result.get("page_type", "不明")
    st.markdown(f"### 【{page_type}】")
    
    # 要素タイプのアイコンマッピング
    type_icons = {
        # テキスト系
        "メインキャッチコピー": "🎯",
        "リードコピー": "📝",
        "タグライン": "🏷️",
        "サブヘッド": "📌",
        "ボディコピー": "📄",
        "ブレット": "✅",
        "注意書き": "⚠️",
        # 信頼系
        "ソーシャルプルーフ": "⭐",
        "トラストバッジ": "🛡️",
        "権威付け": "👑",
        # アクション系
        "CTA": "🔘",
        "オファー": "💰",
        # ビジュアル系
        "メインビジュアル": "🖼️",
        "サブビジュアル": "🎨",
        "アイコン": "🔷",
        "装飾": "✨",
        # 旧形式互換
        "見出し": "📌",
        "キャッチコピー": "🎯",
        "説明文": "📄",
        "表": "📊",
        "チェックリスト": "✅",
        "画像": "🖼️",
    }
    
    # 新形式（elements）対応
    elements = result.get("elements", [])
    if elements:
        st.markdown("**📝 要素一覧**")
        for elem in elements:
            order = elem.get("order", "")
            # type または element_type を取得
            elem_type = elem.get("type", elem.get("element_type", ""))
            content = elem.get("content", "")
            items = elem.get("items", [])
            item_count = elem.get("item_count", len(items))
            char_count = elem.get("char_count", 0)
            layout = elem.get("layout", "")
            has_icon = elem.get("has_icon", False)
            aim = elem.get("aim", "")
            effect = elem.get("effect", "")
            
            # アイコン取得
            icon = type_icons.get(elem_type, "📍")
            
            # 表示
            if elem_type in ["表", "ブレット", "チェックリスト"] or items:
                layout_str = f" ({layout})" if layout else ""
                st.markdown(f"**{order}. {icon} [{elem_type}] {item_count}項目**{layout_str}")
                if items:
                    for item in items:
                        st.markdown(f"　　- {item}")
            else:
                content_str = str(content) if content else ""
                char_str = f"（{char_count}文字）" if char_count else ""
                st.markdown(f"**{order}. {icon} [{elem_type}]** {content_str} {char_str}")
            
            if aim or effect:
                st.caption(f"　狙い: {aim} → 効果: {effect}")
        
        # デザインノート
        design_notes = result.get("design_notes", "")
        if design_notes:
            st.markdown(f"**🎨 デザイン特徴:** {design_notes}")
        return
    
    # 旧形式（texts）対応
    texts = result.get("texts", [])
    if texts:
        st.markdown("**📝 テキスト要素**")
        for t in texts:
            type_str = t.get("type", "")
            size = t.get("size", "")
            content = t.get("content", "")
            items = t.get("items", [])
            item_count = t.get("item_count", len(items))
            char_count = t.get("char_count", "")
            char_per_item = t.get("char_per_item", "")
            aim = t.get("aim", "")
            effect = t.get("effect", "")
            
            # items がある場合（ブレット、キーワード群など）
            if items:
                char_info = f"（{item_count}項目, 平均{char_per_item}文字）" if char_per_item else f"（{item_count}項目）"
                st.markdown(f"* [{type_str}/{size}] {char_info}")
                for item in items:
                    st.markdown(f"  - {item}")
            else:
                st.markdown(f"* [{type_str}/{size}] {content}（{char_count}文字）")
            
            if aim or effect:
                st.markdown(f"  * 狙い: {aim} → 効果: {effect}")
    
    # アイコン要素
    icons = result.get("icons", [])
    if icons:
        st.markdown("**🏷️ アイコン・バッジ**")
        for icon in icons:
            type_str = icon.get("type", "")
            count = icon.get("count", "")
            char_range = icon.get("char_count_range", "")
            layout = icon.get("layout", "")
            aim = icon.get("aim", "")
            effect = icon.get("effect", "")
            st.markdown(f"- [{type_str}] {count}個 / {char_range} / {layout}")
            if aim or effect:
                st.markdown(f"  - 狙い: {aim} → 効果: {effect}")
    
    # 画像要素
    images = result.get("images", [])
    if images:
        st.markdown("**🖼️ 画像要素**")
        for img in images:
            role = img.get("role", "")
            desc = img.get("description", "")
            aim = img.get("aim", "")
            effect = img.get("effect", "")
            st.markdown(f"- [{role}] {desc}")
            if aim or effect:
                st.markdown(f"  - 狙い: {aim} → 効果: {effect}")
    
    # レイアウト
    layout = result.get("layout", {})
    if layout:
        structure = layout.get("structure", "")
        bg = layout.get("background", "")
        st.markdown(f"**🎨 レイアウト:** {structure} / {bg}背景")
