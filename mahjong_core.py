"""
Core Mahjong logic rules and winning condition checks.
Implements the specific rule set: 4 Melds + 1 Pair, with a restriction to max 2 suits.
"""
from collections import Counter

# Game Constants
SUITS = ['B', 'C', 'D']  # Bamboo, Characters, Dots
TILES = [f"{s}{i}" for s in SUITS for i in range(1, 10)]

def get_all_tiles() -> list[str]:
    """Returns a fresh set of all 136 game tiles (4 copies each)."""
    return TILES * 4

class HandChecker:
    """Static utility class for validating winning hands and structural analysis."""
    
    @staticmethod
    def is_winning(hand_tiles: list[str]) -> bool:
        """
        Determines if a 14-tile hand is a valid winning hand.
        
        Rules:
        1. Must be exactly 14 tiles.
        2. Must consist of exactly 1 pair and 4 valid melds (triplets or sequences).
        3. Must contain tiles from at most 2 distinct suits (Qing Yise / Definite mixed rule).
        """
        if len(hand_tiles) != 14:
            return False
            
        # Constraint: Max 2 suits allowed
        present_suits = {t[0] for t in hand_tiles if t[0] in SUITS}
        if len(present_suits) > 2:
            return False
            
        counts = Counter(hand_tiles)
        
        # Iterate over all possible pairs to see if remaining 12 tiles form 4 melds
        possible_pairs = [t for t, c in counts.items() if c >= 2]
        for pair in possible_pairs:
            remaining = counts.copy()
            remaining[pair] -= 2
            if remaining[pair] == 0:
                del remaining[pair]
                
            if HandChecker._check_melds(remaining):
                return True
                
        return False

    @staticmethod
    def _check_melds(counts: Counter) -> bool:
        """Recursive backtracking to check if tiles can be partitioned into valid melds."""
        if sum(counts.values()) == 0:
            return True
            
        tile = min(counts.keys()) # Deterministic processing order
        
        # 1. Try Pung (AAA)
        if counts[tile] >= 3:
            new_counts = counts.copy()
            new_counts[tile] -= 3
            if new_counts[tile] == 0: del new_counts[tile]
            if HandChecker._check_melds(new_counts):
                return True
        
        # 2. Try Chow (ABC) - Sequence
        try:
            suit, num = tile[0], int(tile[1:])
            t1, t2, t3 = tile, f"{suit}{num+1}", f"{suit}{num+2}"
            
            if counts[t1] >= 1 and counts[t2] >= 1 and counts[t3] >= 1:
                new_counts = counts.copy()
                new_counts[t1] -= 1
                new_counts[t2] -= 1
                new_counts[t3] -= 1
                
                # Cleanup
                for t in [t1, t2, t3]:
                    if new_counts[t] <= 0: del new_counts[t]
                        
                if HandChecker._check_melds(new_counts):
                    return True
        except (ValueError, KeyError):
            pass 
            
        return False
