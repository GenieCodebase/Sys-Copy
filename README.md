# Sys Copy

**Version:** 0.1  
**Created by:** Genie Codebase [GC]  
**Repository:** https://github.com/GenieCodebase/Sys-Copy  
**YouTube:** https://youtube.com/@geniecodebase?si=16ZkbBJPVI7Cv4U2

`Sys Copy` is a lightweight Windows desktop utility built with Python and Tkinter that collects live Windows system and hardware diagnostics, installed desktop applications, Python PIP package lists, System/User `PATH` entries, and environment variables for instant, formatted clipboard copying.

---

## Features

* **Live System & Device Diagnostics:** Reads OS edition, version, build, architecture, install date, device name, current user, hardware/BIOS/motherboard details, CPU, RAM, GPU, and storage drives.
* **Python PIP List:** Detects installed Python interpreters and lists installed `pip` packages per interpreter.
* **Installed Apps:** Lists installed desktop applications with version and publisher metadata from the Windows Registry.
* **System & User PATH List:** Separates and numbers System `PATH` and User `PATH` entries for quick inspection.
* **Environment Variables:** Displays System and User environment variables with automatic redaction for sensitive/secret variable names.
* **Privacy-First Redaction:** Masks sensitive identifiers such as Product ID, secret-like environment variables, and `\Users\<Name>` paths while keeping the active `Current User` name visible.
* **One-Click Clipboard Actions:** Copy individual sections, copy all sections at once, or copy all sections except System & Device Info.
* **Modern Windows UI:** High-DPI awareness, automatic Windows Dark/Light theme detection and live switching, collapsible sections, and custom window styling.
* **Local-Only Data:** We do not collect or upload any of your data; your data stays strictly on your PC.

---

## Project Files

* `sys_copy.py` — Main application source code (`v0.1`).
* `Sys-Copy-v0.1.iss` — Inno Setup 7 script for building the Windows installer (`Sys-Copy-v0.1-Setup.exe`).
* `icon.png` — Application icon loaded from the same directory as the script or executable.
* `icon.ico` — Icon file used by the Windows installer executable (`SetupIconFile`).

---

## Running from Source

1. Ensure **Python 3.12** (or a compatible Python 3.x build on Windows) is installed.
2. Place `icon.png` in the same folder as `sys_copy.py`.
3. Run the application:

```powershell
python sys_copy.py