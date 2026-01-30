import json
import os
from typing import Dict, List, Any

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
--------------------------------------------------
【P1】ファーストビュー
--------------------------------------------------
■目的
ユーザーの興味を一瞬で惹きつけ、読み進めてもらうこと

■キャッチコピー
メイン：[コピー]
サブ：[コピー]

■構成・テキスト要素
- ヘッダー：ロゴを中央に配置
- メインビジュアル：...

■デザイン・画像指示
- 全体：[トンマナ]に基づき、〇〇な雰囲気で
- 背景：...
- 商品画像：...

(以下、ページごとに続く)
--------------------------------------------------

【出力言語】
必ず日本語で出力してください。"""
        }
    }

    def __init__(self, prompts_file: str = "data/prompts.json"):
        self.prompts_file = prompts_file
        self._ensure_directory()
        self._load_or_create_prompts()

    def _ensure_directory(self):
        dir_path = os.path.dirname(self.prompts_file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    def _load_or_create_prompts(self):
        try:
            if os.path.exists(self.prompts_file):
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self.prompts = json.load(f)
                
                # デフォルトプロンプトの不足分をマージ
                updated = False
                for key, value in self.DEFAULT_PROMPTS.items():
                    if key not in self.prompts:
                        self.prompts[key] = value.copy()
                        updated = True
                
                if updated:
                    self._save_prompts()
            else:
                self.prompts = {k: v.copy() for k, v in self.DEFAULT_PROMPTS.items()}
                self._save_prompts()
        except:
            self.prompts = {k: v.copy() for k, v in self.DEFAULT_PROMPTS.items()}
            self._save_prompts()

    def _save_prompts(self):
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(self.prompts, f, ensure_ascii=False, indent=2)

    def get_prompt(self, prompt_id: str, variables: Dict[str, str] = None) -> str:
        # 外部ファイルを優先的に読み込む
        external_path = f"data/prompts/{prompt_id}.txt"
        import os
        if os.path.exists(external_path):
            with open(external_path, "r", encoding="utf-8") as f:
                template = f.read()
        elif prompt_id in self.prompts:
            data = self.prompts[prompt_id]
            template = data.get("template", "") if isinstance(data, dict) else data
        else:
            return ""
        
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
            if isinstance(data, dict):
                result.append({"id": pid, "name": data.get("name", pid), "description": data.get("description", "")})
            else:
                result.append({"id": pid, "name": pid, "description": ""})
        return result

    def update_prompt(self, prompt_id: str, template: str) -> bool:
        if prompt_id in self.prompts:
            if isinstance(self.prompts[prompt_id], dict):
                self.prompts[prompt_id]["template"] = template
            else:
                self.prompts[prompt_id] = template
            self._save_prompts()
            return True
        return False

    def reset_to_default(self, prompt_id: str) -> bool:
        if prompt_id in self.DEFAULT_PROMPTS:
            self.prompts[prompt_id] = self.DEFAULT_PROMPTS[prompt_id].copy()
            self._save_prompts()
            return True
        return False
