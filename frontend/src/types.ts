export type Side="axis"|"allies";
export type Phase="contact_setup"|"reinforcement"|"movement_planning"|"torpedo_planning"|"movement_resolution"|"gunnery"|"torpedo_effects"|"fire_end"|"complete";
export interface HexCoord{q:number;r:number}
export interface GunMount{id:string;kind:"primary"|"secondary";position:string;firepower:number;caliber:number;arcs:string[];armour:number|null;destroyed:boolean;fired_this_phase:boolean}
export interface TorpedoLauncher{id:string;position:string;arcs:string[];torpedoes:number;reloads:number;loaded:number;reloads_remaining:number;destroyed:boolean;reload_turns_remaining:number}
export interface Ship{id:string;name:string;side:Side;ship_type:string;position:HexCoord|null;heading:number;current_speed:number;hull:number|null;max_hull:number|null;fire_markers:number;fired:boolean;sunk:boolean;asset:string|null;max_speed:number|null;min_legal_speed:number|null;max_legal_speed:number|null;torpedo_type:string|null;gun_mounts:GunMount[];torpedo_launchers:TorpedoLauncher[]}
export interface Event{sequence:number;turn:number;phase:Phase;type:string;message:string;rule?:{rule_id:string;document:string;pdf_page?:number;section?:string};dice?:{notation:string;raw:number;adjusted?:number}}
export interface Observation{game_id:string;scenario_id:string;scenario_title:string;side:Side;turn:number;max_turns:number;phase:Phase;ships:Ship[];score:Record<string,number>;recent_events:Event[];winner:Side|null;victory_reason:string|null}
