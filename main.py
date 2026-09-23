#!/usr/bin/env python3
#
# Originally created by doxlngs — github.com/doxlngs
# Licensed under the MIT License (see LICENSE file)
#
import argparse
import itertools
import os
import queue
import random
import re
import string
import sys
import threading
import time
from pathlib import Path

import colorama
import requests
from colorama import Style

colorama.init(autoreset=True)

try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
    def get_ua():
        return _ua.random
except Exception:
    UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
    ]
    def get_ua():
        return random.choice(UAS)

GITHUB = "github.com/doxlngs"
DISCORD = "@doxings"
GRAD = ["#9B59B6", "#C070D0", "#E040FB", "#F06292", "#FF4081"]
GREEN = "#00FF88"


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def fg(r, g, b):
    return "\033[38;2;%d;%d;%dm" % (r, g, b)

def paint(text, stops=GRAD, bold=False):
    cols = [rgb(c) for c in stops]
    n = max(len(text) - 1, 1)
    out = "\033[1m" if bold else ""
    for i, ch in enumerate(text):
        pos = i / n * (len(cols) - 1)
        k = min(int(pos), len(cols) - 2)
        f = pos - k
        a, b = cols[k], cols[k + 1]
        out += fg(*[int(a[j] + (b[j] - a[j]) * f) for j in range(3)]) + ch
    return out + Style.RESET_ALL

def dim(text):
    return "%s%s%s" % (Style.DIM, text, Style.RESET_ALL)


BANNER = r"""
███████╗███╗   ██╗██╗██████╗ ███████╗██████╗
██╔════╝████╗  ██║██║██╔══██╗██╔════╝██╔══██╗
███████╗██╔██╗ ██║██║██████╔╝█████╗  ██████╔╝
╚════██║██║╚██╗██║██║██╔═══╝ ██╔══╝  ██╔══██╗
███████║██║ ╚████║██║██║     ███████╗██║  ██║
╚══════╝╚═╝  ╚═══╝╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝"""

def banner():
    os.system("cls" if os.name == "nt" else "clear")
    for line in BANNER.splitlines():
        print("  " + paint(line, bold=True))
    print()
    print("  " + paint("discord · tiktok") + dim("  ·  ") + paint(DISCORD) + dim("  ·  ") + paint(GITHUB))
    print("  " + dim("─" * 52))

def head(title):
    print("\n  " + paint(title, bold=True))
    print("  " + dim("─" * len(title)))

def ask(msg):
    return input("\n  " + paint("›") + " " + msg + " ").strip()

def ask_num(msg, cast, keep):
    raw = ask(msg)
    if not raw:
        return keep
    try:
        return cast(raw)
    except ValueError:
        say_bad("not a number, keeping " + str(keep))
        return keep

def item(key, label, note=""):
    line = "  %s  %s" % (paint("[%s]" % key, bold=True), label)
    if note:
        line += "  " + dim(note)
    print(line)

def say_ok(m):
    print("  %s+%s %s" % (fg(64, 255, 128), Style.RESET_ALL, m))

def say_info(m):
    print("  %s·%s %s" % (fg(150, 150, 170), Style.RESET_ALL, m))

def say_warn(m):
    print("  %s!%s %s" % (fg(255, 200, 0), Style.RESET_ALL, m))

def say_bad(m):
    print("  %sx%s %s" % (fg(255, 80, 80), Style.RESET_ALL, m))

def pause():
    input("\n  " + dim("enter to go back "))


def wipe():
    sys.stdout.write("\r\033[2K")

def out(msg):
    wipe()
    print(msg)

def bar(stats):
    done, total = stats["checked"], stats["total"]
    frac = done / total if total else 0
    n = int(frac * 24)
    txt = "%s%s  %d/%d  %.1f%%  hits %d" % ("█" * n, "░" * (24 - n), done, total, frac * 100, stats["available"])
    sys.stdout.write("\r  " + paint(txt))
    sys.stdout.flush()


PROXY_SOURCES = [
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=5000",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://proxylist.geonode.com/api/proxy-list?limit=200&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps",
]

PROXY_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")


def scrape_proxies(save_path="proxies.txt", timeout=8, validate=False):
    found_all = set()
    s = requests.Session()
    s.headers["User-Agent"] = get_ua()

    say_info("pulling from %d sources" % len(PROXY_SOURCES))
    for url in PROXY_SOURCES:
        host = url.split("/")[2]
        try:
            r = s.get(url, timeout=timeout)
            if "geonode" in url:
                try:
                    rows = r.json().get("data", [])
                    for e in rows:
                        if e.get("ip") and e.get("port"):
                            found_all.add("%s:%s" % (e["ip"], e["port"]))
                    say_ok("%-28s %d" % (host, len(rows)))
                    continue
                except Exception:
                    pass
            hits = PROXY_RE.findall(r.text)
            for ip, port in hits:
                found_all.add("%s:%s" % (ip, port))
            say_ok("%-28s %d" % (host, len(hits)))
        except Exception:
            say_bad("%-28s failed" % host)

    proxies = list(found_all)
    say_info("{:,} unique".format(len(proxies)))

    if validate:
        proxies = validate_proxies(proxies)
        say_info("{:,} alive".format(len(proxies)))

    with open(save_path, "w") as f:
        for p in proxies:
            f.write("http://%s\n" % p)
    say_ok("saved to " + save_path)
    return ["http://%s" % p for p in proxies]


def validate_proxies(proxies, timeout=5):
    alive = []
    lock = threading.Lock()
    q = queue.Queue()
    for p in proxies:
        q.put(p)
    done = [0]

    def run():
        while True:
            try:
                p = q.get(timeout=1)
            except queue.Empty:
                break
            try:
                r = requests.get(
                    "http://www.google.com",
                    proxies={"http": "http://" + p, "https": "http://" + p},
                    timeout=timeout,
                )
                if r.status_code == 200:
                    with lock:
                        alive.append(p)
            except Exception:
                pass
            with lock:
                done[0] += 1
                if done[0] % 100 == 0:
                    say_info("%d/%d checked, %d alive" % (done[0], len(proxies), len(alive)))
            q.task_done()

    ts = [threading.Thread(target=run, daemon=True) for _ in range(50)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return alive


def auto_update_proxies(interval=300, save_path="proxies.txt"):
    def loop():
        while True:
            time.sleep(interval)
            scrape_proxies(save_path=save_path)
    threading.Thread(target=loop, daemon=True).start()


CHARS = string.ascii_lowercase + string.digits

def generate_usernames(modes):
    pool = set()
    for mode in modes:
        mode = mode.upper()
        if mode == "4C":
            gen = itertools.product(CHARS, repeat=4)
        elif mode == "4L":
            gen = itertools.product(string.ascii_lowercase, repeat=4)
        elif mode == "3C":
            gen = itertools.product(CHARS, repeat=3)
        elif mode == "3L":
            gen = itertools.product(string.ascii_lowercase, repeat=3)
        else:
            say_warn("skipping unknown mode " + mode)
            continue
        before = len(pool)
        for combo in gen:
            pool.add("".join(combo))
        say_info("{}: {:,}".format(mode, len(pool) - before))
    return list(pool)


def load_wordlist(path):
    p = Path(path)
    if not p.exists():
        say_bad("wordlist not found: " + path)
        return []
    with open(p) as f:
        return [l.strip() for l in f if l.strip()]


DISCORD_API = "https://discord.com/api/v9/auth/register"
CHECK_DELAY = 1.2

def check_discord(name, session, proxy):
    payload = {
        "username": name,
        "password": "DiscordChecker!9",
        "email": name + "@mailinator.com",
        "consent": True,
        "date_of_birth": "1995-01-01",
        "gift_code_sku_id": None,
        "captcha_key": None,
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": get_ua(),
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/register",
    }
    px = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = session.post(DISCORD_API, json=payload, headers=headers, proxies=px, timeout=10)
        if r.status_code == 429:
            return "rate_limited"
        errors = r.json().get("errors", {})
        for e in errors.get("username", {}).get("_errors", []):
            if e.get("code", "") in ("USERNAME_ALREADY_TAKEN", "USERNAME_TOO_MANY_USERS"):
                return "taken"
        if r.status_code in (200, 201):
            return "available"
        if "username" not in errors and r.status_code == 400:
            return "available"
        return "taken"
    except requests.exceptions.ProxyError:
        return "proxy_error"
    except requests.exceptions.Timeout:
        return "timeout"
    except Exception as e:
        return "error:%s" % e


TT_NAME_RE = re.compile(r"^[a-z0-9_.]{2,24}$")
TT_STATUS_RE = re.compile(r'"statusCode":\s*(\d+)')

def check_tiktok(name, session, proxy):
    name = name.lower()
    if not TT_NAME_RE.match(name) or name.endswith("."):
        return "invalid"
    headers = {
        "User-Agent": get_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    px = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = session.get("https://www.tiktok.com/@" + name, headers=headers, proxies=px, timeout=10)
        if r.status_code in (403, 429):
            return "rate_limited"
        if r.status_code == 404:
            return "available"
        if r.status_code != 200:
            return "error:http %d" % r.status_code

        body = r.text
        i = body.find('"webapp.user-detail"')
        m = TT_STATUS_RE.search(body[i:i + 3000] if i != -1 else body)
        if m:
            code = int(m.group(1))
            if code in (10202, 10221):
                return "available"
            if code in (0, 10222):
                return "taken"
            return "error:tiktok code %d" % code
        if "captcha" in body.lower() or "verify" in body.lower():
            return "rate_limited"
        if "Couldn't find this account" in body:
            return "available"
        return "error:unreadable page"
    except requests.exceptions.ProxyError:
        return "proxy_error"
    except requests.exceptions.Timeout:
        return "timeout"
    except Exception as e:
        return "error:%s" % e


PLATFORMS = {
    "discord": ("Discord", check_discord),
    "tiktok": ("TikTok", check_tiktok),
}


def worker(tasks, results, proxies, out_file, lock, stats, checker):
    session = requests.Session()
    cycle = itertools.cycle(proxies) if proxies else itertools.repeat(None)

    while True:
        try:
            name = tasks.get(timeout=2)
        except queue.Empty:
            break

        status = checker(name, session, next(cycle))

        with lock:
            if status == "rate_limited":
                stats["rate_limited"] += 1
                tasks.put(name)
                tasks.task_done()
                time.sleep(CHECK_DELAY * 4)
                continue

            stats["checked"] += 1
            if status == "available":
                stats["available"] += 1
                results.append(name)
                out("  %s  %s" % (paint("HIT", [GREEN, "#00CCFF"], True), name))
                if out_file:
                    with open(out_file, "a") as f:
                        f.write(name + "\n")
            elif status in ("proxy_error", "timeout"):
                stats["failed"] += 1
            elif status.startswith("error"):
                out("  %sx%s %s  %s" % (fg(255, 80, 80), Style.RESET_ALL, name, dim(status)))
            bar(stats)

        tasks.task_done()
        time.sleep(CHECK_DELAY)

    session.close()


def run_checker(usernames, proxies, out_file, threads=5, platform="discord"):
    if not usernames:
        say_warn("nothing to check")
        return

    label, checker = PLATFORMS[platform]
    if out_file == "hits.txt":
        out_file = "hits_%s.txt" % platform

    tasks = queue.Queue()
    for u in usernames:
        tasks.put(u)

    results = []
    lock = threading.Lock()
    stats = {"checked": 0, "total": len(usernames), "available": 0, "rate_limited": 0, "failed": 0}

    head("Running  ·  " + label)
    say_info("{:,} names   {} threads   {} proxies".format(len(usernames), threads, len(proxies)))
    print()

    ts = [
        threading.Thread(target=worker, args=(tasks, results, proxies, out_file, lock, stats, checker), daemon=True)
        for _ in range(min(threads, len(usernames)))
    ]
    try:
        for t in ts:
            t.start()
        for t in ts:
            while t.is_alive():
                t.join(0.5)
    except KeyboardInterrupt:
        wipe()
        say_warn("stopped early")

    wipe()
    head("Done")
    say_ok("available    %d" % stats["available"])
    say_info("checked      %d" % stats["checked"])
    say_info("rate limited %d" % stats["rate_limited"])
    say_info("proxy fails  %d" % stats["failed"])
    if out_file and stats["available"]:
        say_ok("saved to " + out_file)


SETTINGS = {
    "threads": 5,
    "delay": 1.2,
    "output_file": "hits.txt",
    "proxy_file": "proxies.txt",
}

def load_proxy_file(path):
    pf = Path(path)
    if not pf.exists():
        return None
    with open(pf) as f:
        return [l.strip() for l in f if l.strip()]


def menu_settings():
    banner()
    head("Settings")
    say_info("threads  %s" % SETTINGS["threads"])
    say_info("delay    %ss" % SETTINGS["delay"])
    say_info("output   %s" % SETTINGS["output_file"])
    say_info("proxies  %s" % SETTINGS["proxy_file"])
    print("\n  " + dim("leave blank to keep the current value"))
    SETTINGS["threads"] = ask_num("threads", int, SETTINGS["threads"])
    SETTINGS["delay"] = ask_num("delay (s)", float, SETTINGS["delay"])
    o = ask("output file")
    if o:
        SETTINGS["output_file"] = o
    p = ask("proxy file")
    if p:
        SETTINGS["proxy_file"] = p
    say_ok("saved")
    time.sleep(0.8)


def menu_scrape(validate=False):
    banner()
    head("Validate proxies" if validate else "Scrape proxies")
    scrape_proxies(save_path=SETTINGS["proxy_file"], validate=validate)
    pause()


def menu_autoupdate():
    banner()
    head("Auto-update proxies")
    interval = ask_num("interval in seconds (300)", int, 300)
    auto_update_proxies(interval=interval, save_path=SETTINGS["proxy_file"])
    say_ok("refreshing every %ds in the background" % interval)
    pause()


def menu_check():
    global CHECK_DELAY
    banner()
    head("Platform")
    item(1, "Discord")
    item(2, "TikTok")
    pick = ask("platform")
    if pick == "1":
        platform = "discord"
    elif pick == "2":
        platform = "tiktok"
    else:
        return

    head("Usernames")
    item(1, "Generate", "3L 3C 4L 4C")
    item(2, "Wordlist", "one name per line")
    src = ask("source")

    if src == "1":
        say_info("modes, space separated (3L 3C 4L 4C)")
        modes = ask("modes").split()
        if not modes:
            say_warn("no modes given")
            time.sleep(1)
            return
        usernames = generate_usernames(modes)
    elif src == "2":
        usernames = load_wordlist(ask("path"))
        if not usernames:
            time.sleep(1)
            return
        say_info("{:,} loaded".format(len(usernames)))
    else:
        return

    head("Proxies")
    item(1, "Saved file", SETTINGS["proxy_file"])
    item(2, "Scrape fresh")
    item(3, "None", "direct")
    psrc = ask("source")

    proxies = []
    if psrc == "1":
        proxies = load_proxy_file(SETTINGS["proxy_file"])
        if proxies is None:
            say_warn("no proxy file, going direct")
            proxies = []
        else:
            say_info("{:,} loaded".format(len(proxies)))
    elif psrc == "2":
        proxies = scrape_proxies(save_path=SETTINGS["proxy_file"])

    CHECK_DELAY = SETTINGS["delay"]
    run_checker(usernames, proxies, SETTINGS["output_file"], threads=SETTINGS["threads"], platform=platform)
    pause()


def interactive():
    while True:
        banner()
        print("  " + dim("threads %s  ·  delay %ss  ·  %s" % (SETTINGS["threads"], SETTINGS["delay"], SETTINGS["proxy_file"])))
        print()
        item(1, "Check usernames", "discord / tiktok")
        item(2, "Scrape proxies")
        item(3, "Scrape + validate")
        item(4, "Auto-update proxies")
        item(5, "Settings")
        item(0, "Exit")

        c = ask("")

        if c == "1":
            menu_check()
        elif c == "2":
            menu_scrape()
        elif c == "3":
            menu_scrape(validate=True)
        elif c == "4":
            menu_autoupdate()
        elif c == "5":
            menu_settings()
        elif c == "0":
            print("\n  " + paint(DISCORD) + dim("  ·  ") + paint(GITHUB) + "\n")
            sys.exit(0)


def cli():
    global CHECK_DELAY
    p = argparse.ArgumentParser(description="sniper - %s / %s" % (DISCORD, GITHUB))
    p.add_argument("-P", "--platform", choices=list(PLATFORMS), default="discord")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("-g", "--generate", nargs="+", metavar="MODE")
    src.add_argument("-w", "--wordlist", metavar="FILE")
    p.add_argument("-p", "--proxies", metavar="FILE")
    p.add_argument("-s", "--scrape", action="store_true", help="scrape proxies first")
    p.add_argument("-v", "--validate", action="store_true", help="validate scraped proxies")
    p.add_argument("-o", "--output", default="hits.txt")
    p.add_argument("-t", "--threads", type=int, default=5)
    p.add_argument("-d", "--delay", type=float, default=1.2)
    args = p.parse_args()

    CHECK_DELAY = args.delay
    banner()

    proxies = []
    if args.scrape:
        proxies = scrape_proxies(validate=args.validate)
    elif args.proxies:
        proxies = load_proxy_file(args.proxies)
        if proxies is None:
            say_bad("proxy file not found: " + args.proxies)
            proxies = []

    if args.generate:
        usernames = generate_usernames(args.generate)
    else:
        usernames = load_wordlist(args.wordlist)

    run_checker(usernames, proxies, args.output, threads=args.threads, platform=args.platform)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        interactive()
