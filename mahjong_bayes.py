"""
Bayesian Probabilistic Solver for Mahjong.
Implements the Analytical Mahjong framework: 
1. Infers remaining wall distribution P(x|W).
2. Calculates hand value V(H) based on heuristic shanten and wait probabilities.
3. Optimizes discard Q(a_t) via one-step Expectimax lookahead.
"""
import math
from collections import Counter
from mahjong_core import SUITS, TILES, get_all_tiles, HandChecker

class BayesianMahjong:
    """Agent that estimates probabilities and suggests optimal moves."""
    
    def __init__(self, lambda_decay: float = 1.0):
        self.total_tiles = Counter(get_all_tiles())
        self.LAMBDA_VAL = lambda_decay

    def get_unknown_distribution(self, hand: list[str], discards: list[str]) -> dict[str, float]:
        """
        Calculates P(x | W_t) = count(x in Unknown) / count(Total Unknown).
        Unknowns = Total - (Hand + Discards).
        """
        visible = Counter(hand) + Counter(discards)
        unknowns = self.total_tiles.copy()
        
        for t, count in visible.items():
            unknowns[t] = max(0, unknowns[t] - count)
            
        total_unknown = sum(unknowns.values())
        if total_unknown == 0:
            return {t: 0.0 for t in TILES}
            
        return {t: c / total_unknown for t, c in unknowns.items()}

    def calculate_shanten(self, hand: list[str]) -> int:
        """
        Heuristic evaluation of 'Shanten' (distance to win).
        Includes penalty for violating the 'Max 2 Suits' constraint.
        
        Returns:
            -1: Winning
             0: Tenpai (Ready)
            >0: Approximate distance steps
        """
        if HandChecker.is_winning(hand):
            return -1
            
        # Suit Penalty
        present_suits = {t[0] for t in hand if t[0] in SUITS}
        penalty = 0
        if len(present_suits) > 2:
            # Penalize by size of the smallest suit (cost to flush)
            counts = Counter(t[0] for t in hand if t[0] in SUITS)
            penalty = min(counts.values()) * 2

        # Tenpai Check (Simple 1-step search)
        # Note: If penalized, we assume not Tenpai for a *valid* win.
        if penalty == 0:
             # Optimization: If existing structure implies Tenpai
             # Checking actual 'wait' availability is expensive but accurate.
             # Here we assume a check of "can we win in 1 draw" logic.
            for t in TILES:
                 if HandChecker.is_winning(hand + [t]): # Naive check for Tenpai
                     return 0
                     
        return 1 + penalty

    def hand_value_function_V(self, hand_14: list[str], wall_probs: dict[str, float]) -> float:
        """
        V(H) = P(Win Next) if Tenpai else exp(-lambda * distance).
        Evaluates the potential of a 14-tile hand *after* a draw.
        """
        h_val = self.calculate_shanten(hand_14)
        
        if h_val == -1: # Already Winning
            return 10.0
            
        if h_val == 0: # Tenpai (Ready)
            # Value = Sum of probabilities of drawing winning tiles
            # We must simulate discarding to find the waits?
            # Actually, hand_14 isn't "waiting"—it needs a discard to become waiting.
            # But here V is defined on the RESULT of a draw.
            # If we drew a tile and are now Tenpai (h=0), what is the value?
            # It's the Sum P(winning tiles).
            
            # Find best discard to maximize waits
            max_wait_prob = 0.0
            unique_tiles = set(hand_14)
            for d in unique_tiles:
                temp_hand = list(hand_14)
                temp_hand.remove(d)
                # Sum probs of all w such that temp_hand + w is Win
                current_prob = 0.0
                for w, prob in wall_probs.items():
                    if prob > 0 and HandChecker.is_winning(temp_hand + [w]):
                        current_prob += prob
                max_wait_prob = max(max_wait_prob, current_prob)
            return max_wait_prob
            
        # Not Ready
        return math.exp(-self.LAMBDA_VAL * h_val)

    def optimize_discard(self, hand_14: list[str], discards: list[str]) -> tuple[str, float]:
        """
        Calculates Q(a_t) for all discards and returns the optimal one.
        Q(a_t) = Sum_{x} P(x|W) * V(H_minus + x).
        """
        wall_probs = self.get_unknown_distribution(hand_14, discards)
        best_tile, max_q = None, -1.0
        
        for discard in set(hand_14):
            # Form H_minus
            hand_minus = list(hand_14)
            hand_minus.remove(discard)
            
            # Expectimax Lookahead
            q_val = 0.0
            # Optimization: Only iterate tiles with non-zero probability
            active_probs = [(t, p) for t, p in wall_probs.items() if p > 0]
            
            for tile, prob in active_probs:
                # Next State: H_minus + drawn tile
                v_score = self.hand_value_function_V(hand_minus + [tile], wall_probs)
                q_val += prob * v_score
                
            if q_val > max_q:
                max_q = q_val
                best_tile = discard
                
        return best_tile, max_q
