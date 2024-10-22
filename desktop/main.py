import pygame
from airplane import *

class GameState:
    def __init__(self):
        self.current_player = 1
        self.max_airplanes = 3
        self.player1_airplanes = 0
        self.player2_airplanes = 0
        self.placement_phase = True
        # New attributes for shooting phase
        self.shots_grid1 = [[False for _ in range(10)] for _ in range(10)]  # Track shots on grid 1
        self.shots_grid2 = [[False for _ in range(10)] for _ in range(10)]  # Track shots on grid 2
        self.hits_player1 = 0  # Track hits for player 1
        self.hits_player2 = 0  # Track hits for player 2
        
    def can_place_airplane(self, player):
        if player == 1:
            return self.player1_airplanes < self.max_airplanes
        return self.player2_airplanes < self.max_airplanes
        
    def add_airplane(self, player):
        if player == 1:
            self.player1_airplanes += 1
        else:
            self.player2_airplanes += 1
        
        # Check if placement phase is complete
        if self.player1_airplanes >= self.max_airplanes and self.player2_airplanes >= self.max_airplanes:
            self.placement_phase = False
            
    def switch_turn(self):
        self.current_player = 3 - self.current_player  # Switches between 1 and 2
        
    def get_winner(self):
        if self.hits_player1 >= 30:  # Each plane has 10 cells, 3 planes = 30 hits needed
            return 1
        elif self.hits_player2 >= 30:
            return 2
        return None

# Window settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
TOP_MARGIN = 60

# Colors
SKY_BLUE = (135, 206, 235)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

# pygame setup
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
clock = pygame.time.Clock()
running = True

game_state = GameState()
font = pygame.font.Font(None, 36)

# Grid settings
ROWS, COLS = 10, 10
PADDING = 20
GRID_SPACING = 40

# Calculate the maximum cell size that fits within the available space
max_cell_width = (WINDOW_WIDTH - 2 * PADDING - GRID_SPACING) // (2 * COLS)
max_cell_height = (WINDOW_HEIGHT - 2 * PADDING - TOP_MARGIN) // ROWS
cell_size = min(max_cell_width, max_cell_height)

# Calculate grid positions
grid1_x = PADDING
grid1_y = PADDING + TOP_MARGIN
grid2_x = PADDING + COLS * cell_size + GRID_SPACING
grid2_y = PADDING + TOP_MARGIN

# Initialize grid colors
grid_colors = [[(255, 255, 255) for _ in range(COLS)] for _ in range(ROWS)]
grid_colors2 = [[(255, 255, 255) for _ in range(COLS)] for _ in range(ROWS)]

current_orientation = 'up'

def process_shot(grid_colors, shots_grid, row, col):
    """Process a shot and return whether it was a hit"""
    shots_grid[row][col] = True
    if grid_colors[row][col] != WHITE:  # If the cell is not white, it's a hit
        return True
    return False

def draw_shot_marker(screen, x, y, is_hit):
    """Draw a marker for a shot (X for miss, circle for hit)"""
    if is_hit:
        # Draw a red circle for hit
        pygame.draw.circle(screen, RED, (x + cell_size // 2, y + cell_size // 2), 
                         cell_size // 4)
    else:
        # Draw an X for miss
        margin = cell_size // 4
        pygame.draw.line(screen, BLUE, (x + margin, y + margin), 
                        (x + cell_size - margin, y + cell_size - margin), 2)
        pygame.draw.line(screen, BLUE, (x + cell_size - margin, y + margin), 
                        (x + margin, y + cell_size - margin), 2)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if game_state.placement_phase:
                if event.key == pygame.K_UP:
                    current_orientation = 'up'
                elif event.key == pygame.K_DOWN:
                    current_orientation = 'down'
                elif event.key == pygame.K_LEFT:
                    current_orientation = 'left'
                elif event.key == pygame.K_RIGHT:
                    current_orientation = 'right'
        elif event.type == pygame.MOUSEBUTTONUP:
            mouse_x, mouse_y = event.pos
            
            if game_state.placement_phase:
                # Placement phase logic
                if grid1_x <= mouse_x < grid1_x + COLS * cell_size and grid1_y <= mouse_y < grid1_y + ROWS * cell_size:
                    if game_state.current_player == 1 and game_state.can_place_airplane(1):
                        col = (mouse_x - grid1_x) // cell_size
                        row = (mouse_y - grid1_y) // cell_size
                        airplane = Avion(Pozitie(col, row), current_orientation)
                        if can_place_airplane(grid_colors, airplane):
                            place_airplane(grid_colors, airplane)
                            game_state.add_airplane(1)
                            game_state.switch_turn()
                elif grid2_x <= mouse_x < grid2_x + COLS * cell_size and grid2_y <= mouse_y < grid2_y + ROWS * cell_size:
                    if game_state.current_player == 2 and game_state.can_place_airplane(2):
                        col = (mouse_x - grid2_x) // cell_size
                        row = (mouse_y - grid2_y) // cell_size
                        airplane = Avion(Pozitie(col, row), current_orientation)
                        if can_place_airplane(grid_colors2, airplane):
                            place_airplane(grid_colors2, airplane)
                            game_state.add_airplane(2)
                            game_state.switch_turn()
            else:
                # Shooting phase logic
                if game_state.current_player == 1:
                    # Player 1 shoots at grid 2
                    if grid2_x <= mouse_x < grid2_x + COLS * cell_size and grid2_y <= mouse_y < grid2_y + ROWS * cell_size:
                        col = (mouse_x - grid2_x) // cell_size
                        row = (mouse_y - grid2_y) // cell_size
                        if not game_state.shots_grid2[row][col]:  # Check if not already shot
                            if process_shot(grid_colors2, game_state.shots_grid2, row, col):
                                game_state.hits_player1 += 1
                            game_state.switch_turn()
                else:
                    # Player 2 shoots at grid 1
                    if grid1_x <= mouse_x < grid1_x + COLS * cell_size and grid1_y <= mouse_y < grid1_y + ROWS * cell_size:
                        col = (mouse_x - grid1_x) // cell_size
                        row = (mouse_y - grid1_y) // cell_size
                        if not game_state.shots_grid1[row][col]:  # Check if not already shot
                            if process_shot(grid_colors, game_state.shots_grid1, row, col):
                                game_state.hits_player2 += 1
                            game_state.switch_turn()

    # Fill background
    screen.fill(SKY_BLUE)

    # Draw the grids
    for row in range(ROWS):
        for col in range(COLS):
            # Draw grid 1
            rect1 = pygame.Rect(grid1_x + col * cell_size, 
                              grid1_y + row * cell_size, 
                              cell_size, cell_size)
            color1 = grid_colors[row][col] if game_state.current_player == 1 else WHITE
            pygame.draw.rect(screen, color1, rect1)
            pygame.draw.rect(screen, BLACK, rect1, 1)
            
            # Draw grid 2
            rect2 = pygame.Rect(grid2_x + col * cell_size, 
                              grid2_y + row * cell_size, 
                              cell_size, cell_size)
            color2 = grid_colors2[row][col] if game_state.current_player == 2 else WHITE
            pygame.draw.rect(screen, color2, rect2)
            pygame.draw.rect(screen, BLACK, rect2, 1)
            
            # Draw shot markers
            if not game_state.placement_phase:
                # Draw shots on grid 1
                if game_state.shots_grid1[row][col]:
                    is_hit = grid_colors[row][col] != WHITE
                    draw_shot_marker(screen, grid1_x + col * cell_size, 
                                   grid1_y + row * cell_size, is_hit)
                
                # Draw shots on grid 2
                if game_state.shots_grid2[row][col]:
                    is_hit = grid_colors2[row][col] != WHITE
                    draw_shot_marker(screen, grid2_x + col * cell_size, 
                                   grid2_y + row * cell_size, is_hit)

    # Render text
    if game_state.placement_phase:
        phase_text = "Placement Phase"
    else:
        phase_text = "Shooting Phase"
    
    phase_text = font.render(phase_text, True, BLACK)
    turn_text = font.render(f"Player {game_state.current_player}'s Turn", True, BLACK)
    
    if game_state.placement_phase:
        p1_text = f"P1 Planes: {game_state.player1_airplanes}/{game_state.max_airplanes}"
        p2_text = f"P2 Planes: {game_state.player2_airplanes}/{game_state.max_airplanes}"
    else:
        p1_text = f"P1 Hits: {game_state.hits_player1}/30"
        p2_text = f"P2 Hits: {game_state.hits_player2}/30"
    
    p1_planes = font.render(p1_text, True, BLACK)
    p2_planes = font.render(p2_text, True, BLACK)
    
    # Calculate text positions
    phase_text_rect = phase_text.get_rect(centerx=WINDOW_WIDTH // 2, y=PADDING // 2)
    turn_text_rect = turn_text.get_rect(centerx=WINDOW_WIDTH // 2, y=PADDING * 1.5)
    p1_planes_rect = p1_planes.get_rect(x=grid1_x, bottom=WINDOW_HEIGHT - PADDING)
    p2_planes_rect = p2_planes.get_rect(x=grid2_x, bottom=WINDOW_HEIGHT - PADDING)

    # Draw text
    screen.blit(phase_text, phase_text_rect)
    screen.blit(turn_text, turn_text_rect)
    screen.blit(p1_planes, p1_planes_rect)
    screen.blit(p2_planes, p2_planes_rect)
    
    # Check for winner
    winner = game_state.get_winner()
    if winner:
        winner_text = font.render(f"Player {winner} Wins!", True, BLACK)
        winner_rect = winner_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        pygame.draw.rect(screen, WHITE, winner_rect.inflate(20, 20))
        screen.blit(winner_text, winner_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()