import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const $=x=>document.getElementById(x);
const items={
knight:{title:'Ser Aldren — 15th-century knight',file:'characters/ser_aldren_v006.glb',detail:'45-bone knight. Check the helmet, gauntlets, knee armor and overall silhouette.',pictures:[['ser_aldren_v006_guard_front34.png','Three-quarter front'],['ser_aldren_v006_guard_side.png','Side profile'],['ser_aldren_v006_guard_back34.png','Back armor'],['ser_aldren_v006_guard_detail_upper.png','Helmet and gauntlet closeup'],['ser_aldren_v006_player_pov_portrait.png','First-person combat viewpoint']]},
arms:{title:'William — first-person arm rig',file:'first-person/william_fp_arms_v004.glb',detail:'51-bone rig and articulated fingers. Head parry still hides about 27% of the opponent.',pictures:[['william_fp_arms_v004_pov_ready.png','Ready stance'],['william_fp_arms_v004_pov_head_5.png','Head parry (5)'],['william_fp_arms_v004_pov_upperLeft_4.png','Upper-left parry (4)'],['william_fp_arms_v004_pov_upperRight_3.png','Upper-right parry (3)'],['william_fp_arms_v004_pov_lowerLeft_1.png','Lower-left parry (1)'],['william_fp_arms_v004_pov_lowerRight_2.png','Lower-right parry (2)'],['william_fp_arms_v004_inspect_last_pose.png','Articulated arm inspection']]},
sword:{title:'Type XVa — longsword',file:'weapons/longsword_xva_v006.glb',detail:'2,610 triangles. 92 cm blade, 1.23 m overall, distal taper and leather-wrapped handle.',pictures:[['longsword_xva_v006_three_quarter.png','Three-quarter model'],['longsword_xva_v006_side.png','Side profile'],['longsword_xva_v006_edge.png','Edge geometry'],['longsword_xva_v006_hilt.png','Guard and grip detail']]}
};
const scene=new T.Scene();scene.background=new T.Color(0x293437);
const host=$('viewport'),renderer=new T.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.6));renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.4;renderer.outputColorSpace=T.SRGBColorSpace;host.appendChild(renderer.domElement);
const camera=new T.PerspectiveCamera(50,1,.01,1000);camera.position.set(2,2,3);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.minDistance=.1;orbit.maxDistance=100;
scene.add(new T.HemisphereLight(0xddeeff,0x596368,2.2));
const key=new T.DirectionalLight(0xffe7c6,2.8);key.position.set(-4,7,5);scene.add(key);
const fill=new T.DirectionalLight(0xa4c9ff,1.2);fill.position.set(4,2,-4);scene.add(fill);
try{const pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(new RoomEnvironment(),.05).texture;pmrem.dispose()}catch(err){console.warn('Reflection lighting fallback',err)}
const grid=new T.GridHelper(12,24,0x7b745c,0x465154);scene.add(grid);
let object=null,helper=null,box=null,request=0,photoIndex=0;const cache={},loader=new GLTFLoader();
function reframe(){if(!box)return;const mid=box.getCenter(new T.Vector3()),extent=box.getSize(new T.Vector3()),r=Math.max(.14,extent.length()/2);orbit.target.copy(mid);camera.position.copy(mid).add(new T.Vector3(1.2,.9,1.55).normalize().multiplyScalar(r*2.8));camera.near=Math.max(.001,r/500);camera.far=Math.max(50,r*50);camera.updateProjectionMatrix();grid.position.y=box.min.y-.03;grid.scale.setScalar(Math.max(.14,r*.8));orbit.minDistance=Math.max(.06,r*.25);orbit.maxDistance=Math.max(8,r*25);orbit.update()}
function skeleton(){if(helper){scene.remove(helper);helper=null}if(object&&$('bones').getAttribute('aria-pressed')==='true'){helper=new T.SkeletonHelper(object);helper.material.depthTest=false;helper.material.transparent=true;helper.material.opacity=.75;scene.add(helper)}}
function stats(root,clips){let tris=0;const bones=new Set();root.traverse(n=>{if(n.isBone)bones.add(n.name);if(n.isMesh){if(n.geometry){const count=n.geometry.index?.count||n.geometry.attributes.position?.count||0;tris+=Math.floor(count/3)}if(n.isSkinnedMesh)for(const b of n.skeleton?.bones||[])bones.add(b.name)}});$('tri').textContent=tris.toLocaleString();$('boneCount').textContent=bones.size;$('clips').textContent=clips;return bones.size}
async function choose(id){const serial=++request,it=items[id];$('title').textContent=it.title;$('details').textContent=it.detail;$('tri').textContent=$('boneCount').textContent=$('clips').textContent='—';$('status').textContent='Loading GLB…';
try{if(!cache[id])cache[id]=new Promise((resolve,reject)=>loader.load('assets/'+it.file,resolve,ev=>{if(serial===request&&ev.lengthComputable)$('status').textContent='Downloading '+Math.round(100*ev.loaded/ev.total)+'%'},reject));
const result=await cache[id];if(serial!==request)return;if(object)scene.remove(object);object=result.scene;scene.add(object);object.updateMatrixWorld(true);box=new T.Box3().setFromObject(object);if(box.isEmpty())throw Error('The asset has no visible meshes');
const bones=stats(object,result.animations?.length||0);reframe();skeleton();$('status').textContent='Loaded successfully · '+bones+' rig bones · '+(result.animations?.length||0)+' animation clips';
}catch(error){if(serial!==request)return;cache[id]=null;$('status').textContent='Unable to render: '+(error.message||error);console.error(error)}}
function show(){const a=items[$('model').value].pictures;photoIndex=(photoIndex+a.length)%a.length;$('images').value=String(photoIndex);$('shot').src='previews/'+a[photoIndex][0];$('shot').alt=a[photoIndex][1];$('caption').textContent=a[photoIndex][1]+' ('+(photoIndex+1)+' of '+a.length+')'}
function newGallery(){const list=items[$('model').value].pictures;$('images').replaceChildren();for(let i=0;i<list.length;i++){const opt=document.createElement('option');opt.value=String(i);opt.textContent=list[i][1];$('images').append(opt)}photoIndex=0;show()}
$('model').onchange=()=>{newGallery();choose($('model').value)};
$('images').onchange=()=>{photoIndex=Number($('images').value);show()};
$('prev').onclick=()=>{photoIndex--;show()};
$('next').onclick=()=>{photoIndex++;show()};
$('reset').onclick=reframe;
for(const [id,callback] of [['spin',on=>orbit.autoRotate=on],['grid',on=>grid.visible=on],['bones',skeleton]]){const b=$(id);b.onclick=()=>{const on=b.getAttribute('aria-pressed')!=='true';b.setAttribute('aria-pressed',String(on));b.textContent=(id==='spin'?'Auto-rotate':id==='grid'?'Grid':'Skeleton')+': '+(on?'On':'Off');callback(on)}}
function resize(){const w=Math.max(host.clientWidth,1),h=Math.max(host.clientHeight,1);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()}
new ResizeObserver(resize).observe(host);resize();
renderer.setAnimationLoop(()=>{orbit.update();renderer.render(scene,camera)});
newGallery();choose('knight');
