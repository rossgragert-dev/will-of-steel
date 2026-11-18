// Closest points of two finite 3D blade segments, in world coordinates.
const sub=(a,b)=>a.map((v,i)=>v-b[i]),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),add=(a,b,t)=>a.map((v,i)=>v+b[i]*t),clamp=x=>Math.min(1,Math.max(0,x)),lerp=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
export function segmentContact(a,b,c,d){
 const u=sub(b,a),v=sub(d,c),r=sub(a,c),aa=dot(u,u),ee=dot(v,v),ff=dot(v,r),eps=1e-9;let s=0,t=0;
 if(aa<=eps&&ee<=eps){}else if(aa<=eps)t=clamp(ff/ee);else{const cc=dot(u,r);if(ee<=eps)s=clamp(-cc/aa);else{const bb=dot(u,v),den=aa*ee-bb*bb;s=Math.abs(den)>eps?clamp((bb*ff-cc*ee)/den):0;t=(bb*s+ff)/ee;if(t<0){t=0;s=clamp(-cc/aa)}else if(t>1){t=1;s=clamp((bb-cc)/aa)}}}
 const pa=add(a,u,s),pb=add(c,v,t);return {distance:Math.hypot(...sub(pa,pb)),point:lerp(pa,pb,.5),s,t}
}
export function sweptContact(previous,current,steps=6){
 if(!previous) return segmentContact(...current);
 let best=null;const n=Math.max(1,Math.min(12,Math.floor(steps)));for(let i=0;i<=n;i++){const t=i/n,q=current.map((p,j)=>lerp(previous[j],p,t)),r=segmentContact(...q);if(!best||r.distance<best.distance)best={...r,time:t}}
 return best
}
