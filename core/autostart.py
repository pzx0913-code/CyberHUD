import os
import sys

def get_startup_shortcut_path():
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        appdata = os.path.expanduser(r"~\AppData\Roaming")
    startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.join(startup_dir, "Cyber HUD.lnk")

def is_autostart_enabled():
    path = get_startup_shortcut_path()
    return os.path.exists(path)

def set_autostart(enable: bool):
    shortcut_path = get_startup_shortcut_path()
    if enable:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            target_path = sys.executable
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            target_path = os.path.join(base_dir, "start_hud_silent.vbs")
        
        # Create VBS script to create startup shortcut cleanly
        vbs_cmd = f'''Set WshShell = CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut("{shortcut_path}")
oShortcut.TargetPath = "{target_path}"
oShortcut.WorkingDirectory = "{base_dir}"
oShortcut.Description = "赛博风桌面硬件监视悬浮窗 - 开机登录自启"
oShortcut.Save
'''
        temp_vbs = os.path.join(base_dir, "_temp_startup.vbs")
        try:
            with open(temp_vbs, "w", encoding="gbk") as f:
                f.write(vbs_cmd)
            os.system(f'cscript //nologo "{temp_vbs}"')
        finally:
            if os.path.exists(temp_vbs):
                try:
                    os.remove(temp_vbs)
                except Exception:
                    pass
        return os.path.exists(shortcut_path)
    else:
        if os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
            except Exception:
                pass
        return not os.path.exists(shortcut_path)
