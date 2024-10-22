import pygame
import socket
import pickle
from airplane import *

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
        self.flags = [[False for _ in range(10)] for _ in range(10)]  # Added flags grid

class NetworkClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = "localhost"
        self.port = 5555
        self.addr = (self.server, self.port)
        self.id = self.connect()
        
    def connect(self):
        try:
            self.client.connect(self.addr)
            return self.client.recv(2048).decode()
        except:
            pass
            
    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            return pickle.loads(self.client.recv(2048))
        except socket.error as e:
            print(e)
            return None

# Initialize pygame
pygame.init()
WIDTH = 1280
HEIGHT = 720
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Airplane Game")

# Colors and constants
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GOLD = (255, 215, 0)
SKY_BLUE = (135, 206, 235)
GRAY = (100, 100, 100)

PADDING = 20
TOP_MARGIN = 60
GRID_SPACING = 40
ROWS = COLS = 10

# Calculate grid dimensions
cell_size = min((WIDTH - 2 * PADDING - GRID_SPACING) // (2 * COLS),
                (HEIGHT - 2 * PADDING - TOP_MARGIN) // ROWS)

# Grid positions
grid1_x = PADDING
grid1_y = PADDING + TOP_MARGIN
grid2_x = PADDING + COLS * cell_size + GRID_SPACING
grid2_y = PADDING + TOP_MARGIN

game_state = GameState()
network = NetworkClient()
my_grid = [[(255, 255, 255) for _ in range(COLS)] for _ in range(ROWS)]
current_orientation = 'up'
font = pygame.font.Font(None, 36)

def draw_shot_marker(surface, x, y, shot_type):
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

def draw_flag(surface, x, y):
    """Draw a flag marker to indicate deduced empty cell"""
    margin = cell_size // 8
    # Draw an X with thinner lines and in gray color
    pygame.draw.line(surface, GRAY, 
                    (x + margin, y + margin),
                    (x + cell_size - margin, y + cell_size - margin), 2)
    pygame.draw.line(surface, GRAY,
                    (x + cell_size - margin, y + margin),
                    (x + margin, y + cell_size - margin), 2)

run = True
clock = pygame.time.Clock()

while run:
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
    except:
        run = False
        print("Couldn't get game")
        break

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            pygame.quit()
            
        if event.type == pygame.KEYDOWN and game_state.placement_phase:
            if event.key == pygame.K_UP:
                current_orientation = 'up'
            elif event.key == pygame.K_DOWN:
                current_orientation = 'down'
            elif event.key == pygame.K_LEFT:
                current_orientation = 'left'
            elif event.key == pygame.K_RIGHT:
                current_orientation = 'right'
                
        if event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            
            # Right click for flagging (only on opponent's grid and not in placement phase)
            if event.button == 3 and not game_state.placement_phase:  # Right click
                if (grid2_x <= pos[0] < grid2_x + COLS * cell_size and 
                    grid2_y <= pos[1] < grid2_y + ROWS * cell_size):
                    col = (pos[0] - grid2_x) // cell_size
                    row = (pos[1] - grid2_y) // cell_size
                    if not game_state.my_shots[row][col]:  # Only flag unshot cells
                        game_state.flags[row][col] = not game_state.flags[row][col]  # Toggle flag
                continue
            
            # Left click handling
            if event.button == 1:
                if game_state.placement_phase:
                    if (grid1_x <= pos[0] < grid1_x + COLS * cell_size and 
                        grid1_y <= pos[1] < grid1_y + ROWS * cell_size):
                        if game_state.planes_placed < game_state.max_airplanes:
                            col = (pos[0] - grid1_x) // cell_size
                            row = (pos[1] - grid1_y) // cell_size
                            airplane = Avion(Pozitie(col, row), current_orientation)
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
                            game_state.flags[row][col] = False  # Remove flag if cell is shot

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
                elif game_state.flags[row][col]:  # Draw flags on unshot cells
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