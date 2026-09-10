"use strict";
(() => {
// 铁底湾的回响 IV — RTT 平台 JS 引擎（经典逐舰模式）。
// 规则数据全部来自 data.js（由仓库 YAML 导出）；想定特例解释器与
// Python 版 scenario_rules.py / engine.py 对齐。已知与 Python 引擎的差异
// 见 about.html「与原版引擎的差异」一节。
/* global data */
const D = (typeof data !== "undefined" && data) || require("../data.js")
const hex = (typeof IBS !== "undefined" && IBS.hex) || require("./hex.js")

// ---------------------------------------------------------------- 随机数（MLCG，可复现）
function random(range, game) {
	game.seed = (game.seed * 200105) % 34359738337
	return game.seed % range
}
function rollDie(game) { return random(6, game) + 1 }
function roll2d6(game) { return rollDie(game) + rollDie(game) }

const D66_VALUES = D.rules.d66Values
function rollD66(game) {
	const t = rollDie(game), o = rollDie(game)
	return t * 10 + o
}
function d66Adjust(value, modifier) {
	const index = Math.min(Math.max(D66_VALUES.indexOf(value) + modifier, 0), D66_VALUES.length - 1)
	return D66_VALUES[index]
}

// ---------------------------------------------------------------- 基础规则表
function hitCount(firepower, adjustedRoll) {
	const row = D.rules.gunneryHitTable.find(
		(r) => firepower >= r.firepower_min && firepower <= r.firepower_max
	)
	if (!row) return 0
	const column = adjustedRoll <= 31 ? String(adjustedRoll) : "32_plus"
	return intValue(row[column])
}
function torpedoEffect(roll, displacement) {
	const key = roll <= 2 ? "2-" : roll >= 12 ? "12+" : String(roll)
	const table = D.rules.torpedoCollision
	const column = table.columns.indexOf(displacement)
	if (column < 0 || !table.rows[key]) return "Miss"
	return table.rows[key][column]
}
function parseEffect(effect) {
	if (effect === "Miss") return { hull: 0, speed: 0, sunk: false, fire: false }
	if (effect === "Sunk") return { hull: 999, speed: 0, sunk: true, fire: false }
	const hull = /(\d+)H/.test(effect) ? parseInt(/(\d+)H/.exec(effect)[1], 10) : 0
	const speed = /(?:\/-)?(\d+)MF/.test(effect) ? parseInt(/(?:\/-)?(\d+)MF/.exec(effect)[1], 10) : 0
	return { hull, speed, sunk: false, fire: effect.indexOf("*") >= 0 }
}
function intValue(v) { const n = parseInt(v, 10); return isNaN(n) ? 0 : n }
function rangeValue(rows, distance) { return rows.find((r) => intValue(r.min) <= Math.max(1, distance) && Math.max(1, distance) <= intValue(r.max)) }
function rangeModifier(kind, distance, japanese) {
	const row = rangeValue(D.rules.modifiers.range_modifier[kind], distance)
	return intValue(row.value) + (japanese ? 0 : intValue(row.non_japanese_additional || 0))
}
function targetSpeedModifier(kind, speed) {
	const table = D.rules.modifiers.target_speed_modifier[kind]
	if (table[speed] !== undefined) return intValue(table[speed])
	for (const key of Object.keys(table)) {
		if (typeof key === "string" && key.endsWith("+") && speed >= parseInt(key, 10)) return intValue(table[key])
		if (typeof key === "string" && key.indexOf("-") > 0) {
			const [lo, hi] = key.split("-").map((n) => parseInt(n, 10))
			if (speed >= lo && speed <= hi) return intValue(table[key])
		}
	}
	return 0
}
function table2d6(table, roll) {
	if (table[roll] !== undefined) return table[roll]
	for (const key of Object.keys(table)) {
		if (typeof key === "string" && key.indexOf("-") > 0) {
			const [lo, hi] = key.split("-").map((n) => parseInt(n, 10))
			if (roll >= lo && roll <= hi) return table[key]
		}
	}
	return { kind: "no_effect" }
}
function gunneryResult(roll) {
	const results = D.rules.gunneryResults
	return roll >= 66 ? results["66+"] : results[roll] !== undefined ? results[roll] : { kind: "miss" }
}
function nationOf(shipId) {
	return shipId.indexOf("IBS-U-IJN-") === 0 ? "JP"
		: shipId.indexOf("IBS-U-USN-") === 0 ? "US"
		: (shipId.indexOf("IBS-U-RN-") === 0 || shipId.indexOf("IBS-U-RAN-") === 0) ? "UK"
		: shipId.indexOf("IBS-U-KM-") === 0 ? "DE"
		: shipId.indexOf("IBS-U-NLD-") === 0 ? "NL" : "JP"
}
function penetration(nation, caliber, distance) {
	const dist = Math.max(1, distance)
	const column = ["1-2", "3-5", "6-7", "8-10", "11-13", "14-17", "18-20", "21-25"].find((label) => {
		const [lo, hi] = label.split("-").map((n) => parseInt(n, 10))
		return dist >= lo && dist <= hi
	})
	let best = 0
	for (const row of D.rules.armourPenetration) {
		const calibers = String(row.caliber_in).split("|").map((v) => parseFloat(v))
		const nations = String(row.nation).split("_")
		if (!calibers.some((c) => Math.abs(c - caliber) < 0.26) || nations.indexOf(nation) < 0) continue
		const value = row[column]
		if (value === "-" || value === undefined) continue
		const inches = parseFloat(value)
		if (!isNaN(inches) && inches > best) best = inches
	}
	return best
}
function specialDamageResult(roll, band) {
	const direct = D.rules.specialDamage.direct_results
	if (direct[roll] !== undefined) return direct[roll]
	for (const key of Object.keys(direct)) {
		if (key.indexOf("-") > 0) {
			const [lo, hi] = key.split("-").map((n) => parseInt(n, 10))
			if (roll >= lo && roll <= hi) return direct[key]
		}
	}
	const base = D.rules.specialDamage.results[String(roll)]
	if (!base) return { effect: "Miss" }
	return { effect: base[band], additional: base.additional, armour_check: true }
}

// ---------------------------------------------------------------- 想定特例解释器
function kinds(scenario, kind) {
	return (scenario.special_rule_kinds || []).filter((k) => k.kind === kind)
}
function turnRestrictionReason(scenario, sideValue, turn, action) {
	for (const item of kinds(scenario, "turn_restriction")) {
		if ((item.sides || []).indexOf(sideValue) >= 0 && (item.turns || []).indexOf(turn) >= 0 && (item.actions || []).indexOf(action) >= 0) {
			return item.reason || ("想定特例 " + item.id)
		}
	}
	return null
}
function torpedoRollBonus(scenario, sideValue, turn) {
	let total = 0
	for (const item of kinds(scenario, "torpedo_roll_bonus")) {
		if ((item.sides || []).indexOf(sideValue) >= 0 && (item.turns || []).indexOf(turn) >= 0) total += intValue(item.bonus)
	}
	return total
}
function displayRow(c) { return c.r + (c.q - (c.q & 1)) / 2 }
function gunnerySituationModifier(scenario, attackerPos, targetPos) {
	let total = 0
	for (const item of kinds(scenario, "gunnery_direction_modifier")) {
		if (item.toward === "south" && attackerPos && targetPos && displayRow(targetPos) > displayRow(attackerPos)) {
			total += intValue(item.modifier)
		}
	}
	return total
}
function firepowerMultiplier(scenario, sideValue, shipType, caliber, direction) {
	for (const item of kinds(scenario, "firepower_multiplier")) {
		if ((item.sides || []).indexOf(sideValue) < 0) continue
		if (item.ship_types && item.ship_types.indexOf(shipType) < 0) continue
		const lo = item.caliber_min !== undefined ? item.caliber_min : 0
		const hi = item.caliber_max !== undefined ? item.caliber_max : 999
		if (!(caliber >= lo && caliber <= hi)) continue
		if (item.unless_direction && item.unless_direction === direction) continue
		return { factor: item.factor !== undefined ? item.factor : 1, ceil: !!item.ceil }
	}
	return null
}
function penetrationBlocked(scenario, sideValue, turn, shipType) {
	for (const item of kinds(scenario, "penetration_block")) {
		if ((item.sides || []).indexOf(sideValue) >= 0 && (item.turns || []).indexOf(turn) >= 0 &&
			(!item.ship_types || item.ship_types.indexOf(shipType) >= 0)) return true
	}
	return false
}
function visibilityForTurn(scenario, sideValue, turn) {
	for (const item of kinds(scenario, "visibility_schedule")) {
		if (item.side !== sideValue) continue
		const fromTurn = item.from_turn || {}
		const keys = Object.keys(fromTurn).map((k) => parseInt(k, 10)).filter((t) => turn >= t)
		if (keys.length) return intValue(fromTurn[String(Math.max.apply(null, keys))])
	}
	return null
}

// ---------------------------------------------------------------- 舰船构造
function makeShip(entry, scenario) {
	const record = D.ships[entry.id]
	let ship
	if (record) {
		ship = {
			id: entry.id, name: entry.name || record.name, side: entry.side,
			type: record.ship_type, band: record.displacement_band,
			hullRows: record.hull_rows.slice(), speedDamageTrack: record.speed_damage_track.map((r) => r.slice()),
			speedCrossed: [0, 0, 0],
			guns: record.guns.map((g) => Object.assign({}, g, { destroyed: false, fired: false })),
			launchers: (record.torpedo_launchers || []).map((t) => Object.assign({}, t, {
				loaded: t.torpedoes, reloadsRemaining: entry.torpedo_reloads !== undefined ? entry.torpedo_reloads : t.reloads, destroyed: false, reloadTurns: 0,
			})),
			torpedoType: record.torpedo_type || null,
			armour: Object.assign({ primary: 0, secondary: 0, belt: 0, bridge: 0 }, record.armour || {}),
			fireControl: !!record.fire_control, radar: !!record.radar, aircraft: !!record.aircraft,
			vp: record.vp,
		}
	} else {
		const t = D.templates[entry.template] || { type: "DD", hull: 5, speed_track: [6, 6, 6], primary_gf: 2, primary_caliber: 5, torpedoes: 0, vp: 2 }
		const track = (t.speed_track || [6, 6, 6]).map((s) => {
			const row = []
			for (let v = s; v >= 1; v--) row.push(v)
			return row
		})
		ship = {
			id: entry.id, name: entry.name, side: entry.side, type: t.type,
			band: t.type === "DD" || t.type === "APD" ? "A" : "C",
			hullRows: [t.hull], speedDamageTrack: track, speedCrossed: [0, 0, 0],
			guns: [{ id: "P1", kind: "primary", position: "bow", firepower: t.primary_gf || 0, caliber: t.primary_caliber || 5, arcs: ["bow", "port", "starboard"], destroyed: false, fired: false }],
			launchers: t.torpedoes ? [{ id: "TT1", position: "midships", arcs: ["port", "starboard"], torpedoes: t.torpedoes, loaded: t.torpedoes, reloadsRemaining: 0, destroyed: false, reloadTurns: 0 }] : [],
			torpedoType: t.torpedo_type || null,
			armour: { primary: 0, secondary: 0, belt: t.belt_armor || 0, bridge: 0 },
			fireControl: false, radar: false, aircraft: false, vp: t.vp || 0,
		}
		ship.hull = t.hull
	}
	ship.hull = ship.hullRows.reduce((a, b) => a + b, 0)
	ship.maxHull = ship.hull
	ship.id = entry.id
	ship.flagship = !!entry.flagship
	ship.reinforcementTurn = entry.reinforcement_turn || null
	ship.position = entry.position ? hex.fromLabel(entry.position) : null
	ship.positionLabel = entry.position || null
	ship.heading = entry.heading || 1
	ship.speed = entry.speed || 0
	ship.previousSpeed = ship.speed
	ship.sunk = false
	ship.fired = false
	ship.fireMarkers = 0
	ship.radarDestroyed = false
	ship.mfcDestroyed = false
	ship.torpedoAmmo = ship.launchers.reduce((a, l) => a + l.loaded, 0)
	// 想定编制修改（special_rule_kinds.setup_modification）
	for (const mod of kinds(scenario, "setup_modification")) {
		if (mod.ship_id && mod.ship_id !== ship.id) continue
		if (!mod.ship_id && (mod.sides || []).indexOf(entry.side) < 0) continue
		if (mod.remove_mounts) {
			for (const g of ship.guns) {
				if (g.kind === mod.remove_mounts.kind && (!mod.remove_mounts.position || g.position === mod.remove_mounts.position)) g.destroyed = true
			}
		}
		if (mod.hull_damage) ship.hull = Math.max(1, ship.hull - intValue(mod.hull_damage))
		if (mod.speed_damage_track) ship.speedDamageTrack = mod.speed_damage_track.map((r) => r.slice())
		if (mod.radar) ship.radar = true
	}
	return ship
}

// ---------------------------------------------------------------- 引擎主体
function createGame(seed, scenarioId, options) {
	const scenario = D.scenarios[scenarioId]
	if (!scenario) throw new Error("Unknown scenario " + scenarioId)
	const game = {
		seed: seed >>> 0, scenario: scenarioId, options: Object.assign({}, options || {}),
		log: [], undo: [], state: "reinforcement", active: ["Axis", "Allies"],
		turn: 1, maxTurns: scenario.turns, result: null, victory: null,
		visibility: { Axis: scenario.visibility.axis, Allies: scenario.visibility.allies },
		ships: {}, scenarioState: {}, markers: [], torpedoTracks: [], trackSeq: 0,
		pending: {}, undo: [], undoBy: {}, sealed: {},
	}
	for (const entry of scenario.ships) game.ships[entry.id] = makeShip(entry, scenario)
	if (scenario.reinforcements) {
		for (const entry of scenario.reinforcements.ships) {
			const ship = makeShip(Object.assign({}, entry, { reinforcement_turn: scenario.reinforcements.arrival.turn }), scenario)
			ship.position = null; ship.positionLabel = null
			game.ships[entry.id] = ship
		}
		game.reinforcement = {
			triggerTurn: scenario.reinforcements.trigger.turn, arrivalTurn: scenario.reinforcements.arrival.turn,
			succeedsOn: scenario.reinforcements.trigger.succeeds_on || [1, 2, 3, 4, 5, 6], rolled: false, available: false,
		}
	}
	for (const item of kinds(scenario, "storm_markers")) {
		for (const label of item.hexes || []) {
			game.markers.push({ id: "STORM-" + label, kind: "storm", position: hex.fromLabel(label) })
		}
	}
	const alertRule = kinds(scenario, "alert_states")[0]
	if (alertRule) {
		const alerted = []
		for (const ship of Object.values(game.ships)) {
			if ((alertRule.sides || []).indexOf(ship.side) >= 0 &&
				((alertRule.initial || {}).ships || []).indexOf(ship.id) >= 0) alerted.push(ship.id)
		}
		game.scenarioState.alerted = alerted
	}
	for (const side of ["axis", "allies"]) {
		const value = visibilityForTurn(scenario, side, 1)
		if (value !== null) game.visibility[side === "axis" ? "Axis" : "Allies"] = value
	}
	game.log.push("** 想定开始：" + scenario.title + "（" + scenario.date + "） **")
	game.log.push("第 1 回合 · 能见度 日" + game.visibility.Axis + " / 盟" + game.visibility.Allies)
	return game
}

function maxSpeedForTurn(ship, turn) {
	const row = ship.speedDamageTrack[(turn - 1) % 3]
	const crossed = ship.speedCrossed[(turn - 1) % 3]
	return crossed < row.length ? row[crossed] : 0
}
function legalSpeedRange(ship, turn) {
	let maximum = Math.min(maxSpeedForTurn(ship, turn), ship.previousSpeed + 2)
	const deceleration = ship.type === "BB" || ship.type === "BC" ? 3 : 5
	let minimum = Math.max(0, ship.previousSpeed - deceleration)
	if (minimum > maximum) minimum = 0
	return [minimum, maximum]
}
function movementCommands(plan) {
	const normalized = String(plan || "0").trim().toUpperCase().replace(/左/g, "P").replace(/右/g, "S")
	if (normalized === "0" || normalized === "") return []
	const tokens = normalized.match(/\d+|PP|SS|LL|RR|P|S|L|R/g)
	if (!tokens || tokens.join("") !== normalized) throw new Error("非法移动计划 " + plan)
	const mapping = { P: "turn_port_60", L: "turn_port_60", S: "turn_starboard_60", R: "turn_starboard_60", PP: "turn_port_120", LL: "turn_port_120", SS: "turn_starboard_120", RR: "turn_starboard_120" }
	const commands = []
	for (const token of tokens) {
		if (/^\d+$/.test(token)) for (let i = 0; i < parseInt(token, 10); i++) commands.push("advance")
		else commands.push(mapping[token])
	}
	return commands
}
function validateCommands(commands) {
	if (!commands.length) return
	const turns = ["turn_port_60", "turn_starboard_60", "turn_port_120", "turn_starboard_120"]
	if (commands[0] !== "advance") throw new Error("第一道命令必须是前进")
	for (let i = 0; i < commands.length; i++) {
		const c = commands[i]
		if (c !== "advance" && turns.indexOf(c) < 0) throw new Error("未知移动命令 " + c)
		if (turns.indexOf(c) >= 0) {
			if (i === commands.length - 1 && c !== "turn_port_60" && c !== "turn_starboard_60") throw new Error("回合结束只允许 60 度转向")
			if (i < commands.length - 1 && commands[i + 1] !== "advance") throw new Error("转向后必须前进 1 MF")
		}
	}
}
function movementCost(plan) {
	const commands = movementCommands(plan)
	return commands.filter((c) => c === "advance" || c === "turn_port_120" || c === "turn_starboard_120").length
}
function trajectory(ship, plan) {
	let commands
	try { commands = movementCommands(plan) } catch (e) { return { error: e.message } }
	if (!commands.length) return { path: [], heading: ship.heading }
	let position = ship.position, heading = ship.heading
	const path = []
	try {
		for (const command of commands) {
			if (command === "advance") {
				position = hex.neighbor(position, heading, game.mapColumns, game.mapRows)
				path.push({ position, heading })
			} else if (command === "turn_port_60") heading = heading === 1 ? 6 : heading - 1
			else if (command === "turn_starboard_60") heading = heading === 6 ? 1 : heading + 1
			else if (command === "turn_port_120") { heading = ((heading - 3) % 6 + 6) % 6 + 1; path.push({ position, heading }) }
			else if (command === "turn_starboard_120") { heading = ((heading + 1) % 6) % 6 + 1; path.push({ position, heading }) }
		}
	} catch (e) { return { error: "移动离开地图边缘" } }
	return { path, heading }
}

const IBSApi = {
	random, rollDie, roll2d6, rollD66, d66Adjust, hitCount, torpedoEffect, parseEffect,
	rangeModifier, targetSpeedModifier, table2d6, gunneryResult, specialDamageResult,
	nationOf, penetration, turnRestrictionReason, torpedoRollBonus, gunnerySituationModifier,
	firepowerMultiplier, penetrationBlocked, visibilityForTurn, kinds,
	createGame, makeShip, maxSpeedForTurn, legalSpeedRange, movementCommands, validateCommands,
	movementCost, trajectory,
	intValue,
}
if (typeof module !== "undefined" && module.exports) module.exports = IBSApi
else (window.IBS = window.IBS || {})['core'] = IBSApi
})();
