"""
モデル一覧自動取得モジュール
各APIから利用可能なモデル一覧を取得してdata/models.jsonを更新
"""
import os
import json
import requests
from typing import Dict, List

MODELS_FILE = "data/models.json"

class ModelFetcher:
    """APIからモデル一覧を取得"""
    
    def __init__(self):
        self.openai_key = os.environ.get('OPENAI_API_KEY')
        self.anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        self.google_key = os.environ.get('GOOGLE_API_KEY')
    
    def fetch_all(self) -> Dict:
        """全プロバイダからモデル一覧を取得"""
        result = {
            "llm": {
                "anthropic": self._fetch_anthropic_models(),
                "openai": self._fetch_openai_models(),
                "gemini": self._fetch_gemini_llm_models()
            },
            "image": {
                "openai": self._fetch_openai_image_models(),
                "gemini": self._fetch_gemini_image_models()
            }
        }
        return result
    
    def _fetch_openai_models(self) -> List[Dict]:
        """OpenAI LLMモデル一覧を取得"""
        if not self.openai_key:
            return []
        
        try:
            headers = {"Authorization": f"Bearer {self.openai_key}"}
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # チャット対応モデルのみ抽出（除外: realtime, audio, embedding, whisper等）
            exclude_keywords = ["realtime", "audio", "embedding", "whisper", "tts", "davinci", "babbage", "curie"]
            chat_models = [m for m in data.get("data", []) 
                          if not any(kw in m["id"].lower() for kw in exclude_keywords)
                          and (m["id"].startswith(("gpt-", "o1", "o3", "chatgpt")) 
                               or "gpt" in m["id"].lower())]
            
            # 作成日時で新しい順にソート
            sorted_models = sorted(chat_models, key=lambda m: m.get("created", 0), reverse=True)
            
            models = []
            seen = set()
            for m in sorted_models:
                if m["id"] not in seen:
                    models.append({
                        "id": m["id"],
                        "name": m["id"].upper().replace("-", " "),
                        "desc": "OpenAI"
                    })
                    seen.add(m["id"])
            
            return models[:20]
        except Exception as e:
            print(f"OpenAI モデル取得エラー: {e}")
            return [
                {"id": "gpt-4o", "name": "GPT-4o", "desc": "マルチモーダル"},
                {"id": "gpt-4o-mini", "name": "GPT-4o mini", "desc": "高速、低コスト"}
            ]
    
    def _fetch_openai_image_models(self) -> List[Dict]:
        """OpenAI 画像モデル一覧"""
        return [
            {"id": "dall-e-3", "name": "DALL-E 3", "desc": "高品質画像生成"},
            {"id": "dall-e-2", "name": "DALL-E 2", "desc": "低コスト"}
        ]
    
    def _fetch_anthropic_models(self) -> List[Dict]:
        """Anthropic モデル一覧"""
        return [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "desc": "最新、バランス型"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "desc": "高性能"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "desc": "高速、低コスト"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "desc": "最高性能"}
        ]
    
    def _fetch_gemini_llm_models(self) -> List[Dict]:
        """Gemini LLMモデル一覧を取得"""
        if not self.google_key:
            return []
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.google_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                
                # LLMモデル条件:
                # - generateContent対応
                # - geminiで始まる
                # - image, tts, robotics, computer-useを除外
                if "generateContent" in methods and name.startswith("gemini"):
                    # 除外パターン
                    skip_patterns = ["image", "tts", "robotics", "computer-use"]
                    if any(p in name.lower() for p in skip_patterns):
                        continue
                    
                    # 重複排除のため、主要モデルのみ
                    # preview, exp, latestのない基本形を優先
                    models.append({
                        "id": name,
                        "name": self._format_gemini_name(name),
                        "desc": self._get_gemini_desc(name)
                    })
            
            # 優先順位でソート（3 > 2.5 > 2.0 > 1.5）
            def sort_key(m):
                model_id = m["id"]
                if "gemini-3-" in model_id:
                    if "flash" in model_id:
                        return 1
                    return 0  # 3-pro
                if "gemini-2.5-pro" in model_id:
                    return 2
                if "gemini-2.5-flash" in model_id and "lite" not in model_id:
                    return 3
                if "gemini-2.0-flash" in model_id and "lite" not in model_id:
                    return 4
                if "gemini-1.5-pro" in model_id:
                    return 5
                return 99
            
            models.sort(key=sort_key)
            
            # 重複排除（同系統は1つだけ）
            seen = set()
            unique_models = []
            for m in models:
                # 基本名を抽出（gemini-3-pro, gemini-2.5-flash等）
                base = m["id"].split("-preview")[0].split("-exp")[0].split("-001")[0]
                if base not in seen:
                    seen.add(base)
                    unique_models.append(m)
            
            return unique_models[:10]
        except Exception as e:
            print(f"Gemini モデル取得エラー: {e}")
            return [
                {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "desc": "高速"}
            ]
    
    def _format_gemini_name(self, model_id: str) -> str:
        """Geminiモデル名を整形"""
        name = model_id.replace("-preview", "").replace("-exp", "").replace("-001", "")
        parts = name.split("-")
        
        # gemini-3-pro -> Gemini 3 Pro
        result = []
        for p in parts:
            if p == "gemini":
                result.append("Gemini")
            elif p in ["pro", "flash", "lite"]:
                result.append(p.capitalize())
            else:
                result.append(p)
        
        return " ".join(result)
    
    def _get_gemini_desc(self, model_id: str) -> str:
        """Geminiモデルの説明"""
        if "3-pro" in model_id:
            return "最新、最高性能"
        if "3-flash" in model_id:
            return "最新、高速"
        if "2.5-pro" in model_id:
            return "高性能"
        if "2.5-flash" in model_id and "lite" not in model_id:
            return "バランス型"
        if "2.0-flash" in model_id and "lite" not in model_id:
            return "高速"
        if "lite" in model_id:
            return "軽量、低コスト"
        return "Gemini"
    
    def _fetch_gemini_image_models(self) -> List[Dict]:
        """Gemini 画像生成モデル一覧を取得"""
        if not self.google_key:
            return []
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.google_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                
                # 画像生成モデル
                if "imagen" in name.lower() or ("image" in name.lower() and "gemini" in name.lower()) or "banana" in name.lower():
                    model_desc = "画像生成"
                    if "ultra" in name.lower():
                        model_desc = "最高品質"
                    elif "fast" in name.lower():
                        model_desc = "高速"
                    elif "banana" in name.lower():
                        model_desc = "最高品質（推奨）"
                    elif "4.0" in name:
                        model_desc = "高品質"
                    
                    models.append({
                        "id": name,
                        "name": self._format_image_model_name(name),
                        "desc": model_desc
                    })
            
            # banana > imagen ultra > imagen > gemini image
            def sort_key(m):
                if "banana" in m["id"]:
                    return 0
                if "ultra" in m["id"]:
                    return 1
                if "imagen-4.0" in m["id"] and "fast" not in m["id"]:
                    return 2
                if "gemini-3" in m["id"]:
                    return 3
                return 10
            
            models.sort(key=sort_key)
            return models
        except Exception as e:
            print(f"Gemini 画像モデル取得エラー: {e}")
            return [{"id": "nano-banana-pro-preview", "name": "Nano Banana Pro", "desc": "最高品質"}]
    
    def _format_image_model_name(self, model_id: str) -> str:
        """画像モデル名を整形"""
        replacements = {
            "nano-banana-pro-preview": "Nano Banana Pro",
            "imagen-4.0-ultra-generate-001": "Imagen 4.0 Ultra",
            "imagen-4.0-generate-001": "Imagen 4.0",
            "imagen-4.0-fast-generate-001": "Imagen 4.0 Fast",
            "gemini-3-pro-image-preview": "Gemini 3 Pro Image",
            "gemini-2.5-flash-image": "Gemini 2.5 Flash Image",
            "gemini-2.5-flash-image-preview": "Gemini 2.5 Flash Image",
        }
        return replacements.get(model_id, model_id.replace("-", " ").title())
    
    def save_models(self, models: Dict) -> bool:
        """モデル一覧をファイルに保存"""
        try:
            os.makedirs(os.path.dirname(MODELS_FILE), exist_ok=True)
            with open(MODELS_FILE, 'w', encoding='utf-8') as f:
                json.dump(models, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存エラー: {e}")
            return False
    
    def fetch_and_save(self) -> Dict:
        """取得して保存"""
        models = self.fetch_all()
        self.save_models(models)
        return models
