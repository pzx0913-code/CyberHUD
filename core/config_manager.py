import copy
import json
import os
import sys

DEFAULT_CONFIG = {
    "window": {
        "x": 80,
        "y": 80,
        "width": 330,
        "always_on_top": False,
        "locked": False,
        "opacity": 1.0,
        "magnetic_snap": True,
        "click_through": False,
        "bg_opacity": 0.85
    },
    "theme": {
        "primary_color": "#7DB4FF",      # Restrained Glacier-Blue accent
        "secondary_color": "#E55353",    # Danger red
        "warning_color": "#E6A23C",      # Warning amber
        "success_color": "#4EC28B",      # Online green
        "bg_color": "#111215",           # Frosted charcoal base
        "border_glow": False,
        "font_family": "Segoe UI Variable Display"
    },
    "hardware": {
        "refresh_interval_ms": 1000,
        "history_points": 36
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
            default_cfg = copy.deepcopy(DEFAULT_CONFIG)
            self.save_config(default_cfg)
            return default_cfg
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = copy.deepcopy(DEFAULT_CONFIG)
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in merged:
                        merged[k].update(v)
                    else:
                        merged[k] = v
                return merged
        except Exception as e:
            print(f"[ConfigManager] Error reading config, using defaults: {e}")
            return copy.deepcopy(DEFAULT_CONFIG)

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
