import sys
import os

# Safe stream redirection for windowless pythonw execution
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt

from core.config_manager import ConfigManager
from core.local_monitor import LocalMonitorThread
from core.vps_monitor import VPSMonitorThread
from core.autostart import is_autostart_enabled, set_autostart
from ui.hud_window import CyberHUDWindow
from ui.pomo_window import CyberPomodoroWindow

def create_tray_icon_pixmap():
    """Generates a cyberpunk neon cyan HUD tray icon in-memory."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Dark cyber background circle
    painter.setBrush(QColor("#0E131F"))
    painter.setPen(QPen(QColor("#00F3FF"), 2.0))
    painter.drawEllipse(3, 3, 26, 26)

    # Cyber inner dot
    painter.setBrush(QColor("#00FF88"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(13, 13, 6, 6)

    painter.end()
    return pix

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 1. Config Manager
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_mgr = ConfigManager(base_dir)

    # 2. Main HUD Window (Desktop Layer & Click-Through)
    hud = CyberHUDWindow(config_mgr)
    hud.show()

    # 2.1 Cyber Pomodoro Companion Window (Docked below HUD)
    pomo = CyberPomodoroWindow(config_mgr, hud_window=hud)
    if config_mgr.get("pomodoro", {}).get("enabled", True):
        pomo.show()

    # 3. System Tray Icon
    tray = QSystemTrayIcon(app)
    tray_pix = create_tray_icon_pixmap()
    tray.setIcon(QIcon(tray_pix))
    tray.setToolTip("赛博桌面监视 HUD // CYBER DESKTOP HUD")

    # Connect Pomodoro session completion to tray notification
    def on_pomo_completed(phase):
        if phase == "focus":
            tray.showMessage("⚡ 专注时段已完成", "做得好！请放松休息 5 分钟。", QSystemTrayIcon.MessageIcon.Information, 5000)
        else:
            tray.showMessage("☕ 休息时段结束", "能量已充满，准备开始下一轮高效专注！", QSystemTrayIcon.MessageIcon.Information, 5000)

    pomo.session_completed.connect(on_pomo_completed)

    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #0E131F;
            color: #00F3FF;
            border: 1px solid #00F3FF;
            font-family: 'Consolas', monospace;
            padding: 4px;
            font-size: 13px;
        }
        QMenu::item {
            padding: 6px 22px;
        }
        QMenu::item:selected {
            background-color: #1A2640;
            color: #FFFFFF;
        }
    """)

    # Pomodoro Submenu
    pomo_menu = tray_menu.addMenu("🍅 专注番茄钟 (Pomodoro)")
    act_pomo_toggle = pomo_menu.addAction("▶ / ⏸ 开始/暂停当前计时")
    act_pomo_toggle.triggered.connect(pomo.toggle_timer)

    act_m_focus = pomo_menu.addAction(f"⚡ 切换到 {pomo.focus_min}M 专注模式")
    act_m_focus.triggered.connect(lambda: pomo.switch_mode(pomo.MODE_FOCUS))

    act_m_short = pomo_menu.addAction(f"☕ 切换到 {pomo.short_break_min}M 短休模式")
    act_m_short.triggered.connect(lambda: pomo.switch_mode(pomo.MODE_SHORT_BREAK))

    act_m_long = pomo_menu.addAction(f"🌿 切换到 {pomo.long_break_min}M 长休模式")
    act_m_long.triggered.connect(lambda: pomo.switch_mode(pomo.MODE_LONG_BREAK))

    act_pomo_reset = pomo_menu.addAction("↺ 重置当前计时")
    act_pomo_reset.triggered.connect(pomo.reset_timer)

    pomo_menu.addSeparator()
    act_pomo_dock = pomo_menu.addAction("📌 重新吸附在 HUD 下方")
    act_pomo_dock.triggered.connect(pomo.sync_position_with_hud)

    act_pomo_vis = pomo_menu.addAction("👁 显示/隐藏番茄钟浮窗")
    act_pomo_vis.triggered.connect(lambda: pomo.setVisible(not pomo.isVisible()))

    tray_menu.addSeparator()

    # Drag mode action
    act_drag = tray_menu.addAction("🎯 调整窗口位置 (临时允许拖动 15秒)")
    act_drag.triggered.connect(lambda: hud.enter_drag_mode(15))

    # Background Opacity Menu (Text & lines stay 100% solid)
    op_menu = tray_menu.addMenu("🌓 底板透明度 (文字始终高亮清晰)")
    opacity_presets = [
        (0.90, "90% (深色微透)"),
        (0.65, "65% (半透磨砂，推荐)"),
        (0.45, "45% (通透玻璃)"),
        (0.25, "25% (极透微影)"),
        (0.00, "0% (全透纯HUD，仅留霓虹边框与字)")
    ]
    for val, text in opacity_presets:
        act_op = op_menu.addAction(text)
        act_op.triggered.connect(lambda checked, v=val: (hud.set_bg_opacity(v), pomo.update()))


    # Autostart toggle action
    act_autostart = tray_menu.addAction("🚀 开机登录自动启动")
    act_autostart.setCheckable(True)
    act_autostart.setChecked(is_autostart_enabled())
    act_autostart.triggered.connect(lambda checked: set_autostart(checked))

    # Pin to bottom
    act_bottom = tray_menu.addAction("📌 强制贴回桌面底层")
    act_bottom.triggered.connect(lambda: (hud.send_to_bottom(), pomo.send_to_bottom()))

    # VPS Settings
    act_cfg = tray_menu.addAction("⚙️ 配置 VPS 探针参数...")
    act_cfg.triggered.connect(hud.open_vps_config)

    tray_menu.addSeparator()
    act_quit = tray_menu.addAction("❌ 退出 HUD")
    act_quit.triggered.connect(app.quit)

    tray.setContextMenu(tray_menu)
    tray.show()

    # 4. Local Hardware Monitor Thread
    local_thread = LocalMonitorThread(
        interval_ms=config_mgr.get("hardware", {}).get("refresh_interval_ms", 1000)
    )
    local_thread.metrics_updated.connect(hud.update_local_metrics)
    local_thread.start()

    # 5. VPS Remote Monitor Thread
    vps_thread = VPSMonitorThread(config_mgr)
    vps_thread.vps_metrics_updated.connect(hud.update_vps_metrics)
    vps_thread.start()

    def cleanup():
        local_thread.stop()
        vps_thread.stop()
        pomo.timer.stop()
        pomo.flash_timer.stop()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
