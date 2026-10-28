/*
 * PSU Control – iOS/iPadOS-Bruecke
 * ---------------------------------
 * Wird von der iOS-App vor index.html geladen. Sie beantwortet alle
 * fetch('/api/...')-Aufrufe der Oberflaeche direkt im Browser. Dafuer gibt es
 * dieselben Endpunkte wie beim Mac-Server (mac/udp3305.py), nur hier in JavaScript.
 * Fuer die TCP-Verbindung zum Netzteil, die Netzwerksuche und den
 * Einstellungsspeicher ruft sie die native Swift-Seite auf (NativeBridge.swift).
 *
 * SPDX-License-Identifier: MIT
 */
(function () {
  'use strict';

  // Native Schnittstelle: in der App window.webkit.messageHandlers.native,
  // in Tests kann window.__PSU_NATIVE__ (Funktion msg -> Promise) gesetzt werden.
  let post = null;
  if (typeof window.__PSU_NATIVE__ === 'function') post = window.__PSU_NATIVE__;
  else if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.native)
    post = (m) => window.webkit.messageHandlers.native.postMessage(m);
  if (!post) return;                      // normaler Browser -> Mac-Server benutzen
  window.PSU_NATIVE = 'ios';

  const N = (op, args) => Promise.resolve(post(Object.assign({ op }, args || {})));
  const SCPI_PORT = 5025;
  const CH_NUM = { CH1: 1, CH2: 2, CH3: 3, SER: 5, PARA: 6 };
  const LIMITS = {
    CH1: { v: 32.0, i: 5.2 }, CH2: { v: 32.0, i: 5.2 }, CH3: { v: 6.2, i: 3.2 },
    SER: { v: 64.0, i: 5.2 }, PARA: { v: 32.0, i: 10.4 },
  };
  const nums = (s) => (String(s || '').match(/[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g) || []).map(Number);
  const lastNum = (s) => { const n = nums(s); return n.length ? n[n.length - 1] : null; };
  const onoff = (s) => ['ON', '1'].includes(String(s || '').trim().toUpperCase());
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const errMsg = (e) => String((e && e.message) || e);

  // ------------------------------------------------------------------ TCP
  class TcpIO {
    constructor(host, port) { this.host = host; this.port = port; this.open = false; this.chain = Promise.resolve(); }
    _serial(fn) { const p = this.chain.then(fn, fn); this.chain = p.catch(() => {}); return p; }
    async _do(cmd, want) {
      for (let attempt = 1; attempt <= 2; attempt++) {
        try {
          if (!this.open) { await N('connect', { host: this.host, port: this.port }); this.open = true; }
          const r = await N(want ? 'query' : 'write', { cmd });
          return want ? String(r == null ? '' : r) : null;
        } catch (e) {
          this.open = false;
          try { await N('close'); } catch (_) { /* egal */ }
          if (attempt === 2) throw new Error(`${this.host}:${this.port} – ${errMsg(e)}`);
        }
      }
    }
    query(c) { return this._serial(() => this._do(c, true)); }
    write(c) { return this._serial(() => this._do(c, false)); }
    // mehrere Befehle ohne Unterbrechung durch andere Abfragen
    batch(cmds) { return this._serial(async () => { const out = []; for (const c of cmds) out.push(await this._do(c, c.includes('?'))); return out; }); }
    close() { this.open = false; return this._serial(() => N('close').catch(() => {})); }
  }

  // ------------------------------------------------------------ Simulator
  class SimIO {
    constructor() {
      const mk = () => ({ v: 5.0, i: 1.0, ovp: 33.0, ocp: 5.5, ovp_on: false, ocp_on: false, out: false });
      this.mode = 'NORMAL';
      this.ch = {}; Object.keys(CH_NUM).forEach((c) => (this.ch[c] = mk()));
      this.load = { CH1: 10, CH2: 4, CH3: 2, SER: 20, PARA: 3 };
      this.mem = {}; this.errs = [];
      this.pre = {};
      [1.8, 2.5, 3.3, 5.0, 12.0].forEach((v, k) => {
        const g = {}; Object.keys(CH_NUM).forEach((c) => (g[c] = { v, i: 1.0, ovp_on: false, ovp: 33.0, ocp_on: false, ocp: 5.5 }));
        this.pre[k + 1] = g;
      });
      this.sys = { beep: true, bright: 80, lock: false, klock: false, baud: 9600 };
      this.lan = { dhcp: false, ip: '192.168.0.137', mask: '255.255.255.0', gw: '192.168.0.1' };
      this.cur = 'CH1';
      this.lst = {}; this.dly = {};
      Object.keys(CH_NUM).forEach((c) => {
        this.lst[c] = { g: {}, start: 0, count: 1, cycles: 1, end: 'OFF', run: null, info: null };
        this.dly[c] = { g: {}, start: 0, count: 1, cycles: 1, end: 'OFF', stop: ['NONE', 0], run: null, info: null };
      });
      this.memL = {}; this.memD = {};
    }
    // LIST / DELAYER abspielen (vor jedem Befehl)
    _tick() {
      const now = performance.now() / 1000;
      for (const c of Object.keys(CH_NUM)) {
        for (const kind of ['lst', 'dly']) {
          const L = this[kind][c];
          if (L.run == null) continue;
          const def = kind === 'lst' ? [0, 0, 1] : [false, 1];
          const seq = []; for (let k = L.start; k < L.start + L.count; k++) seq.push(L.g[k] || def);
          const dur = (x) => Math.max(0.1, x[x.length - 1]);
          const T = seq.reduce((a, x) => a + dur(x), 0) || 1;
          const el = now - L.run, cyc = Math.floor(el / T), d = this.ch[c];
          let hit = false;
          if (kind === 'dly' && L.stop[0] !== 'NONE') {
            const [v, i] = this._meas(c), x = { V: v, C: i, P: v * i }[L.stop[0][1]];
            hit = L.stop[0][0] === '<' ? x < L.stop[1] : x > L.stop[1];
          }
          if (cyc >= L.cycles || hit) {
            L.run = null; L.info = null;
            if (L.end === 'OFF') d.out = false; else if (L.end === 'ON') d.out = true;
            continue;
          }
          let pos = el - cyc * T, k = 0;
          while (k < seq.length - 1 && pos >= dur(seq[k])) { pos -= dur(seq[k]); k++; }
          const rest = (L.cycles - cyc - 1) * T + seq.slice(k).reduce((a, x) => a + dur(x), 0) - pos;
          L.info = [rest, L.start + k, L.cycles - cyc - 1];
          if (kind === 'lst') { d.v = seq[k][0]; d.i = seq[k][1]; d.out = true; } else d.out = !!seq[k][0];
        }
      }
    }
    _status(L) {
      const endp = L.start + L.count - 1;
      if (L.run != null && L.info) return `ON,${L.info[0].toFixed(1)},${L.info[1]},${endp},${L.info[2]},${L.end}`;
      return `OFF,0.0,${L.start},${endp},0,${L.end}`;
    }
    _ld(head, arg, args) {
      const hq = head.replace(/\?$/, ''), isQ = head.endsWith('?');
      const busy = (L) => { if (L.run != null) { this.errs.push('-221,"Settings conflict"'); return true; } return false; };
      const block = (data) => `#${String(data.length).length}${data.length}${data}`;
      if ([':INSTRUMENT:SELECT', ':INSTRUMENT:SELE', ':INSTRUMENT', ':INST:SEL', ':INST'].includes(hq)) {
        if (isQ) return this.cur; this.cur = this._c(arg) || this.cur; return '';
      }
      if (hq === ':INSTRUMENT:NSELECT') {
        if (isQ) return String(CH_NUM[this.cur]);
        this.cur = Object.keys(CH_NUM).find((k) => CH_NUM[k] === parseInt(arg, 10)) || this.cur; return '';
      }
      const L = this.lst[this.cur], D = this.dly[this.cur];
      for (const [names, X] of [[[':LISTOUT:STATE', ':LISTOUT'], L], [[':DELAY:STATE', ':DELAY'], D]]) {
        if (names.includes(hq)) {
          if (isQ) return this._status(X);
          if (onoff(arg)) { X.run = performance.now() / 1000; this._tick(); } else { X.run = null; X.info = null; }
          return '';
        }
      }
      if (hq === ':LISTOUT:BASE') {
        if (isQ) return `${L.start},${L.count},${L.cycles},${L.end}`;
        if (busy(L)) return '';
        L.start = parseInt(args[0], 10); L.count = parseInt(args[1], 10); L.cycles = parseInt(args[2], 10); L.end = args[3]; return '';
      }
      if (hq === ':LISTOUT:PARAMETER') {
        if (isQ) {
          const i0 = parseInt(args[0], 10), n = args.length > 1 ? parseInt(args[1], 10) : 1; let data = '';
          for (let k = i0; k < Math.min(2048, i0 + n); k++) { const g = L.g[k] || [0, 0, 1]; data += `${k},${g[0].toFixed(3)},${g[1].toFixed(3)},${g[2].toFixed(1)};`; }
          return block(data);
        }
        if (busy(L)) return '';
        L.g[parseInt(args[0], 10)] = [parseFloat(args[1]), parseFloat(args[2]), parseFloat(args[3])]; return '';
      }
      const dmap = { ':DELAY:START': 'start', ':DELAY:GROUPS': 'count', ':DELAY:CYCLES': 'cycles', ':DELAY:ENDSTATE': 'end' };
      if (dmap[hq]) {
        const k = dmap[hq]; if (isQ) return String(D[k]);
        if (busy(D)) return '';
        D[k] = k === 'end' ? arg.trim() : parseInt(arg, 10); return '';
      }
      if (hq === ':DELAY:STOP') {
        if (isQ) return D.stop[0] === 'NONE' ? 'NONE' : `${D.stop[0]},${D.stop[1].toFixed(3)}`;
        D.stop = [args[0], args.length > 1 ? parseFloat(args[1]) : D.stop[1]]; return '';
      }
      if (hq === ':DELAY:PARAMETER') {
        if (isQ) {
          const i0 = parseInt(args[0], 10), n = args.length > 1 ? parseInt(args[1], 10) : 1; let data = '';
          for (let k = i0; k < Math.min(2048, i0 + n); k++) { const g = D.g[k] || [false, 1]; data += `${k},${g[0] ? 'ON' : 'OFF'},${g[1].toFixed(1)};`; }
          return block(data);
        }
        if (busy(D)) return '';
        D.g[parseInt(args[0], 10)] = [onoff(args[1]), parseFloat(args[2])]; return '';
      }
      const m = head.match(/^:MEMORY(?::STATE)?:(STORE|LOAD|VALID)(\?)?$/);
      if (m && args.length > 1 && (args[0] === 'LST' || args[0] === 'DLY')) {
        const store = args[0] === 'LST' ? this.memL : this.memD, src = args[0] === 'LST' ? this.lst : this.dly, slot = args[1];
        if (m[1] === 'VALID') return store[slot] ? 'YES' : 'NO';
        if (m[1] === 'STORE') {
          const snap = {}; Object.keys(src).forEach((c) => { const x = Object.assign({}, src[c]); delete x.run; delete x.info; snap[c] = JSON.parse(JSON.stringify(x)); });
          store[slot] = snap;
        } else if (store[slot]) Object.keys(store[slot]).forEach((c) => Object.assign(src[c], JSON.parse(JSON.stringify(store[slot][c]))));
        return '';
      }
      return null;
    }
    _c(t) { t = String(t || '').trim().toUpperCase(); return CH_NUM[t] ? t : null; }
    _meas(c) {
      const d = this.ch[c];
      if (!d.out) return [0, 0, 'CV'];
      const r = this.load[c]; let i = d.v / r, v = d.v, m = 'CV';
      if (i > d.i) { i = d.i; v = d.i * r; m = 'CC'; }
      v = Math.max(0, v + (Math.random() - 0.5) * 0.008); i = Math.max(0, i + (Math.random() - 0.5) * 0.004);
      return [v, i, m];
    }
    close() { return Promise.resolve(); }
    async batch(cmds) { return cmds.map((c) => (c.includes('?') ? this._h(c, true) : (this._h(c, false), null))); }
    async query(c) { return this._h(c, true); }
    async write(c) { this._h(c, false); return null; }
    _h(cmd, q) {
      const u = cmd.trim().toUpperCase();
      const sp = u.indexOf(' ');
      const head = sp < 0 ? u : u.slice(0, sp), arg = sp < 0 ? '' : u.slice(sp + 1).trim();
      const args = arg ? arg.split(',').map((a) => a.trim()) : [];
      const f2 = (x) => x.toFixed(2), f3 = (x) => x.toFixed(3), oo = (b) => (b ? 'ON' : 'OFF');
      let m;
      this._tick();
      const ld = this._ld(head, arg, args);
      if (ld != null) return ld;
      if (head === '*IDN?') return 'UNI-T,UDP3305S-E,SIMULATOR,1.17';
      if (head === '*TST?') return '0';
      if (['*RST', '*CLS', ':SYSTEM:COMMUNICATE:LAN:APPLY'].includes(head)) return '';
      if (head === ':SOURCE:MODE?') return this.mode;
      if (head === ':SOURCE:MODE') { this.mode = { NORMAL: 'NORMAL', NORM: 'NORMAL', SER: 'SER', PARA: 'PARA' }[arg] || this.mode; return ''; }
      if (head === ':SYSTEM:ERROR?') return this.errs.length ? this.errs.shift() : '0,"No error"';
      if (head === ':SYSTEM:ERROR:COUNT?') return String(this.errs.length);
      if (head === ':SYSTEM:VERSION?') return '1999.0';
      if (head === '*SAV') { this.mem[args[0] || '1'] = JSON.parse(JSON.stringify(this.ch)); return ''; }
      if (head === '*RCL') { const s = this.mem[args[0] || '1']; if (s) this.ch = JSON.parse(JSON.stringify(s)); return ''; }
      if ((m = head.match(/^:SOURCE(\d)?:(VOLTAGE|CURRENT)(:PROTECTION)?(:STATE)?(\?)?$/))) {
        const n = +(m[1] || 1), c = Object.keys(CH_NUM).find((k) => CH_NUM[k] === n), d = this.ch[c];
        let k = m[2] === 'VOLTAGE' ? 'v' : 'i';
        if (m[3]) k = (k === 'v' ? 'ovp' : 'ocp') + (m[4] ? '_on' : '');
        if (m[5]) return typeof d[k] === 'boolean' ? oo(d[k]) : (k === 'i' || k === 'ocp' ? f3(d[k]) : f2(d[k]));
        d[k] = k.endsWith('_on') ? onoff(arg) : parseFloat(arg); return '';
      }
      if (head.startsWith(':MEASURE:ALL')) { const [v, i] = this._meas(this._c(arg) || 'CH1'); return `${f2(v).padStart(5, '0')},${f3(i)},${f2(v * i).padStart(5, '0')}`; }
      if (head === ':OUTPUT:CVCC?') return this._meas(this._c(arg) || 'CH1')[2];
      if (head === ':OUTPUT:STATE?' || head === ':OUTPUT?') return oo(this.ch[this._c(arg) || 'CH1'].out);
      if (head === ':OUTPUT:STATE' || head === ':OUTPUT') {
        if (args[0] === 'ALL') Object.values(this.ch).forEach((d) => (d.out = onoff(args[1]))); else this.ch[this._c(args[0])].out = onoff(args[1]);
        return '';
      }
      if ((m = head.match(/^:OUTPUT:(OVP|OCP)(:STATE|:VALUE)?(\?)?$/))) {
        const k = m[1].toLowerCase() + (m[2] === ':VALUE' ? '' : '_on'), c = args.length ? this._c(args[0]) : 'CH1';
        if (m[3]) { const v = this.ch[c][k]; return typeof v === 'boolean' ? oo(v) : f3(v); }
        this.ch[c][k] = k.endsWith('_on') ? onoff(args[1]) : parseFloat(args[1]); return '';
      }
      if ((m = head.match(/^:PRESET([1-5])(:APPLY)?$/))) {
        const g = this.pre[+m[1]]; Object.keys(g).forEach((c) => Object.assign(this.ch[c], g[c])); return '';
      }
      if ((m = head.match(/^:PRESET([1-5]):SET:(VOLTAGE|CURRENT|OVP|OCP)(\?)?$/))) {
        const d = this.pre[+m[1]][this._c(args[0]) || 'CH1'];
        if (m[2] === 'VOLTAGE' || m[2] === 'CURRENT') {
          const k = m[2] === 'VOLTAGE' ? 'v' : 'i';
          if (m[3]) return k === 'v' ? f2(d.v).padStart(5, '0') : f3(d.i);
          d[k] = parseFloat(args[1]); return '';
        }
        const k = m[2].toLowerCase();
        if (m[3]) return `${oo(d[k + '_on'])},${f3(d[k])}`;
        d[k + '_on'] = onoff(args[1]); if (args.length > 2) d[k] = parseFloat(args[2]); return '';
      }
      const hq = head.replace(/\?$/, ''), isQ = head.endsWith('?');
      const sysmap = { ':SYSTEM:BEEPER': 'beep', ':SYSTEM:BEEPER:STATE': 'beep', ':SYSTEM:LOCK': 'lock',
        ':SYSTEM:KLOCK:STATE': 'klock', ':SYSTEM:RWLOCK': 'klock', ':SYSTEM:RWLOCK:STATE': 'klock' };
      if (sysmap[hq]) { const k = sysmap[hq]; if (isQ) return oo(this.sys[k]); this.sys[k] = arg ? onoff(arg) : true; return ''; }
      if (hq === ':SYSTEM:BRIGHTNESS') { if (isQ) return String(this.sys.bright); this.sys.bright = parseInt(arg, 10); return ''; }
      if (hq === ':SYSTEM:COMMUNICATE:RS232:BAUD') { if (isQ) return String(this.sys.baud); this.sys.baud = parseInt(arg, 10); return ''; }
      const lanmap = { ':SYSTEM:COMMUNICATE:LAN:DHCP': 'dhcp', ':SYSTEM:COMMUNICATE:LAN:DHCP:STATE': 'dhcp',
        ':SYSTEM:COMMUNICATE:LAN:IPADDRESS': 'ip', ':SYSTEM:COMMUNICATE:LAN:SMASK': 'mask', ':SYSTEM:COMMUNICATE:LAN:GATEWAY': 'gw' };
      if (lanmap[hq]) {
        const k = lanmap[hq];
        if (isQ) return k === 'dhcp' ? oo(this.lan.dhcp) : `"${this.lan[k]}"`;
        this.lan[k] = k === 'dhcp' ? onoff(arg) : arg.replace(/["' ]/g, ''); return '';
      }
      this.errs.push('-113,"Undefined header"');
      return '';
    }
  }

  // --------------------------------------------------------------- Geraet
  class Supply {
    constructor(io) { this.io = io; this.idn = null; this.cache = {}; this.lock = null; this.lockOk = true; }
    async readLock() {
      if (!this.lockOk) return null;
      try {
        const a = onoff(await this.io.query(':SYSTem:LOCK?')), b = onoff(await this.io.query(':SYSTem:KLOCk:STATe?'));
        this.lock = a || b;
      } catch (e) { this.lockOk = false; this.lock = null; }
      return this.lock;
    }
    channels(mode) {
      if (mode.startsWith('SER')) return ['SER', 'CH3'];
      if (mode.startsWith('PARA')) return ['PARA', 'CH3'];
      return ['CH1', 'CH2', 'CH3'];
    }
    async state(full) {
      const q = (c) => this.io.query(c);
      if (this.idn == null) this.idn = await q('*IDN?');
      const mode = ((await q(':SOURce:Mode?')) || 'NORMAL').trim().toUpperCase();
      const out = [];
      for (const ch of this.channels(mode)) {
        const n = CH_NUM[ch];
        const m = nums(await q(`:MEASure:ALL? ${ch}`)).slice(-3);
        while (m.length < 3) m.push(0);
        const d = {
          ch, meas: { v: m[0], i: m[1], p: m[2] },
          out: onoff(await q(`:OUTPut:STATe? ${ch}`)),
          cvcc: ((await q(`:OUTPut:CVCC? ${ch}`)) || '').trim().toUpperCase(),
          limits: LIMITS[ch],
        };
        if (full || !this.cache[ch]) {
          this.cache[ch] = {
            vset: lastNum(await q(`:SOURce${n}:VOLTage?`)),
            iset: lastNum(await q(`:SOURce${n}:CURRent?`)),
            ovp: lastNum(await q(`:OUTPut:OVP:VALue? ${ch}`)),
            ovp_on: onoff(await q(`:OUTPut:OVP:STATe? ${ch}`)),
            ocp: lastNum(await q(`:OUTPut:OCP:VALue? ${ch}`)),
            ocp_on: onoff(await q(`:OUTPut:OCP:STATe? ${ch}`)),
          };
        }
        Object.assign(d, this.cache[ch]);
        out.push(d);
      }
      if (full || this.lock == null) await this.readLock();
      return { ok: true, idn: this.idn, mode, channels: out, lock: this.lock, t: Date.now() / 1000 };
    }
    async error() {
      const e = await this.io.query(':SYSTem:ERRor?');
      return e && !/^\s*\+?0\b/.test(e) ? e : null;
    }
    async apply(req) {
      const w = (c) => this.io.write(c);
      const a = req.action;
      if (a === 'scpi') {
        const cmd = String(req.cmd || '').trim();
        if (!cmd || cmd.includes('\n')) throw new Error('Ungueltiger Befehl');
        if (cmd.includes('?')) return { ok: true, reply: await this.io.query(cmd) };
        await w(cmd); return { ok: true, reply: await this.error() };
      }
      if (a === 'mode') {
        const mode = { NORMAL: 'NORMal', SER: 'SER', PARA: 'PARA' }[req.mode];
        if (!mode) throw new Error('Unbekannter Modus');
        await w(`:SOURce:Mode ${mode}`); await sleep(700); this.cache = {};
        return { ok: true, reply: await this.error() };
      }
      if (a === 'all_out') { await w(`:OUTPut:STATe ALL,${req.on ? 'ON' : 'OFF'}`); return { ok: true, reply: await this.error() }; }
      if (a === 'save' || a === 'recall') {
        const n = parseInt(req.slot, 10);
        if (!(n >= 1 && n <= 10)) throw new Error('Speicherplatz 1–10');
        await w(a === 'save' ? `*SAV ${n}` : `*RCL ${n}`); this.cache = {};
        return { ok: true, reply: await this.error() };
      }
      if (a === 'local') { await w(':SYSTem:LOCK OFF'); await w(':SYSTem:KLOCk:STATe OFF'); this.lock = false; return { ok: true, reply: await this.error() }; }
      if (a === 'lock') {
        if (req.on) await w(':SYSTem:LOCK ON'); else { await w(':SYSTem:LOCK OFF'); await w(':SYSTem:KLOCk:STATe OFF'); }
        const err = await this.error(); await this.readLock();
        return { ok: true, reply: err, lock: this.lock };
      }

      const ch = req.ch;
      if (!CH_NUM[ch]) throw new Error('Unbekannter Kanal');
      const n = CH_NUM[ch], lim = LIMITS[ch], p = req.param, val = req.value;
      const num = (max) => {
        const x = parseFloat(val);
        if (!(x >= 0 && x <= max)) throw new Error(`Wert ausserhalb 0 … ${max}`);
        return x;
      };
      const oo = val ? 'ON' : 'OFF';
      if (p === 'vset') await w(`:SOURce${n}:VOLTage ${num(lim.v).toFixed(2)}`);
      else if (p === 'iset') await w(`:SOURce${n}:CURRent ${num(lim.i).toFixed(3)}`);
      else if (p === 'ovp') await w(`:OUTPut:OVP:VALue ${ch},${num(lim.v * 1.1).toFixed(2)}`);
      else if (p === 'ocp') await w(`:OUTPut:OCP:VALue ${ch},${num(lim.i * 1.1).toFixed(3)}`);
      else if (p === 'ovp_on') await w(`:OUTPut:OVP:STATe ${ch},${oo}`);
      else if (p === 'ocp_on') await w(`:OUTPut:OCP:STATe ${ch},${oo}`);
      else if (p === 'out') await w(`:OUTPut:STATe ${ch},${oo}`);
      else throw new Error('Unbekannter Parameter');
      delete this.cache[ch];
      return { ok: true, reply: await this.error() };
    }
  }

  // ---------------------------------------------------------- Einstellungen
  async function loadCfg() {
    try { const s = await N('cfgGet'); const c = s ? JSON.parse(s) : {}; return c && typeof c === 'object' ? c : {}; }
    catch (_) { return {}; }
  }
  async function saveCfg(c) { try { await N('cfgSet', { value: JSON.stringify(c) }); } catch (_) { /* egal */ } }
  async function rememberHost(host, port, idn) {
    const c = await loadCfg();
    c.host = host; c.port = port;
    c.recent = [{ host, port, idn }].concat((c.recent || []).filter((r) => r.host !== host)).slice(0, 8);
    await saveCfg(c);
  }

  // ------------------------------------------------------------- App-Zustand
  const app = { supply: null, host: null, port: SCPI_PORT, sim: false };
  const label = () => (app.sim ? 'Simulator' : app.host ? `${app.host}:${app.port}` : '');

  async function connect(host, port, test) {
    if (app.supply) await app.supply.io.close();
    if (host === 'SIM') {
      app.sim = true; app.host = null; app.supply = new Supply(new SimIO());
      return 'UNI-T,UDP3305S-E,SIMULATOR';
    }
    let idn = null;
    if (test) idn = await N('probe', { host, port });
    app.sim = false; app.host = host; app.port = port; app.supply = new Supply(new TcpIO(host, port));
    if (idn != null) await rememberHost(host, port, idn);
    return idn;
  }

  const ready = (async () => {
    const c = await loadCfg();
    if (c.host) { try { await connect(c.host, parseInt(c.port, 10) || SCPI_PORT, false); } catch (_) { /* egal */ } }
  })();

  // ------------------------------------------------------------------ API
  async function route(url, method, body) {
    await ready;
    const path = url.split('?')[0];
    if (method === 'GET') {
      if (path === '/api/ping') return { app: 'psu-control-ios' };
      if (path === '/api/state') {
        if (!app.supply) return { ok: false, setup: true, error: 'Kein Netzteil ausgewählt', host: '' };
        try {
          const st = await app.supply.state(url.includes('full=1'));
          st.host = label(); return st;
        } catch (e) { app.supply.idn = null; return { ok: false, error: errMsg(e), host: label() }; }
      }
      if (path === '/api/config') {
        const c = await loadCfg();
        let local = [];
        try { local = await N('localIPs'); } catch (_) { /* egal */ }
        return { host: app.host, port: app.port, sim: app.sim, label: label(), recent: c.recent || [], local: local || [] };
      }
      if (path === '/api/scan') {
        const r = await N('scan', { port: SCPI_PORT, skip: app.host || '' });
        (r.found || []).forEach((d) => { if (d.host === app.host && app.supply && app.supply.idn) d.idn = app.supply.idn; });
        r.found = (r.found || []).sort((a, b) => (/UNI-T/i.test(b.idn) - /UNI-T/i.test(a.idn)) ||
          a.host.split('.').map(Number).reduce((x, y) => x * 256 + y, 0) - b.host.split('.').map(Number).reduce((x, y) => x * 256 + y, 0));
        return r;
      }
      return { ok: false, error: 'Unbekannter Pfad' };
    }
    // POST
    try {
      if (path === '/api/set') {
        if (!app.supply) return { ok: false, error: 'Kein Netzteil verbunden' };
        return await app.supply.apply(body);
      }
      if (path === '/api/batch') {
        if (!app.supply) return { ok: false, error: 'Kein Netzteil verbunden' };
        const cmds = body.cmds;
        if (!Array.isArray(cmds) || !cmds.length || cmds.length > 200 ||
            cmds.some((c) => typeof c !== 'string' || c.includes('\n') || !c.trim())) throw new Error('Ungueltige Befehlsliste');
        const io = app.supply.io, wrote = cmds.some((c) => !c.includes('?'));
        const out = await io.batch(cmds);
        const err = wrote ? await app.supply.error() : null;
        if (wrote) app.supply.cache = {};
        return { ok: true, replies: out, error: err };
      }
      if (path === '/api/connect') {
        const host = String(body.host || '').trim(), port = parseInt(body.port, 10) || SCPI_PORT;
        if (!host) throw new Error('Bitte IP-Adresse eingeben');
        try { const idn = await connect(host, port, true); return { ok: true, idn, label: label() }; }
        catch (e) { return { ok: false, error: `${host}:${port} nicht erreichbar (${errMsg(e)})` }; }
      }
      if (path === '/api/forget') {
        const c = await loadCfg(); c.recent = (c.recent || []).filter((r) => r.host !== body.host); await saveCfg(c);
        return { ok: true };
      }
      if (path === '/api/quit') return { ok: true };
      return { ok: false, error: 'Unbekannter Pfad' };
    } catch (e) { return { ok: false, error: errMsg(e) }; }
  }

  const realFetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = async function (input, opt) {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    if (!url.startsWith('/api/')) return realFetch(input, opt);
    let body = {};
    try { body = opt && opt.body ? JSON.parse(opt.body) : {}; } catch (_) { body = {}; }
    let res;
    try { res = await route(url, ((opt && opt.method) || 'GET').toUpperCase(), body || {}); }
    catch (e) { res = { ok: false, error: errMsg(e) }; }
    return new Response(JSON.stringify(res), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
})();
