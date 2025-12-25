<style>
body {
  font-family: 
    "Noto Sans CJK SC",
    "PingFang SC",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    sans-serif;
}
</style>


## Formulation

$$
\exists\,\pi:\; \sum_{k=1}^{4} M_k + P = H, \qquad |H| = 14, \qquad 
M_k \in \{\text{Chow}, \text{Pung}, \text{Kong}\}, \qquad P = \text{Pair}
$$

$H$: a winning hand  

$M_k$: the $k$-th meld (3 or 4 tiles)

* Chow: $(x,x+1,x+2)$ same suit  
* Pung: $(x,x,x)$  
* Kong: $(x,x,x,x)$  

$P$: one pair $(y,y)$

> A hand wins iff its 14 tiles can be partitioned into four valid melds plus one pair.  
> Special hands are uncovered, while it is easy to account for them.

---

## Probabilistic winning of the player

> **Remark**: Ignoring the winning of the opponents. We focus on finding the minimal rounds for the player to win, or a weighted combination of round numbers and rewards. Rewards are ignored for now.

The probability of winning at round $t$ given current hand $H_t$ and discard pool $A_t$ is written as
$$
\boxed{
P_t(\text{WIN}\mid H_t)
=
P(x_t\mid W_t)\;
P(W_t\mid A_t,H_t)\;
w_{a_t}(\pi\mid H_t,x_t)\;
\boldsymbol{1}(\pi)
}
$$

where:

- $P(x_t\mid W_t)$: probability of drawing tile $x_t$ from the remaining wall $W_t$  
- $P(W_t\mid A_t,H_t)$: probability of the remaining wall given discard history and player hand  
- $w_{a_t}(\pi\mid H_t,x_t)$: **deterministic optimization**, selecting the discard $a_t$ that leads to the optimal next hand  
- $\boldsymbol{1}(\pi)$: indicator of a valid winning formation

with
$$
H_t^+ = (H_t \cup \{x_t\}) \setminus \{a_t\}, 
\qquad
A_t = A_{t-1} \cup \{a_t\} \cup \{a_{t,\text{opponents}}\}.
$$

> **Remark**: $A_t$ is treated as a pool here. In principle, it is a time-ordered discard sequence conditioned on players.  
> One major difficulty is modeling $P(W_t\mid A_t,H_t)$.

> **Remark**: Finding a winning formation $\pi$ is a combinatorial optimization problem and may be impossible for certain $(H_t,x_t)$.

---

## Probabilistic remaining wall

Consider
$$
P(W_t\mid A_t,H_t).
$$

The remaining wall is
$$
W_t = T \setminus H_t \setminus A_t \setminus H_t^{i\neq我},
$$

where:

- $T$: fixed total tile set  
- $H_t$: known player hand  
- $A_t$: known discard history  
- $H_t^{i\neq我}$: unknown opponent hands

The problem reduces to the **opponent-hand likelihood**
$$
P(H_t^{i\neq我}\mid H_t,A_t).
$$

> **Remark**: Modeling the opponent-hand likelihood is the core challenge.  
> It depends on assumptions about opponent playstyle.

> **Simplification 2**: Opponents are independent and do not condition their decisions on each other.

Under this assumption,
$$
P(H_t^{i\neq我}\mid H_t,A_t)
=
\prod_{i\neq我} P(H_t^i\mid A_t^i),
$$
where $A_t^i$ is the discard history of opponent $i$.

---

## Opponent hand inference (Bayesian update)

For a fixed opponent $i$, let
$$
A_{1:t}^i = (a_1^i,\dots,a_t^i)
$$
denote the observed discard sequence.

The posterior over a hypothetical concealed hand $H$ is updated sequentially via
$$
\boxed{
P(H\mid A_{1:t}^i)
\propto
P(a_t^i\mid H)\;
P(H\mid A_{1:t-1}^i)
}
$$

> **Remark**: All modeling assumptions enter through the discard likelihood
$P(a_t^i\mid H)$.

---

## Toy discard likelihood model (average player)

We assume an average (non-expert) player whose discard choice is driven by
hand efficiency and simple structure.

### Approximate shanten (向听数)

Let $\widehat h(H)$ be a cheap approximation of shanten (向听数),
measuring distance to a winning hand (4 melds + 1 pair).

Define the shanten change for discarding tile $x$:
$$
\Delta h(x;H)
=
\widehat h(H\setminus\{x\})-\widehat h(H).
$$

Only relative values of $\Delta h$ are required.

---

### Structural features

For tile $x\in H$:

- $v_{\text{struct}}(x;H)$: structural value  
  (0 = isolated 孤张, 1 = partial group 搭子, 2 = meld or pair 面子/对子)

- $\mathbf{1}_{\text{main}}(x;H)$: indicator that $x$ belongs to the main suit (主做花色)

---

### Discard score and likelihood

Define a discard energy:
$$
E(x;H)
=
\alpha\,\Delta h(x;H)
+
\beta\,v_{\text{struct}}(x;H)
+
\gamma\,\mathbf{1}_{\text{main}}(x;H),
\qquad
\alpha,\beta,\gamma>0.
$$

The discard likelihood is
$$
\boxed{
P(\text{discard }x\mid H)
=
\frac{\exp[-E(x;H)]}
{\sum_{y\in H}\exp[-E(y;H)]}
}
$$

This stochastic model favors discarding isolated, off-suit tiles while suppressing
moves that increase shanten or destroy structure.

---

## Optimal discard decision (one-step optimization)

At round $t$, after drawing a tile, the player holds a 14-tile hand $H_t^+$ and must choose a discard
$$
a_t \in H_t^+.
$$

We assume that the posterior distributions
$$
P(H_t^i \mid A_t^i), \qquad i \neq 我
$$
over opponents’ concealed hands are already available from the inference step.

> **Simplification 3**: For now, we ignore opponent calling and deal-in risk, and consider only the effect of opponents
through the remaining wall distribution.

---

### Remaining wall distribution

Given the discard pool $A_t$, player hand $H_t$, and opponent posteriors,
the expected remaining count of tile $x$ in the wall is
$$
c_x
=
\mathbb E_{H_t^{i\neq我}}
\big[
\text{count of } x \text{ not in } H_t \cup A_t \cup H_t^{i\neq我}
\big].
$$

The draw probability is approximated by
$$
P(x \mid W_t)
=
\frac{c_x}{\sum_y c_y}.
$$

---

### Hand value function

> **Remark**: We define a cheap hand value function $V(H)$ that approximates the probability of winning soon. It favors ready hands, hands with many available waits, and hands closer to completion.

Let:
- $\widehat h(H)$ be the approximate shanten (向听数),
- $\mathcal W(H)$ be the wait set (等牌集合), i.e. tiles that complete the hand.

Define
$$
V(H)
=
\mathbf 1(\widehat h(H)=0)\;
\sum_{x\in\mathcal W(H)} P(x\mid W_t)
\;+\;
\mathbf 1(\widehat h(H)>0)\;
\exp\!\big(-\lambda\,\widehat h(H)\big),
\qquad \lambda>0.
$$

---

### One-step expectimax evaluation

For each discard candidate $a_t$, define
$$
H_t^- = H_t^+ \setminus \{a_t\}.
$$

The expected value of discarding $a_t$ is approximated by
$$
Q(a_t)
=
\sum_x P(x\mid W_t)\;
V\!\big(H_t^- \cup \{x\}\big)
$$

This corresponds to a one-step lookahead over the next draw, marginalizing over wall uncertainty.

The optimal discard decision is
$$
\boxed{
a_t^*
=
\arg\max_{a_t\in H_t^+}
Q(a_t)
}
$$

This strategy maximizes an effective winning probability while implicitly favoring earlier wins.


> **Remarks**: Summarizing the above optimizing strategy: 1. this is a myopic approximation to the optimal POMDP policy; 2. Opponent posteriors affect decisions only through $P(x\mid W_t)$ at this stage; 3. The framework is fully extensible: deal-in risk (放炮风险) and opponent winning probability can be added as penalty terms to $Q(a_t)$ in later refinements.






