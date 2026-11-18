import test from 'node:test';import assert from 'node:assert/strict';import {GUARD_POSES,READY,GRIP_POINTS,PLAYER_ELBOWS,elbowPoint,bladeAxis} from '../rig-poses.js';
test('five poses retain finite numbers',()=>{assert.equal(Object.keys(GUARD_POSES).length,5);for(const g of [READY,...Object.values(GUARD_POSES)])assert.ok([...g.p,g.x,g.y,g.z].every(Number.isFinite))});
test('lower guards mirror placement and point down and outward',()=>{const l=GUARD_POSES.lowerLeft,r=GUARD_POSES.lowerRight;assert.equal(l.x,-r.x);assert.equal(l.y,r.y);const la=bladeAxis(l.p),ra=bladeAxis(r.p);assert.ok(la[0]<0&&ra[0]>0&&la[1]<-.8&&ra[1]<-.8)});
test('low hilt stays below center at safe camera depth',()=>{for(const z of ['lowerLeft','lowerRight']){const g=GUARD_POSES[z];assert.ok(g.y<-.4&&g.z<-1.1);for(const p of GRIP_POINTS){assert.ok(g.y+Math.abs(p[1])<-.3)}}});
test('grip points are distinct and elbow roots are low',()=>{assert.ok(GRIP_POINTS[0][1]>GRIP_POINTS[1][1]);assert.ok(PLAYER_ELBOWS.every(p=>p[1]<-.7&&p[2]<-.5))});
test('enemy elbows bend out from shoulder and wrist',()=>{const v=elbowPoint([.3,0,0],[.1,-.2,.4],1,.18);assert.ok(v[0]>.3&&v[1]<-.2&&v[2]>0)});
