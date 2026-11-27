"""
Sys Copy v1.0 Setup (version 0.1)
Custom GUI installer and uninstaller for Sys Copy v1.0 with Light/Dark
rounded card UI, initial Current User / All Users selection, UAC elevation,
custom non-card Informations dialog, custom Dark/Light dialogs (no system
messageboxes), WinError 32 file-lock retry handling, fixed 580x430
horizontal launch-and-close flow, and custom UI uninstaller with optional
feedback link.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.parse
import webbrowser
import winreg
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

__version__ = "0.1"

APP_DISPLAY_NAME = "Sys Copy v1.0"
INSTALLER_TITLE = "Sys Copy v1.0 Setup"
INFO_WINDOW_TITLE = f"Informations — {INSTALLER_TITLE}"
CREATOR_LABEL = "Genie Codebase [GC]"
REGISTRY_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SysCopy_v1_0"

FEEDBACK_BASE_URL = "https://github.com/GenieCodebase/Sys-Copy/issues/new"

BUNDLED_APP_CANDIDATES = ("Sys-Copy-v0.1.exe", "Sys Copy v1.0.exe")
INSTALLED_APP_FILENAME = "Sys Copy v1.0.exe"
UNINSTALLER_FILENAME = "Uninstall Sys Copy v1.0.exe"

WINDOW_WIDTH = 580
WINDOW_HEIGHT = 430

UNINSTALL_REASONS = (
    "Not needed right now",
    "Found an issue",
    "Switching tools",
    "Other",
)

LIGHT_PALETTE = {
    "bg": "#F3F4F6",
    "surface": "#FFFFFF",
    "surface_alt": "#F9FAFB",
    "border": "#D1D5DB",
    "border_active": "#2563EB",
    "text": "#111827",
    "text_muted": "#4B5563",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_text": "#FFFFFF",
    "btn_sec": "#E5E7EB",
    "btn_sec_hover": "#D1D5DB",
    "track": "#E5E7EB",
}

DARK_PALETTE = {
    "bg": "#111317",
    "surface": "#181B20",
    "surface_alt": "#1E2229",
    "border": "#2B303A",
    "border_active": "#3B82F6",
    "text": "#F3F4F6",
    "text_muted": "#9CA3AF",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_text": "#FFFFFF",
    "btn_sec": "#232730",
    "btn_sec_hover": "#2E333F",
    "track": "#262B34",
}


def enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def is_windows_light_theme() -> bool:
    if os.name != "nt":
        return True
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return bool(int(val) != 0)
    except Exception:
        return True


def apply_title_bar_theme(window: tk.Tk | tk.Toplevel, dark: bool) -> None:
    if os.name != "nt":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:
        pass


def get_resource_path(filename: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidate = Path(base) / filename
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent / filename


def find_bundled_payload() -> Optional[Path]:
    for name in BUNDLED_APP_CANDIDATES:
        p = get_resource_path(name)
        if p.exists():
            return p
    return None


def default_install_dir(scope: str) -> Path:
    if scope == "all":
        pf = os.environ.get("ProgramFiles") or r"C:\Program Files"
        return Path(pf) / APP_DISPLAY_NAME
    local_app = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local_app) / "Programs" / APP_DISPLAY_NAME


def create_shortcut_lnk(
    shortcut_path: Path,
    target_exe: Path,
    working_dir: Path,
    icon_exe: Optional[Path] = None,
    arguments: str = "",
) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    icon_target = icon_exe if (icon_exe and icon_exe.exists()) else target_exe

    def ps_escape(s: str) -> str:
        return s.replace("'", "''")

    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$sc = $ws.CreateShortcut('{ps_escape(str(shortcut_path))}'); "
        f"$sc.TargetPath = '{ps_escape(str(target_exe))}'; "
        f"$sc.WorkingDirectory = '{ps_escape(str(working_dir))}'; "
        f"$sc.IconLocation = '{ps_escape(str(icon_target))},0'; "
        f"$sc.Arguments = '{ps_escape(arguments)}'; "
        "$sc.Save()"
    )
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        check=True,
        startupinfo=startupinfo,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def register_uninstall_entry(
    scope: str,
    install_dir: Path,
    app_exe: Path,
    uninstaller_exe: Path,
) -> None:
    hive = winreg.HKEY_LOCAL_MACHINE if scope == "all" else winreg.HKEY_CURRENT_USER
    access = winreg.KEY_WRITE | getattr(winreg, "KEY_WOW64_64KEY", 0)
    with winreg.CreateKeyEx(hive, REGISTRY_SUBKEY, 0, access) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, CREATOR_LABEL)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(app_exe))
        winreg.SetValueEx(
            key,
            "UninstallString",
            0,
            winreg.REG_SZ,
            f'"{uninstaller_exe}" --uninstall --scope={scope} --dir="{install_dir}"',
        )
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def remove_uninstall_entry(scope: str) -> None:
    hive = winreg.HKEY_LOCAL_MACHINE if scope == "all" else winreg.HKEY_CURRENT_USER
    for flag in (getattr(winreg, "KEY_WOW64_64KEY", 0), 0):
        try:
            winreg.DeleteKeyEx(hive, REGISTRY_SUBKEY, flag, 0)
        except FileNotFoundError:
            pass
        except OSError:
            try:
                winreg.DeleteKey(hive, REGISTRY_SUBKEY)
            except OSError:
                pass


def is_process_running(exe_name: str) -> bool:
    if os.name != "nt":
        return False
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
            text=True,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return exe_name.lower() in out.lower()
    except Exception:
        return False


def stop_process_if_running(exe_name: str) -> None:
    if os.name != "nt" or not is_process_running(exe_name):
        return
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            ["taskkill", "/F", "/IM", exe_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        time.sleep(0.25)
    except Exception:
        pass


def copy_file_with_retry(src: Path, dst: Path, attempts: int = 6, delay_s: float = 0.25) -> None:
    stop_process_if_running(dst.name)
    last_err: Optional[Exception] = None
    for idx in range(attempts):
        try:
            if dst.exists():
                try:
                    os.chmod(dst, 0o666)
                except Exception:
                    pass
                try:
                    dst.unlink()
                except PermissionError:
                    stale = dst.with_name(f"{dst.stem}.old{dst.suffix}")
                    if stale.exists():
                        try:
                            stale.unlink()
                        except Exception:
                            pass
                    os.replace(dst, stale)
            shutil.copy2(src, dst)
            return
        except PermissionError as exc:
            last_err = exc
            if idx < attempts - 1:
                time.sleep(delay_s)
    if last_err:
        raise last_err


def relaunch_as_admin(extra_args: list[str]) -> bool:
    if os.name != "nt":
        return False
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        args_list = extra_args
    else:
        exe_path = sys.executable
        args_list = [str(Path(__file__).resolve())] + extra_args

    def quote_arg(a: str) -> str:
        return f'"{a}"' if (" " in a or not a) else a

    params = " ".join(quote_arg(x) for x in args_list)
    res = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, None, 1)
    return int(res) > 32


def build_round_rect_points(x1: float, y1: float, x2: float, y2: float, r: float) -> list[float]:
    r = max(0.0, min(r, abs(x2 - x1) / 2.0, abs(y2 - y1) / 2.0))
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1, x2, y1 + r,
        x2, y2 - r,
        x2, y2, x2 - r, y2,
        x1 + r, y2,
        x1, y2, x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


class RoundedCard(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        palette: dict[str, str],
        radius: int = 10,
        fill_key: str = "surface",
        border_key: str = "border",
        padding: tuple[int, int, int, int] = (12, 10, 12, 10),
        clickable: bool = False,
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(
            parent,
            highlightthickness=0,
            bd=0,
            bg=palette["bg"],
        )
        self.palette = palette
        self.radius = radius
        self.fill_key = fill_key
        self.border_key = border_key
        self.padding = padding
        self.clickable = clickable
        self.on_click = on_click
        self.hovered = False

        self.inner = tk.Frame(self, bg=palette[fill_key])
        self._inner_win = self.create_window(
            padding[0], padding[1], window=self.inner, anchor="nw"
        )

        self.bind("<Configure>", self._redraw)
        self.inner.bind("<Configure>", self._sync_inner_size)

        if clickable:
            self.configure(cursor="hand2")
            self.inner.configure(cursor="hand2")
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", self._handle_click)
            self._bind_children(self.inner)

    def _bind_children(self, widget: tk.Misc) -> None:
        for child in widget.winfo_children():
            if isinstance(child, (tk.Entry, tk.Checkbutton, tk.Radiobutton)):
                continue
            child.configure(cursor="hand2")
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)
            child.bind("<Button-1>", self._handle_click)
            self._bind_children(child)

    def refresh_bindings(self) -> None:
        if self.clickable:
            self._bind_children(self.inner)

    def _on_enter(self, _event: object = None) -> None:
        self.hovered = True
        self._redraw()

    def _on_leave(self, _event: object = None) -> None:
        self.hovered = False
        self._redraw()

    def _handle_click(self, _event: object = None) -> None:
        if self.on_click:
            self.on_click()

    def _sync_inner_size(self, _event: object = None) -> None:
        w = max(1, self.winfo_width() - self.padding[0] - self.padding[2])
        h = max(1, self.inner.winfo_reqheight())
        self.itemconfigure(self._inner_win, width=w, height=h)
        desired_h = h + self.padding[1] + self.padding[3]
        if int(self["height"]) != desired_h:
            self.configure(height=desired_h)
        self._redraw()

    def _redraw(self, _event: object = None) -> None:
        self.delete("card_bg")
        w = max(4, self.winfo_width())
        h = max(4, self.winfo_height())
        fill = self.palette["surface_alt"] if (self.clickable and self.hovered) else self.palette[self.fill_key]
        outline = self.palette["border_active"] if (self.clickable and self.hovered) else self.palette[self.border_key]
        self.configure(bg=self.palette["bg"])
        self.inner.configure(bg=fill)
        for child in self.inner.winfo_children():
            if isinstance(child, tk.Entry):
                continue
            try:
                child.configure(bg=fill)
            except tk.TclError:
                pass
        pts = build_round_rect_points(1, 1, w - 1, h - 1, self.radius)
        self.create_polygon(
            pts,
            smooth=True,
            splinesteps=16,
            fill=fill,
            outline=outline,
            width=1,
            tags="card_bg",
        )
        self.tag_lower("card_bg")


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        palette: dict[str, str],
        command: Callable[[], None],
        primary: bool = True,
        width: int = 110,
        height: int = 34,
        radius: int = 8,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=palette["bg"],
            cursor="hand2",
        )
        self.text = text
        self.palette = palette
        self.command = command
        self.primary = primary
        self.btn_w = width
        self.btn_h = height
        self.radius = radius
        self.enabled = True
        self.hovered = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.redraw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self.redraw()

    def set_text(self, text: str) -> None:
        self.text = text
        self.redraw()

    def set_parent_bg(self, bg: str) -> None:
        self.configure(bg=bg)
        self.redraw()

    def _on_enter(self, _event: object = None) -> None:
        if self.enabled:
            self.hovered = True
            self.redraw()

    def _on_leave(self, _event: object = None) -> None:
        self.hovered = False
        self._redraw()

    def _on_click(self, _event: object = None) -> None:
        if self.enabled and self.command:
            self.command()

    def redraw(self) -> None:
        self.delete("all")
        w, h = self.btn_w, self.btn_h
        if self.primary:
            fill = self.palette["accent_hover"] if self.hovered else self.palette["accent"]
            outline = fill
            fg = self.palette["accent_text"]
        else:
            fill = self.palette["btn_sec_hover"] if self.hovered else self.palette["btn_sec"]
            outline = self.palette["border"]
            fg = self.palette["text"]

        if not self.enabled:
            fill = self.palette["track"]
            outline = self.palette["border"]
            fg = self.palette["text_muted"]

        pts = build_round_rect_points(1, 1, w - 1, h - 1, self.radius)
        self.create_polygon(pts, smooth=True, splinesteps=16, fill=fill, outline=outline, width=1)
        self.create_text(
            w / 2,
            h / 2,
            text=self.text,
            fill=fg,
            font=("Segoe UI", 9, "bold" if self.primary else "normal"),
        )


class RoundedProgressBar(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        palette: dict[str, str],
        height: int = 14,
        radius: int = 7,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=palette["surface"],
        )
        self.palette = palette
        self.bar_h = height
        self.radius = radius
        self.progress = 0.0
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_progress(self, value: float) -> None:
        self.progress = max(0.0, min(1.0, float(value)))
        self.redraw()

    def set_parent_bg(self, bg: str) -> None:
        self.configure(bg=bg)
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        w = max(8, self.winfo_width())
        h = self.bar_h
        track_pts = build_round_rect_points(1, 1, w - 1, h - 1, self.radius)
        self.create_polygon(
            track_pts,
            smooth=True,
            splinesteps=14,
            fill=self.palette["track"],
            outline=self.palette["border"],
            width=1,
        )
        fill_w = (w - 2) * self.progress
        if fill_w >= 6:
            r = min(self.radius, fill_w / 2.0)
            fill_pts = build_round_rect_points(1, 1, 1 + fill_w, h - 1, r)
            self.create_polygon(
                fill_pts,
                smooth=True,
                splinesteps=14,
                fill=self.palette["accent"],
                outline=self.palette["accent"],
                width=1,
            )


class CustomNoticeModal(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        palette: dict[str, str],
        dark: bool,
        title: str,
        heading: str,
        message: str,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.palette = palette
        self.on_close = on_close
        self.title(title)
        self.configure(bg=palette["bg"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        w, h = 480, 210
        px = parent.winfo_x() + max(0, (parent.winfo_width() - w) // 2)
        py = parent.winfo_y() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{px}+{py}")
        apply_title_bar_theme(self, dark)

        container = tk.Frame(self, bg=palette["bg"], padx=18, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=heading,
            bg=palette["bg"],
            fg=palette["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
            wraplength=440,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        tk.Label(
            container,
            text=message,
            bg=palette["bg"],
            fg=palette["text"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=440,
            justify="left",
        ).pack(fill="x")

        footer = tk.Frame(container, bg=palette["bg"])
        footer.pack(fill="x", side="bottom")
        ok_btn = RoundedButton(
            footer,
            text="OK",
            palette=palette,
            command=self._close,
            primary=True,
            width=96,
            height=32,
            radius=8,
        )
        ok_btn.set_parent_bg(palette["bg"])
        ok_btn.pack(side="right")

    def _close(self) -> None:
        self.destroy()
        if self.on_close:
            self.on_close()


class InformationsModal(tk.Toplevel):
    def __init__(self, parent: tk.Misc, palette: dict[str, str], dark: bool) -> None:
        super().__init__(parent)
        self.palette = palette
        self.title(INFO_WINDOW_TITLE)
        self.configure(bg=palette["bg"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        w, h = 480, 240
        px = parent.winfo_x() + max(0, (parent.winfo_width() - w) // 2)
        py = parent.winfo_y() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{px}+{py}")
        apply_title_bar_theme(self, dark)

        container = tk.Frame(self, bg=palette["bg"], padx=18, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=APP_DISPLAY_NAME,
            bg=palette["bg"],
            fg=palette["text"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            container,
            text=f"Created by: {CREATOR_LABEL}  |  {INSTALLER_TITLE}",
            bg=palette["bg"],
            fg=palette["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=440,
            justify="left",
        ).pack(fill="x", pady=(2, 10))

        lines = (
            "• Privacy: Local system diagnostics only; no data leaves your PC.",
            "• Shortcuts & Uninstall: Creates optional Desktop/Start Menu shortcuts and supports removal via Installed Apps.",
        )
        for line in lines:
            tk.Label(
                container,
                text=line,
                bg=palette["bg"],
                fg=palette["text"],
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=440,
                justify="left",
            ).pack(fill="x", pady=(0, 6))

        footer = tk.Frame(container, bg=palette["bg"])
        footer.pack(fill="x", side="bottom")
        close_btn = RoundedButton(
            footer,
            text="Close",
            palette=palette,
            command=self.destroy,
            primary=True,
            width=96,
            height=32,
            radius=8,
        )
        close_btn.set_parent_bg(palette["bg"])
        close_btn.pack(side="right")


class InstallerApp(tk.Tk):
    def __init__(self, initial_scope: Optional[str] = None, start_step: int = 1) -> None:
        super().__init__()
        self.dark = not is_windows_light_theme()
        self.palette = DARK_PALETTE if self.dark else LIGHT_PALETTE

        self.scope: str = initial_scope if initial_scope in ("user", "all") else "user"
        self.step: int = start_step
        self.install_dir_var = tk.StringVar(value=str(default_install_dir(self.scope)))
        self.desktop_var = tk.BooleanVar(value=True)
        self.startmenu_var = tk.BooleanVar(value=True)
        self.launch_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready to install.")
        self.installing = False

        self.title(INSTALLER_TITLE)
        self.configure(bg=self.palette["bg"])
        self.resizable(False, False)

        self._load_window_icon()
        self._center_window(WINDOW_WIDTH, WINDOW_HEIGHT)
        apply_title_bar_theme(self, self.dark)

        self.root_frame = tk.Frame(self, bg=self.palette["bg"], padx=16, pady=14)
        self.root_frame.pack(fill="both", expand=True)

        self._build_header()
        self.body_frame = tk.Frame(self.root_frame, bg=self.palette["bg"])
        self.body_frame.pack(fill="both", expand=True, pady=(10, 0))

        self._render_step()

    def _show_notice(
        self,
        heading: str,
        message: str,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        CustomNoticeModal(
            self,
            self.palette,
            self.dark,
            title=INSTALLER_TITLE,
            heading=heading,
            message=message,
            on_close=on_close,
        )

    def _load_window_icon(self) -> None:
        png_path = get_resource_path("iicon.png")
        ico_path = get_resource_path("iicon.ico")
        if png_path.exists():
            try:
                self._icon_img = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self._icon_img)
                return
            except Exception:
                pass
        if ico_path.exists():
            try:
                self.iconbitmap(default=str(ico_path))
            except Exception:
                pass

    def _center_window(self, width: int, height: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_header(self) -> None:
        header = tk.Frame(self.root_frame, bg=self.palette["bg"])
        header.pack(fill="x")

        tk.Label(
            header,
            text=INSTALLER_TITLE,
            bg=self.palette["bg"],
            fg=self.palette["text"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(side="left")

        info_btn = RoundedButton(
            header,
            text="!",
            palette=self.palette,
            command=self._open_info_modal,
            primary=False,
            width=32,
            height=30,
            radius=7,
        )
        info_btn.set_parent_bg(self.palette["bg"])
        info_btn.pack(side="right")

    def _open_info_modal(self) -> None:
        InformationsModal(self, self.palette, self.dark)

    def _clear_body(self) -> None:
        for child in self.body_frame.winfo_children():
            child.destroy()

    def _render_step(self) -> None:
        self._clear_body()
        if self.step == 1:
            self._render_scope_step()
        elif self.step == 2:
            self._render_options_step()
        elif self.step == 3:
            self._render_progress_step()
        elif self.step == 4:
            self._render_done_step()

    def _render_scope_step(self) -> None:
        p = self.palette
        tk.Label(
            self.body_frame,
            text="Choose Installation Scope",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        def choose(selected_scope: str) -> None:
            self.scope = selected_scope
            self.install_dir_var.set(str(default_install_dir(selected_scope)))
            self._go_from_scope()

        user_card = RoundedCard(
            self.body_frame,
            p,
            radius=10,
            padding=(14, 10, 14, 10),
            clickable=True,
            on_click=lambda: choose("user"),
        )
        user_card.pack(fill="x", pady=(0, 8))
        tk.Label(
            user_card.inner,
            text="Current User Only",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            user_card.inner,
            text=f"Install to {default_install_dir('user')} (no administrator prompt required).",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=510,
            justify="left",
        ).pack(fill="x", pady=(2, 0))
        user_card.refresh_bindings()

        all_card = RoundedCard(
            self.body_frame,
            p,
            radius=10,
            padding=(14, 10, 14, 10),
            clickable=True,
            on_click=lambda: choose("all"),
        )
        all_card.pack(fill="x")
        tk.Label(
            all_card.inner,
            text="All Users",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            all_card.inner,
            text=f"Install to {default_install_dir('all')} for all accounts (requires administrator approval).",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=510,
            justify="left",
        ).pack(fill="x", pady=(2, 0))
        all_card.refresh_bindings()

        footer = tk.Frame(self.body_frame, bg=p["bg"])
        footer.pack(fill="x", side="bottom")
        cancel_btn = RoundedButton(
            footer,
            text="Cancel",
            palette=p,
            command=self.destroy,
            primary=False,
            width=96,
            height=34,
            radius=8,
        )
        cancel_btn.set_parent_bg(p["bg"])
        cancel_btn.pack(side="right")

    def _go_from_scope(self) -> None:
        if self.scope == "all" and not is_admin():
            launched = relaunch_as_admin(["--scope=all", "--step=2"])
            if launched:
                self.destroy()
            else:
                self._show_notice(
                    "Administrator Approval Needed",
                    "Administrator approval was cancelled or unavailable. You can select Current User Only instead.",
                )
            return
        self.step = 2
        self._render_step()

    def _render_options_step(self) -> None:
        p = self.palette
        scope_label = "All Users" if self.scope == "all" else "Current User"

        path_card = RoundedCard(self.body_frame, p, radius=10, padding=(14, 10, 14, 10))
        path_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            path_card.inner,
            text=f"Destination Folder ({scope_label})",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        row = tk.Frame(path_card.inner, bg=p["surface"])
        row.pack(fill="x")

        entry = tk.Entry(
            row,
            textvariable=self.install_dir_var,
            bg=p["surface_alt"],
            fg=p["text"],
            insertbackground=p["text"],
            relief="solid",
            bd=1,
            font=("Segoe UI", 9),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)

        browse_btn = RoundedButton(
            row,
            text="Browse",
            palette=p,
            command=self._browse_dir,
            primary=False,
            width=84,
            height=30,
            radius=7,
        )
        browse_btn.set_parent_bg(p["surface"])
        browse_btn.pack(side="right")

        opts_card = RoundedCard(self.body_frame, p, radius=10, padding=(14, 10, 14, 10))
        opts_card.pack(fill="x")

        tk.Label(
            opts_card.inner,
            text="Shortcuts & Launch Options",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        for label, var in (
            ("Create Desktop shortcut", self.desktop_var),
            ("Create Start Menu shortcut", self.startmenu_var),
            (f"Launch {APP_DISPLAY_NAME} after installation", self.launch_var),
        ):
            cb = tk.Checkbutton(
                opts_card.inner,
                text=label,
                variable=var,
                bg=p["surface"],
                fg=p["text"],
                activebackground=p["surface"],
                activeforeground=p["text"],
                selectcolor=p["surface_alt"],
                font=("Segoe UI", 9),
                anchor="w",
                highlightthickness=0,
            )
            cb.pack(fill="x", pady=2)

        footer = tk.Frame(self.body_frame, bg=p["bg"])
        footer.pack(fill="x", side="bottom")

        install_btn = RoundedButton(
            footer,
            text="Install",
            palette=p,
            command=self._start_install,
            primary=True,
            width=112,
            height=34,
            radius=8,
        )
        install_btn.set_parent_bg(p["bg"])
        install_btn.pack(side="right")

        back_btn = RoundedButton(
            footer,
            text="Back",
            palette=p,
            command=lambda: self._set_step(1),
            primary=False,
            width=92,
            height=34,
            radius=8,
        )
        back_btn.set_parent_bg(p["bg"])
        back_btn.pack(side="right", padx=(0, 8))

    def _set_step(self, step: int) -> None:
        self.step = step
        self._render_step()

    def _browse_dir(self) -> None:
        current = self.install_dir_var.get().strip() or str(default_install_dir(self.scope))
        chosen = filedialog.askdirectory(
            initialdir=current, title=f"Select Folder for {APP_DISPLAY_NAME}", parent=self
        )
        if chosen:
            chosen_path = Path(chosen)
            if chosen_path.name != APP_DISPLAY_NAME:
                chosen_path = chosen_path / APP_DISPLAY_NAME
            self.install_dir_var.set(str(chosen_path))

    def _render_progress_step(self) -> None:
        p = self.palette
        card = RoundedCard(self.body_frame, p, radius=10, padding=(14, 14, 14, 14))
        card.pack(fill="x")

        tk.Label(
            card.inner,
            text=f"Installing {APP_DISPLAY_NAME}...",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        self.progress_bar = RoundedProgressBar(card.inner, p, height=14, radius=7)
        self.progress_bar.set_parent_bg(p["surface"])
        self.progress_bar.pack(fill="x", pady=(0, 8))

        tk.Label(
            card.inner,
            textvariable=self.status_var,
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")

    def _start_install(self) -> None:
        target_dir = Path(self.install_dir_var.get().strip())
        if not str(target_dir).strip():
            self._show_notice("Invalid Folder", "Please choose a valid installation folder.")
            return

        payload = find_bundled_payload()
        if payload is None:
            self._show_notice(
                "Missing Application File",
                "Bundled application executable was not found inside the installer.",
            )
            return

        if is_process_running(INSTALLED_APP_FILENAME) or is_process_running("Sys-Copy-v0.1.exe"):
            self._show_notice(
                f"{APP_DISPLAY_NAME} Is Running",
                f"{APP_DISPLAY_NAME} is currently running. Please close it before continuing.",
            )
            return

        self.installing = True
        self.step = 3
        self._render_step()

        threading.Thread(
            target=self._run_install_worker,
            args=(payload, target_dir),
            daemon=True,
        ).start()

    def _update_progress_ui(self, fraction: float, message: str) -> None:
        def apply() -> None:
            self.status_var.set(message)
            if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
                self.progress_bar.set_progress(fraction)

        self.after(0, apply)

    def _run_install_worker(self, payload: Path, target_dir: Path) -> None:
        try:
            self._update_progress_ui(0.15, "Creating destination directory...")
            target_dir.mkdir(parents=True, exist_ok=True)

            installed_exe = target_dir / INSTALLED_APP_FILENAME
            self._update_progress_ui(0.45, f"Copying {APP_DISPLAY_NAME}...")
            copy_file_with_retry(payload, installed_exe)

            for icon_name in ("iicon.ico", "iicon.png", "iicon.bmp"):
                src_icon = get_resource_path(icon_name)
                if src_icon.exists():
                    copy_file_with_retry(src_icon, target_dir / icon_name)

            uninstaller_exe = target_dir / UNINSTALLER_FILENAME
            self._update_progress_ui(0.65, "Preparing uninstaller...")
            if getattr(sys, "frozen", False):
                copy_file_with_retry(Path(sys.executable), uninstaller_exe)

            if self.desktop_var.get():
                self._update_progress_ui(0.75, "Creating Desktop shortcut...")
                if self.scope == "all":
                    public_desktop = Path(os.environ.get("PUBLIC") or r"C:\Users\Public") / "Desktop"
                    desk_lnk = public_desktop / f"{APP_DISPLAY_NAME}.lnk"
                else:
                    desk_lnk = Path.home() / "Desktop" / f"{APP_DISPLAY_NAME}.lnk"
                create_shortcut_lnk(desk_lnk, installed_exe, target_dir, installed_exe)

            if self.startmenu_var.get():
                self._update_progress_ui(0.85, "Creating Start Menu shortcut...")
                if self.scope == "all":
                    prog_data = Path(os.environ.get("ProgramData") or r"C:\ProgramData")
                    sm_dir = prog_data / r"Microsoft\Windows\Start Menu\Programs" / APP_DISPLAY_NAME
                else:
                    app_data = Path(os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming"))
                    sm_dir = app_data / r"Microsoft\Windows\Start Menu\Programs" / APP_DISPLAY_NAME
                create_shortcut_lnk(sm_dir / f"{APP_DISPLAY_NAME}.lnk", installed_exe, target_dir, installed_exe)
                if uninstaller_exe.exists():
                    create_shortcut_lnk(
                        sm_dir / f"Uninstall {APP_DISPLAY_NAME}.lnk",
                        uninstaller_exe,
                        target_dir,
                        uninstaller_exe,
                        arguments=f'--uninstall --scope={self.scope} --dir="{target_dir}"',
                    )

            self._update_progress_ui(0.95, "Registering installation...")
            if uninstaller_exe.exists():
                register_uninstall_entry(self.scope, target_dir, installed_exe, uninstaller_exe)

            self._update_progress_ui(1.0, "Installation complete.")
            self.after(200, lambda: self._on_install_finished(installed_exe))
        except Exception as exc:
            err_msg = str(exc)
            self.after(0, lambda: self._on_install_failed(err_msg))

    def _on_install_failed(self, err_msg: str) -> None:
        self.installing = False
        self.step = 2
        self._render_step()
        self._show_notice("Installation Failed", err_msg)

    def _on_install_finished(self, installed_exe: Path) -> None:
        self.installing = False
        if self.launch_var.get():
            self._launch_app_and_close(installed_exe)
        else:
            self.step = 4
            self._render_step()

    def _launch_app_and_close(self, installed_exe: Path) -> None:
        try:
            subprocess.Popen(
                [str(installed_exe)],
                cwd=str(installed_exe.parent),
                close_fds=True,
            )
        except Exception as exc:
            self.step = 4
            self._render_step()
            self._show_notice(
                "Launch Notice",
                f"{APP_DISPLAY_NAME} was installed, but failed to launch automatically:\n{exc}",
            )
            return

        self.after(500, self.destroy)

    def _render_done_step(self) -> None:
        p = self.palette
        card = RoundedCard(self.body_frame, p, radius=10, padding=(14, 14, 14, 14))
        card.pack(fill="x")

        tk.Label(
            card.inner,
            text=f"{APP_DISPLAY_NAME} Installed",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        tk.Label(
            card.inner,
            text=f"Installed to: {self.install_dir_var.get()}",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=510,
            justify="left",
        ).pack(fill="x")

        footer = tk.Frame(self.body_frame, bg=p["bg"])
        footer.pack(fill="x", side="bottom")
        finish_btn = RoundedButton(
            footer,
            text="Finish",
            palette=p,
            command=self.destroy,
            primary=True,
            width=104,
            height=34,
            radius=8,
        )
        finish_btn.set_parent_bg(p["bg"])
        finish_btn.pack(side="right")


class UninstallerApp(tk.Tk):
    def __init__(self, scope: str, target_dir_str: str) -> None:
        super().__init__()
        self.dark = not is_windows_light_theme()
        self.palette = DARK_PALETTE if self.dark else LIGHT_PALETTE
        self.scope = scope if scope in ("user", "all") else "user"
        self.target_dir = Path(target_dir_str) if target_dir_str else default_install_dir(self.scope)

        self.reason_var = tk.StringVar(value="")
        self.note_var = tk.StringVar(value="")
        self.open_feedback_var = tk.BooleanVar(value=False)

        self.title(f"Uninstall {APP_DISPLAY_NAME}")
        self.configure(bg=self.palette["bg"])
        self.resizable(False, False)

        self._load_window_icon()
        self._center_window(WINDOW_WIDTH, WINDOW_HEIGHT)
        apply_title_bar_theme(self, self.dark)

        root_frame = tk.Frame(self, bg=self.palette["bg"], padx=16, pady=14)
        root_frame.pack(fill="both", expand=True)

        header = tk.Frame(root_frame, bg=self.palette["bg"])
        header.pack(fill="x")
        tk.Label(
            header,
            text=f"Uninstall {APP_DISPLAY_NAME}",
            bg=self.palette["bg"],
            fg=self.palette["text"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(side="left")

        info_btn = RoundedButton(
            header,
            text="!",
            palette=self.palette,
            command=lambda: InformationsModal(self, self.palette, self.dark),
            primary=False,
            width=32,
            height=30,
            radius=7,
        )
        info_btn.set_parent_bg(self.palette["bg"])
        info_btn.pack(side="right")

        p = self.palette

        reason_card = RoundedCard(root_frame, p, radius=10, padding=(14, 10, 14, 10))
        reason_card.pack(fill="x", pady=(10, 10))

        tk.Label(
            reason_card.inner,
            text="Reason for uninstalling (optional)",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        grid = tk.Frame(reason_card.inner, bg=p["surface"])
        grid.pack(fill="x")

        for idx, label in enumerate(UNINSTALL_REASONS):
            rb = tk.Radiobutton(
                grid,
                text=label,
                variable=self.reason_var,
                value=label,
                bg=p["surface"],
                fg=p["text"],
                activebackground=p["surface"],
                activeforeground=p["text"],
                selectcolor=p["surface_alt"],
                font=("Segoe UI", 9),
                anchor="w",
                highlightthickness=0,
            )
            rb.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 20), pady=2)

        tk.Label(
            reason_card.inner,
            text="Additional note (optional)",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(6, 3))

        tk.Entry(
            reason_card.inner,
            textvariable=self.note_var,
            bg=p["surface_alt"],
            fg=p["text"],
            insertbackground=p["text"],
            relief="solid",
            bd=1,
            font=("Segoe UI", 9),
        ).pack(fill="x", ipady=3)

        fb_card = RoundedCard(root_frame, p, radius=10, padding=(14, 10, 14, 10))
        fb_card.pack(fill="x")

        tk.Checkbutton(
            fb_card.inner,
            text="Open feedback link in browser with my optional reason & note",
            variable=self.open_feedback_var,
            bg=p["surface"],
            fg=p["text"],
            activebackground=p["surface"],
            activeforeground=p["text"],
            selectcolor=p["surface_alt"],
            font=("Segoe UI", 9),
            anchor="w",
            highlightthickness=0,
        ).pack(fill="x")

        tk.Label(
            fb_card.inner,
            text="Nothing is sent automatically; only what you enter is pre-filled if checked.",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        footer = tk.Frame(root_frame, bg=p["bg"])
        footer.pack(fill="x", side="bottom")

        uninst_btn = RoundedButton(
            footer,
            text="Uninstall",
            palette=p,
            command=self._perform_uninstall,
            primary=True,
            width=112,
            height=34,
            radius=8,
        )
        uninst_btn.set_parent_bg(p["bg"])
        uninst_btn.pack(side="right")

        cancel_btn = RoundedButton(
            footer,
            text="Cancel",
            palette=p,
            command=self.destroy,
            primary=False,
            width=96,
            height=34,
            radius=8,
        )
        cancel_btn.set_parent_bg(p["bg"])
        cancel_btn.pack(side="right", padx=(0, 8))

    def _show_notice(
        self,
        heading: str,
        message: str,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        CustomNoticeModal(
            self,
            self.palette,
            self.dark,
            title=f"Uninstall {APP_DISPLAY_NAME}",
            heading=heading,
            message=message,
            on_close=on_close,
        )

    def _load_window_icon(self) -> None:
        png_path = get_resource_path("iicon.png")
        ico_path = get_resource_path("iicon.ico")
        if png_path.exists():
            try:
                self._icon_img = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self._icon_img)
                return
            except Exception:
                pass
        if ico_path.exists():
            try:
                self.iconbitmap(default=str(ico_path))
            except Exception:
                pass

    def _center_window(self, width: int, height: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _perform_uninstall(self) -> None:
        if is_process_running(INSTALLED_APP_FILENAME) or is_process_running("Sys-Copy-v0.1.exe"):
            self._show_notice(
                f"{APP_DISPLAY_NAME} Is Running",
                f"Please close {APP_DISPLAY_NAME} before uninstalling.",
            )
            return

        if self.open_feedback_var.get():
            reason = self.reason_var.get().strip() or "Not specified"
            note = self.note_var.get().strip()
            body_lines = [f"Uninstall Reason: {reason}"]
            if note:
                body_lines.append(f"Note: {note}")
            query = urllib.parse.urlencode(
                {
                    "title": f"Uninstall Feedback — {APP_DISPLAY_NAME}",
                    "body": "\n".join(body_lines),
                }
            )
            try:
                webbrowser.open(f"{FEEDBACK_BASE_URL}?{query}")
            except Exception:
                pass

        remove_uninstall_entry(self.scope)

        shortcut_paths = [
            Path.home() / "Desktop" / f"{APP_DISPLAY_NAME}.lnk",
            Path(os.environ.get("PUBLIC") or r"C:\Users\Public") / "Desktop" / f"{APP_DISPLAY_NAME}.lnk",
            Path(os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming"))
            / r"Microsoft\Windows\Start Menu\Programs"
            / APP_DISPLAY_NAME,
            Path(os.environ.get("ProgramData") or r"C:\ProgramData")
            / r"Microsoft\Windows\Start Menu\Programs"
            / APP_DISPLAY_NAME,
        ]
        for sp in shortcut_paths:
            try:
                if sp.is_dir():
                    shutil.rmtree(sp, ignore_errors=True)
                elif sp.exists():
                    sp.unlink(missing_ok=True)
            except Exception:
                pass

        if self.target_dir.exists():
            cmd = f'ping 127.0.0.1 -n 3 > nul & rmdir /s /q "{self.target_dir}"'
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(
                ["cmd.exe", "/c", cmd],
                startupinfo=startupinfo,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

        self._show_notice(
            "Uninstall Complete",
            f"{APP_DISPLAY_NAME} has been uninstalled.",
            on_close=self.destroy,
        )


def run_uninstaller(argv: list[str]) -> int:
    enable_dpi_awareness()
    scope = "user"
    target_dir_str = ""
    for arg in argv:
        if arg.startswith("--scope="):
            val = arg.split("=", 1)[1].strip()
            if val in ("user", "all"):
                scope = val
        elif arg.startswith("--dir="):
            target_dir_str = arg.split("=", 1)[1].strip().strip('"')

    if scope == "all" and not is_admin():
        relaunch_as_admin(["--uninstall", "--scope=all", f"--dir={target_dir_str}"])
        return 0

    app = UninstallerApp(scope=scope, target_dir_str=target_dir_str)
    app.mainloop()
    return 0


def parse_args(argv: list[str]) -> tuple[Optional[str], int]:
    scope: Optional[str] = None
    step = 1
    for arg in argv:
        if arg.startswith("--scope="):
            val = arg.split("=", 1)[1].strip()
            if val in ("user", "all"):
                scope = val
        elif arg.startswith("--step="):
            try:
                step = max(1, min(4, int(arg.split("=", 1)[1].strip())))
            except ValueError:
                step = 1
    return scope, step


def main() -> None:
    if "--uninstall" in sys.argv[1:]:
        sys.exit(run_uninstaller(sys.argv[1:]))
    enable_dpi_awareness()
    scope, step = parse_args(sys.argv[1:])
    app = InstallerApp(initial_scope=scope, start_step=step)
    app.mainloop()


if __name__ == "__main__":
    main()