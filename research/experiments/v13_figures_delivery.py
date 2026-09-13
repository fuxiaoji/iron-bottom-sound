"""Final layout-only corrections; retain the frozen original plotting source.

Move C/D legends outside the data region after visual QA detected occlusion.
All data, transformations, thresholds and eight figure definitions are unchanged.
"""
import json
import matplotlib.pyplot as plt
from research.experiments import v13_figures as b

def main():
    b.main()
    p=b.R/'discovery/all_results.json';ds=b.read(p)
    fig,axs=plt.subplots(1,3,figsize=(7.2,3.25),sharey=True)
    for ax,g,n in zip(axs,b.GEO,b.NAME):
        rs=[r for r in ds if r['geometry']==g]
        for k,c,m in [('F',b.BLUE,'o'),('C',b.RED,'s')]:
            ax.plot([r['focal_speed_ratio'] for r in rs],[r['blue']['conditional_flexibility'][k]['F'] for r in rs],color=c,marker=m,label=f'Opponent {k}')
        ax.set(title=n,xlabel='Own operating-speed ratio',xticks=[.7,1.,1.3],ylim=(0,None))
        ax.legend(fontsize=7,loc='lower center',bbox_to_anchor=(.5,1.08),ncol=2,frameon=False,handlelength=1.2,columnspacing=.7)
    axs[0].set_ylabel('Conditional own-flexibility value')
    original=next(r for r in b.MAN if r['figure']=='Fig_C_discovery_curves')
    b.save(fig,'Fig_C_discovery_curves',[p],original['alt_text'])
    p=b.R/'analysis/confirmatory_interactions.json';q=b.R/'analysis/confirmatory_mechanism.json';rows=b.read(p);s=b.read(q)
    fig,ax=plt.subplots(figsize=(7.5,4.2))
    for gi,g in enumerate(b.GEO):
        for k,m in [('F','o'),('C','s')]:
            rs=[r for r in rows if r['geometry']==g and r['opponent_policy']==k]
            ax.scatter([r['delta_Theta_0.9'] for r in rs],[r['M'] for r in rs],color=b.COLORS[gi],marker=m,s=55,label=f'{b.NAME[gi]}, opponent {k}')
    ax.axhline(0,color=b.GRAY,ls='--',lw=.9);ax.axvline(0,color=b.GRAY,ls=':',lw=.9)
    ax.set(xlabel=r'$\Delta\bar\Theta$ (high minus low speed)',ylabel='Conditional flexibility interaction M',title=f"Frozen probe association: Spearman rho = {s['primary_spearman']:.3f}")
    ax.legend(fontsize=7,loc='center left',bbox_to_anchor=(1.02,.5),frameon=False)
    original=next(r for r in b.MAN if r['figure']=='Fig_D_mechanism')
    b.save(fig,'Fig_D_mechanism',[p,q],original['alt_text'])
    unique={r['figure']:r for r in b.MAN}
    for name in ['Fig_C_discovery_curves','Fig_D_mechanism']:
        unique[name]['layout_note']='Legend moved outside the data area after local visual inspection; original frozen plotting source retained unchanged.'
    (b.O/'FIGURE_MANIFEST.json').write_text(json.dumps(list(unique.values()),indent=2))
    print('Final delivery: eight figures, two layout-only legend corrections.')
if __name__=='__main__':main()
