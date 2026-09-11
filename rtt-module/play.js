"use strict"
/* 铁底湾的回响 IV — RTT 前端。持久 DOM + on_update 增量刷新；
   可用性全部查 view.actions；渲染异常 try/catch 写入提示。 */

const hex = (window.IBS && IBS.hex) || null
let selectedShipId = null
let planDrafts = {}          // shipId -> plan string（本方移动草稿）
let torpedoDrafts = []       // {ship_id, launcher_id, count, launch_side, launch_angle}
let gunneryDrafts = []       // {ship_id, target_id}
let shipEls = {}             // shipId -> <g>
let builtFor = null

function on_init(scenario, options) {
	add_main_menu_item("清空本方草稿", () => { planDrafts = {}; torpedoDrafts = []; gunneryDrafts = []; on_update() })
}

function on_update() {
	try { render() } catch (error) { document.title = "渲染错误 " + error.message }
}

function render() {
	const mapEl = document.getElementById("map")
	const panel = document.getElementById("command_panel")
	if (!view) return
	buildMapIfNeeded(mapEl)
	updateMap(view)
	updatePanel(panel)
}

/* ---------- 地图 ---------- */
function mapSize() {
	const columns = (data.scenarios[view.scenario.id] || {}).map_columns || 46
	const rows = (data.scenarios[view.scenario.id] || {}).map_rows || 39
	return { columns, rows }
}
const HEX_W = 34, HEX_H = 30 // 显示尺寸（flat-top）

function hexCenter(q, displayRow) {
	const x = q * HEX_W * 0.75 + HEX_W / 2
	const y = displayRow * HEX_H + (q % 2 ? HEX_H / 2 : 0) + HEX_H / 2
	return { x, y }
}
function labelToPixel(label) {
	const c = hex.fromLabel(label)
	return hexCenter(c.q, c.r + (c.q - (c.q & 1)) / 2)
}

function buildMapIfNeeded(mapEl) {
	const size = mapSize()
	const key = view.scenario.id + ":" + size.columns + "x" + size.rows
	if (builtFor === key) return
	builtFor = key
	shipEls = {}
	const width = size.columns * HEX_W * 0.75 + HEX_W * 0.25
	const height = size.rows * HEX_H + HEX_H
	mapEl.style.width = width + "px"
	mapEl.style.height = height + "px"
	let grid = ""
	for (let q = 0; q < size.columns; q++) {
		const rows = size.rows
		for (let display = 0; display < rows; display++) {
			const r = display - (q - (q & 1)) / 2
			const { x, y } = hexCenter(q, display)
			const points = []
			for (let k = 0; k < 6; k++) {
				const angle = 60 * k
				points.push((x + HEX_W * 0.5 * Math.cos(angle * Math.PI / 180)).toFixed(1) + "," +
					(y + HEX_H * 0.5 * Math.sin(angle * Math.PI / 180)).toFixed(1))
			}
			grid += `<polygon points="${points.join(" ")}" class="hexcell"></polygon>`
		}
	}
	mapEl.innerHTML = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
		<g class="hexgrid">${grid}</g>
		<g id="tracklayer"></g>
		<g id="shiplayer"></g>
	</svg>`
}

function updateMap(viewObj) {
	const layer = document.getElementById("shiplayer")
	const trackLayer = document.getElementById("tracklayer")
	if (!layer) return
	const seen = {}
	for (const ship of viewObj.ships) {
		if (!ship.position) { if (shipEls[ship.id]) { shipEls[ship.id].remove(); delete shipEls[ship.id] } continue }
		seen[ship.id] = true
		let el = shipEls[ship.id]
		if (!el) { el = buildShipEl(ship); layer.appendChild(el); shipEls[ship.id] = el }
		const { x, y } = labelToPixel(ship.position)
		el.setAttribute("transform", `translate(${x},${y})`)
		el.setAttribute("class", "ship " + (ship.side === "axis" ? "axis" : "allies") + (ship.sunk ? " sunk" : "") + (selectedShipId === ship.id ? " selected" : ""))
		updateShipFace(el, ship)
	}
	for (const [id, el] of Object.entries(shipEls)) {
		if (!seen[id]) { el.remove(); delete shipEls[id] }
	}
	trackLayer.innerHTML = (viewObj.torpedoTracks || []).map((t) => {
		const { x, y } = labelToPixel(t.position)
		return `<circle cx="${x}" cy="${y}" r="3" class="torpedodot ${t.side}"></circle>`
	}).join("")
}

function counterAssetPath(ship) {
	const entry = (data.scenarios[view.scenario.id].ships || []).find((e) => e.id === ship.id)
	const asset = (entry && entry.asset) || counterAssetByName(ship)
	return asset ? "assets/counters/" + encodeURIComponent(asset) : null
}
function counterAssetByName(ship) {
	const nation = ship.side === "axis" ? (ship.id.indexOf("IBS-U-KM-") === 0 ? "德国" : "日本")
		: ship.id.indexOf("IBS-U-RAN-") === 0 ? "澳大利亚" : ship.id.indexOf("IBS-U-RN-") === 0 ? "英国" : "美国"
	return nation + "-" + ship.type + "-" + ship.name + ".png"
}
function buildShipEl(ship) {
	const g = document.createElementNS("http://www.w3.org/2000/svg", "g")
	const src = counterAssetPath(ship)
	if (src) {
		g.innerHTML = `<image href="" x="-16" y="-14" width="32" height="28" preserveAspectRatio="xMidYMid meet" class="counterimg"></image>
			<text class="name" y="20"></text><text class="hullpips" y="27"></text>`
	} else {
		g.innerHTML = `<polygon points="14,0 5,-8 -12,-8 -12,8 5,8" class="hull"></polygon>
			<text class="type" y="-9"></text><text class="name" y="2"></text>
			<text class="hullpips" y="12"></text>`
	}
	g.addEventListener("click", () => { selectedShipId = selectedShipId === ship.id ? null : ship.id; on_update() })
	return g
}

function updateShipFace(el, ship) {
	const img = el.querySelector(".counterimg")
	if (img && !img.getAttribute("href")) {
		const src = counterAssetPath(ship)
		if (src) img.setAttribute("href", src)
	}
	const name = el.querySelector(".name")
	if (name) name.textContent = ship.name.slice(0, 6)
	const pips = el.querySelector(".hullpips")
	if (pips) {
		const ratio = ship.maxHull ? ship.hull / ship.maxHull : 0
		pips.textContent = ship.sunk ? "✕" : "▮".repeat(Math.max(0, Math.round(ratio * 4)))
	}
	// 旗向标：舰首指向（航向 1..6 → 屏幕角 330+(h-1)*60 度）
	const angle = 330 + (ship.heading - 1) * 60
	el.querySelector(".counterimg, .hull").style.transform = ship.sunk ? "" : `rotate(${angle - 90}deg)`
	el.style.opacity = ship.sunk ? 0.35 : 1
}

/* ---------- 命令面板 ---------- */
function updatePanel(panel) {
	const myShips = (view.ships || []).filter((s) => s.side === (player === "Axis" ? "axis" : "allies"))
	const phaseNames = { reinforcement: "增援确认", movement: "移动计划", torpedo: "鱼雷命令", gunnery: "炮击命令" }
	let html = ""
	if (view.state === "game_over") {
		html += `<h2>终局</h2><p class="victory">${view.prompt}</p><p>轴心 ${view.score.axis} : ${view.score.allies} 盟军</p>`
	} else if (view.submitted && view.submitted.me) {
		html += `<h2>第 ${view.turn} 回合 · ${phaseNames[view.state] || view.state}</h2><p>已封存，等待对方…</p>`
	} else if (view.actions && view.actions.submit) {
		html += `<h2>第 ${view.turn} 回合 · ${phaseNames[view.state] || view.state}</h2>`
		if (view.error) html += `<p class="error">${view.error}</p>`
		if (view.state === "reinforcement") {
			html += `<p>本想定增援由引擎自动处理（掷骰/固定到达）。直接确认。</p>`
			html += `<button class="primary" onclick="submitPhase()">确认 ✓</button>`
		} else if (view.state === "movement") {
			html += `<p>点选舰船后用方向键编辑航迹；数字=前进格数。</p>`
			html += `<div class="plans">` + myShips.map((s) =>
				`<div class="plan-row${selectedShipId === s.id ? " sel" : ""}" data-ship="${s.id}">
					<b>${s.name}</b><span>${s.position} · 朝${s.heading} · 速${s.speed}</span>
					<code>${planDrafts[s.id] || "0"}</code></div>`).join("") + `</div>`
			if (selectedShipId) {
				html += `<div class="plan-builder">
					<button onclick="planAdd('1')">前进1</button><button onclick="planAdd('2')">前进2</button>
					<button onclick="planAdd('3')">前进3</button>
					<button onclick="planAdd('P')">左60°</button><button onclick="planAdd('S')">右60°</button>
					<button onclick="planAdd('PP')">左120°</button><button onclick="planAdd('SS')">右120°</button>
					<button onclick="planBack()">⌫</button></div>`
			}
			html += `<button class="primary" onclick="submitPhase()">封存移动计划 ✓</button>`
		} else if (view.state === "torpedo") {
			const ship = myShips.find((s) => s.id === selectedShipId && s.launchers && s.launchers.some((l) => l.loaded > 0 && !l.destroyed))
			html += `<div class="plans">` + myShips.map((s) =>
				`<div class="plan-row${selectedShipId === s.id ? " sel" : ""}" data-ship="${s.id}">
					<b>${s.name}</b><span>鱼雷 ${s.torpedoAmmo ?? "?"}</span></div>`).join("") + `</div>`
			if (ship) {
				const launcher = ship.launchers.find((l) => l.loaded > 0 && !l.destroyed && l.reloadTurns === 0)
				if (launcher) {
					const side = launcher.arcs[0] === "port" ? "port" : "starboard"
					html += `<p>${ship.name} · ${launcher.id}（${launcher.loaded} 具）</p><div class="plan-builder">`
					for (const angle of (side === "port" ? ["A", "B"] : ["X", "Y"])) {
						html += `<button onclick="torpedoAdd('${ship.id}','${launcher.id}','${side}','${angle}')">${side.toUpperCase()}${angle} ×2</button>`
					}
					html += `</div>`
				}
			} else html += `<p>点选一艘有鱼雷的舰。</p>`
			html += `<p class="draft">${torpedoDrafts.length ? torpedoDrafts.map((t) => t.ship_id + "×" + t.count).join("；") : ""}</p>`
			html += `<button class="primary" onclick="submitPhase()">封存鱼雷命令 ✓</button>`
		} else if (view.state === "gunnery") {
			const selected = myShips.find((s) => s.id === selectedShipId)
			const enemies = (view.ships || []).filter((s) => s.side !== (player === "Axis" ? "axis" : "allies") && s.position)
			html += `<div class="plans">` + myShips.map((s) =>
				`<div class="plan-row${selectedShipId === s.id ? " sel" : ""}" data-ship="${s.id}">
					<b>${s.name}</b><span>${gunneryDrafts.filter((g) => g.ship_id === s.id).map((g) => "→" + g.target_id).join(" ") || "未分配"}</span></div>`).join("") + `</div>`
			if (selected) {
				html += `<p>点选敌舰为目标（自动分配可射击主炮）：</p><div class="targets">` +
					enemies.map((e) => `<button onclick="gunneryAdd('${selected.id}','${e.id}')">${e.name}</button>`).join("") + `</div>`
			} else html += `<p>点选己方舰船。</p>`
			html += `<button class="primary" onclick="submitPhase()">开火 ✓</button>`
		}
		if (view.actions && view.actions.undo) html += `<button class="quiet" onclick="send_action('undo', null)">撤销本方上一步</button>`
	} else {
		html += `<h2>等待对方…</h2>`
	}
	panel.innerHTML = html
	panel.querySelectorAll(".plan-row[data-ship]").forEach((el) => {
		el.addEventListener("click", () => { selectedShipId = el.dataset.ship; on_update() })
	})
}

function planAdd(token) {
	if (!selectedShipId) return
	planDrafts[selectedShipId] = (planDrafts[selectedShipId] || "0") + token
	on_update()
}
function planBack() {
	if (!selectedShipId || !planDrafts[selectedShipId]) return
	planDrafts[selectedShipId] = planDrafts[selectedShipId].slice(0, -1)
	if (planDrafts[selectedShipId] === "") planDrafts[selectedShipId] = "0"
	on_update()
}
function torpedoAdd(shipId, launcherId, side, angle) {
	torpedoDrafts.push({ ship_id: shipId, launcher_id: launcherId, count: 2, launch_side: side, launch_angle: angle })
	on_update()
}
function gunneryAdd(shipId, targetId) {
	gunneryDrafts = gunneryDrafts.filter((g) => g.ship_id !== shipId)
	gunneryDrafts.push({ ship_id: shipId, target_id: targetId })
	on_update()
}
function submitPhase() {
	if (view.state === "movement") {
		const plans = {}
		for (const s of view.ships.filter((x) => x.side === (player === "Axis" ? "axis" : "allies") && x.position)) {
			plans[s.id] = planDrafts[s.id] || "0"
		}
		send_action("submit", { plans })
		planDrafts = {}
	} else if (view.state === "torpedo") {
		send_action("submit", { torpedoes: torpedoDrafts })
		torpedoDrafts = []
	} else {
		send_action("submit", { gunnery: gunneryDrafts })
		gunneryDrafts = []
	}
}

function on_log(text, i) {
	const div = document.createElement("div")
	div.textContent = text
	if (/^\*\*/i.test(text || "")) div.className = "log-head"
	if (/^💥/.test(text || "")) div.className = "log-sunk"
	if (/^⚠/.test(text || "")) div.className = "log-warn"
	return div
}
function on_prompt(text) { return text }
