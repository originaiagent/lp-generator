import json
import os

class ElementTypes:
    """要素タイプの管理クラス"""
    
    def __init__(self, config_path: str = "data/element_types.json"):
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {"categories": {}}
    
    def save_config(self):
        """設定ファイルを保存"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get_category(self, elem_type: str) -> str:
        """要素タイプからカテゴリを取得"""
        for cat_id, cat_data in self.config.get("categories", {}).items():
            if elem_type in cat_data.get("types", []):
                return cat_id
        return "unknown"
    
    def is_multiple_items(self, elem_type: str) -> bool:
        """複数項目タイプかどうか"""
        return self.get_category(elem_type) == "text_multiple"
    
    def is_visual(self, elem_type: str) -> bool:
        """ビジュアル系かどうか"""
        return self.get_category(elem_type) == "visual"
    
    def get_all_types(self) -> list:
        """全ての要素タイプを取得"""
        all_types = []
        for cat_data in self.config.get("categories", {}).values():
            all_types.extend(cat_data.get("types", []))
        return all_types
    
    def get_types_by_category(self, category: str) -> list:
        """カテゴリ別の要素タイプを取得"""
        cat_data = self.config.get("categories", {}).get(category, {})
        return cat_data.get("types", [])
    
    def add_type(self, category: str, elem_type: str) -> bool:
        """要素タイプを追加"""
        if category in self.config.get("categories", {}):
            types = self.config["categories"][category].get("types", [])
            if elem_type not in types:
                types.append(elem_type)
                self.config["categories"][category]["types"] = types
                self.save_config()
                return True
        return False
    
    def remove_type(self, category: str, elem_type: str) -> bool:
        """要素タイプを削除"""
        if category in self.config.get("categories", {}):
            types = self.config["categories"][category].get("types", [])
            if elem_type in types:
                types.remove(elem_type)
                self.config["categories"][category]["types"] = types
                self.save_config()
                return True
        return False
    
    def get_categories_info(self) -> dict:
        """全カテゴリの情報を取得"""
        return self.config.get("categories", {})
