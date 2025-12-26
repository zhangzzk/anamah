"""Bayesian Probabilistic Solver for Mahjong."""
import math
import random
from collections import Counter
from mahjong_core import SUITS, TILES, get_all_tiles, HandChecker
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
CONFIG = {"alpha": 5.0, "beta": 1.5, "gamma": 2.0, "lambda": 1.0, "n_particles": 50}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            CONFIG.update(json.load(f))
    except: pass

class DiscardModel:
    """Probabilistic model P(discard | Hand)."""
    alpha = CONFIG["alpha"]
    beta = CONFIG["beta"]
    gamma = CONFIG["gamma"]

    @staticmethod
    def calculate_energy(discard: str, hand: list[str]) -> float:
        """Calculate energy."""
        remaining_hand = list(hand)
        if discard in remaining_hand:
            remaining_hand.remove(discard)
            
        shanten = HandChecker.calculate_shanten(remaining_hand)
        s_val = max(0, shanten)
        term_shanten = DiscardModel.alpha * s_val
        
        suit_counts = Counter([t[0] for t in hand if t[0] in SUITS])
        main_suit = suit_counts.most_common(1)[0][0] if suit_counts else None
        is_main = (discard[0] == main_suit)
        
        term_main = DiscardModel.gamma if is_main else 0.0
        
        struct_val = 0
        d_suit, d_val = discard[0], int(discard[1:]) if discard[1:].isdigit() else 0
        
        neighbors = 0
        for t in hand:
            if t == discard: continue
            if t[0] == d_suit:
                try:
                    val = int(t[1:])
                    if abs(val - d_val) <= 2:
                        neighbors += 1
                except: pass
        if hand.count(discard) >= 2: neighbors += 1 
        
        if neighbors >= 2: struct_val = 2 
        elif neighbors == 1: struct_val = 1 
        else: struct_val = 0 
        
        term_struct = DiscardModel.beta * struct_val
        
        # return term_shanten + term_main + term_struct
        return term_shanten + term_main + term_struct

    @staticmethod
    def get_likelihoods(hand: list[str]) -> dict[str, float]:
        """Get likelihoods."""
        energies = {d: DiscardModel.calculate_energy(d, hand) for d in set(hand)}
        min_e = min(energies.values())
        exps = {d: math.exp(min_e - e) for d, e in energies.items()}
        total = sum(exps.values())
        return {d: val/total for d, val in exps.items()}

class OpponentFilter:
    """Particle filter."""
    def __init__(self, name: str, n_particles: int = None):
        self.name = name
        self.N = n_particles if n_particles is not None else CONFIG.get("n_particles", 50)
        self.particles = [] # List of list[str] (hands)
        self.weights = []
        
    def initialize(self, available_tiles: list[str]):
        """Init particles."""
        pool = list(available_tiles)
        random.shuffle(pool)
        self.particles = []
        self.weights = [1.0 / self.N] * self.N
        
        for _ in range(self.N):
            if len(pool) < 13:
                h = random.choices(TILES, k=13)
            else:
                h = random.sample(pool, 13)
            self.particles.append(sorted(h))

    def update(self, discard_tile: str, available_pool: list[str]):
        """Update particles."""
        new_weights = []
        for i, hand in enumerate(self.particles):
            if discard_tile not in hand:
                w = 1e-6
            else:
                probs = DiscardModel.get_likelihoods(hand)
                w = probs.get(discard_tile, 1e-6)
            new_weights.append(w * self.weights[i])
            
        total_w = sum(new_weights)
        if total_w == 0:
            self.weights = [1.0/self.N] * self.N
        else:
            self.weights = [w/total_w for w in new_weights]
            
        indices = random.choices(range(self.N), weights=self.weights, k=self.N)
        new_particles = [list(self.particles[i]) for i in indices]
        
        for hand in new_particles:
            if discard_tile in hand:
                hand.remove(discard_tile)
            
            draw = random.choice(TILES) 
            hand.append(draw)
            hand.sort()
            
        self.particles = new_particles
        self.weights = [1.0/self.N] * self.N

    def get_tile_counts(self) -> Counter:
        """Get tile counts."""
        total_counts = Counter()
        for hand in self.particles:
            total_counts.update(hand)
        return {k: v / self.N for k, v in total_counts.items()}


class BayesianMahjong:
    """Bayesian Agent."""
    
    def __init__(self, lambda_decay: float = None):
        self.total_tiles = Counter(get_all_tiles())
        self.LAMBDA_VAL = lambda_decay if lambda_decay is not None else CONFIG["lambda"]
        self.opponents = {
            "A": OpponentFilter("A"),
            "B": OpponentFilter("B"), 
            "C": OpponentFilter("C")
        }
        self.initialized = False
        self.shanten_cache = {}
        self.shanten_cache = {}

    def lazy_init(self, visible_tiles: list[str]):
        """Lazy init."""
        if self.initialized: return
        pool = list((self.total_tiles - Counter(visible_tiles)).elements())
        for model in self.opponents.values():
            model.initialize(pool)
        self.initialized = True

    def register_opponent_discard(self, who: str, tile: str):
        """Register discard."""
        if who in self.opponents and self.initialized:
            self.opponents[who].update(tile, [])

    def get_distribution(self, hand: list[str], visible_tiles: list[str], use_inference: bool) -> dict[str, float]:
        """Get wall probs."""
        counts = self.total_tiles.copy()
        for t in visible_tiles:
            counts[t] -= 1
        for t in hand:
            counts[t] -= 1
        if use_inference:
            if not self.initialized:
                self.lazy_init(visible_tiles + hand)
            for opp in self.opponents.values():
                opp_counts = opp.get_tile_counts()
                for t, avg_count in opp_counts.items():
                    counts[t] -= avg_count
        for t in counts:
            counts[t] = max(0.0, counts[t])
        total_remaining = sum(counts.values())
        if total_remaining <= 0:
            return {t: 0.0 for t in TILES}
        return {t: c / total_remaining for t, c in counts.items()}
        
    def get_unknown_distribution(self, hand: list[str], visible_tiles: list[str]) -> dict[str, float]:
        # Legacy Wrapper defaulting to inference
        return self.get_distribution(hand, visible_tiles, use_inference=True)

    def optimize_discard(self, hand_14: list[str], visible_pool: list[str], use_inference: bool = True, verbose: bool = False) -> tuple[str, float]:
        """Optimize discard."""
        wall_probs = self.get_distribution(hand_14, visible_pool, use_inference)
        
        if verbose:
            # Debug: Print Inference State
            sorted_probs = sorted(wall_probs.items(), key=lambda x: x[1], reverse=True)
            print(f"  [Bayes] Wall Inference (Top 5): {[(t, round(p,3)) for t, p in sorted_probs[:5]]}")
            dead_tiles = [t for t, p in wall_probs.items() if p < 0.001 and t not in visible_pool and t not in hand_14]
            if dead_tiles:
                print(f"  [Bayes] Suspected Dead Tiles (in Opp hands): {dead_tiles[:5]}...")

            # Calculate and Print Entropy of the Wall Belief
            entropy = 0.0
            for p in wall_probs.values():
                if p > 0:
                    entropy -= p * math.log(p)
            print(f"  [Bayes] Wall Entropy: {entropy:.4f}")

        best_tile, max_q = None, -1.0
        
        q_values = []
        for discard in set(hand_14):
            hand_minus = list(hand_14)
            hand_minus.remove(discard)
            q_val = 0.0
            active_probs = [(t, p) for t, p in wall_probs.items() if p > 0]
            
            for tile, prob in active_probs:
                v_score = self.hand_value_function_V(hand_minus + [tile], wall_probs)
                q_val += prob * v_score
                
            q_values.append((discard, q_val))
            
            if q_val > max_q:
                max_q = q_val
                best_tile = discard
                
        if verbose:
            # Sort Q values for display
            q_values.sort(key=lambda x: x[1], reverse=True)
            print(f"  [Bayes] Discard Computations: {[(t, round(q, 4)) for t, q in q_values[:3]]} ... Best: {best_tile}")
                
        return best_tile, max_q

    def calculate_shanten(self, hand: list[str]) -> int:
        h_key = tuple(sorted(hand))
        if h_key in self.shanten_cache:
            return self.shanten_cache[h_key]
        s = HandChecker.calculate_shanten(hand)
        self.shanten_cache[h_key] = s
        return s

    def hand_value_function_V(self, hand_14: list[str], wall_probs: dict[str, float]) -> float:
        """Evaluate hand V(H) with new formula (Optimized)."""
        h_val = self.calculate_shanten(hand_14)
        if h_val <= -1: return 100.0 
        
        # 1. Base Term
        V_base = math.exp(-self.LAMBDA_VAL * h_val)
        
        # 2. Efficiency Term (eta * Sum P(x|W))
        eta = CONFIG.get("eta", 0.5)
        term_efficiency = 1.0
        if eta > 0:
            efficiency_sum = 0.0
            # HEURISTIC: Only check tiles that could possibly affect shanten
            # Tiles with P > 0 that "touch" the hand
            touch_tiles = set()
            for t in hand_14:
                suit, val = t[0], int(t[1:])
                for dv in [-2, -1, 0, 1, 2]:
                    nv = val + dv
                    if 1 <= nv <= 9:
                        touch_tiles.add(f"{suit}{nv}")
            
            for t in touch_tiles:
                prob = wall_probs.get(t, 0.0)
                if prob > 0:
                    s_new = self.calculate_shanten(hand_14 + [t])
                    if s_new < h_val:
                        efficiency_sum += prob
            term_efficiency += eta * efficiency_sum
            
        # 3. Shape Term (kappa * Q_shape)
        kappa = CONFIG.get("kappa", 0.2)
        term_shape = 1.0
        if kappa > 0:
            counts = Counter(hand_14)
            # Simplistic shape score: Count pairs and triplets
            # But let's follow a robust measure: h_val already covers structure.
            # Let's use pairs + triplets as a refinement.
            pairs = sum(1 for c in counts.values() if c >= 2)
            trips = sum(1 for c in counts.values() if c >= 3)
            q_shape = pairs + trips
            term_shape = math.exp(kappa * q_shape)
            
        # 4. Spread Penalty (-mu * C_spread)
        mu = CONFIG.get("mu", 0.1)
        term_spread = 1.0
        if mu > 0:
            counts = Counter(hand_14)
            c_spread = 0
            for t in counts:
                suit, val = t[0], int(t[1:])
                has_neighbor = False
                for dv in [-2, -1, 1, 2]:
                    if f"{suit}{val+dv}" in counts:
                        has_neighbor = True
                        break
                if not has_neighbor and counts[t] < 2:
                     c_spread += 1
            term_spread = math.exp(-mu * c_spread)

        return V_base * term_efficiency * term_shape * term_spread
