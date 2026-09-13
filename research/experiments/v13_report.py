"""Assemble experiment-stage reports from audited final data; never write a paper."""
import json
from pathlib import Path
R=Path('research/final_v13')
def read(p):return json.loads((R/p).read_text())
def put(p,s):(R/p).write_text(s.strip()+'\n')

def main():
    gate=read('analysis/GATE_DATA.json');audit=read('analysis/NUMERICAL_AUDIT.json');amend=read('analysis/AMENDMENT_AUDIT.json')
    rows=read('analysis/confirmatory_interactions.json');dis=read('analysis/discovery_interactions.json')
    cap=[r for d in read('capability/all_results.json') for r in d['interactions']]
    m=gate['mechanism'];n=gate['n_positive'];nr=gate['n_reversal'];ns=gate['n_strong_reversal'];rho=m['primary_spearman']
    assert gate['pre_refinement_verdict']=='FAIL','This stop-branch report does not implement a success or refinement certification.'
    assert len(rows)==12 and len(cap)==6
    table='|几何|速度对|固定对手|M|数值区间宽度|判定|\n|---|---|---|---:|---:|---|\n'
    for r in rows:table+=f"|{r['geometry']}|{r['v_low']}/{r['v_high']}|{r['opponent_policy']}|{r['M']:+.8f}|{r['interval_width']:.2e}|{'正支持' if r['positive'] else '强反向' if r['strong_reversal'] else '反向' if r['reversal'] else '未分辨'}|\n"
    captable='|几何|固定对手 F 的 M|固定对手 C 的 M|\n|---|---:|---:|\n'
    for g in ['head_on','parallel','crossing']:
        cr=[r for r in cap if r['geometry']==g];captable+=f"|{g}|{cr[0]['M']:+.8f}|{cr[1]['M']:+.8f}|\n"
    geo='；'.join(f'{g} {v}/4' for g,v in gate['per_geometry_positive'].items())
    cls='；'.join(f"对手 {k}：{v['positive']}/6 正、{v['reversal']}/6 反向" for k,v in gate['per_opponent_class'].items())
    put('V13_Q1_GATE.md',f'''
# V13.1 项目科学 Gate：FAIL

2026-09-13。STOP EXPERIMENT EXPANSION = YES。主论文重写 = NO。

修订后完整验证：**{n}/12 正支持，{nr}/12 反向，其中 {ns} 个强反向，{gate['n_unresolved']} 个未分辨**。三几何支持数：{geo}。{cls}。

冻结规则触发：{'; '.join(gate['failure_reasons'])}。这是预先指定研究路线的停止判定，不是编辑决定、中科院分区认证或对所有可能模型的否定。

主机制 Spearman(M, DeltaTheta)={rho:.6f}；对手 F={m['per_opponent_class_spearman']['F']:.6f}，对手 C={m['per_opponent_class_spearman']['C']:.6f}。只有 {m['n_positive_DeltaTheta']}/6 个物理速度对提高 Theta，未达到冻结的至少 5/6 要求。不能把两者同时下降产生的正相关写成“速度改善追踪并提高适应价值”。

能力对照 T=4 的 {sum(r['LB']>1e-5 for r in cap)}/6 正结果单独保留；不加入主验证分母，也不覆盖主 Gate。其迎头/对手 F 的反例否定无条件的能力—适应互补性。

Grid-5、Grid-7、转向率、T=4/6/8 锚点和 rigid 扩展均**按失败分支未触发**；没有伪报稳健性通过。已冻结的基础验证与能力诊断做完，参数扩展停止。最新用户范围要求停在论文开写前，因此即使成功也不在本次写稿；现在更没有依据升级标题、摘要和主贡献。

原验证运行曾在 parallel/.75 独立镜像支付检查失败。原输出在 pre_boundary_amendment/，原设计文件及校验和不变。IMPLEMENTATION_AMENDMENT_01.md 披露随后发生的边界实现修复；RERUN_FREEZE.json 在修复后结果读取前固定代码。最终证据属于**冻结设计下、带已披露实现修订的重算**，不是完全未修改的预注册确认。

manuscript_q2_frozen/ 已保存 fallback；它包含已知证明与叙事缺陷，不能把“回到 fallback”解释为“现稿已达到二区或立即投稿”。当前既未重写，也未投稿。

证据：[完整 12 比较](analysis/confirmatory_interactions.csv)、[Gate 数据](analysis/GATE_DATA.json)、[数值审计](analysis/NUMERICAL_AUDIT.json)、[前后修订比较](analysis/AMENDMENT_AUDIT.json)、[20 问答](FINAL_V13_ADVISOR_REPORT.md)。
''')
    answers=[
      ('v12 solver 是否保持 regression pass？','30 项目标回归通过，包含原矩阵/DP/sequence-form、对称、交换、非负性、变速轨迹和本次边界反例。未重跑完整 v12 Monte Carlo；VALIDATED 只表示已测范围，不能涵盖所有浮点边界。'),
      ('是否使用 old pose cache？','没有。主值来自完整历史支付矩阵、完整 DP/sequence-form；只缓存完整配置对应矩阵，旧 pose-only 科学缓存仍禁用。'),
      ('是否真正固定 opponent conditions？','是。每个高低速对都固定对手速度 1.0、策略类 F 或 C、双方 range=1、几何、T=6、LF、支付与信息规律。主变量是 forced operating speed；新增 T=4 另作真正嵌套的能力对照。'),
      ('discovery 的 F 是否随速度上升？',f"未得到一般单调上升。24 个探索性相邻速度/策略端点中 {sum(r['positive'] for r in dis)} 正、{sum(r['reversal'] for r in dis)} 反向。全 15 个参数单元的两条 F 曲线保留于 Fig C；不从非负性推出单调性。"),
      ('player-swap 是否成立？',f"修复后全部 27 个主参数单元及其独立镜像通过；最大支付镜像差 {max(audit[p]['max_payoff_mirror_error'] for p in ['discovery','confirmatory']):.3e}，最大价值镜像差 {max(audit[p]['max_value_mirror_error'] for p in ['discovery','confirmatory']):.3e}，主 interaction 镜像差 {gate['max_mirror_interaction_error']:.3e}。原失败没有隐藏。"),
      ('held-out 12 comparisons 有多少 M>0？',f'{n}/12，{nr}/12 反向，{ns} 个强反向，{gate["n_unresolved"]} 个未分辨。这里按冻结数值判据计数，不是 iid 总体成功率。'),
      ('三种 geometry 是否都有支持？',geo+'。有局部正点也不能替代完整通过门槛。'),
      ('Grid-3 / Grid-5 是否同方向？','未检验 Grid-5。基础科学 Gate 已失败，按计划未触发细化；不能宣称同向。'),
      ('Grid-7 anchors 是否稳定？','未触发，不能宣称稳定。'),
      ('turn-rate 是否支持 mobility 而非仅 speed？','未触发转向率扩展。现有固定速度主结果不被改名为一般 mobility capability 结果。'),
      ('favorable-set drift 是否稳定可测？','冻结域内所有探针的 alpha=.9/.8 超水平集合均有定义，可重复计算；但有零漂移、负原始 correction 和域外实际状态。可计算不等于域选择稳健，更不等于均衡路径机制已获验证。'),
      ('Theta 是否解释 M？',f"所设想的方向链不支持：提高 Theta 的物理对数 {m['n_positive_DeltaTheta']}/6，pooled rho={rho:.4f}。报告了按几何/策略类散点和固定效应回归，但没有因果中介识别。"),
      ('T=4/6/8 是否稳定？','未触发同模型 horizon 锚点。独立 T=4 的变速能力诊断不等价于 T=6 固定速度结果的 horizon 稳健性。'),
      ('LF / rigid 是否稳定？','未触发 rigid 六锚点，不作跨编队稳健性结论。'),
      ('是否有 multiple strong reversals？',f'是，{ns} 个主端点满足冻结的 M 上界 < −0.1，并满足效应远大于数值区间的要求。'),
      ('Q1-STRONG / CONDITIONAL / FAIL？','FAIL。失败来自科学端点与机制，不能以图表数量、残差小或额外诊断的正结果覆盖。'),
      ('是否允许重写主论文？','不允许。本次范围到开写前；没有改主标题、摘要、贡献列表或主论文叙事。'),
      ('是否值得按中科院一区选刊？','当前新主线证据不支持按一区成熟稿定位。现行具体刊物中科院分区未登录核验；不以 JCR Q1 替换用户口径，不作分区或录用保证。'),
      ('失败后是否切回 Q2 fallback？','停止 v13 主线升级并保留 fallback 为后续工作基线。现存 fallback 并非可直接投稿稿件，仍有已记录的理论/证据缺陷。本次不改稿、不投稿。'),
      ('是否 STOP EXPERIMENT EXPANSION？','是。完成冻结设计全部基础计算、能力对照与报告后，停止网格/参数扩展；不追加参数寻找正结果。')]
    qs='\n\n'.join(f'### {i}. {q}\n\n{a}' for i,(q,a) in enumerate(answers,1))
    put('FINAL_V13_ADVISOR_REPORT.md',f'''
# V13.1 最终实验导师报告 — DRAFT，未开始论文写作

2026-09-13。已完成两份 v13.1 文件在当前停止分支下适用的实验、验证、理论草稿、文献定位、DRAFT 图和复现交付。**项目 Gate = FAIL；主验证 {n}/12 正、{nr}/12 反向、{ns} 个强反向。** 后续细网格等为条件任务，因失败未触发；不是已运行或通过。任务状态详见 PLAN_EXECUTION_LEDGER.md。

## 研究对象与有效比较

主实验比较同一焦点玩家在固定对手策略类 kappa 下的 F(v)=V(F,kappa;v)-V(C,kappa;v)，再作高低速差 M。对手速度固定 1.0，双方 range 固定 1，三几何，T=6，三档转向，LF 三舰。发现集 15 个物理参数单元、验证集 12 个，各自独立计算交换镜像；每单元完整四价值，共 {audit['all_main_values']['count']} 个主实验价值。FF 完整 backward induction，CC 完整矩阵 LP，FC/CF 完整 perfect-recall sequence form 和双方完整 realization best response；没有 receding DO 近似替代。精确指有限离散模型的浮点数值精度，不指连续博弈或符号精确证明。

当前主参数是**固定运行速度**。对手策略类没有在高低速差中偷偷改变，也没有用 V_CC−V_FF 的旧 bilateral sign 替代。H2 的一致定义恰为同一个 factorial 恒等式，不额外增加证据数。

## 验证集完整结果

外层速度对 .75/1.25，内层 .90/1.10；三几何 × 两对 × 对手 F/C = 12 个端点。两策略端点共享物理博弈，镜像不计独立样本。正支持要求 M_LB>1e-5 且 |M|>100×数值区间宽度；强反向另要求 M_UB<−0.1。区间不是抽样置信区间，完整 LB/UB 在 CSV。

{table}

最大主 interaction 数值区间宽度 {gate['max_interaction_interval_width']:.3e}；最小 |M|={gate['min_abs_interaction']:.6g}。小残差不能单独认证支付实现；本次先有实际支付镜像失败，再修复和全面重算。

## 实现修订与前后审计

原 parallel/.75 矩阵 9/531441 项镜像不符，最大差 2.4998096869；不是 LP 残差问题。非零近接触距离把坐标浮点误差放大到 ±150° 边界两侧。v13-only 支付模块统一将距固定射界边界不超过 1e-8 度的角归到边界；标量/向量同时修改，并保留能使旧实现失败的测试。没有对称化矩阵或平均价值。

所有初次输出和当时代码在 pre_boundary_amendment/；原设计未改。此次属于事后发现实现错误、披露修订后按原设计重算。对所有可用旧结果逐项比较：{amend['payoff_matrices_compared']} 个矩阵中 {amend['changed_matrices']} 个有超过 1e-8 的支付改变；最大价值改变 {amend['max_value_change']:.8g}，最大单项支付改变 {amend['max_payoff_change']:.8g}；主 Theta 汇总最大改变 {amend['max_Theta_change']:.3e}。原来未算的 parallel 其他验证速度没有补造旧值。详见两份 AMENDMENT_*_COMPARISON.csv。

v12 冻结结果和 fallback 的原始校验通过，历史失败标签不变。本次发现也提醒：冻结文件内 SOLVER_CORE=VALIDATED 是当时已测试范围内的结论，不代表旧支付函数所有边界均正确。没有为重解释 v12 重跑其完整审计。

## 机制与真正能力对照

27 个机制参数单元，每单元 32 个配对随机转向探针、每探针 6 epochs、两种 alpha；保留 {sum(audit['mechanism'][p]['epoch_alpha_rows'] for p in ['discovery','confirmatory'])} 条 epoch/alpha 记录。Theta 使用明确修正后的 R_plus/(R_plus+D+1e-9)，原始负 R_raw 全部保留。相同探针序列跨速度共享；这些是冻结的运动学探针，不是均衡策略路径。

验证集提高 Theta 的物理对数 {m['n_positive_DeltaTheta']}/6；rho(M,DeltaTheta)={rho:.6f}。geometry/class/contrast 固定效应回归的 DeltaTheta 系数={m['regression']['coefficients']['DeltaTheta']:.6f}，R²={m['regression']['R_squared']:.6f}，设计秩 {m['regression']['rank']}/{m['regression']['n_columns']}。这些是固定设计描述量，没有总体 p 值或因果中介结论。alpha=.8、centroid、Hausdorff、原始 ratio 和 signed correction 的敏感性均在 confirmatory_mechanism.json 中，不用其中某个较好相关替换主指标。

验证探针实际状态域外比例范围 {audit['mechanism']['confirmatory']['min_outside_domain_fraction']:.2%}–{audit['mechanism']['confirmatory']['max_outside_domain_fraction']:.2%}；两 alpha 的负 correction 比例范围 {audit['mechanism']['confirmatory']['min_negative_correction_fraction']:.2%}–{audit['mechanism']['confirmatory']['max_negative_correction_fraction']:.2%}。所有集合有定义，但域覆盖、投影距离和零漂移仍限制机制解释。mechanism_summary.csv 提供探针中位数、四分位数及各类标记比例；四分位数是探针分布，不是均衡价值误差条。

独立能力诊断固定共同初始历史，低菜单 {{.75,1.0}} 嵌入高菜单 {{.75,1.0,1.3}}，每回合可选绝对速度，T=4、三档转向。共同子矩阵差 {audit['capability']['max_nested_payoff_error']:.1e}，镜像检验通过；{audit['capability']['positive']}/6 正、{audit['capability']['reversal']}/6 反向。这个对照说明 forced-speed 与 capability 必须分开，但它不足以建立一般互补定律或替换主 Gate。

{captable}

## 理论与投稿边界

THEOREM_SCRATCHPAD.md 给出策略集合单调性的完整有限 minimax 论证、bilateral decomposition 与 H2 代数恒等式。新增 reduced quadratic tracking theorem 在固定外生扰动分布、球形可选修正、平方损失和 reset epochs 下，以投影公式和 Jensen 证明 increasing differences；同时给出真正嵌套能力却使 adaptation value 从 .5 降到 0 的反例。没有用“假设 increasing returns”循环证明，也没有宣称完整 LF 模型满足定理条件或证明新颖性。

公开原始文献定位见 LITERATURE_NOTES.md。GitHub 高星 K-Dense 的科研批判、审稿、可视化和科学写作技能用于本次实验审计；本地检查不等于独立同行评审，更不等于一区质量认证。当前主线未获支持，fallback 也仍需已记录的实质修订。中科院口径保留，具体期刊当期分区未核实。

## 计划指定的 20 个回答

{qs}

## 交付与复现

figures/ 中有 A–H 共 8 组 DRAFT 图，PNG 和 vector PDF，附原始数据路径与 hash、描述文本和视觉核验记录。完整数据、代码、协议、失败归档和审计均在本目录。仓库根目录运行 `.venv/bin/python reproduce_v13.py` 核验最终文件；`analyze` 仅重算冻结统计与审计，不启动新实验。REPRODUCIBILITY.md 记录原计算命令、软件版本和有限模型范围。未创建或改写主论文，未投稿，未对外发送消息。
''')
    put('ITERATION_03.md',f'''
# V13.1 EXPERIMENT ITERATION 03 — final amended evidence and stop

1. Phase: complete amended discovery, held-out confirmation, capability diagnostic, evidence audit and DRAFT figures.
2. Scientific question: whether own speed increases own adaptation value with opponent conditions fixed.
3. Pre-specified hypothesis: M^F>0 and M^C>0 plus improved tracking in the frozen physical contrasts.
4. Focal player: Blue, independently exchanged Red mirrors retained as validity checks.
5. Opponent conditions held fixed: speed 1, class separately F/C, range 1, geometry, T=6, LF and payoff.
6. Mobility variable changed: forced speed primary; distinct nested selectable-speed menu T=4 diagnostic.
7. Policy variable changed: own C to F inside each fixed-opponent factorial.
8. Exact/approximate solver: complete finite matrix/DP/sequence-form to recorded floating-point precision.
9. Regression tests: 30 passing; all final complete mirrors, nonnegativity, nested payoff consistency and frozen hashes verified.
10. Results: discovery 15 focal +15 mirrors; confirmation 12 focal +12 mirrors, {n}/12 positive interactions. Capability {audit['capability']['positive']}/6 positive, kept separate.
11. Reversals: {nr} primary reversals, including {ns} strong reversals; capability head-on/opponent F reverses. All retained.
12. Mechanism metrics: {m['n_positive_DeltaTheta']}/6 positive DeltaTheta; pooled rho={rho:.6f}; primary directional chain unsupported; alternate metrics remain sensitivities.
13. Discovery or confirmatory: frozen design with disclosed post-freeze implementation amendment, not untouched preregistration. Original outputs preserved and compared.
14. Claim implication: no general speed/capability-adaptation complementarity claim; reduced theorem and counterexample remain bounded results.
15. Q1 Gate implication: FAIL. No Grid-5/7, turn-rate, horizon or rigid expansion; no CAS Q1 certification.
16. Next allowed action: archive and deliver completed experimental packet; STOP EXPERIMENT EXPANSION and stop before manuscript writing.
''')
    print('Generated final FAIL-branch experiment reports from audited data.')
if __name__=='__main__':main()
