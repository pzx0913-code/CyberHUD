import sys
import os

# Safe stream redirection for windowless pythonw execution
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QPointF

from core.config_manager import ConfigManager
from core.local_monitor import LocalMonitorThread
from core.vps_monitor import VPSMonitorThread
from core.autostart import is_autostart_enabled, set_autostart
from ui.cyber_painter import Theme
from ui.hud_window import CyberHUDWindow
from ui.pomo_window import CyberPomodoroWindow


def create_tray_icon_pixmap():
    """Generate a crisp flat dark-graphite tray icon with an Ice Blue status center."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.setBrush(QColor(Theme.BG_PANEL))
    painter.setPen(QPen(QColor(237, 237, 239, 70), 1.5))
    painter.drawEllipse(3, 3, 26, 26)

    painter.setBrush(QColor(Theme.ACCENT))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPointF(16.0, 16.0), 3.5, 3.5)

    painter.end()
    return pix


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 1. Config Manager
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_mgr = ConfigManager(base_dir)

    # 2. Main HUD Window (Desktop Layer & Click-Through)
    hud = CyberHUDWindow(config_mgr)
    hud.show()

    # 2.1 Focus Chronometer Companion Window (Docked below HUD)
    pomo = CyberPomodoroWindow(config_mgr, hud_window=hud)
    if config_mgr.get("pomodoro", {}).get("enabled", True):
        pomo.show()

    # 3. System Tray Icon
    tray = QSystemTrayIcon(app)
    tray_pix = create_tray_icon_pixmap()
    tray.setIcon(QIcon(tray_pix))
    tray.setToolTip("CyberHUD 桌面遥测监控")

    def on_pomo_completed(phase):
        if phase == "focus":
            tray.showMessage(
                "专注时段已完成",
                "可以放松休息片刻，准备下一轮专注。",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
        else:
            tray.showMessage(
                "休息时段已结束",
                "准备开始下一轮专注。",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )

    pomo.session_completed.connect(on_pomo_completed)

    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #141518;
            color: #F4F4F6;
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 8px;
            font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
            padding: 4px;
            font-size: 13px;
        }
        QMenu::item {
            padding: 7px 24px 7px 12px;
            border-radius: 5px;
        }
        QMenu::item:selected {
            background-color: #242730;
            color: #F4F4F6;
        }
        QMenu::separator {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 4px 8px;
        }
    """)

    # Pomodoro Submenu
    pomo_menu = tray_menu.addMenu("专注番茄钟")
    act_pomo_toggle = pomo_menu.addAction("开始 / 暂停计时")
    act_pomo_toggle.triggered.connect(pomo.toggle_timer)

    act_m_focus = pomo_menu.addAction(f"切换至 {pomo.focus_min} 分钟专注")
    act_m_focus.triggered.connect(lambda: pomo.switch_mode(pomo.MODE_FOCUS))

    act_m_short = pomo_menu.addAction(f"切换至 {pomo.short_break_min} 分钟短休")
    act_m_short.triggered.connect(lambda: pomo.switch_mode(pomo.MODE_SHORT_BREAK))

    act_m_long = pomo_menu.addAction(f"切换至 {pomo.long_break_min} 分钟长休")
    act_m_long.triggered.connect(lambda: pomo.switch_mode(pomo.MODE_LONG_BREAK))

    def sync_pomo_menu_labels():
        act_m_focus.setText(f"切换至 {pomo.focus_min} 分钟专注")
        act_m_short.setText(f"切换至 {pomo.short_break_min} 分钟短休")
        act_m_long.setText(f"切换至 {pomo.long_break_min} 分钟长休")

    pomo_menu.aboutToShow.connect(sync_pomo_menu_labels)

    act_pomo_reset = pomo_menu.addAction("重置当前计时")
    act_pomo_reset.triggered.connect(pomo.reset_timer)

    pomo_menu.addSeparator()
    act_pomo_dock = pomo_menu.addAction("重新贴合至 HUD 下方")
    act_pomo_dock.triggered.connect(pomo.sync_position_with_hud)

    act_pomo_vis = pomo_menu.addAction("显示 / 隐藏番茄钟")
    act_pomo_vis.triggered.connect(lambda: pomo.setVisible(not pomo.isVisible()))

    tray_menu.addSeparator()

    # Drag mode action
    act_drag = tray_menu.addAction("调整窗口位置（临时拖动 15 秒）")
    act_drag.triggered.connect(lambda: hud.enter_drag_mode(15))

    # Click-through toggle action
    act_ct = tray_menu.addAction("鼠标穿透模式")
    act_ct.setCheckable(True)
    is_ct = config_mgr.get("window", {}).get("click_through", True)
    act_ct.setChecked(is_ct)

    def on_toggle_click_through(checked):
        config_mgr.set("window", "click_through", checked)
        if checked:
            hud.enable_click_through()
        else:
            hud.disable_click_through()

    act_ct.triggered.connect(on_toggle_click_through)

    # Background Opacity Menu
    op_menu = tray_menu.addMenu("底板不透明度")
    opacity_presets = [
        (0.90, "90% 深色不透"),
        (0.75, "75% 深灰磨砂"),
        (0.55, "55% 半透暗玻"),
        (0.35, "35% 轻透微影"),
        (0.00, "0% 透明无底板"),
    ]
    op_actions = []
    for val, text in opacity_presets:
        act_op = op_menu.addAction(text)
        act_op.setCheckable(True)
        act_op.triggered.connect(lambda checked, v=val: (hud.set_bg_opacity(v), pomo.update()))
        op_actions.append((val, act_op))

    def sync_opacity_menu():
        cur_op = float(config_mgr.get("window", {}).get("bg_opacity", 0.85))
        for v, act in op_actions:
            act.setChecked(abs(cur_op - v) < 0.03)

    op_menu.aboutToShow.connect(sync_opacity_menu)

    # Autostart toggle action
    act_autostart = tray_menu.addAction("开机自动启动")
    act_autostart.setCheckable(True)
    act_autostart.setChecked(is_autostart_enabled())
    act_autostart.triggered.connect(lambda checked: set_autostart(checked))

    # Pin to bottom
    act_bottom = tray_menu.addAction("贴回桌面底层")
    act_bottom.triggered.connect(lambda: (hud.send_to_bottom(), pomo.send_to_bottom()))

    # VPS Settings
    act_cfg = tray_menu.addAction("配置 VPS 探针参数")
    act_cfg.triggered.connect(hud.open_vps_config)

    tray_menu.addSeparator()
    act_quit = tray_menu.addAction("退出 CyberHUD")
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
