#!/usr/bin/env python3
"""
auto_debugger.py - 全自動デバッグスクリプト
放置するだけで全ページが動くまで修正を繰り返す
"""

import os
import sys
import json
import importlib.util
import traceback
import requests
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# 設定
MAX_RETRIES = 5
API_RETRIES = 3
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

UI_PAGES = {
    "product_list": "pages/01_製品一覧.py",
    "input": "pages/02_情報入力.py",
    "model": "pages/03_モデル設定.py",
    "structure": "pages/04_全体構成.py",
    "page_detail": "pages/05_ページ詳細.py",
    "output": "pages/06_出力.py",
    "prompt": "pages/07_プロンプト管理.py",
    "settings": "pages/08_設定.py",
}

BACKEND_MODULES = [
    "modules/settings_manager.py",
    "modules/data_store.py",
    "modules/prompt_manager.py",
    "modules/ai_provider.py",
    "modules/file_parser.py",
    "modules/image_analyzer.py",
    "modules/chat_manager.py",
    "modules/model_generator.py",
    "modules/page_generator.py",
    "modules/output_generator.py",
    "modules/image_generator.py",
    "modules/prompt_optimizer.py",
]

def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def check_syntax(file_path: str) -> Tuple[bool, str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, file_path, 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def check_import(file_path: str) -> Tuple[bool, str]:
    """インポートテスト（Streamlitをモック）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 基本的な構文チェックのみ（Streamlit依存を避ける）
        compile(code, file_path, 'exec')
        
        # 危険なパターンをチェック
        issues = []
        
        # 引数なし初期化チェック
        patterns = [
            ("AIProvider()", "AIProvider requires 'settings' argument"),
            ("ImageAnalyzer()", "ImageAnalyzer requires 'ai_provider, prompt_manager' arguments"),
            ("ModelGenerator()", "ModelGenerator requires 'ai_provider, prompt_manager' arguments"),
            ("PageGenerator()", "PageGenerator requires 'ai_provider, prompt_manager' arguments"),
            ("OutputGenerator()", "OutputGenerator requires 'ai_provider, prompt_manager' arguments"),
            ("ChatManager()", "ChatManager requires 'ai_provider, prompt_manager' arguments"),
        ]
        
        for pattern, msg in patterns:
            if pattern in code:
                issues.append(msg)
        
        # 非推奨API
        if "use_column_width" in code:
            issues.append("use_column_width is deprecated, use width='stretch' or width='content'")
        if "use_container_width" in code:
            issues.append("use_container_width is deprecated, use width='stretch' or width='content'")
        
        if issues:
            return False, "\n".join(issues)
        
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"

def get_file_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def save_file(file_path: str, content: str):
    # バックアップ
    backup_path = file_path + ".bak"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            with open(backup_path, 'w') as bf:
                bf.write(f.read())
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def call_claude(prompt: str) -> str:
    """Claude APIを呼び出し（リトライ付き）"""
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
        "messages": [{"role": "user", "content": prompt}]
    }
    
    for attempt in range(API_RETRIES):
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]
        except requests.exceptions.HTTPError as e:
            if attempt < API_RETRIES - 1:
                log(f"    API エラー、リトライ中... ({attempt + 1}/{API_RETRIES})")
                time.sleep(5)
            else:
                raise
        except Exception as e:
            if attempt < API_RETRIES - 1:
                log(f"    エラー: {e}、リトライ中...")
                time.sleep(5)
            else:
                raise

def get_backend_summary() -> str:
    """バックエンドモジュールのサマリー"""
    summary = """=== バックエンドモジュール初期化方法 ===

# 依存なし
settings_manager = SettingsManager()
data_store = DataStore()
prompt_manager = PromptManager()
file_parser = FileParser()

# settings が必要
settings = settings_manager.get_settings()
ai_provider = AIProvider(settings)

# ai_provider と prompt_manager が必要
image_analyzer = ImageAnalyzer(ai_provider, prompt_manager)
chat_manager = ChatManager(ai_provider, prompt_manager)
model_generator = ModelGenerator(ai_provider, prompt_manager)
page_generator = PageGenerator(ai_provider, prompt_manager)
output_generator = OutputGenerator(ai_provider, prompt_manager)

# 画像生成
from modules.image_generator import ImageGenerator
image_gen = ImageGenerator()  # 引数なしOK

# プロンプト最適化
from modules.prompt_optimizer import PromptOptimizer
optimizer = PromptOptimizer()  # 引数なしOK

=== Streamlit注意点 ===
- use_column_width/use_container_width → width='stretch' or width='content'
- st.experimental_rerun() → st.rerun()
- キーは一意にする: key=f'unique_{index}'
"""
    return summary

def fix_file_with_claude(file_path: str, error: str) -> str:
    """Claudeにファイル修正を依頼"""
    content = get_file_content(file_path)
    backend_summary = get_backend_summary()
    
    prompt = f"""以下のStreamlit UIファイルにエラーがあります。修正してください。

{backend_summary}

=== 対象ファイル: {file_path} ===
```python
{content}
```

=== エラー ===
{error}

=== 指示 ===
1. エラーを修正した完全なPythonコードを出力
2. コードのみを出力、説明不要
3. ```python と ``` で囲む
4. バックエンドの正しい初期化方法を使用
5. Streamlit最新APIを使用
"""

    response = call_claude(prompt)
    
    if "```python" in response:
        code = response.split("```python")[1].split("```")[0].strip()
        return code
    elif "```" in response:
        code = response.split("```")[1].split("```")[0].strip()
        return code
    
    return response

def debug_file(file_path: str) -> bool:
    """1ファイルをデバッグ"""
    log(f"チェック中: {file_path}")
    
    for attempt in range(MAX_RETRIES):
        # 構文チェック
        ok, error = check_syntax(file_path)
        if not ok:
            log(f"  構文エラー (試行 {attempt + 1}/{MAX_RETRIES})")
            log(f"    {error}")
            
            try:
                fixed_code = fix_file_with_claude(file_path, error)
                save_file(file_path, fixed_code)
            except Exception as e:
                log(f"    修正失敗: {e}")
                return False
            continue
        
        # パターンチェック
        ok, error = check_import(file_path)
        if not ok:
            log(f"  パターンエラー (試行 {attempt + 1}/{MAX_RETRIES})")
            log(f"    {error}")
            
            try:
                fixed_code = fix_file_with_claude(file_path, error)
                save_file(file_path, fixed_code)
            except Exception as e:
                log(f"    修正失敗: {e}")
                return False
            continue
        
        log(f"  ✅ OK")
        return True
    
    log(f"  ❌ {MAX_RETRIES}回試行しても修正できず")
    return False

def main():
    log("=" * 60)
    log("AUTO DEBUGGER 開始")
    log("=" * 60)
    
    # バックエンドチェック
    log("\n=== バックエンドモジュール ===")
    for module_path in BACKEND_MODULES:
        if os.path.exists(module_path):
            ok, error = check_syntax(module_path)
            if ok:
                log(f"✅ {module_path}")
            else:
                log(f"❌ {module_path}: {error}")
    
    # UIページデバッグ
    log("\n=== UIページ デバッグ ===")
    results = {}
    
    for name, path in UI_PAGES.items():
        if os.path.exists(path):
            success = debug_file(path)
            results[name] = success
        else:
            log(f"⏭️ {name}: ファイルなし")
            results[name] = None
    
    # サマリー
    log("\n" + "=" * 60)
    log("サマリー")
    log("=" * 60)
    
    success_count = sum(1 for v in results.values() if v is True)
    fail_count = sum(1 for v in results.values() if v is False)
    
    for name, result in results.items():
        status = "✅" if result is True else "❌" if result is False else "⏭️"
        log(f"{status} {name}")
    
    log(f"\n成功: {success_count}, 失敗: {fail_count}")
    
    if fail_count == 0:
        log("\n🎉 全ページ修正完了！")
        log("streamlit run main.py で確認してください")
    else:
        log(f"\n⚠️ {fail_count}ファイルは手動確認が必要")

if __name__ == "__main__":
    main()
