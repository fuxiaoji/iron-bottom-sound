"use strict";
(() => {
// 六边形坐标（flat-top odd-q 偏移，列标签为重复字母制：A..Z, AA..ZZ(26..51), …）
// 与 Python 引擎 models.HexCoord / column codec 逐位对齐；勿手改算法。
// data.js 在浏览器是全局（script 顺序加载）；Node 测试环境退化为 require。
/* global data */
const D = (typeof data !== "undefined" && data) || require("../data.js")

const MAX_COLUMNS = (D.hex && D.hex.MAX_COLUMNS) || 128
const MAX_ROWS = (D.hex && D.hex.MAX_ROWS) || 128
const DIRECTIONS = (D.hex && D.hex.direction_delta) || { "1": [1, -1], "2": [1, 0], "3": [0, 1], "4": [-1, 1], "5": [-1, 0], "6": [0, -1] }

function letterToIndex(ch) { return ch.charCodeAt(0) - 65 } // A=0

function columnToIndex(letters) {
	if (!/^[A-Z]+$/.test(letters)) throw new Error("Invalid map column " + letters)
	const set = new Set(letters.split(""))
	if (set.size !== 1) throw new Error("Invalid map column " + letters + "; expected repeated letters like A-Z, AA-TT")
	const ch = letters[0]
	const count = letters.length
	return letterToIndex(ch) + 26 * (count - 1) // A=0…Z=25, AA=26, TT=45, QQQ=72 …
}

function indexToColumn(index) {
	if (index < 0 || index >= MAX_COLUMNS) throw new Error("column out of range: " + index)
	if (index < 26) return String.fromCharCode(65 + index)
	const count = Math.floor(index / 26) + 1
	const ch = String.fromCharCode(65 + (index % 26))
	return ch.repeat(count)
}

function fromLabel(label) {
	const m = /^([A-Za-z]+)(\d{1,3})$/.exec(String(label).trim())
	if (!m) throw new Error("Invalid hex label " + label)
	const q = columnToIndex(m[1].toUpperCase())
	const displayRow = parseInt(m[2], 10) - 1
	const r = displayRow - (q - (q & 1)) / 2
	return { q, r }
}

function toLabel(coord) {
	const displayRow = coord.r + (coord.q - (coord.q & 1)) / 2
	return indexToColumn(coord.q) + (displayRow + 1)
}

function neighbor(coord, heading, columns, rows) {
	const d = DIRECTIONS[String(heading)]
	if (!d) throw new Error("Invalid heading " + heading)
	const q = coord.q + d[0]
	const r = coord.r + d[1]
	if (q < 0 || q >= (columns || MAX_COLUMNS) || r < -( (rows || MAX_ROWS)) || r > (rows || MAX_ROWS)) {
		throw new Error("neighbor out of map")
	}
	return { q, r }
}

function distance(a, b) {
	const ax = a.q, az = a.r, ay = -ax - az
	const bx = b.q, bz = b.r, by = -bx - bz
	return Math.max(Math.abs(ax - bx), Math.abs(ay - by), Math.abs(az - bz))
}

// 方位 = 与格中心连线最近的六方向（屏幕空间角度，flat-top odd-q）。
// 与 Python engine._bearing_between 同一算法，保证射界/纵队判定一致。
function bearingBetween(origin, target) {
	const dq = target.q - origin.q
	const dr = target.r - origin.r
	const dx = dq * 1.5
	const dy = (dr + dq / 2.0) * Math.sqrt(3.0)
	const angle = Math.atan2(dy, dx) * 180 / Math.PI
	let best = 1, bestDiff = 999
	for (let heading = 1; heading <= 6; heading++) {
		const headingAngle = (330 + (heading - 1) * 60) % 360
		let diff = ((headingAngle - angle + 180) % 360 + 360) % 360 - 180
		diff = Math.abs(diff)
		if (diff < bestDiff) { bestDiff = diff; best = heading }
	}
	return best
}

// 目标相对舰首的射界：bow/starboard/stern/port
function relativeAspect(origin, heading, target) {
	const bearing = bearingBetween(origin, target)
	const relative = ((bearing - heading) % 6 + 6) % 6
	return ["bow", "starboard", "starboard", "stern", "port", "port"][relative]
}

const IBSApi = { MAX_COLUMNS, MAX_ROWS, fromLabel, toLabel, neighbor, distance, bearingBetween, relativeAspect, columnToIndex, indexToColumn }
if (typeof module !== "undefined" && module.exports) module.exports = IBSApi
else (window.IBS = window.IBS || {})['hex'] = IBSApi
})();
