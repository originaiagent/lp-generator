"""
モデル生成モジュール - 人物モデルの属性とプロンプトを管理し、画像を生成
"""
from typing import Dict, List, Optional

class ModelGenerator:
    """モデル生成クラス"""
    
    def __init__(self, ai_provider, prompt_manager):
        self.ai_provider = ai_provider
        self.prompt_manager = prompt_manager
        
        # 設定から画像生成プロバイダを取得
        try:
            from modules.settings_manager import SettingsManager
            settings = SettingsManager().get_settings()
            image_provider = settings.get("image_provider", "auto")
        except:
            image_provider = "auto"
        
        try:
            from modules.image_generator import ImageGenerator
            self.image_generator = ImageGenerator(image_provider)
        except Exception as e:
            print(f"ImageGenerator初期化エラー: {e}")
            self.image_generator = None
        
        try:
            from modules.prompt_optimizer import PromptOptimizer
            self.prompt_optimizer = PromptOptimizer()
        except Exception as e:
            print(f"PromptOptimizer初期化エラー: {e}")
            self.prompt_optimizer = None
    
    def generate_model(self, attributes: Dict[str, str], count: int = 3, custom_notes: str = "") -> List[Dict]:
        """モデルを生成"""
        results = []
        
        for i in range(count):
            # AIでプロンプトを最適化
            if self.prompt_optimizer:
                prompt = self.prompt_optimizer.optimize(attributes, custom_notes)
            else:
                prompt = self.build_prompt(attributes)
            
            # 画像生成
            image_data = None
            if self.image_generator:
                print(f"モデル{i+1}の画像を生成中...")
                image_data = self.image_generator.generate(prompt)
            
            model_data = {
                "id": i + 1,
                "attributes": attributes.copy(),
                "prompt": prompt,
                "image": image_data
            }
            results.append(model_data)
        
        return results
    
    def generate_optimized_prompt(self, attributes: Dict[str, str], custom_notes: str = "") -> str:
        """プロンプトのみを生成（画像生成なし）"""
        if self.prompt_optimizer:
            return self.prompt_optimizer.optimize(attributes, custom_notes)
        return self.build_prompt(attributes)
    
    def build_prompt(self, attributes: Dict[str, str]) -> str:
        """シンプルなプロンプト構築（フォールバック用）"""
        age = attributes.get('age', '30代')
        gender = attributes.get('gender', '男性')
        ethnicity = attributes.get('ethnicity', 'アジア系')
        atmosphere = attributes.get('atmosphere', 'ナチュラル')
        clothing = attributes.get('clothing', 'ビジネス')
        
        prompt = f"{age} {ethnicity} {gender}, {atmosphere} mood, wearing {clothing} attire"
        return prompt
    
    @staticmethod
    def get_attribute_options() -> Dict[str, List[str]]:
        return {
            "age": ["10代", "20代", "30代", "40代", "50代", "60代以上"],
            "gender": ["男性", "女性"],
            "ethnicity": ["アジア系", "白人系", "黒人系", "ラテン系", "中東系"],
            "atmosphere": ["ナチュラル", "エレガント", "カジュアル", "クール", "フレンドリー", "知的", "アクティブ"],
            "clothing": ["ビジネス", "カジュアル", "フォーマル", "スポーツ", "医療系", "作業着"]
        }
