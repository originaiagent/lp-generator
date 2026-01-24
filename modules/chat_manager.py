from typing import Dict, Any, List

class ChatManager:
    def __init__(self, ai_provider, prompt_manager):
        self.ai_provider = ai_provider
        self.prompt_manager = prompt_manager

    def send_message(self, message: str, product_data: Dict, current_tab: str) -> Dict[str, Any]:
        try:
            context_summary = self.get_context_summary(product_data)
            prompt = f"Context: {context_summary}\nTab: {current_tab}\nUser: {message}"
            
            response = self.ai_provider.generate_response(prompt)
            
            return {
                "response": response,
                "auto_actions": []
            }
        except:
            return {
                "response": "申し訳ございませんが、エラーが発生しました。",
                "auto_actions": []
            }

    def get_context_summary(self, product_data: Dict) -> str:
        product_name = product_data.get("name", "未設定")
        return f"製品名: {product_name}の設定を編集中です。"

    def apply_auto_actions(self, product_data: Dict, actions: List[Dict]) -> Dict:
        return product_data