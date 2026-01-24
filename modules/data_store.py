import json
import os
from datetime import datetime
from pathlib import Path

# Replit DB対応（デプロイ環境でデータ永続化）
try:
    from replit import db as replit_db
    USE_REPLIT_DB = True
except ImportError:
    replit_db = None
    USE_REPLIT_DB = False


class DataStore:
    def __init__(self, data_dir: str = "data/products"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_from_replit_db(self, product_id: str):
        """Replit DBから取得"""
        if USE_REPLIT_DB and replit_db is not None:
            try:
                key = f"product_{product_id}"
                if key in replit_db:
                    return json.loads(replit_db[key])
            except Exception:
                pass
        return None
    
    def _save_to_replit_db(self, product_id: str, data: dict):
        """Replit DBに保存"""
        if USE_REPLIT_DB and replit_db is not None:
            try:
                key = f"product_{product_id}"
                replit_db[key] = json.dumps(data, ensure_ascii=False, default=str)
                return True
            except Exception:
                pass
        return False
    
    def _delete_from_replit_db(self, product_id: str):
        """Replit DBから削除"""
        if USE_REPLIT_DB and replit_db is not None:
            try:
                key = f"product_{product_id}"
                if key in replit_db:
                    del replit_db[key]
                    return True
            except Exception:
                pass
        return False
    
    def _get_all_from_replit_db(self):
        """Replit DBから全製品を取得"""
        if USE_REPLIT_DB and replit_db is not None:
            try:
                products = {}
                for key in replit_db.keys():
                    if key.startswith("product_"):
                        product_id = key.replace("product_", "")
                        products[product_id] = json.loads(replit_db[key])
                return products
            except Exception:
                pass
        return None
    
    def get_product(self, product_id: str) -> dict:
        # まずReplit DBから取得を試みる
        product = self._get_from_replit_db(product_id)
        if product:
            return product
        
        # ファイルから取得
        file_path = self.data_dir / f"{product_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                product = json.load(f)
                # Replit DBにも保存（同期）
                self._save_to_replit_db(product_id, product)
                return product
        return None
    
    def create_product(self, name: str) -> dict:
        """新規製品を作成"""
        import uuid
        product_id = f"prod_{uuid.uuid4().hex[:8]}"
        product = {
            "id": product_id,
            "name": name,
            "created_at": __import__('datetime').datetime.now().isoformat()
        }
        self.save_product(product)
        return product

    def save_product(self, product: dict) -> str:
        if 'id' not in product:
            product['id'] = f"prod_{os.urandom(4).hex()}"
        if 'created_at' not in product:
            product['created_at'] = datetime.now().isoformat()
        product['updated_at'] = datetime.now().isoformat()
        
        product_id = product['id']
        
        # Replit DBに保存
        self._save_to_replit_db(product_id, product)
        
        # ファイルにも保存（バックアップ）
        file_path = self.data_dir / f"{product_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2, default=str)
        
        return product_id
    
    def update_product(self, product_id: str, product: dict) -> bool:
        product['updated_at'] = datetime.now().isoformat()
        
        # Replit DBに保存
        self._save_to_replit_db(product_id, product)
        
        # ファイルにも保存
        file_path = self.data_dir / f"{product_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2, default=str)
        return True
    
    def delete_product(self, product_id: str) -> bool:
        # Replit DBから削除
        self._delete_from_replit_db(product_id)
        
        # ファイルからも削除
        file_path = self.data_dir / f"{product_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def list_products(self) -> list:
        products = []
        
        # Replit DBから取得を試みる
        db_products = self._get_all_from_replit_db()
        if db_products:
            return list(db_products.values())
        
        # ファイルから取得
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    product = json.load(f)
                    products.append(product)
                    # Replit DBにも保存（同期）
                    if 'id' in product:
                        self._save_to_replit_db(product['id'], product)
            except Exception:
                continue
        return products
