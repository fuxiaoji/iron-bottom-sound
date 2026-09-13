"""Data-linked scientific figures for v14; never impute missing experiments.

Use --foundations during computation and --all only after the final analysis.
Output PDF is vector except explicitly rasterized dense point clouds. PNG is
600 dpi. Source hashes, exact plotting data and captions accompany each panel.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from research.experiments.v14_setup import ROOT, save, sha
from research.formation.physical_v14 import make_game
from research.formation.commitment_v12 import initial_states, trajectory_batch
from research.formation.payoff_v13 import angle
from research.experiments.t1_exact_discrete_certification import fire_vec

OUT=Path('paper_v14/figures')
GEO=('head_on','parallel','crossing')
GNAME={'head_on':'Head-on','parallel':'Parallel','crossing':'Crossing'}
COLORS=('#0072B2','#D55E00','#009E73','#CC79A7')
MARKERS=('o','s','^','D')
STYLE={'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,
       'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,
       'legend.fontsize':7,'axes.spines.top':False,'axes.spines.right':False,
       'axes.linewidth':.6,'lines.linewidth':1.2,'lines.markersize':3.5,
       'pdf.fonttype':42,'ps.fonttype':42,'savefig.facecolor':'white'}


def rows(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))


def num(row,key):
    value=row.get(key,'')
    return float(value) if value not in ('','None','null',None) else np.nan


def panel(ax,label,title):
    ax.set_title(title,loc='left',pad=7)
    ax.text(-.15,1.07,label,transform=ax.transAxes,weight='bold',fontsize=10)


def publish(fig,name,caption,alt,sources,plotdata=None,scope='frozen design'):
    OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.png'),dpi=600,bbox_inches='tight')
    data=OUT/(name+'_data.json')
    if plotdata is not None:save(data,plotdata)
    manifest={'figure':name,'caption':caption,'alt_text':alt,'scope':scope,
       'source_sha256':{str(p):sha(p) for p in sources},'generator_sha256':sha(__file__),
       'exports':{ext:sha(OUT/(name+'.'+ext)) for ext in ['pdf','png']},
       'plotting_data':str(data) if plotdata is not None else None,
       'style':'general two-column-width scientific layout; not journal acceptance or template compliance',
       'uncertainty':'numerical intervals where shown; no population confidence intervals',
       'missing':'no missing scientific values are replaced by zero'}
    save(OUT/(name+'_manifest.json'),manifest)
    (OUT/(name+'_caption.txt')).write_text(caption+'\n\nAlt text: '+alt+'\n')
    plt.close(fig)


def model():
    c={'geometry':'head_on','speed':1.,'distance':16.,'T':6,'grid':3,'ablation':'none'}
    blue=np.array([[-60.,0.,60.,0.,-60.,60.]])
    red=np.zeros((1,6));g=make_game(c);b,r=initial_states(g)
    pb,hb=trajectory_batch(b,blue,g);pr,hr=trajectory_batch(r,red,g)
    fig=plt.figure(figsize=(6.85,5.7),layout='constrained')
    gs=fig.add_gridspec(2,2,height_ratios=[1.3,1]);ax=fig.add_subplot(gs[0,0])
    for pos,col,lab in [(pb[0],COLORS[0],'Blue'),(pr[0],COLORS[1],'Red')]:
        for ship in range(3):
            ax.plot(pos[:,ship,0],pos[:,ship,1],color=col,ls='-' if ship==0 else '--',
                    alpha=1 if ship==0 else .55,label=lab+' leader' if ship==0 else None)
        for epoch in (0,2,4,6):
            ax.scatter(pos[epoch,:,0],pos[epoch,:,1],c=col,s=14,marker='o' if lab=='Blue' else 's')
            ax.annotate(str(epoch),pos[epoch,0],xytext=(3,3),textcoords='offset points',fontsize=6)
    ax.set(xlabel='x (hex)',ylabel='y (hex)',aspect='equal');ax.legend(loc='upper right')
    panel(ax,'a','History-dependent formation')
    ax=fig.add_subplot(gs[0,1]);ax.axis('off')
    text=[('Directional field','relative range, bearing and aspect'),
          ('Trajectory payoff','endpoint trapezoid over executed motion'),
          ('History state','causal leader path and follower positions'),
          ('Budgeted decision','public calendar; private command blocks')]
    for i,(title,detail) in enumerate(text):
        y=.95-i*.235
        ax.text(.04,y,title,va='top',weight='bold')
        ax.text(.04,y-.065,detail,va='top',fontsize=7,wrap=True)
        if i<3:ax.annotate('',xy=(.48,y-.22),xytext=(.48,y-.12),arrowprops={'arrowstyle':'->','color':'.4'})
    panel(ax,'b','Model-to-decision chain')
    ax=fig.add_subplot(gs[1,:]);ax.set(xlim=(-.55,6.35),ylim=(-.95,3.2))
    for yy,label,S in [(2.5,'Own calendar: K = 2',(2,4)),(1.4,'Opponent F',(1,2,3,4,5)),(.3,'Opponent C',())]:
        boundaries=(0,*S,6)
        for t,e in zip(boundaries[:-1],boundaries[1:]):
            ax.add_patch(Rectangle((t,yy-.21),e-t,.42,facecolor='#DDE9F0',edgecolor='.35',lw=.6))
            if e-t>1:ax.text((t+e)/2,yy,'sealed block',ha='center',va='center',fontsize=6.5)
        for t in boundaries[:-1]:ax.plot(t,yy,'o',color='black',ms=4)
        ax.text(-.42,yy+.32,label,fontsize=7,weight='bold')
    ax.text(0,-.6,'Initial planning is free',fontsize=7)
    ax.text(2.5,-.6,'At updates: executed prefixes visible; future commands private',fontsize=7)
    ax.set_xticks(range(7));ax.set_yticks([]);ax.set_xlabel('Epoch boundary')
    for spine in ['left','top','right']:ax.spines[spine].set_visible(False)
    panel(ax,'c','Public times, sealed actions')
    caption=('Model and information structure. (a) A specified illustrative Grid-3 trajectory, '
       'with three vessels per side and snapshots at epochs 0, 2, 4 and 6; labels mark leaders. '
       'It is not an optimized policy or an equilibrium replay. (b) The model-to-decision chain. '
       '(c) Own calendar S={2,4}, compared with fixed opponent F and C update rights. '
       'Only initial planning is free. Dots identify decisions; unexecuted commands remain private.')
    publish(fig,'fig01_model',caption,'Formation paths and three calendar timelines showing the distinction between public executed history and sealed future actions.',
        [ROOT/'DESIGN.json',Path('research/formation/physical_v14.py'),Path('research/formation/commitment_v12.py')],
        {'config':c,'blue_turns_deg':blue.tolist(),'red_turns_deg':red.tolist(),
         'blue_positions':pb[0].tolist(),'red_positions':pr[0].tolist(),'calendar':[2,4]},'specified explanatory trajectory')


def foundation():
    source=ROOT/'foundations/calibration_test_rows.csv';data=[r for r in rows(source) if r['class']=='CA']
    c={'geometry':'head_on','speed':1.,'distance':16.,'T':4,'grid':3,'ablation':'none'}
    g=make_game(c);theta=np.linspace(-np.pi,np.pi,361);radius=np.linspace(4,24,81)
    tt,rr=np.meshgrid(theta,radius);field=fire_vec(g.kB,rr,angle(np.degrees(tt)),np.full(rr.shape,'broadside'))
    baseline=ROOT/'runs/head_on_v1_d16_T4_G3_none/blue_payoff.npy'
    terminal=ROOT/'runs/head_on_v1_d16_T4_G3_terminal/blue_payoff.npy'
    if not (baseline.exists() and terminal.exists()):return False
    fig=plt.figure(figsize=(6.85,6.0),layout='constrained');gs=fig.add_gridspec(2,2)
    ax=fig.add_subplot(gs[0,0],projection='polar');im=ax.pcolormesh(tt,rr,field,cmap='cividis',shading='auto',rasterized=True)
    ax.set_theta_zero_location('E');ax.set_rlabel_position(145);ax.set_ylim(0,24)
    ax.set_yticks([8,16,24]);ax.set_xticks(np.radians([0,90,180,270]))
    ax.set_title('a  Directional CA field',loc='left',pad=14)
    fig.colorbar(im,ax=ax,shrink=.75,label='Expected effect (proxy units)')
    ax=fig.add_subplot(gs[0,1]);truth=np.array([num(r,'archived_truth') for r in data]);pred=np.array([num(r,'prediction') for r in data])
    ax.scatter(truth,pred,s=4,alpha=.25,color=COLORS[0],rasterized=True)
    top=max(truth.max(),pred.max());ax.plot([0,top],[0,top],color='.25',ls='--',lw=.7)
    ax.set(xlabel='Archived rule-grid effect',ylabel='Frozen kernel prediction');panel(ax,'b','Calibration replay')
    ax.text(.04,.95,'CA test rows: 1,523\nSpearman ρ = 0.99084\nNMAE = 0.05768',transform=ax.transAxes,va='top',fontsize=7)
    ax=fig.add_subplot(gs[1,:]);a=np.load(baseline).ravel();z=np.load(terminal).ravel()
    ax.scatter(a,z,s=3,alpha=.18,color=COLORS[2],rasterized=True);lo=min(a.min(),z.min());hi=max(a.max(),z.max())
    ax.plot([lo,hi],[lo,hi],color='.25',ls='--',lw=.7);ax.axhline(0,color='.7',lw=.5);ax.axvline(0,color='.7',lw=.5)
    ax.set(xlabel='Trajectory-integrated payoff (proxy effect × epoch)',ylabel='T × endpoint payoff (same units)')
    panel(ax,'c','Same paths, different payoff objectives')
    payload={'radius_hex':radius.tolist(),'bearing_radians':theta.tolist(),'field':field.tolist(),
             'calibration':data,'trajectory_payoff':a.tolist(),'terminal_payoff':z.tolist()}
    caption=('Directional field and payoff foundations. (a) Frozen CA kernel at ranges 4–24 hex, '
       'broadside target aspect and the fixed speed channel used by the solver; angular discontinuities are retained. '
       '(b) Arithmetic replay of 1,523 archived CA test rows, without refitting or regenerating engine ground truth. '
       '(c) All 6,561 deterministic path pairs in the head-on, speed-ratio 1, distance 16, T=4, Grid-3 anchor. '
       'The endpoint objective is multiplied by T to retain the same units; the dashed line denotes equality. '
       'Points are path combinations, not independent sampled encounters.')
    publish(fig,'fig02_foundations',caption,'A directional polar field, archived calibration scatter and same-path comparison of integrated and endpoint rewards.',
            [source,ROOT/'foundations/CALIBRATION_REPLAY.json',baseline,terminal],payload)
    return True


def frontier():
    source=ROOT/'analysis/frontiers.csv';data=[r for r in rows(source) if 'test' in r['phases'].split(';')]
    if len(data)!=144:raise RuntimeError('Fig3 requires all 24 frozen conditions and six budgets')
    fig,axes=plt.subplots(3,2,figsize=(6.85,7.2),layout='constrained',sharex=True)
    for row,g in enumerate(GEO):
        for col,k in enumerate(['F','C']):
            ax=axes[row,col]
            for i,speed in enumerate([.8,.95,1.05,1.2]):
                records=sorted([r for r in data if r['geometry']==g and r['opponent']==k and num(r,'speed')==speed],key=lambda r:num(r,'K'))
                x=np.array([num(r,'K') for r in records]);lo=np.array([num(r,'LB') for r in records]);hi=np.array([num(r,'UB') for r in records])
                center=(lo+hi)/2
                ax.plot(x,center,color=COLORS[i],marker=MARKERS[i],label=f'{speed:g}, {num(records[0],"distance"):g}')
                ax.fill_between(x,lo,hi,color=COLORS[i],alpha=.18)
                for xx,ll,uu,rr in zip(x,lo,hi,records):
                    if not np.isfinite(num(rr,'V')):ax.plot([xx,xx],[ll,uu],color=COLORS[i],lw=1.5,marker='_')
            ax.axhline(0,color='.65',lw=.5);ax.set_xticks(range(6));panel(ax,chr(97+2*row+col),f'{GNAME[g]} · opponent {k}')
            if col==0:ax.set_ylabel('Value (proxy effect × epoch)')
            if row==2:ax.set_xlabel('Replanning budget K')
    axes[0,0].legend(title='Speed ratio, distance',fontsize=6,title_fontsize=6,loc='best')
    publish(fig,'fig03_frontiers','Frozen-test budget–value frontiers. Lines join interval midpoints for display; bands are numerical lower/upper bounds, not confidence intervals. Explicit vertical ranges mark unresolved values. Both negative and positive values are retained. Four paired speed–distance configurations per geometry are computational tests and do not identify a causal speed effect.',
        'Six panels of budget–value frontiers, one per geometry and opponent class, showing all four frozen physical configurations.',[source],data)


def calendars():
    source=ROOT/'analysis/frontiers.csv';data=[r for r in rows(source) if 'test' in r['phases'].split(';')]
    if len(data)!=144:raise RuntimeError('Fig4 requires all frozen frontiers')
    fig,axes=plt.subplots(3,2,figsize=(6.85,6.0),layout='constrained',sharex=True,sharey=True)
    plotted=[]
    for i,g in enumerate(GEO):
        for j,k in enumerate(['F','C']):
            ax=axes[i,j];freq=np.zeros((4,5),dtype=int)
            for budget in range(1,5):
                rr=[r for r in data if r['geometry']==g and r['opponent']==k and num(r,'K')==budget]
                for r in rr:
                    for t in [int(x) for x in r['S'].split(',') if x]:freq[budget-1,t-1]+=1
            im=ax.imshow(freq,vmin=0,vmax=4,cmap='Blues',aspect='auto',extent=(.5,5.5,4.5,.5))
            for y in range(4):
                for x in range(5):ax.text(x+1,y+1,str(freq[y,x]),ha='center',va='center',color='white' if freq[y,x]>=3 else 'black')
            ax.set_xticks(range(1,6));ax.set_yticks(range(1,5));panel(ax,chr(97+2*i+j),f'{GNAME[g]} · opponent {k}')
            if j==0:ax.set_ylabel('Budget K')
            if i==2:ax.set_xlabel('Update epoch')
            plotted.append({'geometry':g,'opponent':k,'counts':freq.tolist()})
    fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.6,label='Selected in how many of four configurations',ticks=range(5))
    publish(fig,'fig04_calendars','Selected update epochs on the frozen test. Each cell counts inclusion in the best lower-bound calendar for four predeclared speed–distance pairs at that geometry, opponent and budget. Zero/full budgets are omitted because their calendars are fixed. Ties use the recorded deterministic rule; where a numerical gap remains, the calendar is a certified incumbent rather than an asserted exact optimizer. Complete individual schedules and intervals remain in the supplementary data.',
            'Six heatmaps count the selected update times for budgets one through four; each cell is an integer from zero to four.',[source],{'display':plotted,'individual_frontiers':data})


def losses():
    source=ROOT/'certificates/test_losses.csv';interval=ROOT/'interval_bounds/test.csv'
    data=rows(source) if source.exists() else [];edges=rows(interval) if interval.exists() else []
    fig,axes=plt.subplots(2,2,figsize=(6.85,6.2),layout='constrained')
    for j,k in enumerate(['F','C']):
        ax=axes[0,j]
        for i,g in enumerate(GEO):
            selected=[r for r in data if r['opponent']==k and r['geometry']==g]
            x=np.array([(num(r,'actual_loss_LB')+num(r,'actual_loss_UB'))/2 for r in selected]);y=np.array([num(r,'loss_certificate_UB') for r in selected])
            ax.scatter(x,y,s=9,marker=MARKERS[i],color=COLORS[i],alpha=.45,label=GNAME[g],rasterized=True)
        lim=max([num(r,'loss_certificate_UB') for r in data if r['opponent']==k]+[1.])
        ax.plot([0,lim],[0,lim],color='.35',ls='--',lw=.7);ax.set_xscale('symlog',linthresh=.01);ax.set_yscale('symlog',linthresh=.01)
        ax.set(xlabel='Actual loss (interval midpoint)',ylabel='Coarsened-policy loss upper bound')
        panel(ax,chr(97+j),f'Deletion certificate · {k}')
        ax.text(.04,.96,f'{sum(r["opponent"]==k for r in data)} / 384 calendars',transform=ax.transAxes,va='top',fontsize=6.5)
    axes[0,0].legend(fontsize=6,loc='lower right')
    ax=axes[1,0]
    for i,g in enumerate(GEO):
        rr=[r for r in edges if r['geometry']==g];x=[(num(r,'actual_loss_LB')+num(r,'actual_loss_UB'))/2 for r in rr];y=[num(r,'loss_UB') for r in rr]
        ax.scatter(x,y,s=13,marker=MARKERS[i],color=COLORS[i],alpha=.6)
    lim=max([num(r,'loss_UB') for r in edges]+[1.]);ax.plot([0,lim],[0,lim],color='.35',ls='--',lw=.7)
    ax.set_xscale('symlog',linthresh=.01);ax.set_yscale('symlog',linthresh=.01)
    ax.set(xlabel='Chosen-calendar actual loss',ylabel='Interval-path loss upper bound');panel(ax,'c','Public-interval bound · F only')
    ax.text(.04,.96,f'{len(edges)} / 72 budget decisions',transform=ax.transAxes,va='top',fontsize=6.5)
    ax=axes[1,1];anchor=ROOT/'interval_bounds/head_on_v0.8_d13.5_T6_G3_none/COMPLETE.json';src=[p for p in [source,interval] if p.exists()]
    payload={'deletion':data,'interval':edges}
    if anchor.exists():
        content=json.loads(anchor.read_text());a=np.full((6,6),np.nan)
        for edge in content['edges']:a[edge['t'],edge['end']-1]=edge['loss_UB']
        cmap=plt.get_cmap('cividis').copy();cmap.set_bad('#EEEEEE')
        im=ax.imshow(a,cmap=cmap,aspect='equal');fig.colorbar(im,ax=ax,shrink=.7,label='Loss upper bound')
        ax.set_xticks(range(6),range(1,7));ax.set_yticks(range(6));ax.set(xlabel='Interval end e',ylabel='Interval start t')
        src.append(anchor);payload['anchor_edges']=content['edges']
    else:ax.axis('off');ax.text(.5,.5,'Predeclared edge-map anchor\nnot completed',ha='center',va='center')
    panel(ax,'d','Head-on anchor interval costs')
    publish(fig,'fig05_losses','Certificate tightness on the frozen test. (a,b) Feasible behavioral deletion policies, assessed against complete worst responses, for every available calendar. (c) F-only interval-path bounds for the calendar chosen at each budget. Dashed lines denote equality; both axes use a symmetric-log scale with a linear region below 0.01, preserving zero. Points above the diagonal show conservatism, not additional performance. Counts disclose missing/resource-limited computations. (d) Predeclared first head-on test edge map; grey cells are invalid backward/zero-length intervals, not zero losses. Units are proxy effect × epoch throughout.',
            'Actual-loss versus certified-bound plots for both opponents, the F-only interval method and a forward-interval edge map.',src,payload)


def benchmarks():
    design=json.loads((ROOT/'DESIGN.json').read_text());anchors={c['id'] for c in design['cells'] if c['mirror_solve_all']}
    sources=sorted(p for p in (ROOT/'benchmarks/cold').glob('*.json') if not p.stem.endswith('_progress'))
    data=[json.loads(p.read_text()) for p in sources];data=[r for r in data if r.get('cell') in anchors and 'method' in r]
    methods=['enumeration','branch_bound','response_bound','greedy','uniform','front','back'];names=['Enum.','B&B','Resp.','Greedy','Uniform','Front','Back']
    fig,axes=plt.subplots(2,2,figsize=(6.85,6.3),layout='constrained')
    ordered=sorted({(r['cell'],r['opponent']) for r in data});plot=[]
    for r in data:
        idx=methods.index(r['method']);offset=(ordered.index((r['cell'],r['opponent']))-(len(ordered)-1)/2)*.035
        perf=r.get('execution',{});vals=[perf.get('wall_seconds',r.get('wall_seconds',np.nan)),r.get('oracle_calls',np.nan),
             perf.get('tree_peak_rss_bytes',r.get('peak_process_rss_bytes',np.nan))/1024**3,
             max((b.get('regret_UB',b['UB']-b['LB']) for b in r.get('budgets',[])),default=np.nan)]
        marker='x' if r.get('status')!='completed' else ('o' if r['opponent']=='F' else 's')
        col=COLORS[0] if r['opponent']=='F' else COLORS[1]
        for ax,y in zip(axes.ravel(),vals):ax.scatter(idx+offset,y,s=15,color=col,marker=marker,alpha=.65)
        plot.append({'cell':r['cell'],'opponent':r['opponent'],'method':r['method'],'metrics':vals,'status':r.get('status')})
    titles=['Cold process time','Equilibrium oracle calls','Peak process-tree memory','Largest budget regret upper bound']
    labels=['Seconds, including worker startup','Calls for all six budgets','GiB','Proxy effect × epoch']
    for i,(ax,title,label) in enumerate(zip(axes.ravel(),titles,labels)):
        panel(ax,chr(97+i),title);ax.set_xticks(range(7),names,rotation=35,ha='right');ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
    axes[0,0].set_yscale('symlog',linthresh=.1);axes[1,1].set_yscale('symlog',linthresh=1e-5)
    axes[1,0].axhline(8,color='.35',ls='--',lw=.7)
    publish(fig,'fig06_benchmarks','Cold calendar-search comparisons on six predeclared physical anchors, each with opponents F (blue circles) and C (orange squares). Each method starts with an empty calendar cache and reuses results only across its own budgets. Crosses identify unresolved/resource-limited runs; all such records are retained. Worker time includes process startup and payoff loading; shared physical-matrix construction is reported separately in the cost table. The final panel uses the largest independently bounded regret over budgets, including baselines. Fixed method order shares a six-hour case budget and can disadvantage later methods under censoring. Trace accounting is supplied separately and is not called measured wall-clock speedup.',
            'Four cold-run panels compare actual time, oracle counts, peak memory and regret bounds for seven methods; crosses denote incomplete cases.',[ROOT/'DESIGN.json',*sources],plot)


def robustness():
    source=ROOT/'analysis/cells.csv';data=rows(source)
    fig,axes=plt.subplots(3,2,figsize=(6.85,7.2),layout='constrained');plotted=[]
    for col,k in enumerate(['F','C']):
        for row,kind in enumerate(['horizon','grid','ablation']):
            ax=axes[row,col]
            for i,g in enumerate(GEO):
                rr=[r for r in data if r['geometry']==g and r['opponent']==k and num(r,'speed')==1 and num(r,'distance')==16 and r.get('complete')=='True']
                if kind=='horizon':rr=[r for r in rr if num(r,'grid')==3 and r['ablation']=='none'];rr.sort(key=lambda r:num(r,'T'));xx=[num(r,'T') for r in rr]
                elif kind=='grid':rr=[r for r in rr if num(r,'T')==4 and r['ablation']=='none'];rr.sort(key=lambda r:num(r,'grid'));xx=[num(r,'grid') for r in rr]
                else:
                    order=['none','isotropic','terminal','rigid'];rr=[r for r in rr if num(r,'T')==4 and num(r,'grid')==3];rr.sort(key=lambda r:order.index(r['ablation']));xx=[order.index(r['ablation'])+.1*(i-1) for r in rr]
                lo=np.array([num(r,'adaptation_LB') for r in rr]);hi=np.array([num(r,'adaptation_UB') for r in rr]);center=(lo+hi)/2
                ax.errorbar(xx,center,yerr=[center-lo,hi-center],color=COLORS[i],marker=MARKERS[i],ls='-' if kind!='ablation' else 'none',capsize=2,label=GNAME[g])
                plotted.extend(rr)
            panel(ax,chr(97+2*row+col),f'{kind.capitalize()} · opponent {k}');ax.axhline(0,color='.5',lw=.6)
            if col==0:ax.set_ylabel('Full adaptation value')
            if kind=='horizon':ax.set_xticks([4,5,6,7]);ax.set_xlabel('Horizon T, Grid-3')
            elif kind=='grid':ax.set_xticks([3,5,7]);ax.set_xlabel('Action-grid size, T = 4')
            else:ax.set_xticks(range(4),['LF base','Angle avg.','Endpoint','Rigid'],rotation=25,ha='right')
    axes[0,0].legend(fontsize=6)
    publish(fig,'fig07_robustness','Horizon, action-grid and one-factor model comparisons at speed ratio 1 and distance 16. Full adaptation value is V(F,R)−V(C,R); vertical ranges propagate both numerical intervals. Missing cells are absent, never zero-filled. Connecting horizon/grid observations aids reading and does not establish continuous-time or grid convergence; Grid-5 and Grid-7 are not nested. The isotropic identical-kernel control cancels analytically. All payoffs use proxy effect × epoch; the endpoint ablation includes the T multiplier. Complete budget frontiers and uncertainty statuses accompany the supplement.',
            'Six panels compare adaptation values across horizon, discrete action grids and model ablations for the two fixed opponent classes.',[source],plotted)


def decisions():
    source=ROOT/'analysis/retention.csv';data=[r for r in rows(source) if 'test' in r['phases'].split(';')]
    design=json.loads((ROOT/'DESIGN.json').read_text());configs=[c for g in GEO for c in design['cells'] if c['geometry']==g and 'test' in c['phases']]
    fig,axes=plt.subplots(1,2,figsize=(6.85,5.3),layout='constrained',sharey=True)
    for j,k in enumerate(['F','C']):
        ax=axes[j];a=np.full((12,3),np.nan);labels={}
        for i,c in enumerate(configs):
            for q,rho in enumerate([.9,.95,.99]):
                found=[r for r in data if r['cell']==c['id'] and r['opponent']==k and abs(num(r,'rho')-rho)<1e-9]
                if not found:labels[i,q]='missing';continue
                r=found[0];kc=num(r,'K_certified');kp=num(r,'K_possible')
                if r['status']=='small_or_unresolved_adaptation':labels[i,q]='abs.'
                elif np.isfinite(kc):a[i,q]=kc;labels[i,q]=str(int(kc)) if kp==kc else f'{int(kp)}–{int(kc)}'
                elif np.isfinite(kp):labels[i,q]=f'≥{int(kp)} ?'
                else:labels[i,q]='?'
        cmap=plt.get_cmap('Blues',6).copy();cmap.set_bad('#EEEEEE');im=ax.imshow(a,vmin=-.5,vmax=5.5,cmap=cmap,aspect='auto')
        for (i,q),text in labels.items():ax.text(q,i,text,ha='center',va='center',fontsize=7,color='white' if a[i,q]>=3 else 'black')
        ax.set_xticks(range(3),['90%','95%','99%']);ax.set_xlabel('Fraction of adaptation retained')
        ax.set_yticks(range(12),[f'{GNAME[c["geometry"]]}  {c["speed"]:g}/{c["distance"]:g}' for c in configs])
        for yy in [3.5,7.5]:ax.axhline(yy,color='white',lw=2)
        panel(ax,chr(97+j),f'Opponent {k}')
    fig.colorbar(im,ax=axes.tolist(),shrink=.6,ticks=range(6),label='Certified sufficient update budget')
    publish(fig,'fig08_decisions','Frozen-test minimum-budget decisions. Rows identify geometry and the predeclared speed-ratio/distance pair. A single integer means the possible and certified minimum budgets coincide. A range distinguishes the smallest possible budget from the smallest certified sufficient budget. A question mark denotes unresolved threshold status; “abs.” suppresses unstable percentages for small or unresolved adaptation and refers to the absolute-loss tables. Grey cells are not zero budgets. The guarantee concerns expected payoff against the full permitted opponent class; representative strategy paths are illustrations, with complete response laws in the replay data.',
            'Two twelve-by-three decision heatmaps give interval-aware minimum budgets for retaining 90, 95 and 99 percent of adaptation value.',[source,ROOT/'DESIGN.json'],data)


def main():
    p=argparse.ArgumentParser();p.add_argument('--foundations',action='store_true');p.add_argument('--all',action='store_true');a=p.parse_args()
    with plt.rc_context(STYLE):
        model();ready=foundation()
        if a.all:
            if not ready:raise RuntimeError('foundation ablation outputs missing')
            frontier();calendars();losses();benchmarks();robustness();decisions()
    print(json.dumps({'figure_manifests':[str(x) for x in sorted(OUT.glob('*_manifest.json'))],'foundation_ready':ready}))


if __name__=='__main__':main()
