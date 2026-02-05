import streamlit as st
from typing import List, Dict, Optional
import json

class ImageFactoryManager:
    """Image Factory用のプリセット・生成管理"""
    
    def __init__(self, data_store):
        self.data_store = data_store
        self.supabase = data_store.supabase
    
    # === プリセット取得 ===
    
    def get_reference_thumbnails(self, category: Optional[str] = None) -> List[Dict]:
        """参考サムネプリセット取得"""
        try:
            query = self.supabase.table('if_reference_thumbnails').select('*')
            if category and category != 'すべて':
                query = query.eq('category', category)
            result = query.order('created_at').execute()
            return result.data if result.data else []
        except Exception as e:
            st.error(f"サムネプリセット取得エラー: {str(e)}")
            return []
    
    def get_tonmana_presets(self, category: Optional[str] = None) -> List[Dict]:
        """トンマナプリセット取得"""
        try:
            query = self.supabase.table('if_tonmana_presets').select('*')
            if category and category != 'すべて':
                query = query.eq('category', category)
            result = query.order('created_at').execute()
            return result.data if result.data else []
        except Exception as e:
            st.error(f"トンマナプリセット取得エラー: {str(e)}")
            return []
    
    def get_thumbnail_by_id(self, thumbnail_id: str) -> Optional[Dict]:
        """特定のサムネプリセット取得"""
        try:
            result = self.supabase.table('if_reference_thumbnails')\
                .select('*')\
                .eq('id', thumbnail_id)\
                .single()\
                .execute()
            return result.data
        except Exception as e:
            st.error(f"サムネ取得エラー: {str(e)}")
            return None
    
    def get_tonmana_by_id(self, tonmana_id: str) -> Optional[Dict]:
        """特定のトンマナプリセット取得"""
        try:
            result = self.supabase.table('if_tonmana_presets')\
                .select('*')\
                .eq('id', tonmana_id)\
                .single()\
                .execute()
            return result.data
        except Exception as e:
            st.error(f"トンマナ取得エラー: {str(e)}")
            return None
    
    def get_categories(self, preset_type: str) -> List[str]:
        """カテゴリ一覧取得"""
        table_name = 'if_reference_thumbnails' if preset_type == 'thumbnail' else 'if_tonmana_presets'
        try:
            result = self.supabase.table(table_name).select('category').execute()
            if result.data:
                categories = list(set([item['category'] for item in result.data if item.get('category')]))
                return ['すべて'] + sorted(categories)
            return ['すべて']
        except Exception as e:
            st.error(f"カテゴリ取得エラー: {str(e)}")
            return ['すべて']
    
    # === 生成ジョブ管理 ===
    
    def create_generation_job(self, product_id: str, thumbnail_id: str, 
                             tonmana_id: str, copy_text: str, 
                             copy_source: str = 'manual') -> Optional[str]:
        """生成ジョブ作成"""
        try:
            result = self.supabase.table('if_generation_jobs').insert({
                'product_id': product_id,
                'thumbnail_id': thumbnail_id,
                'tonmana_id': tonmana_id,
                'copy_text': copy_text,
                'copy_source': copy_source,
                'status': 'pending',
                'parameters': {}
            }).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['id']
            return None
        except Exception as e:
            st.error(f"ジョブ作成エラー: {str(e)}")
            return None
    
    def update_job_status(self, job_id: str, status: str, error_message: str = None):
        """ジョブステータス更新"""
        try:
            update_data = {'status': status}
            if error_message:
                update_data['error_message'] = error_message
            
            self.supabase.table('if_generation_jobs')\
                .update(update_data)\
                .eq('id', job_id)\
                .execute()
        except Exception as e:
            st.error(f"ステータス更新エラー: {str(e)}")
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """ジョブ情報取得"""
        try:
            result = self.supabase.table('if_generation_jobs')\
                .select('*')\
                .eq('id', job_id)\
                .single()\
                .execute()
            return result.data
        except Exception as e:
            st.error(f"ジョブ取得エラー: {str(e)}")
            return None
    
    def get_jobs_by_product(self, product_id: str) -> List[Dict]:
        """製品別ジョブ一覧取得"""
        try:
            result = self.supabase.table('if_generation_jobs')\
                .select('*')\
                .eq('product_id', product_id)\
                .order('created_at', desc=True)\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            st.error(f"ジョブ一覧取得エラー: {str(e)}")
            return []
    
    # === 生成画像管理 ===
    
    def save_generated_image(self, job_id: str, product_id: str, 
                           image_url: str, storage_path: str,
                           pattern_index: int, metadata: Dict = None) -> Optional[str]:
        """生成画像保存"""
        try:
            result = self.supabase.table('if_generated_images').insert({
                'job_id': job_id,
                'product_id': product_id,
                'image_url': image_url,
                'storage_path': storage_path,
                'pattern_index': pattern_index,
                'is_selected': False,
                'metadata': metadata or {}
            }).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['id']
            return None
        except Exception as e:
            st.error(f"画像保存エラー: {str(e)}")
            return None
    
    def get_images_by_job(self, job_id: str) -> List[Dict]:
        """ジョブ別生成画像取得"""
        try:
            result = self.supabase.table('if_generated_images')\
                .select('*')\
                .eq('job_id', job_id)\
                .order('pattern_index')\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            st.error(f"画像取得エラー: {str(e)}")
            return []
    
    def select_image(self, image_id: str, job_id: str):
        """画像を選択状態にする（他は非選択に）"""
        try:
            # 同じジョブの他の画像を非選択に
            self.supabase.table('if_generated_images')\
                .update({'is_selected': False})\
                .eq('job_id', job_id)\
                .execute()
            
            # 指定画像を選択状態に
            self.supabase.table('if_generated_images')\
                .update({'is_selected': True})\
                .eq('id', image_id)\
                .execute()
        except Exception as e:
            st.error(f"画像選択エラー: {str(e)}")
