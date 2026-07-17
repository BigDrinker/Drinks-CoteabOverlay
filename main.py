from __future__ import annotations

import traceback
import json
import threading
from typing import Optional, Any
import ctypes
import win32gui, win32con, win32api
import webbrowser
import webview
import os
import sys
import time
import psutil
from datetime import datetime
import logging
import shutil
import subprocess
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import socket
import random
from pathlib import Path
from biome_tracker.config import APPDATA_BASE
import keyboard

ORIGINAL_ABS_FILE = os.path.abspath(__file__)
os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--disable-gpu'

# paths crafting_files_do_not_open and macoroni logs go into appdata/local instead of next to the EXE (maybe)
APPDATA_BASE.mkdir(parents=True, exist_ok=True)
os.chdir(APPDATA_BASE)

# When packaged, the native overlay is launched by starting this same EXE with
# a private command-line switch. Handle it before the single-instance mutex so
# the overlay child is not mistaken for a second macro instance.
if "--native-overlay" in sys.argv:
    os.environ.setdefault("COTEAB_OVERLAY_DIR", str(APPDATA_BASE))
    try:
        from native_overlay_process import Overlay
        Overlay().create()
    except Exception:
        crash_path = APPDATA_BASE / "native_overlay_crash.log"
        crash_path.write_text(traceback.format_exc(), encoding="utf-8")
    sys.exit(0)

_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "CoteabMacroSingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    ctypes.windll.user32.MessageBoxW(
        0,
        "Coteab Macro is already running!\n\nPlease close the existing instance before opening a new one.",
        "Coteab Macro",
        0x30
    )
    sys.exit(0)

try:
    import numpy
    import cv2
    import pyautogui
except Exception as e:
    err_text = str(e)
    if "numpy" in err_text.lower() or "c-extension" in err_text.lower() or "dll" in err_text.lower() or "cv2" in err_text.lower():
        msg = (
            "Coteab Macro failed to load required components.\n\n"
            "This is because your computer is missing the standard 'Visual C++ Redistributable (x64)' (i think so).\n\n"
            "Please download and install it from Microsoft's official website and try open the macro again!\n\n"
            f"Error details: {err_text}"
        )
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "Missing Windows Component", 0x10 | 0x0)
        except Exception:
            pass
        sys.exit(1)
    else:
        raise

# i added this so we can easily change macro version upon releases without having to change multiple back-end & front-end behaviours
# for future people that is reading the open source code, hello :p
current_version = "v2.2-overlay"
os.environ["COTEAB_MACRO_VERSION"] = current_version
UPDATE_LATEST_RELEASE_API_URL = "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest"
os.environ["COTEAB_UPDATE_API_URL"] = UPDATE_LATEST_RELEASE_API_URL
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1" 

_wv2_user_data_base = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "CoteabMacro", "WebView2UserData"
)
try:
    if os.path.exists(_wv2_user_data_base):
        for _f in os.listdir(_wv2_user_data_base):
            try: shutil.rmtree(os.path.join(_wv2_user_data_base, _f), ignore_errors=True)
            except Exception: pass
except Exception:
    pass

_wv2_user_data = os.path.join(_wv2_user_data_base, f"Session_{int(time.time())}")
os.makedirs(_wv2_user_data, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = _wv2_user_data

try: psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception: pass

from biome_tracker.config import (
    ensure_workspace_files,
    sync_config,
    load_config,
    save_config,
    normalize_auto_pop_biomes,
)

def get_base_path(): return sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(ORIGINAL_ABS_FILE)

def _get_frontend_dist_dirs() -> list[str]:
    base_path = get_base_path()
    from biome_tracker.config import APPDATA_BASE
    
    dirs = [
        os.path.join(str(APPDATA_BASE), "dist"),
        os.path.join(str(APPDATA_BASE), "frontend", "dist"),
        os.path.join(os.getcwd(), "frontend", "dist"),
        os.path.join(os.getcwd(), "dist"),
    ]
    
    if getattr(sys, "frozen", False):
        dirs.append(os.path.join(base_path, "lib", "dist"))
        dirs.append(os.path.join(base_path, "dist"))
    else:
        dirs.append(os.path.join(base_path, "frontend", "dist"))
        dirs.append(os.path.join(base_path, "lib", "dist"))
        dirs.append(os.path.join(base_path, "dist"))

    return [d for d in dirs if os.path.exists(d)]


def get_frontend_entry():
    for dist_dir in _get_frontend_dist_dirs():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            try:
                abs_path = os.path.abspath(index_file).replace("\\", "/")
                with open(index_file, "r", encoding="utf-8") as f:
                    html_content = f.read()
                print(f"Loading frontend from local: {abs_path}")
                return {"html": html_content, "url": f"file:///{abs_path}"}
            except Exception as e:
                print(f"Error reading local index.html: {e}")

    frontend_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/index.html"
    try:
        from biome_tracker.config import APPDATA_BASE
        appdata_dist = os.path.join(str(APPDATA_BASE), "dist")
        os.makedirs(appdata_dist, exist_ok=True)

        req = urllib.request.Request(frontend_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            html_content = response.read().decode('utf-8')
            if html_content and len(html_content) > 1000:
                saved_path = os.path.join(appdata_dist, "index.html")
                with open(saved_path, "w", encoding="utf-8") as f: f.write(html_content)
                abs_path = os.path.abspath(saved_path).replace("\\", "/")
                print(f"Fetched frontend from GitHub -> saved to: {abs_path}")
                return {"html": html_content, "url": f"file:///{abs_path}"}
    except Exception as e:
        print(f"Failed to fetch frontend from GitHub: {e}")

    return {"url": "http://localhost:5173"}


def _read_cli_value(flag, default=""):
    try:
        if flag not in sys.argv: return default
        idx = sys.argv.index(flag)
        if idx + 1 >= len(sys.argv): return default
        return str(sys.argv[idx + 1]).strip()
    except Exception:
        return default


def _cfg_bool(cfg, key, default=False):
    try:
        if not isinstance(cfg, dict): return bool(default)
        val = cfg.get(key, default)
        if isinstance(val, str):
            val = val.strip().lower()
            return val in ("1", "true", "yes", "on")
        return bool(val)
    except Exception:
        return bool(default)

class LoggerWriter:
    def __init__(self, filename="macro_logs.txt", original_stream=None):
        self.terminal = original_stream
        self.filename = filename

    def write(self, message):
        if self.terminal is not None:
            try:
                self.terminal.write(message)
                self.terminal.flush()
            except UnicodeEncodeError:
                try:
                    self.terminal.write(message.encode("ascii", "replace").decode("ascii"))
                    self.terminal.flush()
                except Exception:
                    pass
            except Exception:
                pass
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(message)
        except Exception:
            pass

    def flush(self):
        if self.terminal is not None:
            try:
                self.terminal.flush()
            except Exception:
                pass

sys.stdout = LoggerWriter("macro_logs.txt", sys.stdout)
sys.stderr = LoggerWriter("macro_logs.txt", sys.stderr)

class Api:
    def __init__(self, tracker=None):
        self._tracker = tracker
        self._window = None
        self._overlay_window = None
        self._overlay_lock = threading.RLock()
        self._overlay_creating = False
        self._overlay_alpha_lock = threading.Lock()
        self._overlay_alpha_timer = None
        self._overlay_process = None
        self._overlay_state_stop = threading.Event()
        self._overlay_state_thread = None
        self._calib_mgr = None

        # fishing mode stuff
        self._fishing_stop_event = threading.Event()
        self._fishing_thread = None
        self._fishing_lock = threading.Lock()
        self._fishing_runtime_state = {
            "fish_caught_count": 0,
            "fish_caught_since_merchant": 0,
            "fish_caught_since_br_sc": 0,
            "rejoin_in_progress": False,
            "force_sell_on_next_cycle": False,
            "merchant_requires_reset": False,
        }

        # rare biome pop up confirmation
        self._biome_confirm_evt = threading.Event()
        self._biome_confirm_result = None
        self.emergency_port = None

    def set_window(self, window):
        self._window = window
        if self._calib_mgr is None:
            from biome_tracker.base_support import CalibrationManager
            self._calib_mgr = CalibrationManager()
        self._calib_mgr.set_refs(
            window=window,
            tracker=self._tracker,
            save_fn=save_config,
            emit_fn=self.emit_calibration_result
        )

    def get_config(self):
        t = self._tracker
        if t and isinstance(getattr(t, 'config', None), dict) and t.config:
            return t.config
        return load_config()

    def get_biome_data(self):
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            result = {}
            for biome, data in self._tracker.biome_data.items():
                color = data.get("color", "0xffffff")
                if isinstance(color, str) and color.startswith("0x"): color = "#" + color[2:]
                result[biome] = color
            return result
        return {}

    def get_full_biome_data(self):
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            return self._tracker.biome_data
        return {}

    def open_appdata(self):
        try:
            os.startfile(str(APPDATA_BASE))
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, config_data):
        prev_anti_afk = False
        if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
            prev_anti_afk = bool(self._tracker.config.get("anti_afk", False))

        cfg = dict(config_data) if isinstance(config_data, dict) else dict(self.get_config())

        # normalize auto pop biomes with whatever biome list we have
        biome_names = []
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            biome_names = list(self._tracker.biome_data.keys())
        cfg["auto_pop_biomes"] = normalize_auto_pop_biomes(cfg, biome_names=biome_names)


        if _cfg_bool(cfg, "fishing_failsafe_rejoin") and not _cfg_bool(cfg, "auto_reconnect"):
            cfg["fishing_failsafe_rejoin"] = False

        save_config(cfg)
        if self._tracker:
            if not isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config = {}
            self._tracker.config.update(cfg)

            # sync webhook urls to the tracker
            if 'webhook_url' in cfg:
                self._tracker.webhook_urls = cfg['webhook_url']
                try:
                    if hasattr(self._tracker, "refresh_active_webhook_channels"):
                        self._tracker.refresh_active_webhook_channels(force=True)
                except Exception:
                    pass


            if self._tracker.detection_running:
                # hot-swap fishing mode
                if self._is_fishing_mode_enabled():
                    self._start_fishing_worker()
                else:
                    self._stop_fishing_worker()

                if not prev_anti_afk and self._tracker.config.get("anti_afk", False):
                    try:
                        threading.Thread(target=self._tracker.perform_anti_afk_action, daemon=True).start()
                    except Exception:
                        pass

    def import_config(self):
        try:
            if not self._window:
                return {"success": False, "error": "Window not available"}

            result = self._window.create_file_dialog(
                webview.FileDialog.OPEN, allow_multiple=False,
                file_types=("JSON Files (*.json)",),
            )
            if not result:
                return {"success": False, "error": "No file selected"}

            path = result[0] if isinstance(result, (list, tuple)) else result
            with open(path, "r", encoding="utf-8") as f:
                imported = json.loads(f.read())
            if not isinstance(imported, dict):
                return {"success": False, "error": "Invalid config file: must be a JSON object"}

            save_config(imported)

            if self._tracker:
                if not isinstance(getattr(self._tracker, "config", None), dict):
                    self._tracker.config = {}
                self._tracker.config.update(imported)
                if 'webhook_url' in imported:
                    self._tracker.webhook_urls = imported['webhook_url']
                try:
                    if hasattr(self._tracker, "refresh_active_webhook_channels"):
                        self._tracker.refresh_active_webhook_channels(force=True)
                except Exception: pass

            return {"success": True, "config": imported}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_window(self):
        self._stop_fishing_worker()
        # The overlay is a separate process. Stop it before destroying the
        # main window so it cannot remain orphaned after the macro closes.
        try:
            self.hide_overlay()
        except Exception:
            pass
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
        
        def delayed_exit():
            time.sleep(1.5)
            os._exit(0)
        threading.Thread(target=delayed_exit, daemon=True).start()
        return {"success": True}

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def toggle_maximize_window(self):
        if self._window:
            self._window.toggle_fullscreen()

    def set_always_on_top(self, enabled: bool):
        if self._window:
            try:
                hwnd = None
                if hasattr(self._window.gui, 'hwnd'):
                     hwnd = self._window.gui.hwnd
                else:
                     hwnd = win32gui.FindWindow(None, self._window.title)
                     
                if hwnd:
                     flag = win32con.HWND_TOPMOST if enabled else win32con.HWND_NOTOPMOST
                     win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0,
                                           win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except Exception as e:
                print(f"Failed to set always on top via win32gui: {e}")
                self._window.on_top = enabled

    def open_url(self, url: str):
        webbrowser.open(url)

    def _overlay_settings_path(self):
        return APPDATA_BASE / "overlay_settings.json"

    def _overlay_defaults(self):
        return {
            "enabled": False,
            "layout": "expanded",
            "position": "top-right",
            "background_transparency": 0.35,
            "theme": "midnight",
            "accent": "#aeb8ff",
            "font": "Inter",
            "minimum_rarity": 1,
            "show": {
                "status": True, "biome": True, "aura": True, "rarity": True,
                "merchant": True, "merchant_time": True, "time": True, "session": True,
                "biome_count": True, "merchant_count": True,
            },
            "always_on_top": True,
            "click_through": False,
            "scrollable": True,
            "remember_position": True,
            "row_order": ["biome","aura","rarity","merchant","merchant_time","time","session"],
            "notifications": {"biome": True, "aura": True, "merchant": True},
            "profile": "custom",
            "x": 120, "y": 120, "width": 380, "height": 300,
        }

    def _backup_overlay_settings(self):
        """Keep a few timestamped settings backups in AppData."""
        try:
            source = self._overlay_settings_path()
            if not source.exists():
                return
            backup_dir = APPDATA_BASE / "overlay_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(source, backup_dir / f"overlay_settings-{stamp}.json")
            backups = sorted(backup_dir.glob("overlay_settings-*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            for old_backup in backups[5:]:
                old_backup.unlink(missing_ok=True)
        except Exception as exc:
            print(f"[Overlay] Settings backup skipped: {exc}")

    def get_native_overlay_settings(self):
        defaults = self._overlay_defaults()
        try:
            path = self._overlay_settings_path()
            if path.exists():
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    show = dict(defaults["show"])
                    if isinstance(loaded.get("show"), dict):
                        show.update(loaded["show"])
                    defaults.update({k: v for k, v in loaded.items() if k != "show"})
                    defaults["show"] = show
        except Exception as e:
            print(f"[Overlay 2.0] Could not load settings: {e}")
        return defaults

    def update_native_overlay_settings(self, patch):
        if not isinstance(patch, dict):
            return {"success": False, "error": "Expected a settings object"}
        try:
            settings = self.get_native_overlay_settings()
            for key, raw in patch.items():
                if key == "show" and isinstance(raw, dict):
                    for row, value in raw.items():
                        if row in settings["show"]:
                            settings["show"][row] = bool(value)
                elif key == "enabled": settings[key] = bool(raw)
                elif key == "layout": settings[key] = str(raw).lower() if str(raw).lower() in {"compact","expanded"} else "expanded"
                elif key == "position": settings[key] = str(raw).lower() if str(raw).lower() in {"top-right","bottom-right","custom"} else "custom"
                elif key == "background_transparency": settings[key] = max(0.0, min(0.9, float(raw)))
                elif key == "theme": settings[key] = str(raw).lower() if str(raw).lower() in {"midnight","ocean","crimson","emerald","solar","frost","amoled","glass","neon","discord","spotify"} else "midnight"
                elif key == "accent":
                    value=str(raw).strip()
                    settings[key]=value if len(value)==7 and value.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in value[1:]) else '#aeb8ff'
                elif key == "font": settings[key] = str(raw) if str(raw) in {"Inter","Orbitron","JetBrains Mono","Sarpanch","Exo 2","Poppins","Rounded"} else "Inter"
                elif key == "minimum_rarity": settings[key] = max(1, min(10_000_000_000, int(raw)))
                elif key in {"x","y"}: settings[key] = int(raw)
                elif key == "width": settings[key] = max(300, min(900, int(raw)))
                elif key == "height": settings[key] = max(190, min(700, int(raw)))
                elif key == "row_order" and isinstance(raw, list):
                    valid=["biome","aura","rarity","merchant","merchant_time","time","session","biome_count","merchant_count"]
                    seen=[]
                    for item in raw:
                        item=str(item)
                        if item in valid and item not in seen: seen.append(item)
                    settings[key]=seen + [x for x in valid if x not in seen]
                elif key == "notifications" and isinstance(raw, dict):
                    current=dict(settings.get("notifications", {}))
                    for n in ("biome","aura","merchant"):
                        if n in raw: current[n]=bool(raw[n])
                    settings[key]=current
                elif key == "profile": settings[key]=str(raw)
                elif key in {"always_on_top","click_through","scrollable","remember_position"}: settings[key] = bool(raw)
            path=self._overlay_settings_path(); self._backup_overlay_settings(); tmp=path.with_suffix('.tmp')
            tmp.write_text(json.dumps(settings, indent=2), encoding='utf-8'); os.replace(tmp,path)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_minimum_rarity"] = int(settings.get("minimum_rarity", 1))
            if settings["enabled"]: self.show_overlay(settings.get("position"))
            else: self.hide_overlay()
            self._write_overlay_runtime_state_once()
            return {"success": True, "settings": settings}
        except Exception as e:
            print(f"[Overlay 2.0] Settings update failed: {e}")
            return {"success": False, "error": str(e)}

    def reset_native_overlay_settings(self):
        try:
            settings=self._overlay_defaults()
            path=self._overlay_settings_path(); self._backup_overlay_settings(); tmp=path.with_suffix('.tmp')
            tmp.write_text(json.dumps(settings, indent=2), encoding='utf-8'); os.replace(tmp,path)
            self.hide_overlay()
            return {"success": True, "settings": settings}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_native_overlay_profile(self, name):
        profiles = {
            "minimal": {"layout":"compact","show":{"status":True,"biome":True,"aura":True,"rarity":False,"merchant":False,"merchant_time":False,"time":False,"session":True},"row_order":["biome","aura","session","rarity","merchant","merchant_time","time"],"profile":"minimal"},
            "afk": {"layout":"expanded","show":{"status":True,"biome":True,"aura":True,"rarity":True,"merchant":True,"merchant_time":True,"time":True,"session":True},"row_order":["biome","merchant","merchant_time","aura","rarity","session","time"],"profile":"afk"},
            "streaming": {"layout":"compact","background_transparency":0.55,"show":{"status":True,"biome":True,"aura":True,"rarity":True,"merchant":True,"merchant_time":False,"time":False,"session":False},"row_order":["biome","aura","rarity","merchant","session","time","merchant_time"],"profile":"streaming"},
            "full": {"layout":"expanded","show":{"status":True,"biome":True,"aura":True,"rarity":True,"merchant":True,"merchant_time":True,"time":True,"session":True},"row_order":["biome","aura","rarity","merchant","merchant_time","time","session"],"profile":"full"}
        }
        profile=profiles.get(str(name).lower())
        if not profile: return {"success":False,"error":"Unknown profile"}
        return self.update_native_overlay_settings(profile)

    def export_native_overlay_settings(self):
        try:
            out=self._overlay_settings_path().with_name("overlay_profile_export.json")
            out.write_text(json.dumps(self.get_native_overlay_settings(), indent=2), encoding="utf-8")
            return {"success":True,"path":str(out)}
        except Exception as e: return {"success":False,"error":str(e)}

    def import_native_overlay_settings(self):
        try:
            src=self._overlay_settings_path().with_name("overlay_profile_export.json")
            if not src.exists(): return {"success":False,"error":"overlay_profile_export.json was not found"}
            loaded=json.loads(src.read_text(encoding="utf-8"))
            if not isinstance(loaded,dict): return {"success":False,"error":"Invalid profile file"}
            return self.update_native_overlay_settings(loaded)
        except Exception as e: return {"success":False,"error":str(e)}

    def get_overlay_state(self):
        t = self._tracker
        settings = self.get_native_overlay_settings()
        state = {
            "status": "RUNNING" if (t and getattr(t, "detection_running", False)) else "STOPPED",
            "biome": str(getattr(t, "current_biome", None) or "NORMAL") if t else "NORMAL",
            "last_aura": str(getattr(t, "overlay_last_aura_found", None) or "None") if t else "None",
            "aura_rarity": str(getattr(t, "overlay_last_aura_rarity", None) or "Unknown") if t else "Unknown",
            "last_merchant": str(getattr(t, "overlay_last_merchant_found", None) or "None") if t else "None",
            "last_merchant_detected_at": float(getattr(t, "overlay_last_merchant_detected_at", 0) or 0) if t else 0,
            "session": "00:00:00",
            **settings,
        }
        try:
            if t and hasattr(t, "get_total_session_time"):
                state["session"] = str(t.get_total_session_time())
        except Exception:
            pass
        return state

    def update_overlay_settings(self, patch):
        """Atomically update native overlay settings and push runtime state.

        This avoids the frontend saving a stale full config and then calling a
        second setter, which previously caused settings to appear ignored and
        made Reset race the overlay process.
        """
        if not isinstance(patch, dict):
            return {"success": False, "error": "Expected an object of overlay settings"}
        allowed = {
            "overlay_enabled", "overlay_layout", "overlay_position",
            "overlay_transparency", "overlay_theme", "overlay_accent",
            "overlay_font", "overlay_minimum_rarity",
            "overlay_show_status", "overlay_show_biome", "overlay_show_aura",
            "overlay_show_rarity", "overlay_show_merchant",
            "overlay_show_merchant_time", "overlay_show_time",
            "overlay_show_session", "overlay_width", "overlay_height",
            "overlay_x", "overlay_y",
        }
        try:
            cfg = dict(self.get_config() or {})
            for key, raw in patch.items():
                if key not in allowed:
                    continue
                if key == "overlay_layout":
                    value = str(raw).lower()
                    cfg[key] = value if value in {"compact", "expanded"} else "expanded"
                elif key == "overlay_position":
                    value = str(raw).lower()
                    cfg[key] = value if value in {"top-right", "bottom-right", "custom"} else "top-right"
                elif key == "overlay_transparency":
                    cfg[key] = max(0.0, min(0.90, float(raw)))
                elif key == "overlay_theme":
                    value = str(raw).lower()
                    cfg[key] = value if value in {"midnight", "crimson", "emerald", "solar", "frost", "amoled"} else "midnight"
                elif key == "overlay_accent":
                    value = str(raw).strip()
                    cfg[key] = value if (len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:])) else "#aeb8ff"
                elif key == "overlay_font":
                    value = str(raw)
                    cfg[key] = value if value in {"Inter", "Sarpanch", "Orbitron", "Monospace", "Rounded"} else "Inter"
                elif key == "overlay_minimum_rarity":
                    cfg[key] = min(10_000_000_000, max(1, int(raw)))
                elif key == "overlay_width":
                    cfg[key] = max(300, min(900, int(raw)))
                elif key == "overlay_height":
                    cfg[key] = max(190, min(700, int(raw)))
                elif key in {"overlay_x", "overlay_y"}:
                    cfg[key] = int(raw)
                else:
                    cfg[key] = bool(raw)

            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config.update(cfg)

            enabled = bool(cfg.get("overlay_enabled", False))
            if enabled:
                self.show_overlay(cfg.get("overlay_position", "top-right"))
                self._write_overlay_runtime_state_once()
            else:
                self.hide_overlay()
            return {"success": True, "config": {k: cfg.get(k) for k in allowed}}
        except Exception as e:
            print(f"[Overlay] Atomic settings update failed: {e}")
            return {"success": False, "error": str(e)}

    def reset_overlay_layout_safe(self):
        """Reset settings without deleting files or restarting the overlay."""
        defaults = {
            "overlay_position": "top-right",
            "overlay_width": 380,
            "overlay_height": 300,
            "overlay_transparency": 0.35,
            "overlay_theme": "midnight",
            "overlay_accent": "#aeb8ff",
            "overlay_font": "Inter",
            "overlay_layout": "expanded",
            "overlay_minimum_rarity": 1,
            "overlay_show_status": True,
            "overlay_show_biome": True,
            "overlay_show_aura": True,
            "overlay_show_rarity": True,
            "overlay_show_merchant": True,
            "overlay_show_merchant_time": True,
            "overlay_show_time": True,
            "overlay_show_session": True,
        }
        return self.update_overlay_settings(defaults)

    def _overlay_coordinates(self, position=None):
        cfg = self.get_config() or {}
        position = str(position or cfg.get("overlay_position", "top-right")).lower()
        width = max(300, min(700, int(cfg.get("overlay_width", 360) or 360)))
        height = max(190, min(600, int(cfg.get("overlay_height", 230) or 230)))
        margin = 18
        try:
            left, top, right, bottom = win32api.SystemParametersInfo(win32con.SPI_GETWORKAREA)
            if position == "custom" and "overlay_x" in cfg and "overlay_y" in cfg:
                x = max(left, min(int(cfg["overlay_x"]), right - width))
                y = max(top, min(int(cfg["overlay_y"]), bottom - height))
            else:
                x = max(left + margin, right - width - margin)
                y = top + margin if position == "top-right" else max(top + margin, bottom - height - margin)
            return x, y, width, height
        except Exception:
            return 1200, (20 if position == "top-right" else 700), width, height

    def _set_overlay_interactive(self, interactive=False):
        """Toggle mouse interaction without changing the native frame.

        Keeping the original frameless style avoids the white/square frame and
        prevents Windows from shifting the window when Edit Mode is toggled.
        """
        try:
            hwnd = self._find_overlay_hwnd()
            if not hwnd:
                return False
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            # Preserve WS_EX_LAYERED: pywebview/WebView2 needs it for a truly
            # transparent host. Removing it is what caused the white panel.
            exstyle |= win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW
            if interactive:
                exstyle &= ~win32con.WS_EX_TRANSPARENT
            else:
                exstyle |= win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED,
            )
            return True
        except Exception as e:
            print(f"[Overlay] Interaction setup failed: {e}")
            return False

    def _find_overlay_hwnd(self):
        """Return the top-level native overlay window handle."""
        try:
            hwnd = win32gui.FindWindow(None, "Coteab Overlay")
            if hwnd and win32gui.IsWindow(hwnd):
                return hwnd
        except Exception:
            pass
        return 0

    def _apply_overlay_alpha(self):
        """Preserve per-pixel WebView transparency; CSS controls panel alpha."""
        try:
            hwnd = self._find_overlay_hwnd()
            if not hwnd:
                return False
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if not (exstyle & win32con.WS_EX_LAYERED):
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle | win32con.WS_EX_LAYERED)
            return True
        except Exception as e:
            print(f"[Overlay] Could not preserve layered transparency: {e}")
            return False

    def _schedule_overlay_alpha(self, delay=0.12):
        """Coalesce repeated UI requests into one native transparency update."""
        try:
            old = self._overlay_alpha_timer
            if old is not None:
                old.cancel()
        except Exception:
            pass
        timer = threading.Timer(delay, self._apply_overlay_alpha)
        timer.daemon = True
        self._overlay_alpha_timer = timer
        timer.start()

    def _apply_overlay_native_visuals(self):
        """Apply stable native opacity and genuinely rounded window edges.

        DWM handles Windows 11 corner rendering, while the window region is a
        fallback that physically clips the frameless host. This function is not
        called continuously during a resize, which avoids GDI/Win32 crashes.
        """
        try:
            hwnd = self._find_overlay_hwnd()
            if not hwnd:
                return False
            cfg = self.get_config() or {}
            # Alpha is applied separately so frequent slider updates never
            # rebuild the native rounded region.
            self._apply_overlay_alpha()

            # Ask Windows 11 to round the native top-level window.
            try:
                import ctypes
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    int(hwnd), DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(DWMWCP_ROUND), ctypes.sizeof(DWMWCP_ROUND)
                )
            except Exception:
                pass

            # Match the native DWM border to the active overlay theme instead
            # of leaving a contrasting square/white edge around the host.
            try:
                import ctypes
                theme_colors = {
                    "midnight": (10, 13, 24), "crimson": (24, 8, 13),
                    "emerald": (7, 19, 15), "solar": (24, 17, 7),
                    "frost": (7, 18, 27),
                }
                r, g, b = theme_colors.get(str(cfg.get("overlay_theme", "midnight")).lower(), (10, 13, 24))
                colorref = ctypes.c_int(r | (g << 8) | (b << 16))
                DWMWA_BORDER_COLOR = 34
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    int(hwnd), DWMWA_BORDER_COLOR,
                    ctypes.byref(colorref), ctypes.sizeof(colorref)
                )
            except Exception:
                pass

            # Physical clipping fallback for frameless pywebview windows.
            cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
            width, height = max(1, cr - cl), max(1, cb - ct)
            diameter = max(28, min(56, int(min(width, height) * 0.16)))
            region = win32gui.CreateRoundRectRgn(0, 0, width + 1, height + 1, diameter, diameter)
            win32gui.SetWindowRgn(hwnd, region, True)
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED
            )
            return True
        except Exception as e:
            print(f"[Overlay] Native visual setup failed: {e}")
            return False

    def _apply_overlay_clickthrough(self):
        time.sleep(0.8)
        cfg = self.get_config() or {}
        self._set_overlay_interactive(bool(cfg.get("overlay_edit_mode", False)))
        self._apply_overlay_native_visuals()

    def _overlay_runtime_path(self):
        return APPDATA_BASE / "overlay_runtime_state.json"

    def _write_overlay_runtime_state(self):
        while not self._overlay_state_stop.wait(0.5):
            try:
                state = self.get_overlay_state()
                payload = state
                path = self._overlay_runtime_path()
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(payload), encoding="utf-8")
                os.replace(tmp, path)
            except Exception as e:
                print(f"[Native Overlay] state update failed: {e}")

    def show_overlay(self, position=None):
        with self._overlay_lock:
            try:
                if self._overlay_process is not None and self._overlay_process.poll() is None:
                    return {"success": True, "already_open": True}
                self._overlay_state_stop.clear()
                self._write_overlay_runtime_state_once()
                child_env = dict(os.environ)
                child_env["COTEAB_OVERLAY_DIR"] = str(APPDATA_BASE)
                if getattr(sys, "frozen", False):
                    command = [sys.executable, "--native-overlay"]
                    child_cwd = str(APPDATA_BASE)
                else:
                    script = Path(ORIGINAL_ABS_FILE).resolve().parent / "native_overlay_process.py"
                    if not script.exists():
                        return {"success": False, "error": f"Missing {script.name}"}
                    command = [sys.executable, str(script)]
                    child_cwd = str(script.parent)
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                self._overlay_process = subprocess.Popen(
                    command,
                    cwd=child_cwd,
                    env=child_env,
                    creationflags=creationflags,
                )
                if self._overlay_state_thread is None or not self._overlay_state_thread.is_alive():
                    self._overlay_state_thread = threading.Thread(target=self._write_overlay_runtime_state, daemon=True)
                    self._overlay_state_thread.start()
                return {"success": True}
            except Exception as e:
                self._overlay_process = None
                print(f"[Native Overlay] failed to start: {e}")
                return {"success": False, "error": str(e)}

    def _write_overlay_runtime_state_once(self):
        state = self.get_overlay_state()
        payload = state
        self._overlay_runtime_path().write_text(json.dumps(payload), encoding="utf-8")

    def hide_overlay(self):
        with self._overlay_lock:
            try:
                self._overlay_state_stop.set()
                if self._overlay_process is not None and self._overlay_process.poll() is None:
                    self._overlay_process.terminate()
                    try:
                        self._overlay_process.wait(timeout=2)
                    except Exception:
                        self._overlay_process.kill()
                self._overlay_process = None
                self._overlay_window = None
                return {"success": True}
            except Exception as e:
                self._overlay_process = None
                return {"success": False, "error": str(e)}

    def set_overlay_position(self, position):
        requested = str(position).lower()
        position = requested if requested in ("top-right", "bottom-right", "custom") else "top-right"
        try:
            cfg = dict(self.get_config() or {})
            cfg["overlay_position"] = position
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_position"] = position
            return {"success": True, "position": position}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _capture_overlay_bounds(self):
        """Persist the overlay's current native position and size immediately."""
        try:
            hwnd = self._find_overlay_hwnd()
            if not hwnd or not win32gui.IsWindow(hwnd):
                return False
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            width = max(300, r - l)
            height = max(190, b - t)
            cfg = dict(self.get_config() or {})
            cfg.update({
                "overlay_x": int(l),
                "overlay_y": int(t),
                "overlay_width": int(width),
                "overlay_height": int(height),
                "overlay_position": "custom",
            })
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config.update(cfg)
            return True
        except Exception as e:
            print(f"[Overlay] Failed to capture current bounds: {e}")
            return False

    def set_overlay_edit_mode(self, enabled):
        enabled = bool(enabled)
        try:
            bounds = self._persist_overlay_bounds() if not enabled else None
            cfg = dict(self.get_config() or {})
            cfg["overlay_edit_mode"] = enabled
            if bounds:
                cfg.update(bounds)
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config.update(cfg)
            # Do not recreate the region or native frame while toggling edit
            # mode. This keeps the exact position and avoids resize breakage.
            result = {"success": True, "edit_mode": enabled}
            if bounds:
                result.update(bounds)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_opacity(self, opacity):
        try:
            opacity = max(0.25, min(1.0, float(opacity)))
            cfg = dict(self.get_config() or {})
            cfg["overlay_opacity"] = opacity
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_opacity"] = opacity
            return {"success": True, "opacity": opacity}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_transparency(self, transparency):
        try:
            transparency = max(0.0, min(0.90, float(transparency)))
            cfg = dict(self.get_config() or {})
            cfg["overlay_transparency"] = transparency
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_transparency"] = transparency
            return {"success": True, "transparency": transparency}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_theme(self, theme):
        allowed = {"midnight", "crimson", "emerald", "solar", "frost", "amoled"}
        theme = str(theme).lower()
        if theme not in allowed:
            theme = "midnight"
        try:
            cfg = dict(self.get_config() or {})
            cfg["overlay_theme"] = theme
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_theme"] = theme
            self._apply_overlay_native_visuals()
            return {"success": True, "theme": theme}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_accent(self, accent):
        accent = str(accent).strip()
        if not (len(accent) == 7 and accent.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in accent[1:])):
            accent = "#aeb8ff"
        try:
            cfg = dict(self.get_config() or {})
            cfg["overlay_accent"] = accent
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_accent"] = accent
            return {"success": True, "accent": accent}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_font(self, font):
        allowed = {"Inter", "Sarpanch", "Orbitron", "Monospace", "Rounded"}
        font = str(font)
        if font not in allowed:
            font = "Inter"
        try:
            cfg = dict(self.get_config() or {})
            cfg["overlay_font"] = font
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_font"] = font
            return {"success": True, "font": font}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_minimum_rarity(self, rarity):
        try:
            rarity = min(10_000_000_000, max(1, int(rarity)))
            cfg = dict(self.get_config() or {})
            cfg["overlay_minimum_rarity"] = rarity
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_minimum_rarity"] = rarity
            return {"success": True, "minimum_rarity": rarity}
        except Exception as e:
            return {"success": False, "error": str(e)}


    def set_overlay_option(self, key, value):
        """Save a supported native-overlay option and push it to the runtime state."""
        allowed = {
            "overlay_show_status", "overlay_show_biome", "overlay_show_aura",
            "overlay_show_rarity", "overlay_show_merchant",
            "overlay_show_merchant_time", "overlay_show_time",
            "overlay_show_session", "overlay_layout",
        }
        key = str(key)
        if key not in allowed:
            return {"success": False, "error": "Unsupported overlay option"}
        if key == "overlay_layout":
            value = str(value).lower()
            if value not in {"compact", "expanded"}:
                value = "expanded"
        else:
            value = bool(value)
        try:
            cfg = dict(self.get_config() or {})
            cfg[key] = value
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config[key] = value
            self._write_overlay_runtime_state_once()
            return {"success": True, "key": key, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reset_overlay_layout(self):
        try:
            cfg = dict(self.get_config() or {})
            cfg.update({
                "overlay_position": "top-right",
                "overlay_width": 380,
                "overlay_height": 300,
                "overlay_transparency": 0.35,
                "overlay_theme": "midnight",
                "overlay_accent": "#aeb8ff",
                "overlay_font": "Inter",
                "overlay_layout": "expanded",
                "overlay_show_status": True,
                "overlay_show_biome": True,
                "overlay_show_aura": True,
                "overlay_show_rarity": True,
                "overlay_show_merchant": True,
                "overlay_show_merchant_time": True,
                "overlay_show_time": True,
                "overlay_show_session": True,
            })
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config.update(cfg)
            try:
                native_cfg = Path(ORIGINAL_ABS_FILE).resolve().parent / "native_overlay_config.json"
                if native_cfg.exists():
                    native_cfg.unlink()
            except Exception:
                pass
            self._write_overlay_runtime_state_once()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_overlay_size(self, width, height):
        try:
            width = max(300, min(900, int(width)))
            height = max(190, min(700, int(height)))
            cfg = dict(self.get_config() or {})
            cfg["overlay_width"], cfg["overlay_height"] = width, height
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config["overlay_width"] = width
                self._tracker.config["overlay_height"] = height
            return {"success": True, "width": width, "height": height}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _persist_overlay_bounds(self, hwnd=None):
        """Save the current native rectangle without relying on stale UI config."""
        try:
            hwnd = hwnd or self._find_overlay_hwnd()
            if not hwnd or not win32gui.IsWindow(hwnd):
                return None
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            bounds = {
                "overlay_x": int(l), "overlay_y": int(t),
                "overlay_width": max(300, int(r - l)),
                "overlay_height": max(190, int(b - t)),
                "overlay_position": "custom",
            }
            cfg = dict(self.get_config() or {})
            cfg.update(bounds)
            save_config(cfg)
            if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config.update(bounds)
            return bounds
        except Exception as e:
            print(f"[Overlay] Failed to save edited bounds: {e}")
            return None

    def begin_overlay_drag(self):
        try:
            hwnd = self._find_overlay_hwnd()
            if not hwnd:
                return {"success": False, "error": "Overlay window not found"}
            win32gui.ReleaseCapture()
            # SendMessage keeps the native move loop tied to the current mouse
            # press. When it returns, Windows has finalized the exact position.
            win32gui.SendMessage(hwnd, win32con.WM_NCLBUTTONDOWN, win32con.HTCAPTION, 0)
            bounds = self._persist_overlay_bounds(hwnd) or {}
            self._apply_overlay_native_visuals()
            return {"success": True, **bounds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def begin_overlay_resize(self, direction="se"):
        direction = str(direction or "se").lower()
        hit_tests = {
            "n": win32con.HTTOP, "s": win32con.HTBOTTOM,
            "e": win32con.HTRIGHT, "w": win32con.HTLEFT,
            "ne": win32con.HTTOPRIGHT, "nw": win32con.HTTOPLEFT,
            "se": win32con.HTBOTTOMRIGHT, "sw": win32con.HTBOTTOMLEFT,
        }
        if direction not in hit_tests:
            direction = "se"
        try:
            hwnd = self._find_overlay_hwnd()
            if not hwnd:
                return {"success": False, "error": "Overlay window not found"}
            win32gui.ReleaseCapture()
            win32gui.SendMessage(hwnd, win32con.WM_NCLBUTTONDOWN, hit_tests[direction], 0)
            bounds = self._persist_overlay_bounds(hwnd) or {}
            self._apply_overlay_native_visuals()
            return {"success": True, "direction": direction, **bounds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_macro_status(self):
        if self._tracker and getattr(self._tracker, 'detection_running', False):
            return "RUNNING"
        return "STOPPED"

    def get_macro_version(self):
        return current_version

    def _setup_emergency_server(self):
        class SafeModeHandler(BaseHTTPRequestHandler):
            api = self

            def do_GET(self):
                if self.path == "/health":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    # Serve files from any valid dist directory
                    file_path = self.path.split('?')[0].lstrip('/')
                    if not file_path or file_path == 'index.html':
                        file_path = 'index.html'
                    
                    found_full_path = None
                    for dist_dir in _get_frontend_dist_dirs():
                        full_path = os.path.join(dist_dir, file_path)
                        if os.path.exists(full_path) and os.path.isfile(full_path):
                            found_full_path = full_path
                            break
                    
                    if found_full_path:
                        self.send_response(200)
                        if file_path.endswith('.js'): self.send_header('Content-type', 'application/javascript')
                        elif file_path.endswith('.css'): self.send_header('Content-type', 'text/css')
                        elif file_path.endswith('.html'): self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        with open(found_full_path, 'rb') as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_response(404)
                        self.end_headers()

            def do_POST(self):
                if self.path.startswith("/api/"):
                    method_name = self.path.replace("/api/", "")
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    try:
                        args = json.loads(post_data) if post_data else []
                    except:
                        args = []
                    
                    method = getattr(self.api, method_name, None)
                    if method and callable(method):
                        try:
                            if isinstance(args, list): result = method(*args)
                            elif isinstance(args, dict): result = method(**args)
                            else: result = method()
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps(result).encode())
                        except Exception as e:
                            self.send_response(500)
                            self.end_headers()
                            self.wfile.write(str(e).encode())
                
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def log_message(self, format, *args): pass

        self.emergency_port = random.randint(18000, 19000)
        def _run():
            try:
                server = ThreadingHTTPServer(('127.0.0.1', self.emergency_port), SafeModeHandler)
                print(f"Emergency Server running on http://127.0.0.1:{self.emergency_port}")
                server.serve_forever()
            except Exception as e:
                print(f"Server failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _setup_emergency_hotkey(self):
        def trigger():
            print("Emergency UI Triggered! Hiding main window...")
            if hasattr(self, '_window') and self._window:
                try:
                    self._window.hide()
                    print("Main window hidden.")
                except Exception as e:
                    print(f"Note: Could not hide window: {e}")

            url = f"http://127.0.0.1:{self.emergency_port}/index.html?safe_mode=1"
            webbrowser.open(url)
            print(f"Emergency UI opened in browser: {url}")

        keyboard.add_hotkey('ctrl+shift+f10', trigger)

    def get_active_modules(self):
        if not self._tracker: return {}
        t = self._tracker
        cfg = t.config
        
        modules = {
            "Biome Detection": { "active": t.detection_running, "enabled": True },
            "Aura Detection": { "active": t.detection_running and bool(cfg.get("enable_aura_detection", False)), "enabled": bool(cfg.get("enable_aura_detection", False)) },
            "Fishing Mode": { "active": t.detection_running and self._is_fishing_mode_enabled(), "enabled": bool(cfg.get("fishing_mode", False)) },
            "Auto Pop Buff": { "active": bool(getattr(t, "auto_pop_state", False)), "enabled": True },
            "Anti-AFK": { "active": t.detection_running and bool(cfg.get("anti_afk", True)), "enabled": bool(cfg.get("anti_afk", True)) },
            "Auto Merchant": { "active": bool(getattr(t, "on_auto_merchant_state", False)), "enabled": bool(cfg.get("merchant_teleporter", False)) },
            "BR / SC Sequence": { "active": bool(getattr(t, "_br_sc_running", False)), "enabled": bool(cfg.get("biome_randomizer", False)) or bool(cfg.get("strange_controller", False)) },
            "Eden Path": { "active": bool(getattr(t, "_eden_running", False)), "enabled": bool(cfg.get("go_to_eden_spawn", False)) },
            "Auto Eden Contract": { "active": bool(getattr(t, "_eden_running", False)), "enabled": bool(cfg.get("auto_eden_contract", False)) },
            "Egg Pathing": { "active": bool(getattr(t, "_egg_collecting", False)), "enabled": bool(cfg.get("collect_easter_egg", False)) },
            "Basic Obby": { "active": bool(getattr(t, "_obby_running", False)), "enabled": bool(cfg.get("enable_auto_obby", False)) },
            "Daily Quests": { "active": t.detection_running and bool(cfg.get("auto_claim_daily_quests", False)), "enabled": bool(cfg.get("auto_claim_daily_quests", False)) },
            "Potion Crafting": { "active": bool(getattr(t, "_potion_thread_active", False)), "enabled": bool(cfg.get("enable_potion_crafting", False)) },
            "Macro Idle Mode": { "active": bool(cfg.get("enable_idle_mode", False)), "enabled": bool(cfg.get("enable_idle_mode", False)) },
        }
        
        incompatibilities = []
        if cfg.get("enable_idle_mode", False):
            incompatibilities.append("Idle Mode is ON: Most automated actions are paused infinitely.")
        
        if cfg.get("go_to_eden_spawn", False) and bool(cfg.get("fishing_mode", False)):
            incompatibilities.append("Conflict: Both Eden Path and Fishing Mode are enabled. Fishing will take priority unless blocked.")

        if bool(cfg.get("enable_potion_crafting", False)) and bool(cfg.get("fishing_mode", False)):
            incompatibilities.append("Potion Crafting is enabled: It has the highest priority take over from Fishing Mode and cancels any automated actions.")

        return {
            "modules": modules,
            "incompatibilities": incompatibilities
        }

    def _is_fishing_mode_enabled(self):
        cfg = getattr(self._tracker, "config", None) if self._tracker else None
        if not isinstance(cfg, dict): return False
        if cfg.get("enable_idle_mode", False): return False
        return bool(cfg.get("fishing_mode", False))

    def _fishing_can_run(self):
        t = self._tracker
        if not t or not getattr(t, "detection_running", False): return False
        if not self._is_fishing_mode_enabled(): return False

        # pause during reconnect, but mark that we need to sell when we come back
        if getattr(t, "reconnecting_state", False):
            self._fishing_runtime_state["rejoin_in_progress"] = True
            return False
        if self._fishing_runtime_state.get("rejoin_in_progress"):
            self._fishing_runtime_state["rejoin_in_progress"] = False
            self._fishing_runtime_state["force_sell_on_next_cycle"] = True

        _STALE_TIMEOUT = 240
        now = time.time()
        blocking_flags = ("_egg_collecting", "_egg_collection_pending", "auto_pop_state")
        any_blocking = False

        for flag_name in blocking_flags:
            if getattr(t, flag_name, False):
                ts_key = f"_fishing_block_ts_{flag_name}"
                first_seen = self._fishing_runtime_state.get(ts_key, 0)
                if first_seen == 0:
                    self._fishing_runtime_state[ts_key] = now
                    any_blocking = True
                elif (now - first_seen) >= _STALE_TIMEOUT:
                    setattr(t, flag_name, False)
                    self._fishing_runtime_state[ts_key] = 0
                    try:
                        t.append_log(
                            f"[FishingMode] Force cleared stale '{flag_name}' flag "
                            f"after {_STALE_TIMEOUT}s — was blocking fishing."
                        )
                    except Exception: pass
                else:
                    any_blocking = True
            else:
                ts_key = f"_fishing_block_ts_{flag_name}"
                if self._fishing_runtime_state.get(ts_key, 0): self._fishing_runtime_state[ts_key] = 0

        if any_blocking: return False
        return True

    def _fishing_config_provider(self):
        t = self._tracker
        if t and isinstance(getattr(t, "config", None), dict):
            return dict(t.config)
        return load_config()

    def _on_fishing_failsafe_timeout(self):
        if not self._tracker: return
        biome = str(getattr(self._tracker, "current_biome", "") or "").upper().strip()

        # dont kill roblox during a rare biome lol, wait for it to end
        from biome_tracker.base_support import rare_biomes
        if biome in rare_biomes:
            self._tracker._pending_fishing_failsafe_rejoin = True
            try:
                self._tracker.append_log(f"[FishingMode] Failsafe timed out during {biome}; delaying rejoin.")
                self._tracker.send_webhook_status(
                    f"Fishing failsafe timed out during {biome}. Rejoin delayed until biome ends.",
                    color=0xffcc00,
                )
            except Exception: pass
            return

        try: self._tracker.terminate_roblox_processes()
        except Exception as e: print(f"Fishing failsafe close Roblox failed: {e}")

        if not self._fishing_config_provider().get("auto_reconnect", False):
            self._emit_fishing_failsafe_warning(
                "Fishing failsafe timeout: Roblox closed after 60s with no minigame. "
                "Enable PS reconnect in Misc so it can recover automatically."
            )

    def _run_fishing_br_sc_sequence(self):
        if not self._tracker: return False
        t = self._tracker
        old_override = getattr(t, "_fishing_br_sc_override", False)
        t._fishing_br_sc_override = True
        ran = False
        try:
            try: t.activate_roblox_window()
            except Exception: pass

            try:
                t._use_br_sc_impl("strange controller")
                t.last_sc_time = datetime.now()
                ran = True
            except Exception as e:
                print(f"Fishing SC step failed: {e}")
            try:
                t._use_br_sc_impl("biome randomizer")
                t.last_br_time = datetime.now()
                ran = True
            except Exception as e:
                print(f"Fishing BR step failed: {e}")
        except Exception as e:
            print(f"Fishing BR/SC sequence failed: {e}")
        finally:
            t._fishing_br_sc_override = old_override
        return ran

    def _run_fishing_merchant_sequence(self):
        if not self._tracker: return False
        t = self._tracker
        self._fishing_runtime_state["merchant_requires_reset"] = False
        old_override = getattr(t, "_fishing_br_sc_override", False)
        t._fishing_br_sc_override = True
        ran = False
        try:
            try: t.activate_roblox_window()
            except Exception: pass

            merchant_fn = getattr(t, "_merchant_teleporter_impl", None)
            if not callable(merchant_fn):
                print("Fishing merchant sequence skipped: _merchant_teleporter_impl unavailable")
                return False

            # reuse the same merchant logic so we get buy, webhook, limbo, everything
            merchant_fn()
            ran = bool(getattr(t, "_last_merchant_sequence_ran", False))
            self._fishing_runtime_state["merchant_requires_reset"] = bool(
                getattr(t, "_last_merchant_sequence_requires_reset", False)
            )
            if ran: t.last_mt_time = datetime.now()
        except Exception as e:
            print(f"Fishing merchant sequence failed: {e}")
        finally:
            t._fishing_br_sc_override = old_override
        return ran

    def _start_fishing_worker(self) -> None:
        if not self._tracker:
            return
        with self._fishing_lock:
            if self._fishing_thread and self._fishing_thread.is_alive():
                return
            self._fishing_stop_event.clear()

            def _run_fishing():
                try:
                    from biome_tracker.fishing import run_fishing_loop
                    run_fishing_loop(
                        stop_event=self._fishing_stop_event,
                        can_run_cb=self._fishing_can_run,
                        config_provider=self._fishing_config_provider,
                        log_prefix="[FishingMode]",
                        print_start_stop=True,
                        on_failsafe_timeout=self._on_fishing_failsafe_timeout,
                        run_br_sc_sequence_cb=self._run_fishing_br_sc_sequence,
                        run_merchant_sequence_cb=self._run_fishing_merchant_sequence,
                        activate_roblox_cb=self._tracker.activate_roblox_window,
                        close_chat_fn=self._tracker.close_chat_if_open,
                        runtime_state=self._fishing_runtime_state,
                        set_fishing_busy_cb=lambda busy: setattr(self._tracker, "_fishing_busy", busy),
                        on_f2_pressed_cb=lambda: (self.set_biome_detection(False), self._emit_shortcut("STOP")),
                        egg_ocr_check_cb=self._tracker._perform_egg_ocr_check,
                        merchant_ocr_check_cb=getattr(self._tracker, "_scheduled_merchant_ocr_check", None),
                    )
                except Exception as e:
                    print(f"Fishing worker failed: {e}")

            self._fishing_thread = threading.Thread(target=_run_fishing, daemon=True)
            self._fishing_thread.start()

    def _stop_fishing_worker(self) -> None:
        with self._fishing_lock:
            self._fishing_stop_event.set()
            t = self._fishing_thread
            if t and t.is_alive():
                t.join(timeout=1.0)
            if not t or not t.is_alive():
                self._fishing_thread = None

    def set_biome_detection(self, enabled):
        if not self._tracker: return
        if enabled:
            if not self._tracker.detection_running:
                threading.Thread(target=self._tracker.start_detection, daemon=True).start()
            if self._is_fishing_mode_enabled():
                self._start_fishing_worker()
            else:
                self._stop_fishing_worker()
                try: self._tracker.start_potion_crafting()
                except Exception: pass
        else:
            self._stop_fishing_worker()
            self._tracker.stop_detection()
        self._emit_macro_status()

    # --- frontend event emitters (JS bridge) ---

    def _safe_eval_js(self, js_code):
        if not self._window: return
        try:
            self._window.evaluate_js(js_code)
        except Exception: pass

    def _emit_macro_status(self):
        self._safe_eval_js(f'if(window.onMacroStatus) window.onMacroStatus("{self.get_macro_status()}");')

    def _emit_config_update(self):
        self._safe_eval_js('if(window.onConfigUpdated) window.onConfigUpdated();')

    def _emit_biome_update(self, biome):
        self._safe_eval_js(f'if(window.onBiomeUpdate) window.onBiomeUpdate("{biome}");')

    def _emit_shortcut(self, key):
        self._safe_eval_js(f'if(window.onShortcutEvent) window.onShortcutEvent("{key}");')

    def _emit_update_available(self, version, url):
        self._safe_eval_js(f'if(window.onUpdateAvailable) window.onUpdateAvailable("{version}", "{url}");')

    def _emit_update_status(self, status):
        self._safe_eval_js(f'if(window.onUpdateStatus) window.onUpdateStatus("{status}");')

    def _emit_fishing_failsafe_warning(self, msg):
        self._safe_eval_js(f"if(window.onFishingFailsafeWarning) window.onFishingFailsafeWarning({json.dumps(str(msg))});")

    def _request_biome_confirm(self, biome: str):
        self._biome_confirm_evt.clear()
        self._biome_confirm_result = None
        popup_window = None
        try:
            print(f"[BiomeConfirm] Spawning independent popup for biome: {biome}")
            fe = get_frontend_entry()
            popup_w, popup_h = 480, 400
            try:
                screen_w = win32api.GetSystemMetrics(0)
                screen_h = win32api.GetSystemMetrics(1)
                popup_x = (screen_w - popup_w) // 2
                popup_y = (screen_h - popup_h) // 2
            except Exception:
                popup_x, popup_y = 300, 200

            win_kwargs = {
                "title": f"\u26a0\ufe0f Rare Biome Detected \u2014 {biome} \u26a0\ufe0f",
                "js_api": self,
                "width": popup_w,
                "height": popup_h,
                "x": popup_x,
                "y": popup_y,
                "resizable": False,
            }

            if fe and "html" in fe:
                injected_script = f'''<script>
                const _OrigSearchParams = window.URLSearchParams;
                window.URLSearchParams = class extends _OrigSearchParams {{
                    constructor(init) {{
                        if (init === window.location.search || !init) {{
                            init = "?window=biome_confirm&biome={biome}";
                        }}
                        super(init);
                    }}
                }};
                </script>'''
                html = fe["html"].replace("<head>", f"<head>{injected_script}", 1)
                win_kwargs["html"] = html
            else:
                base = fe["url"] if fe else "http://localhost:5173"
                sep = "&" if "?" in base else "?"
                win_kwargs["url"] = f"{base}{sep}window=biome_confirm&biome={biome}"

            popup_window = webview.create_window(**win_kwargs)

            try:
                def _flash():
                    time.sleep(1.0)
                    try:
                        hwnd = win32gui.FindWindow(None, f"⚠️ Rare Biome Detected — {biome} ⚠️")
                        if hwnd:
                            win32gui.FlashWindowEx(hwnd, win32con.FLASHW_ALL | win32con.FLASHW_TIMERNOFG, 5, 0)
                    except Exception:
                        pass
                threading.Thread(target=_flash, daemon=True).start()
            except Exception:
                pass

        except Exception as e:
            print(f"[BiomeConfirm] Failed to create popup window: {e}")
            return None

        responded = self._biome_confirm_evt.wait(timeout=10)

        # Close the popup window
        try:
            if popup_window:
                popup_window.destroy()
        except Exception:
            pass

        if not responded:
            return None
        return self._biome_confirm_result

    def confirm_biome_response(self, confirmed: bool):
        self._biome_confirm_result = bool(confirmed)
        self._biome_confirm_evt.set()

    def apply_update(self, download_url: str, version: str = ""):
        if self._tracker:
            def _do_update():
                try:
                    self._emit_update_status("downloading")
                    self._tracker.download_and_apply_update(download_url, version=version)
                except Exception as e:
                    self._emit_update_status("failed")
            threading.Thread(target=_do_update, daemon=True).start()
            return True
        return False

    def check_for_updates(self):
        if not self._tracker:
            return False

        def _do_check():
            try:
                self._tracker.check_for_updates()
            except Exception as e:
                print(f"Update check failed: {e}")

        threading.Thread(target=_do_check, daemon=True).start()
        return True

    def get_update_available(self):
        if not self._tracker:
            return None
        try:
            latest_release = self._tracker._fetch_latest_release()
            if not isinstance(latest_release, dict):
                return None

            latest_version = str(latest_release.get("tag_name", "")).strip()
            if not latest_version:
                return None
            if self._tracker._is_same_version(latest_version, current_version):
                return None

            _asset_name, download_url = self._tracker._pick_update_exe_asset(latest_release)
            if not download_url:
                return None

            return {"version": latest_version, "url": download_url}
        except Exception as e:
            print(f"Direct update query failed: {e}")
            return None

    def send_webhook_status(self, status: str, color: int):
        if self._tracker and hasattr(self._tracker, 'send_webhook_status'):
            self._tracker.send_webhook_status(status, color)

    def check_winocr_status(self):
        try:
            import winocr
            return {"installed": True, "version": getattr(winocr, "__version__", "unknown")}
        except ImportError:
            return {"installed": False, "version": None}
        except Exception as e:
            return {"installed": False, "version": None, "error": str(e)}

    def test_webhook(self, url): return True  # placeholder

    def get_recorder_status(self):
        return getattr(self._tracker, "_is_recording", False) if self._tracker else False

    def start_macro_recording(self):
        if self._tracker: self._tracker.start_recording_path()

    def stop_macro_recording(self):
        if self._tracker: return self._tracker.stop_recording_path("obby", save_dir="paths")
        return "No tracker"

    def stop_macro_recording_potion(self, name: str):
         if self._tracker:
             return self._tracker.stop_recording_path(name, save_dir="crafting_files_do_not_open")
         return "No tracker"

    def _get_frontend_url(self):
         res = get_frontend_entry()
         return res["url"] if res else "http://localhost:5173"

    def _open_recorder(self, mode: str = "obby"):
         fe = get_frontend_entry()
         query = "window=recorder"
         if mode == "potion":
             query += "&mode=potion"
         title = "Potion Recorder" if mode == "potion" else "Obby Recorder"

         win_kwargs = {
             "title": title,
             "js_api": self,
             "width": 380,
             "height": 320,
             "resizable": True,
             "on_top": True,
         }

         if "html" in fe:
             injected_script = f'''<script>
             const _OrigSearchParams = window.URLSearchParams;
             window.URLSearchParams = class extends _OrigSearchParams {{
                 constructor(init) {{
                     if (init === window.location.search || !init) {{
                         init = "?{query}";
                     }}
                     super(init);
                 }}
             }};
             </script>'''
             html = fe["html"].replace("<head>", f"<head>{injected_script}", 1)
             win_kwargs["html"] = html
         else:
             base = fe["url"]
             sep = "&" if "?" in base else "?"
             win_kwargs["url"] = f"{base}{sep}{query}"

         webview.create_window(**win_kwargs)

    def open_recorder_window(self):
         self._open_recorder("obby")

    def open_recorder_window_potion(self):
         self._open_recorder("potion")

    def list_potion_files(self):
         try:
             rec_dir = "crafting_files_do_not_open"
             if os.path.isdir(rec_dir):
                 return sorted([f for f in os.listdir(rec_dir) if f.lower().endswith(".json")])
         except Exception:
             pass
         return []

    def check_obby_path_exists(self):
        try:
            obby_file = os.path.join(os.getcwd(), "paths", "obby.json")
            if not os.path.isfile(obby_file):
                return False
            with open(obby_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data)
        except Exception:
            return False

    def replay_recording(self):
         if self._tracker:
             return self._tracker.replay_path_recording("obby", save_dir="paths")
         return "No tracker"

    def replay_potion_recording(self, name: str):
         if self._tracker:
             return self._tracker.replay_path_recording(name, save_dir="crafting_files_do_not_open")
         return "No tracker"

    def test_aura_keybind(self):
         if self._tracker:
             def test_record():
                 try:
                    keybind = self._tracker.aura_record_keybind_var.get()
                    if not keybind: return
                    keys = [key.strip() for key in keybind.split('+')]
                    time.sleep(2)
                    pyautogui.hotkey(*keys)
                 except Exception as e:
                    print(f"Error testing aura keybind: {e}")
             threading.Thread(target=test_record, daemon=True).start()

    def test_biome_keybind(self):
         if self._tracker:
             def test_record():
                 try:
                    keybind = self._tracker.rarest_biome_keybind_var.get()
                    if not keybind: return
                    keys = [key.strip() for key in keybind.split('+')]
                    time.sleep(2)
                    pyautogui.hotkey(*keys)
                 except Exception as e:
                    print(f"Error testing biome keybind: {e}")
             threading.Thread(target=test_record, daemon=True).start()

    def align_camera(self):
         if self._tracker:
             self._tracker.align_camera()

    def emit_calibration_result(self, data):
         if self._window:
             js_data = json.dumps(data)
             self._window.evaluate_js(
                 f"if(window.onCalibrationResult) window.onCalibrationResult({js_data});"
                 f"if(window.onCalibrationResultMisc) window.onCalibrationResultMisc({js_data});"
             )

    def create_calibration_window(self, key="unknown", window_type="point"):
        self._calib_mgr.request_calibration(config_key=key, window_type=window_type)

    def display_calibration_on_screen(self, key: str, label: str = "", duration_ms: int = 2500):
        try:
            self._calib_mgr.request_display(
                config_key=key,
                label=label or key,
                duration_ms=duration_ms
            )
            return True
        except Exception:
            return False

    def display_all_fishing_calibrations_on_screen(self, duration_ms: int = 3000):
        try:
            cfg = self.get_config() if callable(getattr(self, "get_config", None)) else {}
            if not isinstance(cfg, dict):
                cfg = {}

            items = [
                {"key": "fishing_detect_pixel", "label": "Fishing Detect Pixel", "value": cfg.get("fishing_detect_pixel", [1176, 836])},
                {"key": "fishing_click_position", "label": "Start Fishing Button", "value": cfg.get("fishing_click_position", [862, 843])},
                {"key": "fishing_midbar_sample_pos", "label": "Mid Bar Sample Position", "value": cfg.get("fishing_midbar_sample_pos", [955, 767])},
                {"key": "fishing_close_button_pos", "label": "Fishing Close Button", "value": cfg.get("fishing_close_button_pos", [1113, 342])},
                {"key": "fishing_bar_region", "label": "Fishing Bar Region", "value": cfg.get("fishing_bar_region", [757, 762, 405, 21])},
                {"key": "fishing_flarg_dialogue_box", "label": "Captain Flarg Dialogue Box", "value": cfg.get("fishing_flarg_dialogue_box", [1046, 782])},
                {"key": "fishing_shop_open_button", "label": "Open Fishing Shop", "value": cfg.get("fishing_shop_open_button", [616, 938])},
                {"key": "fishing_shop_sell_tab", "label": "Fishing Shop Sell Tab", "value": cfg.get("fishing_shop_sell_tab", [1285, 312])},
                {"key": "fishing_shop_close_button", "label": "Close Fishing Shop", "value": cfg.get("fishing_shop_close_button", [1458, 269])},
                {"key": "fishing_shop_first_fish", "label": "First Fish In Shop", "value": cfg.get("fishing_shop_first_fish", [827, 404])},
                {"key": "fishing_shop_sell_all_button", "label": "Sell All Button", "value": cfg.get("fishing_shop_sell_all_button", [662, 799])},
                {"key": "fishing_confirm_sell_all_button", "label": "Confirm Sell All Button", "value": cfg.get("fishing_confirm_sell_all_button", [800, 619])},
            ]
            self._calib_mgr.request_display_many(items=items, duration_ms=duration_ms)
            return True
        except Exception:
            return False


def launch_app(api_class, tracker=None):
    tracker = tracker or BiomeTracker()
    api = api_class(tracker)
    tracker.on_stats_update = api._emit_config_update
    tracker.on_biome_update = api._emit_biome_update
    tracker.on_update_available = api._emit_update_available
    tracker.on_update_status = api._emit_update_status
    tracker.on_biome_confirm_request = api._request_biome_confirm
    tracker.on_status_change = lambda status: api._emit_macro_status()

    fe = get_frontend_entry()
    win_args = {
        "title": f"Coteab Macro {current_version}",
        "js_api": api,
        "width": 985, "height": 550,
        "min_size": (550, 500),
        "resizable": True, "frameless": False
    }
    if fe and "html" in fe: win_args["html"] = fe["html"]
    else: win_args["url"] = fe["url"] if fe else "http://localhost:5173"

    window = webview.create_window(**win_args)
    api.set_window(window)

    # F1 = start, F2 = stop
    _VK_F1 = 0x70
    _VK_F2 = 0x71
    _hotkey_stop = threading.Event()
    _user32 = ctypes.windll.user32

    def _hotkey_poll_loop():
        f1_was = False
        f2_was = False
        while not _hotkey_stop.is_set():
            try:
                f1_now = bool(_user32.GetAsyncKeyState(_VK_F1) & 0x8000)
                f2_now = bool(_user32.GetAsyncKeyState(_VK_F2) & 0x8000)

                if f1_now and not f1_was:
                    def _do_start():
                        try:
                            if not api._tracker.detection_running:
                                api.set_biome_detection(True)
                                api._emit_shortcut("START")
                        except Exception:
                            pass
                    threading.Thread(target=_do_start, daemon=True).start()

                if f2_now and not f2_was:
                    def _do_stop():
                        try:
                            if api._tracker.detection_running:
                                api.set_biome_detection(False)
                                api._emit_shortcut("STOP")
                        except Exception:
                            pass
                    threading.Thread(target=_do_stop, daemon=True).start()

                f1_was = f1_now
                f2_was = f2_now
            except Exception:
                pass
            _hotkey_stop.wait(0.05)

    _hotkey_thread = threading.Thread(target=_hotkey_poll_loop, name="HotkeyPoll", daemon=True)
    _hotkey_thread.start()

    class _WvLog(logging.Handler):
        def emit(self, record):
            try: tracker.append_log(f"[pywebview] {record.getMessage()}")
            except Exception: pass
    logging.getLogger("pywebview").addHandler(_WvLog())

    # try edgechromium first, fall back to whatever else is available
    try:
        tracker.append_log("Starting pywebview (edgechromium)")
        webview.start(debug=False, gui="qt", private_mode=False)
    except Exception as e:
        print(f"[Webview] edgechromium failed: {e}")
        tracker.append_log(f"edgechromium failed: {e}, retrying default...")
        try: webview.start(debug=False, private_mode=False)
        except Exception as e2:
            print(f"[Webview] Default backend also failed: {e2}")
            tracker.append_log(f"Default backend also failed: {e2}")

    return tracker

def stop_app(tracker):
    if tracker and getattr(tracker, "detection_running", False): tracker.stop_detection()

def main():
    ensure_workspace_files()
    tracker = None
    api = Api(tracker=None)
    api._setup_emergency_server()
    api._setup_emergency_hotkey()
    try:
        fe = get_frontend_entry()
        win_args = {
            "title": f"Coteab Macro {current_version}",
            "js_api": api,
            "width": 985, "height": 550,
            "min_size": (550, 500),
            "resizable": True, "frameless": False,
        }
        if "html" in fe: win_args["html"] = fe["html"]
        else: win_args["url"] = fe["url"]

        window = webview.create_window(**win_args)
        api._window = window

        def _background_init():
            nonlocal tracker
            try:
                from biome_tracker.core import BiomeTracker
                tracker = BiomeTracker()
                canonical = _read_cli_value("--coteab-target", "CoteabMacro.exe")
                old_pid_raw = _read_cli_value("--coteab-old-pid", "")
                try: old_pid = int(old_pid_raw) if old_pid_raw else None
                except Exception: old_pid = None

                if tracker.maybe_self_rename_to_canonical_exe(canonical, old_pid=old_pid):
                    window.destroy()
                    return

                # Automatic updater disabled for this custom overlay build.
                # The upstream updater can replace this build with an older official EXE.
                try:
                    tracker.config["auto_update_enabled"] = False
                except Exception:
                    pass


                api._tracker = tracker
                tracker.on_stats_update = api._emit_config_update
                tracker.on_biome_update = api._emit_biome_update
                tracker.on_update_available = api._emit_update_available
                tracker.on_update_status = api._emit_update_status
                tracker.on_biome_confirm_request = api._request_biome_confirm
                tracker.on_status_change = lambda status: api._emit_macro_status()
                tracker.on_remote_start = lambda: api.set_biome_detection(True)
                tracker.on_remote_stop = lambda: api.set_biome_detection(False)
                api.set_window(window)
                overlay_settings = api.get_native_overlay_settings()
                if bool(overlay_settings.get("enabled", False)):
                    api.show_overlay(overlay_settings.get("position", "top-right"))

            except Exception as exc:
                print(f"Background init error: {exc}")
                traceback.print_exc()

        # ---- F1/F2 hotkeys ----
        _VK_F1 = 0x70
        _VK_F2 = 0x71
        _hotkey_stop = threading.Event()
        _user32 = ctypes.windll.user32

        def _hotkey_poll_loop():
            f1_was = False
            f2_was = False
            while not _hotkey_stop.is_set():
                try:
                    if api._tracker is None:
                        _hotkey_stop.wait(0.2)
                        continue

                    f1_now = bool(_user32.GetAsyncKeyState(_VK_F1) & 0x8000)
                    f2_now = bool(_user32.GetAsyncKeyState(_VK_F2) & 0x8000)

                    if f1_now and not f1_was:
                        def _do_start():
                            try:
                                if not api._tracker.detection_running:
                                    api.set_biome_detection(True)
                                    api._emit_shortcut("START")
                            except Exception:
                                pass
                        threading.Thread(target=_do_start, daemon=True).start()

                    if f2_now and not f2_was:
                        def _do_stop():
                            try:
                                if api._tracker.detection_running:
                                    api.set_biome_detection(False)
                                    api._emit_shortcut("STOP")
                            except Exception:
                                pass
                        threading.Thread(target=_do_stop, daemon=True).start()

                    f1_was = f1_now
                    f2_was = f2_now
                except Exception:
                    pass
                _hotkey_stop.wait(0.05)

        threading.Thread(target=_hotkey_poll_loop, name="HotkeyPoll", daemon=True).start()

        class _WvLog(logging.Handler):
            def emit(self, record):
                try:
                    if tracker: tracker.append_log(f"[pywebview] {record.getMessage()}")
                except Exception: pass
        logging.getLogger("pywebview").addHandler(_WvLog())

        try:
            webview.start(func=_background_init, debug=False, gui="qt", private_mode=False)
        except Exception as e:
            print(f"[Webview] edgechromium failed: {e}")
            try: webview.start(func=_background_init, debug=False, private_mode=False)
            except Exception as e2:
                print(f"[Webview] Default backend also failed: {e2}")

        return 0

    except KeyboardInterrupt:
        print("Exited (Ctrl+C)")
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}")
        traceback.print_exc()
        return 1
    finally:
        # webview.start returns when the main window is closed. Always stop the
        # child overlay process, including closes performed with the title-bar X.
        try: api.hide_overlay()
        except Exception: pass
        try: stop_app(tracker)
        except Exception: pass
        try: sync_config()
        except Exception: pass
        try: _hotkey_stop.set()
        except Exception: pass


if __name__ == "__main__":
    raise SystemExit(main())