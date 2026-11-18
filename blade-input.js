// Full-screen pointer aim and speed-gated strikes. Coordinates are normalized to the canvas.
export function guardAt(x,y){const a=x-.5,b=y-.5;if(Math.max(Math.abs(a),Math.abs(b))<.14)return 'center';return Math.abs(a)>Math.abs(b)?(a<0?'left':'right'):(b<0?'down':'up')}
export class BladeInput {
 constructor(){this.reset()}
 reset(){this.active=false;this.aim=null;this.samples=[];this.last=null;this.latch=null;this.lastCut=-Infinity;this.hold=false;this.start=null;this.defensive=false;this.ratio=1}
 begin(x,y,t,ratio,defensive){this.active=true;this.aim={x,y};this.ratio=ratio;this.defensive=defensive;this.samples=[{x,y,t}];this.last={x,y,t};this.start={x,y,t};this.hold=!defensive&&guardAt(x,y)==='center';this.latch=null;return defensive?{guard:guardAt(x,y)}:{}}
 stance(defensive,t){this.defensive=defensive;this.hold=false;this.latch=null;this.samples=this.aim?[{...this.aim,t}]:[];this.last=this.samples[0]||null;return defensive&&this.aim?guardAt(this.aim.x,this.aim.y):null}
 move(x,y,t){if(!this.active)return {};const old=this.last;this.aim={x,y};this.last={x,y,t};if(this.defensive)return {guard:guardAt(x,y)};if(this.start&&Math.hypot(x-this.start.x,(y-this.start.y)*this.ratio)>.035)this.hold=false;
 if(old&&t-old.t>135){this.samples=[old];this.latch=null}
 this.samples=this.samples.filter(p=>t-p.t<=125);
 if(!this.samples.length&&old&&t-old.t<=160)this.samples.push(old);
 this.samples.push({x,y,t});
 if(this.samples.length<2)return {};
 const p=this.samples[0],dx=x-p.x,dy=(y-p.y)*this.ratio,dist=Math.hypot(dx,dy),elapsed=Math.max(12,t-p.t);
 if(old&&this.latch){const sx=x-old.x,sy=(y-old.y)*this.ratio;const dot=sx*this.latch.x+sy*this.latch.y;if(dot<-.012){this.latch=null;this.samples=[old,{x,y,t}];return {}}}
 if(this.latch||dist<.115||dist/elapsed<.00165||t-this.lastCut<180)return {};
 this.latch={x:dx/dist,y:dy/dist};this.lastCut=t;this.hold=false;this.samples=[{x,y,t}];return {cut:Math.abs(dx)>Math.abs(dy)?(dx>0?'right':'left'):(dy>0?'down':'up')}}
 tick(t){if(!this.active||this.defensive||!this.hold||!this.start||t-this.start.t<330)return {};this.hold=false;return {cut:'center'}}
 end(){this.active=false;this.hold=false;this.samples=[];this.last=null;this.latch=null}
}
