"use strict";
(() => {
// RTT 回合状态机与裁决：增援 → 移动 → 鱼雷 → 炮击 → 火灾 → 回合结束。
// 双方同时封存计划后内部推进（对应 Python 引擎的多阶段裁决）。
/* global data */
const D = (typeof data !== "undefined" && data) || require("../data.js")
const hex = (typeof IBS !== "undefined" && IBS.hex) || require("./hex.js")
const core = (typeof IBS !== "undefined" && IBS.core) || require("./core.js")

const SIDE_VALUES = { Axis: "axis", Allies: "allies" }
const ROLE_VALUES = { axis: "Axis", allies: "Allies" }

function create(seed, scenarioId, options) {
	const game = core.createGame(seed, scenarioId, options)
	game.mapColumns = Math.min(game.maxColumns || 46, 46)
	// 用想定声明地图尺寸（新想定可能 92×78）
	const scenario = D.scenarios[scenarioId]
	game.mapColumns = scenario.map_columns || 46
	game.mapRows = scenario.map_rows || 39
	game.phase = "reinforcement"
	game.submitted = {}
	return game
}

function log(game, text) { game.log.push(text) }

function scenarioOf(game) { return D.scenarios[game.scenario] }

function liveShips(game, side) {
	return Object.values(game.ships).filter((s) => s.side === side && !s.sunk && s.position)
}
function weatherBlocked(game, position) {
	if (!position) return false
	for (const marker of game.markers) {
		if (!marker.position || hex.distance(marker.position, position) > 1) continue
		if (marker.kind === "storm") return true
	}
	return false
}
function canSee(game, attacker, target) {
	if (!attacker.position || !target.position) return false
	if (weatherBlocked(game, attacker.position) || weatherBlocked(game, target.position)) return false
	const illuminated = game.markers.some((m) => m.kind === "star_shell" && m.turn === game.turn &&
		m.position && target.position && hex.distance(m.position, target.position) <= 2)
	const dist = hex.distance(attacker.position, target.position)
	const vis = game.visibility[attacker.side === "axis" ? "Axis" : "Allies"]
	if (dist <= vis) return true
	return !!game.options.radar && attacker.radar && !attacker.radarDestroyed
}

function markAlerted(game, shipId, reason) {
	const scenario = scenarioOf(game)
	const rule = core.kinds(scenario, "alert_states")[0]
	if (!rule || !game.ships[shipId]) return
	const ship = game.ships[shipId]
	if ((rule.sides || []).indexOf(ship.side) < 0) return
	const alerted = game.scenarioState.alerted || []
	if (alerted.indexOf(shipId) >= 0) return
	alerted.push(shipId)
	game.scenarioState.alerted = alerted
	log(game, "⚠ " + ship.name + " 转入警戒状态（" + reason + "）")
}

function applyTurnStartRules(game) {
	const scenario = scenarioOf(game)
	for (const side of ["axis", "allies"]) {
		const value = core.visibilityForTurn(scenario, side, game.turn)
		if (value !== null) game.visibility[side === "axis" ? "Axis" : "Allies"] = value
	}
	const rule = core.kinds(scenario, "alert_states")[0]
	if (rule) {
		const sides = rule.sides || []
		const autoTurn = intOr0(rule.all_alerted_turn)
		if (autoTurn && game.turn >= autoTurn) {
			for (const ship of Object.values(game.ships)) {
				if (sides.indexOf(ship.side) >= 0) markAlerted(game, ship.id, "第 " + autoTurn + " 回合自动警戒")
			}
		}
		const alerted = game.scenarioState.alerted || []
		for (const ship of Object.values(game.ships)) {
			if (sides.indexOf(ship.side) < 0 || alerted.indexOf(ship.id) >= 0 || ship.sunk || !ship.position) continue
			const vis = game.visibility[ship.side === "axis" ? "Axis" : "Allies"]
			const enemyVisible = Object.values(game.ships).some((e) =>
				e.side !== ship.side && !e.sunk && e.position && hex.distance(ship.position, e.position) <= vis)
			if (enemyVisible) markAlerted(game, ship.id, "敌舰进入可视范围")
		}
	}
	log(game, "第 " + game.turn + " 回合 · 能见度 日" + game.visibility.Axis + " / 盟" + game.visibility.Allies)
}

function intOr0(v) { const n = parseInt(v, 10); return isNaN(n) ? 0 : n }

// ---------------------------------------------------------------- 移动
function validateMovement(game, side, plans) {
	const scenario = scenarioOf(game)
	const errors = []
	const active = Object.values(game.ships).filter((s) => s.side === side && !s.sunk && s.position)
	const submitted = Object.keys(plans)
	for (const ship of active) {
		if (submitted.indexOf(ship.id) < 0) { errors.push(ship.id + ": 缺少移动计划"); continue }
		let plan = plans[ship.id]
		if (plan === undefined || plan === null || plan === "") plan = "0"
		let commands, cost
		try {
			commands = core.movementCommands(plan)
			core.validateCommands(commands)
			cost = core.movementCost(plan)
		} catch (e) { errors.push(ship.id + ": " + e.message); continue }
		const [minSpeed, maxSpeed] = core.legalSpeedRange(ship, game.turn)
		if (cost < minSpeed || cost > maxSpeed) errors.push(ship.id + ": 航速 " + cost + " 超出合法区间 " + minSpeed + "-" + maxSpeed)
		// 想定约束：邻接 / 警戒直行 / 提速上限
		for (const constraint of core.kinds(scenario, "movement_constraint")) {
			if (constraint.constraint !== "stay_adjacent") continue
			const subjects = constraint.subjects || {}, anchors = constraint.anchors || {}
			if (subjects.sides.indexOf(side) < 0 || subjects.ship_types.indexOf(ship.type) < 0) continue
			const anchorPositions = Object.values(game.ships).filter((o) =>
				o.id !== ship.id && o.side === ship.side && anchors.ship_types.indexOf(o.type) >= 0 && !o.sunk && o.position)
				.map((o) => o.position)
			if (!anchorPositions.length) continue
			const maxDistance = intOr0(constraint.max_distance) || 1
			const finalPosition = commands.length ? (trajectoryEnd(ship, commands) || ship.position) : ship.position
			if (!finalPosition || !anchorPositions.some((pos) => hex.distance(finalPosition, pos) <= maxDistance)) {
				errors.push(ship.id + ": 想定特例——必须与" + anchors.ship_types.join("/") + "保持" + maxDistance + "格内邻接")
			}
		}
		const alertRule = core.kinds(scenario, "alert_states")[0]
		if (alertRule && (alertRule.sides || []).indexOf(side) >= 0) {
			const alerted = game.scenarioState.alerted || []
			if (alerted.indexOf(ship.id) < 0) {
				if (commands.some((c) => c !== "advance")) errors.push(ship.id + ": 想定特例——未警戒单位只能保持原有方向直行")
				else if (cost !== ship.speed) errors.push(ship.id + ": 想定特例——未警戒单位只能以当前航速 " + ship.speed + " 直行")
			}
			if ((alertRule.speed_cap_ships || []).indexOf(ship.id) >= 0 && cost > ship.speed + 1) {
				errors.push(ship.id + ": 想定特例——每回合航速最多提升 1 MF（当前 " + ship.speed + "）")
			}
		}
	}
	for (const id of submitted) {
		if (!active.some((s) => s.id === id)) errors.push(id + ": 不可移动（不在场/已沉）")
	}
	return errors
}

function trajectoryEnd(ship, commands) {
	let position = ship.position, heading = ship.heading
	try {
		for (const command of commands) {
			if (command === "advance") position = hex.neighbor(position, heading, game.mapColumns, game.mapRows)
			else if (command === "turn_port_60") heading = heading === 1 ? 6 : heading - 1
			else if (command === "turn_starboard_60") heading = heading === 6 ? 1 : heading + 1
			else if (command === "turn_port_120") heading = ((heading - 3) % 6 + 6) % 6 + 1
			else if (command === "turn_starboard_120") heading = ((heading + 1) % 6) % 6 + 1
		}
	} catch (e) { return null }
	return position
}

function resolveMovement(game, plansBySide) {
	// 逐脉冲同时移动；同格碰撞 = 双方停车（简化：不掷碰撞损伤，记入日志差异）
	const paths = {}
	for (const side of Object.keys(plansBySide)) {
		for (const [shipId, plan] of Object.entries(plansBySide[side])) {
			const ship = game.ships[shipId]
			if (!ship || ship.sunk || !ship.position) continue
			let commands
			try { commands = core.movementCommands(plan) } catch (e) { continue }
			const result = { path: [], heading: ship.heading }
			let position = ship.position, heading = ship.heading
			for (const command of commands) {
				try {
					if (command === "advance") { position = hex.neighbor(position, heading, game.mapColumns, game.mapRows) }
					else if (command === "turn_port_60") { heading = heading === 1 ? 6 : heading - 1; continue }
					else if (command === "turn_starboard_60") { heading = heading === 6 ? 1 : heading + 1; continue }
					else if (command === "turn_port_120") heading = ((heading - 3) % 6 + 6) % 6 + 1
					else if (command === "turn_starboard_120") heading = ((heading + 1) % 6) % 6 + 1
					result.path.push({ position, heading })
				} catch (e) { break }
			}
			paths[shipId] = { ship, path: result.path, planUsed: String(plan ?? "0") }
		}
	}
	const maxImpulses = Math.max(1, ...Object.values(paths).map((p) => p.path.length))
	const stopped = {}
	for (let impulse = 0; impulse < maxImpulses; impulse++) {
		const destinations = {}
		for (const [shipId, item] of Object.entries(paths)) {
			if (stopped[shipId] || impulse >= item.path.length) continue
			destinations[shipId] = item.path[impulse].position
		}
		// 同格碰撞：全部停车
		const byHex = {}
		for (const [shipId, dest] of Object.entries(destinations)) {
			const key = hex.toLabel(dest)
			byHex[key] = byHex[key] || []
			byHex[key].push(shipId)
		}
		for (const [key, ids] of Object.entries(byHex)) {
			if (ids.length < 2) continue
			for (const id of ids) {
				stopped[id] = true
				log(game, "碰撞风险：" + game.ships[id].name + " 在 " + key + " 停车（同格会船）")
			}
		}
		for (const [shipId, dest] of Object.entries(destinations)) {
			if (stopped[shipId]) continue
			const ship = game.ships[shipId]
			ship.position = dest
			ship.positionLabel = hex.toLabel(dest)
			ship.heading = paths[shipId].path[impulse].heading
		}
	}
	for (const [shipId, item] of Object.entries(paths)) {
		item.ship.previousSpeed = core.movementCost(item.planUsed || "0")
	}
}

// ---------------------------------------------------------------- 鱼雷
function resolveTorpedoes(game, ordersBySide) {
	const scenario = scenarioOf(game)
	for (const side of Object.keys(ordersBySide)) {
		for (const order of ordersBySide[side] || []) {
			const ship = game.ships[order.ship_id]
			if (!ship || ship.sunk || !ship.position) continue
			const launcher = ship.launchers.find((l) => l.id === order.launcher_id)
			if (!launcher || launcher.destroyed || launcher.reloadTurns > 0 || launcher.loaded < order.count) continue
			launcher.loaded -= order.count
			ship.torpedoAmmo = ship.launchers.reduce((a, l) => a + l.loaded, 0)
			if (launcher.loaded === 0 && launcher.reloadsRemaining > 0) {
				launcher.reloadTurns = ship.type === "DD" || ship.type === "APD" ? 4 : 3
				launcher.reloadsRemaining -= 1
			}
			const expended = game.scenarioState.torpedoExpended || (game.scenarioState.torpedoExpended = {})
			expended[ship.side] = (expended[ship.side] || 0) + order.count
			const direction = order.launch_side === "port" ? -1 : 1
			const angleOffset = { A: -1, B: -1, X: 1, Y: 1 }[order.launch_angle] || 0
			let heading = ((ship.heading + direction * (order.launch_angle === "A" || order.launch_angle === "B" ? 1 : 2)) % 6 + 6) % 6 + 1
			heading = ((ship.heading - 1 + direction * (order.launch_angle === "A" || order.launch_angle === "B" ? 1 : 2)) % 6 + 6) % 6 + 1
			let position
			try { position = hex.neighbor(ship.position, heading, game.mapColumns, game.mapRows) } catch (e) { continue }
			const definition = D.rules.torpedoes[ship.torpedoType] || { settings: [{ speed: [5, 4, 4], range: 10 }] }
			game.trackSeq += 1
			game.torpedoTracks.push({
				id: "TT" + game.trackSeq, shipId: ship.id, side: ship.side,
				position, heading, remaining: definition.settings[0].range,
				speedCycle: definition.settings[0].speed, speedIndex: 0, salvo: order.count,
				type: ship.torpedoType,
			})
			log(game, ship.name + " " + launcher.id + " 发射 " + order.count + " 枚鱼雷（" + order.launch_side.toUpperCase() + order.launch_angle + "）")
		}
	}
	// 鱼雷轨迹推进与命中
	const tracks = game.torpedoTracks
	game.torpedoTracks = []
	for (const track of tracks) {
		for (let step = 0; step < track.speedCycle[track.speedIndex] && track.remaining > 0; step++) {
			let next
			try { next = hex.neighbor(track.position, track.heading, game.mapColumns, game.mapRows) } catch (e) { track.remaining = 0; break }
			track.position = next
			track.remaining -= 1
			const hitShip = Object.values(game.ships).find((s) =>
				s.position && !s.sunk && s.side !== track.side && s.position.q === next.q && s.position.r === next.r)
			if (hitShip) {
				const attacker = game.ships[track.shipId]
				const roll = core.roll2d6(game) + core.torpedoRollBonus(scenarioOf(game), track.side, game.turn) +
					core.rangeModifier("torpedo", Math.max(1, track.salvo ? 10 - track.remaining : 1), attacker.id.indexOf("IBS-U-IJN-") === 0) +
					core.targetSpeedModifier("torpedo", hitShip.speed)
				const aspect = "broadside"
				const hits = aspect === "broadside" ? (roll >= 13 ? 2 : roll >= 11 ? 1 : 0) : (roll >= 13 ? 1 : 0)
				markAlerted(game, hitShip.id, "被鱼雷命中")
				log(game, attacker.name + " 的鱼雷命中 " + hitShip.name + "（掷 " + roll + "，" + hits + " 命中）")
				for (let i = 0; i < Math.min(hits, track.salvo); i++) {
					const damageRoll = core.roll2d6(game) + intOr0((D.rules.torpedoes[track.type] || {}).damage_modifier)
					const effect = core.torpedoEffect(damageRoll, hitShip.band)
					applyEffect(game, hitShip, core.parseEffect(effect), attacker, "torpedo")
					log(game, "  ↳ " + hitShip.name + " 鱼雷损伤判定 " + damageRoll + "：" + effect)
				}
				track.remaining = 0
				break
			}
		}
		if (track.remaining > 0) game.torpedoTracks.push(track)
	}
}

function applyEffect(game, ship, effect, attacker, cause) {
	if (effect.sunk) damageHull(game, ship, ship.hull, cause, attacker)
	else if (effect.hull > 0) damageHull(game, ship, effect.hull, cause, attacker)
	if (effect.speed > 0) loseSpeed(ship, effect.speed)
	if (effect.fire) ship.fireMarkers += 1
}

function damageHull(game, ship, amount, cause, attacker) {
	if (amount <= 0 || ship.sunk) return
	const actual = Math.min(ship.hull, amount)
	ship.hull -= actual
	if (attacker && attacker.side !== ship.side) {
		game.score = game.score || { axis: 0, allies: 0 }
		game.score[attacker.side] += actual
	}
	if (ship.hull <= 0) {
		ship.sunk = true
		ship.position = null
		ship.positionLabel = null
		log(game, "💥 " + ship.name + " 被击沉" + (attacker ? "（" + attacker.name + "）" : ""))
		if (attacker && attacker.side !== ship.side) {
			game.score = game.score || { axis: 0, allies: 0 }
			game.score[attacker.side] += ship.vp
		}
	}
}

function loseSpeed(ship, amount) {
	for (let i = 0; i < amount; i++) {
		ship.speedCrossed = ship.speedCrossed.map((crossed, index) =>
			Math.min(crossed + 1, ship.speedDamageTrack[index].length))
	}
	ship.speed = Math.min(ship.speed, core.maxSpeedForTurn(ship, 1))
}

// ---------------------------------------------------------------- 炮击
function resolveGunnery(game, ordersBySide) {
	const scenario = scenarioOf(game)
	for (const side of ["axis", "allies"]) {
		for (const order of ordersBySide[side] || []) {
			const attacker = game.ships[order.ship_id]
			if (!attacker || attacker.sunk || !attacker.position) continue
			const target = game.ships[order.target_id]
			if (!target || target.sunk || !target.position) continue
			const restriction = core.turnRestrictionReason(scenario, side, game.turn, "gunnery")
			if (restriction) { log(game, attacker.name + " 炮击被想定特例阻止：" + restriction); continue }
			if (!canSee(game, attacker, target)) { log(game, attacker.name + " 无法看见 " + target.name + "，炮击取消"); continue }
			const aspect = bearingAspect(attacker, target)
			const usable = attacker.guns.filter((g) => !g.destroyed && !g.fired && g.kind === "primary" &&
				g.arcs.indexOf(aspect) >= 0 &&
				(!order.mount_ids || order.mount_ids.indexOf(g.id) >= 0))
			if (!usable.length) continue
			for (const g of usable) g.fired = true
			let firepower = usable.reduce((a, g) => a + g.firepower, 0)
			const caliber = Math.max.apply(null, usable.map((g) => g.caliber))
			const direction = target.position.q > attacker.position.q ? "east" : "other"
			const multiplier = core.firepowerMultiplier(scenario, side, attacker.type, caliber, direction)
			if (multiplier) firepower = multiplier.ceil ? Math.ceil(firepower * multiplier.factor) : Math.floor(firepower * multiplier.factor)
			const distance = hex.distance(attacker.position, target.position)
			const japanese = attacker.id.indexOf("IBS-U-IJN-") === 0
			let modifier = core.rangeModifier("gunnery", distance, japanese) +
				core.targetSpeedModifier("gunnery", target.speed) +
				core.gunnerySituationModifier(scenario, attacker.position, target.position)
			if (game.options.radar && attacker.radar && !attacker.radarDestroyed && distance > game.visibility[side === "axis" ? "Axis" : "Allies"]) {
				modifier += intOr0((D.rules.modifiers.optional || {}).star_shell_or_radar_illumination)
			}
			const raw = core.rollD66(game)
			const adjusted = core.d66Adjust(raw, modifier)
			let hits = core.hitCount(firepower, adjusted)
			attacker.fired = true
			markAlerted(game, target.id, "被炮击")
			log(game, attacker.name + " 炮击 " + target.name + "：火力 " + firepower + "，修正 " + modifier + "，掷 " + adjusted + "，命中 " + hits)
			if (hits > 0 && core.penetrationBlocked(scenario, side, game.turn, attacker.type)) {
				log(game, "  ↳ 想定特例：炮击无法穿透 " + target.name + " 的装甲（高爆弹）")
				hits = 0
			}
			for (let i = 0; i < hits; i++) {
				const resultRoll = core.rollD66(game)
				const result = core.gunneryResult(resultRoll)
				applyGunneryResult(game, attacker, target, result, distance, caliber)
				log(game, "  ↳ " + target.name + " 命中结果 " + resultRoll)
				// 炮击结果表 * 注：日/德 4.7"/5" 炮命中后额外检视火灾判定表
				if (attacker.id.indexOf("IBS-U-IJN-") === 0 || attacker.id.indexOf("IBS-U-KM-") === 0) {
					if (Math.abs(caliber - 4.7) < 0.05 || Math.abs(caliber - 5) < 0.05) extraFireDetermination(game, target, attacker, caliber)
				}
			}
		}
	}
}

function bearingAspect(attacker, target) {
	return hex.relativeAspect(attacker.position, attacker.heading, target.position)
}

function applyGunneryResult(game, attacker, target, result, distance, caliber) {
	if (result === "miss" || (result && result.kind === "miss")) return
	if (result === "special") { resolveSpecialDamage(game, target, attacker, distance, caliber); return }
	const items = Array.isArray(result) ? result : [result]
	for (const item of items) {
		if (item === "special") { resolveSpecialDamage(game, target, attacker, distance, caliber); continue }
		if (item === "radar") { target.radarDestroyed = true; log(game, "  ↳ " + target.name + " 雷达被毁"); continue }
		if (item === "fire_control") { target.mfcDestroyed = true; log(game, "  ↳ " + target.name + " 火控被毁"); continue }
		if (typeof item === "string" && item.indexOf("primary") === 0) {
			const position = item.endsWith("_bow") ? "bow" : item.endsWith("_mid") ? "midships" : item.endsWith("_stern") ? "stern" : null
			destroyGuns(game, target, "primary", 1, position)
			continue
		}
		if (item === "secondary") { destroyGuns(game, target, "secondary", 1, null); continue }
		if (typeof item === "object" && item !== null) {
			if (item.hull_by_ship_type) {
				const group = target.type === "BB" || target.type === "BC" ? "BB_BC" :
					["AV", "CA", "CL"].indexOf(target.type) >= 0 ? "AV_CA_CL" : "other"
				const key = item.hull_by_ship_type[group] !== undefined ? group : "other"
				damageHull(game, target, intOr0(item.hull_by_ship_type[key]), "gunnery", attacker)
				continue
			}
			let armour = target.armour.belt
			if (Object.keys(item).some((k) => k.indexOf("primary") === 0)) armour = target.armour.primary
			else if (item.secondary !== undefined) armour = target.armour.secondary
			if (item.armour_check && !penetrates(game, attacker, armour, distance, caliber)) continue
			if (item.hull) damageHull(game, target, intOr0(item.hull), "gunnery", attacker)
			if (item.speed_loss) loseSpeed(target, intOr0(item.speed_loss))
			if (item.fire_check) target.fireMarkers += 1
			if (item.secondary !== undefined) destroyGuns(game, target, "secondary", intOr0(item.secondary), null)
			for (const key of Object.keys(item)) {
				if (key.indexOf("primary") === 0 && key !== "primary" && key !== "primary_or") {
					const position = key.endsWith("_bow") ? "bow" : key.endsWith("_mid") ? "midships" : key.endsWith("_stern") ? "stern" : null
					destroyGuns(game, target, "primary", intOr0(item[key]), position)
				}
			}
		}
	}
}

function penetrates(game, attacker, armour, distance, caliber) {
	// 穿甲表注释：穿甲值必须大于装甲（平值不穿透）
	if (!armour || armour <= 0) return true
	const period = core.penetrationPeriod(gameMod_scenario(game))
	return core.penetration(core.nationOf(attacker.id), caliber || 5, distance, period) > armour
}
function gameMod_scenario(game) { return D.scenarios[game.scenario] }

function destroyGuns(game, ship, kind, count, position) {
	let destroyed = 0
	for (const g of ship.guns) {
		if (destroyed >= count) break
		if (g.kind === kind && !g.destroyed && (!position || g.position === position)) { g.destroyed = true; destroyed++ }
	}
	if (destroyed) log(game, "  ↳ " + ship.name + " 损失 " + destroyed + " 座" + (kind === "primary" ? "主炮" : "副炮"))
}

function extraFireDetermination(game, target, attacker, caliber) {
	let roll = core.roll2d6(game)
	if (!target.fired) roll = Math.min(12, roll + intOr0((D.rules.fireTable.modifiers || {}).ship_did_not_fire))
	const ignore = D.rules.fireTable.modifiers && (D.rules.fireTable.modifiers.ignore_results_if_ship_did_not_fire || [])
	if (!target.fired && ignore.indexOf(roll) >= 0) return
	const result = core.table2d6(D.rules.fireTable.results, roll)
	if (result.kind === "special_damage") resolveSpecialDamage(game, target, attacker, null, caliber)
	if (result.hull) damageHull(game, target, intOr0(result.hull), "fire", attacker)
	if (result.speed_loss) loseSpeed(target, intOr0(result.speed_loss))
	if (result.secondary) destroyGuns(game, target, "secondary", intOr0(result.secondary), null)
	if (result.primary) destroyGuns(game, target, "primary", intOr0(result.primary), null)
	if (result.extinguish) target.fireMarkers = Math.max(0, target.fireMarkers - 1)
}

function resolveSpecialDamage(game, target, attacker, distance, caliber) {
	const roll = core.rollD66(game)
	const result = core.specialDamageResult(roll, target.band)
	log(game, "  ↳ 特殊损伤判定 " + roll)
	if (result.radar) { target.radarDestroyed = true }
	let penetrated = true
	if (result.armour_check) penetrated = penetrates(game, attacker, target.armour.belt, distance, caliber)
	if (!penetrated) { log(game, "    装甲弹开，无效果"); return }
	if (result.effect) {
		const effect = core.parseEffect(result.effect)
		applyEffect(game, target, effect, attacker, "special")
	} else {
		if (result.sunk) damageHull(game, target, target.hull, "special", attacker)
		else if (result.hull) damageHull(game, target, intOr0(result.hull), "special", attacker)
		if (result.speed_loss) loseSpeed(target, intOr0(result.speed_loss))
		if (result.fire) target.fireMarkers += intOr0(result.fire)
		if (result.fire_control) target.mfcDestroyed = true
	}
}

// ---------------------------------------------------------------- 火灾与回合结束
function resolveFire(game) {
	for (const ship of Object.values(game.ships)) {
		for (let i = 0; i < ship.fireMarkers; i++) {
			let roll = core.roll2d6(game)
			if (!ship.fired) roll = Math.min(12, roll + intOr0((D.rules.fireTable || {}).modifiers?.ship_did_not_fire))
			const result = core.table2d6(D.rules.fireTable.results, roll)
			if (result.hull) damageHull(game, ship, intOr0(result.hull), "fire", null)
			if (result.speed_loss) loseSpeed(ship, intOr0(result.speed_loss))
			if (result.extinguish && (result.applies_to !== "US_only" || ship.id.indexOf("IBS-U-USN-") === 0)) {
				ship.fireMarkers = Math.max(0, ship.fireMarkers - 1)
			}
		}
	}
	for (const ship of Object.values(game.ships)) {
		ship.fired = false
		for (const l of ship.launchers) {
			if (l.reloadTurns > 0) {
				l.reloadTurns -= 1
				if (l.reloadTurns === 0 && l.reloadsRemaining >= 0) { l.loaded = l.torpedoes; ship.torpedoAmmo = ship.launchers.reduce((a, x) => a + x.loaded, 0) }
			}
		}
	}
	game.markers = game.markers.filter((m) => m.kind === "storm" || m.expires === undefined)
}

// ---------------------------------------------------------------- 胜利判定
function resolveVictory(game) {
	const scenario = scenarioOf(game)
	const kind = (scenario.victory || {}).kind
	const margin = (game.score && game.score.axis ? game.score.axis : 0) - (game.score && game.score.allies ? game.score.allies : 0)
	const sunkCount = (side, types) => Object.values(game.ships).filter((s) => s.sunk && s.side === side && types.indexOf(s.type) >= 0).length
	function standard(threshold, label) {
		if (Math.abs(margin) >= threshold) {
			const winner = margin > 0 ? "Axis" : "Allies"
			game.result = winner; game.victory = label + "：胜利点领先 " + Math.abs(margin) + " 分"
			return true
		}
		return false
	}
	let decided = false
	if (kind === "bc_kill_comparison") {
		const threshold = intOr0(scenario.victory.leader_margin) || 5
		const axisKills = sunkCount("allies", ["BC"]), alliesKills = sunkCount("axis", ["BC"])
		if (Math.abs(margin) >= threshold && axisKills !== alliesKills) {
			if (margin > 0 && axisKills > alliesKills) { game.result = "Axis"; game.victory = "胜利点领先 " + margin + " 分且击沉战巡 " + axisKills + " 比 " + alliesKills; decided = true }
			else if (margin < 0 && alliesKills > axisKills) { game.result = "Allies"; game.victory = "胜利点领先 " + (-margin) + " 分且击沉战巡 " + alliesKills + " 比 " + axisKills; decided = true }
		}
		if (!decided) { game.result = null; game.victory = "平局：未同时满足分差门槛与击沉战巡优势" }
	} else if (kind === "score_threshold_tiers") {
		const expended = (game.scenarioState.torpedoExpended || {}).axis || 0
		const axisScore = (game.score && game.score.axis ? game.score.axis : 0) + expended * 4
		const m = axisScore - (game.score && game.score.allies ? game.score.allies : 0)
		const caSunk = sunkCount("axis", ["CA"])
		if (caSunk >= 3 && (game.score.allies || 0) > axisScore) { game.result = "Allies"; game.victory = "盟军决定性胜利：击沉 " + caSunk + " 艘日军重巡且分数领先" }
		else if (m >= intOr0(scenario.victory.decisive_margin) || 50) { game.result = "Axis"; game.victory = "日军决定性胜利：领先 " + m + " 分" }
		else if (m >= intOr0(scenario.victory.tactical_margin) || 16) { game.result = "Axis"; game.victory = "日军战术胜利：领先 " + m + " 分" }
		else { game.result = "Allies"; game.victory = "盟军战术胜利：分数差 " + m }
		decided = true
	} else if (kind === "dd_kill_comparison") {
		const alliesKills = sunkCount("axis", ["DD", "APD"]), axisKills = sunkCount("allies", ["DD", "APD"])
		if (alliesKills >= 3 && axisKills <= 1) { game.result = "Allies"; game.victory = "盟军战役级胜利：击沉 " + alliesKills + " 艘日军DD，仅损失 " + axisKills + " 艘" }
		else if (axisKills >= 3 && alliesKills === 0) { game.result = "Axis"; game.victory = "日军战役级胜利：击沉 " + axisKills + " 艘盟军DD，己方DD无损" }
		else game.victory = "平局：未达成任何一方战役级胜利条件"
		decided = true
	} else if (kind === "margin_tiers") {
		const tactical = intOr0(scenario.victory.tactical_margin) || 3
		const campaign = intOr0(scenario.victory.campaign_margin) || 6
		if (Math.abs(margin) >= campaign) { game.result = margin > 0 ? "Axis" : "Allies"; game.victory = "战役级胜利：领先 " + Math.abs(margin) + " 分" }
		else if (Math.abs(margin) >= tactical) { game.result = margin > 0 ? "Axis" : "Allies"; game.victory = "战术胜利：领先 " + Math.abs(margin) + " 分" }
		else game.victory = "平局：分数差不足 " + tactical + " 分"
		decided = true
	} else if (kind === "vp_with_decisive_margin") {
		const decisive = intOr0(scenario.victory.decisive_margin) || 20
		if (Math.abs(margin) >= decisive) { game.result = margin > 0 ? "Axis" : "Allies"; game.victory = "决定性胜利：领先 " + Math.abs(margin) + " 分" }
		decided = false
	} else if (kind === "vp_with_bb_decisive_clause") {
		for (const side of ["axis", "allies"]) {
			const enemy = side === "axis" ? "allies" : "axis"
			const enemyBb = sunkCount(enemy, ["BB"]), ownBb = sunkCount(side, ["BB"])
			if (enemyBb >= 1 && enemyBb <= 2 && ownBb === 0) {
				game.result = side === "axis" ? "Axis" : "Allies"
				game.victory = "决定性胜利：敌方损失 " + enemyBb + " 艘战列舰而己方战列舰无损"
				decided = true; break
			}
		}
	}
	if (!decided) {
		if (!standard(4, "想定结束")) { game.result = null; game.victory = "平局：胜利点差小于 4" }
	}
	game.state = "game_over"
	game.active = "None"
	log(game, "", "** 终局：" + (game.result ? game.result + " 获胜 —— " : "") + game.victory + " **")
}

// ---------------------------------------------------------------- 回合推进
function advancePhase(game) {
	const scenario = scenarioOf(game)
	const submitted = {
		axis: game.submitted.Axis || {}, allies: game.submitted.Allies || {},
	}
	if (game.phase === "reinforcement") {
		if (game.reinforcement && !game.reinforcement.rolled) {
			const roll = core.rollDie(game)
			game.reinforcement.rolled = true
			game.reinforcement.available = game.reinforcement.succeedsOn.indexOf(roll) >= 0
			log(game, "增援检定 " + roll + "：" + (game.reinforcement.available ? "成功" : "失败"))
		}
		game.phase = "movement"
	} else if (game.phase === "movement") {
		resolveMovement(game, { axis: submitted.axis.plans || {}, allies: submitted.allies.plans || {} })
		game.phase = "torpedo"
	} else if (game.phase === "torpedo") {
		resolveTorpedoes(game, { axis: submitted.axis.torpedoes || [], allies: submitted.allies.torpedoes || [] })
		game.phase = "gunnery"
	} else if (game.phase === "gunnery") {
		resolveGunnery(game, { axis: submitted.axis.gunnery || [], allies: submitted.allies.gunnery || [] })
		resolveFire(game)
		if (game.turn >= game.maxTurns) { resolveVictory(game); return }
		game.turn += 1
		applyTurnStartRules(game)
		game.phase = "reinforcement"
	}
}

const IBSApi = {
	SIDE_VALUES, ROLE_VALUES, create, log, scenarioOf, liveShips, canSee, markAlerted,
	applyTurnStartRules, validateMovement, resolveMovement, resolveTorpedoes, resolveGunnery,
	resolveFire, resolveVictory, advancePhase, damageHull,
}
if (typeof module !== "undefined" && module.exports) module.exports = IBSApi
else (window.IBS = window.IBS || {})['game'] = IBSApi
})();
