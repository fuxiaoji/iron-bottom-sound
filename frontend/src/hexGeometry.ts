export const HEX_SIZE=24;
export const HEX_ROW_HEIGHT=HEX_SIZE*Math.sqrt(3);

export function displayRowToAxial(q:number,row:number){
 return row-Math.floor(q/2);
}

export function hexCenter(q:number,r:number){
 return {x:38+q*HEX_SIZE*1.5,y:35+(r+q/2)*HEX_ROW_HEIGHT};
}

export function hexDistance(a:{q:number;r:number},b:{q:number;r:number}){
 const dq=a.q-b.q,dr=a.r-b.r;
 return (Math.abs(dq)+Math.abs(dr)+Math.abs(dq+dr))/2;
}

export function columnLabel(q:number){
 return q<26?String.fromCharCode(65+q):String.fromCharCode(65+q-26).repeat(2);
}

export function hexLabel(coord:{q:number;r:number}){
 return `${columnLabel(coord.q)}${coord.r+Math.floor(coord.q/2)+1}`;
}

// Inverse of hexLabel: parse an engine hex label ("R16", "HH27") back into axial
// coordinates. Pure geometry, no rule data. Two-letter columns cover q 26..33.
export function hexFromLabel(label:string){
 const match=/^([A-Z]{1,2})(\d{1,2})$/.exec(label.trim().toUpperCase());
 if(!match)throw new Error(`Invalid hex label ${label}`);
 const letters=match[1];
 const column=letters.length===1?letters.charCodeAt(0)-65:(letters.charCodeAt(0)-65)+26;
 const displayRow=Number.parseInt(match[2],10)-1;
 return {q:column,r:displayRow-Math.floor(column/2)};
}

// IBS-M-MAIN compass: 1 NE, 2 SE, 3 S, 4 SW, 5 NW, 6 N. Counter artwork's
// printed bow arrow points left (180 degrees), so rotate that arrow onto the
// corresponding edge-centre vector.
export function headingRotation(heading:number){
 return (150+((heading-1)%6+6)%6*60)%360;
}

export function headingVector(heading:number,length=1){
 const radians=(180+headingRotation(heading))*Math.PI/180;
 return {x:Math.cos(radians)*length,y:Math.sin(radians)*length};
}

// The source torpedo artwork points to direction 5 (north-west) before rotation.
export function torpedoCounterRotation(heading:number){
 return (((heading-5)%6+6)%6)*60;
}

// Source map IBS-M-MAIN uses flat-top odd-q: B/D/... sit half a row below A/C/....
const even=hexCenter(0,displayRowToAxial(0,0));
const odd=hexCenter(1,displayRowToAxial(1,0));
if(Math.abs((odd.y-even.y)-HEX_ROW_HEIGHT/2)>1e-9)throw new Error("odd-q projection invariant failed");
const compassRotations=[150,210,270,330,30,90];
if(compassRotations.some((rotation,index)=>headingRotation(index+1)!==rotation))throw new Error("IBS-M-MAIN heading compass invariant failed");
const torpedoRotations=[120,180,240,300,0,60];
if(torpedoRotations.some((rotation,index)=>torpedoCounterRotation(index+1)!==rotation))throw new Error("torpedo counter heading invariant failed");
if(hexLabel({q:17,r:7})!=="R16"||hexLabel({q:16,r:7})!=="Q16"||hexLabel({q:0,r:0})!=="A1"||hexLabel({q:33,r:10})!=="HH27")throw new Error("IBS-M-MAIN coordinate label invariant failed");
if(hexLabel(hexFromLabel("HH27"))!=="HH27"||hexFromLabel(hexLabel({q:17,r:7})).q!==17||hexFromLabel("R16").r!==7)throw new Error("hexFromLabel round-trip invariant failed");
