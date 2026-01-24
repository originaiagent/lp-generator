import sys

pages = [
    "pages/01_製品一覧.py",
    "pages/02_情報入力.py",
    "pages/03_モデル設定.py",
    "pages/04_全体構成.py",
    "pages/05_ページ詳細.py",
    "pages/06_出力.py",
    "pages/07_プロンプト管理.py",
    "pages/08_設定.py",
]

modules = [
    "modules/data_store.py",
    "modules/ai_provider.py",
    "modules/prompt_manager.py",
    "modules/settings_manager.py",
    "modules/page_guard.py",
    "modules/ai_sidebar.py",
]

print("🔍 構文チェック開始...\n")

errors = []

for f in modules + pages:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            code = file.read()
        compile(code, f, 'exec')
        print(f"✅ {f}")
    except FileNotFoundError:
        print(f"⚠️ {f} - ファイルなし")
    except SyntaxError as e:
        print(f"❌ {f} - 構文エラー: {e}")
        errors.append(f)

print(f"\n{'='*40}")
if errors:
    print(f"❌ {len(errors)}件のエラー")
else:
    print("✅ 全ファイル構文OK")
