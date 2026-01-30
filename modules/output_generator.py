from typing import Dict, List
import json

class OutputGenerator:
    def __init__(self, ai_provider, prompt_manager):
        self.ai_provider = ai_provider
        self.prompt_manager = prompt_manager

    def extract_image_elements(self, product_data: Dict) -> List[Dict]:
        """ページ詳細から画像要素を抽出"""
        image_elements = []
        
        page_contents = product_data.get('page_contents', {})
        for page_id, content in page_contents.items():
            if not isinstance(content, dict):
                continue
            
            result = content.get('result', {})
            
            # resultがstrの場合はスキップ（旧形式）
            if isinstance(result, str):
                continue
            
            parsed = result.get('parsed', result) if isinstance(result, dict) else {}
            
            if isinstance(parsed, dict):
                elements = parsed.get('elements', [])
                for elem in elements:
                    if elem.get('type') == '画像':
                        image_elements.append({
                            'page_id': page_id,
                            'order': elem.get('order', 0),
                            'description': elem.get('description', ''),
                            'items': elem.get('items', [])
                        })
        
        return image_elements

    def get_tone_manner(self, product_data: Dict) -> Dict:
        """トンマナ情報を取得"""
        tone_manner = product_data.get('tone_manner', {})
        if isinstance(tone_manner, dict) and 'result' in tone_manner:
            return tone_manner['result']
        return tone_manner if isinstance(tone_manner, dict) else {}

    def build_image_prompt(self, product_data: Dict) -> List[Dict]:
        """画像生成用プロンプトを作成"""
        image_elements = self.extract_image_elements(product_data)
        tone_manner = self.get_tone_manner(product_data)
        
        prompts = []
        
        for img_elem in image_elements:
            # 画像指示を取得
            descriptions = []
            if img_elem.get('description'):
                descriptions.append(img_elem['description'])
            if img_elem.get('items'):
                for item in img_elem['items']:
                    if isinstance(item, dict):
                        descriptions.append(item.get('description', ''))
                    else:
                        descriptions.append(str(item))
            
            # トンマナ情報を追加
            colors = tone_manner.get('colors', {})
            style = tone_manner.get('overall_style', {})
            
            prompt_data = {
                'page_id': img_elem['page_id'],
                'order': img_elem['order'],
                'description': ' / '.join(descriptions),
                'tone_manner': {
                    'main_color': colors.get('main', ''),
                    'accent_color': colors.get('accent', ''),
                    'background': colors.get('background', ''),
                    'impression': style.get('impression', ''),
                    'target': f"{style.get('target_gender', '')} / {style.get('target_age', '')}"
                }
            }
            prompts.append(prompt_data)
        
        return prompts

    def generate_image_prompt_text(self, prompt_data: Dict) -> str:
        """画像生成API用のプロンプトテキストを生成"""
        parts = []
        
        # メインの説明
        if prompt_data.get('description'):
            parts.append(prompt_data['description'])
        
        # トンマナ
        tm = prompt_data.get('tone_manner', {})
        if tm.get('main_color'):
            parts.append(f"Main color: {tm['main_color']}")
        if tm.get('accent_color'):
            parts.append(f"Accent color: {tm['accent_color']}")
        if tm.get('impression'):
            parts.append(f"Style: {tm['impression']}")
        
        return ', '.join(parts)

    def generate_design_instruction(self, product_data: Dict) -> str:
        """AIを使用してデザイナー向け指示書を生成"""
        # 製品名
        product_name = product_data.get('name', '製品名未設定')
        
        # 構成情報を取得
        structure = product_data.get('structure', {})
        if isinstance(structure, dict) and 'result' in structure:
            structure = structure['result']
        pages = structure.get('pages', []) if isinstance(structure, dict) else []
        
        # コンテンツ詳細を取得
        page_contents = product_data.get('page_contents', {})
        
        # トンマナ情報を取得
        tone_manner = self.get_tone_manner(product_data)
        
        # 指示書生成用にデータを整理
        input_data_list = []
        for page in pages:
            page_id = page.get('id', 'unknown')
            content_data = page_contents.get(page_id, {})
            parsed = {}
            if isinstance(content_data, dict) and 'result' in content_data:
                res = content_data['result']
                parsed = res.get('parsed', res) if isinstance(res, dict) else {}
            
            input_data_list.append({
                "order": page.get('order'),
                "title": page.get('title'),
                "role": page.get('role'),
                "appeals": page.get('appeals', []),
                "elements": page.get('elements', []),
                "generated_content": parsed
            })
        
        # トンマナ情報のテキスト化
        tone_manner_text = "未設定"
        if tone_manner:
            colors = tone_manner.get('colors', {})
            style = tone_manner.get('overall_style', {})
            tone_manner_text = f"""
- メインカラー: {colors.get('main', '')}
- アクセントカラー: {colors.get('accent', '')}
- 背景色: {colors.get('background', '')}
- 文字色: {colors.get('text', '')}
- フォント: {tone_manner.get('font', {}).get('type', '')} ({tone_manner.get('font', {}).get('weight', '')})
- 印象: {style.get('impression', '')}
- ターゲット: {style.get('target_gender', '')} / {style.get('target_age', '')}
"""

        # プロンプト変数
        variables = {
            "product_name": product_name,
            "tone_manner": tone_manner_text,
            "content_json": json.dumps(input_data_list, ensure_ascii=False, indent=2)
        }
        
        prompt = self.prompt_manager.get_prompt("designer_instruction_generation", variables)
        
        # AIで生成
        response = self.ai_provider.generate_text(prompt)
        
        return response
