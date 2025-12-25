"""
Interactive Game Tracker & REST API.
API: uvicorn game_tracker:app --reload
CLI: python game_tracker.py
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from mahjong_core import HandChecker
from mahjong_bayes import BayesianMahjong

# API Setup
app = FastAPI()
agent = BayesianMahjong()

# --- Store ---
game_state = {"hand": [], "discards": []}

# --- Models ---
class InitRequest(BaseModel):
    initial_hand: List[str]

class AdviceResponse(BaseModel):
    discard: str
    score: float
    is_winning: bool

# --- Endpoints ---
@app.post("/start")
def start_game(req: InitRequest):
    game_state["hand"] = req.initial_hand
    game_state["discards"] = []
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
    h, d = game_state["hand"], game_state["discards"]
    if HandChecker.is_winning(h):
        return AdviceResponse(discard="WIN", score=100.0, is_winning=True)
        
    best, val = agent.optimize_discard(h, d)
    return AdviceResponse(discard=best, score=val, is_winning=False)

@app.post("/discard")
def discard(tile: str):
    if tile in game_state["hand"]:
        game_state["hand"].remove(tile)
        game_state["discards"].append(tile)
    return {"hand": game_state["hand"]}

# --- CLI ---
def cli():
    print("--- ANAMAH CLI ---")
    raw = input("Initial Hand (space-sep): ").strip()
    if not raw: return
    game_state["hand"] = raw.split()
    
    while True:
        print(f"\nHand: {game_state['hand']}")
        if HandChecker.is_winning(game_state["hand"]):
            print("!!! WIN !!!")
            break
            
        act = input("[D]raw / [O]pponent / [Q]uit: ").upper()
        if act == "Q": break
        if act == "O":
            t = input("Opp Tile: ")
            game_state["discards"].append(t)
            continue
            
        # Draw flow
        dt = input("Drawn Tile: ")
        game_state["hand"].append(dt)
        
        # Advice
        best, val = agent.optimize_discard(game_state["hand"], game_state["discards"])
        print(f"AI Suggests: {best} ({val:.3f})")
        
        # Discard
        disc = input(f"Discard [{best}]: ") or best
        if disc in game_state["hand"]:
            game_state["hand"].remove(disc)
            game_state["discards"].append(disc)

if __name__ == "__main__":
    cli()
