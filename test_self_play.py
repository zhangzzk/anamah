import random
from collections import Counter
from mahjong_core import TILES, HandChecker, SUITS
from mahjong_bayes import BayesianMahjong, DiscardModel
import math

# Baseline Agent using Greedy Shanten (tries to win fast)
class BaselineAgent:
    def __init__(self):
        pass

    def choose_discard(self, hand):
        best_tile = None
        best_shanten = float('inf')
        
        unique_tiles = list(set(hand))
        random.shuffle(unique_tiles)
        
        for tile in unique_tiles:
            temp_hand = list(hand)
            temp_hand.remove(tile)
            s = HandChecker.calculate_shanten(temp_hand)
            if s < best_shanten:
                best_shanten = s
                best_tile = tile
        return best_tile

# Naive Bayesian Agent: Uses the V(H) formula but NO opponent inference (Uniform Wall)
class NaiveBayesAgent:
    def __init__(self):
        self.engine = BayesianMahjong()

    def choose_discard(self, hand, visible_pool, verbose=False):
        # use_inference=False disables the particle filters
        d_tile, _ = self.engine.optimize_discard(hand, visible_pool, use_inference=False, verbose=verbose)
        return d_tile

class MatchRunner:
    def __init__(self, num_rounds=100):
        self.num_rounds = num_rounds
        self.stats = {
            "P0_Bayes": {"wins": 0, "score": 0},
            "P1_Naive": {"wins": 0, "score": 0},
            "P2_Base": {"wins": 0, "score": 0},
            "P3_Base": {"wins": 0, "score": 0},
            "Draws": 0
        }

    def run_match(self, verbose=False):
        print(f"Starting {self.num_rounds} rounds of Blood Battle...")
        for r in range(1, self.num_rounds + 1):
            is_verbose = verbose and (r == 1) 
            winner_list = self.play_round(r, verbose=is_verbose)

            if winner_list == ["Draw"]:
                self.stats["Draws"] += 1
            else:
                for w in winner_list:
                    role = ""
                    if w == "P0": role = "P0_Bayes"
                    elif w == "P1": role = "P1_Naive"
                    else: role = f"{w}_Base"
                    self.stats[role]["wins"] += 1
            
            # Progress bar
            sys.stdout.write(f"\r[{'=' * (int(r/self.num_rounds*40))}{'-' * (40-int(r/self.num_rounds*40))}] {r}/{self.num_rounds} | P0_Bayes: {self.stats['P0_Bayes']['wins']}, P1_Naive: {self.stats['P1_Naive']['wins']}, P2_Base: {self.stats['P2_Base']['wins']}, P3_Base: {self.stats['P3_Base']['wins']}, Draws: {self.stats['Draws']}")
            sys.stdout.flush()
        print(f"\n\n=== FINAL STATISTICS ===")
        print(f"P0_Bayes: {self.stats['P0_Bayes']['wins']}, P1_Naive: {self.stats['P1_Naive']['wins']}, P2_Base: {self.stats['P2_Base']['wins']}, P3_Base: {self.stats['P3_Base']['wins']}, Draws: {self.stats['Draws']}")

    def play_round(self, round_num, verbose=False):
        wall = get_wall()
        players = ["P0", "P1", "P2", "P3"]
        hands = {p: [wall.pop() for _ in range(13)] for p in players}
        
        #四川麻将 (Void Suit Choice)
        void_suits = {}
        for p in players:
            counts = Counter(t[0] for t in hands[p])
            void_suits[p] = min(SUITS, key=lambda s: counts[s])

        if verbose:
            print(f"\n--- ROUND {round_num} START ---")
            for p in players:
                print(f"{p} Hand: {sorted(hands[p])} Void: {void_suits[p]}")

        # Agents
        bayes_agent = BayesianMahjong() # P0: Full Bayesian
        naive_agent = NaiveBayesAgent() # P1: Naive (No Inference)
        baseline_agents = {p: BaselineAgent() for p in players if p not in ["P0", "P1"]}
        
        discards_log = [] # List of {"tile":t, "who":p}
        winners = []      # List of players who won (Bloody Rules)
        turn_idx = 0
        
        while len(winners) < 3 and wall:
            curr_p = players[turn_idx % 4]
            if curr_p in winners:
                turn_idx += 1
                continue
                
            draw_card = wall.pop()
            hands[curr_p].append(draw_card)
            
            if verbose and curr_p == "P0":
                print(f"{curr_p} Draw {draw_card}. Hand: {sorted(hands[curr_p])}")

            # Win check
            has_void = any(t[0] == void_suits[curr_p] for t in hands[curr_p])
            if not has_void and HandChecker.is_winning(hands[curr_p]):
                if verbose: print(f"!!! {curr_p} TSUMO with {draw_card} !!!")
                winners.append(curr_p)
                turn_idx += 1
                continue
                
            # Discard
            discard = None
            curr_hand = hands[curr_p]
            void_candidates = [t for t in curr_hand if t[0] == void_suits[curr_p]]
            
            if void_candidates:
                discard = random.choice(void_candidates)
            else:
                visible = [d["tile"] for d in discards_log]
                if curr_p == "P0":
                    d_tile, _ = bayes_agent.optimize_discard(curr_hand, visible, use_inference=True, verbose=verbose)
                    discard = d_tile
                elif curr_p == "P1":
                    discard = naive_agent.choose_discard(curr_hand, visible, verbose=verbose)
                else:
                    discard = baseline_agents[curr_p].choose_discard(curr_hand)
            
            if discard in curr_hand:
                hands[curr_p].remove(discard)
                discards_log.append({"tile": discard, "who": curr_p})
                if verbose and curr_p == "P0":
                    print(f"[{turn_idx}] {curr_p} Discards {discard}.")
                
                # Check for RON
                for other in players:
                    if other == curr_p or other in winners: continue
                    has_void_other = any(t[0] == void_suits[other] for t in hands[other])
                    if not has_void_other and HandChecker.is_winning(hands[other] + [discard]):
                        if verbose: print(f"!!! {other} RON on {discard} !!!")
                        winners.append(other)
            
            turn_idx += 1

        if verbose:
            if not winners: print("Draw.")
            else: print(f"Round End. Winners: {winners}")
            
        return winners if winners else ["Draw"]

def get_wall():
    from mahjong_core import get_all_tiles
    w = get_all_tiles()
    random.shuffle(w)
    return w

def demo_verbose():
    print("--- DEMO MATCH (Verbose) ---")
    demo_runner = MatchRunner(num_rounds=1)
    demo_runner.run_match(verbose=True)

if __name__ == "__main__":
    import sys
    # demo_verbose()
    
    print("\n--- STATISTICAL RUN ---")
    runner = MatchRunner(num_rounds=500)
    runner.run_match(verbose=False)
