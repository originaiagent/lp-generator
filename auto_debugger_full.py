#!/usr/bin/env python3
"""
auto_debugger_full.py - 完全自動デバッグ
静的解析 + ランタイムチェック
"""

import os
import sys
import subprocess
import time
import requests
import signal
import re
import ast
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime

# 設定
MAX_RETRIES = 5
API_RETRIES = 3
STREAMLIT_PORT = 8501
STARTUP_WAIT = 8
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

UI_PAGES = {
    "main": "/",
    "product_list": "/product_list",
    "input": "/input", 
    "model": "/model",
    "structure": "/structure",
    "page_detail": "/page_detail",
    "output": "/output",
    "prompt": "/prompt",
    "settings": "/settings",
}

PAGE_FILES = {
    "main": "main.py",
    "product_list": "pages/01_product_list.py",
    "input": "pages/02_input.py",
    "model": "pages/03_model.py",
    "structure": "pages/04_structure.py",
    "page_detail": "pages/05_page_detail.py",
    "output": "pages/06_output.py",
    "prompt": "pages/07_prompt.py",
    "settings": "pages/08_settings.py",
}

# バックエンドクラスの既知メソッド
KNOWN_METHODS = {
    "SettingsManager": ["get_settings", "update_settings", "get_task_model", "set_task_model"],
    "DataStore": ["get", "set", "delete", "list_keys", "get_product", "save_product", "delete_product", "list_products"],
    "PromptManager": ["get_prompt", "save_prompt", "list_prompts"],
    "AIProvider": ["chat", "generate"],
    "FileParser": ["parse", "parse_file"],
    "ImageAnalyzer": ["analyze", "analyze_image"],
    "ChatManager": ["chat", "get_history"],
    "ModelGenerator": ["generate_model", "generate_optimized_prompt", "build_prompt", "get_attribute_options"],
    "PageGenerator": ["generate", "generate_page"],
    "OutputGenerator": ["generate", "generate_output"],
    "ImageGenerator": ["generate", "get_provider_name"],
    "PromptOptimizer": ["optimize"],
}

streamlit_process = None

def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def get_file_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def save_file(file_path: str, content: str):
    backup_path = file_path + ".bak"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            with open(backup_path, 'w') as bf:
                bf.write(f.read())
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def check_syntax(file_path: str) -> Tuple[bool, str]:
    """構文チェック"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, file_path, 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError Line {e.lineno}: {e.msg}"

def check_method_calls(file_path: str) -> Tuple[bool, str]:
    """存在しないメソッド呼び出しをチェック"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        issues = []
        
        # 既知の問題パターンを直接チェック
        problem_patterns = {
            r'settings_manager\.save_settings': "SettingsManager.save_settings() は存在しない。update_settings() を使用",
            r'\.save_settings\(': "save_settings() は存在しない可能性。update_settings() を確認",
            r'use_column_width': "use_column_width は非推奨。use_container_width を使用",
            r'st\.experimental_rerun': "st.experimental_rerun() は非推奨。st.rerun() を使用",
        }
        
        for pattern, msg in problem_patterns.items():
            if re.search(pattern, code):
                issues.append(msg)
        
        # 引数なし初期化チェック
        init_patterns = {
            r'AIProvider\(\s*\)': "AIProvider() には settings 引数が必要",
            r'ImageAnalyzer\(\s*\)': "ImageAnalyzer() には ai_provider, prompt_manager 引数が必要",
            r'ChatManager\(\s*\)': "ChatManager() には ai_provider, prompt_manager 引数が必要",
            r'ModelGenerator\(\s*\)': "ModelGenerator() には ai_provider, prompt_manager 引数が必要",
            r'PageGenerator\(\s*\)': "PageGenerator() には ai_provider, prompt_manager 引数が必要",
            r'OutputGenerator\(\s*\)': "OutputGenerator() には ai_provider, prompt_manager 引数が必要",
        }
        
        for pattern, msg in init_patterns.items():
            if re.search(pattern, code):
                issues.append(msg)
        
        if issues:
            return False, "\n".join(issues)
        
        return True, ""
    except Exception as e:
        return False, str(e)

def start_streamlit() -> subprocess.Popen:
    """Streamlitをバックグラウンドで起動"""
    global streamlit_process
    if streamlit_process:
        stop_streamlit()
    
    log("Streamlit起動中...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", "main.py", "--server.port", str(STREAMLIT_PORT), "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    time.sleep(STARTUP_WAIT)
    log("Streamlit起動完了")
    return streamlit_process

def stop_streamlit():
    """Streamlitを停止"""
    global streamlit_process
    if streamlit_process:
        try:
            os.killpg(os.getpgid(streamlit_process.pid), signal.SIGTERM)
            streamlit_process.wait(timeout=5)
        except:
            pass
        streamlit_process = None

def check_page_runtime(page_name: str, path: str) -> Tuple[bool, str]:
    """ページにアクセスしてランタイムエラーをチェック"""
    url = f"http://localhost:{STREAMLIT_PORT}{path}"
    
    try:
        response = requests.get(url, timeout=30)
        html = response.text
        
        error_patterns = [
            r'class="stException"',
            r'Traceback \(most recent call last\)',
            r'AttributeError:',
            r'TypeError:',
            r'NameError:',
            r'ImportError:',
            r'KeyError:',
            r'ValueError:',
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                error = extract_error_from_html(html)
                return False, error
        
        return True, ""
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)

def extract_error_from_html(html: str) -> str:
    """HTMLからエラーメッセージを抽出"""
    match = re.search(r'((?:Error|Exception|Traceback)[^\n]*(?:\n[^\n]*){0,15})', html, re.DOTALL | re.IGNORECASE)
    if match:
        error = re.sub(r'<[^>]+>', '', match.group(1))
        return error.strip()[:1500]
    return "Unknown error"

def call_claude(prompt: str) -> str:
    """Claude API呼び出し"""
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
            return response.json()["content"][0]["text"]
        except Exception as e:
            if attempt < API_RETRIES - 1:
                log(f"    APIリトライ... ({attempt + 1}/{API_RETRIES})")
                time.sleep(5)
            else:
                raise

def get_backend_summary() -> str:
    return """=== バックエンドモジュール ===

# 依存なし
settings_manager = SettingsManager()
data_store = DataStore()
prompt_manager = PromptManager()
file_parser = FileParser()

# settings必要
settings = settings_manager.get_settings()
ai_provider = AIProvider(settings)

# ai_provider, prompt_manager必要
model_generator = ModelGenerator(ai_provider, prompt_manager)

# 引数なしOK
image_gen = ImageGenerator()
optimizer = PromptOptimizer()

=== SettingsManagerメソッド ===
get_settings() - 設定取得
update_settings(dict) - 設定更新
※ save_settings() は存在しない！

=== Streamlit ===
use_container_width (not use_column_width)
st.rerun() (not st.experimental_rerun())
"""

def fix_file_with_claude(file_path: str, error: str) -> str:
    """Claudeに修正依頼"""
    content = get_file_content(file_path)
    
    prompt = f"""{get_backend_summary()}

=== ファイル: {file_path} ===
```python
{content}
```

=== エラー ===
{error}

=== 指示 ===
修正した完全なPythonコードを出力。```python で囲む。説明不要。
"""

    response = call_claude(prompt)
    
    if "```python" in response:
        return response.split("```python")[1].split("```")[0].strip()
    elif "```" in response:
        return response.split("```")[1].split("```")[0].strip()
    return response

def debug_file(file_path: str, need_restart: bool = False) -> Tuple[bool, bool]:
    """ファイルをデバッグ。戻り値: (成功, 再起動必要)"""
    
    for attempt in range(MAX_RETRIES):
        # 構文チェック
        ok, error = check_syntax(file_path)
        if not ok:
            log(f"  構文エラー (試行 {attempt + 1}/{MAX_RETRIES}): {error}")
            try:
                fixed = fix_file_with_claude(file_path, error)
                save_file(file_path, fixed)
                need_restart = True
            except Exception as e:
                log(f"    修正失敗: {e}")
                return False, need_restart
            continue
        
        # 静的解析
        ok, error = check_method_calls(file_path)
        if not ok:
            log(f"  静的解析エラー (試行 {attempt + 1}/{MAX_RETRIES}): {error}")
            try:
                fixed = fix_file_with_claude(file_path, error)
                save_file(file_path, fixed)
                need_restart = True
            except Exception as e:
                log(f"    修正失敗: {e}")
                return False, need_restart
            continue
        
        return True, need_restart
    
    return False, need_restart

def main():
    log("=" * 60)
    log("AUTO DEBUGGER FULL v2 - 静的解析 + ランタイム")
    log("=" * 60)
    
    # Phase 1: 静的解析で全ファイルチェック
    log("\n=== Phase 1: 静的解析 ===")
    need_restart = False
    
    for page_name, file_path in PAGE_FILES.items():
        if not os.path.exists(file_path):
            continue
        
        log(f"チェック中: {page_name}")
        ok, restart = debug_file(file_path)
        need_restart = need_restart or restart
        
        if ok:
            log(f"  ✅ OK")
        else:
            log(f"  ❌ 修正失敗")
    
    # Phase 2: ランタイムチェック
    log("\n=== Phase 2: ランタイムチェック ===")
    
    try:
        start_streamlit()
        
        results = {}
        for page_name, path in UI_PAGES.items():
            log(f"チェック中: {page_name}")
            ok, error = check_page_runtime(page_name, path)
            
            if ok:
                log(f"  ✅ OK")
                results[page_name] = True
            else:
                log(f"  ❌ エラー: {error[:100]}...")
                
                # 修正試行
                file_path = PAGE_FILES.get(page_name)
                if file_path and os.path.exists(file_path):
                    try:
                        fixed = fix_file_with_claude(file_path, error)
                        save_file(file_path, fixed)
                        log(f"    修正適用、再起動...")
                        stop_streamlit()
                        time.sleep(2)
                        start_streamlit()
                        
                        # 再チェック
                        ok2, _ = check_page_runtime(page_name, path)
                        results[page_name] = ok2
                        if ok2:
                            log(f"  ✅ 修正完了")
                        else:
                            log(f"  ❌ 修正失敗")
                    except Exception as e:
                        log(f"    修正失敗: {e}")
                        results[page_name] = False
                else:
                    results[page_name] = False
        
        # サマリー
        log("\n" + "=" * 60)
        log("サマリー")
        log("=" * 60)
        
        for name, result in results.items():
            status = "✅" if result else "❌"
            log(f"{status} {name}")
        
        success = sum(1 for v in results.values() if v)
        fail = sum(1 for v in results.values() if not v)
        log(f"\n成功: {success}, 失敗: {fail}")
        
        if fail == 0:
            log("\n🎉 全ページ正常動作！")
        
    finally:
        stop_streamlit()

if __name__ == "__main__":
    main()
