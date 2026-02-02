import json
import os
from typing import Dict, List, Any
from supabase import create_client, Client

class PromptManager:
    DEFAULT_PROMPTS = {
        "ai_chat": {
            "name": "AIアシスタント",
            "description": "サイドバーのAI相談で使用",
            "template": """あなたはLP制作のエキスパートです。
{product_info}

【質問】
{user_input}

簡潔に回答してください（200-400文字）。

【出力言語】
必ず日本語で出力してください。"""
        },
        "competitor_analysis": {
            "name": "競合情報分析",
            "description": "競合商品の情報を分析",
            "template": """以下の競合商品情報を分析して、マーケティングに役立つインサイトを抽出してください。

【分析観点】
1. 製品の強み・特徴
2. ターゲット顧客層
3. 価格戦略
4. 訴求ポイント
5. 弱点・改善余地

【競合情報】
{competitor_text}

【出力形式】
各観点について箇条書きで簡潔にまとめてください。

【出力言語】
必ず日本語で出力してください。"""
        },
        "element_analysis": {
            "name": "LP要素分析",
            "description": "CVR向上のためのLP要素を分析",
            "template": """以下の情報を元に、CVR向上のためのLP要素を分析してJSON形式で出力してください。

【製品情報】
{product_info}

【競合分析結果】
{competitor_analysis}

【出力形式】
各要素に「name」と「reason」（根拠）を含めてください。
{{"必須": [], "推奨": [], "差別化": [], "独自": [], "強み": [], "ベネフィット": [], "顧客ニーズ": [], "CVRブースト": []}}

【出力言語】
JSONのキー以外（値の部分）は必ず日本語で出力してください。"""
        },
        "structure_generation": {
            "name": "ページ構成生成",
            "description": "訴求ポイントからLP構成を生成",
            "template": """以下の情報を元に、{page_count}ページ構成のLPを作成してください。

【製品情報】
{product_name}: {product_description}

【訴求ポイント】
{selected_appeals}

【参考LP分析】
{lp_analysis_summary}

【出力ルール】
- titleは簡潔に（例：「ファーストビュー」「滑り止め性能」「比較表」）
- 長い説明文は不要。キーワードレベルで簡潔に
- 複数ポイントをまとめてもOK（例：「頑丈さ / 抗菌性能」）
- summaryは10文字以内
- ページ数は{page_count}ページ

JSON形式で出力:
{{"pages": [{{"id": "P1", "order": 1, "title": "ファーストビュー", "summary": "要素詰め込み", "elements": []}}]}}

【出力言語】
JSONの値は必ず日本語で出力してください。"""
        },
        "page_detail_generation": {
            "name": "ページ詳細生成",
            "description": "各ページのコンテンツを生成",
            "template": """以下のページの詳細コンテンツを生成してください。

【ページ】{page_title}
【概要】{page_summary}
【要素】{page_elements}
【製品情報】{product_info}

出力: 見出し、本文（200-400文字）、キャッチコピー案3つ

【出力言語】
必ず日本語で出力してください。"""
        },
        "keyword_organize": {
            "name": "キーワード整理",
            "description": "レビューシート等から重要キーワードを抽出・整理",
            "template": """以下の情報を元に、マーケティング上重要なキーワードを重要度順に整理して出力してください。

【元データ】
{raw_data}

【出力形式】
以下の形式のみを出力してください（Markdownの表形式等は不要、プレーンテキスト可、または箇条書き）。
重要度高（S）: ...
重要度中（A）: ...
重要度低（B）: ...

顧客の不満点（ペイン）: ...
顧客の満足点（ゲイン）: ...

【出力言語】
必ず日本語で出力してください。"""
        },
        "sheet_organize": {
            "name": "シート内容整理",
            "description": "製品情報シートの内容を構造化して整理",
            "template": """以下の製品情報シートの内容を、LP制作に使いやすいように整理して出力してください。

【元データ】
{raw_data}

【整理の観点】
- 製品名 / キャッチコピー
- ターゲット層・どんな人向けか
- 主な特徴・メリット（3〜5点）
- スペック情報（サイズ、素材など）
- 価格・オファー内容

【出力形式】
見出し付きのテキスト形式で分かりやすく。

【出力言語】
必ず日本語で出力してください。"""
        },
        "designer_instruction_generation": {
            "name": "デザイナー向け指示書生成",
            "description": "ページ構成とコンテンツからデザイナー向けの指示書を一括生成",
            "template": """各ページの構成案とコンテンツ内容を元に、デザイナー向けの制作指示書を生成してください。
デザイナーが迷わずに画像制作に取り掛かれるレベルの具体性を持たせてください。

【重要な指示】
- 入力されたJSONデータをそのまま出力しないでください
- 必ず以下の形式に変換して出力してください
- 各ページごとに、目的・キャッチコピー・イメージ画像指示を含めてください

【入力データ】
■製品情報: {product_name}
■トンマナ・デザイン方針:
{tone_manner}

■ページ構成とコンテンツ:
{content_json}

【生成の指針】
1. **構造化された指示**: 各ページごとに明確に区切って出力してください。
2. **必須項目**:
   - 目的（このページの役割）
   - キャッチコピー（メイン・サブ）
   - デザイン構成案（テキストの配置、強調ポイント）
   - イメージ画像指示（背景、人物、商品写真の扱いなど具体的に）
3. **トンマナの反映**: 指定されたトンマナ情報を元に、色使いやフォント、あしらいの雰囲気を具体的に指示してください。
4. **AIの裁量**: 上記の項目に加え、デザイナーにとって有益と思われる情報は適宜追加・調整して最適な形式で出力してください。

【出力形式の例】
【P1】ファーストビュー
- 目的： このページの役割を1文で
- キャッチコピー：
  - メイン： 〇〇〇
  - サブ： 〇〇〇
- テキスト要素： キーワードをスペース区切りで
- イメージ画像指示：
  - 背景：〇〇
  - メインビジュアル：〇〇
  - 強調ポイント：〇〇

(以下、ページごとに続く)

【出力言語】
必ず日本語で出力してください。"""
        },
        "lp_image_generation": {
             "name": "LP画像生成",
             "description": "LPの1セクションの画像を生成",
             "template": """あなたはWEBデザインのプロフェッショナルです。
LPの1セクション（画像）を作成してください。

【製品・トンマナ情報】
- メインカラー: {main_color}
- アクセントカラー: {accent_color}
- 背景色: {background_color}
- テキスト色: {text_color}
- フォント: {font_type}（{font_weight}）
- 印象: {impression}

【セクションの内容】
{content_text}

【レイアウト指示】
{layout_instructions}

画像のアスペクト比は1:1に近い正方形、またはコンテンツに応じた縦長で出力してください。
文字はダミーではなく、意味のある日本語のテキストとして読めるように配置してください。"""
        },
        "persona_generation": {
            "name": "ペルソナ生成",
            "description": "商品と露出先に応じた購買者ペルソナを生成",
            "template": """あなたはマーケティングリサーチの専門家です。

【商品情報】
製品名: {product_name}
説明: {product_description}
カテゴリ: {product_category}

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
}}"""
        },
        "persona_evaluation": {
            "name": "ペルソナ評価",
            "description": "特定ペルソナの視点でLPを評価",
            "template": """あなたは以下のペルソナになりきって、このLPを見た感想を述べてください。

【あなたのプロフィール】
{persona_name}
年代: {persona_age}
職業: {persona_occupation}
この商品を見ている理由: {persona_motivation}
購入にあたっての不安: {persona_concerns}
購買スタイル: {persona_decision_style}
価格感度: {persona_budget_sensitivity}

【露出先】
{exposure_type}

【この露出先で特に重要な評価ポイント】
{exposure_focus}

【LP内容】
{lp_content}

【競合情報】
{competitors}

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
}}"""
        },
        "diagnosis_summary": {
            "name": "診断総合分析",
            "description": "複数ペルソナの評価を総合的に分析",
            "template": """以下は複数のペルソナによるLP評価結果です。

【露出先】
{exposure_type}

【各ペルソナの評価】
{evaluations_json}

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
}}"""
        },
        "improvement_proposal": {
            "name": "改善案生成",
            "description": "診断結果から具体的なテキスト修正案を生成",
            "template": """あなたはLPの改善エキスパートです。

以下の改善提案を、具体的なテキスト修正に落とし込んでください。
現在のページ構成とコンテンツを参考に、最も効果の高い箇所の修正案を1つ作成してください。

【改善提案】
{improvement_text}

【現在のページ構成とコンテンツ】
{pages_data_json}

【出力形式】JSONで出力してください。Markdownのコードブロックなどは含めず、純粋なJSONのみを返してください。
{{
    "target_page_index": 0,
    "target_page_name": "ファーストビュー",
    "target_element_index": 0,
    "target_element_type": "サブヘッド",
    "before_text": "修正前のテキスト",
    "after_text": "修正後のテキスト",
    "reason": "この修正により〇〇が改善されます"
}}"""
        },
        "employee_evaluation": {
            "name": "従業員AI評価",
            "description": "特定の役割を持つ従業員の視点でLPを評価（過去のフィードバックを学習可能）",
            "template": """あなたは、以下のプロフィールを持つ当社の従業員として、このLPを専門的な視点で評価してください。

【あなたのプロフィール】
名前: {employee_name}
役割: {employee_role}
専門分野: {employee_expertise}
評価の重点: {employee_evaluation_perspective}
性格・口調: {employee_personality_traits}

【過去のあなたへのフィードバック（学習データ）】
以下の内容は、過去にあなたが行った評価に対して、上司や担当者から寄せられた修正や補足です。
今回の評価では、これらの傾向を反映させ、より「あなたらしい」リアルな回答を心がけてください。
{past_feedback}

【露出先】
{exposure_type}

【LP内容】
{lp_content}

【指示】
このLPをあなたの専門的な視点で分析し、率直な感想を述べてください。

【出力形式】JSONのみ
{{
  "overall_rating": 5段階評価（1-5）,
  "purchase_decision": "活用する / 検討の余地あり / 差し戻し",
  "first_impression": "第一印象（専門家の視点で感じたこと）",
  "voice": "あなたの生の声（あなたの性格や口調を反映させた2-3文で）",
  "resonated_points": ["評価できるポイント1", "評価できるポイント2"],
  "concerns": ["懸念点・修正が必要な点1", "懸念点・修正が必要な点2"],
  "vs_competitors": "競合と比較した自社の優位性・課題（1文）",
  "improvement_suggestion": "具体的な改善アドバイス（1文）"
}}"""
        }
    }

    def __init__(self, prompts_file: str = "data/prompts.json"):
        self.prompts_file = prompts_file
        self.prompts = {}
        self.use_supabase = False
        self.supabase = None
        
        # Supabase接続試行
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if url and (key or service_key):
            try:
                self.supabase = create_client(url, service_key if service_key else key)
                self.use_supabase = True
            except Exception as e:
                print(f"Supabase init error in PromptManager: {e}")
        
        # 初期読み込み
        self._load_prompts()
    
    def _ensure_directory(self):
        dir_path = os.path.dirname(self.prompts_file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    def _load_prompts(self):
        """Supabase または ローカルファイルからプロンプトを読み込む"""
        loaded = False
        
        if self.use_supabase:
            try:
                # DBから全プロンプト取得
                response = self.supabase.table("prompts").select("*").execute()
                db_prompts = response.data
                
                if db_prompts:
                    for item in db_prompts:
                        pid = item.get('id')
                        self.prompts[pid] = {
                            "name": item.get('name', ''),
                            "description": item.get('description', ''),
                            "template": item.get('template', '')
                        }
                    loaded = True
            except Exception as e:
                print(f"Failed to load prompts from Supabase: {e}")
        
        # Supabaseから読み込めなかった場合、またはDBが空の場合はローカル/デフォルトを確認
        if not loaded or not self.prompts:
            if os.path.exists(self.prompts_file):
                try:
                    with open(self.prompts_file, 'r', encoding='utf-8') as f:
                        self.prompts = json.load(f)
                except:
                    self.prompts = {}
            
            # デフォルトで補完
            updated = False
            for key, value in self.DEFAULT_PROMPTS.items():
                if key not in self.prompts:
                    self.prompts[key] = value.copy()
                    updated = True
            
            # Supabaseが有効なら、デフォルト値をDBに保存（初期化）
            if self.use_supabase and updated:
                self._sync_defaults_to_db()

    def _sync_defaults_to_db(self):
        """デフォルト値をDBに保存"""
        if not self.use_supabase:
            return
            
        try:
            for pid, data in self.prompts.items():
                # 存在確認
                check = self.supabase.table("prompts").select("id").eq("id", pid).execute()
                if not check.data:
                    # 新規挿入
                    insert_data = {
                        "id": pid,
                        "name": data.get("name", ""),
                        "description": data.get("description", ""),
                        "template": data.get("template", "")
                    }
                    self.supabase.table("prompts").insert(insert_data).execute()
        except Exception as e:
            print(f"Error syncing defaults to DB: {e}")

    def get_prompt(self, prompt_id: str, variables: Dict[str, str] = None) -> str:
        data = self.prompts.get(prompt_id, {})
        if not data and prompt_id in self.DEFAULT_PROMPTS:
            data = self.DEFAULT_PROMPTS[prompt_id]
        
        if not data:
            return ""
            
        template = data.get("template", "")
        
        if variables:
            try:
                return template.format(**variables)
            except KeyError:
                return template
        return template

    def get_prompt_data(self, prompt_id: str) -> Dict[str, Any]:
        return self.prompts.get(prompt_id, {})

    def list_prompts(self) -> List[str]:
        return list(self.prompts.keys())

    def list_prompts_with_names(self):
        result = []
        for pid, data in self.prompts.items():
            result.append({"id": pid, "name": data.get("name", pid), "description": data.get("description", "")})
        return result

    def update_prompt(self, prompt_id: str, template: str) -> bool:
        # メモリ更新
        if prompt_id in self.prompts:
            self.prompts[prompt_id]["template"] = template
        else:
            self.prompts[prompt_id] = {
                "name": prompt_id,
                "description": "Custom prompt",
                "template": template
            }
        
        # DB更新
        if self.use_supabase:
            try:
                # 存在チェック
                check = self.supabase.table("prompts").select("*").eq("id", prompt_id).execute()
                if check.data:
                    self.supabase.table("prompts").update({"template": template}).eq("id", prompt_id).execute()
                else:
                    self.supabase.table("prompts").insert({
                        "id": prompt_id,
                        "name": self.prompts[prompt_id]["name"],
                        "description": self.prompts[prompt_id]["description"],
                        "template": template
                    }).execute()
                return True
            except Exception as e:
                print(f"Error updating prompt in DB: {e}")
                return False
        else:
            # ローカル保存
            self._ensure_directory()
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, ensure_ascii=False, indent=2)
            return True

    def reset_to_default(self, prompt_id: str) -> bool:
        if prompt_id in self.DEFAULT_PROMPTS:
            self.prompts[prompt_id] = self.DEFAULT_PROMPTS[prompt_id].copy()
            template = self.prompts[prompt_id]["template"]
            
            # DB更新
            if self.use_supabase:
                try:
                    self.supabase.table("prompts").update({"template": template}).eq("id", prompt_id).execute()
                    return True
                except Exception as e:
                    print(f"Error resetting prompt in DB: {e}")
                    return False
            else:
                 self._ensure_directory()
                 with open(self.prompts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.prompts, f, ensure_ascii=False, indent=2)
                 return True
        return False
