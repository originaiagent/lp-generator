import json
import os
from datetime import datetime
from pathlib import Path
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# Supabase設定
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

class DataStore:
    def __init__(self, data_dir: str = "data/products"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.supabase: Client = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"Supabase connection failed: {e}")

    def _get_from_supabase(self, product_id: str):
        """Supabaseから取得"""
        if self.supabase:
            try:
                response = self.supabase.table("lp_products").select("*").eq("id", product_id).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0]
            except Exception as e:
                print(f"Supabase get error: {e}")
        return None
    
    def _save_to_supabase(self, product: dict):
        """Supabaseに保存"""
        if self.supabase:
            try:
                # 辞書をそのまま保存 (テーブルのカラムとキーが一致している前提)
                self.supabase.table("lp_products").upsert(product).execute()
                return True
            except Exception as e:
                print(f"Supabase save error: {e}")
        return False
    
    def _delete_from_supabase(self, product_id: str):
        """Supabaseから削除"""
        if self.supabase:
            try:
                self.supabase.table("lp_products").delete().eq("id", product_id).execute()
                return True
            except Exception as e:
                print(f"Supabase delete error: {e}")
        return False
    
    def _get_all_from_supabase(self):
        """Supabaseから全製品を取得"""
        if self.supabase:
            try:
                response = self.supabase.table("lp_products").select("*").execute()
                if response.data:
                    # IDをキーにした辞書に変換
                    products = {item['id']: item for item in response.data if 'id' in item}
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
