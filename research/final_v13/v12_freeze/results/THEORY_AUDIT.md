# v12 mathematical audit and corrected statements

This is an AI-assisted author working draft. Definitions and proofs are independently reviewable; no journal decision or human verification is asserted.

## 1. Game and policy spaces

Fix one finite horizon T, one transition/reward model, initial complete LF histories, finite action grid, and an observation function. At a replan epoch a player chooses a sealed block; the opponent does not observe its current choice or future suffix. After execution, the history of physical observations and one's own actions is recalled. For the exact finite model we explicitly use public executed histories, reconstructible from the observed per-turn leader headings (turn changes are in [-60,60] degrees) and the station traces. Current simultaneous choices remain hidden. A different observation model would define a different extensive-form game.

Let P_i^C be the finite set of deterministic full-horizon sealed plans and P_i^F the finite set of deterministic contingent plans on the permitted information sets. A committed plan embeds into a flexible plan that ignores observations and remembers its private initial plan. The mixed strategic-form sets are Delta(P_i); correlated random choices across a player's own time are allowed. Perfect recall gives realization-equivalence to behavioral strategies, not independence of a committed plan's components. Existence of a zero-sum value follows from finite minimax. The information structure, rewards, transition and opponent class are held fixed when a single player's policy set is enlarged.

V(P_B,P_R)=max_{x in Delta(P_B)} min_{y in Delta(P_R)} x^T A y.

## 2. Proposition A: own flexibility cannot hurt

If P_B^C is embedded in P_B^F, every mixed committed strategy is an admissible mixed flexible strategy with identical payoff against every opponent strategy. For each x in Delta(P_B^C), its minimum against the fixed opponent class is unchanged by this embedding. Taking the maximum over the larger feasible set can only increase the value. Therefore V(FC)>=V(CC). Define F_B=V(FC)-V(CC)>=0. No capability monotonicity, public disclosure of sealed plans, or feedback uniqueness is assumed.

## 3. Proposition B: opponent flexibility cannot help Blue

For any fixed x, the minimum over Delta(P_R^F) is no greater than the minimum over its embedded subset Delta(P_R^C). Maximizing both sides over the same Blue class proves V(FF)<=V(FC). Define F_R=V(FC)-V(FF)>=0. This is the Red player's own payoff benefit along the specified comparison path, not a separately optimized social welfare measure.

## 4. Proposition C: decomposition, and its limitation

Subtract the two definitions: F_R-F_B=V(CC)-V(FF)=C_bilat. This is an algebraic identity. The sign of C_bilat is not determined by the two nonnegativity results.

The alternative path through CF gives F'_B=V(FF)-V(CF)>=0 and F'_R=V(CC)-V(CF)>=0, also C_bilat=F'_R-F'_B. Individual attribution is path-dependent in general. Its interaction term is I=V(FC)+V(CF)-V(FF)-V(CC)=F_B-F'_B=F_R-F'_R. Symmetric path averages are nonnegative and give the same bilateral difference. Report the comparison path explicitly; do not call either path a unique intrinsic value of flexibility.

With the plan's definition of disadvantaged/advantaged, Delta_F=sign(eta_r-1)*(F_R-F_B)=sign(eta_r-1)*C_bilat. Thus the proposed new direction test is algebraically the original bilateral range-sign test. Computing FC/CF can reveal magnitudes and interaction, but cannot turn a failed bilateral sign into a passed sign by re-labeling it. This is a limitation of the requested revival narrative, not a reason to omit negative cells.

## 5. Proposition D: exchange cancellation

Suppose S is an involution of the full state/history space and M is a bijection between corresponding feasible pure policies such that J(Ss,M p_R,M p_B)=-J(s,p_B,p_R), including the observation law, terminal reward and chance law if any. Assume the two players have exchange-corresponding C and F classes. The strategic-form payoff at Ss is -A(s)^T up to policy permutations. Finite minimax gives V_XY(Ss)=-V_YX(s). At an exchange-fixed initial state (including equivalence by a reward/dynamics-preserving spatial isometry), V_FF(s)=V_CC(s)=0 and V_FC(s)=-V_CF(s). Hence F_B=F_R and C_bilat=0. Equal hardware alone is not sufficient; the initial histories and observation structures must also be fixed under the exchange isometry.

For the prescribed initial LF states: a half-turn about the leader midpoint exchanges head_on and crossing formations; parallel uses reflection in the line parallel to both headings through their midpoint, together with negating turn rates. Reflection additionally requires the kernel's port/starboard symmetry. Tests verify each premise before using common exchange-mapped support sets. No numerical skew projection is performed.

## 6. Correct replacement for the v11 all-state degeneracy theorem

For a finite simultaneous zero-sum Markov game with odd stage reward and equivariant dynamics, corresponding feasible actions, and exchange-odd terminal value, backward induction proves V_t(Ss)=-V_t(s). Indeed the continuation matrix at Ss is the negative transpose (with action permutations) of the matrix at s, because the induction hypothesis applies to S F(s,a,b). The value of -A^T is -val(A); adding odd immediate reward completes induction. At fixed states V_t(s)=0. This argument applies also to an interval reward r(s,a,b) if it is odd under exchange of state and actions.

For infinite horizon, bounded rewards and 0<gamma<1 make the mixed Bellman operator a gamma-contraction in sup norm. It commutes with the exchange-odd transformation. The unique fixed point is exchange-odd. This proves zero value at fixed states, not V(s)=ell(s) everywhere.

Counterexample to v11's stronger assertion: state space {-1,+1}, S(s)=-s, one action for each player, F(s)=s, ell(s)=s, zero terminal reward. Oddness and equivariance both hold. The two-stage value is 2s, not s; the infinite discounted value is s/(1-gamma). The v11 proof erroneously replaces F(Ss,v,u) with F(s,v,u). Kinematic asymmetry can also destroy fixed-state exchange symmetry when capability labels are part of the state.

## 7. Numerical certificates: what can be bounded

For the finite open-loop matrix and candidate mixtures x,y, LB=min_j(x^T A)_j and UB=max_i(Ay)_i bound its equilibrium value. This remains true when both supports are restricted, provided best responses range over the full finite action-plan space. The restricted matrix value alone is neither a valid full-game lower nor upper bound. LP failure or an unmet cap returns an explicit failure, never a fallback equilibrium.

Summing these open-loop gaps across receding epochs does NOT bound error relative to a feedback equilibrium. The future game used by an open-loop oracle differs from the feedback continuation; that structural error is unmeasured. v12 reports the sum only as a local residual diagnostic.

For exact block backward induction, each matrix contains the correct continuation value on every branch. If each local numerical minimax value has error at most e_t(s), the sup-norm nonexpansiveness of matrix value propagates an error bound <= maximum-path sum of these local errors (discounted when appropriate). The implemented conservative budget sums the maximum measured local primal-dual gap at each block depth. This is a numerical finite-game certificate conditional on the supplied floating-point payoff matrix, not a rigorous interval-arithmetic bound on continuous dynamics or arbitrary roundoff.

## 8. Cadence ordering and player mirrors

Committed h=T policies embed in fully flexible h=1 policies. Intermediate cadences are nested only when their decision-time sets refine one another. h=2 and h=3 are not ordered refinements on T=6, so monotonic marginal values between those cadences are not implied. Simultaneously restricting both players never supplies a universal monotonic sign.

Swapping capabilities exchanges absolute ranges and speeds. Merely pairing eta_r=0.8 with 1.2 is NOT an exact player-swap pair; inverse ratios and the reference scale must be transformed consistently. Metamorphic tests swap actual kernel objects, histories and speeds, not approximate ratio labels.

## 9. Scope of mathematical novelty

Nested-set monotonicity, finite minimax, sequence form and exchange cancellation are established principles. Their application and diagnostic role can support this formation-game study; A-C and the decomposition alone are not novel Q1-level mathematical contributions. Any broader novelty claim needs a substantive new result or controlled application evidence and specialist literature review. No quality tier is certified by the number of propositions or figures.
