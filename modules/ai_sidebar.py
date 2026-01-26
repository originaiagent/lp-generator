import streamlit as st
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.settings_manager import SettingsManager
from modules.prompt_manager import PromptManager
import json
import re

def set_value_by_path(obj, path, value):
    """
    JSONパス（例: structure.pages[0].appeals）に基づいてオブジェクトの値を更新する
    """
    parts = path.replace(']', '').replace('[', '.').split('.')
    parts = [p for p in parts if p != '']
    
    curr = obj
    for i in range(len(parts) - 1):
        key = parts[i]
        
        # structureの正規化
        if key == "structure" and i == 0:
            if "structure" not in curr:
                curr["structure"] = {}
            struct_obj = curr["structure"]
            if isinstance(struct_obj, dict) and "result" in struct_obj:
                curr = struct_obj["result"]
            else:
                curr = struct_obj
            continue

        if key.isdigit():
            key = int(key)
        
        # 存在しない場合は空の辞書またはリストを作成
        if isinstance(curr, list):
             while len(curr) <= key:
                 curr.append({})
             curr = curr[key]
        else:
            if key not in curr:
                # 次のキーが数値ならリスト、そうでなければ辞書
                curr[key] = [] if parts[i+1].isdigit() else {}
            curr = curr[key]
            
    last_key = parts[-1]
    if last_key.isdigit():
        last_key = int(last_key)
        
    if isinstance(curr, list):
        while len(curr) <= last_key:
            curr.append(None)
        curr[last_key] = value
    else:
        curr[last_key] = value
    return obj


def get_current_value(product, target):
    """targetパスから現在の値を取得"""
    try:
        parts = target.replace(']', '').replace('[', '.').split('.')
        parts = [p for p in parts if p != '']
        value = product
        for i, part in enumerate(parts):
            if part == 'structure' and isinstance(value.get('structure'), dict):
                # structureの中にresultがある場合はそちらを使う
                struct = value.get('structure', {})
                value = struct.get('result', struct)
            elif part.isdigit():
                if isinstance(value, list) and int(part) < len(value):
                    value = value[int(part)]
                else:
                    value = {} # 途切れた場合は空辞書扱いにして最終的に（なし）へ
            else:
                value = (value.get(part) or {}) if isinstance(value, dict) else {}
        
        # 値の整形
        if value is None or value == {} or value == []:
            return "（なし）"
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    except Exception as e:
        return "（なし）"


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
                    # 画像があれば表示
                    if 'images' in msg and msg['images']:
                        import base64
                        for img_data in msg['images']:
                            # data:mime;base64,data string format check
                            if isinstance(img_data, dict) and 'data' in img_data:
                                # image bytes restoration
                                try:
                                    img_bytes = base64.b64decode(img_data['data'])
                                    st.image(img_bytes, use_container_width=True)
                                except:
                                    st.error("画像の表示に失敗しました")
                    
                    st.markdown(msg['content'])
            
            if st.session_state.ai_generating:
                with st.chat_message("assistant"):
                    st.markdown("⏳ **考え中...**")
    
    # 編集提案カード
    if 'active_proposals' in st.session_state and st.session_state.active_proposals:
        proposals = st.session_state.active_proposals
        idx = st.session_state.get('proposal_idx', 0)
        
        if idx < len(proposals):
            prop = proposals[idx]
            st.markdown("---")
            
            # カード風UI
            with st.container():
                st.markdown(f"#### 💡 提案 {idx + 1}/{len(proposals)}")
                
                st.markdown(f"📍 **{prop.get('label', '設定変更')}**")
                
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**【現在】**")
                    target = prop.get('target')
                    st.write(f"DEBUG target: {target}")

                    # structureの中身を確認
                    structure = context.get('structure', {})
                    st.write(f"DEBUG structure keys: {list(structure.keys()) if isinstance(structure, dict) else 'not dict'}")

                    if isinstance(structure, dict) and 'result' in structure:
                        result = structure['result']
                        st.write(f"DEBUG result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
                        pages = result.get('pages', [])
                        if pages:
                            st.write(f"DEBUG pages[0] keys: {list(pages[0].keys()) if isinstance(pages[0], dict) else 'not dict'}")
                            st.write(f"DEBUG pages[0].get('appeals'): {pages[0].get('appeals')}")

                    current_val = get_current_value(context, target)
                    st.write(f"DEBUG current_value: {current_val}")
                    st.caption(str(current_val))
                with col_right:
                    st.markdown("**【提案】**")
                    # after_value の整形
                    after_val = prop.get('after', '')
                    if isinstance(after_val, list):
                        after_display = ", ".join(str(v) for v in after_val)
                    else:
                        after_display = str(after_val)
                    st.info(after_display)
                
                if prop.get('reason'):
                    st.markdown(f"💬 *{prop.get('reason')}*")
                
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
                with btn_col1:
                    if st.button("✅ 適用", key=f"apply_prop_{idx}", type="primary", use_container_width=True):
                        apply_generalized_proposal(prop, context)
                        st.session_state.proposal_idx = idx + 1
                        if st.session_state.proposal_idx >= len(proposals):
                            del st.session_state.active_proposals
                            del st.session_state.proposal_idx
                        st.rerun()
                with btn_col2:
                    if st.button("⏭️ スキップ", key=f"skip_prop_{idx}", use_container_width=True):
                        st.session_state.proposal_idx = idx + 1
                        if st.session_state.proposal_idx >= len(proposals):
                            del st.session_state.active_proposals
                            del st.session_state.proposal_idx
                        st.rerun()
        else:
            # 全て終了
            if 'active_proposals' in st.session_state:
                del st.session_state.active_proposals
                if 'proposal_idx' in st.session_state:
                    del st.session_state.proposal_idx
            st.rerun()

    
    st.markdown("---")
    
    # 入力エリア
    col1, col2, col3 = st.columns([10, 1, 1])
    with col1:
        user_input = st.text_input("メッセージ", key=f"chat_input_{st.session_state.chat_input_key}", label_visibility="collapsed", placeholder="メッセージを入力...")
    
    # 画像アップロード（エキスパンダーで隠すか、アイコンで表示）
    uploaded_file = st.file_uploader("画像を追加", type=['png', 'jpg', 'jpeg', 'webp'], key=f"chat_image_{st.session_state.chat_input_key}", label_visibility="collapsed")
    
    with col2:
        send_clicked = st.button("📤", type="primary", key="send_btn", help="送信")
    with col3:
        if st.button("🗑️", key="clear_btn", help="クリア"):
            st.session_state.ai_sidebar_messages = []
            if 'active_proposals' in st.session_state:
                del st.session_state.active_proposals
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 送信処理
    if send_clicked and (user_input or uploaded_file) and not st.session_state.ai_generating:
        message_content = user_input.strip() if user_input else ""
        message_data = {'role': 'user', 'content': message_content}
        
        # 画像処理
        if uploaded_file:
            import base64
            image_bytes = uploaded_file.getvalue()
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = uploaded_file.type
            message_data['images'] = [{'data': encoded_image, 'mime_type': mime_type}]
            
            # 画像を表示用に追加
            st.session_state.ai_sidebar_messages.append(message_data)
        elif message_content:
             st.session_state.ai_sidebar_messages.append(message_data)
        else:
            # 入力なし
            st.warning("メッセージまたは画像を入力してください")
            st.stop()

        st.session_state.ai_generating = True
        st.session_state.pending_user_input = message_content
        if uploaded_file:
            st.session_state.pending_user_images = message_data.get('images')
        
        st.session_state.chat_input_key += 1
        st.rerun()
    
    # AI応答生成
    if st.session_state.ai_generating:
        user_msg = st.session_state.get('pending_user_input', '')
        user_images = st.session_state.get('pending_user_images', None)
        
        # クリーンアップ
        if 'pending_user_input' in st.session_state: del st.session_state.pending_user_input
        if 'pending_user_images' in st.session_state: del st.session_state.pending_user_images
        
        generate_ai_response(user_msg, context, user_images)
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

def generate_ai_response(user_input, context, images=None):
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
ユーザーのリクエストに基づき、LPの構成や設定を改善するための具体的な提案を行ってください。

【現在の製品情報】
{product_info}

【ユーザーのリクエスト】
{user_input}

【出力ルール】
1. 提案の理由と内容を簡潔に日本語で説明してください（チャット用）。
2. プログラムが自動適用できるよう、以下のJSON形式を含むブロックを必ず出力してください。
   JSONは ```json で囲んでください。

3. ユーザーの指示に従って変更提案を作成すること。
   - ユーザーが具体的な文言を指定している場合（「〇〇」「△△」など）：その文言をそのまま使用する。勝手に補足や言い換えをしない。
   - ユーザーが曖昧な指示の場合（「改善して」「もっと良くして」など）：AIが最適な内容を考えて提案する。

```json
{{
  "proposals": [
    {{
      "target": "JSONのパス（例: structure.pages[0].appeals）",
      "label": "タブ名 > 項目名（例: 全体構成 > P1: 訴求ポイント）",
      "before": "現在の値（文字列）",
      "after": "提案する新しい値（文字列または配列。targetの型に合わせる）",
      "reason": "変更の理由"
    }}
  ]
}}
```

4. ターゲットパスの例:
   - 製品名: name
   - 製品説明: description
   - ページ構成の訴求: structure.pages[0].appeals
   - ページ見出し: structure.pages[1].title
5. 複数提案がある場合は、proposals配列に複数含めてください。
"""
    else:
        prompt = prompt_manager.get_prompt("ai_chat", {"product_info": product_info, "user_input": user_input})
    
    try:
        settings_manager = SettingsManager()
        settings = settings_manager.get_settings()
        ai_provider = AIProvider(settings)
        
        # 画像がある場合は、画像付きリクエストを送信
        if images:
            # imagesは [{'data': '...', 'mime_type': '...'}] の形式を想定
            response = ai_provider.ask(prompt, "chat", images=images)
        else:
            response = ai_provider.ask(prompt, "chat")
        
        if is_edit_request:
            # JSON提案を抽出
            try:
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                    proposal_data = json.loads(json_str)
                    if "proposals" in proposal_data:
                        st.session_state.active_proposals = proposal_data["proposals"]
                        st.session_state.proposal_idx = 0
            except Exception as e:
                print(f"Proposal extraction error: {e}")

        
        st.session_state.ai_sidebar_messages.append({'role': 'assistant', 'content': response})
    except Exception as e:
        st.session_state.ai_sidebar_messages.append({'role': 'assistant', 'content': f"エラー: {e}"})

def apply_generalized_proposal(proposal, context):
    """汎用的な提案を適用する"""
    try:
        product_id = context.get('_product_id')
        data_store = context.get('_data_store')
        
        if not product_id or not data_store:
            st.error("製品情報が取得できません")
            return False
            
        target_path = proposal.get('target')
        after_value = proposal.get('after')
        
        if not target_path:
            return False
            
        product = data_store.get_product(product_id)
        
        # 値を更新
        try:
            # 配列の場合は、カンマ区切りの文字列をリストに変換するなどの処理が必要かもしれない
            # ただしAIにtargetの型に合わせるよう指示しているので、一旦そのまま
            product = set_value_by_path(product, target_path, after_value)
            
            data_store.update_product(product_id, product)
            st.success(f"「{proposal.get('label', target_path)}」を更新しました。")
            return True
        except Exception as e:
            st.error(f"パス解析エラー: {e}")
            return False
            
    except Exception as e:
        st.error(f"適用エラー: {e}")
        return False

