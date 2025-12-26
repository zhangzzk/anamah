"""
Bayesian Probabilistic Solver for Mahjong.
Implements the Analytical Mahjong framework: 
1. Infers remaining wall distribution P(x|W).
2. Calculates hand value V(H) based on heuristic shanten and wait probabilities.
3. Optimizes discard Q(a_t) via one-step Expectimax lookahead.
"""
import math
import random
from collections import Counter
from mahjong_core import SUITS, TILES, get_all_tiles, HandChecker

class DiscardModel:
    """Probabilistic model P(discard | Hand)."""
    
    @staticmethod
    def calculate_energy(discard: str, hand: list[str]) -> float:
        """
        E(x; H) = alpha * delta_shanten + beta * struct_val + gamma * main_suit
        We use a simplified proxy since full shanten is expensive.
        """
        # Feature 1: Main Suit (We assume the suit with most tiles is Main)
        suit_counts = Counter([t[0] for t in hand if t[0] in SUITS])
        if not suit_counts:
            main_suit = None
        else:
            main_suit = suit_counts.most_common(1)[0][0]
            
        is_main = (discard[0] == main_suit)
        
        # Feature 2: Isolation (Is it part of a pair or sequence?)
        # Simple check: Does hand have neighbors?
        has_neighbor = False
        try:
            d_suit, d_val = discard[0], int(discard[1:])
            for t in hand:
                if t == discard: continue
                if t[0] == d_suit:
                    val = int(t[1:])
                    if abs(val - d_val) <= 2:
                        has_neighbor = True
                        break
        except:
            if hand.count(discard) > 1: has_neighbor = True
            
        # Energy Score (Higher Score = Better Discard Candidate = Low Energy)
        # We want P ~ exp(Score).
        score = 0.0
        if not is_main: score += 2.0
        if not has_neighbor: score += 1.5
        
        return score

    @staticmethod
    def get_likelihoods(hand: list[str]) -> dict[str, float]:
        """Returns P(d | hand) for all d in hand."""
        # Calculate scores
        scores = {d: DiscardModel.calculate_energy(d, hand) for d in set(hand)}
        # Softmax
        max_s = max(scores.values())
        exps = {d: math.exp(s - max_s) for d, s in scores.items()}
        total = sum(exps.values())
        return {d: val/total for d, val in exps.items()}

class OpponentFilter:
    """Particle Filter for one opponent."""
    def __init__(self, name: str, n_particles: int = 50):
        self.name = name
        self.N = n_particles
        self.particles = [] # List of list[str] (hands)
        self.weights = []
        
    def initialize(self, available_tiles: list[str]):
        """Draw random 13-tile hands from available pool."""
        pool = list(available_tiles)
        random.shuffle(pool)
        self.particles = []
        self.weights = [1.0 / self.N] * self.N
        
        for _ in range(self.N):
            # Sample 13 tiles with replacement from pool approximation
            if len(pool) < 13:
                h = random.choices(TILES, k=13)
            else:
                h = random.sample(pool, 13)
            self.particles.append(sorted(h))

    def update(self, discard_tile: str, available_pool: list[str]):
        """
        1. Weight particles by P(discard | particle_hand).
        2. Resample.
        3. Transition (Remove discard from hand, Draw new tile).
        """
        # 1. Reweight
        new_weights = []
        for i, hand in enumerate(self.particles):
            if discard_tile not in hand:
                w = 1e-6
            else:
                probs = DiscardModel.get_likelihoods(hand)
                w = probs.get(discard_tile, 1e-6)
            new_weights.append(w * self.weights[i])
            
        # Normalize
        total_w = sum(new_weights)
        if total_w == 0:
            self.weights = [1.0/self.N] * self.N
        else:
            self.weights = [w/total_w for w in new_weights]
            
        # 2. Resample
        indices = random.choices(range(self.N), weights=self.weights, k=self.N)
        new_particles = [list(self.particles[i]) for i in indices]
        
        # 3. Transition: Remove Discard, Add Random Draw
        for hand in new_particles:
            if discard_tile in hand:
                hand.remove(discard_tile)
            
            # Simulate Fill (Draw 1) form pool
            draw = random.choice(TILES) 
            hand.append(draw)
            hand.sort()
            
        self.particles = new_particles
        self.weights = [1.0/self.N] * self.N

    def get_tile_counts(self) -> Counter:
        """Return expected count of each tile held by this opponent."""
        total_counts = Counter()
        for hand in self.particles:
            total_counts.update(hand)
        return {k: v / self.N for k, v in total_counts.items()}


class BayesianMahjong:
    """Agent that estimates probabilities and suggests optimal moves."""
    
    def __init__(self, lambda_decay: float = 1.0):
        self.total_tiles = Counter(get_all_tiles())
        self.LAMBDA_VAL = lambda_decay
        self.opponents = {
            "A": OpponentFilter("A"),
            "B": OpponentFilter("B"), 
            "C": OpponentFilter("C")
        }
        self.initialized = False

    def lazy_init(self, visible_tiles: list[str]):
        """Initialize opponent filters if not done."""
        if self.initialized: return
        # Initial pool for particles
        # We need a rough count of available tiles to sample from
        # Total - Visible
        pool = list((self.total_tiles - Counter(visible_tiles)).elements())
        for model in self.opponents.values():
            model.initialize(pool)
        self.initialized = True

    def register_opponent_discard(self, who: str, tile: str):
        """Called by game_tracker when opponent discards."""
        if who in self.opponents and self.initialized:
            self.opponents[who].update(tile, [])

    def get_distribution(self, hand: list[str], visible_tiles: list[str], use_inference: bool) -> dict[str, float]:
        """
        Calculates P(x | W_t).
        If use_inference=True, subtracts E[Opponents] from unknown.
        If use_inference=False, assumes unknown is uniform.
        """
        # 1. Total counts
        counts = self.total_tiles.copy()
        
        # 2. Subtract Visible and Hand (Always)
        for t in visible_tiles:
            counts[t] -= 1
        for t in hand:
            counts[t] -= 1
            
        # 3. Optional: Subtract Inferred Opponent Hands
        if use_inference:
            if not self.initialized:
                self.lazy_init(visible_tiles + hand)
            for opp in self.opponents.values():
                opp_counts = opp.get_tile_counts()
                for t, avg_count in opp_counts.items():
                    counts[t] -= avg_count
        
        # 4. Normalize
        for t in counts:
            counts[t] = max(0.0, counts[t])
            
        total_remaining = sum(counts.values())
        if total_remaining <= 0:
            return {t: 0.0 for t in TILES}
            
        return {t: c / total_remaining for t, c in counts.items()}
        
    def get_unknown_distribution(self, hand: list[str], visible_tiles: list[str]) -> dict[str, float]:
        # Legacy Wrapper defaulting to inference
        return self.get_distribution(hand, visible_tiles, use_inference=True)

    def optimize_discard(self, hand_14: list[str], visible_pool: list[str], use_inference: bool = True) -> tuple[str, float]:
        """
        Calculates Q(a_t) for all discards and returns the optimal one.
        Q(a_t) = Sum_{x} P(x|W) * V(H_minus + x).
        """
        wall_probs = self.get_distribution(hand_14, visible_pool, use_inference)
        best_tile, max_q = None, -1.0
        
        for discard in set(hand_14):
            hand_minus = list(hand_14)
            hand_minus.remove(discard)
            q_val = 0.0
            active_probs = [(t, p) for t, p in wall_probs.items() if p > 0]
            
            for tile, prob in active_probs:
                v_score = self.hand_value_function_V(hand_minus + [tile], wall_probs)
                q_val += prob * v_score
                
            if q_val > max_q:
                max_q = q_val
                best_tile = discard
                
        return best_tile, max_q

    def calculate_shanten(self, hand: list[str]) -> int:
        if HandChecker.is_winning(hand):
            return -1
        
        present_suits = {t[0] for t in hand if t[0] in SUITS}
        penalty = 0
        if len(present_suits) > 2:
            counts = Counter(t[0] for t in hand if t[0] in SUITS)
            penalty = min(counts.values()) * 2

        if penalty == 0:
            for t in TILES:
                 if HandChecker.is_winning(hand + [t]): 
                     return 0
        return 1 + penalty

    def hand_value_function_V(self, hand_14: list[str], wall_probs: dict[str, float]) -> float:
        h_val = self.calculate_shanten(hand_14)
        
        if h_val == -1: return 10.0
        if h_val == 0: # Tenpai
            max_wait_prob = 0.0
            unique_tiles = set(hand_14)
            for d in unique_tiles:
                temp_hand = list(hand_14)
                temp_hand.remove(d)
                current_prob = 0.0
                for w, prob in wall_probs.items():
                    if prob > 0 and HandChecker.is_winning(temp_hand + [w]):
                        current_prob += prob
                max_wait_prob = max(max_wait_prob, current_prob)
            return max_wait_prob
            
        return math.exp(-self.LAMBDA_VAL * h_val)

