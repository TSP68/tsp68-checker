TSP68 Checker - Tools / Python Setup
====================================

TData Checker can verify folder structure without Python.
Live Telegram validation requires Python 3.11 and packages below.

STEP 1 - Install Python 3.11.9
------------------------------
Download:
https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

Run the installer.
IMPORTANT: Check "Add python.exe to PATH" before clicking Install.

STEP 2 - Install packages (CMD)
-------------------------------
Press Win+R, type: cmd
Press Enter, then paste this single line:

pip install telethon opentele tgcrypto customtkinter Pillow python-socks

STEP 3 - Restart TSP68 Checker
-------------------------------
Close and reopen TSP68Checker.exe, then run TData Checker again.

Notes
-----
- Keep the Tools folder next to TSP68Checker.exe (do not delete tdtt.py or tdata_checker_bridge.py).
- If pip is not found, reopen CMD after Python install or use: py -3.11 -m pip install telethon opentele tgcrypto customtkinter Pillow python-socks
