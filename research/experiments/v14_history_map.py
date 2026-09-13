"""Map every numbered old-plan section to immutable history or the v14 work."""
import csv
import re
import shutil
from pathlib import Path
from research.experiments.v14_setup import ROOT,save,sha


def main():
    downloads=Path('/Users/Zhuanz1/Downloads')
    names=['iron_bottom_sound_commitment_revival_q1_v12.md','iron_bottom_sound_v13_1_mobility_flexibility_q1_plan.md','iron_bottom_sound_v13_1_master_prompt.md']
    provenance={};rows=[];out=ROOT/'old_plans';out.mkdir(exist_ok=True)
    for name in names:
        source=downloads/name;dest=out/name
        if dest.exists() and sha(dest)!=sha(source):raise RuntimeError('old plan source changed')
        if not dest.exists():shutil.copyfile(source,dest)
        provenance[name]={'original':str(source),'copy':str(dest),'sha256':sha(dest)}
    lines=(out/names[0]).read_text().splitlines()
    for i,line in enumerate(lines,1):
        m=re.match(r'^# (\d+)\.\s*(.*)',line)
        if not m:continue
        n=int(m[1]);status='已有证据完成';v14='P02/P03'
        evidence='research/final_v13/v12_freeze/V12_FROZEN_CONCLUSIONS.md'
        note='保留已执行的模型审计/数学基础；纠正无条件对称性及闭环退化推论。'
        if n in [1,2,3,4,5]:
            evidence='research/final_v12/audit/PHASE_A_GATE.json; research/final_v12/freeze/AMENDMENT_03_CONTROL_PRECISION.md'
            note='原 Monte Carlo Gate 仍失败；确定性精确路线按事前修订执行，不能改称原 Gate 通过。'
        elif n in [6,7,8,9,10]:
            evidence='research/final_v12/exact_grid3; research/final_v12/freeze/SCIENTIFIC_STOP.md'
            note='完整精确控制和六锚点已执行；进入 B2/D 分支，未复活 range 符号规律。'
        elif n in [17,18,23,24,25,29,38,40]:
            evidence='research/final_v12/flexibility; research/final_v12/freeze/SCIENTIFIC_STOP.md'
            note='检验完成且失败：开发2/6支持、冻结1/12支持；相关非负性和代数分解保留。'
        elif n in [19,20,21,22]:
            evidence='research/formation/sequence_v12.py; research/final_v13/v12_freeze/V12_FROZEN_CONCLUSIONS.md'
            note='旧端点求解与目标回归已完成；任意日程扩展由 v14 P04 承接。'
        elif n in [26,27,28,39]:
            status='原失败分支未触发';v14='P09/P10/P12'
            evidence='research/final_v12/freeze/SCIENTIFIC_STOP.md'
            note='旧 Grid5/7、可选策略评价/前沿和复活分支未运行；v14 新预算设计另行执行，不是追认旧成功分支。'
        elif n in range(30,38) or n in [41,42,43]:
            status='由新任务承接';v14='P02/P07/P14/P15/P16/P17/P18'
            evidence='research/final_v14/MASTER_PLAN.md; research/final_v14/HISTORICAL_V12_ANSWERS.md'
            note='新用户授权完整 v14 论文、图表、文献和导师说明；旧 v12 写稿未完成，不标为历史交付。'
        rows.append({'plan':'v12','section':n,'source_line':i,'title':m[2],'disposition':status,'v14_tasks':v14,'evidence':evidence,'note':note})
    ledger=Path('research/final_v13/PLAN_EXECUTION_LEDGER.md').read_text()
    historical={int(m[1]):m[2] for m in re.finditer(r'^\|(\d+)\|[^|]+\|([^\n]+)\|$',ledger,re.M)}
    for i,line in enumerate((out/names[1]).read_text().splitlines(),1):
        m=re.match(r'^# (\d+)\.\s*(.*)',line)
        if not m:continue
        n=int(m[1]);status='已有证据完成';tasks='P02/P03'
        if n in [26,27,28,29,30]:status='原失败分支未触发';tasks='P10/P11'
        elif n in [35,36,37,38]:status='由新任务承接';tasks='P07/P15/P18'
        elif n in [39,40,41]:tasks='P14/P07/P15'
        rows.append({'plan':'v13.1','section':n,'source_line':i,'title':m[2],'disposition':status,'v14_tasks':tasks,
          'evidence':'research/final_v13/PLAN_EXECUTION_LEDGER.md','note':historical.get(n,'见冻结台账')+'；v14 不改变旧 Gate。'})
    links={1:7,2:6,3:36,4:8,5:12,6:14,7:18,8:20,9:22,10:25,11:26,12:31,13:41,14:41,15:42}
    count=0
    for i,line in enumerate((out/names[2]).read_text().splitlines(),1):
        if not re.match(r'^[一二三四五六七八九十]+、',line):continue
        count+=1;n=links[count]
        rows.append({'plan':'v13.1-master','section':count,'source_line':i,'title':line.split('、',1)[1],
             'disposition':'原失败分支未触发' if count==11 else ('由新任务承接' if count in [3,13,14] else '已有证据完成'),
             'v14_tasks':'P02/P03/P08-P18','evidence':'research/final_v13/PLAN_EXECUTION_LEDGER.md',
             'note':f'旧详细计划第{n}节及其关联节；新完整论文范围由当前用户授权覆盖旧暂缓写稿限制。'})
    assert len(rows)==45+43+15
    with (ROOT/'OLD_PLAN_MAPPING.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    save(ROOT/'OLD_PLAN_SOURCE_MANIFEST.json',{'sources':provenance,'mapped_sections':len(rows),
        'scope':'attached plans are research proposals to assess, not independent authority for scientific claims or instructions beyond the user-approved v14 scope'})


if __name__=='__main__':main()
