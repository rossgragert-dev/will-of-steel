import {solveJoint,bladeBasis,ENEMY_READY} from './motion.js';
// Bone hierarchy drives the existing rigid metal meshes; no skin deformation required for plate armor.
export function buildFencingRig(T,knight,legs,torso,head,arms){
 const down=new T.Vector3(0,-1,0),v=new T.Vector3(),q=new T.Quaternion(),parentQ=new T.Quaternion();
 const bone=(parent,name,x,y,z)=>{const b=new T.Bone();b.name=name;b.position.set(x,y,z);parent.add(b);return b};
 const hip=bone(knight,'hips',0,.94,0),chest=bone(hip,'chest',0,.09,0);
 knight.updateMatrixWorld(true);chest.attach(torso);chest.attach(head);chest.attach(arms);
 const pairs=legs.map((source,i)=>{
  const side=i===0?-1:1,upper=bone(hip,'thigh_'+i,side*.15,0,0),lower=bone(upper,'shin_'+i,0,-.43,0),foot=bone(lower,'foot_'+i,0,-.40,0);
  const items=[...source.children];knight.updateMatrixWorld(true);
  for(const [n,item] of items.entries())(n<2?upper:n<5?lower:foot).attach(item);
  knight.remove(source);
  return {side,upper,lower,foot};
 });
 function apply(p=ENEMY_READY,rootAdvance=0,recoil=0,lead=1){
  hip.position.y=.94-p.crouch;chest.rotation.set(-.06-p.advance*.2-.10*recoil,p.yaw,0);
  for(const {side,upper,lower,foot} of pairs){
   const active=side===lead,step=active?p.step:0,lift=active?p.lift:0;
   const origin=[side*.15,0,0],target=[side*.15,.11-hip.position.y+lift,side*.115+step-rootAdvance];
   const sol=solveJoint(origin,target,.43,.40,[side*.10,.05,1]);
   v.set(sol.joint[0]-origin[0],sol.joint[1]-origin[1],sol.joint[2]-origin[2]).normalize();upper.quaternion.setFromUnitVectors(down,v);
   v.set(sol.end[0]-sol.joint[0],sol.end[1]-sol.joint[1],sol.end[2]-sol.joint[2]).normalize().applyQuaternion(q.copy(upper.quaternion).invert());lower.quaternion.setFromUnitVectors(down,v);
   parentQ.copy(upper.quaternion).multiply(lower.quaternion);foot.quaternion.copy(parentQ).invert();
  }
 }
 return {apply};
}
export function makeBladeOrienter(T){const x=new T.Vector3(),y=new T.Vector3(),z=new T.Vector3(),m=new T.Matrix4(),q=new T.Quaternion();return (obj,pose,blend=1)=>{const b=bladeBasis(pose.axis,pose.edge);x.set(...b.x);y.set(...b.y);z.set(...b.z);m.makeBasis(x,y,z);q.setFromRotationMatrix(m);obj.quaternion.slerp(q,blend)}}
