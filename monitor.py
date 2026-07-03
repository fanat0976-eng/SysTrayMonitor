"""
SysTray Monitor — иконка в трее с CPU/RAM/Disk + Ollama статус.
"""
import asyncio
import threading
import time
import sys
from datetime import datetime

import psutil
import httpx
import pystray
from PIL import Image, ImageDraw, ImageFont


# ── Config ─────────────────────────────────────────────
OLLAMA_URL = "http://127.0.0.1:11434"
UPDATE_INTERVAL = 3  # seconds


# ── System metrics ─────────────────────────────────────
def get_metrics():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    ollama_status = "OFF"
    ollama_models = 0
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if r.status_code == 200:
            models = r.json().get("models", [])
            ollama_status = "ON"
            ollama_models = len(models)
    except Exception:
        pass

    return {
        "cpu": cpu,
        "ram_used": ram.used // (1024 * 1024),
        "ram_total": ram.total // (1024 * 1024),
        "ram_pct": ram.percent,
        "disk_free": disk.free // (1024 * 1024 * 1024),
        "disk_total": disk.total // (1024 * 1024 * 1024),
        "disk_pct": disk.percent,
        "ollama": ollama_status,
        "ollama_models": ollama_models,
    }


# ── Icon generation ────────────────────────────────────
def create_icon(cpu_pct, ram_pct, ollama_ok):
    """Create a small tray icon with status color."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle — color by CPU load
    if cpu_pct > 80:
        color = (220, 50, 50)  # red
    elif cpu_pct > 50:
        color = (220, 160, 30)  # yellow
    else:
        color = (50, 180, 80)  # green

    draw.ellipse([4, 4, 60, 60], fill=color)

    # CPU number
    text = f"{int(cpu_pct)}"
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((64 - tw) / 2, (64 - th) / 2 - 2), text, fill="white", font=font)

    # Ollama dot
    dot_color = (0, 200, 0) if ollama_ok else (100, 100, 100)
    draw.ellipse([48, 2, 60, 14], fill=dot_color)

    return img


# ── Tooltip ────────────────────────────────────────────
def make_tooltip(m):
    return (
        f"CPU: {m['cpu']:.0f}%\n"
        f"RAM: {m['ram_used']}MB / {m['ram_total']}MB ({m['ram_pct']:.0f}%)\n"
        f"Disk C:: {m['disk_free']}GB free / {m['disk_total']}GB\n"
        f"Ollama: {m['ollama']} ({m['ollama_models']} models)"
    )


# ── Menu ───────────────────────────────────────────────
def make_menu(m):
    return pystray.Menu(
        pystray.MenuItem(f"CPU: {m['cpu']:.0f}%", None, enabled=False),
        pystray.MenuItem(f"RAM: {m['ram_used']}MB / {m['ram_total']}MB ({m['ram_pct']:.0f}%)", None, enabled=False),
        pystray.MenuItem(f"Disk: {m['disk_free']}GB free ({m['disk_pct']:.0f}%)", None, enabled=False),
        pystray.MenuItem(f"Ollama: {m['ollama']} ({m['ollama_models']} models)", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Refresh", lambda: None),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", lambda icon, item: icon.stop()),
    )


# ── Main loop ──────────────────────────────────────────
class TrayMonitor:
    def __init__(self):
        self.icon = None
        self.running = True

    def update(self):
        while self.running:
            try:
                m = get_metrics()
                img = create_icon(m["cpu"], m["ram_pct"], m["ollama"] == "ON")
                tooltip = make_tooltip(m)
                menu = make_menu(m)

                if self.icon:
                    self.icon.icon = img
                    self.icon.title = tooltip
                    self.icon.menu = menu
            except Exception as e:
                print(f"Update error: {e}")
            time.sleep(UPDATE_INTERVAL)

    def run(self):
        m = get_metrics()
        img = create_icon(m["cpu"], m["ram_pct"], m["ollama"] == "ON")

        self.icon = pystray.Icon(
            "SysTrayMonitor",
            icon=img,
            title="SysTray Monitor",
            menu=make_menu(m),
        )

        # Background updater
        t = threading.Thread(target=self.update, daemon=True)
        t.start()

        # Run tray (blocking)
        self.icon.run()


if __name__ == "__main__":
    monitor = TrayMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.running = False
        sys.exit(0)
