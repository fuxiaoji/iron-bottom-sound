"use strict"
// 全想定运行验证：按平台契约对每个想定 setup → view → 打完一局
const r = require("../rules.js")

const ids = r.scenarios
console.log("模块声明的想定数:", ids.length)

let ok = 0, bad = 0
for (const id of ids) {
  let line = `  ${id.padEnd(14)}`
  try {
    const g = r.setup(7, id, { ai_side: "none" })
    const shipCount = Object.keys(g.ships).length
    const vAxis = r.view(g, "Axis")
    const vAllies = r.view(g, "Allies")
    const vObs = r.view(g, "Observer")
    if (!vAxis || !vAllies || !vObs) throw new Error("view 返回空")
    if (!Array.isArray(vAxis.ships)) throw new Error("view.ships 非数组")

    // 打完一局（双方提交直至终局）
    let guard = 0
    while (g.state !== "game_over" && guard++ < 400) {
      for (const role of ["Axis", "Allies"]) {
        if (!g.submitted[role]) r.action(g, role, "submit", null)
      }
    }
    const status = g.state === "game_over" ? "终局" : "未完(" + g.state + ")"
    console.log(`${line} 舰${String(shipCount).padStart(3)} 回合${String(g.turn).padStart(2)} ${status} 守卫${guard}`)
    if (g.state === "game_over") ok++; else bad++
  } catch (e) {
    console.log(`${line} ❌ 异常: ${e.message}`)
    bad++
  }
}
console.log(`\n可运行: ${ok}/${ids.length}，异常或未终局: ${bad}`)
