import json
import os
from datetime import datetime

class UsageTracker:
    """API使用量とコストを追跡"""
    
    def __init__(self):
        self.log_path = "data/usage_log.json"
        self.settings_path = "data/settings.json"
        self._ensure_files()
    
    def _ensure_files(self):
        """ファイルが存在しない場合は作成"""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
    
    def get_pricing(self):
        """料金設定を取得（$/100万トークン）"""
        pricing_path = "data/pricing.json"
        try:
            with open(pricing_path, "r", encoding="utf-8") as f:
                pricing_data = json.load(f)
            return pricing_data.get("text_generation", self._default_pricing())
        except:
            return self._default_pricing()
    
    def get_image_pricing(self):
        """画像生成料金を取得（$/枚）"""
        pricing_path = "data/pricing.json"
        try:
            with open(pricing_path, "r", encoding="utf-8") as f:
                pricing_data = json.load(f)
            return pricing_data.get("image_generation", {})
        except:
            return {}
    
    def _default_pricing(self):
        """デフォルト料金（設定がない場合）"""
        return {
            "claude": {"input": 3.0, "output": 15.0},
            "gpt": {"input": 2.5, "output": 10.0},
            "gemini": {"input": 0.075, "output": 0.3}
        }
    
    def calculate_cost(self, provider, input_tokens, output_tokens, model=None):
        """コストを計算（円）"""
        text_pricing = self.get_pricing()
        image_pricing = self.get_image_pricing()
        provider_key = self._normalize_provider(provider)
        usd_to_jpy = self._get_exchange_rate()
        
        # まずモデル名で画像生成料金を探す（画像生成モデルはプロバイダー関係なくモデル名で管理）
        if model and model in image_pricing:
            rates = image_pricing[model]
            input_cost = (input_tokens / 1_000_000) * rates.get("input", 0) * usd_to_jpy
            output_cost = (output_tokens / 1_000_000) * rates.get("output", 0) * usd_to_jpy
            return round(input_cost + output_cost, 2)
        
        # テキスト生成料金を探す
        if provider_key not in text_pricing:
            return 0.0
        
        provider_pricing = text_pricing[provider_key]
        
        # モデル指定があればそのモデルの料金を使用
        if model and model in provider_pricing:
            rates = provider_pricing[model]
        else:
            # デフォルト：最初のモデルの料金を使用
            first_model = list(provider_pricing.keys())[0] if provider_pricing else None
            rates = provider_pricing.get(first_model, {"input": 0, "output": 0})
        
        input_cost = (input_tokens / 1_000_000) * rates.get("input", 0) * usd_to_jpy
        output_cost = (output_tokens / 1_000_000) * rates.get("output", 0) * usd_to_jpy
        
        return round(input_cost + output_cost, 2)
    
    def calculate_image_cost(self, model, size="1024x1024", quality="standard"):
        """画像生成コストを計算（円）"""
        pricing = self.get_image_pricing()
        usd_to_jpy = self._get_exchange_rate()
        
        # モデル名を正規化
        model_key = model.lower()
        if "dall-e-3" in model_key or "dalle-3" in model_key:
            model_key = "dall-e-3"
        elif "dall-e-2" in model_key or "dalle-2" in model_key:
            model_key = "dall-e-2"
        elif "imagen" in model_key:
            model_key = "imagen-3"
        
        if model_key not in pricing:
            return 0.0
        
        model_pricing = pricing[model_key]
        
        # サイズとクオリティで料金を決定
        size_key = size
        if quality == "hd":
            size_key = f"{size}_hd"
        
        rate = model_pricing.get(size_key, model_pricing.get("default", 0))
        return round(rate * usd_to_jpy, 2)
    
    def record_image_generation(self, model, size="1024x1024", quality="standard"):
        """画像生成を記録"""
        today = datetime.now().strftime("%Y-%m-%d")
        cost = self.calculate_image_cost(model, size, quality)
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except:
            log = {}
        
        if today not in log:
            log[today] = {
                "total": {"input_tokens": 0, "output_tokens": 0, "cost_jpy": 0},
                "by_function": {},
                "by_provider": {},
                "image_generation": {"count": 0, "cost_jpy": 0}
            }
        
        if "image_generation" not in log[today]:
            log[today]["image_generation"] = {"count": 0, "cost_jpy": 0}
        
        log[today]["image_generation"]["count"] += 1
        log[today]["image_generation"]["cost_jpy"] = round(
            log[today]["image_generation"]["cost_jpy"] + cost, 2
        )
        log[today]["total"]["cost_jpy"] = round(
            log[today]["total"]["cost_jpy"] + cost, 2
        )
        
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        
        return {"model": model, "size": size, "cost_jpy": cost}
    
    def _get_exchange_rate(self):
        """為替レートを取得"""
        pricing_path = "data/pricing.json"
        try:
            with open(pricing_path, "r", encoding="utf-8") as f:
                pricing_data = json.load(f)
            return pricing_data.get("usd_to_jpy", 150)
        except:
            return 150
    
    def _normalize_provider(self, provider):
        """プロバイダー名を正規化"""
        provider = provider.lower()
        if "claude" in provider or "anthropic" in provider:
            return "claude"
        elif "gpt" in provider or "openai" in provider:
            return "gpt"
        elif "gemini" in provider or "google" in provider:
            return "gemini"
        return provider
    
    def record_usage(self, provider, input_tokens, output_tokens, function_name="unknown", model=None):
        """使用量を記録"""
        today = datetime.now().strftime("%Y-%m-%d")
        cost = self.calculate_cost(provider, input_tokens, output_tokens, model)
        
        # 画像生成モデルかどうか判定
        image_pricing = self.get_image_pricing()
        is_image_gen = model and model in image_pricing
        
        # ログを読み込み
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except:
            log = {}
        
        # 今日のエントリがなければ作成
        if today not in log:
            log[today] = {
                "total": {"input_tokens": 0, "output_tokens": 0, "cost_jpy": 0},
                "by_function": {},
                "by_provider": {},
                "image_generation": {"count": 0, "cost_jpy": 0}
            }
        
        # image_generationがなければ追加
        if "image_generation" not in log[today]:
            log[today]["image_generation"] = {"count": 0, "cost_jpy": 0}
        
        # 画像生成の場合は枚数もカウント
        if is_image_gen:
            log[today]["image_generation"]["count"] += 1
            log[today]["image_generation"]["cost_jpy"] = round(
                log[today]["image_generation"]["cost_jpy"] + cost, 2
            )
        
        # トータル更新
        log[today]["total"]["input_tokens"] += input_tokens
        log[today]["total"]["output_tokens"] += output_tokens
        log[today]["total"]["cost_jpy"] = round(log[today]["total"]["cost_jpy"] + cost, 2)
        
        # 機能別更新
        if function_name not in log[today]["by_function"]:
            log[today]["by_function"][function_name] = {"input": 0, "output": 0, "cost": 0}
        log[today]["by_function"][function_name]["input"] += input_tokens
        log[today]["by_function"][function_name]["output"] += output_tokens
        log[today]["by_function"][function_name]["cost"] = round(
            log[today]["by_function"][function_name]["cost"] + cost, 2
        )
        
        # プロバイダー別更新
        provider_key = self._normalize_provider(provider)
        if provider_key not in log[today]["by_provider"]:
            log[today]["by_provider"][provider_key] = {"input": 0, "output": 0, "cost": 0}
        log[today]["by_provider"][provider_key]["input"] += input_tokens
        log[today]["by_provider"][provider_key]["output"] += output_tokens
        log[today]["by_provider"][provider_key]["cost"] = round(
            log[today]["by_provider"][provider_key]["cost"] + cost, 2
        )
        
        # 保存
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        
        return {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_jpy": cost}
    
    def get_today_usage(self):
        """今日の使用量を取得"""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
            return log.get(today, {"total": {"input_tokens": 0, "output_tokens": 0, "cost_jpy": 0}})
        except:
            return {"total": {"input_tokens": 0, "output_tokens": 0, "cost_jpy": 0}}
    
    def get_usage_by_date(self, date_str):
        """特定日の使用量を取得"""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
            return log.get(date_str, None)
        except:
            return None
    
    def get_last_call_usage(self):
        """最後のAPI呼び出しの使用量（session_stateから取得）"""
        import streamlit as st
        return st.session_state.get('last_api_usage', None)
