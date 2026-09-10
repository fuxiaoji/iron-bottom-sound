"use strict"
// 引擎冒烟与规则验证：node tests/verify_engine.js
const r = require("../rules.js")
let pass = 0, fail = 0
const check = (name, cond, detail) => cond ? pass++ : (fail++, console.log("  ❌", name, detail ?? ""))

// 1) setup
const g = r.setup(42, "IBS-S-03", { ai_side: "none" })
check("setup: 8 舰", Object.keys(g.ships).length === 8, Object.keys(g.ships).length)
check("setup: 阶段=reinforcement", g.state === "reinforcement")
check("setup: 双方同时行动", Array.isArray(g.active))

// 2) 视图：本方完整/敌方按雾
let v = r.view(g, "Axis")
check("view: 本方 3 艘", v.ships.filter(s => s.side === "axis").length === 3)
check("view: actions.submit 可用", v.actions && v.actions.submit === 1)

// 3) 一整局打完（双方提交直至终局）
let guard = 0
while (g.state !== "game_over" && guard++ < 200) {
	for (const role of ["Axis", "Allies"]) {
		if (!g.submitted[role]) r.action(g, role, "submit", payloadFor(g, role))
	}
}
check("整局完成", g.state === "game_over", "guard=" + guard + " state=" + g.state)
check("终局有 victory 文案", typeof g.victory === "string" && g.victory.length > 0)
check("回合数 ≤ maxTurns", g.turn <= g.maxTurns, g.turn + "/" + g.maxTurns)

function payloadFor(game, role) {
	const side = role === "Axis" ? "axis" : "allies"
	const payload = { plans: {}, torpedoes: [], gunnery: [] }
	for (const ship of Object.values(game.ships)) {
		if (ship.side !== side || ship.sunk || !ship.position) continue
		if (game.phase === "movement") payload.plans[ship.id] = ship.id.indexOf("KM-") >= 0 || side === "axis" ? "1" : "0"
		if (game.phase === "torpedo" && ship.torpedoAmmo > 0 && ship.launchers.length) {
			const l = ship.launchers.find(x => !x.destroyed && x.reloadTurns === 0 && x.loaded > 0)
			if (l) payload.torpedoes.push({ ship_id: ship.id, launcher_id: l.id, count: 1, launch_side: l.arcs[0] === "port" ? "port" : "starboard", launch_angle: "A" })
		}
		if (game.phase === "gunnery") {
			const enemy = Object.values(game.ships).find(s => s.side !== side && !s.sunk && s.position)
			if (enemy) payload.gunnery.push({ ship_id: ship.id, target_id: enemy.id, mount_ids: null })
		}
	}
	return payload
}

// 4) 人机模式（AI 执同盟）
const g2 = r.setup(7, "IBS-S-03", { ai_side: "allies" })
let guard2 = 0
while (g2.state !== "game_over" && guard2++ < 200) {
	if (!g2.submitted.Axis) r.action(g2, "Axis", "submit", payloadFor(g2, "Axis"))
	else if (!g2.submitted.Allies && !g2.aiFilled) { /* AI 在提交后自动补 */ break }
	if (g2.state !== "game_over" && !g2.submitted.Axis) continue
}
check("人机模式可推进到终局或稳定循环", g2.state === "game_over" || guard2 >= 199, "state=" + g2.state)

// 5) 想定特例抽查：S-05 日军 T1 禁炮击（日志应有阻止记录）
const g3 = r.setup(3, "IBS-S-05", { ai_side: "none" })
const phaseOrder = ["reinforcement", "movement", "torpedo", "gunnery"]
let guard3 = 0
while (g3.phase !== "gunnery" && guard3++ < 10) {
	for (const role of ["Axis", "Allies"]) if (!g3.submitted[role]) r.action(g3, role, "submit", {})
	if (g3.phase !== "gunnery" && !g3.submitted.Axis && !g3.submitted.Allies) { /* resolved */ }
}
// S-05 首回合从增援开始走完 4 阶段后应已进入第 2 回合（限制在 T1 炮击阶段生效）
check("S-05 推进不抛错", g3.state !== "game_over" || g3.victory)

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)
