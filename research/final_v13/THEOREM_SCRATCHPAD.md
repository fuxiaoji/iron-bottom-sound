# Theory scratchpad — DRAFT, no manuscript rewrite

## Established policy-set facts

For fixed opponent conditions, embedding committed pure policies in flexible pure policies gives F_B^F=V_FF-V_CF>=0 and F_B^C=V_FC-V_CC>=0 by finite minimax. Their differences across operating speeds need not be nonnegative because forced speeds do not produce nested policy sets. Even when capabilities DO produce nested policy sets, the difference of two nondecreasing value functions need not increase. The v12 bilateral identity is retained but is not the new estimand.

### Finite-game proof and algebraic identities

Let A be the fixed finite history-payoff matrix induced by the physical model, and let P_C subset P_F be the maximizer's distributions over pure contingent policies; let Q_kappa be the SAME fixed opponent policy set in the two games. For every p in P_C the quantity min(q in Q_kappa) p'Aq is feasible in the maximization over P_F. Taking maxima proves V(F,kappa)>=V(C,kappa). A committed sequence embeds as the flexible policy that plays that sequence regardless of observed executed history. Finite mixed-strategy minimax, or the equivalent perfect-recall realization representation, supplies the values. For the minimizing player enlargement reverses the value inequality. This proves nonnegative adaptation value for either focal player after consistent payoff sign conversion; it compares neither physical speed nor different opponent classes.

Define A_R=V_FC-V_FF>=0 (Red's adaptation value with Blue F), A_B=V_FC-V_CC>=0 (Blue's adaptation value with Red C). Direct cancellation proves V_CC-V_FF=A_R-A_B. The difference of these nonnegative terms has no predetermined sign. The same identity holds pointwise in speed; it is retained as algebra, not counted as an additional observed phenomenon.

For any fixed kappa, write the own-speed premiums S_F=V(F,kappa;v_H)-V(F,kappa;v_L) and S_C=V(C,kappa;v_H)-V(C,kappa;v_L). Expanding and regrouping gives S_F-S_C=M^kappa exactly. Thus the plan's H2 is the same factorial contrast as H1, not a second test or independent evidence. In the kappa=F case the committed term is V_CF, not V_CC; calling it mutual commitment would change the opponent condition and be incorrect.

All identities concern exact real-valued game values; reported floating-point identities are checked within the recorded numerical error. No global equality V(s)=one-stage-payoff(s) is asserted: player exchange implies oddness across exchanged states and zero only at appropriate symmetric fixed states.

## A reduced tracking theorem with explicit sufficient conditions

Let D be a random displacement in R^d with E||D||²<infinity and distribution independent of control authority v>=0. At each independent reset epoch choose correction u in the closed Euclidean ball ||u||<=v. Payoff is -||D-u||². The committed decision chooses u before observing D; the flexible decision observes D first. The action constraint is identical for the two information structures. There is no adjustment cost, delayed dynamics, state-dependent feasible set, strategic change in the disturbance law, or carry-over state.

Write mu=E[D], r=||mu|| and X=||D||. Completing the square gives committed minimum loss

    L_C(v)=E||D||²-||mu||²+(r-v)_+².

Pointwise projection onto the ball gives flexible minimum loss

    L_F(v)=E[(X-v)_+²].

Consequently the value of adaptation is A(v)=L_C(v)-L_F(v)>=0. It is absolutely continuous on bounded v intervals: the derivatives of each squared positive-part term are bounded by an integrable multiple of X+r+v. Almost everywhere,

    A'(v)=2{E[(X-v)_+]-(r-v)_+} >= 0.

For the inequality, z -> (||z||-v)_+ is convex (the maximum of the convex function ||z||-v and zero), so Jensen gives E[(||D||-v)_+] >= (||E D||-v)_+. Integrating the nonnegative derivative proves A(v_H)>=A(v_L). Any finite sum of independent reset-epoch payoffs with nonnegative fixed weights inherits this increasing-differences property. Strictness requires strict inequality on a set of v values of positive measure; degeneracy or saturation can give equality. No symmetry or Gaussian distribution is needed.

The proof supplies a transparent sufficient-condition example. It does NOT establish increasing differences for the full formation game, where drifts are endogenous, turning and history restrict reachability, speeds may be forced, and future observations change opponent responses. The proof is not claimed as novel without specialist literature review.

## Counterexample: nested capabilities alone do not suffice

Consider an exogenous hidden state taking two values with probability 1/2 each. Low capability permits actions a,b with rewards (1,0) and (0,1). High capability additionally permits c with rewards (1,1). A committed player chooses before seeing the state; a flexible player observes it first. Low-capability values are V_C=.5 and V_F=1, so adaptation value is .5. High-capability values are V_C=V_F=1, so adaptation value is 0. The policy sets are nested for each information structure, all flexibility values are nonnegative, yet M=-.5. The extra robust action substitutes for information. The same numbers arise against a zero-sum adversary selecting the hidden state before the flexible player's observation, with low committed mixing .5/.5.

This counterexample excludes the circular argument that greater feasible correction alone implies complementarity. A sufficient condition cannot simply assume the increasing returns one is trying to prove.

## Metric correction

For forced motion the current state may not belong to the next-epoch reachable set. Hence R_raw can be negative. The originally proposed Theta formula is not a boundedness theorem. v13 preserves signed R_raw and uses its positive part only in the explicitly defined bounded diagnostic. Neither clipping nor the reduced theorem constitutes empirical support for M>0.
