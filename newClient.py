import pygame
import asyncio
import websockets
import json
from queue import Queue
import threading
from typing import List, Tuple, Optional
import random
import logging
from dataclasses import dataclass

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize pygame
pygame.init()

# Constants
WIDTH = 1280
HEIGHT = 720
PADDING = 20
TOP_MARGIN = 60
GRID_SPACING = 40
ROWS = COLS = 10

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GOLD = (255, 215, 0)
SKY_BLUE = (135, 206, 235)
GRAY = (100, 100, 100)

# Calculate grid dimensions
cell_size = min((WIDTH - 2 * PADDING - GRID_SPACING) // (2 * COLS),
                (HEIGHT - 2 * PADDING - TOP_MARGIN) // ROWS)

# Grid positions
grid1_x = PADDING
grid1_y = PADDING + TOP_MARGIN
grid2_x = PADDING + COLS * cell_size + GRID_SPACING
grid2_y = PADDING + TOP_MARGIN

@dataclass
class Position:
    x: int
    y: int

class Airplane:
    def __init__(self, head_position: Position, orientation: str):
        self.head_pos = head_position
        self.orientation = orientation
        self.color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )

    def get_positions(self) -> List[Tuple[int, int]]:
        positions = []
        x, y = self.head_pos.x, self.head_pos.y
        
        if self.orientation == 'up':
            positions = [(x, y), (x, y+1), (x-2, y+1), (x-1, y+1), 
                        (x+1, y+1), (x+2, y+1), (x, y+2), (x, y+3), 
                        (x-1, y+3), (x+1, y+3)]
        elif self.orientation == 'down':
            positions = [(x, y), (x, y-1), (x-2, y-1), (x-1, y-1), 
                        (x+1, y-1), (x+2, y-1), (x, y-2), (x, y-3), 
                        (x-1, y-3), (x+1, y-3)]
        elif self.orientation == 'left':
            positions = [(x, y), (x-1, y), (x-1, y-2), (x-1, y-1), 
                        (x-1, y+1), (x-1, y+2), (x-2, y), (x-3, y), 
                        (x-3, y-1), (x-3, y+1)]
        elif self.orientation == 'right':
            positions = [(x, y), (x+1, y), (x+1, y-2), (x+1, y-1), 
                        (x+1, y+1), (x+1, y+2), (x+2, y), (x+3, y), 
                        (x+3, y-1), (x+3, y+1)]
        return positions

class NetworkClient:
    def __init__(self):
        self.server = "ws://localhost:8000"  # Change to your Render URL when deployed
        self.game_id = "main"
        self.websocket = None
        self.id = None
        self.message_queue = Queue()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def connect_websocket(self):
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                self.websocket = await websockets.connect(
                    f"{self.server}/ws/{self.game_id}/player")
                self.connected = True
                self.reconnect_attempts = 0
                asyncio.create_task(self.message_listener())
                logger.info("Connected to server successfully")
                return True
            except Exception as e:
                self.reconnect_attempts += 1
                logger.error(f"Connection attempt {self.reconnect_attempts} failed: {e}")
                await asyncio.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
        return False

    async def message_listener(self):
        while self.connected:
            try:
                message = await self.websocket.recv()
                self.message_queue.put(json.loads(message))
            except websockets.exceptions.ConnectionClosed:
                self.connected = False
                logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break

    def connect(self):
        return asyncio.run(self.connect_websocket())

    def send(self, data):
        if not self.connected:
            return None

        asyncio.run(self.send_async(data))
        try:
            return self.message_queue.get(timeout=5)
        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return None

    async def send_async(self, data):
        try:
            await self.websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            self.connected = False

class GameState:
    def __init__(self):
        self.placement_phase = True
        self.my_turn = False
        self.planes_placed = 0
        self.max_airplanes = 3
        self.opponent_ready = False
        self.heads_hit = 0
        self.opponent_heads_hit = 0
        self.my_shots = [[False for _ in range(10)] for _ in range(10)]
        self.opponent_shots = [[False for _ in range(10)] for _ in range(10)]
        self.head_positions = []
        self.shot_results = {}
        self.flags = [[False for _ in range(10)] for _ in range(10)]

def can_place_airplane(grid: List[List[tuple]], airplane: Airplane) -> bool:
    for pos in airplane.get_positions():
        if pos[0] < 0 or pos[0] >= len(grid[0]) or pos[1] < 0 or pos[1] >= len(grid):
            return False
        if grid[pos[1]][pos[0]] != WHITE:
            return False
    return True

def place_airplane(grid: List[List[tuple]], airplane: Airplane):
    for pos in airplane.get_positions():
        grid[pos[1]][pos[0]] = airplane.color

def draw_shot_marker(surface, x: int, y: int, shot_type: str):
    center = (x + cell_size // 2, y + cell_size // 2)
    if shot_type == "miss":
        margin = cell_size // 4
        pygame.draw.line(surface, BLUE, (x + margin, y + margin),
                        (x + cell_size - margin, y + cell_size - margin), 2)
        pygame.draw.line(surface, BLUE, (x + cell_size - margin, y + margin),
                        (x + margin, y + cell_size - margin), 2)
    elif shot_type == "hit":
        pygame.draw.circle(surface, RED, center, cell_size // 4)
    elif shot_type == "head":
        radius = cell_size // 3
        pygame.draw.circle(surface, GOLD, center, radius)
        pygame.draw.circle(surface, RED, center, radius - 4)
        margin = radius // 2
        pygame.draw.line(surface, GOLD,
                        (center[0] - margin, center[1] - margin),
                        (center[0] + margin, center[1] + margin), 3)
        pygame.draw.line(surface, GOLD,
                        (center[0] + margin, center[1] - margin),
                        (center[0] - margin, center[1] + margin), 3)

def draw_flag(surface, x: int, y: int):
    margin = cell_size // 8
    pygame.draw.line(surface, GRAY,
                    (x + margin, y + margin),
                    (x + cell_size - margin, y + cell_size - margin), 2)
    pygame.draw.line(surface, GRAY,
                    (x + cell_size - margin, y + margin),
                    (x + margin, y + cell_size - margin), 2)

def main():
    # Initialize window
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Airplane Game")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    # Initialize game objects
    game_state = GameState()
    network = NetworkClient()
    my_grid = [[WHITE for _ in range(COLS)] for _ in range(ROWS)]
    current_orientation = 'up'

    # Connect to server
    if not network.connect():
        logger.error("Failed to connect to server")
        return

    running = True
    while running:
        clock.tick(60)

        # Get network data
        try:
            game_data = network.send({
                "grid": my_grid,
                "shots": game_state.my_shots,
                "head_positions": game_state.head_positions
            })

            if game_data:
                game_state.opponent_ready = game_data.get("opponent_ready", False)
                game_state.my_turn = game_data.get("your_turn", False)
                game_state.placement_phase = game_data.get("placement_phase", True)
                game_state.opponent_shots = game_data.get("opponent_shots", [])
                game_state.heads_hit = game_data.get("heads_hit", 0)
                game_state.opponent_heads_hit = game_data.get("opponent_heads_hit", 0)
                if "shot_results" in game_data:
                    game_state.shot_results.update(game_data["shot_results"])

                # Check for game over
                if game_data.get("game_over", False):
                    winner = "You win!" if game_data.get("winner") == network.id else "Opponent wins!"
                    logger.info(f"Game Over: {winner}")
        except Exception as e:
            logger.error(f"Network error: {e}")
            running = False
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and game_state.placement_phase:
                if event.key == pygame.K_UP:
                    current_orientation = 'up'
                elif event.key == pygame.K_DOWN:
                    current_orientation = 'down'
                elif event.key == pygame.K_LEFT:
                    current_orientation = 'left'
                elif event.key == pygame.K_RIGHT:
                    current_orientation = 'right'

            elif event.type == pygame.MOUSEBUTTONUP:
                pos = pygame.mouse.get_pos()

                # Right click for flagging
                if event.button == 3 and not game_state.placement_phase:
                    if (grid2_x <= pos[0] < grid2_x + COLS * cell_size and
                            grid2_y <= pos[1] < grid2_y + ROWS * cell_size):
                        col = (pos[0] - grid2_x) // cell_size
                        row = (pos[1] - grid2_y) // cell_size
                        if not game_state.my_shots[row][col]:
                            game_state.flags[row][col] = not game_state.flags[row][col]
                    continue

                # Left click handling
                if event.button == 1:
                    if game_state.placement_phase:
                        if (grid1_x <= pos[0] < grid1_x + COLS * cell_size and
                                grid1_y <= pos[1] < grid1_y + ROWS * cell_size):
                            if game_state.planes_placed < game_state.max_airplanes:
                                col = (pos[0] - grid1_x) // cell_size
                                row = (pos[1] - grid1_y) // cell_size
                                airplane = Airplane(Position(col, row), current_orientation)
                                if can_place_airplane(my_grid, airplane):
                                    place_airplane(my_grid, airplane)
                                    game_state.planes_placed += 1
                                    game_state.head_positions.append((row, col))

                    elif game_state.my_turn:
                        if (grid2_x <= pos[0] < grid2_x + COLS * cell_size and
                                grid2_y <= pos[1] < grid2_y + ROWS * cell_size):
                            col = (pos[0] - grid2_x) // cell_size
                            row = (pos[1] - grid2_y) // cell_size
                            if not game_state.my_shots[row][col]:
                                game_state.my_shots[row][col] = True
                                game_state.flags[row][col] = False

        # Draw game state
        win.fill(SKY_BLUE)

        # Draw grids
        for row in range(ROWS):
            for col in range(COLS):
                # Left grid (my grid)
                rect1 = pygame.Rect(grid1_x + col * cell_size,
                                  grid1_y + row * cell_size,
                                  cell_size, cell_size)
                pygame.draw.rect(win, my_grid[row][col], rect1)
                pygame.draw.rect(win, BLACK, rect1, 1)

                # Right grid (opponent's grid)
                rect2 = pygame.Rect(grid2_x + col * cell_size,
                                  grid2_y + row * cell_size,
                                  cell_size, cell_size)
                pygame.draw.rect(win, WHITE, rect2)
                pygame.draw.rect(win, BLACK, rect2, 1)

        # Draw shots and flags
        if not game_state.placement_phase:
            # Draw my shots and flags on right grid
            for row in range(ROWS):
                for col in range(COLS):
                    if game_state.my_shots[row][col]:
                        shot_result = game_state.shot_results.get((row, col), "miss")
                        draw_shot_marker(win, grid2_x + col * cell_size,
                                       grid2_y + row * cell_size, shot_result)
                    elif game_state.flags[row][col]:
                        draw_flag(win, grid2_x + col * cell_size,
                                grid2_y + row * cell_size)

            # Draw opponent's shots on my grid
            for shot in game_state.opponent_shots:
                row, col = shot
                if (row, col) in game_state.head_positions:
                    shot_type = "head"
                elif my_grid[row][col] != WHITE:
                    shot_type = "hit"
                else:
                    shot_type = "miss"
                draw_shot_marker(win, grid1_x + col * cell_size,
                               grid1_y + row * cell_size, shot_type)

        # Draw UI text
        if game_state.placement_phase:
            status = f"Place your planes: {game_state.planes_placed}/{game_state.max_airplanes}"
            if game_state.planes_placed >= game_state.max_airplanes:
                status += " - Waiting for opponent..."
        else:
            status = "Your turn!" if game_state.my_turn else "Opponent's turn..."
        
        status_text = font.render(status, True, BLACK)
        score_text = font.render(f"Heads Hit - You: {game_state.heads_hit} Opponent: {game_state.opponent_heads_hit}", True, BLACK)
        
        status_rect = status_text.get_rect(centerx=WIDTH // 2, y=PADDING)
        score_rect = score_text.get_rect(x=PADDING, bottom=HEIGHT - PADDING)
        
        win.blit(status_text, status_rect)
        win.blit(score_text, score_rect)
        
        # Check for winner
        if game_state.heads_hit >= 3 or game_state.opponent_heads_hit >= 3:
            winner = "You win!" if game_state.heads_hit >= 3 else "Opponent wins!"
            winner_text = font.render(winner, True, BLACK)
            winner_rect = winner_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            pygame.draw.rect(win, WHITE, winner_rect.inflate(20, 20))
            win.blit(winner_text, winner_rect)

        pygame.display.update()

    pygame.quit()

if __name__ == "__main__":
    main()