"""Build local evidence-bounded developmental-review inputs, not certification."""
import csv,json
from pathlib import Path
R=Path('research/final_v13');O=R/'reviews'
SK=Path('/Users/Zhuanz1/.codex/skills')
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    g=json.loads((R/'analysis/GATE_DATA.json').read_text());a=json.loads((R/'analysis/NUMERICAL_AUDIT.json').read_text())
    claims=[
      ('C01','Gate','primary_outcome',f"Primary positive support {g['n_positive']}/12 under amended frozen design",'E_CONFIRM;E_GATE','supported','none','Finite forced-speed Grid3 T6 only',''),
      ('C02','Theory','generalization','Mobility capability always increases adaptation value','E_CAPABILITY;E_THEORY','unsupported','scope','Nested-menu and algebraic counterexamples retained','Do not assert general complementarity.'),
      ('C03','Mechanism','causal','Higher speed improves tracking and thereby adaptation','E_MECHANISM','unsupported','causal_language','Standardized probes and failed directional chain','Do not claim causal mediation or a positive chain.'),
      ('C04','Capability','secondary_outcome',f"Separate T4 capability diagnostic {a['capability']['positive']}/6 positive",'E_CAPABILITY','supported','none','Not primary confirmation or horizon robustness',''),
      ('C05','Theory','other','Reduced quadratic tracking theorem under fixed disturbance and ball/reset assumptions','E_THEORY','supported','none','Proof scope explicit; novelty and specialist endorsement unverified',''),
      ('C06','Numerics','methods','Final complete mirrors and nonnegative adaptation verified in tested cells','E_AUDIT;E_TESTS','supported','none','Finite floating-point calculation; not universal solver correctness',''),
      ('C07','Readiness','generalization','Current experiment establishes CAS Q1 or Q2 manuscript readiness','E_GATE;E_FALLBACK','unsupported','scope','No current new manuscript or independent review; fallback known defects','Do not certify journal rank or readiness.'),
      ('C08','Protocol','methods','Design stayed fixed but payoff implementation was amended after a mirror failure','E_AMENDMENT;E_FREEZE','supported','none','Original incomplete run archived; all affected scientific data rerun','')]
    fields=['claim_id','location','claim_type','claim_summary','evidence_ids','support_level','alignment_issue','limitation','requested_action']
    with (O/'claim_evidence.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(claims)
    evidence={'E_CONFIRM':'analysis/confirmatory_interactions.csv','E_GATE':'analysis/GATE_DATA.json','E_CAPABILITY':'capability/all_results.json','E_THEORY':'THEOREM_SCRATCHPAD.md','E_MECHANISM':'analysis/confirmatory_mechanism.json','E_AUDIT':'analysis/NUMERICAL_AUDIT.json','E_TESTS':'REGRESSION_FINAL.log','E_AMENDMENT':'analysis/AMENDMENT_AUDIT.json','E_FREEZE':'RERUN_FREEZE.json','E_FALLBACK':'../../manuscript_q2_frozen/README.md'}
    dump(O/'evidence_index.json',evidence)
    s=json.loads((SK/'peer-review/assets/statistical_reproducibility_template.json').read_text());s['checklist_id']='IBS-V13-EXPERIMENT';s['study_design']='finite_computational_game';s['specialist_review']={'needed':'yes','areas':['mathematical_novelty','numerical_game_theory','journal_fit'],'requested':False}
    notes={
      'question.estimand_alignment':('confirmatory_design/CONFIRMATORY_DESIGN.md','Fixed opponent speed and class; H2 is algebraically the same factorial, no new endpoint.'),
      'design.unit_and_independence':('confirmatory_design/CONFIRMATORY_DESIGN.md','Twelve fixed endpoints, six physical speed contrasts; mirrors and policy classes are not extra independent replicates.'),
      'design.sample_size_precision':('DISCOVERY_PROTOCOL.md','Grid fixed for finite exhaustive computation; no population power claim or binomial inference.'),
      'data.inclusion_exclusion':('analysis/confirmatory_interactions.csv','All frozen endpoints retained; original failure archived rather than excluded.'),
      'data.missing_data':('analysis/NUMERICAL_AUDIT.json','No missing final primary value or favorable set; domain-exceeding states and zero drift separately flagged.'),
      'data.outliers_transformations':('MECHANISM_PROTOCOL.md','Signed raw correction preserved; declared positive-part bounded diagnostic and fixed medians, no outlier deletion.'),
      'analysis.prespecification':('IMPLEMENTATION_AMENDMENT_01.md','Post-freeze implementation correction disclosed; design unchanged, entire dataset recomputed.'),
      'analysis.method_design_alignment':('analysis/confirmatory_mechanism.json','Full finite game values; descriptive fixed-design association, no sampling p-values.'),
      'analysis.assumptions_diagnostics':('THEOREM_SCRATCHPAD.md','Reduced theorem assumptions do not establish full naval mechanism; no finer-grid or domain sensitivity after failed gate.'),
      'analysis.multiplicity':('confirmatory_design/CONFIRMATORY_DESIGN.md','Primary hierarchy fixed; capability and alternative metric correlations not added to primary success count.'),
      'analysis.clustering_repeated_measures':('MECHANISM_PROTOCOL.md','Paired seeded probes shared across speeds, classes and geometries; no independent N inflation.'),
      'results.effect_sizes_uncertainty':('analysis/confirmatory_interactions.csv','Full floating-point value bounds propagated by interval subtraction; not confidence intervals; probe IQR separate.'),
      'results.denominators_flow':('analysis/NUMERICAL_AUDIT.json','27 focal and 27 mirror games, four values each; 12 endpoints; 6 separate capability interactions.'),
      'results.complete_outcomes_harms':('PLAN_EXECUTION_LEDGER.md','Nulls, reversals, missing original computations, amendment and conditional non-execution all reported.'),
      'reproducibility.data_materials_access':('REPRODUCIBILITY.md','Local code, complete matrices, protocols, raw probe records, figures and original failure preserved.'),
      'reproducibility.code_environment_parameters':('ENVIRONMENT.json','Versioned Python environment, seed, grid and rerun instructions recorded.'),
      'reproducibility.provenance_versions':('RERUN_FREEZE.json','Original and amended freezes, independent archive, final checksums and comparison table.'),
      'ethics.approval_consent_governance':('reviews/SCOPE.md','Author-requested local developmental review; no humans/animals enrolled or external manuscript upload.'),
      'interpretation.claim_evidence_causality':('V13_Q1_GATE.md','Explicit failed chain, reduced theorem scope, no generality or publication certification.'),
      'integrity.deviations_selective_reporting':('analysis/AMENDMENT_AUDIT.json','Every available original value compared; no old values imputed or design thresholds adjusted.')}
    for x in s['items']:
        if x['id'] in ['design.allocation_randomization','design.blinding']:
            x.update(applicability='not_applicable',status='not_applicable',evidence_locations=['MECHANISM_PROTOCOL.md'],note='No participant allocation or blinded clinical assessment. Deterministic exact model; probe PCG64 seed and paired actions are fixed. Analysts saw discovery and the implementation failure.',requested_action='')
        else:
            loc,note=notes[x['id']];x.update(status='verified_present',evidence_locations=[loc],note=note,requested_action='')
    # This screen records disclosure completeness, not that these limitations vanished.
    dump(O/'statistics_reproducibility.json',s)
    facts=[]
    for i,section in enumerate(['Gate','Advisor'],1):
        facts.append({'fact_id':f'N{i:03}','section':section,'concept':'primary_positive_support','analysis_set':'amended_frozen_primary','value':g['n_positive'],'unit':'count','numerator':g['n_positive'],'denominator':12,'sample_size':None,'evidence_ids':['E001']})
    cm={'schema_version':'1.0','numeric_facts':facts,'methods':[{'method_id':'M001','name':'final rerun analysis: implementation amended after original held-out failure and before rerun; design unchanged','analysis_intent':'confirmatory','protocol_status':'amended_before_analysis','outcome_ids':['O001']}],
      'results':[{'result_id':'R001','method_id':'M001','outcome_id':'O001','analysis_intent':'confirmatory','reported_sections':['Gate','Advisor'],'sample_size':12,'evidence_ids':['E001']}]}
    dump(O/'consistency_manifest.json',cm)
    (O/'CONSISTENCY_SCOPE.md').write_text('E001 maps to E_CONFIRM in evidence_index.json. The generic validator requires a non-null sample_size: 12 here means the count of fixed computational endpoints, NOT 12 independent sampled observations. Protocol status amended_before_analysis is scoped to the final rerun analysis; the implementation correction occurred AFTER the original held-out failure, as disclosed throughout the report. The original design was unchanged.\n')
    print('Review inputs created; automated checks do not certify merit or replace independent review.')
if __name__=='__main__':main()
