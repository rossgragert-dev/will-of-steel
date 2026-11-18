// Original procedural assets, no external model or texture licenses.
export const BLADE_PROFILE=[[.16,.038,.010],[.19,.039,.010],[.79,.036,.008],[.95,.032,.007],[1.16,0,0]];
export const CUIRASS_PROFILE=[[.025,.255,.128],[.10,.265,.155],[.23,.30,.195],[.36,.315,.18],[.48,.28,.14],[.53,.17,.105]];
export function seeded(seed=90210){return ()=>{seed=(Math.imul(1664525,seed)+1013904223)>>>0;return seed/4294967296}}
export function bladeData(){
 const vertices=[],indices=[],uv=[];
 for(let i=0;i<BLADE_PROFILE.length;i++){const [y,w,d]=BLADE_PROFILE[i];vertices.push(-w,y,0,0,y,d,w,y,0,0,y,-d);for(let j=0;j<4;j++)uv.push(j*.25,i/(BLADE_PROFILE.length-1))}
 for(let i=0;i<BLADE_PROFILE.length-1;i++)for(let j=0;j<4;j++){const a=i*4+j,b=i*4+(j+1)%4,c=b+4,d=a+4;if(i===BLADE_PROFILE.length-2)indices.push(a,b,c);else indices.push(a,b,c,a,c,d)}
 indices.push(0,2,1,0,3,2);return {vertices,indices,uv}
}
export function createArt(T,renderer){
 const r=seeded(),mesh=(p,g,m,x=0,y=0,z=0)=>{const a=new T.Mesh(g,m);a.position.set(x,y,z);a.castShadow=true;a.receiveShadow=true;p.add(a);return a};
 const group=(p,x=0,y=0,z=0)=>{let a=new T.Group();p.add(a);a.position.set(x,y,z);return a};
 const box=(p,m,w,h,d,x=0,y=0,z=0)=>mesh(p,new T.BoxGeometry(w,h,d),m,x,y,z);
 const ell=(p,m,x,y,z,a,b,c)=>{let s=mesh(p,new T.SphereGeometry(1,20,14),m,x,y,z);s.scale.set(a,b,c);return s};
 const cyl=(p,m,a,b,h,x=0,y=0,z=0)=>mesh(p,new T.CylinderGeometry(a,b,h,16),m,x,y,z);
 const mat=(color,metalness=0,roughness=.7,props={})=>new T.MeshStandardMaterial({color,metalness,roughness,...props});
 function texture(kind){const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d'),im=x.createImageData(256,256),data=im.data,r=seeded(kind==='stone'?772:kind==='steel'?19:126);
 for(let y=0;y<256;y++)for(let i=0;i<256;i++){const k=(y*256+i)*4,n=r(),v=kind==='stone'?145+28*Math.sin(i*.11)*Math.cos(y*.07)+24*Math.sin((i+y)*.035)+n*45:kind==='steel'?190+n*30+9*Math.sin(y*1.9):125+n*42+11*Math.sin(y*2.7);data[k]=data[k+1]=data[k+2]=v;data[k+3]=255}
 x.putImageData(im,0,0);x.strokeStyle='rgba(35,28,22,.18)';x.lineWidth=.75;for(let j=0;j<50;j++){let a=r()*256,b=r()*256;x.beginPath();x.moveTo(a,b);x.lineTo(a+r()*(kind==='steel'?60:20),b+r()*(kind==='steel'?2:20));x.stroke()}const tex=new T.CanvasTexture(c);tex.wrapS=tex.wrapT=T.RepeatWrapping;tex.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());return tex}
 const stoneTex=texture('stone'),metalTex=texture('steel'),hideTex=texture('hide');
 const steel=mat(0xabb3b9,.80,.34,{roughnessMap:metalTex}),edge=mat(0xd4dce1,.90,.23,{roughnessMap:metalTex}),dark=mat(0x303439,.56,.58),mail=mat(0x555b5b,.60,.68,{bumpMap:hideTex,bumpScale:.018}),leather=mat(0x503523,.04,.83,{bumpMap:hideTex,bumpScale:.014}),gold=mat(0x987b47,.75,.42),cloth=mat(0x334c50,0,.87,{bumpMap:hideTex,bumpScale:.025}),red=mat(0x71332d,0,.86,{bumpMap:hideTex,bumpScale:.022}),wood=mat(0x5a422c,0,.86,{bumpMap:hideTex,bumpScale:.028}),stone=mat(0x99978e,0,.93,{map:stoneTex,bumpMap:stoneTex,bumpScale:.04}),trim=mat(0xb6b0a2,0,.86,{map:stoneTex,bumpMap:stoneTex,bumpScale:.025}),dirt=mat(0x666052,0,1,{bumpMap:stoneTex,bumpScale:.07});
 function env(scene){let pmrem,s;try{s=new T.Scene();s.background=new T.Color(0x8896a2);const panel=(w,h,x,y,z,rot,c)=>{let p=new T.Mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({color:c}));p.position.set(x,y,z);p.rotation.set(...rot);s.add(p)};
 panel(8,6,-4,3,0,[0,Math.PI/2,0],new T.Color(2.3,2.1,1.8));panel(5,8,4,1,0,[0,-Math.PI/2,0],new T.Color(.85,1.05,1.25));panel(9,9,0,5,0,[Math.PI/2,0,0],new T.Color(1.5,1.65,1.8));panel(10,10,0,-4,0,[-Math.PI/2,0,0],0x4a4239);
 pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(s,.07,.1,20).texture;scene.environmentIntensity=.85;}catch(e){console.warn('Reflection fallback',e);steel.metalness=.38;edge.metalness=.42;gold.metalness=.38;dark.metalness=.2}finally{pmrem?.dispose();s?.traverse(a=>{if(a.isMesh){a.geometry.dispose();a.material.dispose()}})}}
 function batch(p,material,list){const inst=new T.InstancedMesh(new T.BoxGeometry(1,1,1),material,list.length),dummy=new T.Object3D(),col=new T.Color();list.forEach((v,i)=>{dummy.position.set(...v.pos);dummy.scale.set(...v.size);dummy.rotation.set(...(v.rot||[0,0,0]));dummy.updateMatrix();inst.setMatrixAt(i,dummy.matrix);col.setRGB(v.shade,v.shade,v.shade*.98);inst.setColorAt(i,col)});inst.instanceMatrix.needsUpdate=true;inst.instanceColor.needsUpdate=true;inst.castShadow=true;inst.receiveShadow=true;inst.computeBoundingSphere();p.add(inst)}
 function courtyard(scene){const g=group(scene),floor=[],walls=[],tr=[];const block=(list,pos,size,rot=null)=>list.push({pos,size,rot,shade:.74+r()*.30});
 box(g,dirt,30,.35,30,0,-.185,0);
 for(let z=-6;z<7;z++)for(let x=-7;x<7;x++)block(floor,[x*.82+(z%2)*.18,.012,z*.82],[.76+r()*.03,.10,.75+r()*.04],[0,(r()-.5)*.025,0]);
 batch(g,stone,floor);
 const spring=1.94,rad=1.20;
 for(let row=0;row<10;row++)for(let j=-9;j<10;j++){const x=j*.62+(row%2)*.31,y=.21+row*.41,inner=y<spring?rad:y<spring+rad?Math.sqrt(Math.max(0,rad*rad-(y-spring)**2)):0;if(inner>0&&Math.abs(x)<inner+.14)continue;block(walls,[x,y,-5.12],[.60,.397,.56])}
 for(const s of [-1,1]){for(let row=0;row<8;row++)for(let j=0;j<17;j++)block(walls,[s*5.75,.21+row*.41,-5+j*.64+(row%2)*.3],[.56,.397,.62]);for(let j=0;j<8;j++)block(tr,[s*1.38,.125+j*.245,-4.78],[.32,.24,.72]);for(let j=0;j<7;j++)block(tr,[s*2.9,.3+j*.54,-4.65],[.61,.52,.70]);block(tr,[s*2.9,3.99,-4.65],[.85,.20,.83]);for(let j=1;j<9;j+=2)block(tr,[s*j*.65,4.29,-5.12],[.47,.49,.63])}
 for(let i=0;i<17;i++){const a=(i+.5)*Math.PI/17;block(tr,[Math.cos(a)*1.39,spring+Math.sin(a)*1.39,-4.78],[.26,.38,.72],[0,0,a-Math.PI/2])}batch(g,stone,walls);batch(g,trim,tr);
 // A dark recessed gateway with iron-bound wooden planks.
 for(let j=-5;j<=5;j++){const x=j*.20,height=spring+Math.sqrt(Math.max(0,1.13**2-x*x));box(g,wood,.199,height,.12,x,height/2,-5.39)}
 for(let y of [.53,1.5,2.05])box(g,dark,2.25,.065,.05,0,y,-5.30);box(g,dark,.045,2.62,.05,0,1.31,-5.29);
 for(const s of [-1,1]){const banner=group(g,s*3.9,3.43,-4.73);box(banner,wood,1.12,.055,.09,0,.05,0);ell(banner,gold,-.59,.05,0,.045,.045,.045);ell(banner,gold,.59,.05,0,.045,.045,.045);
 const shape=new T.Shape();shape.moveTo(-.43,0);shape.lineTo(.43,0);shape.lineTo(.43,-1.3);shape.lineTo(0,-1.61);shape.lineTo(-.43,-1.3);shape.closePath();const bm=mesh(banner,new T.ShapeGeometry(shape),s<0?red:cloth,0,0,.03);bm.material.side=T.DoubleSide;box(banner,gold,.06,.73,.015,0,-.71,.052);box(banner,gold,.48,.06,.015,0,-.60,.052);
 const rack=group(g,s*4.7,0,-3.25);box(rack,wood,.11,1.5,.13,0,.75,0);box(rack,wood,.95,.12,.15,0,1.24,0);for(let j=0;j<3;j++){const beam=box(rack,wood,.055,1.46,.055,-.31+j*.31,.76,.08);beam.rotation.z=(j-1)*.08}
 const barrel=group(g,s*4.7,0,-1.7);cyl(barrel,wood,.31,.28,.72,0,.36,0);for(let y of [.10,.34,.62])cyl(barrel,dark,.315,.315,.044,0,y,0)}
 }
 function rings(profile,n=28){const v=[],uv=[],idx=[];for(let k=0;k<profile.length;k++){const [y,rx,rz]=profile[k];for(let j=0;j<=n;j++){const a=j/n*Math.PI*2;v.push(Math.sin(a)*rx,y,Math.cos(a)*rz);uv.push(j/n,k/(profile.length-1))}}for(let k=0;k<profile.length-1;k++)for(let j=0;j<n;j++){const a=k*(n+1)+j,b=a+1,c=a+n+1,d=c+1;idx.push(a,b,c,b,d,c)}const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(v,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.setIndex(idx);geo.computeVertexNormals();return geo}
 function breastplate(p){ell(p,mail,0,.23,0,.263,.28,.140);mesh(p,rings(CUIRASS_PROFILE),steel);
 for(let i=0;i<4;i++){const y=.12-i*.047,rx=.259+i*.014;mesh(p,rings([[y-.043,rx+.008,.151+i*.014],[y,rx,.155+i*.013]]),steel);for(const s of [-1,1])ell(p,dark,s*.19,y-.02,.145+i*.012,.012,.012,.008)}
 mesh(p,rings([[-.033,.303,.185],[.035,.30,.183]]),leather);box(p,gold,.084,.061,.024,.04,0,.196);box(p,dark,.054,.033,.026,.04,0,.212);
 const sh=new T.Shape();sh.moveTo(-.044,.02);sh.lineTo(.044,.02);sh.lineTo(.042,-.033);sh.lineTo(0,-.069);sh.lineTo(-.042,-.033);sh.closePath();mesh(p,new T.ShapeGeometry(sh),gold,.10,.33,.187);
 for(const s of [-1,1])for(let i=0;i<3;i++)ell(p,dark,s*(.21-i*.018),.44-i*.043,.113+i*.018,.009,.009,.006);
 }
 function helmet(p){ell(p,mail,0,-.015,0,.145,.15,.14);mesh(p,rings([[-.08,.166,.139],[-.035,.183,.17],[.045,.188,.182],[.13,.172,.169],[.20,.13,.13],[.238,.071,.075],[.257,.001,.001]],32),steel);
 ell(p,steel,0,.045,.068,.175,.102,.15);box(p,dark,.267,.032,.035,0,.078,.216);box(p,edge,.27,.012,.026,0,.101,.218);ell(p,steel,0,-.054,.063,.16,.086,.131);
 for(let i=-3;i<=3;i++)box(p,dark,.009,.026,.012,i*.028,-.031,.194-Math.abs(i)*.006);for(const s of [-1,1])ell(p,gold,s*.175,.071,.065,.017,.018,.022);mesh(p,rings([[-.13,.139,.144],[-.093,.174,.163]]),steel)}
 function legs(knight){for(const s of [-1,1]){const g=group(knight,s*.15,.94,0);ell(g,mail,0,-.18,0,.102,.26,.105);mesh(g,rings([[-.40,.084,.094],[-.32,.106,.118],[-.09,.116,.130],[0,.104,.119]],24),steel);ell(g,steel,0,-.43,.055,.118,.10,.116);ell(g,steel,s*.067,-.43,.012,.075,.064,.069);mesh(g,rings([[-.83,.058,.066],[-.70,.070,.085],[-.52,.087,.099],[-.45,.084,.091]],24),steel);for(let j=0;j<5;j++)ell(g,steel,0,-.85,.035+j*.038,.088-j*.002,.048,.065);ell(g,leather,0,-.889,.108,.087,.025,.139)}}
 function sword(parent,scale=1){const g=group(parent);g.scale.setScalar(scale);const d=bladeData(),geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(d.vertices,3));geo.setAttribute('uv',new T.Float32BufferAttribute(d.uv,2));geo.setIndex(d.indices);const flat=geo.toNonIndexed();geo.dispose();flat.computeVertexNormals();mesh(g,flat,edge);
 for(const s of [-1,1]){const path=new T.CatmullRomCurve3([new T.Vector3(0,.145,0),new T.Vector3(s*.07,.145,0),new T.Vector3(s*.145,.157,0),new T.Vector3(s*.175,.188,0)]);mesh(g,new T.TubeGeometry(path,12,.018,8,false),dark);ell(g,gold,s*.175,.188,0,.020,.019,.020)}
 cyl(g,leather,.031,.035,.274,0,-.017,0);for(let i=0;i<9;i++)cyl(g,dark,.034,.034,.005,0,-.135+i*.029,0);cyl(g,gold,.039,.039,.025,0,.123,0);cyl(g,dark,.039,.039,.027,0,-.15,0);ell(g,dark,0,-.194,0,.046,.043,.034);ell(g,gold,0,-.194,.027,.024,.026,.009);ell(g,gold,0,-.194,-.027,.024,.026,.009);return g}
 return {steel,edge,dark,leather,gold,cloth,wood,mail,env,courtyard,breastplate,helmet,legs,sword};
}
