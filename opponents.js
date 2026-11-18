// All opponents use the same five-zone combat system; no hidden input reading.
export const OPPONENTS={
 squire:{name:'The Squire',title:'Edric',difficulty:'I · Novice',description:'Long windups, predictable high cuts, and generous openings.',wind:1.16,jitter:.17,idle:.78,recovery:.91,feint:0,damage:.72,guard:68,guardRegen:6,adapt:0,counter:0,weights:[4,2,2,1,1],color:0x929c9e,foot:.72},
 knight:{name:'The Valley Knight',title:'Ser Aldren',difficulty:'II · Intermediate',description:'Balanced offense, defense and occasional feints.',wind:.78,jitter:.31,idle:.45,recovery:.66,feint:.27,damage:1,guard:100,guardRegen:8,adapt:.12,counter:0,weights:[1,1,1,1,1],color:0xabb3b9,foot:1},
 duelist:{name:'The Duelist',title:'Ser Lucan',difficulty:'III · Expert',description:'Quick cuts, frequent feints, light damage, short openings.',wind:.58,jitter:.16,idle:.34,recovery:.40,feint:.50,damage:.88,guard:82,guardRegen:8,adapt:.23,counter:.22,weights:[1,3,3,1,1],color:0xa7b7c8,foot:1.15},
 mercenary:{name:'The Mercenary',title:'Garrick',difficulty:'IV · Veteran',description:'Heavy blows, strong guard, slower but punishing attacks.',wind:.96,jitter:.18,idle:.27,recovery:.83,feint:.12,damage:1.38,guard:125,guardRegen:10,adapt:.10,counter:0,weights:[3,1,1,3,3],color:0x716b62,foot:1.28},
 master:{name:'The Swordmaster',title:'Master Rowan',difficulty:'V · Master',description:'Varied attacks, reads repeated habits and counters predictable cuts.',wind:.64,jitter:.24,idle:.30,recovery:.49,feint:.39,damage:1.13,guard:112,guardRegen:12,adapt:.62,counter:.62,weights:[1,1,1,1,1],color:0x626e78,foot:.95}
};
export function opponentFor(id){return OPPONENTS[id]||OPPONENTS.knight}
export function pickZone(zones,profile,history={},last=null,roll=.5){
 const weights=zones.map((z,i)=>Math.max(.15,(profile.weights[i]||1)*(1-(z===last?.22:0))/(1+profile.adapt*(history[z]||0))));
 let n=Math.max(0,Math.min(.999999,roll))*weights.reduce((a,b)=>a+b,0);for(let i=0;i<zones.length;i++){n-=weights[i];if(n<0)return zones[i]}return zones.at(-1)
}
export function remember(history,zone){for(const key of Object.keys(history))history[key]*=.8;history[zone]=(history[zone]||0)+1}
export function counterChance(profile,history,zone){return Math.min(.72,profile.counter*Math.max(0,Math.min(1,((history[zone]||0)-1.1)/2)))}
export function scaledDamage(n,m){return Math.max(1,Math.round(n*m))}
