# 開発ルール

## Supabase連携
- 新しいカラムを使うコードを書く場合、必要なSQLも出力すること
- 例: ALTER TABLE テーブル名 ADD COLUMN カラム名 jsonb DEFAULT '{}';
- スキーマ変更が必要な場合は先に報告すること

## 共通モジュール
- settings_manager.py, ai_provider.py, prompt_manager.py, data_store.py は流用前提
- これらの構造を変更する場合は事前確認すること

## コーディングルール
- ハードコーディング禁止（価格、モデル名、API情報、設定値）
- 推測で進めず、不明点は確認すること
