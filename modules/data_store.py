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
        self.supabase: Client = None
        self.service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.last_error = None  # 詳細エラー保持用
        
        # 環境変数から設定を取得
        base_url = os.environ.get("SUPABASE_URL")
        api_key = os.environ.get("SUPABASE_KEY")

        if base_url and (api_key or self.service_key):
            try:
                # サービスキーがあれば優先的に使用（RLS回避用）
                key_to_use = self.service_key if self.service_key else api_key
                self.supabase = create_client(base_url, key_to_use)
                self.use_supabase = True
                self.base_url = f"{base_url}/rest/v1"
                
                # ヘッダー情報を取得（手動構築ではなくクライアントから取得）
                if self.supabase.options and self.supabase.options.headers:
                     self.headers = self.supabase.options.headers
                else:
                     # フォールバック
                     self.headers = {
                        "apikey": key_to_use,
                        "Authorization": f"Bearer {key_to_use}",
                        "Content-Type": "application/json"
                     }
                     
                if self.service_key:
                    print("Using Supabase Service Role Key (Admin Access)")
                    
            except Exception as e:
                print(f"Supabase connection/init error: {e}")
                self.use_supabase = False
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
            
            # スキーマに存在しないローカル専用フィールドを除外
            data_to_save = product.copy()
            exclude_keys = ["review_sheet_data"] # 随時追加。DBカラムにあるものは除外しない
            for key in exclude_keys:
                if key in data_to_save:
                    del data_to_save[key]
            
            response = requests.post(url, headers=headers, json=data_to_save)
            
            if response.status_code not in [200, 201]:
                self.last_error = f"Status: {response.status_code}, Body: {response.text}"
                print(f"Supabase save failed: {self.last_error}")
                return False
                
            return True
        except Exception as e:
            self.last_error = str(e)
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
        product_data = None
        
        # Supabase Cloudを優先（Streamlit Cloud対応）
        if self.use_supabase:
            product_data = self._get_from_supabase(product_id)
        
        # ローカルファイルからデータを取得（バックアップまたは補完用）
        local_data = None
        file_path = self.data_dir / f"{product_id}.json"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
            except Exception as e:
                print(f"Local file read error: {e}")

        # Supabaseデータがある場合でも、ローカルデータで特定のフィールドを補完する
        # (Supabaseのスキーマ変更などが間に合っていない場合への対策)
        if product_data:
            if local_data:
                # 補完したいフィールド（Supabaseに無い可能性があるもの、またはローカルパス）
                merge_keys = [
                    "lp_analyses", "lp_analyses_dict", "review_sheet_data", "tone_manner",
                    "reference_lp_images", "tone_manner_images", # ローカルパスも補完
                    "product_images", "model_images", "model_prompts",
                    "reference_lp_image_urls", "tone_manner_image_urls", "product_image_urls"
                ]
                for key in merge_keys:
                    if (key not in product_data or not product_data[key]) and (key in local_data and local_data[key]):
                        product_data[key] = local_data[key]
            
            # None対策: リスト型フィールドがNoneの場合は[]に変換
            list_keys = ["reference_lp_images", "reference_lp_image_urls", "lp_analyses", "tone_manner_images", "tone_manner_image_urls"]
            for key in list_keys:
                if key in product_data and product_data[key] is None:
                    product_data[key] = []

            return product_data
        
        # Supabaseになければローカルデータを返す
        if local_data:
            return local_data
            
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
            if not self._save_to_supabase(product):
                import streamlit as st
                error_msg = self.last_error if self.last_error else "Unknown error"
                st.error(f"データベース保存エラー: {error_msg}")
                return False
        
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

    def upload_image(self, file_data, file_name: str, bucket_name: str = "lp-generator-images") -> str:
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

