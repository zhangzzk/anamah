from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union
from mahjong_core import HandChecker, TILES
from mahjong_bayes import BayesianMahjong

# API Setup
app = FastAPI()
agent = BayesianMahjong()

# --- Store ---
# discards: List[dict] -> [{"tile": "1B", "who": "A"}, ...]
# melds: List[List[str]] -> [["1B", "1B", "1B"], ...]
# melds: Dict[str, List[List[str]]] -> {"Me": [], "A": [], "B": [], "C": []}
game_state = {
    "hand": [], 
    "discards": [], 
    "melds": {"Me": [], "A": [], "B": [], "C": []}
}

# --- Models ---
class InitRequest(BaseModel):
    initial_hand: List[str]

class AdviceResponse(BaseModel):
    discard: str
    score: float
    is_winning: bool

# --- Helpers ---
def get_visible_tiles():
    """Flatten discards and melds for the agent."""
    visible = [d["tile"] for d in game_state["discards"]]
    for player_melds in game_state["melds"].values():
        for m in player_melds:
            visible.extend(m)
    return visible

def check_pong(hand: List[str], tile: str) -> bool:
    return hand.count(tile) >= 2

def perform_pong(tile: str, who: str):
    """
    Register a Pong for 'who'. 
    If who == "Me", remove from hand.
    Always add to melds.
    """
    if who == "Me":
        # Remove 2 instances
        if game_state["hand"].count(tile) < 2:
            print("Error: Impossible State. Pong called but < 2 tiles in hand.")
            return
        game_state["hand"].remove(tile)
        game_state["hand"].remove(tile)
        
    # Add to melds (3 tiles)
    # Note: Logic usually implies 1 tile came from discard, 2 from hand.
    # But for "Visible Tiles" counting, we just need to know these 3 are now out.
    # The discarded tile was NOT added to 'discards' list if it was called (usually).
    # We will assume calling logic handles the 'not-in-discard-pool' aspect.
    game_state["melds"][who].append([tile, tile, tile])

def normalize_tile(t: str) -> str:
    t = t.upper()
    if t in TILES: return t
    
    # Check for swapped format (e.g., 1C instead of C1)
    if len(t) == 2:
        # If t is "1C", reversed is "C1"
        rev = t[1] + t[0]
        if rev in TILES: return rev
        
    return t

def is_valid_tile(t: str) -> bool:
    return normalize_tile(t) in TILES

# --- Endpoints ---
@app.post("/start")
def start_game(req: InitRequest):
    game_state["hand"] = req.initial_hand
    game_state["discards"] = []
    game_state["melds"] = {"Me": [], "A": [], "B": [], "C": []}
    return {"status": "started", "hand": game_state["hand"]}

@app.post("/draw")
def draw(tile: str):
    game_state["hand"].append(tile)
    return {
        "drawn": tile, 
        "win": HandChecker.is_winning(game_state["hand"])
    }

@app.get("/advice", response_model=AdviceResponse)
def get_advice():
    h = game_state["hand"]
    visible = get_visible_tiles()
    
    if HandChecker.is_winning(h):
        return AdviceResponse(discard="WIN", score=100.0, is_winning=True)
        
    best, val = agent.optimize_discard(h, visible)
    return AdviceResponse(discard=best or "NONE", score=val, is_winning=False)

@app.post("/discard")
def discard(tile: str, who: str = "Me"):
    # If it's me, remove from hand
    if who == "Me" and tile in game_state["hand"]:
        game_state["hand"].remove(tile)
    
    game_state["discards"].append({"tile": tile, "who": who})
    return {"hand": game_state["hand"]}

# --- CLI Helpers ---
def print_table():
    print("\n" + "="*60)
    print(f"MY HAND ({len(game_state['hand'])}): {sorted(game_state['hand'])}")
    
    # Print Melds
    # Format: Me: [...], A: [...], B: [...], C: [...]
    all_melds = []
    for p in ["Me", "A", "B", "C"]:
        if game_state["melds"][p]:
            all_melds.append(f"{p}:{game_state['melds'][p]}")
    if all_melds:
        print(f"MELDS: {' | '.join(all_melds)}")
        
    print("-" * 60)
    # Group discards
    pools = {"Me": [], "A": [], "B": [], "C": []}
    for d in game_state["discards"]:
        if d["who"] in pools:
            pools[d["who"]].append(d["tile"])
    
    print("DISCARD POOLS:")
    print(f"Me: {pools['Me']}")
    print(f"A : {pools['A']}")
    print(f"B : {pools['B']}")
    print(f"C : {pools['C']}")
    print("="*60 + "\n")

def validate_hand_length(expected_mod: int):
    # expected_mod: 2 for (14,11,8,5,2) - Discard Phase
    # expected_mod: 1 for (13,10,7,4,1) - Draw Phase
    l = len(game_state["hand"])
    if l % 3 != expected_mod:
        print(f"WARNING: Hand length {l} seems irregular (Expected mod 3 == {expected_mod}). check inputs!")

# --- CLI ---
def cli():
    print("--- ANAMAH CLI ---")
    print("Supports: Pong (P), Kong (K), Ron (Win)")
    
    # 1. Initial Hand Setup
    while True:
        raw = input("Initial Hand (13 tiles): ").strip()
        if not raw: return
        hand = [normalize_tile(t) for t in raw.split()]
        
        # Validations
        invalid_tiles = [t for t in hand if t not in TILES]
        if invalid_tiles:
            print(f"Error: Invalid tiles detected: {invalid_tiles}")
            continue
            
        if len(hand) != 13:
            print(f"Error: Must start with exactly 13 tiles. (You has {len(hand)})")
            continue
            
        game_state["hand"] = hand
        break
        
    game_state["discards"] = []
    game_state["melds"] = {"Me": [], "A": [], "B": [], "C": []}
    
    # Players: 0=Me, 1=A, 2=B, 3=C
    players = ["Me", "A", "B", "C"]
    
    # Who starts?
    while True:
        starter = input("Who starts? [Me]/A/B/C: ").strip().capitalize() or "Me"
        if starter in players:
            current_idx = players.index(starter)
            break
        print("Invalid player. Choose Me, A, B, or C.")
    
    pending_discard = False

    while True:
        print_table()
        current_player = players[current_idx]
        print(f"--- TURN: {current_player} ---")
        
        # === MY TURN ===
        if current_player == "Me":
            if pending_discard:
                print(">> Me (After Call) - Must Discard.")
                pending_discard = False
            else:
                # Direct to Draw
                dt = input(">> I Draw: ").strip()
                dt = normalize_tile(dt)
                if not is_valid_tile(dt):
                    print(f"Invalid tile '{dt}'")
                    continue
                game_state["hand"].append(dt)
                
            validate_hand_length(2) # Expect 14 (or 11 if Pon'd)
            
            if HandChecker.is_winning(game_state["hand"]):
                print("!!! TSUMO (Self-Draw Win) !!!")
                break
                
            # Advise
            visible = get_visible_tiles()
            
            # 1. Bayes
            best_bayes, val_bayes = agent.optimize_discard(game_state["hand"], visible, use_inference=True)
            # 2. Naive
            best_naive, val_naive = agent.optimize_discard(game_state["hand"], visible, use_inference=False)
            
            print(f"AI Suggests (Bayes): {best_bayes} ({val_bayes:.3f}) | (Naive): {best_naive} ({val_naive:.3f})")
            
            # Determine best for prompt
            best = best_bayes
            
            # Discard
            discard_tile = None
            while True:
                disc = input(f">> Discard [{best}]: ").strip()
                if not disc: disc = best
                disc = normalize_tile(disc)
                if disc in game_state["hand"]:
                    game_state["hand"].remove(disc)
                    discard_tile = disc
                    break
                else: 
                    print(f"Tile {disc} not in hand.")
            
            # Now, did anyone call it?
            call_input = input(f"Did opponents call {discard_tile}? [N] / [Player] (add 'W' for Win): ").upper().strip() or "N"
            
            # Check for Win (e.g. "A W", "B WIN")
            if " " in call_input or "W" in call_input:
                # Naive parse: find player in string
                winner = None
                for p in ["A", "B", "C"]:
                    if p in call_input:
                        winner = p
                        break
                if winner:
                    print(f"!!! {winner} RON on {discard_tile} !!!")
                    print("Game continues...")
                    current_idx = (players.index(winner) + 1) % 4
                    continue

            # Standard Pong
            if call_input in ["A", "B", "C"]:
                # Opponent called it.
                perform_pong(discard_tile, call_input)
                print(f"Turn jumps to {call_input}.")
                current_idx = players.index(call_input)
                # Skip normal rotation
                continue
            
            # If no call, add to My Discards
            game_state["discards"].append({"tile": discard_tile, "who": "Me"})
            current_idx = (current_idx + 1) % 4
            

        else:
            # They draw hiddenly. They discard openly. (Or they Win)
            t = input(f">> {current_player} Discards (or [W]in): ").strip()
            
            # Handle Self-Draw Win (Tsumo)
            if t.upper() in ["W", "WIN", "TSUMO"]:
                print(f"!!! {current_player} TSUMO (Self-Draw Win) !!!")
                print("Game continues...")
                current_idx = (current_idx + 1) % 4
                continue

            t = normalize_tile(t)
            if not is_valid_tile(t):
                print(f"Invalid tile '{t}'"); continue
                
            # 1. Can I Ron?
            if HandChecker.is_winning(game_state["hand"] + [t]):
                ron = input(f"!!! CAN RON on {t}! Do it? [Y]/n: ").upper()
                if ron != "N":
                    game_state["hand"].append(t)
                    print("!!! RON !!!")
                    break
                    
            # 2. Can I Pon?
            can_pong = check_pong(game_state["hand"], t)
            if can_pong:
                pon = input(f"Can Pon {t}. Do it? [Y]/n: ").upper().strip() or "Y"
                if pon != "N":
                    perform_pong(t, "Me")
                    current_idx = 0 # Jump to Me
                    pending_discard = True
                    # We enter loop, but I need to Discard, not Draw.
                    continue
            
            # 3. Did Other Opponents Call?
            # Filter out current player and me
            others = [p for p in ["A", "B", "C"] if p != current_player]
            call_input = input(f"Did {others} call? [N] / [Player] (add 'W' for Win): ").upper().strip() or "N"
            
            # Check for Win (e.g. "C W")
            if " " in call_input or "W" in call_input:
                winner = None
                for p in ["A", "B", "C"]:
                    if p in call_input:
                        winner = p
                        break
                if winner and winner != current_player: # Basic check
                    print(f"!!! {winner} RON on {t} !!!")
                    print("Game continues...")
                    current_idx = (players.index(winner) + 1) % 4
                    continue

            if call_input in ["A", "B", "C"]:
                if call_input == current_player:
                    print("Error: Player cannot call own tile (except Kan, unsupported).")
                else:
                    perform_pong(t, call_input)
                    current_idx = players.index(call_input)
                    continue
            
            # If No One Called
            agent.register_opponent_discard(current_player, t)
            game_state["discards"].append({"tile": t, "who": current_player})
            current_idx = (current_idx + 1) % 4
                
if __name__ == "__main__":
    cli()

