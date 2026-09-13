"""Publication figures from preserved result files; no new hypothesis tests."""
import csv,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path('research/final_v12');OUT=Path('paper_v12/figures');OUT.mkdir(exist_ok=True)
GEO=('head_on','parallel','crossing');NAMES=('Head-on','Parallel','Crossing')
BLUE='#0072B2';RED='#D55E00';GREEN='#009E73';PURPLE='#CC79A7';GRAY='#667085'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10,
 'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.17,
 'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':320,'figure.constrained_layout.use':True})
MAN=[]
def read(p):return json.loads(Path(p).read_text())
def save(fig,name,sources,alt):
    for ext in ('pdf','png'):fig.savefig(OUT/f'{name}.{ext}',bbox_inches='tight')
    plt.close(fig)
    MAN.append({'figure':name,'sources':[{'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sources],
                'alt_text':alt,'format':'vector PDF; 320 dpi PNG','generated_by':__file__})

def information():
    fig,ax=plt.subplots(figsize=(7.0,3.9));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
    for x,y,label,sub in [(3,4.3,r'$V_{FF}$','both adapt'),(7,4.3,r'$V_{FC}$','Blue adapts'),
                           (3,1.8,r'$V_{CF}$','Red adapts'),(7,1.8,r'$V_{CC}$','both sealed')]:
        ax.add_patch(FancyBboxPatch((x-1.25,y-.64),2.5,1.28,boxstyle='round,pad=.12',fc='#F4F7FA',ec='#B7C2CE'))
        ax.text(x,y+.17,label,ha='center',va='center',fontsize=16);ax.text(x,y-.3,sub,ha='center',color=GRAY)
    ax.text(3,5.6,'Red flexible',ha='center');ax.text(7,5.6,'Red committed',ha='center')
    ax.text(.65,4.3,'Blue\nflexible',ha='center',va='center');ax.text(.65,1.8,'Blue\ncommitted',ha='center',va='center')
    for y in (1.8,4.3):ax.annotate('',(4.4,y),(5.6,y),arrowprops={'arrowstyle':'->','color':RED,'lw':1.8})
    for x in (3,7):ax.annotate('',(x,3.5),(x,2.6),arrowprops={'arrowstyle':'->','color':BLUE,'lw':1.8})
    ax.text(5,3.02,r'$F_R=V_{FC}-V_{FF}$',ha='center',color=RED)
    ax.text(8.75,3.1,r'$F_B$',ha='center',color=BLUE)
    ax.text(5,.35,r'$C=V_{CC}-V_{FF}=F_R-F_B$;  individual attribution depends on the path',ha='center')
    save(fig,'fig01_information',[ROOT/'THEORY_AUDIT.md'],'Four information structures; adding Blue flexibility raises value and adding Red flexibility lowers it. Bilateral effect is a difference of nonnegative path-specific benefits.')

def geometry():
    from research.formation.path_following import make_lf_game
    from research.formation.commitment_v12 import initial_states,formation_snapshot
    kd=read('research/results/e01/kernel_fits.json')['CA'];fig,axs=plt.subplots(1,3,figsize=(7.2,2.75),sharex=True,sharey=True)
    for ax,g,n in zip(axs,GEO,NAMES):
        game=make_lf_game(kd,g,1.,1.,6);b,r=initial_states(game)
        for s,c in [(b,BLUE),(r,RED)]:
            p,h=formation_snapshot(s,game);ax.plot(s.stations[:,0],s.stations[:,1],color=c,alpha=.25,lw=1)
            ax.scatter(p[:,0],p[:,1],color=c,s=[48,28,28],zorder=3)
            ax.quiver(p[:,0],p[:,1],np.cos(np.radians(h)),np.sin(np.radians(h)),color=c,scale=8)
        ax.set(title=n,aspect='equal',xlim=(-7,23),ylim=(-6,19),xlabel='x (grid-length unit)')
    axs[0].set_ylabel('y (grid-length unit)')
    save(fig,'fig02_geometry',['research/formation/path_following.py','research/formation/commitment_v12.py'],
         'Three prescribed initial geometries with complete straight prehistories. Half-turn exchange applies to head-on and crossing; reflection applies to parallel.')

def audit():
    p=ROOT/'audit/history_tests.json';d=read(p);rows=d['rows'];fig,axs=plt.subplots(1,2,figsize=(7.1,3.05))
    x=np.arange(1,len(rows)+1)
    for key,label,c in [('old_scalar_batch_error','Legacy scalar/vector',RED),('scalar_batch_error','Corrected scalar/vector',BLUE),('swap_error','Corrected swap',GREEN)]:
        axs[0].scatter(x,np.maximum([r[key] for r in rows],1e-16),s=10,label=label,color=c,alpha=.8)
    axs[0].axhline(1e-8,color=GRAY,ls='--',lw=1);axs[0].set(yscale='log',xlabel='Reachable history ID',ylabel='Absolute payoff error',title='(a) Independent payoff checks');axs[0].legend(fontsize=7,loc='center right')
    p2=ROOT/'audit/initial_grid5_controls.json';ds=read(p2)
    for r,n,c in zip(ds,NAMES,(BLUE,RED,GREEN)):
        axs[1].plot([a['iteration'] for a in r['trace']],np.maximum([a['gap'] for a in r['trace']],1e-15),label=n,color=c)
    axs[1].axhline(.005,color=GRAY,ls='--',lw=1);axs[1].axvline(15,color=GRAY,ls=':',lw=1)
    axs[1].set(yscale='log',xlabel='Double-oracle iteration',ylabel='Full open-loop saddle gap',title='(b) Initial Grid-5 controls');axs[1].legend(fontsize=7)
    save(fig,'fig03_audit',[p,p2], 'Legacy errors exceed numerical tolerance in every sampled history. Corrected errors approach floating-point precision. Initial Grid-5 games require 80 to 144 oracle iterations to meet strict gap tolerance.')

def cadence():
    p=ROOT/'exact_grid3/discovery_summary.json';ds=read(p)['rows'];fig,axs=plt.subplots(1,3,figsize=(7.2,2.85),sharex=True)
    for ax,g,n in zip(axs,GEO,NAMES):
        for er,c,m in [(.8,BLUE,'o'),(1.2,RED,'s')]:
            r=next(r for r in ds if r['geometry']==g and r['eta_r']==er)
            ys=[r['values'][str(h)]['V']-r['values']['1']['V'] for h in (1,2,3,6)]
            ax.plot((1,2,3,6),ys,marker=m,color=c,label=fr'$\eta_r={er}$')
        ax.axhline(0,color=GRAY,lw=.8);ax.set(title=n,xlabel='Sealed block length h',xticks=[1,2,3,6]);ax.legend(fontsize=8)
    axs[0].set_ylabel(r'Exact $V_{hh}-V_{11}$')
    save(fig,'fig04_exact_cadence',[p], 'All six exact discovery cadence curves are retained. Head-on has the hypothesized bilateral sign; parallel and crossing reverse it. Cadences two and three are not nested decision schedules.')

def flexibility():
    p=ROOT/'flexibility/discovery_summary.json'
    if not p.exists():return
    ds=read(p);fig,axs=plt.subplots(1,3,figsize=(7.2,2.85),sharey=True)
    for ax,g,n in zip(axs,GEO,NAMES):
        rows=[r for r in ds if r['geometry']==g]
        for k,c,m,lab in [('F_B',BLUE,'o',r'$F_B=V_{FC}-V_{CC}$'),('F_R',RED,'s',r'$F_R=V_{FC}-V_{FF}$')]:
            ax.plot([r['eta_r'] for r in rows],[r[k] for r in rows],marker=m,color=c,label=lab)
        ax.set(title=n,xlabel=r'Range ratio $\eta_r$',xticks=[.8,1.2],ylim=(0,None));ax.legend(fontsize=7)
    axs[0].set_ylabel('Path-specific flexibility value')
    save(fig,'fig05_flexibility',[p], 'Blue and Red unilateral flexibility benefits for all discovery cells. Both are nonnegative, but their ordering depends on geometry and range ratio.')

def heldout():
    p=ROOT/'flexibility/heldout_summary.json'
    if not p.exists():return
    ds=read(p);fig,ax=plt.subplots(figsize=(7.2,4.25))
    for i,r in enumerate(ds['rows']):
        c=GREEN if r['correct_resolved'] else RED;ax.errorbar(r['Delta_F'],i,xerr=[[r['Delta_F']-r['Delta_LB']],[r['Delta_UB']-r['Delta_F']]],fmt='o',color=c,capsize=3)
    ax.axvline(0,color=GRAY,ls='--',lw=1);ax.set_yticks(range(12),[f"{NAMES[GEO.index(r['geometry'])]:9s}   {r['eta_r']:.2f}   {r['eta_v']:.1f}" for r in ds['rows']],fontsize=8)
    ax.invert_yaxis();ax.set(xlabel=r'$\Delta_F=\mathrm{sign}(\eta_r-1)(V_{CC}-V_{FF})$',ylabel=r'Geometry    $\eta_r$    $\eta_v$',title=f"Frozen held-out grid: {ds['n_correct_resolved']}/12 support, {ds['n_reverse_resolved']}/12 reverse")
    save(fig,'fig06_heldout',[p], 'All twelve pre-frozen held-out cells with finite-game numerical bounds. Positive means support for the prespecified hypothesis, negative means reversal; bounds are not statistical confidence intervals.')

def mc():
    fig,axs=plt.subplots(1,3,figsize=(7.2,3.0),sharey=True);sources=[]
    for ax,g,n in zip(axs,GEO,NAMES):
        for tag,c,shift,lab in [('ordinary',GRAY,-.13,'Independent LP'),('spatial',BLUE,.13,'Coupled / canonical')]:
            p=ROOT/f'audit/{tag}_{g}_summary.json';sources.append(p);rs=read(p)[1:]
            for i,r in enumerate(rs):ax.errorbar(i+shift,r['C'],yerr=[[r['C']-r['CI_lo']],[r['CI_hi']-r['C']]],fmt='o',color=c,capsize=3,label=lab if i==0 else None)
        ax.axhline(0,color=GRAY,ls='--',lw=.8);ax.set(title=n,xticks=[0,1,2],xticklabels=['2','3','6'],xlabel='Replanning cadence h');ax.legend(fontsize=7)
    axs[0].set_ylabel('Receding-policy payoff difference\n(mean and pointwise 95% bootstrap CI)')
    save(fig,'figS01_mc_controls',sources,'Paired 200-seed Monte Carlo receding-policy contrasts; original threshold gate fails. These are planner outcomes, not exact feedback equilibrium values; intervals are pointwise, unadjusted.')

def sweep():
    caps=[15,30,60,120,200];tols=[.05,.02,.01,.005];fig,axs=plt.subplots(2,3,figsize=(7.4,5.0));sources=[]
    for j,(g,n) in enumerate(zip(GEO,NAMES)):
        a=np.zeros((4,5));labels={};points=[]
        for i,tol in enumerate(tols):
            for k,cap in enumerate(caps):
                p=ROOT/f'audit/sweep_tol{tol:g}_cap{cap}_{g}_summary.json';q=ROOT/f'audit/sweep_tol{tol:g}_cap{cap}_{g}.json';sources.extend([p,q]);r=read(p)[-1];eps=read(q)['epochs'];gap=max(e['rel_gap'] for e in eps)
                a[i,k]=r['complete'];labels[i,k]=f"{r['C']:.2f}" if r['complete'] else 'fail'
                if r['complete']:points.append((gap,r,tol,cap))
        ax=axs[0,j];ax.imshow(a,cmap=matplotlib.colors.ListedColormap(['#E8EAED','#C9E6F0']),vmin=0,vmax=1,aspect='auto')
        for (i,k),lab in labels.items():ax.text(k,i,lab,ha='center',va='center',fontsize=8)
        ax.set(xticks=range(5),xticklabels=caps,yticks=range(4),yticklabels=['5%','2%','1%','0.5%'],xlabel='Iteration cap',title=n);ax.grid(False)
        ax=axs[1,j]
        for gap,r,tol,cap in points:
            ax.errorbar(max(gap,1e-13),r['C'],yerr=[[r['C']-r['CI_lo']],[r['CI_hi']-r['C']]],fmt='o',color=BLUE,alpha=.45,capsize=2)
        ax.axhline(0,color=GRAY,ls='--');ax.set(xscale='log',xlabel='Max sampled local relative gap')
    axs[0,0].set_ylabel('Requested relative tolerance');axs[1,0].set_ylabel('C6, N=8 diagnostic\n(pointwise 95% bootstrap CI)')
    save(fig,'figS02_sweep',sources,'Sixty tolerance-cap settings. Failed episodes invalidate cell means. Valid cells retain Monte Carlo uncertainty; reducing local open-loop gap does not prove convergence to a feedback equilibrium.')

def legacy():
    p=Path('research/results/e01/baselines.json');ds=read(p)['per_class'];fig,axs=plt.subplots(1,2,figsize=(7.2,2.8));x=np.arange(4)
    for ax,k1,k2,title in [(axs[0],'spearman_full','spearman_isotropic','Held-out rank correlation'),(axs[1],'nmae_full','nmae_isotropic','Held-out normalized MAE')]:
        ax.bar(x-.18,[r[k1] for r in ds.values()],.36,color=BLUE,label='Directional');ax.bar(x+.18,[r[k2] for r in ds.values()],.36,color=GRAY,label='Isotropic')
        ax.set(xticks=x,xticklabels=list(ds),title=title);ax.legend(fontsize=8)
    save(fig,'figS03_kernel',[p],'Archived E01 directional and isotropic kernel held-out comparison across four classes, 1523 test points per class. Data are carried forward, not new v12 calibration.')
    p=Path('research/results/b2/snapshot_vs_integral.csv');rows=list(csv.DictReader(p.open()));q=Path('research/results/b2/example_AB.json');ex=read(q)['example'];fig,axs=plt.subplots(1,2,figsize=(7.2,3.0))
    for pair,c,lab in [('integral_vs_snapshot_T',BLUE,'Terminal'),('integral_vs_snapshot_peak',RED,'Peak')]:
        rs=[r for r in rows if r['objective_pair']==pair];axs[0].plot(range(9),[float(r['kendall_entry']) for r in rs],marker='o',color=c,label=lab)
    axs[0].set(xlabel='Archived cell ID',ylabel=r'Kendall $\tau$ with integral payoff',ylim=(0,1));axs[0].legend(fontsize=8)
    for k,c in [('A',RED),('B',BLUE)]:axs[1].plot(range(40),ex[k]['L_series'],color=c,label=f"{k}: peak {ex[k]['peak']:.2f}, J {ex[k]['integral']:.2f}")
    axs[1].axhline(0,color=GRAY,lw=.8);axs[1].set(xlabel='Turn (archived 40-turn model)',ylabel='Instantaneous payoff');axs[1].legend(fontsize=7)
    save(fig,'figS04_objectives',[p,q],'Archived snapshot and path-integral rankings differ. The illustrative A and B joint trajectories use different plans for both players and do not isolate a unilateral causal effect.')
    p=Path('research/results/b4/b41_monotonicity.csv');rs=list(csv.DictReader(p.open()));fig,axs=plt.subplots(1,2,figsize=(7.2,2.85))
    for ax,g,n in zip(axs,GEO[:2],NAMES[:2]):
        for er,c in [(.75,BLUE),(1.,GRAY),(1.33,RED)]:
            ds=[r for r in rs if r['geometry']==g and float(r['eta_r'])==er]
            ax.plot([float(r['vbar']) for r in ds],[float(r['V_lp']) for r in ds],marker='o',color=c,label=fr'$\eta_r={er}$')
        ax.set(title=n,xlabel='Selectable speed ceiling',xticks=[2,4,6]);ax.legend(fontsize=8)
    axs[0].set_ylabel('Archived 40-turn matrix value')
    save(fig,'figS05_capability',[p],'Archived nested selectable speed sets have nondecreasing values. This is distinct from forcing a larger operating speed and is not a new flexibility result.')
    p=Path('research/final_v10/torpedo_sensitivity/threat_contraction.csv');rs=list(csv.DictReader(p.open()));fig,axs=plt.subplots(1,3,figsize=(7.2,3.0),sharey=True)
    for ax,geo,title in zip(axs,GEO,NAMES):
        for model,c,m in [('rigid_line_ahead',GRAY,'s'),('leader_follower',BLUE,'o')]:
            for intensity,ls in [(.5,'--'),(2.,'-')]:
                ds=[r for r in rs if r['geometry']==geo and r['model']==model and float(r['intensity'])==intensity]
                ax.plot([float(r['corridor_halfwidth']) for r in ds],[float(r['c_resp']) for r in ds],color=c,marker=m,ls=ls,label=f"{'Rigid' if model.startswith('rigid') else 'LF'}, intensity {intensity}")
        ax.set(title=title,xlabel='Threat corridor half-width');ax.legend(fontsize=6)
    axs[0].set_ylabel('Response-library contraction')
    save(fig,'figS06_archived_threat',[p],'All 36 archived threat sensitivity settings for LF and rigid models under legacy path semantics. These exploratory diagnostics do not establish v12 formation robustness.')

def main():
    information();geometry();audit();cadence();flexibility();heldout();mc();sweep();legacy()
    (OUT/'FIGURE_MANIFEST.json').write_text(json.dumps(MAN,indent=2))
    print('Generated',len(MAN),'figures')
if __name__=='__main__':main()
