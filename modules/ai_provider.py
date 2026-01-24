import os
from typing import Dict, Any, List, Optional
import json
import streamlit as st
from modules.usage_tracker import UsageTracker

class AIProvider:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.current_provider = settings.get("default_provider", "gemini")
        self.current_model = settings.get("default_model", "gemini-1.5-flash")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
    
    def ask(self, prompt: str, task: str = "chat", images: List[str] = None) -> str:
        # タスク別プロバイダ対応
        task_models = self.settings.get("task_models", {})
        if images and "image_analysis_provider" in task_models:
            provider = task_models["image_analysis_provider"]
        else:
            provider = self.settings.get("llm_provider", self.settings.get("provider", self.current_provider))
        
        if provider == "anthropic" and self.anthropic_api_key:
            return self._ask_anthropic(prompt, images)
        elif provider == "openai" and self.openai_api_key:
            return self._ask_openai(prompt, images)
        elif provider == "gemini" and self.google_api_key:
            return self._ask_gemini(prompt, images)
        else:
            # フォールバック：利用可能なAPIを探す
            if self.google_api_key:
                return self._ask_gemini(prompt, images)
            elif self.anthropic_api_key:
                return self._ask_anthropic(prompt, images)
            elif self.openai_api_key:
                return self._ask_openai(prompt, images)
            else:
                return "エラー: APIキーが設定されていません。設定画面でAPIキーを確認してください。"
    
    def _ask_anthropic(self, prompt: str, images: List[str] = None) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            
            model = self.settings.get("model", "claude-3-5-sonnet-20241022")
            
            message = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            # トークン使用量を記録
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            self._record_usage("claude", input_tokens, output_tokens)
            
            return message.content[0].text
        except Exception as e:
            return f"Anthropic APIエラー: {str(e)}"
    
    def _ask_openai(self, prompt: str, images: List[str] = None) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            model = self.settings.get("model", "gpt-4o-mini")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048
            )
            # トークン使用量を記録
            if hasattr(response, 'usage') and response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self._record_usage("gpt", input_tokens, output_tokens)
            
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI APIエラー: {str(e)}"
    
    def _ask_gemini(self, prompt: str, images: List[str] = None) -> str:
        try:
            import google.generativeai as genai
            import base64
            genai.configure(api_key=self.google_api_key)
            
            # タスク別モデル選択
            task_models = self.settings.get("task_models", {})
            if images and "image_analysis" in task_models:
                model_name = task_models["image_analysis"]
            else:
                model_name = self.settings.get("llm_model", self.settings.get("model", "gemini-2.0-flash"))
            model = genai.GenerativeModel(model_name)
            
            if images:
                # 画像付きリクエスト
                parts = [prompt]
                for img_data in images:
                    # base64データを画像パートに変換（inline_data形式）
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_data
                        }
                    })
                response = model.generate_content(parts)
            else:
                response = model.generate_content(prompt)
            # トークン使用量を記録（Geminiはusage_metadataから取得）
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                self._record_usage("gemini", input_tokens, output_tokens)
            
            return response.text
        except Exception as e:
            return f"Gemini APIエラー: {str(e)}"
    
    def _record_usage(self, provider: str, input_tokens: int, output_tokens: int, model: str = None):
        """API使用量を記録"""
        try:
            tracker = UsageTracker()
            usage = tracker.record_usage(provider, input_tokens, output_tokens, "api_call", model)
            # session_stateに最後の使用量を保存
            if usage:
                st.session_state['last_api_usage'] = usage
        except Exception as e:
            print(f"[DEBUG] _record_usage error: {e}")  # デバッグ用
    
    def get_available_models(self, provider: str) -> List[str]:
        models_map = {
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"],
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        }
        return models_map.get(provider, [])
    
    def generate_image(self, prompt: str, size: str = "1024x1024", reference_image_path: str = None) -> dict:
        """画像を生成してローカルに保存"""
        # 設定から画像生成プロバイダを取得（複数の設定形式に対応）
        image_settings = self.settings.get("image_generation", {})
        provider = self.settings.get("image_provider") or image_settings.get("provider", "gemini")
        model = self.settings.get("image_model") or image_settings.get("model", "gemini-3-pro-image-preview")
        
        if provider == "gemini" and self.google_api_key:
            return self._generate_image_gemini(prompt, model, reference_image_path)
        elif provider == "openai" and self.openai_api_key:
            return self._generate_image_dalle(prompt, size)
        else:
            # フォールバック
            if self.google_api_key:
                return self._generate_image_gemini(prompt, model, reference_image_path)
            elif self.openai_api_key:
                return self._generate_image_dalle(prompt, size)
            else:
                return {"error": "画像生成用のAPIキーが設定されていません"}
    
    def _generate_image_dalle(self, prompt: str, size: str) -> dict:
        try:
            from openai import OpenAI
            import requests
            import uuid
            from pathlib import Path
            
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            
            # 画像をダウンロードして保存
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                save_dir = Path("data/generated_images")
                save_dir.mkdir(parents=True, exist_ok=True)
                
                filename = f"{uuid.uuid4().hex[:8]}.png"
                save_path = save_dir / filename
                
                with open(save_path, "wb") as f:
                    f.write(img_response.content)
                
                # トークン使用量を記録
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = getattr(response.usage, 'prompt_tokens', 0)
                    output_tokens = getattr(response.usage, 'completion_tokens', 0)
                    self._record_usage("gpt", input_tokens, output_tokens)
                
                return {"path": str(save_path), "url": image_url}
            else:
                return {"error": f"画像ダウンロード失敗: {img_response.status_code}"}
        
        except Exception as e:
            return {"error": f"DALL-E APIエラー: {str(e)}"}
    
    def _generate_image_gemini(self, prompt: str, model: str = "nano-banana-pro-preview", reference_image_path: str = None) -> dict:
        """Gemini/Imagen系で画像生成（参照画像対応）"""
        try:
            import google.generativeai as genai
            import uuid
            from pathlib import Path
            import base64
            
            genai.configure(api_key=self.google_api_key)
            
            gen_model = genai.GenerativeModel(model)
            
            # コンテンツを構築
            contents = []
            
            # 参照画像がある場合は追加
            if reference_image_path and Path(reference_image_path).exists():
                with open(reference_image_path, "rb") as f:
                    ref_image_data = f.read()
                ext = reference_image_path.lower().split('.')[-1]
                mime_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
                mime_type = mime_types.get(ext, "image/jpeg")
                contents.append({
                    "mime_type": mime_type,
                    "data": base64.b64encode(ref_image_data).decode()
                })
            
            contents.append(prompt)
            
            response = gen_model.generate_content(contents)
            
            # 画像データを取得して保存
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        
                        save_dir = Path("data/generated_images")
                        save_dir.mkdir(parents=True, exist_ok=True)
                        
                        filename = f"{uuid.uuid4().hex[:8]}.png"
                        save_path = save_dir / filename
                        
                        with open(save_path, "wb") as f:
                            f.write(base64.b64decode(image_data) if isinstance(image_data, str) else image_data)
                        
                        # トークン使用量を記録（画像生成もトークンベース）
                        if hasattr(response, 'usage_metadata'):
                            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                            self._record_usage("gemini", input_tokens, output_tokens, model)
                        
                        return {"path": str(save_path)}
            
            return {"error": "画像データが取得できませんでした"}
        
        except Exception as e:
            return {"error": f"Gemini画像生成エラー: {str(e)}"}
    
    def _has_api_key(self) -> bool:
        return any([
            self.anthropic_api_key,
            self.openai_api_key,
            self.google_api_key
        ])

    def analyze_image(self, image_path: str, prompt: str) -> str:
        """画像を分析（Vision API）"""
        import base64
        
        # 画像をBase64エンコード
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # 画像の拡張子からMIMEタイプを判定
        ext = image_path.lower().split('.')[-1]
        mime_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif"}
        mime_type = mime_types.get(ext, "image/jpeg")
        
        provider = self.settings.get("llm_provider", "gemini")
        
        try:
            if provider == "gemini":
                return self._analyze_image_gemini(image_data, mime_type, prompt)
            elif provider == "openai":
                return self._analyze_image_openai(image_data, mime_type, prompt)
            elif provider == "anthropic":
                return self._analyze_image_anthropic(image_data, mime_type, prompt)
        except Exception as e:
            return f"画像分析エラー: {e}"
    
    def _analyze_image_gemini(self, image_data: str, mime_type: str, prompt: str) -> str:
        import google.generativeai as genai
        # タスク別モデル設定を優先
        task_models = self.settings.get("task_models", {})
        model_name = task_models.get("image_analysis", self.settings.get("llm_model", "gemini-2.0-flash"))
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([
            {"mime_type": mime_type, "data": image_data},
            prompt
        ])
        # トークン使用量を記録
        if hasattr(response, 'usage_metadata'):
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            self._record_usage("gemini", input_tokens, output_tokens)
        return response.text
    
    def _analyze_image_openai(self, image_data: str, mime_type: str, prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model=self.settings.get("llm_model", "gpt-4o"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}}
                ]
            }]
        )
        # トークン使用量を記録
        if hasattr(response, 'usage') and response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            self._record_usage("gpt", input_tokens, output_tokens)
        return response.choices[0].message.content
    
    def _analyze_image_anthropic(self, image_data: str, mime_type: str, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.settings.get("llm_model", "claude-3-5-sonnet-20241022"),
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_data}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        # トークン使用量を記録
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self._record_usage("claude", input_tokens, output_tokens)
        return response.content[0].text
