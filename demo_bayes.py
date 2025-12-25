"""
Demo script to demonstrate the Bayesian Mahjong Agent's capabilities.
Scenarios:
1. Valid Winning Hand Check.
2. Max 2 Suit Constraint Enforcement logic.
"""
from mahjong_core import HandChecker
from mahjong_bayes import BayesianMahjong

def run_concise_demo():
    print("=== ANAMAH: Bayesian Mahjong Demo ===")
    agent = BayesianMahjong()

    # 1. Constraint Check
    # Hand with 3 suits (B, C, D) -> Should NOT win despite valid melds
    multi_suit_hand = [
        "B1", "B2", "B3", "C4", "C5", "C6", "D7", "D8", "D9", 
        "B5", "B5", "B5", "C1", "C1"
    ]
    print(f"\n[Scenario 1] 3-Suit Hand:\n{multi_suit_hand}")
    print(f"Is Winning: {HandChecker.is_winning(multi_suit_hand)} (Expected: False)")

    # 2. Optimization with Lookahead
    # User holds melds in B and C, plus trash tiles in D.
    # Agent should discard D to align with Max-2-Euit constraint.
    hand = [
        "B1", "B2", "B3", "C4", "C5", "C6", "C8", "C8", # Core
        "B8", "B9", # Penchan wait
        "D1", "D2", "C9", # Trash / D-suit
        "C1" # draw
    ]
    # Note: 14 tiles
    print(f"\n[Scenario 2] Logic Test (B/C Melds vs D trash):\n{hand}")
    
    # Run Opt
    best, score = agent.optimize_discard(hand, discards=[])
    print(f"Optimal Discard: {best} (Score: {score:.4f})")
    
    if best.startswith("D"):
        print(">> SUCCESS: Agent flushed the 3rd suit.")
    else:
        print(f">> ANALYSIS: Agent chose {best}.")

if __name__ == "__main__":
    run_concise_demo()
