# Baysian Inference for Chinese Mahjong

## Formulation

$$
\exists\,\pi:\; \sum_{k=1}^{4} M_k + P = H, \qquad |H| = 14, \qquad M_k \in \{\text{Chow}, \text{Pung}, \text{Kong}\}, \qquad P = \text{Pair}
$$

$H$: a winning hand

$M_k$: the k-th meld (3 or 4 tiles)

* Chow: (x,x+1,x+2) same suit
* Pung: (x,x,x)
* Kong: (x,x,x,x)

$P$: one pair (y,y)

> A hand wins iff its 14 tiles can be partitioned into four valid melds plus one pair.

(Special hands uncovered.)

## Probablistic winning conditions

$$
P_t(\text{WIN}|H_t)=P(x_t|W_t) P(W_t|A_t) w_{a_t}(\pi|H^+_t) \boldsymbol{1}(\pi)
$$


$P_t(\text{WIN}|H_t)$: ***Probabilistic***; the probability of winning round $t$ given the current hand $H_t$ and discard pool $A_t$.

$P(x_t|W_t)$: ***Probabilistic***; the probability of drawing tile $x_t$ given the current remaining wall $W_t$.

$P(W_t|A_t)$: ***Probabilistic***; the probability of the current remaining wall $W_t$ given the discard pool $A_t$.

$w_{a_t}(\pi|H^+_t)$: ***Deterministic, optimization***; the hand formation given the optimal choice of the next hand $H^+_t$. 

* $H^+_t = (H_t \cup \{x_t\}) \setminus \{a_t\}$
* $A_t$ = $A_{t-1} \cup \{a_t\} \cup \{a_{t,\text{opponents}}\}$

$\boldsymbol{1}(\pi)$: ***Deterministic***; the indicator function of the winning hand $\pi$.

