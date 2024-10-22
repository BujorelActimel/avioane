from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import json
import asyncio
import logging
from dataclasses import dataclass
from pydantic import BaseModel
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Airplane Game Server")

@dataclass
class PlayerState:
    websocket: WebSocket
    grid: Optional[List[List[tuple]]] = None
    shots: List[Tuple[int, int]] = None
    head_positions: List[Tuple[int, int]] = None
    heads_hit: int = 0
    ready: bool = False

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.shots = []
        self.head_positions = []
        self.heads_hit = 0
        self.ready = False

class GameState:
    def __init__(self):
        self.players: Dict[str, PlayerState] = {}
        self.current_player: str = "1"
        self.placement_phase: bool = True
        self.game_started: bool = False
        
    def add_player(self, player_id: str, websocket: WebSocket) -> bool:
        """Add a new player to the game."""
        if len(self.players) >= 2:
            return False
        self.players[player_id] = PlayerState(websocket)
        return True
    
    def remove_player(self, player_id: str):
        """Remove a player from the game."""
        if player_id in self.players:
            del self.players[player_id]
            self.reset_if_empty()
    
    def reset_if_empty(self):
        """Reset game state if no players are connected."""
        if not self.players:
            self.placement_phase = True
            self.game_started = False
            self.current_player = "1"
    
    def get_opponent_id(self, player_id: str) -> Optional[str]:
        """Get the opponent's ID for a given player."""
        return "2" if player_id == "1" else "1" if player_id == "2" else None
    
    def check_placement_complete(self) -> bool:
        """Check if all players have placed their planes."""
        if len(self.players) != 2:
            return False
        return all(len(player.head_positions) >= 3 for player in self.players.values())
    
    def process_shot(self, player_id: str, shot: Tuple[int, int]) -> str:
        """Process a shot and return the result (miss, hit, or head)."""
        opponent_id = self.get_opponent_id(player_id)
        if not opponent_id or opponent_id not in self.players:
            return "miss"
        
        row, col = shot
        opponent = self.players[opponent_id]
        
        # Check if it's a head shot
        if (row, col) in opponent.head_positions:
            self.players[player_id].heads_hit += 1
            return "head"
        # Check if it's a body shot
        elif opponent.grid and opponent.grid[row][col] != (255, 255, 255):
            return "hit"
        return "miss"

class GameServer:
    def __init__(self):
        self.games: Dict[str, GameState] = {"main": GameState()}
        self.active_connections: Set[WebSocket] = set()
    
    def get_game(self, game_id: str = "main") -> GameState:
        """Get or create a game instance."""
        return self.games.get(game_id)
    
    async def connect(self, websocket: WebSocket, game_id: str = "main") -> Optional[str]:
        """Connect a new player to the game."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        game = self.get_game(game_id)
        if not game:
            return None
        
        player_id = "1" if "1" not in game.players else "2"
        if game.add_player(player_id, websocket):
            logger.info(f"Player {player_id} connected to game {game_id}")
            return player_id
        return None
    
    async def disconnect(self, websocket: WebSocket, player_id: str, game_id: str = "main"):
        """Handle player disconnection."""
        self.active_connections.remove(websocket)
        game = self.get_game(game_id)
        if game:
            game.remove_player(player_id)
            logger.info(f"Player {player_id} disconnected from game {game_id}")
    
    async def process_game_update(self, game: GameState, player_id: str, data: dict) -> dict:
        """Process game update from a player and return response data."""
        player = game.players[player_id]
        opponent_id = game.get_opponent_id(player_id)
        
        # Update player state
        if "grid" in data:
            player.grid = data["grid"]
        if "head_positions" in data:
            player.head_positions = data["head_positions"]
        
        # Process new shots
        shot_results = {}
        if "shots" in data and not game.placement_phase:
            current_shots = data["shots"]
            for row in range(len(current_shots)):
                for col in range(len(current_shots[row])):
                    if current_shots[row][col] and (row, col) not in player.shots:
                        shot = (row, col)
                        player.shots.append(shot)
                        result = game.process_shot(player_id, shot)
                        shot_results[shot] = result
                        if result != "miss":  # Hit or head shot
                            logger.info(f"Player {player_id} scored a {result} at {shot}")
        
        # Check if placement phase should end
        if game.placement_phase and game.check_placement_complete():
            game.placement_phase = False
            game.game_started = True
            logger.info("Placement phase complete, game starting")
        
        # Prepare response
        response = {
            "opponent_ready": opponent_id in game.players,
            "your_turn": game.current_player == player_id,
            "placement_phase": game.placement_phase,
            "opponent_shots": game.players[opponent_id].shots if opponent_id in game.players else [],
            "heads_hit": player.heads_hit,
            "opponent_heads_hit": game.players[opponent_id].heads_hit if opponent_id in game.players else 0,
            "shot_results": shot_results,
            "game_started": game.game_started
        }
        
        # Switch turns if a shot was made and game has started
        if shot_results and game.game_started:
            game.current_player = opponent_id
        
        return response

game_server = GameServer()

@app.websocket("/ws/{game_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, client_id: str):
    player_id = await game_server.connect(websocket, game_id)
    if not player_id:
        await websocket.close(code=1008, reason="Game is full")
        return
    
    try:
        while True:
            data = await websocket.receive_json()
            game = game_server.get_game(game_id)
            if not game:
                break
                
            response = await game_server.process_game_update(game, player_id, data)
            await websocket.send_json(response)
            
            # Check for winner
            if response["heads_hit"] >= 3:
                await websocket.send_json({"game_over": True, "winner": player_id})
                logger.info(f"Player {player_id} wins the game!")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for player {player_id}")
    except Exception as e:
        logger.error(f"Error in game loop: {e}")
    finally:
        await game_server.disconnect(websocket, player_id, game_id)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Airplane Game Server is running"}

@app.get("/stats")
async def stats():
    """Server statistics endpoint."""
    main_game = game_server.get_game("main")
    return {
        "active_connections": len(game_server.active_connections),
        "players_in_main_game": len(main_game.players) if main_game else 0,
        "game_phase": "placement" if main_game and main_game.placement_phase else "playing"
    }

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )