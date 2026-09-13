"""DRAFT experimental figures only; no manuscript files are touched."""
import hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Circle

R=Path('research/final_v13');O=R/'figures';O.mkdir(exist_ok=True)
GEO=('head_on','parallel','crossing');NAME=('Head-on','Parallel','Crossing')
COLORS=('#0072B2','#D55E00','#009E73');BLUE=COLORS[0];RED=COLORS[1];GRAY='#667085';MAN=[]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10,
 'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,
 'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':320,'figure.constrained_layout.use':True})
def read(p):return json.loads(Path(p).read_text())
def save(fig,name,sources,alt):
    fig.suptitle('DRAFT · experimental evidence',fontsize=10,color=GRAY)
    for ext in ('png','pdf'):fig.savefig(O/f'{name}.{ext}',bbox_inches='tight')
    plt.close(fig);MAN.append({'figure':name,'status':'DRAFT','alt_text':alt,'formats':'vector PDF and 320 dpi PNG',
      'sources':[{'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sources]})

def favorable():
    p=R/'mechanism/discovery/illustration_head_on_0.7.npz';q=R/'mechanism/discovery/illustration_head_on_1.3.npz';a=np.load(p);b=np.load(q)
    fig,axs=plt.subplots(1,2,figsize=(7.2,3.6))
    for ax,key,title in zip(axs,['L_before','L_after'],['Before opponent turn','After opponent turn']):
        Z=a['Z'];L=a[key];z=Z[L>=.9*L.max()];ax.scatter(z[:,0],z[:,1],s=45,marker='s',color='#009E73',label='Favorable states (heading projected)')
        ax.add_patch(Circle((0,0),24,fill=False,ec=GRAY,ls=':',lw=.8));ax.scatter([0],[0],color=GRAY,marker='x',s=45,label='Opponent leader origin')
        ax.set(title=title,xlabel='Relative x',ylabel='Relative y',aspect='equal',xlim=(-25,25),ylim=(-25,25));ax.legend(fontsize=6,loc='lower left')
    ax=axs[1]
    for data,c,m,label in [(a,BLUE,'o','Slow: speed ratio .70'),(b,RED,'^','Fast: speed ratio 1.30')]:
        z=data['reachable'];ax.scatter(z[:,0],z[:,1],color=c,marker=m,s=35,label=label)
    ax.scatter(a['before'][0],a['before'][1],color='black',marker='+',s=70,label='Current focal pose, next frame')
    ax.legend(fontsize=6,loc='lower left')
    save(fig,'Fig_A_favorable_set',[p,q,R/'MECHANISM_PROTOCOL.md'],
         'Preselected head-on probe zero, epoch zero. Favorable three-dimensional states are projected onto position; heading is not discarded in distance calculations. Three discrete reachable endpoints per speed are shown, not a continuous reachable region. Frames translate with the opponent, retaining world orientation.')

def factorial():
    fig,ax=plt.subplots(figsize=(7.,3.5));ax.set(xlim=(0,10),ylim=(0,5.4));ax.axis('off')
    for x,y,text in [(3,3.8,r'$V(C,\kappa_R;v_H)$'),(7,3.8,r'$V(F,\kappa_R;v_H)$'),(3,1.8,r'$V(C,\kappa_R;v_L)$'),(7,1.8,r'$V(F,\kappa_R;v_L)$')]:
        ax.add_patch(FancyBboxPatch((x-1.6,y-.6),3.2,1.2,boxstyle='round,pad=.1',ec='#ACB8C5',fc='#F4F7FA'));ax.text(x,y,text,ha='center',va='center',fontsize=13)
    ax.text(.6,3.8,'High\nspeed',ha='center',va='center');ax.text(.6,1.8,'Low\nspeed',ha='center',va='center')
    ax.text(3,4.9,'Own committed',ha='center');ax.text(7,4.9,'Own flexible',ha='center')
    for y in [1.8,3.8]:ax.annotate('',(5.3,y),(4.7,y),arrowprops={'arrowstyle':'->','color':BLUE,'lw':1.8})
    ax.text(5,.55,r'$M^{\kappa_R}=\mathcal{F}(v_H\mid\kappa_R)-\mathcal{F}(v_L\mid\kappa_R)$',ha='center',fontsize=12)
    ax.text(5,.08,'Opponent speed and policy class are held fixed in all four cells.',ha='center',color=GRAY)
    save(fig,'Fig_B_factorial',[R/'DISCOVERY_PROTOCOL.md'],'The own-speed by own-adaptation factorial holds the opponent speed and strategy class fixed. Its interaction is distinct from the bilateral commitment difference.')

def curves():
    p=R/'discovery/all_results.json';d=read(p);fig,axs=plt.subplots(1,3,figsize=(7.2,3.0),sharey=True)
    for ax,g,n in zip(axs,GEO,NAME):
        rs=[r for r in d if r['geometry']==g]
        for k,c,m in [('F',BLUE,'o'),('C',RED,'s')]:
            ax.plot([r['focal_speed_ratio'] for r in rs],[r['blue']['conditional_flexibility'][k]['F'] for r in rs],color=c,marker=m,label=f'Opponent {k}')
        ax.set(title=n,xlabel='Own operating-speed ratio',xticks=[.7,1.,1.3],ylim=(0,None));ax.legend(fontsize=8)
    axs[0].set_ylabel('Conditional own-flexibility value')
    save(fig,'Fig_C_discovery_curves',[p],'All five speed values and both fixed opponent classes, for all three geometries. Curves are exploratory and nonmonotone; nonnegative flexibility does not imply positive speed interaction.')

def confirmatory():
    p=R/'analysis/confirmatory_interactions.json'
    if not p.exists():return
    rows=read(p);q=R/'analysis/confirmatory_mechanism.json';s=read(q)
    fig,ax=plt.subplots(figsize=(6.5,3.9))
    for gi,g in enumerate(GEO):
        for k,m in [('F','o'),('C','s')]:
            rs=[r for r in rows if r['geometry']==g and r['opponent_policy']==k]
            ax.scatter([r['delta_Theta_0.9'] for r in rs],[r['M'] for r in rs],color=COLORS[gi],marker=m,s=55,label=f'{NAME[gi]}, opponent {k}')
    ax.axhline(0,color=GRAY,ls='--',lw=.9);ax.axvline(0,color=GRAY,ls=':',lw=.9)
    ax.set(xlabel=r'$\Delta\bar\Theta$ (high minus low speed)',ylabel='Conditional flexibility interaction M',title=f"Frozen probe association: Spearman rho = {s['primary_spearman']:.3f}")
    ax.legend(fontsize=7,loc='best')
    save(fig,'Fig_D_mechanism',[p,q], 'Twelve policy endpoints share six physical speed contrasts. The plot is descriptive, not causal mediation. A positive association when both tracking and adaptation decline does not support the proposed directional chain.')
    fig,ax=plt.subplots(figsize=(7.1,4.5))
    for i,r in enumerate(rows):
        c='#009E73' if r['positive'] else RED;m='o' if r['positive'] else 'x'
        ax.errorbar(r['M'],i,xerr=[[max(0,r['M']-r['LB'])],[max(0,r['UB']-r['M'])]],fmt=m,color=c,capsize=3)
    ax.axvline(0,color=GRAY,ls='--');ax.set_yticks(range(len(rows)),[f"{NAME[GEO.index(r['geometry'])]} / {r['contrast']} / opp. {r['opponent_policy']}" for r in rows],fontsize=8)
    ax.invert_yaxis();ax.set(xlabel='M with finite-game numerical bounds',title=f"Primary held-out support: {sum(r['positive'] for r in rows)}/12")
    save(fig,'Fig_E_confirmatory_forest',[p], 'Every pre-frozen held-out interaction is retained. Bounds are numerical finite-game intervals, not sampling confidence intervals; they may be narrower than markers. Crosses denote resolved negative outcomes.')
    fig,ax=plt.subplots(figsize=(6.8,3.2));x=np.arange(1,len(rows)+1)
    ax.semilogy(x,[abs(r['M']) for r in rows],'o',color=BLUE,label='Absolute interaction')
    ax.semilogy(x,np.maximum([r['interval_width'] for r in rows],1e-16),'x',color=RED,label='Numerical interval width')
    ax.set(xlabel='Held-out endpoint ID',ylabel='Payoff units, logarithmic scale',xticks=x);ax.legend(fontsize=8)
    save(fig,'Fig_H_numerical_separation',[p],'Effect magnitudes and full interval widths for all twelve primary endpoints. Log-display floor is 1e-16 only; original values are preserved in the source table.')

def capability():
    p=R/'capability/all_results.json'
    if not p.exists():return
    ds=read(p);rows=[r for d in ds for r in d['interactions']];fig,ax=plt.subplots(figsize=(7.,3.25))
    for i,r in enumerate(rows):
        ok=r['LB']>0;ax.errorbar(r['M'],i,xerr=[[r['M']-r['LB']],[r['UB']-r['M']]],fmt='o' if ok else 'x',color='#009E73' if ok else RED,capsize=3)
    ax.set_yticks(range(6),[f"{NAME[GEO.index(r['geometry'])]} / opponent {r['opponent_policy']}" for r in rows],fontsize=8);ax.invert_yaxis();ax.axvline(0,color=GRAY,ls='--')
    ax.set(xlabel='M: expanded selectable-speed menu minus baseline menu',title='Separate T=4 capability diagnostic; not part of primary count')
    save(fig,'Fig_F_capability',[p],'Six interactions from genuinely nested per-turn speed menus, low .75/1.0 and high .75/1.0/1.3. Five support complementarity; head-on against a flexible opponent reverses. This limited-horizon check is separate from the forced-speed primary experiment.')

def metrics():
    p=R/'mechanism/discovery/all_results.json';ds=read(p);fig,axs=plt.subplots(1,2,figsize=(7.2,3.0))
    for g,n,c,m in zip(GEO,NAME,COLORS,['o','s','^']):
        rs=[r for r in ds if r['geometry']==g]
        for alpha,ls in [(.9,'-'),(.8,'--')]:
            ss=[next(s for s in r['summary'] if s['alpha']==alpha) for r in rs]
            axs[0].plot([r['focal_speed_ratio'] for r in rs],[s['Theta'] for s in ss],color=c,ls=ls,marker=m,label=f'{n}, alpha {alpha}')
        axs[1].plot([r['focal_speed_ratio'] for r in rs],[r['summary'][0]['negative_correction_fraction'] for r in rs],color=c,marker=m,label=n)
    axs[0].set(xlabel='Own operating-speed ratio',ylabel='Median bounded tracking score',ylim=(-.01,.5));axs[0].legend(fontsize=6)
    axs[1].set(xlabel='Own operating-speed ratio',ylabel='Fraction with negative raw correction',ylim=(0,1));axs[1].legend(fontsize=7)
    save(fig,'Fig_G_tracking_diagnostics',[p], 'Frozen primary and alpha=.8 tracking curves plus negative raw-correction frequencies. Signed corrections remain in data; only the declared bounded score uses their positive part. The tracking axis displays the observed lower half of its theoretical zero-to-one range.')

def main():
    favorable();factorial();curves();confirmatory();capability();metrics()
    (O/'FIGURE_MANIFEST.json').write_text(json.dumps(MAN,indent=2));print('DRAFT figures',len(MAN))
if __name__=='__main__':main()
