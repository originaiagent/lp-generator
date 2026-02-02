import json
import os
from datetime import datetime
from pathlib import Path
import requests
from urllib.parse import unquote
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
                    "reference_lp_image_urls", "tone_manner_image_urls", "product_image_urls",
                    "designer_instruction"
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
                return False
        
        # ローカルファイルにも保存（バックアップ）
        file_path = self.data_dir / f"{product_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product, f, ensure_ascii=False, indent=2, default=str)
        return True

    def duplicate_product(self, product_id):
        """製品を複製して新しい製品を作成"""
        import uuid
        
        # 元の製品を取得
        original = self.get_product(product_id)
        if not original:
            return None
        
        # 新しい製品IDを生成
        new_product_id = f"prod_{uuid.uuid4().hex[:8]}"
        
        # 複製データを作成
        new_product = original.copy()
        new_product['id'] = new_product_id
        new_product['name'] = f"{original.get('name', '')}のコピー"
        new_product['created_at'] = datetime.now().isoformat()
        new_product['updated_at'] = datetime.now().isoformat()
        
        # 画像をコピー（Supabase使用時）
        if self.use_supabase:
            # 製品画像をコピー
            new_product['product_image_urls'] = self._copy_images_to_new_product(
                original.get('product_image_urls') or [],
                new_product_id,
                'product_images'
            )
            
            # 参考LP画像をコピー
            new_product['reference_lp_image_urls'] = self._copy_images_to_new_product(
                original.get('reference_lp_image_urls') or [],
                new_product_id,
                'reference_lp'
            )
            
            # トンマナ画像をコピー
            new_product['tone_manner_image_urls'] = self._copy_images_to_new_product(
                original.get('tone_manner_image_urls') or [],
                new_product_id,
                'tone_manner'
            )
            
            # 競合画像をコピー
            competitor_data = new_product.get('competitor_analysis_v2') or {}
            competitors = competitor_data.get('competitors') or []
            for i, comp in enumerate(competitors):
                comp['file_urls'] = self._copy_images_to_new_product(
                    comp.get('file_urls') or [],
                    new_product_id,
                    f'competitors/{i}'
                )
            new_product['competitor_analysis_v2'] = competitor_data
            
            # ローカルパスは空にする
            new_product['product_images'] = []
            new_product['reference_lp_images'] = []
            new_product['tone_manner_images'] = []
        
        # 新しい製品を保存
        if self.use_supabase:
            data_to_save = new_product.copy()
            exclude_keys = ["review_sheet_data"]
            for key in exclude_keys:
                if key in data_to_save:
                    del data_to_save[key]
            
            result = self.supabase.table("lp_products").insert(data_to_save).execute()
            return result.data[0] if result.data else None
        else:
            self.save_product(new_product)
            return new_product

    def _copy_images_to_new_product(self, image_urls, new_product_id, folder):
        """画像を新しい製品フォルダにコピー"""
        import uuid
        import requests
        
        new_urls = []
        for url in image_urls:
            try:
                # 画像をダウンロード
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    # 新しいファイル名を生成
                    extension = url.split('.')[-1].split('?')[0]
                    if len(extension) > 5: # 拡張子がおかしい場合はjpgにフォールバック
                        extension = 'jpg'
                    new_filename = f"{uuid.uuid4().hex[:12]}.{extension}"
                    new_path = f"{new_product_id}/{folder}/{new_filename}"
                    
                    # 新しい場所にアップロード
                    new_url = self.upload_image(
                        response.content,
                        new_path,
                        bucket_name="lp-generator-images"
                    )
                    if new_url:
                        new_urls.append(new_url)
                    else:
                        # アップロード失敗時は元のURLを使用（フォールバック）
                        new_urls.append(url)
                else:
                    new_urls.append(url)
            except Exception as e:
                print(f"画像コピーエラー: {e}")
                new_urls.append(url)
        
        return new_urls

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
        """画像をSupabase Storageにアップロードし、公開URLを返す"""
        if not self.supabase:
            return None
        
        try:
            # バケットの存在確認と作成
            buckets = self.supabase.storage.list_buckets()
            bucket_exists = any(b.name == bucket_name for b in buckets)
            if not bucket_exists:
                self.supabase.storage.create_bucket(bucket_name, options={"public": True})
            
            file_options = {"upsert": "true", "content-type": "image/jpeg"}
            if file_name.lower().endswith(".png"):
                file_options["content-type"] = "image/png"
            elif file_name.lower().endswith(".webp"):
                file_options["content-type"] = "image/webp"
            
            # 1. アップロード処理
            self.supabase.storage.from_(bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options=file_options
            )
            
            # 2. 公開URLを取得
            url_result = self.supabase.storage.from_(bucket_name).get_public_url(file_name)
            
            # URLの抽出
            url = None
            if isinstance(url_result, str):
                url = url_result
            elif isinstance(url_result, dict):
                url = url_result.get('publicUrl') or url_result.get('public_url')
            elif hasattr(url_result, 'public_url'):
                url = url_result.public_url
            
            return url
            
        except Exception as e:
            # 失敗しても続行（URL取得は試みる価値がある場合もあるが、ここではメソッド全体で例外処理）
            print(f"Supabase storage upload error: {e}")
            return None

    def delete_image(self, file_path: str, bucket_name: str = "lp-generator-images") -> bool:
        """Supabase Storageからファイルを削除する"""
        if not self.supabase:
            return False
        
        try:
            # 引数のパスからスラッシュ等を除去して整形（必要に応じて）
            # もしフルURLが渡された場合は、パス部分だけを抽出する
            path_to_delete = file_path
            if "storage/v1/object/public/" in file_path:
                path_to_delete = file_path.split(f"{bucket_name}/")[-1]
            
            res = self.supabase.storage.from_(bucket_name).remove([path_to_delete])
            return True
        except Exception as e:
            print(f"Supabase storage delete error: {e}")
            return False

    def delete_storage_file(self, file_url, bucket_name: str = "lp-generator-images") -> bool:
        """Supabase StorageのファイルをURLから削除"""
        if not self.supabase:
            return False
        try:
            # URLからパスを抽出
            # 例: https://xxx.supabase.co/storage/v1/object/public/lp-generator-images/prod_xxx/reference_lp/image.jpg
            # → prod_xxx/reference_lp/image.jpg
            if f'{bucket_name}/' in file_url:
                path = file_url.split(f'{bucket_name}/')[1]
                # クエリパラメータ等が含まれている場合は除去
                path = path.split('?')[0]
                # URLデコード（%20 → 空白など）
                path = unquote(path)
                self.supabase.storage.from_(bucket_name).remove([path])
                return True
        except Exception as e:
            print(f"Storage削除エラー: {e}")
        return False

    def delete_storage_files(self, file_urls, bucket_name: str = "lp-generator-images"):
        """複数ファイルを削除"""
        if not file_urls:
            return
        for url in file_urls:
            if url:
                self.delete_storage_file(url, bucket_name)

    def get_presets(self, preset_type):
        """プリセット一覧を取得"""
        if not self.supabase:
            return []
        try:
            response = self.supabase.table('image_presets').select('*').eq('type', preset_type).order('created_at', desc=True).execute()
            return response.data or []
        except Exception as e:
            print(f"Error fetching presets: {e}")
            return []

    def save_preset(self, name, preset_type, images):
        """プリセットを保存"""
        if not self.supabase:
            return None
        try:
            data = {
                'name': name,
                'type': preset_type,
                'images': images
            }
            response = self.supabase.table('image_presets').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error saving preset: {e}")
            return None

    def delete_preset(self, preset_id):
        """プリセットを削除"""
        if not self.supabase:
            return False
        try:
            self.supabase.table('image_presets').delete().eq('id', preset_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting preset: {e}")
            return False

    def delete_preset_with_images(self, preset_id, preset_images):
        """プリセットとその画像を削除"""
        # Storage内のプリセット画像を削除
        if preset_images:
            for img_url in preset_images:
                try:
                    self.delete_storage_file(img_url)
                except Exception as e:
                    print(f"Error deleting storage file during preset deletion: {e}")
        
        # DBからプリセットを削除
        return self.delete_preset(preset_id)

    def save_diagnosis(self, product_id, exposure_type, personas, evaluations, summary):
        """LP診断結果を保存"""
        if not self.supabase:
            return None
        try:
            data = {
                "product_id": product_id,
                "exposure_type": exposure_type,
                "personas": personas,
                "evaluations": evaluations,
                "summary": summary
            }
            result = self.supabase.table("lp_diagnoses").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error saving diagnosis: {e}")
            return None

    def get_diagnoses(self, product_id):
        """製品のLP診断履歴を取得"""
        if not self.supabase:
            return []
        try:
            result = self.supabase.table("lp_diagnoses").select("*").eq("product_id", product_id).order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching diagnoses: {e}")
            return []

    def get_latest_diagnosis(self, product_id):
        """製品の最新LP診断を取得"""
        if not self.supabase:
            return None
        try:
            result = self.supabase.table("lp_diagnoses").select("*").eq("product_id", product_id).order("created_at", desc=True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching latest diagnosis: {e}")
            return None

    # --- Employee AI 関連 ---

    def get_employee_personas(self):
        """全従業員AIペルソナを取得"""
        if not self.supabase:
            return []
        try:
            result = self.supabase.table("employee_personas").select("*").eq("is_active", True).order("created_at").execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching employee personas: {e}")
            return []

    def add_employee_persona(self, data):
        """従業員AIペルソナを新規登録"""
        if not self.supabase:
            return None
        try:
            data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            result = self.supabase.table("employee_personas").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error adding employee persona: {e}")
            return None

    def update_employee_persona(self, employee_id, data):
        """従業員AIペルソナを更新"""
        if not self.supabase:
            return None
        try:
            data['updated_at'] = datetime.now().isoformat()
            result = self.supabase.table("employee_personas").update(data).eq("id", employee_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating employee persona: {e}")
            return None

    def delete_employee_persona(self, employee_id):
        """従業員AIペルソナを削除（非活性化）"""
        if not self.supabase:
            return False
        try:
            # ソフトデリート (is_active = false)
            self.supabase.table("employee_personas").update({"is_active": False}).eq("id", employee_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting employee persona: {e}")
            return False

    def get_employee_feedback(self, employee_id, limit=20):
        """特定の従業員の過去のフィードバックを取得（学習用）"""
        if not self.supabase:
            return []
        try:
            result = self.supabase.table("employee_feedback")\
                .select("*")\
                .eq("employee_id", employee_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching employee feedback: {e}")
            return []

    def add_employee_feedback(self, data):
        """従業員AIへのフィードバックを保存"""
        if not self.supabase:
            return None
        try:
            if 'created_at' not in data:
                data['created_at'] = datetime.now().isoformat()
            result = self.supabase.table("employee_feedback").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error adding employee feedback: {e}")
            return None

    # 後放互換性のためのエイリアス
    def upsert_employee_persona(self, data):
        if 'id' in data and data['id']:
            return self.update_employee_persona(data['id'], data)
        return self.add_employee_persona(data)

    def save_employee_feedback(self, employee_id, product_id, ai_evaluation, user_feedback):
        data = {
            "employee_id": employee_id,
            "product_id": product_id,
            "ai_evaluation": ai_evaluation,
            "user_feedback": user_feedback
        }
        return self.add_employee_feedback(data)

