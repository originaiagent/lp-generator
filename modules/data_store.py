import json
import os
from datetime import datetime
from pathlib import Path
import requests
from supabase import create_client, Client

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
            try:
                self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"Supabase client init error: {e}")
                self.supabase = None
        else:
            self.supabase = None

    def _get_from_supabase(self, product_id: str):
        """Supabaseから取得 (REST API)"""
        if not self.use_supabase:
            return None
        try:
            url = f"{self.base_url}/lp_products?id=eq.{product_id}"
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
        if not self.use_supabase:
            return False
        try:
            url = f"{self.base_url}/lp_products"
            headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
            response = requests.post(url, headers=headers, json=product)
            return response.status_code in [200, 201]
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
        if not self.use_supabase:
            return None
        try:
            url = f"{self.base_url}/lp_products"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Supabase get all error: {e}")
        return None
    
    def get_product(self, product_id: str) -> dict:
        # Supabase Cloudを優先（Streamlit Cloud対応）
        if self.use_supabase:
            supabase_data = self._get_from_supabase(product_id)
            if supabase_data:
                return supabase_data
        
        # フォールバック：ローカルファイル
        file_path = self.data_dir / f"{product_id}.json"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Local file read error: {e}")
                return None
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
        
        # Supabase DBに保存（Streamlit Cloud対応）
        if self.use_supabase:
            self._save_to_supabase(product)
        
        # ローカルファイルにも保存（バックアップ）
        file_path = self.data_dir / f"{product_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2, default=str)
        
        return product_id
    
    def update_product(self, product_id: str, product: dict) -> bool:
        product['updated_at'] = datetime.now().isoformat()
        if 'id' not in product:
            product['id'] = product_id
        
        # Supabase DBに保存（Streamlit Cloud対応）
        if self.use_supabase:
            self._save_to_supabase(product)
        
        # ローカルファイルにも保存（バックアップ）
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
        # Supabaseから取得を試みる（Streamlit Cloud対応）
        if self.use_supabase:
            db_products = self._get_all_from_supabase()
            if db_products:
                return db_products  # リストをそのまま返す
        
        # フォールバック：ファイルから取得
        products = []
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    product = json.load(f)
                    products.append(product)
            except Exception:
                continue
        return products

    def upload_image(self, file_data, file_name: str, bucket_name: str = "product-dev-images") -> str:
        """Supabase Storageに画像をアップロードし、公開URLを返す"""
        if not self.supabase:
            return None
        
        try:
            # バケットの存在確認と作成
            buckets = self.supabase.storage.list_buckets()
            bucket_exists = any(b.name == bucket_name for b in buckets)
            
            if not bucket_exists:
                self.supabase.storage.create_bucket(bucket_name, options={"public": True})
            
            # ファイルのアップロード
            # 重複を避けるためにタイムスタンプなどを付与するか、呼び出し元で制御
            # ここでは単純に上書き(upsert)設定
            file_options = {"upsert": "true", "content-type": "image/jpeg"} # 簡易的にjpegとする
            if file_name.lower().endswith(".png"):
                 file_options["content-type"] = "image/png"
            
            res = self.supabase.storage.from_(bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options=file_options
            )
            
            # 公開URLを取得
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(file_name)
            return public_url
            
        except Exception as e:
            import streamlit as st
            st.error(f"Supabase storage upload error details: {str(e)}")
            print(f"Supabase storage upload error: {e}")
            return None

