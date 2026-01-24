import json
import os
from datetime import datetime
from pathlib import Path
import requests

# Supabase設定
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

class DataStore:
    def __init__(self, data_dir: str = "data/products"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_supabase = False
        self.headers = {}
        self.base_url = ""
        
        if SUPABASE_URL and SUPABASE_KEY:
            self.use_supabase = True
            self.base_url = f"{SUPABASE_URL}/rest/v1"
            self.headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }

    def _get_from_supabase(self, product_id: str):
        """Supabaseから取得 (REST API)"""
        if self.use_supabase:
            try:
                url = f"{self.base_url}/lp_products?id=eq.{product_id}&select=*"
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return data[0]
            except Exception as e:
                print(f"Supabase get error: {e}")
        return None
    
    def _save_to_supabase(self, product: dict):
        """Supabaseに保存 (REST API - Upsert)"""
        if self.use_supabase:
            try:
                url = f"{self.base_url}/lp_products"
                # on_conflictはurlパラメータで指定（idをキーにする）
                params = {"on_conflict": "id"}
                # POSTメソッドでupsertを行う（Prefer: resolution=merge-duplicates はヘッダーで指定可能だが、
                # SupabaseのREST APIではPOSTに on_conflict パラメータをつけるのが一般的）
                
                # Supabase REST APIのUpsert: POST to /table with Prefer: resolution=merge-duplicates
                headers = self.headers.copy()
                headers["Prefer"] = "resolution=merge-duplicates,return=representation"
                
                response = requests.post(url, headers=headers, json=product)
                
                if response.status_code in [200, 201]:
                    return True
                else:
                    print(f"Supabase save failed: {response.status_code} {response.text}")
            except Exception as e:
                print(f"Supabase save error: {e}")
        return False
    
    def _delete_from_supabase(self, product_id: str):
        """Supabaseから削除 (REST API)"""
        if self.use_supabase:
            try:
                url = f"{self.base_url}/lp_products?id=eq.{product_id}"
                response = requests.delete(url, headers=self.headers)
                if response.status_code in [200, 204]:
                    return True
            except Exception as e:
                print(f"Supabase delete error: {e}")
        return False
    
    def _get_all_from_supabase(self):
        """Supabaseから全製品を取得 (REST API)"""
        if self.use_supabase:
            try:
                url = f"{self.base_url}/lp_products?select=*"
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    # IDをキーにした辞書に変換
                    products = {item['id']: item for item in data if 'id' in item}
                    return products
            except Exception as e:
                print(f"Supabase list error: {e}")
        return None
    
    def get_product(self, product_id: str) -> dict:
        # まずSupabaseから取得を試みる
        product = self._get_from_supabase(product_id)
        if product:
            return product
        
        # ファイルから取得 (Supabase接続失敗時やデータがない場合のフォールバック)
        file_path = self.data_dir / f"{product_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                product = json.load(f)
                # Supabaseにも保存（同期試行）
                self._save_to_supabase(product)
                return product
        return None
    
    def create_product(self, name: str) -> dict:
        """新規製品を作成"""
        import uuid
        product_id = f"prod_{uuid.uuid4().hex[:8]}"
        product = {
            "id": product_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
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
        
        # Supabaseに保存
        self._save_to_supabase(product)
        
        # ファイルにも保存（バックアップ）
        file_path = self.data_dir / f"{product_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2, default=str)
        
        return product_id
    
    def update_product(self, product_id: str, product: dict) -> bool:
        product['updated_at'] = datetime.now().isoformat()
        
        # Supabaseに保存
        self._save_to_supabase(product)
        
        # ファイルにも保存
        file_path = self.data_dir / f"{product_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2, default=str)
        return True
    
    def delete_product(self, product_id: str) -> bool:
        # Supabaseから削除
        self._delete_from_supabase(product_id)
        
        # ファイルからも削除
        file_path = self.data_dir / f"{product_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def list_products(self) -> list:
        # Supabaseから取得を試みる
        db_products = self._get_all_from_supabase()
        if db_products:
            return list(db_products.values())
        
        # ファイルから取得 (Supabase失敗時)
        products = []
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    product = json.load(f)
                    products.append(product)
                    # Supabaseにも保存（同期試行）
                    if 'id' in product:
                        self._save_to_supabase(product)
            except Exception:
                continue
        return products
