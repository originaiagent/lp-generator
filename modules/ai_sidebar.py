import streamlit as st
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.settings_manager import SettingsManager
from modules.prompt_manager import PromptManager
import json

def render_ai_sidebar():
    """サイドバーにAIボタン、メインエリアに大きなパネル表示"""
    if 'ai_generating' not in st.session_state:
        st.session_state.ai_generating = False
    if 'ai_sidebar_messages' not in st.session_state:
        st.session_state.ai_sidebar_messages = []
    if 'show_ai_chat' not in st.session_state:
        st.session_state.show_ai_chat = False
    if 'chat_input_key' not in st.session_state:
        st.session_state.chat_input_key = 0
    
    with st.sidebar:
        st.markdown("---")
        if st.session_state.show_ai_chat:
            if st.button("✕ AIを閉じる", width="stretch"):
                st.session_state.show_ai_chat = False
                st.rerun()
        else:
            if st.button("🤖 AIアシスタント", width="stretch", type="primary"):
                st.session_state.show_ai_chat = True
                st.rerun()
    
    if st.session_state.show_ai_chat:
        render_chat_panel()

def render_chat_panel():
    """メインエリアに大きなチャットパネル（モーダル風）"""
    context = get_product_context()
    
    # 最上部にスクロール（複数の方法で確実に）
    st.markdown("""
    <div id="ai-panel-top"></div>
    <script>
        // 即座にスクロール
        document.body.scrollTop = 0;
        document.documentElement.scrollTop = 0;
        window.scrollTo(0, 0);
        
        // Streamlitのメインコンテナもスクロール
        const mainContainer = document.querySelector('[data-testid="stAppViewContainer"]');
        if (mainContainer) {
            mainContainer.scrollTop = 0;
        }
        const mainBlock = document.querySelector('.main');
        if (mainBlock) {
            mainBlock.scrollTop = 0;
        }
        
        // 少し遅延させて再度スクロール
        setTimeout(function() {
            document.body.scrollTop = 0;
            document.documentElement.scrollTop = 0;
            window.scrollTo(0, 0);
        }, 100);
    </script>
    """, unsafe_allow_html=True)
    
    # スタイル
    st.markdown("""
    <style>
    .ai-panel {
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        padding: 0;
        margin-bottom: 20px;
    }
    .ai-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px 25px;
        border-radius: 12px 12px 0 0;
        color: white;
        font-size: 18px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # パネル開始
    st.markdown('<div class="ai-panel">', unsafe_allow_html=True)
    st.markdown('<div class="ai-header">🤖 AIアシスタント</div>', unsafe_allow_html=True)
    
    # 製品情報
    col1, col2 = st.columns([6, 1])
    with col1:
        if context:
            st.info(f"📦 **{context.get('name', '未設定')}**")
        else:
            st.warning("📦 製品を選択してください")
    with col2:
        if st.button("✕ 閉じる", key="close_panel"):
            st.session_state.show_ai_chat = False
            st.rerun()
    
    # 会話エリア（大きめ）
    chat_container = st.container(height=500)
    with chat_container:
        if not st.session_state.ai_sidebar_messages:
            st.markdown("""
            <div style="text-align: center; color: #666; padding: 100px 20px;">
                <div style="font-size: 50px; margin-bottom: 20px;">💬</div>
                <div style="font-size: 18px; margin-bottom: 15px;">質問や編集指示を入力してください</div>
                <div style="font-size: 14px; color: #999;">
                    例: 「進捗を確認して」「P1の訴求を変更して」「使い方を教えて」
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.ai_sidebar_messages:
                with st.chat_message(msg['role']):
                    st.markdown(msg['content'])
            
            if st.session_state.ai_generating:
                with st.chat_message("assistant"):
                    st.markdown("⏳ **考え中...**")
    
    # 編集提案ボタン
    if 'pending_edit' in st.session_state and st.session_state.pending_edit:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("✅ この変更を適用", type="primary", width="stretch", key="apply_edit"):
                apply_edit_proposal(st.session_state.pending_edit)
                del st.session_state.pending_edit
                st.rerun()
        with col2:
            if st.button("❌ キャンセル", width="stretch", key="cancel_edit"):
                del st.session_state.pending_edit
                st.rerun()
    
    st.markdown("---")
    
    # 入力エリア
    col1, col2, col3 = st.columns([10, 1, 1])
    with col1:
        user_input = st.text_input("メッセージ", key=f"chat_input_{st.session_state.chat_input_key}", label_visibility="collapsed", placeholder="メッセージを入力...")
    with col2:
        send_clicked = st.button("📤", type="primary", key="send_btn", help="送信")
    with col3:
        if st.button("🗑️", key="clear_btn", help="クリア"):
            st.session_state.ai_sidebar_messages = []
            if 'pending_edit' in st.session_state:
                del st.session_state.pending_edit
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 送信処理
    if send_clicked and user_input and user_input.strip() and not st.session_state.ai_generating:
        st.session_state.ai_sidebar_messages.append({'role': 'user', 'content': user_input.strip()})
        st.session_state.ai_generating = True
        st.session_state.pending_user_input = user_input.strip()
        st.session_state.chat_input_key += 1
        st.rerun()
    
    # AI応答生成
    if st.session_state.ai_generating and 'pending_user_input' in st.session_state:
        user_msg = st.session_state.pending_user_input
        del st.session_state.pending_user_input
        generate_ai_response(user_msg, context)
        st.session_state.ai_generating = False
        st.rerun()

def get_product_status(context):
    if not context:
        return "製品が選択されていません"
    status_lines = []
    name = context.get('name', '')
    status_lines.append(f"✅ 製品名: {name}" if name else "❌ 製品名: 未設定")
    ref_lps = context.get('reference_lp_images', [])
    status_lines.append(f"✅ 参照LP: {len(ref_lps)}枚" if ref_lps else "❌ 参照LP: 未アップロード")
    tone = context.get('tone_manner', {})
    status_lines.append("✅ トンマナ: 分析済み" if tone else "❌ トンマナ: 未分析")
    structure = context.get('structure', {})
    has_structure = bool(structure.get('result', {}).get('pages', []) if isinstance(structure, dict) else False)
    status_lines.append("✅ ページ構成: 生成済み" if has_structure else "❌ ページ構成: 未生成")
    page_contents = context.get('page_contents', {})
    status_lines.append(f"✅ ページ詳細: {len(page_contents)}ページ" if page_contents else "❌ ページ詳細: 未生成")
    generated = context.get('generated_lp_images', {})
    status_lines.append(f"✅ LP画像: {len(generated)}枚生成" if generated else "❌ LP画像: 未生成")
    return '\n'.join(status_lines)

def get_product_context():
    if 'current_product_id' not in st.session_state:
        return None
    data_store = DataStore()
    product_id = st.session_state['current_product_id']
    try:
        product = data_store.get_product(product_id)
        if product:
            product['_product_id'] = product_id
            product['_data_store'] = data_store
        return product
    except:
        return None

def generate_ai_response(user_input, context):
    product_info = "製品未選択"
    structure_info = ""
    
    if context:
        competitor = context.get('competitor_analysis', '')
        if isinstance(competitor, dict):
            competitor_text = str(competitor.get('result', ''))[:500]
        else:
            competitor_text = str(competitor)[:500] if competitor else '未実施'
        
        structure = context.get('structure', {})
        if isinstance(structure, dict) and 'result' in structure:
            structure = structure['result']
        pages = structure.get('pages', []) if isinstance(structure, dict) else []
        
        if pages:
            structure_lines = ["\n【現在のページ構成】"]
            for p in pages:
                appeals = ', '.join(p.get('appeals', []))
                structure_lines.append(f"P{p.get('order', '?')}: {p.get('title', '無題')[:30]}")
                structure_lines.append(f"  役割: {p.get('role', '未設定')[:50]}")
                structure_lines.append(f"  訴求: {appeals}")
            structure_info = '\n'.join(structure_lines)
        
        organized = context.get('product_sheet_organized', '')[:500]
        
        product_info = f"""製品名: {context.get('name', '未設定')}
説明: {context.get('description', '未設定')}
競合分析: {competitor_text}
整理済み製品情報: {organized}{structure_info}"""
    
    edit_keywords = ['追加して', '変更して', '修正して', '削除して', '入れて', '変えて', '更新して']
    help_keywords = ['使い方', 'どうすれば', 'やり方', '方法', 'ヘルプ', '教えて', '次は何', '何をすれば']
    status_keywords = ['進捗', '状態', 'ステータス', '確認して', '今どう']
    
    is_edit_request = any(kw in user_input for kw in edit_keywords)
    is_help_request = any(kw in user_input for kw in help_keywords)
    is_status_request = any(kw in user_input for kw in status_keywords)
    
    prompt_manager = PromptManager()
    
    if is_status_request:
        status = get_product_status(context)
        prompt = f"""あなたはLPジェネレーターのアシスタントです。

{product_info}

【現在の進捗】
{status}

【ユーザーの質問】
{user_input}

【指示】
1. 現在の進捗状況を分かりやすく説明
2. 次にやるべきことを具体的に提案
3. 未完了の項目があれば優先度順に案内"""
    
    elif is_help_request:
        prompt = f"""あなたはLPジェネレーターの使い方サポートです。

【ツールの機能】
1. 製品一覧: 製品の作成・管理
2. 情報入力: 製品情報・参照LP・トンマナ画像のアップロード
3. モデル設定: AI設定（Claude/GPT/Gemini）
4. 全体構成: LP構成の自動生成・訴求ポイント選択
5. ページ詳細: 各ページのコンテンツ生成
6. 出力: LP画像生成・問題検出・指示書出力

【現在の製品情報】
{product_info}

【ユーザーの質問】
{user_input}

【指示】
1. 質問に対して具体的な操作手順を説明
2. 現在のページに関連する場合は、そのページでの操作を案内
3. 必要であれば「こう言えば編集できます」という例も提示"""
    
    elif is_edit_request:
        prompt = f"""あなたはLP制作のエキスパートです。

{product_info}

【ユーザーの編集リクエスト】
{user_input}

【指示】
1. まず、変更の妥当性を簡潔に説明（1-2文）
2. 編集対象を特定し、以下の形式で変更内容を提示：

---変更提案---
【編集対象】structure_appeals
【対象ページ】P1

■ 変更前
訴求: （現在の訴求をカンマ区切りで）

■ 変更後
訴求: （変更後の訴求をカンマ区切りで）
---

3. 訴求は「○○訴求」という形式で記載。
4. この形式を厳守してください。"""
    else:
        prompt = prompt_manager.get_prompt("ai_chat", {"product_info": product_info, "user_input": user_input})
    
    try:
        settings_manager = SettingsManager()
        settings = settings_manager.get_settings()
        ai_provider = AIProvider(settings)
        response = ai_provider.ask(prompt, "chat")
        
        if is_edit_request and '---変更提案---' in response:
            st.session_state.pending_edit = {'response': response, 'context': context}
        
        st.session_state.ai_sidebar_messages.append({'role': 'assistant', 'content': response})
    except Exception as e:
        st.session_state.ai_sidebar_messages.append({'role': 'assistant', 'content': f"エラー: {e}"})

def apply_edit_proposal(edit_data):
    """編集提案を実際に適用する"""
    try:
        context = edit_data.get('context', {})
        response = edit_data.get('response', '')
        
        product_id = context.get('_product_id')
        data_store = context.get('_data_store')
        
        if not product_id or not data_store:
            st.error("製品情報が取得できません")
            return
        
        # ページ番号を特定
        page_idx = 0
        for i in range(1, 10):
            if f'P{i}' in response or f'【対象ページ】P{i}' in response:
                page_idx = i - 1
                break
        
        if '変更後' not in response:
            st.warning("変更後の内容が見つかりません")
            return
            
        after_text = response.split('変更後')[1]
        if '---' in after_text:
            after_text = after_text.split('---')[0]
        after_text = after_text.strip()
        
        # 訴求ポイントの行を探す
        appeals_line = None
        for line in after_text.split('\n'):
            line = line.strip()
            if line.startswith('訴求:') or line.startswith('訴求：'):
                appeals_line = line.replace('訴求:', '').replace('訴求：', '').strip()
                break
        
        if not appeals_line:
            for line in after_text.split('\n'):
                if '訴求' in line:
                    appeals_line = line.split('訴求')[-1].strip()
                    appeals_line = appeals_line.lstrip(':').lstrip('：').strip()
                    break
        
        if appeals_line:
            product = data_store.get_product(product_id)
            structure = product.get('structure', {})
            if isinstance(structure, dict) and 'result' in structure:
                result = structure['result']
            else:
                result = structure
            
            pages = result.get('pages', [])
            if pages and page_idx < len(pages):
                new_appeals = []
                for a in appeals_line.replace('、', ',').split(','):
                    a = a.strip()
                    if a and '訴求' in a:
                        new_appeals.append(a)
                
                if new_appeals:
                    pages[page_idx]['appeals'] = new_appeals
                    
                    if isinstance(structure, dict) and 'result' in structure:
                        structure['result']['pages'] = pages
                    else:
                        structure['pages'] = pages
                    
                    product['structure'] = structure
                    data_store.update_product(product_id, product)
                    st.success(f"P{page_idx + 1}の訴求を更新しました！\n{', '.join(new_appeals)}")
                    return
        
        st.warning("変更内容を自動適用できませんでした。")
    except Exception as e:
        st.error(f"適用エラー: {e}")
