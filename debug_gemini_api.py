
import os
import sys
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# モジュールパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 環境変数読み込み
load_dotenv()

def debug_gemini_vision():
    print("=== Debugging Gemini Vision API ===")
    
    # 1. APIキー確認
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment")
        return False
    else:
        print(f"✅ GOOGLE_API_KEY found ({api_key[:5]}...)")

    # 2. テスト用モジュールのインポート
    try:
        from modules.ai_provider import AIProvider
        print("✅ AIProvider imported")
    except ImportError as e:
        print(f"❌ Failed to import AIProvider: {e}")
        return False

    # 3. インスタンス化
    settings = {
        "llm_provider": "gemini",
        "llm_model": "gemini-2.0-flash",
        "task_models": {
            "image_analysis": "gemini-2.0-flash"
        }
    }
    provider = AIProvider(settings)
    print(f"✅ AIProvider initialized (Model: {settings['llm_model']})")

    # 4. テスト用画像の準備 (ダミーの小さな画像を作成)
    # 1x1 pixel red dot
    dummy_img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    dummy_img_data = base64.b64decode(dummy_img_b64)
    dummy_path = "debug_temp_image.png"
    
    with open(dummy_path, "wb") as f:
        f.write(dummy_img_data)
    print(f"✅ Dummy image created: {dummy_path}")

    # 5. ローカル画像分析テスト
    print("\n--- Testing Local Image Analysis ---")
    prompt = "Describe this image in one word."
    
    # AIProvider._analyze_image_gemini を直接呼ぶか、analyze_image経由かでテスト
    # analyze_imageはファイルパスを受け取る
    try:
        result = provider.analyze_image(dummy_path, prompt)
        print(f"Result (Local): {result}")
        if result and "error" not in result.lower():
            print("✅ Local Image Analysis Success")
        else:
            print("❌ Local Image Analysis Failed or Error returned")
    except Exception as e:
        print(f"❌ Local Image Analysis Exception: {e}")
        import traceback
        traceback.print_exc()

    # 6. リモート画像（URL）分析テスト
    print("\n--- Testing Remote Image Analysis ---")
    # Wikipediaの安定した画像URLを使用
    remote_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Synthese%2B.svg/200px-Synthese%2B.svg.png"
    
    try:
        result = provider.analyze_image(remote_url, prompt)
        print(f"Result (Remote): {result}")
        if result and "error" not in result.lower():
            print("✅ Remote Image Analysis Success")
        else:
            print("❌ Remote Image Analysis Failed or Error returned")
    except Exception as e:
        print(f"❌ Remote Image Analysis Exception: {e}")
        import traceback
        traceback.print_exc()

    # 7. 後始末
    if os.path.exists(dummy_path):
        os.remove(dummy_path)
        print("✅ Cleanup done")

if __name__ == "__main__":
    debug_gemini_vision()
