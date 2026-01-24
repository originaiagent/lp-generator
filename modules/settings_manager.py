import json
import os
from typing import Dict, Any

DEFAULT_SETTINGS = {
    "default_provider": "openai",
    "task_models": {
        "ai_chat": "gpt-4o",
        "code_generation": "gpt-4o",
        "text_analysis": "gpt-3.5-turbo"
    }
}

class SettingsManager:
    def __init__(self, settings_file: str = "data/settings.json"):
        self.settings_file = settings_file
        self._ensure_settings_file()
    
    def _ensure_settings_file(self):
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, 'w') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
    
    def get_settings(self) -> Dict[str, Any]:
        with open(self.settings_file, 'r') as f:
            return json.load(f)
    
    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        settings = self.get_settings()
        settings.update(updates)
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        return settings
    
    def get_task_model(self, task: str) -> str:
        settings = self.get_settings()
        return settings.get("task_models", {}).get(task, settings.get("default_provider", "gpt-4o"))
    
    def set_task_model(self, task: str, model: str) -> bool:
        settings = self.get_settings()
        if "task_models" not in settings:
            settings["task_models"] = {}
        settings["task_models"][task] = model
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        return True