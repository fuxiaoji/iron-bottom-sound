export type Side="axis"|"allies";
export interface ResearchConsent{allow:boolean;handle?:string|null}
export type Phase="contact_setup"|"reinforcement"|"movement_planning"|"torpedo_planning"|"movement_resolution"|"gunnery"|"torpedo_effects"|"fire_end"|"complete";
export interface HexCoord{q:number;r:number}
export interface GunMount{id:string;kind:"primary"|"secondary";position:string;firepower:number;caliber:number;arcs:string[];armour:number|null;destroyed:boolean;fired_this_phase:boolean}
export interface TorpedoLauncher{id:string;position:string;arcs:string[];torpedoes:number;reloads:number;loaded:number;reloads_remaining:number;destroyed:boolean;reload_turns_remaining:number}
export interface Event{sequence:number;turn:number;phase:Phase;type:string;message:string;payload?:Record<string,unknown>;rule?:{rule_id:string;document:string;pdf_page?:number;section?:string};dice?:{notation:string;raw:number;adjusted?:number|null}}
export interface ShipCombatEntry{sequence:number;turn:number;phase:Phase;direction:"inflicted"|"received";event_type:string;message:string;related_ship_id:string|null;related_ship_name:string|null;rule:Event["rule"];dice:Event["dice"];payload?:Record<string,unknown>}
export interface Ship{id:string;name:string;side:Side;ship_type:string;position:HexCoord|null;heading:number;current_speed:number;hull:number|null;max_hull:number|null;fire_markers:number;fired:boolean;sunk:boolean;asset:string|null;max_speed:number|null;speed_damage_crossed?:number[]|null;speed_damage_track?:number[][]|null;min_legal_speed:number|null;max_legal_speed:number|null;torpedo_type:string|null;gun_mounts:GunMount[];torpedo_launchers:TorpedoLauncher[];turn_limit_degrees?:number|null;forced_straight_turns?:number;forced_circle_turns?:number;forced_turn_side?:"port"|"starboard"|null;forced_speed?:number|null;mfc_destroyed?:boolean;radar_destroyed?:boolean;bridge_destroyed?:boolean;rudder_destroyed?:boolean;captain_status?:"fit"|"wounded"|"killed"|null;combat_history:ShipCombatEntry[]}
export interface MovementNextAdvance{hex:HexCoord;label:string;heading:number;cost_delta:number}
export interface MovementNextTurn{action:string;cost_delta:number;heading_after:number;legal:boolean;reason:string|null}
export interface MovementPreview{
 ship_id:string;commands:string[];plan:string;cost:number;valid:boolean;errors:string[];commitable:boolean;
 current_hex:HexCoord|null;current_label:string|null;current_heading:number|null;
 trajectory:{hex:HexCoord;label:string;heading:number;mf:number}[];
 min_cost:number;max_cost:number;
 next_options:{advance:MovementNextAdvance[];turns:MovementNextTurn[]};
 reachable:{hex:HexCoord;label:string;cost:number;final_headings:number[]}[];
 forced:{turn_limit_degrees:number|null;forced_straight_turns:number;forced_circle_turns:number;forced_turn_side:"port"|"starboard"|null;forced_speed:number|null};
}
export interface TorpedoTrack{id:string;side:Side;launcher_ship_id:string;torpedo_type:string;position:HexCoord;heading:number;range_remaining:number;distance_travelled:number;salvo_size:number;launch_position:HexCoord|null;launch_side:"port"|"starboard"|null;launch_angle:"A"|"B"|"X"|"Y"|null;traversed_hexes:HexCoord[];contact_ship_ids:string[];hidden:boolean}
export interface Marker{id:string;kind:string;position:HexCoord|null;ship_id:string|null;target_ship_id:string|null;heading:number|null}
export interface Observation{game_id:string;scenario_id:string;scenario_title:string;side:Side;turn:number;max_turns:number;phase:Phase;visibility:number;ships:Ship[];torpedo_tracks:TorpedoTrack[];markers:Marker[];score:Record<string,number>;recent_events:Event[];winner:Side|null;victory_reason:string|null}
export interface LegalAction{kind:string;ship_id?:string|null;schema_hint:Record<string,unknown>}
export interface BattleReportCapture{side:Side;image_path:string}
export interface BattleReportPlan{
 turn?:number;phase?:string;
 situation_summary?:string|null;phase_goal?:string|null;
 unit_intents?:Record<string,string>;contingency?:string[];
 orders?:Record<string,unknown>;
}
export interface BattleReportAiAction{
 plan:BattleReportPlan;reasoning:string|null;model:string;
 elapsed_ms:number;input_tokens:number;output_tokens:number;
}
export interface BattleReportPhase{phase:string;captures:BattleReportCapture[];narrative:string|null;ai_actions:Record<string,BattleReportAiAction>}
export interface BattleReportTurnEvent{sequence:number;phase:string;type:string;message:string}
export interface BattleReportTurn{turn:number;narrative:string|null;phases:BattleReportPhase[];events:BattleReportTurnEvent[]}
export interface BattleReportMeta{game_id:string;scenario_id:string;scenario_title:string;mode:string;seed:number;turn:number;max_turns:number;phase:string;winner:Side|null;victory_reason:string|null;score:Record<string,number>}
export interface BattleReport{meta:BattleReportMeta;turns:BattleReportTurn[]}
export interface TorpedoAssistCombo{
 ship_id:string;launcher_id:string;launch_at_mf:number;launch_hex:string;launch_heading:number;
 launch_side:"port"|"starboard";launch_angle:"A"|"B"|"X"|"Y";setting_index:number;salvo_size:number;
 torpedo_heading:number;distance:number;aspect:"bow_stern"|"broadside"|null;modifier:number|null;
 hit_probability:number|null;expected_hits:number;intercept_hex:string|null;intercept_turn:number;
 predicted_path:string[];predicted_end:string;blocked_reason:string|null;
}
export interface TorpedoAssistResponse{
 target_id:string|null;target_name:string|null;
 projected_target:{hex:HexCoord|null;label:string|null;heading:number|null;speed:number|null;turns:number}|null;
 combos:TorpedoAssistCombo[];
}
export interface GunneryAssistRecommendation{ship_id:string;target_id:string;mount_ids:string[];range:number;modifier:number}
export interface GunneryAssistExcluded{ship_id:string;reason:string}
export interface GunneryAssistResponse{recommendations:GunneryAssistRecommendation[];excluded:GunneryAssistExcluded[]}
export interface MovementTrajectory{
 ship_id:string;plan:string;cost:number;valid:boolean;commitable:boolean;errors:string[];
 trajectory:{hex:HexCoord;label:string;heading:number;mf:number}[];
 end_hex:string|null;end_heading:number|null;
}
export interface MovementTrajectoriesResponse{trajectories:MovementTrajectory[]}
export interface SealedMovementTrajectory extends MovementTrajectory{name:string;side:Side}
export interface SealedMovementTrajectoriesResponse{trajectories:SealedMovementTrajectory[]}
export interface FireHeatmapSide{
 hexes:Record<string,number>;max_heat:number;
 ships:{ship_id:string;name:string;position:string;heading:number}[];
}
export interface FireHeatmapResponse{viewer:Side;sides:{axis:FireHeatmapSide;allies:FireHeatmapSide}}
export type FireHeatmapMode="off"|"axis"|"allies"|"both"|"ship"
export interface ReinforcementCandidateShip{ship_id:string;name:string;asset:string|null;max_speed:number|null}
export interface ReinforcementCandidates{
 group_available:boolean;arrival_turn:number|null;trigger_turn:number|null;succeeds_on:number[];
 roll_result:{roll:number;available:boolean}|null;
 entry_range:[string,string]|null;entry_hexes:string[];ships:ReinforcementCandidateShip[];
}
