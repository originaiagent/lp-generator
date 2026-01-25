-- lp_products テーブルに不足している可能性のあるカラムを追加するSQL
-- SupabaseのSQL Editorで実行してください。

ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS structure jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS appeal_points jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS confirmed_elements jsonb DEFAULT '[]';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS selected_appeals jsonb DEFAULT '[]';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS page_details jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS page_contents jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS generated_lp_images jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS generated_versions jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS custom_prompts jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS competitor_analysis_v2 jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS lp_analyses jsonb DEFAULT '[]';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS lp_analyses_dict jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS product_sheet_organized text;
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS tone_manner jsonb DEFAULT '{}';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS product_image_urls jsonb DEFAULT '[]';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS reference_lp_image_urls jsonb DEFAULT '[]';
ALTER TABLE lp_products ADD COLUMN IF NOT EXISTS tone_manner_image_urls jsonb DEFAULT '[]';
