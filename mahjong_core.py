"""Core Mahjong logic rules."""
from collections import Counter
from functools import lru_cache

# Game Constants
SUITS = ['B', 'C', 'D']  # Bamboo, Characters, Dots
TILES = [f"{s}{i}" for s in SUITS for i in range(1, 10)]

def get_all_tiles() -> list[str]:
    """Returns a fresh set of all 136 game tiles (4 copies each)."""
    return TILES * 4

@lru_cache(maxsize=4096)
def _shanten_search(counts_tuple, groups, partials, pair_found):
    # Base Shanten (rough estimate)
    best_s = 8 - 2*groups - partials - (1 if pair_found else 0)
    
    # Find first non-zero tile
    tile_idx = -1
    for i in range(len(TILES)):
        if counts_tuple[i] > 0:
            tile_idx = i
            break
            
    if tile_idx == -1:
        p = 1 if pair_found else 0
        g = groups
        t = partials
        if g + t > 4: t = 4 - g
        return 8 - 2*g - t - p

    tile = TILES[tile_idx]
    counts_list = list(counts_tuple)
    
    # 1. Pung
    if counts_list[tile_idx] >= 3:
        counts_list[tile_idx] -= 3
        s = _shanten_search(tuple(counts_list), groups + 1, partials, pair_found)
        if s < best_s: best_s = s
        counts_list[tile_idx] += 3
        
    # 2. Chow
    suit, num = tile[0], int(tile[1:])
    if num <= 7:
        t2_idx, t3_idx = tile_idx + 1, tile_idx + 2
        if counts_list[t2_idx] > 0 and counts_list[t3_idx] > 0:
            counts_list[tile_idx] -= 1
            counts_list[t2_idx] -= 1
            counts_list[t3_idx] -= 1
            s = _shanten_search(tuple(counts_list), groups + 1, partials, pair_found)
            if s < best_s: best_s = s
            counts_list[tile_idx] += 1
            counts_list[t2_idx] += 1
            counts_list[t3_idx] += 1

    # 3. Partials
    if groups + partials < 4:
        # Pair
        if counts_list[tile_idx] >= 2:
            counts_list[tile_idx] -= 2
            if not pair_found:
                s = _shanten_search(tuple(counts_list), groups, partials, True)
                if s < best_s: best_s = s
            s = _shanten_search(tuple(counts_list), groups, partials + 1, pair_found)
            if s < best_s: best_s = s
            counts_list[tile_idx] += 2
            
        # Neighbor
        if num <= 8:
            t2_idx = tile_idx + 1
            if TILES[t2_idx][0] == suit and counts_list[t2_idx] > 0:
                counts_list[tile_idx] -= 1
                counts_list[t2_idx] -= 1
                s = _shanten_search(tuple(counts_list), groups, partials + 1, pair_found)
                if s < best_s: best_s = s
                counts_list[tile_idx] += 1
                counts_list[t2_idx] += 1
        
        # Gap
        if num <= 7:
            t3_idx = tile_idx + 2
            if TILES[t3_idx][0] == suit and counts_list[t3_idx] > 0:
                counts_list[tile_idx] -= 1
                counts_list[t3_idx] -= 1
                s = _shanten_search(tuple(counts_list), groups, partials + 1, pair_found)
                if s < best_s: best_s = s
                counts_list[tile_idx] += 1
                counts_list[t3_idx] += 1

    # 4. Discard
    counts_list[tile_idx] -= 1
    s = _shanten_search(tuple(counts_list), groups, partials, pair_found)
    if s < best_s: best_s = s
    counts_list[tile_idx] += 1
    
    return best_s

class HandChecker:
    """Hand utilities."""
    
    @staticmethod
    def is_winning(hand_tiles: list[str]) -> bool:
        """Check win (Standard Mahjong + Sichuan Void Constraint)."""
        if len(hand_tiles) not in [14, 11, 8, 5, 2]:
            return False
        present_suits = {t[0] for t in hand_tiles if t[0] in SUITS}
        if len(present_suits) > 2:
            return False
        counts = Counter(hand_tiles)
        possible_pairs = [t for t, c in counts.items() if c >= 2]
        for pair in possible_pairs:
            remaining = counts.copy()
            remaining[pair] -= 2
            if remaining[pair] == 0: del remaining[pair]
            if HandChecker._check_melds(remaining):
                return True
        return False

    @staticmethod
    def calculate_shanten(hand_tiles: list[str]) -> int:
        """Calc shanten using cached search."""
        ts = [t for t in hand_tiles if t[0] in SUITS]
        suit_counts = Counter(t[0] for t in ts)
        penalty = 0
        kept_tiles = list(hand_tiles)
        if len(suit_counts) > 2:
            top_2 = [s for s, c in suit_counts.most_common(2)]
            kept_tiles = [t for t in hand_tiles if t[0] in top_2]
            penalty = len(hand_tiles) - len(kept_tiles)

        counts = Counter(kept_tiles)
        counts_tuple = [0] * len(TILES)
        for t, c in counts.items():
            if t in TILES:
                counts_tuple[TILES.index(t)] = c
                
        return _shanten_search(tuple(counts_tuple), 0, 0, False) + penalty

    @staticmethod
    def _check_melds(counts: Counter) -> bool:
        """Recursive check melds."""
        if sum(counts.values()) == 0:
            return True
        tile = min(counts.keys()) 
        if counts[tile] >= 3:
            new_counts = counts.copy()
            new_counts[tile] -= 3
            if new_counts[tile] == 0: del new_counts[tile]
            if HandChecker._check_melds(new_counts):
                return True
        try:
            suit, num = tile[0], int(tile[1:])
            t1, t2, t3 = tile, f"{suit}{num+1}", f"{suit}{num+2}"
            if counts[t1] >= 1 and counts[t2] >= 1 and counts[t3] >= 1:
                new_counts = counts.copy()
                new_counts[t1] -= 1
                new_counts[t2] -= 1
                new_counts[t3] -= 1
                for t in [t1, t2, t3]:
                    if new_counts[t] <= 0: del new_counts[t]
                if HandChecker._check_melds(new_counts):
                    return True
        except (ValueError, KeyError):
            pass 
        return False
