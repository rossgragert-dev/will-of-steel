// Write metadata-free copies of review renders for public distribution. Originals are never modified.
// PNG: all text chunks (tEXt, zTXt, iTXt) are dropped - Blender stores the source .blend path there - pixel data and
// every other chunk are copied byte-for-byte. Other files (mp4, json) are copied unchanged. Refuses to overwrite and
// verifies each output contains no local path / user name.
// Usage: node tools/validation/publish-sanitized.mjs <srcDir|file> [...more] --out <dstRoot> --base <srcBase>
import {readFileSync, writeFileSync, existsSync, mkdirSync, statSync, readdirSync} from 'node:fs';
import {join, relative, dirname} from 'node:path';
import {userInfo, homedir} from 'node:os';

const args = process.argv.slice(2);
const oi = args.indexOf('--out'), bi = args.indexOf('--base');
if (oi < 0 || bi < 0) { console.error('usage: publish-sanitized <src...> --out <dstRoot> --base <srcBase>'); process.exit(2); }
const out = args[oi + 1], base = args[bi + 1];
const srcs = args.filter((_, i) => i !== oi && i !== oi + 1 && i !== bi && i !== bi + 1);
// Forbidden content is derived at runtime from the machine running the tool (no personal data in this file).
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const FORBID = new RegExp([userInfo().username, homedir(), homedir().replace(/\\/g, '/'), 'C:\\Users', 'C:/Users'].filter(Boolean).map(esc).join('|'), 'i');

export function stripPngText(buf) {
  const sig = buf.subarray(0, 8);
  if (sig.toString('hex') !== '89504e470d0a1a0a') throw new Error('not a PNG');
  const parts = [sig];
  let off = 8, dropped = 0;
  while (off < buf.length) {
    const len = buf.readUInt32BE(off), type = buf.toString('latin1', off + 4, off + 8);
    const total = 12 + len;
    if (['tEXt', 'zTXt', 'iTXt'].includes(type)) dropped++;
    else parts.push(buf.subarray(off, off + total));
    off += total;
    if (type === 'IEND') break;
  }
  return {buf: Buffer.concat(parts), dropped};
}

const walk = p => statSync(p).isDirectory() ? readdirSync(p).flatMap(n => walk(join(p, n))) : [p];
let n = 0, chunks = 0;
for (const s of srcs) for (const f of walk(s)) {
  if (/[\\/]frames[\\/]/.test(f)) continue;                       // frame sequences are not published
  const dst = join(out, relative(base, f));
  if (existsSync(dst)) { console.error('refusing to overwrite ' + dst); process.exit(1); }
  mkdirSync(dirname(dst), {recursive: true});
  let data = readFileSync(f);
  if (f.toLowerCase().endsWith('.png')) { const r = stripPngText(data); data = r.buf; chunks += r.dropped; }
  if (FORBID.test(data.toString('latin1'))) { console.error('still contains a local path: ' + f); process.exit(1); }
  writeFileSync(dst, data, {flag: 'wx'});
  n++;
}
console.log(`published ${n} sanitized files to ${out} (removed ${chunks} PNG text chunks)`);
