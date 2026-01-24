"""
プロンプト最適化モジュール - 設定に基づいてLLMを選択
"""
import os
import requests
from typing import Dict, Optional

class PromptOptimizer:
    """設定に基づいてプロンプトを最適化"""
    
    def __init__(self):
        self.anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        self.openai_key = os.environ.get('OPENAI_API_KEY')
        self.google_key = os.environ.get('GOOGLE_API_KEY')
        
        # 設定を読み込む
        try:
            from modules.settings_manager import SettingsManager
            settings = SettingsManager().get_settings()
            self.provider = settings.get('llm_provider', 'openai')
            self.model = settings.get('llm_model', '')
        except:
            self.provider = 'openai'
            self.model = ''
    
    def optimize(self, attributes: Dict[str, str], custom_notes: str = "") -> str:
        """属性と備考からDALL-E/Imagen用の最適なプロンプトを生成"""
        
        system_prompt = """あなたはAI画像生成用のプロンプトエンジニアです。
与えられた人物属性と備考から、最高品質の画像を生成するためのプロンプトを作成してください。

【重要ルール】
1. 英語で出力すること
2. 必ず「photorealistic, not AI-generated looking, natural imperfections, authentic」を含めてAI画像っぽさを排除する
3. 備考欄に「アニメ」「イラスト」「レトロ写真」「水彩画」などスタイル指定があれば、それを最優先で反映する
4. スタイル指定がなければ、プロのスタジオ撮影のような高品質実写を目指す
5. 備考欄の指示は必ず全て反映する
6. 100-150語程度に収める
7. プロンプトのみを出力し、説明は不要

【スタイル別の対応】
- 指定なし/実写: プロの写真家が撮影したような自然なポートレート、スタジオライティング
- アニメ/イラスト: 高品質アニメスタイル、ただしAI特有の不自然さは避ける
- レトロ写真: フィルム感、粒子感、時代に合った色調
- その他: ユーザーの指定スタイルを最大限尊重"""

        user_message = f"""以下の属性と備考から、AI画像生成用の最適なプロンプトを作成してください。

【属性】
- 年齢: {attributes.get('age', '30代')}
- 性別: {attributes.get('gender', '男性')}
- 人種: {attributes.get('ethnicity', 'アジア系')}
- 雰囲気: {attributes.get('atmosphere', 'ナチュラル')}
- 服装: {attributes.get('clothing', 'ビジネス')}

【備考・追加指示】
{custom_notes if custom_notes else 'なし'}

上記を元に、最高品質の画像を生成するプロンプトを英語で出力してください。"""

        # 設定に基づいてAPIを呼び出し
        if self.provider == 'anthropic' and self.anthropic_key:
            return self._call_anthropic(system_prompt, user_message)
        elif self.provider == 'openai' and self.openai_key:
            return self._call_openai(system_prompt, user_message)
        elif self.provider == 'gemini' and self.google_key:
            return self._call_gemini(system_prompt, user_message)
        else:
            # フォールバック: 利用可能なAPIを使う
            if self.openai_key:
                return self._call_openai(system_prompt, user_message)
            elif self.anthropic_key:
                return self._call_anthropic(system_prompt, user_message)
            elif self.google_key:
                return self._call_gemini(system_prompt, user_message)
            else:
                return self._fallback_prompt(attributes, custom_notes)
    
    def _call_anthropic(self, system: str, user: str) -> str:
        """Anthropic APIを呼び出し"""
        try:
            model = self.model if self.model and 'claude' in self.model else 'claude-3-5-sonnet-20241022'
            
            headers = {
                "x-api-key": self.anthropic_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": model,
                "max_tokens": 500,
                "system": system,
                "messages": [{"role": "user", "content": user}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"].strip()
        except Exception as e:
            print(f"Anthropic APIエラー: {e}")
            return self._fallback_prompt({}, "")
    
    def _call_openai(self, system: str, user: str) -> str:
        """OpenAI APIを呼び出し"""
        try:
            model = self.model if self.model and 'gpt' in self.model else 'gpt-4o-mini'
            
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "max_tokens": 500
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"OpenAI APIエラー: {e}")
            return self._fallback_prompt({}, "")
    
    def _call_gemini(self, system: str, user: str) -> str:
        """Gemini APIを呼び出し"""
        try:
            model = self.model if self.model and 'gemini' in self.model else 'gemini-1.5-flash'
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.google_key}"
            
            headers = {"Content-Type": "application/json"}
            
            data = {
                "contents": [{
                    "parts": [{"text": f"{system}\n\n{user}"}]
                }]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            candidates = result.get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"].strip()
            return self._fallback_prompt({}, "")
        except Exception as e:
            print(f"Gemini APIエラー: {e}")
            return self._fallback_prompt({}, "")
    
    def _fallback_prompt(self, attributes: Dict, custom: str) -> str:
        """フォールバック用のプロンプト"""
        age = attributes.get('age', '30s')
        gender = attributes.get('gender', 'person')
        ethnicity = attributes.get('ethnicity', 'Asian')
        atmosphere = attributes.get('atmosphere', 'natural')
        clothing = attributes.get('clothing', 'business')
        
        prompt = f"Professional studio portrait of a {age} {ethnicity} {gender}, "
        prompt += f"{atmosphere} expression, wearing {clothing} attire, "
        prompt += "photorealistic, not AI-generated looking, natural imperfections, authentic, "
        prompt += "soft studio lighting, neutral background, high-end fashion photography, "
        prompt += "8k resolution, sharp focus"
        
        if custom:
            prompt += f", {custom}"
        
        return prompt
