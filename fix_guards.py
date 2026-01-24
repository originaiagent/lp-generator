import os

guard_code = '''import streamlit as st
from modules.page_guard import require_product

# 製品選択チェック（製品一覧以外で必須）
require_product()

'''

pages_to_guard = [
    'pages/02_情報入力.py',
    'pages/03_モデル設定.py',
    'pages/04_全体構成.py',
    'pages/05_ページ詳細.py',
    'pages/06_出力.py',
]

for page in pages_to_guard:
    if os.path.exists(page):
        with open(page, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 既存のimport streamlit as stを削除して先頭にガード追加
        content = content.replace('import streamlit as st\n', '')
        new_content = guard_code + content
        
        with open(page, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ {page} 修正完了")

print("全ページ修正完了！")
