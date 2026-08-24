export const HEX_SIZE=24;
export const HEX_ROW_HEIGHT=HEX_SIZE*Math.sqrt(3);

export function displayRowToAxial(q:number,row:number){
 return row-Math.floor(q/2);
}

export function hexCenter(q:number,r:number){
 return {x:38+q*HEX_SIZE*1.5,y:35+(r+q/2)*HEX_ROW_HEIGHT};
}

export function columnLabel(q:number){
 return q<26?String.fromCharCode(65+q):String.fromCharCode(65+q-26).repeat(2);
}

// The counter artwork is horizontal. On a flat-top grid, a legal heading runs
// through an edge centre, so heading 1 starts at 30 degrees, not at a vertex.
export function headingRotation(heading:number){
 return 30+((heading-1)%6+6)%6*60;
}

// Source map IBS-M-MAIN uses flat-top odd-q: B/D/... sit half a row below A/C/....
const even=hexCenter(0,displayRowToAxial(0,0));
const odd=hexCenter(1,displayRowToAxial(1,0));
if(Math.abs((odd.y-even.y)-HEX_ROW_HEIGHT/2)>1e-9)throw new Error("odd-q projection invariant failed");
if([1,2,3,4,5,6].some((heading,index)=>headingRotation(heading)!==30+index*60))throw new Error("edge-facing heading invariant failed");
