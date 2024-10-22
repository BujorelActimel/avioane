import random

class Pozitie:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

class Avion:
    def __init__(self, pozitieCap: Pozitie, orientare: str):
        self.pozCap = pozitieCap
        self.orientare = orientare
        # Generate a random color for each airplane
        self.color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )

    def get_positions(self):
        positions = []
        x, y = self.pozCap.x, self.pozCap.y
        if self.orientare == 'up':
            positions = [(x, y), (x, y+1), (x-2, y+1), (x-1, y+1), (x+1, y+1), (x+2, y+1), (x, y+2), (x, y+3), (x-1, y+3), (x+1, y+3)]
        elif self.orientare == 'down':
            positions = [(x, y), (x, y-1), (x-2, y-1), (x-1, y-1), (x+1, y-1), (x+2, y-1), (x, y-2), (x, y-3), (x-1, y-3), (x+1, y-3)]
        elif self.orientare == 'left':
            positions = [(x, y), (x-1, y), (x-1, y-2), (x-1, y-1), (x-1, y+1), (x-1, y+2), (x-2, y), (x-3, y), (x-3, y-1), (x-3, y+1)]
        elif self.orientare == 'right':
            positions = [(x, y), (x+1, y), (x+1, y-2), (x+1, y-1), (x+1, y+1), (x+1, y+2), (x+2, y), (x+3, y), (x+3, y-1), (x+3, y+1)]
        return positions

def can_place_airplane(grid, airplane):
    for pos in airplane.get_positions():
        if pos[0] < 0 or pos[0] >= len(grid[0]) or pos[1] < 0 or pos[1] >= len(grid):
            return False
        if grid[pos[1]][pos[0]] != (255, 255, 255):
            return False
    return True

def place_airplane(grid, airplane):
    for pos in airplane.get_positions():
        grid[pos[1]][pos[0]] = airplane.color