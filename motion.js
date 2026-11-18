// Authoring coordinates: enemy +Z forward; William camera space -Z forward.
// Every cut is a timed sequence of grip translations, blade axes and edge alignment.
// Data is original hand-authored motion, not motion capture.
export const CONTACT=.72;
export const V=(x,y,z)=>[x,y,z];
const add=(a,b)=>a.map((v,i)=>v+b[i]),sub=(a,b)=>a.map((v,i)=>v-b[i]),mul=(a,s)=>a.map(v=>v*s),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
export const length=v=>Math.hypot(...v);
export function unit(v,f=[0,1,0]){const n=length(v);return n>1e-7?mul(v,1/n):f.slice()}
export const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
const smooth=t=>t*t*(3-2*t);
export function bladeBasis(axis,edge){const y=unit(axis),projection=sub(edge,mul(y,dot(edge,y)));const x=length(projection)>1e-6?unit(projection):unit(cross(y,Math.abs(y[2])<.85?[0,0,1]:[0,1,0]));return {x,y,z:unit(cross(x,y))}}
export const ENEMY_READY={grip:[.01,-.22,.36],axis:[.58,.61,.54],edge:[1,0,0],yaw:0,advance:0,crouch:.045,step:0,lift:0};
export const PLAYER_READY={grip:[.28,-.51,-1.13],axis:[.02,.814,-.58],edge:[1,0,0],yaw:0,advance:0,crouch:0,step:0,lift:0};
const K=(t,grip,axis,edge,yaw=0,advance=0,crouch=.045,step=0,lift=0)=>({t,grip,axis,edge,yaw,advance,crouch,step,lift});
const ready=(p,t)=>({...p,t});
const mirror=(frames)=>frames.map(k=>({...k,grip:[-k.grip[0],k.grip[1],k.grip[2]],axis:[-k.axis[0],k.axis[1],k.axis[2]],edge:[-k.edge[0],k.edge[1],k.edge[2]],yaw:-k.yaw}));
function timeline(stand,wind,load,hit,follow,release){return [ready(stand,0),K(.30,...wind),K(.52,...load),K(CONTACT,...hit),K(.84,...follow),K(.94,...release),ready(stand,1)]}
const E=ENEMY_READY,P=PLAYER_READY;
const eh=timeline(E,
 [[.03,.28,.24],[.08,.97,-.24],[0,-1,1],-.06,.015,.062,0,.02],
 [[.04,.34,.17],[.04,.68,-.73],[0,-1,-1],-.09,.045,.085,.08,.04],
 [[.04,.04,.50],[.02,-.18,.98],[0,-1,0],.02,.20,.08,.18,0],
 [[.02,-.27,.37],[0,-.82,.57],[0,-1,-1],.08,.20,.095,.18,0],
 [[.03,-.29,.34],[.25,-.50,.83],[0,1,0],.02,.07,.06,.06,.035]);
const eu=timeline(E,
 [[-.22,.10,.26],[-.73,.52,.45],[1,-.3,0],-.20,.02,.065,0,.02],
 [[-.26,.12,.19],[-.67,.45,-.60],[1,-.25,1],-.27,.045,.085,.08,.04],
 [[-.08,-.01,.50],[.17,-.12,.98],[1,-.35,0],.12,.19,.082,.17,0],
 [[.25,-.18,.34],[.81,-.40,.43],[1,-.35,-.5],.24,.19,.09,.17,0],
 [[.18,-.23,.32],[.75,.28,.59],[0,1,0],.12,.06,.055,.05,.025]);
const el=timeline(E,
 [[-.21,-.33,.25],[-.71,-.66,.25],[1,.65,0],-.16,.015,.08,0,.018],
 [[-.24,-.36,.19],[-.60,-.62,-.50],[1,.75,1],-.23,.04,.10,.07,.04],
 [[-.06,-.25,.48],[.22,.02,.97],[1,.72,0],.10,.19,.10,.17,0],
 [[.24,.02,.32],[.77,.50,.39],[1,.5,-.3],.22,.19,.09,.17,0],
 [[.16,-.13,.30],[.62,.66,.40],[1,0,0],.08,.06,.06,.05,.025]);
const ph=timeline(P,
 [[.20,.06,-1.01],[.05,.91,.40],[0,-1,-1]],
 [[.15,.14,-1.00],[.02,.70,.71],[0,-1,-1]],
 [[.03,-.06,-1.40],[.01,-.20,-.98],[0,-1,0]],
 [[.08,-.48,-1.19],[.04,-.79,-.61],[0,-1,1]],
 [[.23,-.53,-1.09],[.21,.38,-.90],[1,0,0]]);
// The player's right-to-left diagonal attack targets the visible upper-left zone.
const pu=timeline(P,
 [[.38,-.16,-1.03],[.78,.53,.33],[-1,-.35,0]],
 [[.38,-.10,-1.00],[.84,.24,.48],[-1,-.35,-1]],
 [[.02,-.25,-1.42],[-.29,.03,-.95],[-1,-.30,0]],
 [[-.29,-.45,-1.16],[-.83,-.40,-.38],[-1,-.30,1]],
 [[-.11,-.53,-1.14],[-.55,.28,-.76],[1,0,0]]);
const pl=timeline(P,
 [[.36,-.58,-1.00],[.78,-.58,.24],[-1,.65,0]],
 [[.38,-.59,-.99],[.68,-.53,.48],[-1,.65,-1]],
 [[.03,-.51,-1.42],[-.23,.02,-.97],[-1,.65,0]],
 [[-.27,-.21,-1.15],[-.82,.42,-.39],[-1,.65,1]],
 [[-.10,-.38,-1.16],[-.52,.66,-.54],[1,0,0]]);
// Mirror the active motion, not the right-handed ready pose.
function opposite(frames,stand){const a=mirror(frames);a[0]=ready(stand,0);a[a.length-1]=ready(stand,1);return a}
export const CLIPS={enemy:{head:eh,upperLeft:eu,upperRight:opposite(eu,E),lowerLeft:el,lowerRight:opposite(el,E)},player:{head:ph,upperLeft:pu,upperRight:opposite(pu,P),lowerLeft:pl,lowerRight:opposite(pl,P)}};
export function timelineTime(time,start,hit,end){return time<=hit?CONTACT*clamp((time-start)/Math.max(.001,hit-start)):CONTACT+(1-CONTACT)*clamp((time-hit)/Math.max(.001,end-hit))}
export function sampleClip(view,zone,phase){
 const clip=CLIPS[view]?.[zone];if(!clip)return view==='enemy'?ENEMY_READY:PLAYER_READY;
 phase=clamp(phase);let i=1;while(i<clip.length-1&&phase>clip[i].t)i++;
 const a=clip[i-1],b=clip[i],raw=clamp((phase-a.t)/(b.t-a.t)),u=smooth(raw),out={grip:mix(a.grip,b.grip,u),axis:unit(mix(unit(a.axis),unit(b.axis),u),unit(b.axis)),edge:unit(mix(unit(a.edge),unit(b.edge),u),unit(b.edge))};
 for(const key of ['yaw','advance','crouch','step','lift'])out[key]=a[key]+(b[key]-a[key])*u;
 // Edge orientation is unambiguous even when hint is parallel to blade.
 return out
}
// Analytic two-link solution, with bounded unreachable targets and stable bend direction.
export function solveJoint(origin,target,l1,l2,pole){
 const delta=sub(target,origin),axis=unit(delta,[0,-1,0]),d=clamp(length(delta),Math.abs(l1-l2)+.0001,l1+l2-.0001);
 const along=(l1*l1-l2*l2+d*d)/(2*d),height=Math.sqrt(Math.max(0,l1*l1-along*along));
 let bend=sub(pole,mul(axis,dot(pole,axis)));if(length(bend)<1e-6)bend=cross(axis,Math.abs(axis[2])<.8?[0,0,1]:[0,1,0]);
 const joint=add(add(origin,mul(axis,along)),mul(unit(bend),height));
 return {joint,end:add(origin,mul(axis,d)),reachable:Math.abs(length(delta)-d)<.001}
}
