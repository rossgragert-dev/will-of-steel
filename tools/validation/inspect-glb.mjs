// Read-only GLB inspector: node tools/validation/inspect-glb.mjs <file.glb> [--require a,b,c] [--max-tris N]
// Parses the GLB container, counts triangles/materials/textures, checks required node names. Writes nothing.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

export function parseGLB(buf){
  if(buf.readUInt32LE(0)!==0x46546C67) throw new Error('not a GLB (bad magic)');
  const version=buf.readUInt32LE(4); if(version!==2) throw new Error('GLB version '+version);
  let off=12, json=null, bin=null;
  while(off<buf.length){const len=buf.readUInt32LE(off), type=buf.readUInt32LE(off+4), data=buf.subarray(off+8,off+8+len);
    if(type===0x4E4F534A) json=JSON.parse(data.toString('utf8')); else if(type===0x004E4942) bin=data; off+=8+len}
  if(!json) throw new Error('no JSON chunk'); return {json,bin};
}

export function summarize(buf){
  const {json}=parseGLB(buf), acc=json.accessors||[];
  let tris=0;
  for(const m of json.meshes||[]) for(const p of m.primitives){const mode=p.mode??4; if(mode!==4) continue;
    tris+=(p.indices!==undefined?acc[p.indices].count:acc[p.attributes.POSITION].count)/3}
  return {bytes:buf.length, sha256:createHash('sha256').update(buf).digest('hex'), triangles:tris,
    nodes:(json.nodes||[]).map(n=>n.name), meshes:(json.meshes||[]).length, materials:(json.materials||[]).map(m=>m.name),
    textures:(json.textures||[]).length, images:(json.images||[]).map(i=>i.mimeType), skins:(json.skins||[]).length,
    animations:(json.animations||[]).map(a=>a.name), generator:json.asset?.generator};
}

if(process.argv[1]?.replace(/\\/g,'/').endsWith('tools/validation/inspect-glb.mjs')){
  const [file,...rest]=process.argv.slice(2); if(!file){console.error('usage: inspect-glb <file.glb> [--require a,b] [--max-tris N]');process.exit(2)}
  const s=summarize(readFileSync(file)); console.log(JSON.stringify(s,null,2));
  let ok=true; const ri=rest.indexOf('--require'), mi=rest.indexOf('--max-tris');
  if(ri>=0) for(const n of rest[ri+1].split(',')) if(!s.nodes.includes(n)){console.error('MISSING node: '+n);ok=false}
  if(mi>=0&&s.triangles>Number(rest[mi+1])){console.error(`OVER BUDGET: ${s.triangles} > ${rest[mi+1]} tris`);ok=false}
  console.log(ok?'PASS':'FAIL'); process.exit(ok?0:1);
}
