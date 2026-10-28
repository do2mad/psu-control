#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
PSU Control – Mac-Server fuer das UNI-T UDP3305S-E
--------------------------------------------------
Kleiner lokaler Webserver (nur Python-Standardbibliothek), der eine
Bedienoberflaeche im Browser bereitstellt und die Befehle per SCPI
(TCP-Socket, Port 5025) an das UNI-T Netzteil weiterreicht.

Start:   python3 udp3305.py                 (Netzteil 192.168.0.137)
         python3 udp3305.py --host 192.168.0.50
         python3 udp3305.py --lan           (auch von iPhone/iPad im LAN erreichbar)
         python3 udp3305.py --sim           (Simulator, ohne Netzteil)
Dann im Browser:  http://localhost:8080
"""
import argparse
import hashlib
import concurrent.futures
import http.server
import ipaddress
import json
import os
import re
import socket
import socketserver
import sys
import threading
import time
import webbrowser

SCPI_PORT = 5025
APP_ID = "udp3305-control"
HERE = os.path.dirname(os.path.abspath(__file__))


def ui_file():
    """index.html liegt in der App neben diesem Skript, im Repository unter ../web."""
    for p in (os.path.join(HERE, "index.html"), os.path.join(HERE, "..", "web", "index.html")):
        if os.path.exists(p):
            return p
    raise FileNotFoundError("index.html nicht gefunden")


# --------------------------------------------------------------------------
# Einstellungen (letzte IP, zuletzt benutzte Geraete)
# --------------------------------------------------------------------------
def config_path():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/PSU Control")
        old = os.path.expanduser("~/Library/Application Support/UDP3305 Control/config.json")
        if not os.path.exists(os.path.join(base, "config.json")) and os.path.exists(old):
            os.makedirs(base, exist_ok=True)
            try:
                with open(old) as src, open(os.path.join(base, "config.json"), "w") as dst:
                    dst.write(src.read())   # Einstellungen der frueheren "UDP3305 Control" uebernehmen
            except OSError:
                pass
    else:
        base = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "psu-control")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "config.json")


def load_config():
    try:
        with open(config_path()) as f:
            c = json.load(f)
            if isinstance(c, dict):
                return c
    except (OSError, ValueError):
        pass
    return {}


def save_config(c):
    try:
        with open(config_path(), "w") as f:
            json.dump(c, f, indent=2)
    except OSError:
        pass


def remember_host(host, port, idn):
    c = load_config()
    c["host"], c["port"] = host, port
    rec = [r for r in c.get("recent", []) if r.get("host") != host]
    rec.insert(0, {"host": host, "port": port, "idn": idn})
    c["recent"] = rec[:8]
    save_config(c)


# --------------------------------------------------------------------------
# Netzwerksuche
# --------------------------------------------------------------------------
def local_ipv4s():
    ips = set()
    for probe in ("10.255.255.255", "192.168.255.255", "172.31.255.255"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((probe, 1))  # es wird nichts gesendet, nur die Route ermittelt
            ips.add(s.getsockname()[0])
            s.close()
        except OSError:
            pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith(("127.", "169.254.", "0.")))


def probe_idn(host, port, timeout=1.5):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(b"*IDN?\n")
        buf = b""
        while b"\n" not in buf and len(buf) < 512:
            d = s.recv(512)
            if not d:
                break
            buf += d
        return buf.decode("ascii", "replace").strip()


def scan_network(port=SCPI_PORT, skip=None, skip_idn=None):
    targets = []
    nets = set()
    for ip in local_ipv4s():
        net = ipaddress.ip_network(ip + "/24", strict=False)
        if net in nets:
            continue
        nets.add(net)
        targets += [str(h) for h in net.hosts() if str(h) != ip]

    def try_one(h):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.35)
        try:
            if s.connect_ex((h, port)) != 0:
                return None
        except OSError:
            return None
        finally:
            s.close()
        if h == skip and skip_idn:
            return {"host": h, "port": port, "idn": skip_idn}
        try:
            idn = probe_idn(h, port)
        except OSError:
            idn = ""
        return {"host": h, "port": port, "idn": idn or "(antwortet nicht auf *IDN?)"}

    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=96) as ex:
        for r in ex.map(try_one, targets):
            if r:
                found.append(r)
    found.sort(key=lambda r: ("UNI-T" not in r["idn"].upper(), tuple(int(x) for x in r["host"].split("."))))
    return {"networks": [str(n) for n in sorted(nets)], "found": found}

# Kanalnummern fuer [:SOURce#] laut Programmieranleitung
CH_NUM = {"CH1": 1, "CH2": 2, "CH3": 3, "SER": 5, "PARA": 6}
# Eingabegrenzen fuer die Oberflaeche (das Geraet begrenzt zusaetzlich selbst)
LIMITS = {
    "CH1": {"v": 32.0, "i": 5.2},
    "CH2": {"v": 32.0, "i": 5.2},
    "CH3": {"v": 6.2, "i": 3.2},
    "SER": {"v": 64.0, "i": 5.2},
    "PARA": {"v": 32.0, "i": 10.4},
}
NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def nums(s):
    return [float(x) for x in NUM_RE.findall(s or "")]


def last_num(s):
    n = nums(s)
    return n[-1] if n else None


def onoff(s):
    s = (s or "").strip().upper()
    return s in ("ON", "1")


# --------------------------------------------------------------------------
# SCPI ueber TCP
# --------------------------------------------------------------------------
class ScpiError(Exception):
    pass


class ScpiSocket:
    def __init__(self, host, port=SCPI_PORT, timeout=2.0, gap=0.01):
        self.host, self.port, self.timeout, self.gap = host, port, timeout, gap
        self.sock = None
        self.buf = b""
        self.lock = threading.RLock()
        self.last = 0.0

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None
        self.buf = b""

    def _connect(self):
        self.close()
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(self.timeout)
        self.sock = s

    def _drain(self):
        """Verwirft unerwartet anstehende Antworten, damit Abfragen synchron bleiben."""
        self.buf = b""
        self.sock.setblocking(False)
        try:
            while True:
                d = self.sock.recv(4096)
                if not d:
                    raise ConnectionError("Verbindung geschlossen")
        except (BlockingIOError, socket.timeout):
            pass
        finally:
            self.sock.settimeout(self.timeout)

    def _send(self, cmd):
        wait = self.gap - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.sock.sendall((cmd.strip() + "\n").encode("ascii", "replace"))
        self.last = time.monotonic()

    def _readline(self):
        while b"\n" not in self.buf:
            d = self.sock.recv(4096)
            if not d:
                raise ConnectionError("Verbindung geschlossen")
            self.buf += d
        line, _, self.buf = self.buf.partition(b"\n")
        return line.decode("ascii", "replace").strip()

    def _do(self, cmd, want):
        with self.lock:
            for attempt in (1, 2):
                try:
                    if self.sock is None:
                        self._connect()
                    self._drain()
                    self._send(cmd)
                    return self._readline() if want else None
                except (OSError, ConnectionError) as e:
                    self.close()
                    if attempt == 2:
                        raise ScpiError(f"{self.host}:{self.port} – {e}") from e

    def query(self, cmd):
        return self._do(cmd, True)

    def write(self, cmd):
        self._do(cmd, False)


# --------------------------------------------------------------------------
# Simulator (zum Testen ohne Netzteil)
# --------------------------------------------------------------------------
class SimScpi:
    def __init__(self):
        self.lock = threading.RLock()
        self.mode = "NORMAL"
        self.ch = {c: dict(v=5.0, i=1.0, ovp=33.0, ocp=5.5, ovp_on=False, ocp_on=False, out=False)
                   for c in CH_NUM}
        self.load = {"CH1": 10.0, "CH2": 4.0, "CH3": 2.0, "SER": 20.0, "PARA": 3.0}
        self.mem = {}
        self.errs = []
        self.pre = {n: {c: dict(v=[1.8, 2.5, 3.3, 5.0, 12.0][n - 1], i=1.0, ovp_on=False, ovp=33.0,
                                 ocp_on=False, ocp=5.5) for c in CH_NUM} for n in range(1, 6)}
        self.sys = dict(beep=True, bright=80, lock=False, klock=False, baud=9600)
        self.lan = dict(dhcp=False, ip="192.168.0.137", mask="255.255.255.0", gw="192.168.0.1")
        self.cur = "CH1"
        self.lst = {c: dict(g={}, start=0, count=1, cycles=1, end="OFF", run=None, info=None) for c in CH_NUM}
        self.dly = {c: dict(g={}, start=0, count=1, cycles=1, end="OFF", stop=("NONE", 0.0), run=None, info=None)
                    for c in CH_NUM}
        self.mem_l, self.mem_d = {}, {}

    # ---- LIST / DELAYER abspielen (wird vor jedem Befehl aufgerufen)
    def _tick(self):
        now = time.monotonic()
        for c in CH_NUM:
            for kind in ("lst", "dly"):
                L = getattr(self, kind)[c]
                if L["run"] is None:
                    continue
                default = (0.0, 0.0, 1.0) if kind == "lst" else (False, 1.0)
                seq = [L["g"].get(k, default) for k in range(L["start"], L["start"] + L["count"])]
                T = sum(max(0.1, x[-1]) for x in seq) or 1.0
                el = now - L["run"]
                cyc = int(el // T)
                d = self.ch[c]
                stop_hit = False
                if kind == "dly" and L["stop"][0] != "NONE":
                    v, i, _ = self._meas(c)
                    cond, val = L["stop"]
                    x = {"V": v, "C": i, "P": v * i}[cond[1]]
                    stop_hit = x < val if cond[0] == "<" else x > val
                if cyc >= L["cycles"] or stop_hit:
                    L["run"], L["info"] = None, None
                    if L["end"] == "OFF":
                        d["out"] = False
                    elif L["end"] == "ON":
                        d["out"] = True
                    continue
                pos, k = el - cyc * T, 0
                while k < len(seq) - 1 and pos >= max(0.1, seq[k][-1]):
                    pos -= max(0.1, seq[k][-1])
                    k += 1
                rest = (L["cycles"] - cyc - 1) * T + (sum(max(0.1, x[-1]) for x in seq[k:]) - pos)
                L["info"] = (rest, L["start"] + k, L["cycles"] - cyc - 1)
                if kind == "lst":
                    d["v"], d["i"] = seq[k][0], seq[k][1]
                    d["out"] = True
                else:
                    d["out"] = bool(seq[k][0])

    def _status(self, L):
        endp = L["start"] + L["count"] - 1
        if L["run"] is not None and L["info"]:
            rest, cur, cyc = L["info"]
            return f"ON,{rest:.1f},{cur},{endp},{cyc},{L['end']}"
        return f"OFF,0.0,{L['start']},{endp},0,{L['end']}"

    def _ch(self, tok):
        tok = (tok or "").upper().strip().rstrip(",")
        for c in CH_NUM:
            if tok == c:
                return c
        return None

    def _meas(self, c):
        d = self.ch[c]
        if not d["out"]:
            return 0.0, 0.0, "CV"
        import random
        r = self.load[c]
        i = d["v"] / r
        if i > d["i"]:
            i, v, m = d["i"], d["i"] * r, "CC"
        else:
            v, m = d["v"], "CV"
        v = max(0, v + random.uniform(-0.004, 0.004))
        i = max(0, i + random.uniform(-0.002, 0.002))
        return v, i, m

    def close(self):
        pass

    def _list_delay(self, head, arg, args):
        """LIST-, DELAYER-, INSTrument- und MEMory-Befehle. None = nicht zustaendig."""
        import copy
        hq, isq = head.rstrip("?"), head.endswith("?")
        if hq in (":INSTRUMENT:SELECT", ":INSTRUMENT:SELE", ":INSTRUMENT", ":INST:SEL", ":INST"):
            if isq:
                return self.cur
            self.cur = self._ch(arg) or self.cur
            return ""
        if hq == ":INSTRUMENT:NSELECT":
            if isq:
                return str(CH_NUM[self.cur])
            n = int(float(arg))
            self.cur = [k for k, v in CH_NUM.items() if v == n][0]
            return ""
        L, D = self.lst[self.cur], self.dly[self.cur]
        if hq in (":LISTOUT:STATE", ":LISTOUT"):
            if isq:
                return self._status(L)
            if onoff(arg):
                L["run"] = time.monotonic()
                self._tick()
            else:
                L["run"], L["info"] = None, None
            return ""
        if hq in (":DELAY:STATE", ":DELAY"):
            if isq:
                return self._status(D)
            if onoff(arg):
                D["run"] = time.monotonic()
                self._tick()
            else:
                D["run"], D["info"] = None, None
            return ""
        if hq == ":LISTOUT:BASE":
            if isq:
                return f"{L['start']},{L['count']},{L['cycles']},{L['end']}"
            if L["run"] is not None:
                self.errs.append('-221,"Settings conflict"')
                return ""
            L["start"], L["count"], L["cycles"], L["end"] = int(args[0]), int(args[1]), int(args[2]), args[3]
            return ""
        if hq == ":LISTOUT:PARAMETER":
            if isq:
                i0, n = int(args[0]), int(args[1]) if len(args) > 1 else 1
                data = "".join(f"{k},{L['g'].get(k, (0, 0, 1))[0]:.3f},{L['g'].get(k, (0, 0, 1))[1]:.3f},"
                               f"{L['g'].get(k, (0, 0, 1))[2]:.1f};" for k in range(i0, min(2048, i0 + n)))
                return f"#{len(str(len(data)))}{len(data)}{data}"
            if L["run"] is not None:
                self.errs.append('-221,"Settings conflict"')
                return ""
            L["g"][int(args[0])] = (float(args[1]), float(args[2]), float(args[3]))
            return ""
        dmap = {":DELAY:START": "start", ":DELAY:GROUPS": "count", ":DELAY:CYCLES": "cycles", ":DELAY:ENDSTATE": "end"}
        if hq in dmap:
            k = dmap[hq]
            if isq:
                return str(D[k])
            if D["run"] is not None:
                self.errs.append('-221,"Settings conflict"')
                return ""
            D[k] = arg.strip() if k == "end" else int(float(arg))
            return ""
        if hq == ":DELAY:STOP":
            if isq:
                return D["stop"][0] if D["stop"][0] == "NONE" else f"{D['stop'][0]},{D['stop'][1]:.3f}"
            D["stop"] = (args[0], float(args[1]) if len(args) > 1 else D["stop"][1])
            return ""
        if hq == ":DELAY:PARAMETER":
            if isq:
                i0, n = int(args[0]), int(args[1]) if len(args) > 1 else 1
                data = "".join(f"{k},{'ON' if D['g'].get(k, (False, 1.0))[0] else 'OFF'},{D['g'].get(k, (False, 1.0))[1]:.1f};"
                               for k in range(i0, min(2048, i0 + n)))
                return f"#{len(str(len(data)))}{len(data)}{data}"
            if D["run"] is not None:
                self.errs.append('-221,"Settings conflict"')
                return ""
            D["g"][int(args[0])] = (onoff(args[1]), float(args[2]))
            return ""
        m = re.match(r":MEMORY(?::STATE)?:(STORE|LOAD|VALID)(\?)?$", head)
        if m and args and args[0] in ("LST", "DLY"):
            slot, store = args[1], (self.mem_l if args[0] == "LST" else self.mem_d)
            src = self.lst if args[0] == "LST" else self.dly
            if m.group(1) == "VALID":
                return "YES" if slot in store else "NO"
            if m.group(1) == "STORE":
                store[slot] = {c: {k: v for k, v in copy.deepcopy(x).items() if k not in ("run", "info")} for c, x in src.items()}
            elif slot in store:
                for c, x in store[slot].items():
                    src[c].update(copy.deepcopy(x))
            return ""
        return None

    def query(self, cmd):
        with self.lock:
            return self._handle(cmd, True)

    def write(self, cmd):
        with self.lock:
            self._handle(cmd, False)

    def _handle(self, cmd, q):
        time.sleep(0.003)
        c = cmd.strip()
        u = c.upper()
        parts = u.split(None, 1)
        head, arg = parts[0], (parts[1] if len(parts) > 1 else "")
        args = [a.strip() for a in arg.split(",")] if arg else []
        self._tick()
        res = self._list_delay(head, arg, args)
        if res is not None:
            return res if q else None
        if head == "*IDN?":
            return "UNI-T,UDP3305S-E,SIMULATOR,1.17"
        if head == ":SOURCE:MODE?":
            return self.mode
        if head == ":SOURCE:MODE":
            self.mode = {"NORMAL": "NORMAL", "NORM": "NORMAL", "SER": "SER", "PARA": "PARA"}.get(arg.strip(), self.mode)
            return
        if head == ":SYSTEM:ERROR?":
            return self.errs.pop(0) if self.errs else '0,"No error"'
        if head == "*CLS":
            return
        if head in ("*SAV", "*RCL"):
            n = args[0] if args else "1"
            import copy
            if head == "*SAV":
                self.mem[n] = copy.deepcopy(self.ch)
            elif n in self.mem:
                self.ch = copy.deepcopy(self.mem[n])
            return
        m = re.match(r":SOURCE(\d)?:(VOLTAGE|CURRENT)(:PROTECTION)?(:STATE)?(\?)?$", head)
        if m:
            n = int(m.group(1) or 1)
            ch = [k for k, v in CH_NUM.items() if v == n][0]
            key = ("v" if m.group(2) == "VOLTAGE" else "i")
            if m.group(3):
                key = ("ovp" if key == "v" else "ocp") + ("_on" if m.group(4) else "")
            d = self.ch[ch]
            if m.group(5):
                val = d[key]
                if isinstance(val, bool):
                    return "ON" if val else "OFF"
                return f"{val:.3f}" if key in ("i", "ocp") else f"{val:.2f}"
            if key.endswith("_on"):
                d[key] = onoff(arg)
            else:
                d[key] = float(arg)
            return
        if head.startswith(":MEASURE:ALL"):
            v, i, _ = self._meas(self._ch(arg) or "CH1")
            return f"{v:05.2f},{i:.3f},{v*i:05.2f}"
        if head == ":OUTPUT:CVCC?":
            return self._meas(self._ch(arg) or "CH1")[2]
        if head in (":OUTPUT:STATE?", ":OUTPUT?"):
            return "ON" if self.ch[self._ch(arg) or "CH1"]["out"] else "OFF"
        if head in (":OUTPUT:STATE", ":OUTPUT"):
            if args[0] == "ALL":
                for k in self.ch:
                    self.ch[k]["out"] = onoff(args[1])
            else:
                self.ch[self._ch(args[0])]["out"] = onoff(args[1])
            return
        m = re.match(r":OUTPUT:(OVP|OCP)(:STATE|:VALUE)?(\?)?$", head)
        if m:
            key = m.group(1).lower() + ("" if m.group(2) == ":VALUE" else "_on")
            ch = self._ch(args[0]) if args else "CH1"
            if m.group(3):
                val = self.ch[ch][key]
                return ("ON" if val else "OFF") if isinstance(val, bool) else f"{val:.3f}"
            self.ch[ch][key] = onoff(args[1]) if key.endswith("_on") else float(args[1])
            return
        m = re.match(r":PRESET([1-5])(:APPLY)?$", head)
        if m:
            for c, d in self.pre[int(m.group(1))].items():
                self.ch[c].update(v=d["v"], i=d["i"], ovp_on=d["ovp_on"], ovp=d["ovp"], ocp_on=d["ocp_on"], ocp=d["ocp"])
            return
        m = re.match(r":PRESET([1-5]):SET:(VOLTAGE|CURRENT|OVP|OCP)(\?)?$", head)
        if m:
            g, what, isq = self.pre[int(m.group(1))], m.group(2), m.group(3)
            d = g[self._ch(args[0]) or "CH1"]
            if what in ("VOLTAGE", "CURRENT"):
                k = "v" if what == "VOLTAGE" else "i"
                if isq:
                    return f"{d[k]:05.2f}" if k == "v" else f"{d[k]:.3f}"
                d[k] = float(args[1])
                return
            k = what.lower()
            if isq:
                return f"{'ON' if d[k + '_on'] else 'OFF'},{d[k]:.3f}"
            d[k + "_on"] = onoff(args[1])
            if len(args) > 2:
                d[k] = float(args[2])
            return
        sysmap = {":SYSTEM:BEEPER": "beep", ":SYSTEM:BEEPER:STATE": "beep", ":SYSTEM:LOCK": "lock",
                  ":SYSTEM:KLOCK:STATE": "klock", ":SYSTEM:RWLOCK": "klock", ":SYSTEM:RWLOCK:STATE": "klock"}
        hq = head.rstrip("?")
        if hq in sysmap:
            k = sysmap[hq]
            if head.endswith("?"):
                return "ON" if self.sys[k] else "OFF"
            self.sys[k] = onoff(arg) if arg else True
            return
        if hq == ":SYSTEM:BRIGHTNESS":
            if head.endswith("?"):
                return str(self.sys["bright"])
            self.sys["bright"] = int(float(arg))
            return
        if hq == ":SYSTEM:COMMUNICATE:RS232:BAUD":
            if head.endswith("?"):
                return str(self.sys["baud"])
            self.sys["baud"] = int(arg)
            return
        lanmap = {":SYSTEM:COMMUNICATE:LAN:DHCP": "dhcp", ":SYSTEM:COMMUNICATE:LAN:DHCP:STATE": "dhcp",
                  ":SYSTEM:COMMUNICATE:LAN:IPADDRESS": "ip", ":SYSTEM:COMMUNICATE:LAN:SMASK": "mask",
                  ":SYSTEM:COMMUNICATE:LAN:GATEWAY": "gw"}
        if hq in lanmap:
            k = lanmap[hq]
            if head.endswith("?"):
                return ("ON" if self.lan[k] else "OFF") if k == "dhcp" else f'"{self.lan[k]}"'
            self.lan[k] = onoff(arg) if k == "dhcp" else arg.strip('"\' ')
            return
        if head in (":SYSTEM:COMMUNICATE:LAN:APPLY", "*RST", "*CLS"):
            return
        if head == ":SYSTEM:VERSION?":
            return "1999.0"
        if head == ":SYSTEM:ERROR:COUNT?":
            return str(len(self.errs))
        if head == "*TST?":
            return "0"
        self.errs.append('-113,"Undefined header"')
        return "" if q else None


# --------------------------------------------------------------------------
# Geraetelogik
# --------------------------------------------------------------------------
class Supply:
    def __init__(self, io):
        self.io = io
        self.idn = None
        self.cache = {}
        self.lock = None        # Tastensperre am Geraet (LOCK / Fernsperre)
        self.lock_ok = True     # False, falls das Geraet die Abfrage nicht kennt

    def read_lock(self):
        if not self.lock_ok:
            return None
        try:
            a = onoff(self.io.query(":SYSTem:LOCK?"))
            b = onoff(self.io.query(":SYSTem:KLOCk:STATe?"))
            self.lock = a or b
        except ScpiError:
            self.lock_ok = False
            self.lock = None
        return self.lock

    def channels(self, mode):
        if mode.startswith("SER"):
            return ["SER", "CH3"]
        if mode.startswith("PARA"):
            return ["PARA", "CH3"]
        return ["CH1", "CH2", "CH3"]

    def state(self, full):
        q = self.io.query
        if self.idn is None:
            self.idn = q("*IDN?")
        mode = (q(":SOURce:Mode?") or "NORMAL").strip().upper()
        out = []
        for ch in self.channels(mode):
            n = CH_NUM[ch]
            m = nums(q(f":MEASure:ALL? {ch}"))[-3:]
            while len(m) < 3:
                m.append(0.0)
            d = {
                "ch": ch,
                "meas": {"v": m[0], "i": m[1], "p": m[2]},
                "out": onoff(q(f":OUTPut:STATe? {ch}")),
                "cvcc": (q(f":OUTPut:CVCC? {ch}") or "").strip().upper(),
                "limits": LIMITS[ch],
            }
            if full or ch not in self.cache:
                self.cache[ch] = {
                    "vset": last_num(q(f":SOURce{n}:VOLTage?")),
                    "iset": last_num(q(f":SOURce{n}:CURRent?")),
                    "ovp": last_num(q(f":OUTPut:OVP:VALue? {ch}")),
                    "ovp_on": onoff(q(f":OUTPut:OVP:STATe? {ch}")),
                    "ocp": last_num(q(f":OUTPut:OCP:VALue? {ch}")),
                    "ocp_on": onoff(q(f":OUTPut:OCP:STATe? {ch}")),
                }
            d.update(self.cache[ch])
            out.append(d)
        if full or self.lock is None:
            self.read_lock()
        return {"ok": True, "idn": self.idn, "mode": mode, "channels": out, "lock": self.lock, "t": time.time()}

    def apply(self, req):
        """Fuehrt eine Aenderung aus. req ist ein dict aus der Weboberflaeche."""
        w = self.io.write
        action = req.get("action")
        if action == "scpi":
            cmd = str(req.get("cmd", "")).strip()
            if not cmd or "\n" in cmd:
                raise ValueError("Ungueltiger Befehl")
            if "?" in cmd:
                return {"ok": True, "reply": self.io.query(cmd)}
            w(cmd)
            return {"ok": True, "reply": self.error()}
        if action == "mode":
            mode = {"NORMAL": "NORMal", "SER": "SER", "PARA": "PARA"}[req["mode"]]
            w(f":SOURce:Mode {mode}")
            time.sleep(0.7)  # laut Anleitung mind. 500 ms warten
            self.cache.clear()
            return {"ok": True, "reply": self.error()}
        if action == "all_out":
            w(f":OUTPut:STATe ALL,{'ON' if req['on'] else 'OFF'}")
            return {"ok": True, "reply": self.error()}
        if action in ("save", "recall"):
            n = int(req["slot"])
            if not 1 <= n <= 10:
                raise ValueError("Speicherplatz 1–10")
            w(f"*SAV {n}" if action == "save" else f"*RCL {n}")
            self.cache.clear()
            return {"ok": True, "reply": self.error()}
        if action == "local":
            w(":SYSTem:LOCK OFF")
            w(":SYSTem:KLOCk:STATe OFF")
            self.lock = False
            return {"ok": True, "reply": self.error()}
        if action == "lock":   # Tastensperre ein/aus (wie LOCK-Taste am Geraet)
            if req.get("on"):
                w(":SYSTem:LOCK ON")
            else:
                w(":SYSTem:LOCK OFF")
                w(":SYSTem:KLOCk:STATe OFF")
            err = self.error()
            self.read_lock()
            return {"ok": True, "reply": err, "lock": self.lock}

        ch = req.get("ch")
        if ch not in CH_NUM:
            raise ValueError("Unbekannter Kanal")
        n = CH_NUM[ch]
        lim = LIMITS[ch]
        p = req.get("param")
        val = req.get("value")

        def num(maxv):
            x = float(val)
            if not (0 <= x <= maxv):
                raise ValueError(f"Wert ausserhalb 0 … {maxv}")
            return x

        if p == "vset":
            w(f":SOURce{n}:VOLTage {num(lim['v']):.2f}")
        elif p == "iset":
            w(f":SOURce{n}:CURRent {num(lim['i']):.3f}")
        elif p == "ovp":
            w(f":OUTPut:OVP:VALue {ch},{num(lim['v'] * 1.1):.2f}")
        elif p == "ocp":
            w(f":OUTPut:OCP:VALue {ch},{num(lim['i'] * 1.1):.3f}")
        elif p == "ovp_on":
            w(f":OUTPut:OVP:STATe {ch},{'ON' if val else 'OFF'}")
        elif p == "ocp_on":
            w(f":OUTPut:OCP:STATe {ch},{'ON' if val else 'OFF'}")
        elif p == "out":
            w(f":OUTPut:STATe {ch},{'ON' if val else 'OFF'}")
        else:
            raise ValueError("Unbekannter Parameter")
        self.cache.pop(ch, None)
        return {"ok": True, "reply": self.error()}

    def error(self):
        try:
            e = self.io.query(":SYSTem:ERRor?")
        except ScpiError:
            raise
        except Exception:
            return None
        if e and not e.lstrip("+").startswith("0"):
            return e
        return None


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
class App:
    """Haelt die aktuelle Verbindung; kann zur Laufzeit auf eine andere IP umschalten."""

    def __init__(self, sim=False):
        self.lock = threading.Lock()
        self.sim = sim
        self.supply = None
        self.host = None
        self.port = SCPI_PORT
        self.server = None

    def label(self):
        if self.sim:
            return "Simulator"
        return f"{self.host}:{self.port}" if self.host else ""

    def connect(self, host, port=SCPI_PORT, test=True):
        if host == "SIM":
            with self.lock:
                if self.supply:
                    self.supply.io.close()
                self.sim, self.host = True, None
                self.supply = Supply(SimScpi())
            return "UNI-T,UDP3305S-E,SIMULATOR"
        host = host.strip()
        idn = probe_idn(host, port, timeout=2.5) if test else None
        with self.lock:
            if self.supply:
                self.supply.io.close()
            self.sim, self.host, self.port = False, host, port
            self.supply = Supply(ScpiSocket(host, port))
        if idn is not None:
            remember_host(host, port, idn)
        return idn


class Handler(http.server.BaseHTTPRequestHandler):
    app = None

    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        ln = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(ln) or b"{}")

    def do_GET(self):
        app = self.app
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            with open(ui_file(), "rb") as f:
                b = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif path == "/api/ping":
            self._json({"app": APP_ID, "build": BUILD})
        elif path == "/api/state":
            sup = app.supply
            if sup is None:
                return self._json({"ok": False, "setup": True, "error": "Kein Netzteil ausgewählt", "host": ""})
            try:
                st = sup.state("full=1" in self.path)
                st["host"] = app.label()
                self._json(st)
            except Exception as e:
                sup.idn = None
                self._json({"ok": False, "error": str(e), "host": app.label()})
        elif path == "/api/config":
            c = load_config()
            self._json({"host": app.host, "port": app.port, "sim": app.sim, "label": app.label(),
                        "recent": c.get("recent", []), "local": local_ipv4s()})
        elif path == "/api/scan":
            sup = app.supply
            self._json(scan_network(skip=app.host, skip_idn=sup.idn if sup else None))
        else:
            self.send_error(404)

    def do_POST(self):
        app = self.app
        path = self.path.split("?")[0]
        try:
            req = self._body()
            if path == "/api/set":
                if app.supply is None:
                    return self._json({"ok": False, "error": "Kein Netzteil verbunden"}, 409)
                return self._json(app.supply.apply(req))
            if path == "/api/batch":
                if app.supply is None:
                    return self._json({"ok": False, "error": "Kein Netzteil verbunden"}, 409)
                cmds = req.get("cmds")
                if not isinstance(cmds, list) or not 0 < len(cmds) <= 200 or \
                        any(not isinstance(c, str) or "\n" in c or not c.strip() for c in cmds):
                    raise ValueError("Ungueltige Befehlsliste")
                io, out, wrote = app.supply.io, [], False
                with io.lock:   # Liste ohne Unterbrechung durch andere Abfragen ausfuehren
                    for c in cmds:
                        if "?" in c:
                            out.append(io.query(c))
                        else:
                            io.write(c)
                            out.append(None)
                            wrote = True
                err = app.supply.error() if wrote else None
                if wrote:
                    app.supply.cache.clear()
                return self._json({"ok": True, "replies": out, "error": err})
            if path == "/api/connect":
                host = str(req.get("host", "")).strip()
                port = int(req.get("port") or SCPI_PORT)
                if not host:
                    raise ValueError("Bitte IP-Adresse eingeben")
                try:
                    idn = app.connect(host, port)
                except OSError as e:
                    return self._json({"ok": False, "error": f"{host}:{port} nicht erreichbar ({e})"})
                return self._json({"ok": True, "idn": idn, "label": app.label()})
            if path == "/api/forget":
                c = load_config()
                c["recent"] = [r for r in c.get("recent", []) if r.get("host") != req.get("host")]
                save_config(c)
                return self._json({"ok": True})
            if path == "/api/quit":
                self._json({"ok": True})
                threading.Thread(target=app.server.shutdown, daemon=True).start()
                return
            self.send_error(404)
        except (ValueError, KeyError, TypeError) as e:
            self._json({"ok": False, "error": str(e)}, 400)
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 502)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True   # Port nach Neustart sofort wieder nutzbar (aktive Server werden trotzdem erkannt)


def build_id():
    """Kennung dieses Stands (Server + Oberflaeche). Aendert sich bei jedem Update."""
    h = hashlib.sha1()
    for p in (os.path.abspath(__file__), ui_file()):
        try:
            with open(p, "rb") as f:
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()[:12]


BUILD = None


def _local_http(port, method, path):
    with socket.create_connection(("127.0.0.1", port), timeout=0.8) as s:
        s.settimeout(1.5)
        s.sendall(f"{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n".encode())
        data = b""
        while True:
            d = s.recv(4096)
            if not d:
                break
            data += d
        return data.decode("utf-8", "replace")


def check_running(port):
    """'same' = diese Version laeuft schon, 'old' = eine andere Version von uns, None = frei/fremd."""
    try:
        r = _local_http(port, "GET", "/api/ping")
    except OSError:
        return None
    if "udp3305-control" not in r and APP_ID not in r:
        return None
    return "same" if BUILD and BUILD in r else "old"


def stop_old(port):
    """Beendet eine aeltere laufende Version (alle Versionen kennen /api/quit)."""
    try:
        _local_http(port, "POST", "/api/quit")
    except OSError:
        pass
    for _ in range(30):
        time.sleep(0.1)
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
        except OSError:
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Web-Steuerung fuer UNI-T UDP3305S-E")
    ap.add_argument("--host", default=os.environ.get("UDP_HOST"), help="IP des Netzteils (sonst letzte gespeicherte)")
    ap.add_argument("--port", type=int, default=SCPI_PORT, help="SCPI-Port (5025)")
    ap.add_argument("--web", type=int, default=8080, help="Port der Weboberflaeche")
    ap.add_argument("--lan", action="store_true", help="Weboberflaeche auch im LAN freigeben")
    ap.add_argument("--sim", action="store_true", help="Simulator statt echtem Netzteil")
    ap.add_argument("--no-browser", action="store_true", help="Browser nicht automatisch oeffnen")
    a = ap.parse_args()

    global BUILD
    BUILD = build_id()
    # Eigene, schon laufende Instanzen auf allen moeglichen Ports suchen
    for port in range(a.web, a.web + 20):
        state = check_running(port)
        if state == "same":
            print(f"Läuft bereits auf Port {port} – öffne Browser.")
            if not a.no_browser:
                webbrowser.open(f"http://localhost:{port}")
            return
        if state == "old":
            print(f"Ältere Version auf Port {port} – wird beendet.")
            stop_old(port)

    app = App()
    Handler.app = app
    if a.sim:
        app.connect("SIM")
    else:
        cfg = load_config()
        host = a.host or cfg.get("host")
        if host:
            app.connect(host, a.port if a.host else int(cfg.get("port", SCPI_PORT)), test=False)

    bind = "0.0.0.0" if a.lan else "127.0.0.1"
    srv = None
    for attempt in range(15):          # bevorzugten Port bis zu 3 s erneut versuchen
        try:
            srv = Server((bind, a.web), Handler)
            break
        except OSError:
            if check_running(a.web) is not None or attempt == 14:
                break
            time.sleep(0.2)
    for web in range(a.web + 1, a.web + 20):
        if srv:
            break
        try:
            srv = Server((bind, web), Handler)
        except OSError:
            continue
    if srv is None:
        sys.exit("Kein freier Port gefunden")
    app.server = srv
    url = f"http://localhost:{srv.server_address[1]}"
    print(f"PSU Control  ->  {url}   (Netzteil: {app.label() or 'noch nicht gewählt'})")
    if a.lan:
        print("Im LAN erreichbar unter http://<IP-dieses-Macs>:%d" % srv.server_address[1])
    print("Beenden mit Ctrl+C oder in der Oberfläche über ‚Verbindung → App beenden‘")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        if app.supply:
            app.supply.io.close()


if __name__ == "__main__":
    main()
