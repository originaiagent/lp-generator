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
