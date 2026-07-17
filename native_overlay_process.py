
import ctypes
import json
import sys
import os
from ctypes import wintypes
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required. Run: py -3.12 -m pip install pillow")
    raise

if sys.platform != "win32":
    raise SystemExit("This test only works on Windows.")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Pointer-sized Win32 types for Python 3.12 compatibility
LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
HINSTANCE = wintypes.HINSTANCE
HWND = wintypes.HWND
HDC = wintypes.HDC
HBITMAP = wintypes.HBITMAP
HGDIOBJ = wintypes.HGDIOBJ
UINT = wintypes.UINT
DWORD = wintypes.DWORD
LONG = wintypes.LONG
BOOL = wintypes.BOOL
BYTE = ctypes.c_ubyte

WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
GWL_EXSTYLE = -20
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
SW_SHOW = 5

WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_NCHITTEST = 0x0084
WM_SIZE = 0x0005
WM_MOVE = 0x0003
WM_EXITSIZEMOVE = 0x0232
WM_KEYDOWN = 0x0100
WM_MOUSEWHEEL = 0x020A
WM_LBUTTONDOWN = 0x0201
WM_TIMER = 0x0113

VK_ESCAPE = 0x1B
VK_UP = 0x26
VK_DOWN = 0x28
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

BI_RGB = 0
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020

MIN_W = 300
MIN_H = 190
EDGE = 10
RADIUS = 20

OVERLAY_DIR = Path(os.environ.get("COTEAB_OVERLAY_DIR", Path(__file__).resolve().parent))
OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = OVERLAY_DIR / "native_overlay_config.json"
STATE_PATH = OVERLAY_DIR / "overlay_runtime_state.json"
SETTINGS_PATH = Path(__file__).with_name("overlay_settings.json")


class POINT(ctypes.Structure):
    _fields_ = [("x", LONG), ("y", LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", LONG), ("cy", LONG)]


class RECT(ctypes.Structure):
    _fields_ = [("left", LONG), ("top", LONG), ("right", LONG), ("bottom", LONG)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", BYTE),
        ("BlendFlags", BYTE),
        ("SourceConstantAlpha", BYTE),
        ("AlphaFormat", BYTE),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", DWORD * 3)]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", UINT),
        ("style", UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


def loword(value):
    return ctypes.c_short(value & 0xFFFF).value


def hiword(value):
    return ctypes.c_short((value >> 16) & 0xFFFF).value


def load_config():
    data = {"x": 120, "y": 120, "width": 380, "height": 300, "bg_alpha": 150}
    try:
        if CONFIG_PATH.exists():
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            data.update({k: int(loaded[k]) for k in data if k in loaded})
    except Exception:
        pass
    return data


def save_config(hwnd, bg_alpha):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    data = {
        "x": rect.left, "y": rect.top,
        "width": rect.right - rect.left, "height": rect.bottom - rect.top,
        "bg_alpha": bg_alpha,
    }
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        settings = {}
        if SETTINGS_PATH.exists():
            loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict): settings = loaded
        if bool(settings.get("remember_position", True)):
            settings.update({"x": data["x"], "y": data["y"], "width": data["width"], "height": data["height"], "position": "custom"})
            tmp = SETTINGS_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
            tmp.replace(SETTINGS_PATH)
    except Exception:
        pass


def get_font(size, bold=False, family="Inter"):
    family = str(family or "Inter").lower()
    choices = {
        "sarpanch": [r"frontend\public\fonts\sarpanch-700.ttf", r"C:\Windows\Fonts\seguisb.ttf"],
        "orbitron": [r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\seguisb.ttf"],
        "jetbrains mono": [r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\consola.ttf"],
        "exo 2": [r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\seguisb.ttf"],
        "poppins": [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
        "rounded": [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
        "inter": [r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"],
    }
    candidates = choices.get(family, choices["inter"])
    if bold and family not in {"sarpanch", "orbitron", "monospace"}:
        candidates = [r"C:\Windows\Fonts\seguisb.ttf", *candidates]
    base = Path(__file__).resolve().parent
    for item in candidates:
        path = Path(item)
        if not path.is_absolute():
            path = base / path
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    return ImageFont.load_default()


def parse_hex(value, fallback=(174, 184, 255)):
    try:
        text = str(value).strip().lstrip("#")
        if len(text) == 6:
            return tuple(int(text[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        pass
    return fallback


def theme_palette(name):
    themes = {
        "midnight": ((17,24,39), (15,23,42), (156,163,175), (249,250,251), (99,102,241)),
        "crimson": ((42,13,22), (31,8,16), (211,154,169), (255,244,247), (244,63,94)),
        "emerald": ((8,36,29), (5,28,22), (148,201,183), (239,255,249), (16,185,129)),
        "solar": ((43,30,9), (32,22,6), (214,188,132), (255,250,235), (245,158,11)),
        "frost": ((9,31,45), (6,24,36), (150,194,218), (240,250,255), (56,189,248)),
        "amoled": ((3,3,4), (0,0,0), (160,160,170), (255,255,255), (139,92,246)),
        "ocean": ((7,24,39), (4,18,32), (125,185,220), (240,250,255), (14,165,233)),
        "glass": ((20,25,35), (15,20,30), (185,195,210), (255,255,255), (148,163,184)),
        "neon": ((10,8,24), (5,3,16), (190,170,235), (255,255,255), (217,70,239)),
        "discord": ((43,45,49), (35,36,40), (181,186,193), (248,249,250), (88,101,242)),
        "spotify": ((12,20,15), (8,14,10), (168,190,175), (255,255,255), (29,185,84)),
    }
    return themes.get(str(name).lower(), themes["midnight"])


def load_runtime_state():
    data = {
        "status": "STOPPED",
        "session": "00:00:00",
        "biome": "NORMAL",
        "last_aura": "None",
        "aura_rarity": "Unknown",
        "last_merchant": "None",
        "last_merchant_detected_at": 0,
        "minimum_rarity": 1,
        "transparency": 0.35,
        "theme": "midnight",
        "accent": "#aeb8ff",
        "font": "Inter",
        "layout": "expanded",
        "position": "top-right",
        "width": 380,
        "height": 300,
        "show_status": True,
        "biome": True,
        "aura": True,
        "rarity": True,
        "merchant": True,
        "merchant_time": True,
        "time": True,
        "session": True,
    }
    try:
        if STATE_PATH.exists():
            loaded = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
    except Exception:
        pass
    return data


class Overlay:
    def __init__(self):
        self.cfg = load_config()
        self.bg_alpha = max(30, min(230, self.cfg["bg_alpha"]))
        self.hwnd = None
        self.class_name = "CoteabNativeOverlayStep8"
        self._wndproc = WNDPROC(self.wndproc)
        self._last_requested_position = None
        self._last_requested_size = None
        self.scroll_offset = 0
        self._last_click_through = None
        self._last_always_on_top = None
        self._seen_biome = None
        self._seen_aura = None
        self._seen_merchant = None
        self.biome_count = 0
        self.merchant_count = 0
        self.notice_text = ""
        self.notice_until = 0.0

    def create(self):
        hinstance = kernel32.GetModuleHandleW(None)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 0
        wc.lpfnWndProc = self._wndproc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = None
        wc.hCursor = user32.LoadCursorW(None, 32512)  # IDC_ARROW
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = self.class_name
        wc.hIconSm = None

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom and ctypes.get_last_error() != 1410:
            raise ctypes.WinError()

        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
            self.class_name,
            "Coteab Native Overlay",
            WS_POPUP | WS_VISIBLE,
            self.cfg["x"],
            self.cfg["y"],
            max(MIN_W, self.cfg["width"]),
            max(MIN_H, self.cfg["height"]),
            None,
            None,
            hinstance,
            None,
        )
        if not self.hwnd:
            raise ctypes.WinError()

        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.SetForegroundWindow(self.hwnd)
        self.render()
        user32.SetTimer(self.hwnd, 1, 500, None)

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TIMER:
            runtime = load_runtime_state()
            self.apply_runtime_geometry(runtime)
            self.apply_window_options(runtime)
            self.render()
            return 0

        if msg == WM_DESTROY:
            save_config(hwnd, self.bg_alpha)
            user32.PostQuitMessage(0)
            return 0

        if msg == WM_KEYDOWN:
            if wparam == VK_ESCAPE:
                user32.DestroyWindow(hwnd)
                return 0
            if wparam in (VK_UP, VK_ADD, VK_OEM_PLUS):
                self.bg_alpha = min(230, self.bg_alpha + 15)
                self.render()
                save_config(hwnd, self.bg_alpha)
                return 0
            if wparam in (VK_DOWN, VK_SUBTRACT, VK_OEM_MINUS):
                self.bg_alpha = max(30, self.bg_alpha - 15)
                self.render()
                save_config(hwnd, self.bg_alpha)
                return 0


        if msg == WM_MOUSEWHEEL:
            runtime = load_runtime_state()
            if bool(runtime.get("scrollable", True)):
                delta = hiword(wparam)
                self.scroll_offset = max(0, self.scroll_offset + (-1 if delta > 0 else 1))
                self.render()
            return 0

        if msg == WM_NCHITTEST:
            x = loword(lparam)
            y = hiword(lparam)
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            local_x = x - rect.left
            local_y = y - rect.top

            left = local_x <= EDGE
            right = local_x >= width - EDGE
            top = local_y <= EDGE
            bottom = local_y >= height - EDGE

            if top and left:
                return HTTOPLEFT
            if top and right:
                return HTTOPRIGHT
            if bottom and left:
                return HTBOTTOMLEFT
            if bottom and right:
                return HTBOTTOMRIGHT
            if left:
                return HTLEFT
            if right:
                return HTRIGHT
            if top:
                return HTTOP
            if bottom:
                return HTBOTTOM

            # Top header moves the window.
            if local_y <= 48:
                return HTCAPTION
            return HTCLIENT

        if msg == WM_SIZE:
            width = loword(lparam)
            height = hiword(lparam)
            if width >= MIN_W and height >= MIN_H:
                self.render(width, height)
            return 0

        if msg == WM_EXITSIZEMOVE:
            save_config(hwnd, self.bg_alpha)
            self.render()
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


    def apply_window_options(self, runtime):
        try:
            always = bool(runtime.get("always_on_top", True))
            if always != self._last_always_on_top:
                user32.SetWindowPos(self.hwnd, HWND_TOPMOST if always else HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                self._last_always_on_top = always
            click = bool(runtime.get("click_through", False))
            if click != self._last_click_through:
                exstyle = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
                if click: exstyle |= WS_EX_TRANSPARENT
                else: exstyle &= ~WS_EX_TRANSPARENT
                user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, exstyle)
                self._last_click_through = click
        except Exception:
            pass

    def apply_runtime_geometry(self, runtime):
        try:
            rect = RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            cur_w, cur_h = rect.right - rect.left, rect.bottom - rect.top
            wanted_w = max(MIN_W, min(900, int(runtime.get("width", cur_w) or cur_w)))
            wanted_h = max(MIN_H, min(700, int(runtime.get("height", cur_h) or cur_h)))
            position = str(runtime.get("position", "custom")).lower()
            requested_size = (wanted_w, wanted_h)
            position_changed = position != self._last_requested_position
            size_changed = requested_size != self._last_requested_size
            if not position_changed and not size_changed:
                return
            x, y = rect.left, rect.top
            if position in {"top-right", "bottom-right"}:
                work = RECT()
                SPI_GETWORKAREA = 0x0030
                user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work), 0)
                margin = 18
                x = work.right - wanted_w - margin
                y = work.top + margin if position == "top-right" else work.bottom - wanted_h - margin
            elif position == "custom":
                x = int(runtime.get("x", rect.left) or rect.left)
                y = int(runtime.get("y", rect.top) or rect.top)
            if (x, y, wanted_w, wanted_h) != (rect.left, rect.top, cur_w, cur_h):
                user32.SetWindowPos(self.hwnd, -1, x, y, wanted_w, wanted_h, 0x0010)
            self._last_requested_position = position
            self._last_requested_size = requested_size
        except Exception:
            pass

    def render(self, width=None, height=None):
        if not self.hwnd:
            return

        if width is None or height is None:
            rect = RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top

        width = max(MIN_W, int(width))
        height = max(MIN_H, int(height))

        runtime = load_runtime_state()
        transparency = max(0.0, min(0.90, float(runtime.get("background_transparency", 0.35) or 0.0)))
        self.bg_alpha = max(26, min(245, int(round(255 * (1.0 - transparency)))))
        panel_rgb, header_rgb, muted_rgb, text_rgb, theme_accent = theme_palette(runtime.get("theme", "midnight"))
        accent_rgb = parse_hex(runtime.get("accent"), theme_accent)
        font_family = runtime.get("font", "Inter")
        compact = str(runtime.get("layout", "expanded")).lower() == "compact"

        # Fully transparent canvas. Only the rounded panel receives alpha.
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        panel = (0, 0, width - 1, height - 1)
        draw.rounded_rectangle(panel, radius=RADIUS,
            fill=(*panel_rgb, self.bg_alpha), outline=(*accent_rgb, 235), width=2)
        draw.rounded_rectangle((2, 2, width - 3, 48), radius=max(1, RADIUS - 2),
            fill=(*header_rgb, min(250, self.bg_alpha + 35)))
        draw.rectangle((2, 28, width - 3, 48), fill=(*header_rgb, min(250, self.bg_alpha + 35)))

        title_font = get_font(20, True, font_family)
        small_bold = get_font(12, True, font_family)
        label_font = get_font(13 if compact else 14, False, font_family)
        value_font = get_font(13 if compact else 14, True, font_family)
        hint_font = get_font(10, False, font_family)

        draw.text((16, 12), "COTEAB", font=title_font, fill=(*accent_rgb, 255))
        status = str(runtime.get("status", "STOPPED")).upper()
        if bool(runtime.get("show", {}).get("status", True)):
            status_color = (101,230,166) if status == "RUNNING" else (255,122,138)
            bbox = draw.textbbox((0, 0), status, font=small_bold)
            draw.text((width - (bbox[2] - bbox[0]) - 16, 18), status,
                      font=small_bold, fill=(*status_color, 255))

        biome = str(runtime.get("biome", "NORMAL") or "NORMAL").strip().upper()
        last_aura = str(runtime.get("last_aura", "None") or "None")
        aura_rarity = str(runtime.get("aura_rarity", "Unknown") or "Unknown")
        last_merchant = str(runtime.get("last_merchant", "None") or "None")
        try:
            merchant_ts = float(runtime.get("last_merchant_detected_at", 0) or 0)
        except (TypeError, ValueError):
            merchant_ts = 0
        if merchant_ts > 0:
            elapsed = max(0, int(__import__("time").time() - merchant_ts))
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            merchant_ago = f"{hours:d}:{minutes:02d}:{seconds:02d} ago" if hours else f"{minutes:d}:{seconds:02d} ago"
        else:
            merchant_ago = "Never"

        now = __import__("datetime").datetime.now()
        local_time = now.strftime("%I:%M %p").lstrip("0")
        day_period = "DAY" if 6 <= now.hour < 18 else "NIGHT"
        import time as _time
        notices = runtime.get("notifications", {}) if isinstance(runtime.get("notifications"), dict) else {}
        if self._seen_biome is None: self._seen_biome = biome
        elif biome != self._seen_biome:
            self._seen_biome = biome; self.biome_count += 1
            if notices.get("biome", True): self.notice_text=f"Biome changed: {biome}"; self.notice_until=_time.time()+4
        if self._seen_aura is None: self._seen_aura = last_aura
        elif last_aura not in {"None", ""} and last_aura != self._seen_aura:
            self._seen_aura = last_aura
            if notices.get("aura", True): self.notice_text=f"Aura found: {last_aura}"; self.notice_until=_time.time()+4
        if self._seen_merchant is None: self._seen_merchant = last_merchant
        elif last_merchant not in {"None", ""} and last_merchant != self._seen_merchant:
            self._seen_merchant = last_merchant; self.merchant_count += 1
            if notices.get("merchant", True): self.notice_text=f"Merchant detected: {last_merchant}"; self.notice_until=_time.time()+4

        row_map = {
            "biome": ("Biome", biome),
            "aura": ("Last Aura", last_aura),
            "rarity": ("Aura Rarity", aura_rarity),
            "merchant": ("Last Merchant", last_merchant),
            "merchant_time": ("Merchant Seen", merchant_ago),
            "time": ("Time", f"{local_time} · {day_period}"),
            "session": ("Session", str(runtime.get("session", "00:00:00"))),
            "biome_count": ("Biome Changes", str(self.biome_count)),
            "merchant_count": ("Merchants", str(self.merchant_count)),
        }
        order = runtime.get("row_order") if isinstance(runtime.get("row_order"), list) else list(row_map)
        rows=[]
        for flag in order:
            if flag in row_map and bool(runtime.get("show", {}).get(flag, True)):
                rows.append(row_map[flag])
        if compact: rows = rows[:4]
        max_offset = max(0, len(rows) - 1)
        self.scroll_offset = min(self.scroll_offset, max_offset)
        rows = rows[self.scroll_offset:]

        row_step = 25 if compact else 29
        y = 62
        available_bottom = height - 28
        for label, value in rows:
            if y + row_step > available_bottom:
                break
            draw.text((18, y), label, font=label_font, fill=(*muted_rgb, 255))
            max_value_width = max(80, int(width * 0.58))
            shown = value
            while shown and draw.textbbox((0,0), shown, font=value_font)[2] > max_value_width:
                shown = shown[:-1]
            if shown != value and len(shown) > 2:
                shown = shown[:-2] + "…"
            value_box = draw.textbbox((0, 0), shown, font=value_font)
            value_w = value_box[2] - value_box[0]
            draw.text((width - value_w - 18, y), shown, font=value_font, fill=(*text_rgb, 255))
            y += row_step

        if self.notice_text and __import__("time").time() < self.notice_until:
            notice_font = get_font(11, True, font_family)
            nb = draw.textbbox((0,0), self.notice_text, font=notice_font)
            nw = min(width-24, (nb[2]-nb[0])+24)
            draw.rounded_rectangle((width-nw-12, 52, width-12, 82), radius=10, fill=(*accent_rgb, 220))
            draw.text((width-nw, 60), self.notice_text, font=notice_font, fill=(255,255,255,255))
        hint = "Header: move · Edges: resize · Settings live-update"
        draw.text((18, height - 24), hint, font=hint_font, fill=(*muted_rgb, 220))

        # Windows layered windows expect premultiplied BGRA.
        r, g, b, a = img.split()
        import PIL.ImageChops as ImageChops
        r = ImageChops.multiply(r, a)
        g = ImageChops.multiply(g, a)
        b = ImageChops.multiply(b, a)
        premultiplied = Image.merge("RGBA", (b, g, r, a))
        raw = premultiplied.tobytes("raw", "RGBA")

        screen_dc = user32.GetDC(None)
        mem_dc = gdi32.CreateCompatibleDC(screen_dc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        bits = ctypes.c_void_p()
        hbitmap = gdi32.CreateDIBSection(
            mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS,
            ctypes.byref(bits), None, 0
        )
        old_bitmap = gdi32.SelectObject(mem_dc, hbitmap)
        ctypes.memmove(bits, raw, len(raw))

        rect = RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        dst = POINT(rect.left, rect.top)
        size = SIZE(width, height)
        src = POINT(0, 0)
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

        user32.UpdateLayeredWindow(
            self.hwnd,
            screen_dc,
            ctypes.byref(dst),
            ctypes.byref(size),
            mem_dc,
            ctypes.byref(src),
            0,
            ctypes.byref(blend),
            ULW_ALPHA,
        )

        gdi32.SelectObject(mem_dc, old_bitmap)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(None, screen_dc)


if __name__ == "__main__":
    Overlay().create()
