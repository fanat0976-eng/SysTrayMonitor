"""
SysTray Monitor — иконка в трее с CPU/RAM/Disk + Ollama статус.
"""
import threading
import time
import sys

import psutil
import httpx
import pystray
from PIL import Image, ImageDraw, ImageFont


# ── Config ─────────────────────────────────────────────
OLLAMA_URL = "http://127.0.0.1:11434"
UPDATE_INTERVAL = 3

# Shared state
_metrics = {}
_lock = threading.Lock()


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
def create_icon(cpu_pct, ollama_ok):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if cpu_pct > 80:
        color = (220, 50, 50)
    elif cpu_pct > 50:
        color = (220, 160, 30)
    else:
        color = (50, 180, 80)

    draw.ellipse([4, 4, 60, 60], fill=color)

    text = f"{int(cpu_pct)}"
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((64 - tw) / 2, (64 - th) / 2 - 2), text, fill="white", font=font)

    dot_color = (0, 200, 0) if ollama_ok else (100, 100, 100)
    draw.ellipse([48, 2, 60, 14], fill=dot_color)

    return img


# ── Dynamic menu ───────────────────────────────────────
def make_menu():
    """Build menu with current metrics."""
    with _lock:
        m = _metrics.copy()

    if not m:
        return pystray.Menu(
            pystray.MenuItem("Loading...", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda i, i2: i.stop()),
        )

    return pystray.Menu(
        pystray.MenuItem(f"CPU:  {m.get('cpu', 0):.0f}%", None, enabled=False),
        pystray.MenuItem(f"RAM:  {m.get('ram_used', 0)} / {m.get('ram_total', 0)} MB ({m.get('ram_pct', 0):.0f}%)", None, enabled=False),
        pystray.MenuItem(f"Disk: {m.get('disk_free', 0)} GB free ({m.get('disk_pct', 0):.0f}%)", None, enabled=False),
        pystray.MenuItem(f"Ollama: {m.get('ollama', '?')} ({m.get('ollama_models', 0)} models)", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Refresh", lambda i, i2: update_now()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", lambda i, i2: i.stop()),
    )


def update_now():
    """Force immediate metrics update."""
    global _metrics
    m = get_metrics()
    with _lock:
        _metrics = m


# ── Background updater ─────────────────────────────────
def updater(icon):
    """Background thread that updates icon + shared state."""
    while True:
        try:
            m = get_metrics()
            with _lock:
                global _metrics
                _metrics = m

            icon.icon = create_icon(m["cpu"], m["ollama"] == "ON")
            icon.title = f"CPU {m['cpu']:.0f}% | RAM {m['ram_pct']:.0f}% | Ollama {m['ollama']}"
            icon.menu = make_menu()
        except Exception as e:
            print(f"Update error: {e}")
        time.sleep(UPDATE_INTERVAL)


# ── Main ───────────────────────────────────────────────
def main():
    m = get_metrics()
    with _lock:
        global _metrics
        _metrics = m

    icon = pystray.Icon(
        "SysTrayMonitor",
        icon=create_icon(m["cpu"], m["ollama"] == "ON"),
        title=f"CPU {m['cpu']:.0f}% | RAM {m['ram_pct']:.0f}% | Ollama {m['ollama']}",
        menu=make_menu(),
    )

    # Start background updater
    t = threading.Thread(target=updater, args=(icon,), daemon=True)
    t.start()

    icon.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
