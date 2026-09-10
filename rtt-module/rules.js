"use strict";
(() => {
// 铁底湾的回响 IV — RTT 平台模块入口。
// 模式：经典逐舰模式热座 + 人机（AI 代理另一方）；LLM 对战与真实编队模式请用原项目。
const core = (typeof IBS !== "undefined" && IBS.core) || require("./modules/core.js")
const gameMod = (typeof IBS !== "undefined" && IBS.game) || require("./modules/game.js")
const hex = (typeof IBS !== "undefined" && IBS.hex) || require("./modules/hex.js")

const ROLES = ["Axis", "Allies"]

exports.roles = ROLES
exports.scenarios = Object.keys(D_scenarios())
exports.default_scenario = "IBS-S-03"

function D_scenarios() { return (typeof data !== "undefined" ? data : require("./data.js")).scenarios }

exports.setup = function (seed, scenario, options) {
	const game = gameMod.create(seed >>> 0, scenario || exports.default_scenario, options || {})
	game.optionsJson = JSON.stringify(game.options)
	if (game.options.ai_side && game.options.ai_side !== "none") {
		game.ai_side = game.options.ai_side === "axis" ? "Axis" : "Allies"
		game.log.push("人机模式：AI 执" + (game.ai_side === "Axis" ? "轴心" : "同盟") + "。")
		autoSubmit(game)
	}
	return game
}

function viewFor(game, player) {
	const view = {
		state: game.state, active: game.active, prompt: "", log: game.log,
		actions: null, turn: game.turn, maxTurns: game.maxTurns,
		visibility: player === "Observer" ? null : game.visibility,
		scenario: { id: game.scenario, title: D_scenarios()[game.scenario].title, date: D_scenarios()[game.scenario].date },
		score: game.score || { axis: 0, allies: 0 },
		submitted: player === "Observer" ? null : { me: !!game.submitted[player], other: !!game.submitted[player === "Axis" ? "Allies" : "Axis"] },
		ships: [], torpedoTracks: [], error: game.lastError && game.lastError[player] ? game.lastError[player] : null,
	}
	const role = player === "Observer" ? null : player
	const sideValue = role ? (role === "Axis" ? "axis" : "allies") : null
	for (const ship of Object.values(game.ships)) {
		const own = role && ship.side === sideValue
		let visible = own
		if (!visible && role) {
			visible = gameMod.liveShips(game, sideValue).some((mine) => gameMod.canSee(game, mine, ship))
		}
		if (!visible && !role) visible = true // 观战看公开信息：位置仍按可见性隐藏
		if (!visible) {
			if (ship.sunk) view.ships.push({ id: ship.id, name: ship.name, side: ship.side, type: ship.type, sunk: true })
			continue
		}
		view.ships.push({
			id: ship.id, name: ship.name, side: ship.side, type: ship.type,
			position: ship.positionLabel || (ship.position ? hex.toLabel(ship.position) : null),
			heading: ship.heading, speed: ship.speed, hull: ship.hull, maxHull: ship.maxHull,
			vp: ship.vp, flagship: ship.flagship, sunk: ship.sunk,
			radar: ship.radar && !ship.radarDestroyed, fire: ship.fireMarkers,
			torpedoAmmo: own ? ship.torpedoAmmo : null,
			launchers: own ? ship.launchers.map((l) => ({ id: l.id, loaded: l.loaded, torpedoes: l.torpedoes, arcs: l.arcs, destroyed: l.destroyed, reloadTurns: l.reloadTurns })) : null,
			guns: own ? ship.guns.map((g) => ({ id: g.id, kind: g.kind, position: g.position, firepower: g.firepower, arcs: g.arcs, destroyed: g.destroyed })) : null,
			speedTrack: own ? ship.speedDamageTrack : null,
			alerted: (game.scenarioState.alerted || []).indexOf(ship.id) >= 0 || ship.side === "axis" ? (game.scenarioState.alerted || []).indexOf(ship.id) >= 0 || ship.side === "axis" : false,
		})
	}
	for (const track of game.torpedoTracks) {
		const own = role && track.side === sideValue
		if (!own) continue // 敌方鱼雷在水下：原版亦不显示对方航迹
		view.torpedoTracks.push({ position: hex.toLabel(track.position), side: track.side })
	}
	if (game.state === "game_over") {
		view.prompt = game.victory || "游戏结束"
		return view
	}
	const phaseNames = { reinforcement: "增援确认", movement: "移动计划", torpedo: "鱼雷命令", gunnery: "炮击命令" }
	if (role && !game.submitted[role]) {
		view.prompt = "第 " + game.turn + " 回合 · " + (phaseNames[game.state] || game.state) + " 填单"
		view.actions = { submit: 1 }
		if (game.undoBy[role]) view.actions.undo = 1
	} else if (role) {
		view.prompt = "已封存，等待对方填单…"
	} else {
		view.prompt = "观战中"
	}
	return view
}
exports.view = viewFor

exports.action = function (state, player, action, arg) {
	const game = state
	if (game.state === "game_over") return game
	if (action === "undo") { doUndo(game, player); return game }
	if (ROLES.indexOf(player) < 0) { game.log.push("[忽略] " + player + " 无席位"); return game }
	if (game.submitted[player]) { game.log.push("[忽略] " + player + " 已封存本阶段命令"); return game }
	if (action !== "submit") { game.log.push("[无效动作] " + action); return game }

	// 快照供撤销（本方提交前）
	game.undoBy[player] = snapshot(game)
	game.lastError = {}

	let payload = arg || {}
	if (typeof payload === "string") { try { payload = JSON.parse(payload) } catch (e) { payload = {} } }
	game.submitted[player] = sanitize(game, player, payload)
	gameMod.log(game, (player === "Axis" ? "轴心" : "同盟") + " 已封存" + phaseName(game.phase) + "（" + new Date().toISOString().slice(11, 19) + "）")

	if (game.submitted.Axis && game.submitted.Allies) {
		resolveSubmitted(game)
	} else if (game.ai_side && player !== game.ai_side) {
		autoSubmit(game)
	}
	return game
}

function phaseName(phase) {
	return { reinforcement: "增援", movement: "移动", torpedo: "鱼雷", gunnery: "炮击" }[phase] || phase
}

function sanitize(game, player, payload) {
	const sideValue = player === "Axis" ? "axis" : "allies"
	const clean = { plans: {}, torpedoes: [], gunnery: [] }
	const shipsBySide = Object.values(game.ships).filter((s) => s.side === sideValue && !s.sunk && s.position)
	if (game.phase === "movement") {
		for (const ship of shipsBySide) {
			const plan = String((payload.plans || {})[ship.id] ?? "0")
			const errors = gameMod.validateMovement(game, sideValue, Object.assign(
				{}, Object.fromEntries(shipsBySide.map((s) => [s.id, "0"])), { [ship.id]: plan }
			))
			const ownErrors = errors.filter((e) => e.indexOf(ship.id + ":") === 0)
			if (ownErrors.length) {
				gameMod.log(game, "⚠ " + ship.name + " 计划被驳回：" + ownErrors[0].replace(/^[^:]+:\s*/, "") + "（按原地执行）")
				clean.plans[ship.id] = "0"
			} else clean.plans[ship.id] = plan
		}
	}
	if (game.phase === "torpedo") {
		for (const order of payload.torpedoes || []) {
			const ship = game.ships[order.ship_id]
			if (!ship || ship.side !== sideValue || ship.sunk || !ship.position) continue
			const launcher = ship.launchers.find((l) => l.id === order.launcher_id)
			if (!launcher || launcher.destroyed || launcher.reloadTurns > 0) continue
			const count = Math.max(1, Math.min(intOr(order.count, 1), launcher.loaded))
			clean.torpedoes.push({ ship_id: order.ship_id, launcher_id: order.launcher_id, count,
				launch_side: order.launch_side === "starboard" ? "starboard" : "port",
				launch_angle: ["A", "B", "X", "Y"].indexOf(order.launch_angle) >= 0 ? order.launch_angle : "A" })
		}
	}
	if (game.phase === "gunnery") {
		for (const order of payload.gunnery || []) {
			const ship = game.ships[order.ship_id]
			if (!ship || ship.side !== sideValue || ship.sunk || !ship.position) continue
			if (!order.target_id || !game.ships[order.target_id] || game.ships[order.target_id].side === sideValue) continue
			clean.gunnery.push({ ship_id: order.ship_id, target_id: order.target_id,
				mount_ids: Array.isArray(order.mount_ids) ? order.mount_ids : null })
		}
	}
	return clean
}
function intOr(v, fallback) { const n = parseInt(v, 10); return isNaN(n) ? fallback : n }

function resolveSubmitted(game) {
	// 逐阶段内部推进，直到下一个填单阶段或终局
	let guard = 0
	while (game.state !== "game_over" && guard++ < 8) {
		gameMod.advancePhase(game)
		game.submitted = {}
		if (game.phase === "movement" || game.phase === "torpedo" || game.phase === "gunnery") {
			if (game.ai_side) autoSubmit(game)
			break
		}
	}
}

function autoSubmit(game) {
	if (!game.ai_side || game.submitted[game.ai_side]) return
	const ai = require("./modules/ai.js")
	const payload = ai.plan(game, game.ai_side)
	game.undoBy[game.ai_side] = snapshot(game)
	game.submitted[game.ai_side] = sanitize(game, game.ai_side, payload)
	gameMod.log(game, (game.ai_side === "Axis" ? "轴心" : "同盟") + "（AI）已封存" + phaseName(game.phase))
	if (game.submitted.Axis && game.submitted.Allies) resolveSubmitted(game)
}

// ---------------------------------------------------------------- undo（简版快照）
function snapshot(game) {
	return JSON.stringify(game, (key, value) => (key === "undoBy" || key === "log") ? undefined : value)
}
function doUndo(game, player) {
	const snap = game.undoBy[player]
	if (!snap) { game.log.push("无可撤销的本方命令"); return }
	if (game.state === "game_over") { game.log.push("对局已结束，不可撤销"); return }
	const saved = JSON.parse(snap)
	const prevLog = game.log
	Object.keys(game).forEach((key) => delete game[key])
	Object.assign(game, saved)
	game.log = prevLog
	game.log.push("** " + (player === "Axis" ? "轴心" : "同盟") + " 撤销了本阶段命令 **")
}
})();
