"""
画像生成モジュール - DALL-E と Gemini 両対応
設定ファイルからモデルを読み込む
"""
import os
import json
import requests
from typing import Optional

MODELS_FILE = "data/models.json"

class ImageGenerator:
    """画像生成クラス（複数AI対応）"""
    
    def __init__(self, provider: str = "auto"):
        self.openai_key = os.environ.get('OPENAI_API_KEY')
        self.gemini_key = os.environ.get('GOOGLE_API_KEY')
        
        # 設定からモデルを取得
        try:
            from modules.settings_manager import SettingsManager
            settings = SettingsManager().get_settings()
            self.image_model = settings.get('image_model', '')
        except:
            self.image_model = ''
        
        if provider == "auto":
            if self.gemini_key:
                self.provider = "gemini"
            elif self.openai_key:
                self.provider = "openai"
            else:
                self.provider = None
        else:
            self.provider = provider
    
    def _get_default_model(self, provider: str) -> str:
        """設定ファイルから該当プロバイダのデフォルトモデルを取得"""
        try:
            if os.path.exists(MODELS_FILE):
                with open(MODELS_FILE, 'r', encoding='utf-8') as f:
                    models_config = json.load(f)
                
                image_models = models_config.get("image", {}).get(provider, [])
                if image_models:
                    return image_models[0]["id"]  # 最初のモデルをデフォルトに
        except Exception as e:
            print(f"モデル設定読み込みエラー: {e}")
        
        # フォールバック（設定ファイルがない場合）
        if provider == "openai":
            return "dall-e-3"
        elif provider == "gemini":
            return "nano-banana-pro-preview"
        return ""
    
    def generate(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """画像を生成してBase64を返す"""
        if self.provider == "openai":
            return self._generate_dalle(prompt, size)
        elif self.provider == "gemini":
            return self._generate_gemini(prompt)
        else:
            print("画像生成APIが設定されていません")
            return None
    
    def _generate_dalle(self, prompt: str, size: str) -> Optional[str]:
        """DALL-E で画像生成"""
        if not self.openai_key:
            print("OpenAI APIキーが設定されていません")
            return None
        
        model = self.image_model if self.image_model else self._get_default_model("openai")
        
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"
        }
        
        try:
            print(f"DALL-E 画像生成中... (model: {model})")
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result["data"][0]["b64_json"]
        except Exception as e:
            print(f"DALL-E エラー: {e}")
            return None
    
    def _generate_gemini(self, prompt: str) -> Optional[str]:
        """Gemini で画像生成"""
        if not self.gemini_key:
            print("Gemini APIキーが設定されていません")
            return None
        
        model = self.image_model if self.image_model else self._get_default_model("gemini")
        
        # Imagen 系は predict エンドポイント
        if 'imagen' in model:
            return self._generate_imagen(prompt, model)
        
        # その他は generateContent エンドポイント
        return self._generate_gemini_content(prompt, model)
    
    def _generate_gemini_content(self, prompt: str, model: str) -> Optional[str]:
        """Gemini generateContent API で画像生成"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        
        headers = {"Content-Type": "application/json"}
        
        data = {
            "contents": [{
                "parts": [{
                    "text": f"Generate an image: {prompt}"
                }]
            }],
            "generationConfig": {
                "responseModalities": ["image", "text"]
            }
        }
        
        try:
            print(f"Gemini 画像生成中... (model: {model})")
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        return part["inlineData"].get("data")
            
            print(f"Gemini: 画像データが見つかりません")
            return None
        except Exception as e:
            print(f"Gemini エラー: {e}")
            return None
    
    def _generate_imagen(self, prompt: str, model: str) -> Optional[str]:
        """Imagen API で画像生成"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={self.gemini_key}"
        
        headers = {"Content-Type": "application/json"}
        
        data = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "1:1"
            }
        }
        
        try:
            print(f"Imagen 画像生成中... (model: {model})")
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            if "predictions" in result and len(result["predictions"]) > 0:
                return result["predictions"][0].get("bytesBase64Encoded")
            
            print(f"Imagen: 画像データが見つかりません")
            return None
        except Exception as e:
            print(f"Imagen エラー: {e}")
            return None
    
    def get_provider_name(self) -> str:
        """現在のプロバイダ名を返す"""
        model = self.image_model if self.image_model else self._get_default_model(self.provider or "")
        if self.provider == "openai":
            return f"DALL-E ({model})"
        elif self.provider == "gemini":
            return f"Gemini ({model})"
        return "未設定"
