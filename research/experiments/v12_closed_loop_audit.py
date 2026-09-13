"""Small correctness diagnostic only; not an expansion of the legacy B3 grid."""
import json,numpy as np
from pathlib import Path
from research.formation.exact_v12 import values_3x3
from research.geometry.differential_game import ReducedGame
from research.geometry.firepower_kernel import KernelFit
from research.geometry.committed_game import KernelWrap

class CorrectAspectReducedGame(ReducedGame):
    def _classify(self,radians):
        return super()._classify(np.degrees(radians))


def main():
    fit=KernelFit.from_dict(json.load(open('research/results/e01/kernel_fits.json'))['CA']);k=KernelWrap(fit)
    old=ReducedGame(k,k,n_r=4,n_alpha=12);new=CorrectAspectReducedGame(k,k,n_r=4,n_alpha=12)
    records=[]
    for tag,g in [('legacy_aspect',old),('correct_aspect',new)]:
        L=g._L;dyn=g._dynamics();Q=np.array([L+g.gamma*g._interp_V(L,*s) for s in dyn]).reshape(3,3,*g.shape)
        mats=Q.reshape(3,3,-1).transpose(2,0,1)
        mixed,gaps,_=values_3x3(mats);pure=mats.min(2).max(1)
        ix=int(np.argmax(abs(mixed-L.ravel())))
        records.append({'model':tag,'n_states':len(mats),'max_mixed_V2_minus_L':float(np.max(abs(mixed-L.ravel()))),
                        'max_pure_vs_mixed':float(np.max(abs(pure-mixed))),'max_lp_gap':float(max(gaps)),
                        'witness_state_index':list(map(int,np.unravel_index(ix,g.shape))),
                        'witness_L':float(L.ravel()[ix]),'witness_V2':float(mixed[ix]),
                        'witness_continuation_matrix':mats[ix].tolist()})
    result={'scope':'targeted 4x12x12 finite-two-stage regression; not a replacement of the legacy B3 experiment',
            'aspect_at_pi_over_2_old':str(old._classify(np.array(np.pi/2))),
            'aspect_at_pi_over_2_corrected':str(new._classify(np.array(np.pi/2))),
            'max_stage_change':float(np.max(abs(old._L-new._L))),'rows':records}
    Path('research/final_v12/audit/closed_loop_defects.json').write_text(json.dumps(result,indent=2));print(result)

if __name__=='__main__':main()
