"use strict";
(() => {
// 简化战术 AI：朝最近可接敌目标直行，进入视距后分配主炮齐射，近距离发射鱼雷。
const hex = (typeof IBS !== "undefined" && IBS.hex) || require("./hex.js")
const core = (typeof IBS !== "undefined" && IBS.core) || require("./core.js")

function plan(game, role) {
	const sideValue = role === "Axis" ? "axis" : "allies"
	const enemySide = sideValue === "axis" ? "allies" : "axis"
	const myShips = Object.values(game.ships).filter((s) => s.side === sideValue && !s.sunk && s.position)
	const enemies = Object.values(game.ships).filter((s) => s.side === enemySide && !s.sunk && s.position)
	const payload = { plans: {}, torpedoes: [], gunnery: [] }
	if (!enemies.length) {
		for (const ship of myShips) payload.plans[ship.id] = "0"
		return payload
	}
	for (const ship of myShips) {
		const target = enemies.map((e) => ({ e, d: hex.distance(ship.position, e.position) }))
			.sort((a, b) => a.d - b.d)[0]
		if (!target) { payload.plans[ship.id] = "0"; continue }
		const plan = approachPlan(game, ship, target.e)
		payload.plans[ship.id] = plan
		// 鱼雷：距离 ≤4 且有装填鱼雷
		if (target.d <= 4 && ship.torpedoAmmo > 0) {
			for (const launcher of ship.launchers) {
				if (launcher.destroyed || launcher.reloadTurns > 0 || launcher.loaded <= 0) continue
				payload.torpedoes.push({ ship_id: ship.id, launcher_id: launcher.id,
					count: Math.min(2, launcher.loaded), launch_side: launcher.arcs[0] === "port" ? "port" : "starboard",
					launch_angle: "A" })
				break
			}
		}
		// 炮击：可见即打
		const vis = game.visibility[role]
		if (target.d <= vis) {
			payload.gunnery.push({ ship_id: ship.id, target_id: target.e.id, mount_ids: null })
		}
	}
	return payload
}

// 一次一步的追踪：选让距离最小的 60° 内航向直行 1-2 格（受合法速度域约束）
function approachPlan(game, ship, enemy) {
	const [minSpeed, maxSpeed] = core.legalSpeedRange(ship, game.turn)
	// 警戒/相邻约束等由 sanitize 兜底驳回为原地
	const candidates = []
	for (let speed = Math.max(minSpeed, 1); speed <= Math.min(maxSpeed, 3); speed++) {
		for (const turns of [[], ["turn_port_60"], ["turn_starboard_60"]]) {
			let position = ship.position, heading = ship.heading, ok = true
			const commands = []
			for (const t of turns) { commands.push(t); heading = t === "turn_port_60" ? (heading === 1 ? 6 : heading - 1) : (heading === 6 ? 1 : heading + 1) }
			for (let i = 0; i < speed; i++) {
				try { position = hex.neighbor(position, heading, game.mapColumns, game.mapRows) } catch (e) { ok = false; break }
				commands.push("advance")
			}
			if (!ok) continue
			if (commands.length && commands[0] !== "advance") continue
			if (commands.length > 1 && commands[0] !== "advance") continue
			// 转向后必须紧跟前进；末位 60 度转向合法
			const distance = hex.distance(position, enemy.position)
			candidates.push({ distance, plan: commandsToPlan(commands) })
		}
		const straight = []
		let p = ship.position
		for (let i = 0; i < speed; i++) {
			try { p = hex.neighbor(p, ship.heading, game.mapColumns, game.mapRows) } catch (e) { break }
			straight.push("advance")
		}
		if (straight.length) candidates.push({ distance: hex.distance(p, enemy.position), plan: String(speed) })
	}
	if (!candidates.length) return "0"
	candidates.sort((a, b) => a.distance - b.distance)
	return candidates[0].plan
}

function commandsToPlan(commands) {
	let plan = "", advances = 0
	for (const c of commands) {
		if (c === "advance") advances++
		else {
			if (advances) { plan += advances; advances = 0 }
			plan += c === "turn_port_60" ? "P" : c === "turn_starboard_60" ? "S" : c === "turn_port_120" ? "PP" : "SS"
		}
	}
	if (advances) plan += advances
	return plan || "0"
}

const IBSApi = { plan }
if (typeof module !== "undefined" && module.exports) module.exports = IBSApi
else (window.IBS = window.IBS || {})['ai'] = IBSApi
})();
