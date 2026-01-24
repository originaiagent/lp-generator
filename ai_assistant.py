#!/usr/bin/env python3
"""
ai_assistant.py - 自然言語でコード修正を指示

使い方:
  python ai_assistant.py "画像生成がおかしい、確認して"
  python ai_assistant.py  # 対話モード
"""

import os
import sys
import json
import glob
import requests
import subprocess
from datetime import datetime

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# プロジェクト構成
PROJECT_FILES = {
    "pages": "pages/*.py",
    "modules": "modules/*.py",
    "config": "data/*.json",
    "main": "main.py",
}

def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def get_project_files() -> dict:
    """プロジェクトファイルを収集"""
    files = {}
    for category, pattern in PROJECT_FILES.items():
        for filepath in glob.glob(pattern):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    files[filepath] = f.read()
            except:
                pass
    return files

def get_file_summary() -> str:
    """ファイル構成のサマリー"""
    summary = "=== プロジェクト構成 ===\n"
    for category, pattern in PROJECT_FILES.items():
        files = glob.glob(pattern)
        if files:
            summary += f"\n{category}:\n"
            for f in files:
                summary += f"  - {f}\n"
    return summary

def get_relevant_files(query: str) -> dict:
    """クエリに関連するファイルを取得"""
    files = {}
    query_lower = query.lower()
    
    # キーワードとファイルの対応
    keywords_to_files = {
        "画像": ["modules/image_generator.py", "modules/prompt_optimizer.py", "pages/03_model.py"],
        "image": ["modules/image_generator.py", "modules/prompt_optimizer.py", "pages/03_model.py"],
        "モデル": ["modules/model_generator.py", "modules/model_fetcher.py", "pages/03_model.py", "data/models.json"],
        "model": ["modules/model_generator.py", "modules/model_fetcher.py", "pages/03_model.py", "data/models.json"],
        "設定": ["modules/settings_manager.py", "pages/08_settings.py", "data/settings.json"],
        "setting": ["modules/settings_manager.py", "pages/08_settings.py", "data/settings.json"],
        "プロンプト": ["modules/prompt_optimizer.py", "modules/prompt_manager.py"],
        "prompt": ["modules/prompt_optimizer.py", "modules/prompt_manager.py"],
        "llm": ["modules/ai_provider.py", "modules/prompt_optimizer.py", "pages/08_settings.py"],
        "gemini": ["modules/image_generator.py", "modules/model_fetcher.py", "modules/prompt_optimizer.py"],
        "openai": ["modules/image_generator.py", "modules/ai_provider.py"],
        "dall-e": ["modules/image_generator.py"],
        "input": ["pages/02_input.py", "modules/file_parser.py"],
        "output": ["pages/06_output.py", "modules/output_generator.py"],
        "structure": ["pages/04_structure.py", "modules/page_generator.py"],
        "page": ["pages/05_page_detail.py", "modules/page_generator.py"],
    }
    
    # 関連ファイルを収集
    relevant = set()
    for keyword, file_list in keywords_to_files.items():
        if keyword in query_lower:
            relevant.update(file_list)
    
    # デフォルト（何も一致しない場合）
    if not relevant:
        relevant = {"main.py", "pages/08_settings.py"}
    
    # ファイル内容を取得
    for filepath in relevant:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    files[filepath] = f.read()
            except:
                pass
    
    return files

def call_claude(system: str, user: str) -> str:
    """Claude APIを呼び出し"""
    if not ANTHROPIC_API_KEY:
        raise Exception("ANTHROPIC_API_KEY not set")
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8000,
        "system": system,
        "messages": [{"role": "user", "content": user}]
    }
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data,
        timeout=120
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]

def parse_response(response: str) -> dict:
    """レスポンスからファイル修正を抽出"""
    result = {
        "message": response,
        "files_to_update": {}
    }
    
    # ```python:filepath の形式を探す
    import re
    pattern = r'```(?:python)?:([^\n]+)\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL)
    
    for filepath, content in matches:
        filepath = filepath.strip()
        result["files_to_update"][filepath] = content.strip()
    
    # 代替形式: === filepath === の形式
    pattern2 = r'===\s*([^\n=]+\.py)\s*===\n```(?:python)?\n(.*?)```'
    matches2 = re.findall(pattern2, response, re.DOTALL)
    
    for filepath, content in matches2:
        filepath = filepath.strip()
        result["files_to_update"][filepath] = content.strip()
    
    return result

def apply_updates(files_to_update: dict) -> list:
    """ファイル更新を適用"""
    updated = []
    for filepath, content in files_to_update.items():
        try:
            # バックアップ
            if os.path.exists(filepath):
                backup = filepath + ".bak"
                with open(filepath, 'r') as f:
                    with open(backup, 'w') as bf:
                        bf.write(f.read())
            
            # ディレクトリ作成
            os.makedirs(os.path.dirname(filepath), exist_ok=True) if '/' in filepath else None
            
            # 更新
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            updated.append(filepath)
        except Exception as e:
            log(f"更新失敗 {filepath}: {e}")
    
    return updated

def run_debugger():
    """auto_debugger_full.pyを実行"""
    log("デバッグ実行中...")
    result = subprocess.run(
        ["python", "auto_debugger_full.py"],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

def process_query(query: str):
    """クエリを処理"""
    log(f"処理中: {query}")
    
    # 関連ファイルを取得
    files = get_relevant_files(query)
    log(f"関連ファイル: {', '.join(files.keys())}")
    
    # コンテキスト構築
    file_context = ""
    for filepath, content in files.items():
        file_context += f"\n=== {filepath} ===\n```python\n{content}\n```\n"
    
    system_prompt = """あなたはStreamlitプロジェクトの開発アシスタントです。
ユーザーの指示に従って、コードを確認・修正してください。

【重要ルール】
1. 問題を分析し、原因を特定する
2. 修正が必要な場合、完全なファイル内容を出力する
3. 修正ファイルは ```python:filepath の形式で出力する
4. 例: ```python:modules/image_generator.py
5. 説明は簡潔に、日本語で
6. 複数ファイルの修正が必要な場合は全て出力する

【プロジェクト構成】
- pages/*.py: StreamlitのUIページ
- modules/*.py: バックエンドモジュール
- data/*.json: 設定ファイル
- main.py: エントリーポイント"""

    user_message = f"""【ユーザーの指示】
{query}

【関連ファイル】
{file_context}

上記を確認して、必要な対応をしてください。"""

    # Claude呼び出し
    log("Claude APIに問い合わせ中...")
    response = call_claude(system_prompt, user_message)
    
    # レスポンス解析
    result = parse_response(response)
    
    # メッセージ表示
    print("\n" + "=" * 60)
    print("【回答】")
    print("=" * 60)
    print(result["message"])
    
    # ファイル更新
    if result["files_to_update"]:
        print("\n" + "=" * 60)
        print("【ファイル更新】")
        print("=" * 60)
        
        for filepath in result["files_to_update"]:
            print(f"  - {filepath}")
        
        confirm = input("\n適用しますか？ (y/n): ").strip().lower()
        if confirm == 'y':
            updated = apply_updates(result["files_to_update"])
            log(f"更新完了: {', '.join(updated)}")
            
            # デバッグ実行
            run_debug = input("デバッグを実行しますか？ (y/n): ").strip().lower()
            if run_debug == 'y':
                output = run_debugger()
                print(output)
    
    return result

def interactive_mode():
    """対話モード"""
    print("=" * 60)
    print("AI Assistant - 自然言語でコード修正")
    print("=" * 60)
    print("指示を入力してください。終了は 'exit' または Ctrl+C")
    print()
    
    while True:
        try:
            query = input("あなた: ").strip()
            if not query:
                continue
            if query.lower() in ['exit', 'quit', '終了']:
                print("終了します")
                break
            
            process_query(query)
            print()
        except KeyboardInterrupt:
            print("\n終了します")
            break
        except Exception as e:
            log(f"エラー: {e}")

def main():
    if len(sys.argv) > 1:
        # 引数ありの場合、直接処理
        query = " ".join(sys.argv[1:])
        process_query(query)
    else:
        # 対話モード
        interactive_mode()

if __name__ == "__main__":
    main()
