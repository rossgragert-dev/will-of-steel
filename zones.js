// Zone sides are from William's screen perspective.
export const ZONES=['head','upperLeft','upperRight','lowerLeft','lowerRight'];
export const ZONE_NAMES={head:'Head',upperLeft:'Upper left',upperRight:'Upper right',lowerLeft:'Lower left',lowerRight:'Lower right'};
export const PARRY_NUMBERS={head:5,upperLeft:4,upperRight:3,lowerLeft:1,lowerRight:2};
export function zoneAt(x,y){if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||x>1||y<0||y>1)return null;if(y<.33)return 'head';return (y<.66?'upper':'lower')+(x<.5?'Left':'Right')}
export class ParryControl{
 constructor(mode='hold'){this.mode=mode;this.active=false;this.pointer=null}
 down(id){if(this.pointer!==null)return this.active;this.pointer=id;this.active=this.mode==='toggle'?!this.active:true;return this.active}
 up(id,cancel=false){if(id!==this.pointer)return this.active;this.pointer=null;if(cancel||this.mode==='hold')this.active=false;return this.active}
 reset(mode=this.mode){this.mode=mode;this.active=false;this.pointer=null;return false}
}
