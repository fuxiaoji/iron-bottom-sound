"use strict"
// 随机压测：随机合法动作直到终局（RTT 验收线：25 局 完成25/卡死0/崩溃0）
const r = require("../rules.js")
const GAMES = parseInt(process.env.GAMES || "25", 10)
let finished = 0, stuck = 0, crashed = 0
const scenarioPool = ["IBS-S-03", "IBS-S-01", "IBS-S-04", "IBS-S-05", "IBS-S-09", "IBS-S-13", "IBS-S-14"]
for (let n = 0; n < GAMES; n++) {
	try {
		const scenario = scenarioPool[n % scenarioPool.length]
		const g = r.setup(1000 + n, scenario, { ai_side: n % 2 ? "allies" : "none" })
		let steps = 0
		while (g.state !== "game_over" && steps++ < 3000) {
			const roles = ["Axis", "Allies"].filter((role) => !g.submitted[role])
			if (!roles.length) { stuck++; break }
			const role = roles[Math.floor(Math.random() * roles.length)]
			const v = r.view(g, role)
			if (!v.actions || !v.actions.submit) { stuck++; break }
			r.action(g, role, "submit", randomPayload(g, role))
		}
		if (g.state === "game_over") finished++
		else stuck++
	} catch (e) {
		crashed++
		console.log("  💥", scenarioPool[n % scenarioPool.length], e.message)
	}
}
console.log(`fuzz: ${finished}/${GAMES} finished, stuck=${stuck}, crashed=${crashed}`)
process.exit(crashed > 0 || finished < GAMES ? 1 : 0)

function randomPayload(game, role) {
	const side = role === "Axis" ? "axis" : "allies"
	const payload = { plans: {}, torpedoes: [], gunnery: [] }
	const mine = Object.values(game.ships).filter((s) => s.side === side && !s.sunk && s.position)
	for (const ship of mine) {
		if (game.phase === "movement") {
			const options = ["0", "1", "2", "1P1", "1S1", "PP1"]
			payload.plans[ship.id] = options[Math.floor(Math.random() * options.length)]
		}
		if (game.phase === "torpedo" && ship.torpedoAmmo > 0 && ship.launchers.length) {
			const l = ship.launchers.find((x) => !x.destroyed && x.reloadTurns === 0 && x.loaded > 0)
			if (l) payload.torpedoes.push({ ship_id: ship.id, launcher_id: l.id, count: 1,
				launch_side: l.arcs[0] === "port" ? "port" : "starboard",
				launch_angle: ["A", "B", "X", "Y"][Math.floor(Math.random() * 4)] })
		}
		if (game.phase === "gunnery") {
			const enemy = Object.values(game.ships).find((s) => s.side !== side && !s.sunk && s.position)
			if (enemy) payload.gunnery.push({ ship_id: ship.id, target_id: enemy.id, mount_ids: null })
		}
	}
	return payload
}
