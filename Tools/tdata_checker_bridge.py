"""Headless TData checker bridge for TSP68 Checker (uses tdtt.py engine)."""
import argparse
import importlib.util
import json
import sys
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path


def load_tdtt():
    here = Path(__file__).resolve().parent
    for candidate in [here / "tdtt.py", Path.home() / "Desktop" / "tdtt.py"]:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("tdtt", candidate)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError("tdtt.py not found next to bridge or on Desktop")


def load_proxies(proxy_file: str):
    if not proxy_file:
        return []
    proxies = []
    for line in Path(proxy_file).read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line:
            proto = line.split("://")[0]
            rest = line.split("://", 1)[1]
            ptype = 2 if "socks5" in proto else (1 if "socks4" in proto else 3)
            if "@" in rest:
                cred, hp = rest.rsplit("@", 1)
                user, pw = cred.split(":", 1) if ":" in cred else (cred, "")
                host, port = hp.rsplit(":", 1)
                proxies.append((ptype, host, int(port), True, user, pw))
            else:
                host, port = rest.rsplit(":", 1)
                proxies.append((ptype, host, int(port)))
        elif ":" in line:
            parts = line.split(":")
            if len(parts) == 2:
                proxies.append((2, parts[0], int(parts[1])))
            elif len(parts) >= 4:
                proxies.append((2, parts[0], int(parts[1]), True, parts[2], parts[3]))
    return proxies


def to_json_safe(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [to_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_json_safe(v) for k, v in value.items()}
    return str(value)


def account_to_dict(acc):
    return to_json_safe(asdict(acc))


def emit_progress(phase, current, total, target, detail=""):
    msg = f"PROGRESS|{phase}|{current}|{total}|{target}|{detail}"
    print(msg, file=sys.stderr, flush=True)


def write_output(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False, default=str)
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="+", required=True)
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--passcode", default="")
    parser.add_argument("--proxy-file", default="")
    parser.add_argument("--deep", action="store_true", default=True)
    args = parser.parse_args()

    tdtt = load_tdtt()
    proc = tdtt.TDataProcessor()
    proxies = load_proxies(args.proxy_file)

    folders = []
    emit_progress("scan", 0, len(args.roots), "", "Searching tdata folders...")
    for i, root in enumerate(args.roots, start=1):
        emit_progress("scan", i, len(args.roots), root, "Scanning root")
        folders.extend(proc.find_tdata(root, args.deep))
    folders = sorted(set(folders))
    emit_progress("scan_done", len(folders), len(folders), "", f"Found {len(folders)} tdata folder(s)")

    results = []
    total = max(len(folders), 1)
    for i, folder in enumerate(folders, start=1):
        proxy = proxies[(i - 1) % len(proxies)] if proxies else None
        emit_progress("check", i, total, folder, "Telegram validation")
        try:
            acc = proc.check_sync(folder, passcode=args.passcode, proxy=proxy)
            results.append(account_to_dict(acc))
            status = "VALID" if acc.is_valid else (acc.error_message or "invalid")
            emit_progress("result", i, total, folder, status)
            if acc.is_valid:
                summary = account_to_dict(acc)
                summary.pop("session_string", None)
                payload = json.dumps(summary, ensure_ascii=False)
                print(f"ACCOUNT|{folder}|{payload}", file=sys.stderr, flush=True)
        except Exception as ex:
            results.append({
                "tdata_path": folder,
                "is_valid": False,
                "error_message": str(ex)[:200],
            })
            emit_progress("result", i, total, folder, str(ex)[:120])

    write_output({"folders": folders, "accounts": results})


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        emit_progress("error", 0, 1, "", str(ex)[:200])
        write_output({"folders": [], "accounts": [], "error": str(ex), "trace": traceback.format_exc()[-2000:]})
        sys.exit(1)
