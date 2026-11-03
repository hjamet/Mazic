#!/usr/bin/env python3
"""
Mazic Online Launcher — Starts FastAPI 30 Hz server + Cloudflare Quick Tunnel.
Binds on dual-stack IPv4/IPv6 port 8090 and creates a public trycloudflare.com URL.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TUNNEL_FILE = BASE_DIR / "tunnel_url.txt"

CLOUDFLARED_CANDIDATES = [
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
    "cloudflared",
]


def find_cloudflared() -> str:
    """Finds the cloudflared executable path."""
    for candidate in CLOUDFLARED_CANDIDATES:
        p = Path(candidate)
        if p.exists() and p.is_file():
            return str(p)
    # Fallback to PATH check
    import shutil
    which_path = shutil.which("cloudflared")
    if which_path:
        return which_path
    return CLOUDFLARED_CANDIDATES[0]


def print_banner(tunnel_url: str):
    """Displays server launch banner with URLs."""
    banner = f"""
========================================================================
  🔮  MAZIC — MULTIJOUEUR EN LIGNE AUTORITAIRE 30 Hz
========================================================================
  🏠  Local URL:   http://localhost:8090
  🌐  Tunnel URL:  {tunnel_url}
  
  🎮  Envoie l'URL publique à tes amis pour jouer ensemble !
  🛑  Appuie sur Ctrl+C pour arrêter le serveur et fermer le tunnel.
========================================================================
"""
    print(banner, flush=True)


def main():
    cloudflared_bin = find_cloudflared()
    if not Path(cloudflared_bin).exists() and shutil.which(cloudflared_bin) is None:
        print(f"[ERROR] cloudflared introuvable à l'adresse : {cloudflared_bin}", file=sys.stderr)
        sys.exit(1)

    # 1. Clean previous tunnel_url.txt
    if TUNNEL_FILE.exists():
        try:
            TUNNEL_FILE.unlink()
        except Exception:
            pass

    print("[1/3] Démarrage du serveur FastAPI / WebSockets sur port 8090 (0.0.0.0)...")
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8090",
        "--log-level",
        "info",
    ]
    server_proc = subprocess.Popen(
        uvicorn_cmd,
        cwd=str(BASE_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # Small delay for socket binding
    time.sleep(1.0)

    print(f"[2/3] Démarrage du tunnel Cloudflared ({cloudflared_bin})...")
    cf_cmd = [
        cloudflared_bin,
        "tunnel",
        "--url",
        "http://127.0.0.1:8090",
        "--no-autoupdate",
    ]
    cf_proc = subprocess.Popen(
        cf_cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    tunnel_url = None
    url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    def monitor_cloudflared():
        nonlocal tunnel_url
        try:
            for line in cf_proc.stdout:
                line_str = line.strip()
                if not tunnel_url:
                    match = url_regex.search(line_str)
                    if match:
                        tunnel_url = match.group(0)
                        TUNNEL_FILE.write_text(tunnel_url, encoding="utf-8")
                        print_banner(tunnel_url)
                # Output key tunnel info lines
                if "INF" in line_str or "ERR" in line_str or "trycloudflare" in line_str:
                    print(f"[cloudflared] {line_str}", flush=True)
        except Exception:
            pass

    cf_thread = threading.Thread(target=monitor_cloudflared, daemon=True)
    cf_thread.start()

    def shutdown(signum=None, frame=None):
        print("\n[3/3] Arrêt des processus Mazic...")
        if cf_proc.poll() is None:
            cf_proc.terminate()
            try:
                cf_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cf_proc.kill()

        if server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_proc.kill()

        if TUNNEL_FILE.exists():
            try:
                TUNNEL_FILE.unlink()
            except Exception:
                pass
        print("Serveur arrêté proprement.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Wait for processes
    try:
        while True:
            if server_proc.poll() is not None:
                print(f"[WARN] Le serveur FastAPI s'est arrêté avec le code {server_proc.returncode}")
                break
            if cf_proc.poll() is not None:
                print(f"[WARN] Cloudflared s'est arrêté avec le code {cf_proc.returncode}")
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
