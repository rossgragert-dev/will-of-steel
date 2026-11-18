// Camera-space positions: both low guards keep the hilt low and off center.
// Sword points (local +Y) turn downward and outward; arms do not inherit sword rotation.
export const READY={p:[-.62,0,-.02],x:.28,y:-.51,z:-1.13};
export const GUARD_POSES={
 head:{p:[-.22,0,1.50],x:.32,y:.31,z:-1.24},
 upperLeft:{p:[-.34,0,.12],x:-.30,y:-.40,z:-1.23},
 upperRight:{p:[-.34,0,-.12],x:.30,y:-.40,z:-1.23},
 lowerLeft:{p:[-.36,0,2.80],x:-.29,y:-.48,z:-1.26},
 lowerRight:{p:[-.36,0,-2.80],x:.29,y:-.48,z:-1.26}
};
export const GRIP_POINTS=[[0,.047,0],[0,-.067,0]];
export const PLAYER_ELBOWS=[[.54,-.80,-.66],[-.54,-.81,-.66]];
export function elbowPoint(shoulder,wrist,side,bend=.21){return [(shoulder[0]+wrist[0])*.5+side*bend,(shoulder[1]+wrist[1])*.5-.17,(shoulder[2]+wrist[2])*.5-.035]}
export function bladeAxis(p){const a=p[0],b=p[1],c=p[2];return [-Math.cos(b)*Math.sin(c),Math.cos(a)*Math.cos(c)-Math.sin(a)*Math.sin(b)*Math.sin(c),Math.sin(a)*Math.cos(c)+Math.cos(a)*Math.sin(b)*Math.sin(c)]}
