// Headless screenshots / perf numbers for the v0.4 animation lab. Node built-ins only; starts no server.
// Usage:
//   node tools/serve.mjs 8080            (in another terminal)
//   node tools/validation/lab-screenshots.mjs [--base http://localhost:8080] [--static|--synthetic] [--only <clip>] [--perf] [--simple]
// Writes NEW timestamped PNGs into previews/v0.4.0/lab-screenshots/ (never overwrites) and a temporary Chrome
// profile into build/chrome-profile-<timestamp>/ (git-ignored). Never touches the user's Chrome profile.
//
// Default mode drives headless Chrome (--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader, 720x1280)
// over the DevTools protocol (Node's built-in WebSocket): it waits until the page sets window.__labReady, then
// captures. --simple uses plain `chrome --screenshot=<png> --virtual-time-budget=<ms>` instead; that is racy for this
// page (GLB download/texture decode does not reliably hold virtual time) and can capture the "Loading…" state.
import {spawn} from 'node:child_process';
import {existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('--base', 'http://localhost:8080').replace(/\/$/, '');
const CHROME = opt('--chrome', 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe');
const ONLY = opt('--only', null);
const SIMPLE = args.includes('--simple');
const BUDGET = opt('--budget', '15000');
const READY_TIMEOUT = Number(opt('--ready-timeout', '120000'));
const LAB = BASE + '/preview/v040-animation-lab/index.html';
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..*/, '').replace('T', '-');
const OUT = join(ROOT, 'previews', 'v0.4.0', 'lab-screenshots');
const PROFILE = join(ROOT, 'build', `chrome-profile-${STAMP}`);
mkdirSync(OUT, {recursive: true}); mkdirSync(PROFILE, {recursive: true});
const FLAGS = ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--window-size=720,1280', '--hide-scrollbars',
  '--no-first-run', '--no-default-browser-check', '--disable-extensions'];
const sleep = ms => new Promise(r => setTimeout(r, ms));

function uniquePath(name) {
  let p = join(OUT, `${name}_${STAMP}.png`), i = 1;
  while (existsSync(p)) p = join(OUT, `${name}_${STAMP}_${i++}.png`);
  return p;
}

// ---------- simple mode: one Chrome process per screenshot ----------
function simpleShot(file, url) {
  return new Promise((res, rej) => {
    const p = spawn(CHROME, [...FLAGS, `--virtual-time-budget=${BUDGET}`, `--user-data-dir=${join(PROFILE, 'simple')}`, `--screenshot=${file}`, url], {windowsHide: true});
    let err = ''; p.stderr.on('data', d => (err += d));
    const timer = setTimeout(() => { p.kill(); rej(new Error('chrome timeout')); }, 180000);
    p.on('close', code => { clearTimeout(timer); res({code, err}); }); p.on('error', rej);
  });
}

// ---------- DevTools-protocol mode: one Chrome, wait for window.__labReady ----------
class Browser {
  async start() {
    const dir = join(PROFILE, 'cdp');
    this.proc = spawn(CHROME, [...FLAGS, '--remote-debugging-port=0', `--user-data-dir=${dir}`, 'about:blank'], {windowsHide: true});
    this.proc.stderr.on('data', () => {});
    const portFile = join(dir, 'DevToolsActivePort');
    for (let i = 0; i < 300 && !existsSync(portFile); i++) await sleep(100);
    if (!existsSync(portFile)) throw new Error('Chrome did not open a DevTools port');
    const port = readFileSync(portFile, 'utf8').split('\n')[0].trim();
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const page = targets.find(t => t.type === 'page');
    this.ws = new WebSocket(page.webSocketDebuggerUrl);
    this.id = 0; this.pending = new Map(); this.logs = [];
    this.ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) { const {res, rej} = this.pending.get(m.id); this.pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
      else if (m.method === 'Runtime.consoleAPICalled') this.logs.push(m.params.type + ': ' + m.params.args.map(a => a.value ?? a.description).join(' '));
      else if (m.method === 'Runtime.exceptionThrown') this.logs.push('exception: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    };
    await new Promise((res, rej) => { this.ws.onopen = res; this.ws.onerror = rej; });
    await this.send('Page.enable'); await this.send('Runtime.enable');
    await this.send('Emulation.setDeviceMetricsOverride', {width: 720, height: 1280, deviceScaleFactor: 1, mobile: false});
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res, rej) => { this.pending.set(id, {res, rej}); this.ws.send(JSON.stringify({id, method, params})); });
  }
  async eval(expr) { const r = await this.send('Runtime.evaluate', {expression: expr, returnByValue: true}); return r.result?.value; }
  async open(url) {
    this.logs = [];
    await this.send('Page.navigate', {url});
    const t0 = Date.now();
    while (Date.now() - t0 < READY_TIMEOUT) {
      await sleep(250);
      const st = await this.eval('({ready: window.__labReady === true, error: window.__labError || null, title: document.title})').catch(() => null);
      if (st?.ready) { await sleep(300); return st; }
      if (st?.error) return st;
    }
    return {ready: false, error: 'timeout waiting for window.__labReady', title: await this.eval('document.title').catch(() => '?')};
  }
  async screenshot(file) { const r = await this.send('Page.captureScreenshot', {format: 'png'}); writeFileSync(file, Buffer.from(r.data, 'base64')); }
  async close() { try { await this.send('Browser.close'); } catch { /* already closed */ } try { this.ws.close(); } catch {} await sleep(500); try { this.proc.kill(); } catch {} }
}

async function states() {
  const list = [];
  let index = null;
  try { const r = await fetch(BASE + '/assets/v0.4.0/animations/clips_index_v003.json'); index = r.ok ? await r.json() : null; } catch { index = null; }
  if (args.includes('--synthetic')) {
    // In-memory synthetic clips (lab ?synthetic=1); only active while the real clips index is absent.
    list.push(['synthetic_both_attack_f20_side', 'synthetic=1&char=both&clip=aldren_attack_head&frame=20&cam=side&overlays=path,contact,hitbox,v03']);
    list.push(['synthetic_william_attack_f12_fp', 'synthetic=1&char=william&clip=william_attack_head&frame=12&cam=fp&overlays=path,sockets,v03']);
    list.push(['synthetic_aldren_attack_f12_front', 'synthetic=1&char=aldren&clip=aldren_attack_head&frame=12&cam=front&overlays=path,skeleton,joints,root,feet,v03']);
    list.push(['synthetic_both_combat', 'synthetic=1&char=both&clip=william_attack_head&frame=20&cam=combat&overlays=path,contact,hitbox']);
    return list;
  }
  if (!index || args.includes('--static')) {
    console.log(index ? 'static mode requested' : 'clips not yet available: capturing static models only');
    for (const ch of ['aldren', 'william', 'both']) for (const cam of ['side', 'fp', 'orbit']) {
      list.push([`static_${ch}_${cam}`, `char=${ch}&cam=${cam}&overlays=path,sockets,contact`]);
    }
    return list;
  }
  for (const [name, m] of Object.entries(index.clips)) {
    if (ONLY && name !== ONLY) continue;
    const f = m.contact_frame ?? m.expected_contact_frame ?? Math.round(m.frame_end / 2);
    for (const cam of ['side', 'fp']) list.push([`${name}_f${f}_${cam}`, `char=${m.character}&clip=${name}&frame=${f}&cam=${cam}&overlays=path,contact,sockets`]);
    if (m.kind === 'attack') list.push([`${name}_both_f${f}_side`, `char=both&clip=${name}&frame=${f}&cam=side&overlays=path,contact,hitbox`]);
  }
  return list;
}

async function main() {
  try { const r = await fetch(LAB); if (!r.ok) throw new Error('HTTP ' + r.status); }
  catch (e) { console.error(`Lab not reachable at ${LAB} (${e.message}). Start: node tools/serve.mjs 8080`); process.exit(2); }
  console.log('profile dir:', PROFILE);
  if (SIMPLE) {
    if (args.includes('--perf')) { console.error('--perf needs the default (DevTools) mode'); process.exit(2); }
    let n = 0;
    for (const [name, q] of await states()) {
      const file = uniquePath(name), url = `${LAB}?${q}&ui=stage&paused=1`;
      await simpleShot(file, url); const ok = existsSync(file); if (ok) n++;
      console.log(`${ok ? 'OK  ' : 'FAIL'} ${file}\n     ${url}  (simple mode: verify the image is not the loading state)`);
    }
    console.log(`${n} screenshots written to ${OUT}`);
    return;
  }
  const b = new Browser(); await b.start();
  try {
    if (args.includes('--perf')) {
      for (const q of ['char=both&perf=1&perfFrames=120', 'char=aldren&perf=1&perfFrames=120', 'char=william&cam=fp&perf=1&perfFrames=120',
        'synthetic=1&char=both&clip=aldren_attack_head&perf=1&perfFrames=120']) {
        const st = await b.open(`${LAB}?${q}&ui=stage`);
        const json = await b.eval("document.getElementById('perfOut').textContent");
        console.log(`PERF ${q}\n  title: ${st.title}\n  ${json || 'no perf output: ' + (st.error || '')}`);
      }
      return;
    }
    let n = 0, failed = 0;
    for (const [name, q] of await states()) {
      const url = `${LAB}?${q}&ui=stage&paused=1`;
      const st = await b.open(url);
      const file = uniquePath(st.ready ? name : name + '_NOT_READY');
      await b.screenshot(file); n++;
      if (!st.ready) failed++;
      const status = await b.eval("document.getElementById('status').textContent").catch(() => '');
      console.log(`${st.ready ? 'OK  ' : 'FAIL'} ${file}\n     ${url}\n     status: ${status}${st.error ? '\n     error: ' + st.error : ''}`);
      const errs = b.logs.filter(l => /^(error|exception)/.test(l));
      if (errs.length) console.log('     console: ' + errs.slice(0, 4).join(' | '));
    }
    console.log(`${n} screenshots written to ${OUT}${failed ? ` (${failed} NOT READY)` : ''}`);
    if (failed) process.exitCode = 1;
  } finally { await b.close(); }
}
main().catch(e => { console.error(e); process.exit(1); });
