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

// Source map IBS-M-MAIN uses flat-top odd-q: B/D/... sit half a row below A/C/....
const even=hexCenter(0,displayRowToAxial(0,0));
const odd=hexCenter(1,displayRowToAxial(1,0));
if(Math.abs((odd.y-even.y)-HEX_ROW_HEIGHT/2)>1e-9)throw new Error("odd-q projection invariant failed");
const compassRotations=[150,210,270,330,30,90];
if(compassRotations.some((rotation,index)=>headingRotation(index+1)!==rotation))throw new Error("IBS-M-MAIN heading compass invariant failed");
