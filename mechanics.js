// Advanced duel rules are opt-in; the training bout retains the original balance.
export const ARMOR={head:{label:'Helmet',hit:18,riposte:28,received:18},upperLeft:{label:'Upper plate',hit:16,riposte:30,received:20},upperRight:{label:'Upper plate',hit:16,riposte:30,received:20},lowerLeft:{label:'Lower armor',hit:20,riposte:34,received:16},lowerRight:{label:'Lower armor',hit:20,riposte:34,received:16}};
export function damageFor(zone,riposte=false){const a=ARMOR[zone];return a?(riposte?a.riposte:a.hit):18}
export function chooseFeint(zones,initial,roll){const options=zones.filter(z=>z!==initial);return options[Math.min(options.length-1,Math.max(0,Math.floor(roll*options.length)))]}
export function windupPlan(zones,initial,now,duration,feintRoll,zoneRoll,chance=.27){const feint=feintRoll<chance;return {dir:initial,start:now,until:now+duration+(feint?.19:0),feintTo:feint?chooseFeint(zones,initial,zoneRoll):null,feintAt:now+duration*.42}}
export function clamp01(x){return Math.min(1,Math.max(0,x))}
export function footwork(phase,progress){const p=clamp01(progress);switch(phase){case 'windup':return .08+.18*p;case 'recovery':return -.12*Math.sin(Math.PI*p);case 'strike':return .26+.24*Math.sin(Math.PI*p);default:return 0}}
