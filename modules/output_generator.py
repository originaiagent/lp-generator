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
        """デザイナー向け指示書を生成"""
        instruction_parts = []
        
        # 製品情報
        instruction_parts.append(f"# {product_data.get('name', '製品名未設定')} LP制作指示書\n")
        
        # トンマナ
        tone_manner = self.get_tone_manner(product_data)
        if tone_manner:
            instruction_parts.append("## トーン＆マナー\n")
            colors = tone_manner.get('colors', {})
            if colors:
                instruction_parts.append("### カラー")
                instruction_parts.append(f"- メイン: {colors.get('main', '未設定')}")
                instruction_parts.append(f"- アクセント: {colors.get('accent', '未設定')}")
                instruction_parts.append(f"- 背景: {colors.get('background', '未設定')}")
                instruction_parts.append(f"- テキスト: {colors.get('text', '未設定')}\n")
            
            font = tone_manner.get('font', {})
            if font:
                instruction_parts.append("### フォント")
                instruction_parts.append(f"- 種類: {font.get('type', '未設定')}")
                instruction_parts.append(f"- 太さ: {font.get('weight', '未設定')}")
                instruction_parts.append(f"- スタイル: {font.get('style', '未設定')}\n")
            
            style = tone_manner.get('overall_style', {})
            if style:
                instruction_parts.append("### 全体の印象")
                instruction_parts.append(f"- 印象: {style.get('impression', '未設定')}")
                instruction_parts.append(f"- ターゲット: {style.get('target_gender', '')} / {style.get('target_age', '')}\n")
        
        # ページ構成
        structure = product_data.get('structure', {})
        if isinstance(structure, dict) and 'result' in structure:
            structure = structure['result']
        
        pages = structure.get('pages', []) if isinstance(structure, dict) else []
        if pages:
            instruction_parts.append("## ページ構成\n")
            for page in pages:
                instruction_parts.append(f"### P{page.get('order', '')} - {page.get('title', '')}")
                instruction_parts.append(f"役割: {page.get('role', '')}")
                appeals = page.get('appeals', [])
                if appeals:
                    instruction_parts.append(f"訴求: {', '.join(appeals)}\n")
        
        # コンテンツ詳細
        page_contents = product_data.get('page_contents', {})
        if page_contents:
            instruction_parts.append("## コンテンツ詳細\n")
            for page_id, content in page_contents.items():
                result = content.get('result', {})
                display = result.get('display', '')
                if display:
                    instruction_parts.append(f"### {page_id}")
                    instruction_parts.append(f"{display}\n")
        
        return '\n'.join(instruction_parts)
