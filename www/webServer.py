from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import json
from collections import defaultdict
import asyncio
from typing import Dict, Set, List, Optional
import uvicorn

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class GameState:
    def __init__(self):
        self.reset_all()

    def reset_all(self):
        """Reset all game state"""
        self.games = {}
        self.grids = {}
        self.shots = defaultdict(lambda: defaultdict(list))
        self.head_positions = defaultdict(lambda: defaultdict(list))
        self.heads_hit = defaultdict(lambda: defaultdict(int))
        self.current_player = {}
        self.placement_phase = {}
        self.waiting_players = []  # Changed from set() to list()
        self.shot_results = defaultdict(lambda: defaultdict(dict))
        self.active_games = set()
        self.game_status = {}

    def cleanup_game(self, game_id: str):
        """Clean up all game-related data"""
        print(f"Cleaning up game {game_id}")
        if game_id in self.games:
            self.games.pop(game_id, None)
        if game_id in self.grids:
            self.grids.pop(game_id, None)
        if game_id in self.shots:
            self.shots.pop(game_id, None)
        if game_id in self.head_positions:
            self.head_positions.pop(game_id, None)
        if game_id in self.heads_hit:
            self.heads_hit.pop(game_id, None)
        if game_id in self.current_player:
            self.current_player.pop(game_id, None)
        if game_id in self.placement_phase:
            self.placement_phase.pop(game_id, None)
        if game_id in self.shot_results:
            self.shot_results.pop(game_id, None)
        if game_id in self.active_games:
            self.active_games.remove(game_id)
        if game_id in self.game_status:
            self.game_status.pop(game_id, None)

    def create_new_game(self) -> str:
        """Create a new game with a unique ID"""
        # Clean up any stale games first
        for game_id in list(self.active_games):
            if game_id not in self.games or not self.games[game_id]:
                self.cleanup_game(game_id)

        # Create new game ID
        game_id = "0"
        while game_id in self.active_games:
            game_id = str(int(game_id) + 1)
        
        # Initialize game state
        self.games[game_id] = {}
        self.placement_phase[game_id] = True
        self.current_player[game_id] = "1"
        self.active_games.add(game_id)
        self.game_status[game_id] = 'waiting'
        
        print(f"Created new game {game_id}")
        return game_id

    def is_game_available(self, game_id: str) -> bool:
        """Check if a game is available to join"""
        return (game_id in self.active_games and 
                game_id in self.games and 
                len(self.games[game_id]) < 2 and
                self.game_status[game_id] == 'waiting')

game_state = GameState()

@app.get("/")
async def get_index():
    return RedirectResponse(url='/static/index.html')

async def find_game(websocket: WebSocket) -> str:
    """Find an available game or create a new one"""
    if websocket in game_state.waiting_players:
        game_state.waiting_players.remove(websocket)
    
    # Clean up any empty or stale games
    for game_id in list(game_state.active_games):
        if game_id not in game_state.games or not game_state.games[game_id]:
            game_state.cleanup_game(game_id)
    
    # Look for available games
    for game_id in list(game_state.active_games):
        if game_state.is_game_available(game_id):
            print(f"Found available game {game_id}")
            return game_id
    
    # Create new game if no available games found
    return game_state.create_new_game()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    game_id = None
    player_id = None
    
    try:
        await websocket.accept()
        
        game_id = await find_game(websocket)
        player_id = str(len(game_state.games[game_id]) + 1)
        game_state.games[game_id][player_id] = websocket
        
        if len(game_state.games[game_id]) == 2:
            game_state.game_status[game_id] = 'in_progress'
        
        print(f"Player {player_id} joined game {game_id}")
        
        await websocket.send_json({
            "type": "init",
            "player_id": player_id,
            "game_id": game_id
        })
        
        while True:
            data = await websocket.receive_json()
            
            if "grid" in data:
                if game_id not in game_state.grids:
                    game_state.grids[game_id] = {}
                game_state.grids[game_id][player_id] = data["grid"]
                
            if "head_positions" in data:
                game_state.head_positions[game_id][player_id] = data["head_positions"]
                
            opponent_id = "2" if player_id == "1" else "1"
            
            # Check if placement phase should end
            placement_phase_just_ended = False
            if game_state.placement_phase[game_id]:
                if game_id in game_state.grids and len(game_state.grids[game_id]) == 2:
                    planes_placed_p1 = len(game_state.head_positions[game_id].get("1", []))
                    planes_placed_p2 = len(game_state.head_positions[game_id].get("2", []))
                    print(f"Checking placement status - P1: {planes_placed_p1}, P2: {planes_placed_p2}")
                    
                    if planes_placed_p1 >= 3 and planes_placed_p2 >= 3:
                        game_state.placement_phase[game_id] = False
                        game_state.current_player[game_id] = "1"
                        placement_phase_just_ended = True
                        game_state.game_status[game_id] = 'in_progress'
                        print(f"Game {game_id} placement phase complete. P1: {planes_placed_p1}, P2: {planes_placed_p2}")
            
            if placement_phase_just_ended:
                # Send immediate updates to both players
                for pid, ws in game_state.games[game_id].items():
                    try:
                        is_player_one = pid == "1"
                        other_player = "2" if is_player_one else "1"
                        update_msg = {
                            "type": "update",
                            "opponent_ready": True,
                            "your_turn": is_player_one,
                            "placement_phase": False,
                            "opponent_shots": game_state.shots[game_id][other_player],
                            "heads_hit": game_state.heads_hit[game_id][pid],
                            "opponent_heads_hit": game_state.heads_hit[game_id][other_player],
                            "shot_results": game_state.shot_results[game_id][pid]
                        }
                        await ws.send_json(update_msg)
                        print(f"Sent placement complete to P{pid}, turn: {is_player_one}")
                    except Exception as e:
                        print(f"Error sending placement complete to P{pid}: {e}")
                continue

            current_shots = data.get("shots", [])
            if (not game_state.placement_phase[game_id] and 
                game_state.current_player[game_id] == player_id):
                for row in range(len(current_shots)):
                    for col in range(len(current_shots[row])):
                        if (current_shots[row][col] and 
                            (row, col) not in game_state.shots[game_id][player_id]):
                            
                            game_state.shots[game_id][player_id].append((row, col))
                            coords = f"{row},{col}"
                            
                            in_head_positions = any(row == hr and col == hc 
                                                  for hr, hc in game_state.head_positions[game_id][opponent_id])
                            if in_head_positions:
                                game_state.shot_results[game_id][player_id][coords] = "head"
                                game_state.heads_hit[game_id][player_id] += 1
                            elif (opponent_id in game_state.grids[game_id] and 
                                  game_state.grids[game_id][opponent_id][row][col] != [255, 255, 255]):
                                game_state.shot_results[game_id][player_id][coords] = "hit"
                            else:
                                game_state.shot_results[game_id][player_id][coords] = "miss"
                            
                            game_state.current_player[game_id] = opponent_id
                            
                            shooter_response = {
                                "type": "update",
                                "opponent_ready": True,
                                "your_turn": False,
                                "placement_phase": False,
                                "opponent_shots": game_state.shots[game_id][opponent_id],
                                "heads_hit": game_state.heads_hit[game_id][player_id],
                                "opponent_heads_hit": game_state.heads_hit[game_id][opponent_id],
                                "shot_results": game_state.shot_results[game_id][player_id]
                            }
                            await websocket.send_json(shooter_response)
                            
                            if opponent_id in game_state.games[game_id]:
                                try:
                                    opponent_response = {
                                        "type": "update",
                                        "opponent_ready": True,
                                        "your_turn": True,
                                        "placement_phase": False,
                                        "opponent_shots": game_state.shots[game_id][player_id],
                                        "heads_hit": game_state.heads_hit[game_id][opponent_id],
                                        "opponent_heads_hit": game_state.heads_hit[game_id][player_id]
                                    }
                                    await game_state.games[game_id][opponent_id].send_json(opponent_response)
                                except Exception as e:
                                    print(f"Error sending update to opponent: {e}")
                            continue

            response = {
                "type": "update",
                "opponent_ready": len(game_state.games[game_id]) == 2,
                "your_turn": game_state.current_player[game_id] == player_id,
                "placement_phase": game_state.placement_phase[game_id],
                "opponent_shots": game_state.shots[game_id][opponent_id],
                "heads_hit": game_state.heads_hit[game_id][player_id],
                "opponent_heads_hit": game_state.heads_hit[game_id][opponent_id],
                "shot_results": game_state.shot_results[game_id][player_id],
                "placement_status": {
                    "your_planes": len(game_state.head_positions[game_id].get(player_id, [])),
                    "opponent_planes": len(game_state.head_positions[game_id].get(opponent_id, []))
                }
            }
            
            # Add debug logging
            if game_state.placement_phase[game_id]:
                print(f"Game {game_id} - P{player_id} placement status: " +
                      f"Own planes: {len(game_state.head_positions[game_id].get(player_id, []))}, " +
                      f"Opponent planes: {len(game_state.head_positions[game_id].get(opponent_id, []))}")
            
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        print(f"Player {player_id} disconnected from game {game_id}")
    except Exception as e:
        print(f"Error in game {game_id}, player {player_id}: {e}")
    finally:
        if game_id and player_id and game_id in game_state.games:
            if player_id in game_state.games[game_id]:
                del game_state.games[game_id][player_id]
                
                # Clean up the game completely
                game_state.cleanup_game(game_id)
                
                # If there's a remaining player, notify them
                remaining_players = list(game_state.games.get(game_id, {}).values())
                for remaining_ws in remaining_players:
                    try:
                        await remaining_ws.send_json({
                            "type": "update",
                            "opponent_ready": False,
                            "your_turn": False,
                            "placement_phase": True,
                            "message": "Opponent disconnected. Please refresh to start a new game."
                        })
                    except:
                        pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)