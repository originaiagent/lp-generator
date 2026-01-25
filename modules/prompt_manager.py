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
