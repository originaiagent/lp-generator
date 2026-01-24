from typing import Dict, Any, List

class PageGenerator:
    def __init__(self, ai_provider, prompt_manager):
        self.ai_provider = ai_provider
        self.prompt_manager = prompt_manager

    def get_page_template(self, page_type: str) -> Dict[str, Any]:
        templates = {
            "first_view": {
                "items": [
                    {"type": "headline", "content": ""},
                    {"type": "subheadline", "content": ""},
                    {"type": "cta_button", "content": ""}
                ]
            },
            "features": {
                "items": [
                    {"type": "section_title", "content": ""},
                    {"type": "feature_list", "content": []},
                    {"type": "description", "content": ""}
                ]
            },
            "benefits": {
                "items": [
                    {"type": "benefit_title", "content": ""},
                    {"type": "benefit_points", "content": []},
                    {"type": "summary", "content": ""}
                ]
            }
        }
        
        return templates.get(page_type, {"items": []})

    def generate_page_details(self, structure: Dict, product_info: Dict, tone_analysis: Dict) -> List[Dict]:
        result = []
        
        if "pages" in structure:
            for page in structure["pages"]:
                page_detail = {
                    "id": page.get("id", ""),
                    "type": page.get("type", ""),
                    "title": page.get("title", ""),
                    "content": self.get_page_template(page.get("type", ""))
                }
                result.append(page_detail)
        
        return result