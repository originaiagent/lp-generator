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
        self.anthropic_api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip().strip('"').strip("'")
        self.openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip().strip('"').strip("'")
        self.google_api_key = (os.getenv("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
    
    def ask(self, prompt: str, task: str = "chat", images: List[Any] = None) -> str:
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
    
    def _ask_gemini(self, prompt: str, images: List[Any] = None) -> str:
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
                for img_item in images:
                    # img_itemは base64文字列 または {'data': ..., 'mime_type': ...} の辞書
                    mime_type = "image/jpeg"
                    img_data = img_item
                    
                    if isinstance(img_item, dict):
                        img_data = img_item.get('data')
                        mime_type = img_item.get('mime_type', "image/jpeg")
                    
                    # base64データを画像パートに変換（inline_data形式）
                    parts.append({
                        "inline_data": {
                            "mime_type": mime_type,
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
    
    def _get_image_info(self, source: str) -> Optional[dict]:
        """画像ソース（パスまたはURL）からデータとMIMEタイプを取得"""
        import base64
        import requests
        from pathlib import Path

        try:
            if source.startswith("http"):
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(source, headers=headers, timeout=30)
                response.raise_for_status()
                image_bytes = response.content
                content_type = response.headers.get("Content-Type", "image/jpeg")
                mime_type = "image/png" if "png" in content_type else "image/jpeg"
                if "gif" in content_type: mime_type = "image/gif"
            else:
                if not Path(source).exists():
                    return None
                with open(source, "rb") as f:
                    image_bytes = f.read()
                ext = source.lower().split('.')[-1]
                mime_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif"}
                mime_type = mime_types.get(ext, "image/jpeg")
            
            return {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode()
            }
        except Exception as e:
            print(f"Error loading image {source}: {e}")
            return None

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
            if reference_image_path:
                img_info = self._get_image_info(reference_image_path)
                if img_info:
                    contents.append(img_info)
            
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
        """画像を分析（Vision API）- ローカルパスまたはURL対応"""
        img_info = self._get_image_info(image_path)
        if not img_info:
            return f"画像分析エラー: 画像の読み込みに失敗しました ({image_path})"
        
        image_data = img_info["data"]
        mime_type = img_info["mime_type"]
        
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
        
        # inline_data形式で構築
        parts = [prompt]
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": image_data
            }
        })
        
        response = model.generate_content(parts)
        
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
    def generate_wireframe(self, image_path_or_url, prompt=None):
        """Generate a wireframe version of an existing image"""
        try:
            import google.generativeai as genai
            import uuid
            from pathlib import Path
            import base64
            
            api_key = self.google_api_key
            if not api_key:
                print("[ERROR] No Gemini API key for wireframe generation")
                return None
            
            genai.configure(api_key=api_key)
            
            # 既存の画像生成と同じモデルを使用
            image_settings = self.settings.get("image_generation", {})
            model_name = self.settings.get("image_model") or image_settings.get("model", "gemini-3-pro-image-preview")
            
            gen_model = genai.GenerativeModel(model_name)
            
            # デフォルトのワイヤーフレーム用プロンプト
            if not prompt:
                prompt = "この画像をワイヤーフレーム（構成案）に変換してください。完全なモノクロ・グレースケールで、写真はプレースホルダーボックスに、テキストは横線で表現してください。"
            
            # 参照画像情報を取得（_generate_image_geminiと同じパターン）
            contents = []
            img_info = self._get_image_info(image_path_or_url)
            if img_info:
                contents.append(img_info)
            else:
                print(f"[ERROR] Could not load source image for wireframe: {image_path_or_url}")
                return None
            
            contents.append(prompt)
            
            # API呼び出し（_generate_image_geminiと同じパターン）
            # 注意: モダリティ指定が必要なモデルの場合は以下を追加検討
            # generation_config=genai.GenerationConfig(response_modalities=["image", "text"])
            # ただし、_generate_image_geminiが使用していないため、まずはなしで試す
            response = gen_model.generate_content(contents)
            
            # 画像データを取得して保存（_generate_image_geminiと同じパターン）
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        
                        save_dir = Path("data/generated_images")
                        save_dir.mkdir(parents=True, exist_ok=True)
                        
                        filename = f"wf_{uuid.uuid4().hex[:8]}.png"
                        save_path = save_dir / filename
                        
                        raw_data = base64.b64decode(image_data) if isinstance(image_data, str) else image_data
                        
                        with open(save_path, "wb") as f:
                            f.write(raw_data)
                        
                        # トークン使用量を記録
                        if hasattr(response, 'usage_metadata'):
                            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                            self._record_usage("gemini", input_tokens, output_tokens, model_name)
                        
                        return {
                            "local_path": str(save_path),
                            "filename": filename,
                            "image_data": base64.b64encode(raw_data).decode('utf-8')
                        }

            print(f"[DEBUG] Wireframe - no image found in response")
            if response and response.candidates:
                for part in response.candidates[0].content.parts:
                    print(f"[DEBUG] Part type: {type(part)}, has inline_data: {hasattr(part, 'inline_data')}")
                    if hasattr(part, 'text'):
                        print(f"[DEBUG] Text response: {part.text[:300]}")
            
            return None
        except Exception as e:
            import traceback
            print(f"[ERROR] generate_wireframe: {e}")
            print(traceback.format_exc())
            return None
