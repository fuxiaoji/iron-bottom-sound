# Sealed-block calendar games: mathematical record

Status: complete derivations for the stated finite model; author-workspace draft, not independent specialist verification. Numerical tests corroborate implementation and are not the proofs below. Prior concepts (minimax, perfect recall, column generation, branch-and-bound and information monotonicity) are credited in LITERATURE_POSITIONING.md.

## 1. Model and definitions

There are T simultaneous action epochs, finite state-independent action menus of size b, known initial state and deterministic causal transitions. A terminal payoff A(i,j) is a bounded function of both COMPLETE executed action histories; it may include any accumulated intermediate rewards. No Markov compression is assumed. An update calendar S is a subset of {1,...,T−1}; t=0 is compulsory and free. At t in {0} union S, the player observes both executed prefixes and selects the entire action block through the next own update. Opponents do not see current actions or future sealed commands. At the next update all preceding own commands have finished; their values and all executed observations are remembered. Calendars are publicly fixed parameters, not strategic hidden signals.

A pure policy maps each feasible update information set to a legal block. Mixed policies randomize over such maps. This is a finite perfect-recall extensive-form game. P_S denotes the maximizer's mixed-policy set; Q_R the minimizer's fixed-calendar policy set. The value is V(S,R)=max_p min_q E[A]. Throughout comparisons, R and A remain fixed. The finite minimax theorem supplies existence and equality of max-min and min-max.

## 2. Inclusion and endpoints (standard foundation)

**Proposition 1.** If S is contained in U, then V(S,R)<=V(U,R). V(empty,R) is the committed value; V({1,...,T−1},R) is the flexible value. Consequently W_K=max_{|S|<=K}V(S,R) is nondecreasing.

**Proof.** Given a pure S-policy, at the first U-update within an S-block choose the relevant portion of the block the S-policy would have chosen. At added updates, ignore new observations and continue that block. Remembering the original block (or equivalently the sampled pure policy) is allowed. This constructs an outcome-equivalent U-policy against every q in the SAME Q_R. Extend linearly to mixed policies. Taking the maximum over a superset proves the inequality. Endpoints follow from one initial block versus one action per update. Maximizing over a larger budget family proves W monotonicity. No conclusion compares different physical speeds or different opponent calendars. □

This proof does not establish positive complementarity, strict improvement, submodularity, novelty, or a publication tier.

## 3. Exact sealed-block sequence form

For own update t with next update e, an information set is (t,i_t,j_t), where i_t and j_t encode the executed prefixes. It has b^(e−t) block actions. Its realization-flow constraint is sum of child realization weights = its parent sequence weight. The parent is the block selected at the previous own update p, together with the observed prefixes through p; the own part of the executed prefix through t identifies the entire selected parent block. Thus a player does not forget its prior selected commands. The root realization weight is one.

For terminal paths i,j, select each player's last block sequence using its own last-update prefixes and complete final block. Attach A(i,j) to those two terminal sequences. Summing bilinear realization products reproduces exactly the probability of every terminal history. Standard sequence-form primal/dual LP therefore solves this finite game. Opponent suffixes never enter information-set IDs; branching inside a sealed block would represent a different game.

## 4. Common-update decomposition

**Proposition 2.** At any common update c in S intersect R, every executed history prefix defines a proper subgame. Solving the subgames backwards gives the exact root value without merging distinct histories.

**Proof.** At c both players' previous blocks have ended. The complete executed prefix is public; no unexecuted private command remains from either player. Each player knows its information set and all decision nodes that share it lie inside the same prefix subtree. Consequently no information set crosses the proposed cut. The continuation game at each prefix can be replaced by its minimax value: a player can guarantee that value within the subgame, and the opponent can bound it from above. Combining these local guarantees with the preceding block game proves equality. Apply induction over the common boundaries backwards. In particular, a Blue update is not a valid cut if Red still holds an unfinished committed block. □

**Error corollary.** If every replacement at level l has uniform error at most e_l, then root error is at most sum_l e_l. For any fixed p,q, a uniform payoff perturbation e changes expected payoff by at most e; taking min and max preserves the bound. Induction proves the sum. This is an error propagation statement, not a guarantee that floating-point errors equal zero.

## 5. Exact history-dependent best-response pricing

For a fixed causal opponent policy q, let C_q(j|i) be its realization probability of opponent path j when the own path i is externally fixed. This is a counterfactual conditional law, not an assumption that the opponent actually commits. Define B(i,j)=A(i,j) C_q(j|i). For a committed opponent, C_q(j|i)=q_j.

Start with H_T(i,j)=B(i,j). For successive own block boundaries t<e, reduce

    H_t(i_t,j_t) = max_a sum_z H_e(i_t a, j_t z),

where a is a whole own block and z the opponent's block of executed actions over [t,e). Store an argmax for every pair of executed prefixes. Ties use the first lexicographic action. Never maximize separately for different unobserved z.

**Proposition 3.** The recurrence yields the value and a feasible pure best response against q over the complete own-calendar policy space.

**Proof.** Counterfactual opponent probability up to t depends only on the executed prefix, by causality. It is constant with respect to the yet-unchosen own block. Conditional on that prefix and block, all opponent continuations must be summed before a command is selected. At the next own update, continuations can be chosen separately for each observed prefix; the induction hypothesis already maximizes these branches. Thus the displayed sum-then-max is precisely the feasible decision at t. Backward induction proves optimality at the root. Keeping unnormalized prefix weights avoids division by zero; decisions at zero-weight histories are arbitrary but legal. Recorded argmax blocks depend only on observed prefixes, proving feasibility. □

For a mixture of pure causal opponent maps r_m(i), C_q(j|i)=sum_m w_m 1{r_m(i)=j}. Every positive mixture weight is retained. The history payoff matrix is not replaced by a pose cache. Direct counterfactual DP costs O(b^(2T)) arithmetic up to a geometric-series factor and O(b^(2T)) memory; it does not enumerate all contingent policies. Terminal payoff generation and the outer number of oracle iterations remain additional costs.

## 6. Oracle bounds and column generation (standard framework, specialized pricing)

Against committed Red, retain all b^T opponent plans and a finite set of Blue contingent policies. Solve their rectangular matrix game to obtain a feasible mixture x and opponent law q. Let L=min_j sum_m x_m A(policy_m(j),j). Let U be the full best response from Proposition 3 against q. Then L<=V(S,C)<=U: the first is a feasible guaranteed policy payoff, and the second fixes a feasible opponent policy in the minimax expression.

If U−L exceeds the requested tolerance, append a maximizing contingent policy. In exact arithmetic it cannot already be among the restricted policies at a positive gap. There are finitely many pure policies, so exact generation terminates finitely. This is not a polynomial iteration bound. Floating-point implementations report full-response intervals, residual/repair details when using LP realization plans, padding and stall/time limits. A restricted two-sided matrix value alone is not a full-game bound.

For Red F, common-update reduction leaves Blue committed versus Red flexible blocks. Exchanging the minimizer/maximizer inside that algebraic subgame applies the same exact pricing routine. The physical player-swap audit still uses an independently generated physical matrix.

## 7. Calendar-transfer and deletion certificate

**Proposition 4 (opponent reuse).** Any causal opponent policy feasible for the fixed calendar R remains feasible when only the maximizer's calendar changes. For a pool Q0 of such policies,

    V(S,R) <= min_{q in Q0} BR_S(q).

**Proof.** The opponent's observable variables (executed prefixes), update opportunities and legal action menu are unchanged. Its old map can ignore the new publicly announced calendar and execute the same history-based map. Current and future sealed commands are absent from that map. Each q therefore belongs to the target Q_R, and fixing q gives a minimax upper bound. The minimum of valid bounds is valid. Adding response opportunities to S gives an upper bound for every calendar contained in S by Proposition 1. □

**Proposition 5 (constructive coarsening).** Suppose S' is contained in S and actions have state-independent legal menus. Given a mixture of pure S-policies, construct each S'-block by completing the observed opponent prefix with a fixed hypothetical straight-action suffix and taking the corresponding block from the source pure policy's output path. Preserve the original mixture weights. The resulting policy is feasible for S'. If L' is its value against a full opponent best response and U bounds V(S,R), then

    0 <= V(S,R)−V(S',R) <= U−L'.

**Proof.** Each constructed block uses only the actual opponent prefix available at the S'-update, a predetermined completion and the privately sampled source-policy index. It never reads the actual future suffix. Its actions remain legal because menus do not depend on the shadow trajectory's state. This gives a feasible mixed S'-policy, although it may perform poorly. Therefore L'<=V(S',R). Combine with V(S,R)<=U and inclusion. The hypothetical path may differ from the actual one; no claim that they coincide is required. □

This constructive upper bound may be loose. Its empirical tightness and utility for pruning are research questions, not consequences of feasibility. For state-dependent action constraints this construction requires a separate legal-action repair and cannot be applied unchanged.

**Behavioral construction used for realization-plan outputs.** A full-update realization plan can instead be expressed as conditional action kernels, assigning uniform legal actions when the incoming realization weight is zero. At a coarse update keep the actual own and opponent prefixes. For every possible own block multiply the source kernels along that block and a fixed hypothetical straight opponent continuation. Summing over all own blocks gives one by iterated normalization. This is consequently a feasible distribution over coarse blocks and the same full-response loss inequality applies. Unlike preserving a source root mixture, this construction specifies a new behavioral policy; the two constructions are labeled separately. With the full update calendar retained, the kernels reproduce the original realization plan exactly. The implementation uses this exact behavioral construction uniformly for final deletion-certificate experiments.

## 8. Budget search and stopping

A search node fixes included updates I, excluded updates E and leaves the rest undecided. Every feasible descendant lies inside U={1,...,T−1}\E. Any upper bound on V(U,R), including a transferred response bound, bounds all descendants. Any evaluated feasible calendar of size <=K supplies an incumbent lower bound L*. Prune a node only when its upper bound <=L*+epsilon. Nodes with |I|>K are infeasible; when |I|=K only I needs evaluation; when |U|<=K inclusion means U dominates its descendants.

**Proposition 6.** When the finite search exhausts or prunes every node, its returned calendar has value at least L*, and W_K<=max of all final-node upper bounds. If their difference is <=epsilon, the returned solution is epsilon-optimal.

**Proof.** Binary inclusion/exclusion covers all subsets. Infeasible nodes contain no admissible calendar; both terminal reductions preserve a dominating admissible calendar by inclusion. Each remaining candidate lies in an evaluated or safely bounded terminal node. The largest upper bound therefore bounds its value. The incumbent is feasible and its lower bound is valid. Subtraction proves the certificate. □

The proof makes no submodularity assumption. It also gives no universal strict improvement over uniform calendars and no universal speedup versus enumeration.

## 9. Submodularity counterexample and a sufficient special case

Let T=3, both action menus {0,1}, and Red commit its path. The payoff is 1{b_1=r_0 and b_2=r_1}; b_0 and r_2 do not affect it. Candidate updates are 1 and 2. Values for empty,{1},{2},{1,2} are respectively 1/4,1/2,1/2,1.

**Proof.** Without updating, independent uniform guesses for b_1,b_2 guarantee 1/4 against every Red path, and independent uniform r_0,r_1 limit every Blue policy to 1/4. With only update 1, match b_1 to the observed r_0 and uniformly guess b_2; independent uniform r_1 limits the guarantee to 1/2. With only update 2, uniformly guess b_1 and match b_2 to observed r_1; uniform r_0 limits it to 1/2. With both updates, both matches are certain. The marginal value of update 2 rises from 1/4 to 1/2 when update 1 is present, violating submodularity. □

This is a counterexample in the general finite history-payoff class, not proof that every physical formation instance violates submodularity. The physical dataset will be checked separately with interval-aware second differences.

**Sufficient special case.** If each candidate update concerns an independent reset game, rewards add, feasible policies factor across reset games, and neither dynamics nor information nor an opponent resource constraint couples those games, the total minimax value is the sum of their values. Select a product of equilibrium strategies to achieve the sum as both lower and upper guarantees. Each update then adds its own fixed nonnegative information premium, so the set function is modular (and submodular). History-dependent formation dynamics generally violate these reset assumptions. This special case is explanatory and not presented as a novel generic greedy guarantee.

## 10. Corrections to older claims and decision reporting

Exchange-equivariant dynamics and antisymmetric payoff imply V(exchange(s))=−V(s), by exchanging feasible strategies. They imply zero at exchange-fixed states (including a verified spatial isometry), not V(s)=one-step payoff(s) for every state. Absorbing exchanged states s=±1 with one-step reward s over two steps have V(s)=2s, a direct counterexample to the old claim. Pure max-min of a skew matrix need not be zero; mixed minimax is essential.

For rho in (0,1), retaining rho of full adaptation is W_K>=rho V_full+(1−rho)V_empty. Certify this by L_K−rho U_full−(1−rho)U_empty>=0; rule it out by U_K−rho L_full−(1−rho)L_empty<0. Report possible and certified minimum budgets separately when intervals straddle a threshold. If adaptation is too small to resolve relative to numerical scale, report absolute loss instead. These are deterministic finite-game intervals, not population confidence intervals or continuous-control error bounds.

## 11. Public-interval loss bound and budget allocation (opponent F only)

Let v_t(h) be the continuation value with both players updating every epoch at complete public prefix h. For t<e define b_{t,e}(h) as the local game value with Blue sealed over [t,e), Red fully updating, and terminal reward v_e. Put d(t,e)=max_h [v_t(h)−b_{t,e}(h)]. Inclusion gives nonnegativity and d(t,t+1)=0. The maximum covers every prefix, including histories with zero probability under a particular equilibrium.

**Proposition 7.** For calendar boundaries 0=t_0<...<t_m=T,

    0 <= V(F,F)−V({t_1,...,t_{m−1}},F) <= sum_j d(t_j,t_{j+1}).

**Proof.** At each chosen boundary and observed prefix, use a maximizing block policy of the local game defining b. Suppose the remaining stitched policy guarantees v_e(h')−D uniformly at all successor prefixes. The uniform payoff-perturbation argument reduces the local guarantee by at most D, so the preceding block guarantees b_{t,e}(h)−D >= v_t(h)−d(t,e)−D. Backward induction from the terminal boundary proves the result. Policies are feasible because each block is selected from the actual public prefix, and Red has no unexecuted private block across a cut. The same argument does not apply to a committed opponent with a crossing private suffix. □

Minimizing the sum of edge costs on the acyclic epoch graph from 0 to T with at most K+1 edges gives a calendar with a conservative performance guarantee. Use dynamic programming for each exact edge count and then minimize over counts up to K+1; no triangle inequality or monotone bound for exact counts is assumed. All budgets require O(T³) arithmetic **after** the edge map exists. Full-history value-tree and local-game preprocessing are exponential in T and must be included in computational comparisons. A sufficient budget from this bound is not a proof of minimality for the true value threshold.

Numerically, use a uniform full-tree interval and a lower bound for every local block value (including terminal-error propagation). Each edge upper bound is max_h(U_v−L_b), clipped below at zero; singleton edges use the identical-game identity. Sum upper bounds and take a minimum only across complete feasible paths. Partial edge maps never become complete certificates. The construction is a specialization of standard minimax perturbation and shortest-path arguments. Novel practical value depends on measured tightness and total cost.

Implementation and two independent binary T3 checks are fixed by INTERVAL_BOUND_FREEZE.json. Development outcomes were already viewed when this additional method was fixed; frozen-test outputs were absent. This timing is disclosed in INTERVAL_BOUND_PROTOCOL.md.
