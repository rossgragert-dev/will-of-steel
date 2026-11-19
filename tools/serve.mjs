// Read-only local static server for previewing the game and the animation lab.
// Usage: node tools/serve.mjs [port]   ->  http://localhost:8080/
// Serves only files inside the repository and refuses path traversal. Never writes or deletes anything.
import {createServer} from 'node:http';
import {readFile, stat} from 'node:fs/promises';
import {resolve, extname, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=resolve(fileURLToPath(new URL('..',import.meta.url)));
const PORT=Number(process.argv[2]||8080);
const TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css',
  '.json':'application/json','.glb':'model/gltf-binary','.gltf':'model/gltf+json','.png':'image/png','.jpg':'image/jpeg',
  '.webp':'image/webp','.svg':'image/svg+xml','.mp4':'video/mp4','.webm':'video/webm','.md':'text/plain; charset=utf-8'};
const PRIVATE=['backups','build','.git','.claude','source'];

createServer(async(req,res)=>{
  try{
    let p=decodeURIComponent(new URL(req.url,'http://x').pathname); if(p.endsWith('/')) p+='index.html';
    const f=resolve(ROOT,'.'+p);
    if(!f.startsWith(ROOT+sep)||PRIVATE.some(d=>f.startsWith(resolve(ROOT,d)+sep))){res.writeHead(403).end('forbidden');return}
    if(!(await stat(f)).isFile()) throw 0;
    res.writeHead(200,{'Content-Type':TYPES[extname(f)]||'application/octet-stream','Cache-Control':'no-store'});
    res.end(await readFile(f));
  }catch{res.writeHead(404).end('not found')}
}).listen(PORT,'127.0.0.1',()=>console.log(`Will of Steel local preview: http://localhost:${PORT}/  (lab: /previews/lab/)`));
