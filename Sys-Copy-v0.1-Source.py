"""
App Name: Sys Copy
Version: 0.1
Created by: Genie Codebase [GC]
Description: Live Windows system diagnostics, hardware/OS details, installed apps,
             Python PIP packages, PATH, and environment variables extractor with
             one-click formatted clipboard copy and auto Windows Dark/Light theme.
"""

import ctypes
import datetime
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser
import winreg


APP_NAME = "Sys Copy"
APP_VERSION = "0.1"
CREATED_BY = "Genie Codebase [GC]"
REPO_URL = "https://github.com/GenieCodebase/Sys-Copy"
YOUTUBE_URL = "https://youtube.com/@geniecodebase?si=l6ZkbBJPVl7Cv4U2"
APP_USER_MODEL_ID = "GenieCodebase.SysCopy.0_1"
ICON_FILENAME = "icon.png"
APP_DESCRIPTION = (
    "Live Windows system & hardware diagnostics, installed apps, Python PIP list, "
    "System/User PATH, and Environment Variables extractor with instant formatted "
    "clipboard copy."
)

WINDOW_WIDTH = 400
WINDOW_HEIGHT = 625

SECRET_ENV_KEYWORDS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASS",
    "PWD",
    "AUTH",
    "API",
    "PRIVATE",
    "CREDENTIAL",
    "CONN",
)

THEMES = {
    "dark": {
        "bg": "#121316",
        "surface": "#1C1E24",
        "surface_hover": "#262A34",
        "card_body": "#16181D",
        "border": "#2E323D",
        "border_hover": "#4B5563",
        "fg": "#F1F3F5",
        "fg_muted": "#9AA0AC",
        "accent": "#3B82F6",
        "accent_hover": "#2563EB",
        "accent_fg": "#FFFFFF",
        "btn_sec_bg": "#252830",
        "btn_sec_hover": "#343946",
        "btn_sec_fg": "#E5E7EB",
        "success": "#10B981",
        "scroll_trough": "#1A1D24",
        "scroll_thumb": "#3A404E",
        "scroll_thumb_hover": "#4E5668",
    },
    "light": {
        "bg": "#F4F6F9",
        "surface": "#FFFFFF",
        "surface_hover": "#EEF2F7",
        "card_body": "#FAFBFD",
        "border": "#DCE1E8",
        "border_hover": "#94A3B8",
        "fg": "#181B20",
        "fg_muted": "#5E6673",
        "accent": "#2563EB",
        "accent_hover": "#1D4ED8",
        "accent_fg": "#FFFFFF",
        "btn_sec_bg": "#E9EDF3",
        "btn_sec_hover": "#D8E0EB",
        "btn_sec_fg": "#1F242D",
        "success": "#059669",
        "scroll_trough": "#EAEFF5",
        "scroll_thumb": "#B8C2D1",
        "scroll_thumb_hover": "#9AA7BC",
    },
}


# ==============================================================================
# WINDOWS DPI, THEME, ICON & WINDOW STYLE HELPERS
# ==============================================================================

def enable_dpi_awareness() -> None:
    """Prevent UI blurriness on high-DPI Windows displays."""
    try:
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        )
        return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def set_app_user_model_id() -> None:
    """Ensure Windows Taskbar shows custom app icon."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def get_app_base_dir() -> str:
    """Return directory containing this script or frozen EXE."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resolve_icon_path() -> str | None:
    """Find icon.png from the same folder as the script/EXE (or bundled resources)."""
    candidates = [os.path.join(get_app_base_dir(), ICON_FILENAME)]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, ICON_FILENAME))

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def apply_custom_icon(win: tk.Misc) -> tk.PhotoImage | None:
    """Apply icon.png to a Tk/Toplevel window."""
    icon_file = resolve_icon_path()
    if not icon_file:
        return None
    try:
        img = tk.PhotoImage(file=icon_file)
        win.iconphoto(True, img)
        return img
    except Exception:
        return None


def detect_windows_theme() -> str:
    """Detect Windows 10/11 AppsUseLightTheme from Registry. Fallback to light."""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if int(value) == 1 else "dark"
    except Exception:
        return "light"


def apply_win32_window_rules(hwnd: int, is_dark: bool) -> None:
    """Disable Maximize button, enable Win11 rounded corners, and set dark/light title bar."""
    if not hwnd:
        return
    try:
        GWL_STYLE = -16
        WS_MAXIMIZEBOX = 0x00010000
        WS_THICKFRAME = 0x00040000

        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~WS_MAXIMIZEBOX
        style &= ~WS_THICKFRAME
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
        )
    except Exception:
        pass

    try:
        dwmapi = ctypes.windll.dwmapi
        val = ctypes.c_int(1 if is_dark else 0)
        if dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)) != 0:
            dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))

        corner_pref = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref)
        )
    except Exception:
        pass


# ==============================================================================
# SENSITIVE DATA REDACTION (KEEPS USERNAME VISIBLE)
# ==============================================================================

def _mask_user_paths(text: str) -> str:
    """Mask C:\\Users\\<Name> while keeping Current User field visible."""
    return re.sub(
        r"(?i)(\\Users\\)([^\\/\r\n;\"']+)",
        r"\1[REDACTED]",
        text,
    )


def _is_secret_env_name(var_name: str) -> bool:
    upper = var_name.upper()
    return any(k in upper for k in SECRET_ENV_KEYWORDS)


# ==============================================================================
# LIVE SYSTEM DATA COLLECTORS
# ==============================================================================

def _run_hidden(cmd: list[str], timeout: int = 12) -> str:
    """Run subprocess silently without flashing a console window."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
            creationflags=creationflags,
            timeout=timeout,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def _read_reg_val(root, path: str, name: str, default: str = "N/A") -> str:
    try:
        with winreg.OpenKey(root, path) as key:
            val, _ = winreg.QueryValueEx(key, name)
            return str(val).strip() if val is not None else default
    except Exception:
        return default


def struct_bits() -> int:
    return ctypes.sizeof(ctypes.c_void_p) * 8


def collect_system_info() -> str:
    """Collect OS, Windows build, Hardware, Manufacturer, CPU, RAM, GPU, Storage."""
    lines = []

    nt_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    product_name = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "ProductName", platform.system())
    display_ver = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "DisplayVersion", "")
    if not display_ver or display_ver == "N/A":
        display_ver = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "ReleaseId", "N/A")

    build_num = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "CurrentBuildNumber", platform.version())
    ubr = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "UBR", "")
    full_build = f"{build_num}.{ubr}" if ubr and ubr != "N/A" else build_num

    try:
        if int(build_num) >= 22000 and "Windows 10" in product_name:
            product_name = product_name.replace("Windows 10", "Windows 11")
    except ValueError:
        pass

    edition_id = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "EditionID", "N/A")
    install_ts = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, nt_path, "InstallDate", "")
    install_date = "N/A"
    if install_ts.isdigit():
        try:
            install_date = datetime.datetime.fromtimestamp(int(install_ts)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    bios_path = r"HARDWARE\DESCRIPTION\System\BIOS"
    sys_mfg = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "SystemManufacturer", "N/A")
    sys_prod = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "SystemProductName", "N/A")
    sys_family = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "SystemFamily", "N/A")
    board_mfg = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "BaseBoardManufacturer", "N/A")
    board_prod = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "BaseBoardProduct", "N/A")
    bios_vendor = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "BIOSVendor", "N/A")
    bios_ver = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "BIOSVersion", "N/A")
    bios_date = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, bios_path, "BIOSReleaseDate", "N/A")

    cpu_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    cpu_name = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, cpu_path, "ProcessorNameString", platform.processor())
    cpu_mhz = _read_reg_val(winreg.HKEY_LOCAL_MACHINE, cpu_path, "~MHz", "N/A")
    logical_cores = os.cpu_count() or "N/A"

    total_ram_str = "N/A"
    avail_ram_str = "N/A"
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_gb = stat.ullTotalPhys / (1024 ** 3)
        avail_gb = stat.ullAvailPhys / (1024 ** 3)
        total_ram_str = f"{total_gb:.2f} GB ({stat.dwMemoryLoad}% in use)"
        avail_ram_str = f"{avail_gb:.2f} GB"
    except Exception:
        pass

    gpus = []
    gpu_base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, gpu_base) as base_key:
            for i in range(16):
                try:
                    sub_name = winreg.EnumKey(base_key, i)
                    if not sub_name.isdigit():
                        continue
                    with winreg.OpenKey(base_key, sub_name) as sub_key:
                        desc, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                        if desc:
                            gpus.append(str(desc).strip())
                except OSError:
                    break
                except Exception:
                    continue
    except Exception:
        pass
    gpu_str = ", ".join(dict.fromkeys(gpus)) if gpus else "N/A"

    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for idx in range(26):
            if bitmask & (1 << idx):
                letter = f"{chr(65 + idx)}:\\"
                dtype = ctypes.windll.kernel32.GetDriveTypeW(letter)
                if dtype in (2, 3):
                    try:
                        usage = shutil.disk_usage(letter)
                        t_gb = usage.total / (1024 ** 3)
                        f_gb = usage.free / (1024 ** 3)
                        drives.append(f"{letter[:2]} {f_gb:.1f} GB free / {t_gb:.1f} GB total")
                    except Exception:
                        pass
    except Exception:
        pass

    current_user = os.environ.get("USERNAME", "N/A")

    lines.extend([
        "[Windows & OS]",
        f"OS Edition        : {product_name}",
        f"Edition ID        : {edition_id}",
        f"Version           : {display_ver}",
        f"OS Build          : {full_build}",
        f"Architecture      : {platform.machine()} ({struct_bits()}-bit)",
        f"Install Date      : {install_date}",
        f"Product ID        : [REDACTED]",
        f"Device Name       : {platform.node()}",
        f"Current User      : {current_user}",
        "",
        "[Device & Manufacturer]",
        f"Manufacturer      : {sys_mfg}",
        f"Model / Product   : {sys_prod}",
        f"System Family     : {sys_family}",
        f"Motherboard       : {board_mfg} ({board_prod})",
        f"BIOS              : {bios_vendor} | {bios_ver} ({bios_date})",
        "",
        "[Hardware & Storage]",
        f"Processor         : {cpu_name}",
        f"Base Clock        : {cpu_mhz} MHz",
        f"Logical Cores     : {logical_cores}",
        f"Installed RAM     : {total_ram_str}",
        f"Available RAM     : {avail_ram_str}",
        f"Graphics (GPU)    : {gpu_str}",
        f"Storage Drives    : {' | '.join(drives) if drives else 'N/A'}",
    ])
    return "\n".join(lines)


def _find_real_python_executables() -> list[str]:
    """Find actual Python installations without triggering the frozen PyInstaller EXE."""
    candidates = []
    frozen_exe = os.path.abspath(sys.executable).lower() if getattr(sys, "frozen", False) else ""

    where_out = _run_hidden(["where", "python"], timeout=5)
    for line in where_out.splitlines():
        path = line.strip()
        if path and os.path.isfile(path):
            if "windowsapps" in path.lower():
                continue
            if frozen_exe and os.path.abspath(path).lower() == frozen_exe:
                continue
            candidates.append(os.path.abspath(path))

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for reg_path in (r"SOFTWARE\Python\PythonCore", r"SOFTWARE\WOW6432Node\Python\PythonCore"):
            try:
                with winreg.OpenKey(root, reg_path) as core_key:
                    idx = 0
                    while True:
                        try:
                            ver = winreg.EnumKey(core_key, idx)
                            idx += 1
                            with winreg.OpenKey(core_key, f"{ver}\\InstallPath") as ip_key:
                                exe_path, _ = winreg.QueryValueEx(ip_key, "ExecutablePath")
                                if exe_path and os.path.isfile(exe_path):
                                    candidates.append(os.path.abspath(exe_path))
                        except OSError:
                            break
            except Exception:
                continue

    unique = []
    seen = set()
    for c in candidates:
        low = c.lower()
        if low not in seen:
            seen.add(low)
            unique.append(c)
    return unique


def collect_pip_list() -> str:
    """Collect installed PIP packages across detected Python interpreters."""
    pythons = _find_real_python_executables()
    if not pythons:
        return "No Python / PIP installation detected on this system."

    sections = []
    for py_exe in pythons:
        py_ver = _run_hidden([py_exe, "--version"], timeout=5) or "Python"
        pip_out = _run_hidden([py_exe, "-m", "pip", "list", "--disable-pip-version-check"], timeout=15)
        safe_exe = _mask_user_paths(py_exe)
        header = f"Interpreter: {py_ver} ({safe_exe})"
        if pip_out:
            sections.append(f"{header}\n{pip_out}")
        else:
            sections.append(f"{header}\nNo PIP packages found or pip is not installed.")

    return "\n\n".join(sections)


def collect_installed_apps() -> str:
    """Collect installed desktop apps from Windows Registry."""
    apps = {}
    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for root, path in uninstall_roots:
        try:
            with winreg.OpenKey(root, path) as key:
                idx = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(key, idx)
                        idx += 1
                        with winreg.OpenKey(key, sub_name) as sub_key:
                            try:
                                name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                            except OSError:
                                continue
                            name = str(name).strip()
                            if not name:
                                continue

                            try:
                                sys_comp, _ = winreg.QueryValueEx(sub_key, "SystemComponent")
                                if int(sys_comp) == 1:
                                    continue
                            except Exception:
                                pass

                            version = ""
                            publisher = ""
                            try:
                                version = str(winreg.QueryValueEx(sub_key, "DisplayVersion")[0]).strip()
                            except Exception:
                                pass
                            try:
                                publisher = str(winreg.QueryValueEx(sub_key, "Publisher")[0]).strip()
                            except Exception:
                                pass

                            key_id = name.lower()
                            if key_id not in apps:
                                apps[key_id] = (name, version, publisher)
                    except OSError:
                        break
        except Exception:
            continue

    sorted_apps = sorted(apps.values(), key=lambda x: x[0].lower())
    if not sorted_apps:
        return "No installed applications found."

    lines = [f"Total Installed Desktop Apps: {len(sorted_apps)}", ""]
    for idx, (name, ver, pub) in enumerate(sorted_apps, start=1):
        meta = []
        if ver:
            meta.append(f"v{ver}")
        if pub:
            meta.append(pub)
        suffix = f"  [{' | '.join(meta)}]" if meta else ""
        lines.append(f"{idx}. {name}{suffix}")

    return _mask_user_paths("\n".join(lines))


def _read_env_block(root, subkey: str) -> dict[str, str]:
    result = {}
    try:
        with winreg.OpenKey(root, subkey) as key:
            idx = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, idx)
                    idx += 1
                    result[str(name)] = str(val)
                except OSError:
                    break
    except Exception:
        pass
    return result


def collect_paths() -> str:
    """Collect System PATH and User PATH entries cleanly separated."""
    sys_env = _read_env_block(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
    )
    usr_env = _read_env_block(winreg.HKEY_CURRENT_USER, r"Environment")

    sys_path_raw = next((v for k, v in sys_env.items() if k.lower() == "path"), "")
    usr_path_raw = next((v for k, v in usr_env.items() if k.lower() == "path"), "")

    sys_entries = [_mask_user_paths(p.strip()) for p in sys_path_raw.split(";") if p.strip()]
    usr_entries = [_mask_user_paths(p.strip()) for p in usr_path_raw.split(";") if p.strip()]

    lines = [f"[System PATH ({len(sys_entries)} entries)]"]
    if sys_entries:
        lines.extend(f"{i}. {p}" for i, p in enumerate(sys_entries, 1))
    else:
        lines.append("(Empty)")

    lines.append("")
    lines.append(f"[User PATH ({len(usr_entries)} entries)]")
    if usr_entries:
        lines.extend(f"{i}. {p}" for i, p in enumerate(usr_entries, 1))
    else:
        lines.append("(Empty)")

    return "\n".join(lines)


def collect_env_variables() -> str:
    """Collect System and User Environment Variables with secret masking."""
    sys_env = _read_env_block(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
    )
    usr_env = _read_env_block(winreg.HKEY_CURRENT_USER, r"Environment")

    lines = [f"[System Environment Variables ({len(sys_env)})]"]
    for k in sorted(sys_env.keys(), key=str.lower):
        val = "[REDACTED]" if _is_secret_env_name(k) else _mask_user_paths(sys_env[k])
        lines.append(f"{k} = {val}")

    lines.append("")
    lines.append(f"[User Environment Variables ({len(usr_env)})]")
    if usr_env:
        for k in sorted(usr_env.keys(), key=str.lower):
            val = "[REDACTED]" if _is_secret_env_name(k) else _mask_user_paths(usr_env[k])
            lines.append(f"{k} = {val}")
    else:
        lines.append("(None)")

    return "\n".join(lines)


# ==============================================================================
# ROUNDED CORNERS & UI COMPONENTS
# ==============================================================================

def draw_rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int,
                       fill: str, outline: str = "", width: int = 1, tag: str = "round_bg"):
    """Draw a smooth rounded rectangle onto a Canvas."""
    canvas.delete(tag)
    r = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    if r == 0:
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=tag)
        return

    pts = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    canvas.create_polygon(pts, smooth=True, splinesteps=12, fill=fill, outline=outline, width=width, tags=tag)


class RoundedButton(tk.Canvas):
    """Custom button with smooth rounded corners and hover/copied feedback."""

    def __init__(self, parent, text: str, command=None, height: int = 32,
                 radius: int = 8, font=("Segoe UI", 9, "bold"), fixed_width: int | None = None):
        super().__init__(
            parent,
            height=height,
            width=fixed_width if fixed_width else 80,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self._text = text
        self._display_text = text
        self._command = command
        self._radius = radius
        self._font = font
        self._fixed_width = fixed_width
        self._hovered = False
        self._override_bg = None
        self._override_fg = None
        self._bg_normal = "#2563EB"
        self._bg_hover = "#1D4ED8"
        self._fg_color = "#FFFFFF"
        self._parent_bg = "#F4F6F9"

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_palette(self, parent_bg: str, bg_normal: str, bg_hover: str, fg_color: str):
        self._parent_bg = parent_bg
        self._bg_normal = bg_normal
        self._bg_hover = bg_hover
        self._fg_color = fg_color
        self.configure(bg=parent_bg)
        self._redraw()

    def set_temp_state(self, text: str, bg: str, fg: str, duration_ms: int = 1200):
        self._display_text = text
        self._override_bg = bg
        self._override_fg = fg
        self._redraw()
        self.after(duration_ms, self._clear_temp_state)

    def _clear_temp_state(self):
        self._display_text = self._text
        self._override_bg = None
        self._override_fg = None
        self._redraw()

    def _on_enter(self, _e=None):
        self._hovered = True
        self._redraw()

    def _on_leave(self, _e=None):
        self._hovered = False
        self._redraw()

    def _on_click(self, _e=None):
        if callable(self._command):
            self._command()

    def _redraw(self, _e=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 2 or h <= 2:
            w = self._fixed_width or int(self.cget("width"))
            h = int(self.cget("height"))

        self.delete("all")
        self.configure(bg=self._parent_bg)

        if self._override_bg:
            fill = self._override_bg
            fg = self._override_fg or "#FFFFFF"
        else:
            fill = self._bg_hover if self._hovered else self._bg_normal
            fg = self._fg_color

        draw_rounded_rect(self, 1, 1, w - 1, h - 1, self._radius, fill=fill, outline=fill, width=1, tag="btn_shape")
        self.create_text(w // 2, h // 2, text=self._display_text, fill=fg, font=self._font, tags="btn_lbl")


class CollapsibleSection(tk.Frame):
    """Rounded accordion section that starts collapsed and expands only when clicked."""

    def __init__(self, parent, index: int, title: str, on_copy_callback, on_main_scroll_callback):
        super().__init__(parent, bd=0, highlightthickness=0)
        self.index = index
        self.title = title
        self.on_copy_callback = on_copy_callback
        self.on_main_scroll_callback = on_main_scroll_callback
        self.is_expanded = False
        self.is_hovered = False
        self.content_text = "Loading..."
        self.theme = THEMES["light"]

        self.header_canvas = tk.Canvas(
            self, height=42, bd=0, highlightthickness=0, cursor="hand2"
        )
        self.header_canvas.pack(fill="x")

        self.arrow_lbl = tk.Label(
            self.header_canvas,
            text="▶",
            font=("Segoe UI", 9, "bold"),
            width=2,
            cursor="hand2",
        )
        self.title_lbl = tk.Label(
            self.header_canvas,
            text=f"{index}. {title}",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            cursor="hand2",
        )
        self.copy_btn = RoundedButton(
            self.header_canvas,
            text="Copy",
            command=self._handle_copy,
            height=26,
            radius=6,
            font=("Segoe UI", 8, "bold"),
            fixed_width=58,
        )

        self.arrow_win = self.header_canvas.create_window(12, 21, window=self.arrow_lbl, anchor="w")
        self.title_win = self.header_canvas.create_window(34, 21, window=self.title_lbl, anchor="w")
        self.copy_win = self.header_canvas.create_window(0, 21, window=self.copy_btn, anchor="e")

        self.body_frame = tk.Frame(self, bd=0, highlightthickness=1)
        self.text_box = tk.Text(
            self.body_frame,
            height=9,
            wrap="none",
            font=("Consolas", 8),
            bd=0,
            padx=8,
            pady=6,
            state="disabled",
            cursor="arrow",
        )
        self.v_scroll = ttk.Scrollbar(
            self.body_frame, orient="vertical", command=self.text_box.yview
        )
        self.h_scroll = ttk.Scrollbar(
            self.body_frame, orient="horizontal", command=self.text_box.xview
        )
        self.text_box.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
        )

        self.text_box.bind("<MouseWheel>", self._route_to_main_scroll)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.text_box.pack(side="left", fill="both", expand=True)

        self.header_canvas.bind("<Configure>", self._layout_header)
        for widget in (self.header_canvas, self.arrow_lbl, self.title_lbl):
            widget.bind("<Button-1>", self.toggle)
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")

    def _route_to_main_scroll(self, event):
        self.on_main_scroll_callback(event)
        return "break"

    def _layout_header(self, event=None):
        w = event.width if event else self.header_canvas.winfo_width()
        if w <= 2:
            w = 372
        self.header_canvas.coords(self.copy_win, w - 8, 21)
        title_max_w = max(60, w - 106)
        self.title_lbl.configure(wraplength=0)
        self.header_canvas.itemconfigure(self.title_win, width=title_max_w)
        self._redraw_header_bg(w)

    def _redraw_header_bg(self, w: int | None = None):
        if w is None:
            w = self.header_canvas.winfo_width()
        if w <= 2:
            w = 372
        t = self.theme
        fill = t["surface_hover"] if self.is_hovered else t["surface"]
        outline = t["border_hover"] if self.is_hovered else t["border"]

        self.header_canvas.configure(bg=t["bg"])
        self.arrow_lbl.configure(bg=fill, fg=t["accent"])
        self.title_lbl.configure(bg=fill, fg=t["fg"])
        self.copy_btn.set_palette(
            parent_bg=fill,
            bg_normal=t["btn_sec_bg"],
            bg_hover=t["btn_sec_hover"],
            fg_color=t["btn_sec_fg"],
        )
        draw_rounded_rect(
            self.header_canvas, 1, 1, w - 1, 41, radius=10,
            fill=fill, outline=outline, width=1, tag="sec_card_bg"
        )
        self.header_canvas.tag_lower("sec_card_bg")

    def _on_enter(self, _e=None):
        self.is_hovered = True
        self._redraw_header_bg()

    def _on_leave(self, _e=None):
        self.is_hovered = False
        self._redraw_header_bg()

    def toggle(self, _event=None):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.arrow_lbl.configure(text="▼")
            self.body_frame.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        else:
            self.arrow_lbl.configure(text="▶")
            self.body_frame.pack_forget()

    def set_content(self, text: str):
        self.content_text = text
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", text)
        self.text_box.configure(state="disabled")

    def get_formatted_block(self) -> str:
        return f"===== {self.index}. {self.title} =====\n{self.content_text}"

    def _handle_copy(self):
        self.on_copy_callback(self)

    def flash_copied(self, theme: dict):
        self.copy_btn.set_temp_state("Copied!", theme["success"], "#FFFFFF", duration_ms=1200)

    def apply_theme(self, theme: dict):
        self.theme = theme
        self.configure(bg=theme["bg"])
        self._redraw_header_bg()
        self.body_frame.configure(bg=theme["card_body"], highlightbackground=theme["border"])
        self.text_box.configure(
            bg=theme["card_body"],
            fg=theme["fg"],
            insertbackground=theme["fg"],
            selectbackground=theme["accent"],
            selectforeground="#FFFFFF",
        )


# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

class SysCopyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self._icon_refs = []
        self.current_theme_name = detect_windows_theme()
        self.theme = THEMES[self.current_theme_name]
        self.info_popup = None

        self.title(APP_NAME)
        self._center_and_lock_window()

        icon_img = apply_custom_icon(self)
        if icon_img:
            self._icon_refs.append(icon_img)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._build_ui()
        self._apply_theme(self.current_theme_name)

        self.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
        apply_win32_window_rules(hwnd, self.current_theme_name == "dark")

        self._load_all_data_async()
        self.after(350, self._poll_windows_theme)

    def _center_and_lock_window(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - WINDOW_WIDTH) // 2)
        y = max(0, (screen_h - WINDOW_HEIGHT) // 2)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.resizable(False, False)

    def _build_ui(self):
        self.top_bar = tk.Frame(self)
        self.top_bar.pack(fill="x", padx=14, pady=(12, 6))

        self.app_title_lbl = tk.Label(
            self.top_bar,
            text=APP_NAME,
            font=("Segoe UI", 13, "bold"),
        )
        self.app_title_lbl.pack(side="left")

        self.info_btn = RoundedButton(
            self.top_bar,
            text="!",
            command=self._show_info_popup,
            height=28,
            radius=8,
            font=("Segoe UI", 9, "bold"),
            fixed_width=32,
        )
        self.info_btn.pack(side="right")

        self.action_bar = tk.Frame(self)
        self.action_bar.pack(fill="x", padx=14, pady=(4, 10))

        self.copy_all_btn = RoundedButton(
            self.action_bar,
            text="Copy All",
            command=lambda: self._copy_bulk(exclude_sys_info=False),
            height=34,
            radius=8,
            font=("Segoe UI", 9, "bold"),
        )
        self.copy_all_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.copy_no_sys_btn = RoundedButton(
            self.action_bar,
            text="Copy All (Except Sys Info)",
            command=lambda: self._copy_bulk(exclude_sys_info=True),
            height=34,
            radius=8,
            font=("Segoe UI", 8, "bold"),
        )
        self.copy_no_sys_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

        self.scroll_container = tk.Frame(self)
        self.scroll_container.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.canvas = tk.Canvas(self.scroll_container, bd=0, highlightthickness=0)
        self.cards_frame = tk.Frame(self.canvas)

        self.cards_window = self.canvas.create_window(
            (0, 0), window=self.cards_frame, anchor="nw"
        )
        self.canvas.pack(fill="both", expand=True)

        self.cards_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.cards_window, width=e.width),
        )
        self.bind_all("<MouseWheel>", self._on_main_mousewheel)

        section_defs = [
            (1, "SYSTEM & DEVICE INFO"),
            (2, "PIP LIST"),
            (3, "INSTALLED APPS"),
            (4, "SYSTEM & USER PATH LIST"),
            (5, "ENVIRONMENT VARIABLES"),
        ]
        self.sections: list[CollapsibleSection] = []
        for idx, title in section_defs:
            sec = CollapsibleSection(
                self.cards_frame,
                idx,
                title,
                on_copy_callback=self._copy_single_section,
                on_main_scroll_callback=self._scroll_main_canvas,
            )
            sec.pack(fill="x", pady=(0, 8))
            self.sections.append(sec)

    def _scroll_main_canvas(self, event):
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        content_h = bbox[3] - bbox[1]
        canvas_h = self.canvas.winfo_height()
        if content_h > canvas_h:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_main_mousewheel(self, event):
        self._scroll_main_canvas(event)
        if isinstance(event.widget, tk.Text):
            return "break"

    def _load_all_data_async(self):
        collectors = [
            (0, collect_system_info),
            (1, collect_pip_list),
            (2, collect_installed_apps),
            (3, collect_paths),
            (4, collect_env_variables),
        ]

        def worker():
            for sec_idx, func in collectors:
                try:
                    data = func()
                except Exception as exc:
                    data = f"Error collecting data: {exc}"
                self.after(0, self.sections[sec_idx].set_content, data)

        threading.Thread(target=worker, daemon=True).start()

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _copy_single_section(self, section: CollapsibleSection):
        self._copy_to_clipboard(section.get_formatted_block())
        section.flash_copied(self.theme)

    def _copy_bulk(self, exclude_sys_info: bool):
        target_sections = self.sections[1:] if exclude_sys_info else self.sections
        blocks = [sec.get_formatted_block() for sec in target_sections]
        self._copy_to_clipboard("\n\n".join(blocks))

        btn = self.copy_no_sys_btn if exclude_sys_info else self.copy_all_btn
        btn.set_temp_state("Copied!", self.theme["success"], "#FFFFFF", duration_ms=1200)

    def _show_info_popup(self):
        if self.info_popup and self.info_popup.winfo_exists():
            self.info_popup.lift()
            return

        popup = tk.Toplevel(self)
        self.info_popup = popup
        popup.title(f"About {APP_NAME}")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        popup_icon = apply_custom_icon(popup)
        if popup_icon:
            self._icon_refs.append(popup_icon)

        pw, ph = 336, 325
        px = self.winfo_x() + (WINDOW_WIDTH - pw) // 2
        py = self.winfo_y() + (WINDOW_HEIGHT - ph) // 2
        popup.geometry(f"{pw}x{ph}+{px}+{py}")

        t = self.theme
        popup.configure(bg=t["surface"])

        tk.Label(
            popup,
            text=f"{APP_NAME}  v{APP_VERSION}",
            font=("Segoe UI", 12, "bold"),
            bg=t["surface"],
            fg=t["fg"],
        ).pack(anchor="w", padx=18, pady=(12, 2))

        tk.Label(
            popup,
            text=f"Created by: {CREATED_BY}",
            font=("Segoe UI", 9, "bold"),
            bg=t["surface"],
            fg=t["accent"],
        ).pack(anchor="w", padx=18, pady=(0, 6))

        tk.Label(
            popup,
            text=APP_DESCRIPTION,
            font=("Segoe UI", 8),
            bg=t["surface"],
            fg=t["fg_muted"],
            wraplength=300,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 8))

        gh_lbl = tk.Label(
            popup,
            text=f"GitHub: {REPO_URL}",
            font=("Segoe UI", 8, "underline"),
            bg=t["surface"],
            fg=t["accent"],
            wraplength=300,
            justify="left",
            cursor="hand2",
        )
        gh_lbl.pack(anchor="w", padx=18, pady=(0, 4))
        gh_lbl.bind("<Button-1>", lambda _e: webbrowser.open(REPO_URL))
        gh_lbl.bind("<Enter>", lambda _e: gh_lbl.configure(fg=t["accent_hover"]))
        gh_lbl.bind("<Leave>", lambda _e: gh_lbl.configure(fg=t["accent"]))

        yt_lbl = tk.Label(
            popup,
            text=f"YouTube: {YOUTUBE_URL}",
            font=("Segoe UI", 8, "underline"),
            bg=t["surface"],
            fg=t["accent"],
            wraplength=300,
            justify="left",
            cursor="hand2",
        )
        yt_lbl.pack(anchor="w", padx=18, pady=(0, 10))
        yt_lbl.bind("<Button-1>", lambda _e: webbrowser.open(YOUTUBE_URL))
        yt_lbl.bind("<Enter>", lambda _e: yt_lbl.configure(fg=t["accent_hover"]))
        yt_lbl.bind("<Leave>", lambda _e: yt_lbl.configure(fg=t["accent"]))

        close_btn = RoundedButton(
            popup,
            text="Close",
            command=popup.destroy,
            height=36,
            radius=8,
            font=("Segoe UI", 9, "bold"),
            fixed_width=84,
        )
        close_btn.pack(anchor="e", padx=18, pady=(2, 14))
        close_btn.set_palette(
            parent_bg=t["surface"],
            bg_normal=t["accent"],
            bg_hover=t["accent_hover"],
            fg_color=t["accent_fg"],
        )

        popup.update_idletasks()
        p_hwnd = ctypes.windll.user32.GetParent(popup.winfo_id()) or popup.winfo_id()
        apply_win32_window_rules(p_hwnd, self.current_theme_name == "dark")

    def _apply_theme(self, theme_name: str):
        self.current_theme_name = theme_name
        t = THEMES[theme_name]
        self.theme = t

        self.configure(bg=t["bg"])
        self.top_bar.configure(bg=t["bg"])
        self.app_title_lbl.configure(bg=t["bg"], fg=t["fg"])

        self.info_btn.set_palette(
            parent_bg=t["bg"],
            bg_normal=t["btn_sec_bg"],
            bg_hover=t["btn_sec_hover"],
            fg_color=t["accent"],
        )

        self.action_bar.configure(bg=t["bg"])
        self.copy_all_btn.set_palette(
            parent_bg=t["bg"],
            bg_normal=t["accent"],
            bg_hover=t["accent_hover"],
            fg_color=t["accent_fg"],
        )
        self.copy_no_sys_btn.set_palette(
            parent_bg=t["bg"],
            bg_normal=t["btn_sec_bg"],
            bg_hover=t["btn_sec_hover"],
            fg_color=t["btn_sec_fg"],
        )

        self.scroll_container.configure(bg=t["bg"])
        self.canvas.configure(bg=t["bg"])
        self.cards_frame.configure(bg=t["bg"])

        for sb_style in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            self.style.configure(
                sb_style,
                background=t["scroll_thumb"],
                troughcolor=t["scroll_trough"],
                bordercolor=t["bg"],
                arrowcolor=t["fg_muted"],
                relief="flat",
            )
            self.style.map(
                sb_style,
                background=[("active", t["scroll_thumb_hover"])],
            )

        for sec in self.sections:
            sec.apply_theme(t)

        if self.info_popup and self.info_popup.winfo_exists():
            p_hwnd = ctypes.windll.user32.GetParent(self.info_popup.winfo_id()) or self.info_popup.winfo_id()
            apply_win32_window_rules(p_hwnd, theme_name == "dark")

    def _poll_windows_theme(self):
        latest = detect_windows_theme()
        if latest != self.current_theme_name:
            self._apply_theme(latest)
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            apply_win32_window_rules(hwnd, latest == "dark")
        self.after(350, self._poll_windows_theme)


if __name__ == "__main__":
    enable_dpi_awareness()
    set_app_user_model_id()
    app = SysCopyApp()
    app.mainloop()