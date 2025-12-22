# Analytical probablistic approach in Chinese Mahjong

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

> Special hands are uncovered, while it is easy to account for them.

## Probablistic winning of the player

> **Simplification**: Ignoring the winning of the opponents, instead, we focus on finding the minimal rounds of the player to win, or, a weighted combination of round numbers and rewards. We will ignore the rewards for now.

The probability of winning round $t$ given the current hand $H_t$ and discard pool $A_t$ can be written as
$$
P_t(\text{WIN}|H_t)=P(x_t|W_t) P(W_t|A_t) w_{a_t}(\pi|H_t,x_t) \boldsymbol{1}(\pi)
$$


$P(x_t|W_t)$: the probability of drawing tile $x_t$ given the current remaining wall $W_t$.

$P(W_t|A_t)$: the probability of the current remaining wall $W_t$ given the discard pool $A_t$.

$w_{a_t}(\pi|H^+_t)$: ***Deterministic, optimization***; the hand formation given the optimal choice of the next hand $H^+_t$. 

* $H^+_t = (H_t \cup \{x_t\}) \setminus \{a_t\}$
* $A_t$ = $A_{t-1} \cup \{a_t\} \cup \{a_{t,\text{opponents}}\}$

$\boldsymbol{1}(\pi)$: ***Deterministic***; the indicator function of the winning hand $\pi$.

> Subtlety 1: As its simplest form, $A_t$ can be treated as a pool. In princeple, it is a time sequence of discarded tiles conditioned on players. One of the major difficulties of the problem is to model $P(W_t|A_t)$.

> Subtlety 2: Finding a winning formation $\pi$ is a combinatorial optimization problem. It can be impossible given certain $H_t$ and $x_t$. The other major difficulty of the problem is to find the optimal hand beyond current round. 





## Probablistic winning of the opponents



