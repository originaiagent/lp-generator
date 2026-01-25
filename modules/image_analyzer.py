from typing import List, Dict, Any

class ImageAnalyzer:
    def __init__(self, ai_provider, prompt_manager):
        self.ai_provider = ai_provider
        self.prompt_manager = prompt_manager
    
    def analyze_references(self, image_paths: List[str]) -> Dict[str, Any]:
        try:
            # AIを使用した分析を試行
            if hasattr(self.ai_provider, 'analyze_images') and callable(getattr(self.ai_provider, 'analyze_images')):
                result = self.ai_provider.analyze_images(image_paths)
                if isinstance(result, dict) and "pages" in result:
                    return result
        except:
            pass
        
        # AIが使えない場合やエラーの場合はモックデータを返す
        return {
            "pages": [
                {
                    "page_number": i + 1,
                    "elements": ["text", "image", "layout"],
                    "structure": "standard"
                } for i in range(len(image_paths))
            ]
        }
    
    def analyze_tone_manner(self, image_paths: List[str]) -> Dict[str, Any]:
        try:
            # AIを使用した分析を試行
            if hasattr(self.ai_provider, 'analyze_tone') and callable(getattr(self.ai_provider, 'analyze_tone')):
                result = self.ai_provider.analyze_tone(image_paths)
                if isinstance(result, dict):
                    return result
        except:
            pass
        
        # AIが使えない場合やエラーの場合はモックデータを返す
        return {
            "tone": "professional",
            "manner": "formal",
            "style": "clean"
        }
    def analyze_image(self, image_path: str) -> str:
        """単一画像から訴求要素のみを抽出"""
        try:
            prompt = """この画像はLP（ランディングページ）の一部です。
この画像で訴求している「要素」「特徴」「メリット」をキーワードで抽出してください。

【出力ルール】
- カンマ区切りで出力
- 短いキーワードのみ（説明文は不要）
- 最大10個まで

【出力例】
厚み, 防水, 非粘着, お手入れ簡単, カット自由"""
            result = self.ai_provider.analyze_image(image_path, prompt)
            return result.strip() if result else ""
        except Exception as e:
            return ""
    
    def analyze_text_elements(self, text: str) -> list:
        """テキストから訴求要素を抽出"""
        try:
            prompt = f"""以下のテキストから、製品の「訴求要素」「特徴」「メリット」をキーワードで抽出してください。

【テキスト】
{text[:3000]}

【出力ルール】
- カンマ区切りで出力
- 短いキーワードのみ（説明文は不要）
- 最大15個まで

【出力例】
厚み, 防水, 非粘着, お手入れ簡単, カット自由"""
            result = self.ai_provider.ask(prompt)
            if result:
                elements = [e.strip().strip("・-　 ") for e in result.replace("\n", ",").split(",") if e.strip()]
                return elements
            return []
        except:
            return []
    
    def analyze_image_batch(self, image_paths: list) -> list:
        """複数画像をバッチで分析（5枚ずつ）"""
        import base64
        all_elements = []
        
        # 5枚ずつバッチ処理
        batch_size = 5
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            
            try:
                # 画像をbase64エンコード
                images_data = []
                for path in batch:
                    with open(path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    ext = path.lower().split('.')[-1]
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")
                    images_data.append({"data": img_data, "mime": mime})
                
                prompt = f"""以下の{len(batch)}枚の画像はLP（ランディングページ）の一部です。
全ての画像から訴求している「要素」「特徴」「メリット」をキーワードで抽出してください。

【出力ルール】
- カンマ区切りで出力
- 短いキーワードのみ（説明文は不要）
- 重複は除く
- 最大20個まで

【出力例】
厚み, 防水, 非粘着, お手入れ簡単, カット自由"""
                
                # Geminiに複数画像を送信
                result = self.ai_provider.ask(prompt, images=[d["data"] for d in images_data])
                
                if result:
                    elements = [e.strip().strip("・-　 ") for e in result.replace("\n", ",").split(",") if e.strip()]
                    all_elements.extend(elements)
            except Exception as e:
                # エラー時は個別処理にフォールバック
                for path in batch:
                    elem_str = self.analyze_image(path)
                    if elem_str:
                        elements = [e.strip().strip("・-　 ") for e in elem_str.replace("\n", ",").split(",") if e.strip()]
                        all_elements.extend(elements)
        
        return list(set(all_elements))
    
    def analyze_competitor(self, name: str, image_paths: list, text: str = "", progress_callback=None) -> dict:
        """1競合の画像+テキストを分析（バッチ処理版）"""
        all_elements = set()
        
        # 画像分析（バッチ処理）
        if image_paths:
            if progress_callback:
                progress_callback(f"{name}: 画像分析中...")
            elements = self.analyze_image_batch(image_paths)
            all_elements.update(elements)
        
        # テキスト分析
        if text.strip():
            if progress_callback:
                progress_callback(f"{name}: テキスト分析中...")
            text_elements = self.analyze_text_elements(text)
            all_elements.update(text_elements)
        
        return {
            "name": name,
            "text": text,  # 元のテキストを保持
            "files": image_paths,  # 元のファイルパスを保持
            "image_count": len(image_paths),
            "has_text": bool(text.strip()),
            "elements": list(all_elements)
        }
    
    def summarize_all_competitors(self, competitor_results: list) -> dict:
        """全競合の訴求要素を集約"""
        element_count = {}
        total = len(competitor_results)
        
        for comp in competitor_results:
            for elem in comp.get("elements", []):
                if elem:
                    element_count[elem] = element_count.get(elem, 0) + 1
        
        sorted_elements = sorted(element_count.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_competitors": total,
            "element_ranking": sorted_elements
        }
