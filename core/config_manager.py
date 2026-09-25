import json
import os
import sys

DEFAULT_CONFIG = {
    "window": {
        "x": 80,
        "y": 80,
        "width": 320,
        "always_on_top": True,
        "locked": False,
        "opacity": 0.92,
        "magnetic_snap": True,
        "click_through": False
    },
    "theme": {
        "primary_color": "#00F3FF",      # Cyber Cyan
        "secondary_color": "#FF0055",    # Cyber Magenta
        "warning_color": "#FFB800",      # Warning Amber
        "success_color": "#00FF88",      # Success Green
        "bg_color": "#0B0E17",           # Deep Space Black
        "border_glow": True,
        "font_family": "Consolas"
    },
    "hardware": {
        "refresh_interval_ms": 1000,
        "history_points": 30
    },
    "vps": {
        "enabled": True,
        "collapsed": False,
        "refresh_interval_s": 4,
        "type": "ssh",
        "host": "",
        "port": 22,
        "username": "root",
        "auth_type": "password",
        "password": "",
        "key_path": "",
        "http_url": "",
        "name": "VPS-NODE-01"
    },
    "pomodoro": {
        "enabled": True,
        "focus_min": 25,
        "short_break_min": 5,
        "long_break_min": 15,
        "auto_dock": True,
        "sound_alert": True
    }
}

class ConfigManager:
    def __init__(self, config_dir=None):
        if config_dir is None:
            if getattr(sys, 'frozen', False):
                config_dir = os.path.dirname(sys.executable)
            else:
                config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(config_dir, "config.json")
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in merged:
                        merged[k].update(v)
                    else:
                        merged[k] = v
                return merged
        except Exception as e:
            print(f"[ConfigManager] Error reading config, using defaults: {e}")
            return DEFAULT_CONFIG.copy()

    def save_config(self, new_config=None):
        if new_config:
            self.config = new_config
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, section, key, value):
        if section not in self.config or not isinstance(self.config[section], dict):
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
