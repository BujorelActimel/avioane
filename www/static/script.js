const WHITE = [255, 255, 255];
let currentOrientation = 'up';
let placementPhase = true;
let myTurn = false;
let planesPlaced = 0;
const maxAirplanes = 3;
let myGrid = Array(10).fill().map(() => Array(10).fill().map(() => WHITE));
let myShots = Array(10).fill().map(() => Array(10).fill(false));
let flags = Array(10).fill().map(() => Array(10).fill(false));
let headPositions = [];
let ws;
let opponentShots = new Set();
let shotResults = {};
let gameStats = {
    startTime: Date.now(),
    totalShots: 0,
    hits: 0
};
const previewStyles = `
.preview-cell {
    position: absolute;
    width: 100%;
    height: 100%;
    background-color: rgba(144, 238, 144, 0.5);  /* Light green */
    transition: all 0.2s ease;
}

.invalid-preview-cell {
    background-color: rgba(255, 99, 71, 0.5);  /* Light red */
}
`;
const styleSheet = document.createElement("style");
styleSheet.textContent = previewStyles;
document.head.appendChild(styleSheet);


function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket Connected');
        document.getElementById('status').textContent = 'Connected! Waiting for opponent...';
    };
    
    ws.onclose = () => {
        console.log('WebSocket Disconnected');
        document.getElementById('status').textContent = 'Disconnected from server';
        // Try to reconnect after 3 seconds
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            initializeWebSocket();
        }, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
    };

    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };
}

function showAirplanePreview(row, col) {
    if (!placementPhase || planesPlaced >= maxAirplanes) return;
    
    // Clear any existing preview
    clearAirplanePreview();
    
    const airplane = createAirplane(col, row, currentOrientation);
    const isValid = canPlaceAirplane(airplane);
    
    const myGridElement = document.getElementById('my-grid');
    
    airplane.forEach(([previewRow, previewCol]) => {
        if (previewRow >= 0 && previewRow < 10 && previewCol >= 0 && previewCol < 10) {
            const cell = myGridElement.children[previewRow * 10 + previewCol];
            const preview = document.createElement('div');
            preview.className = 'preview-cell';
            if (!isValid) {
                preview.classList.add('invalid-preview-cell');
            }
            cell.appendChild(preview);
        }
    });
}

function clearAirplanePreview() {
    const previewCells = document.querySelectorAll('.preview-cell');
    previewCells.forEach(cell => cell.remove());
}

function createGrid(elementId, isOpponentGrid = false) {
    const grid = document.getElementById(elementId);
    grid.innerHTML = '';
    
    for (let row = 0; row < 10; row++) {
        for (let col = 0; col < 10; col++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.row = row;
            cell.dataset.col = col;
            
            if (isOpponentGrid) {
                cell.addEventListener('click', () => handleOpponentGridClick(row, col));
                cell.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    handleFlag(row, col);
                });
            } else {
                cell.addEventListener('click', () => handleMyGridClick(row, col));
                // Add hover events for airplane placement
                cell.addEventListener('mouseenter', () => showAirplanePreview(row, col));
                cell.addEventListener('mouseleave', clearAirplanePreview);
            }
            
            grid.appendChild(cell);
        }
    }
}

function updateGridDisplay() {
    const myGridElement = document.getElementById('my-grid');
    for (let row = 0; row < 10; row++) {
        for (let col = 0; col < 10; col++) {
            const cell = myGridElement.children[row * 10 + col];
            const color = myGrid[row][col];
            cell.style.backgroundColor = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        }
    }
}

function handleMyGridClick(row, col) {
    if (!placementPhase || planesPlaced >= maxAirplanes) return;
    
    const airplane = createAirplane(col, row, currentOrientation);
    if (canPlaceAirplane(airplane)) {
        placeAirplane(airplane);
        planesPlaced++;
        headPositions.push([row, col]);
        updateGridDisplay();
        sendGameState();
    }
    clearAirplanePreview();
}

function handleOpponentGridClick(row, col) {
    if (placementPhase || !myTurn || myShots[row][col]) {
        console.log("Cannot shoot now:", {
            placementPhase,
            myTurn,
            alreadyShot: myShots[row][col]
        });
        return;
    }
    
    gameStats.totalShots++; // Track total shots
    myShots[row][col] = true;
    flags[row][col] = false;
    updateShotDisplay();
    sendGameState();
    myTurn = false;
    document.getElementById('status').textContent = "Opponent's turn...";
}

function handleFlag(row, col) {
    if (placementPhase || myShots[row][col]) return;
    flags[row][col] = !flags[row][col];
    updateShotDisplay();
}

function updateShotDisplay() {
    const opponentGrid = document.getElementById('opponent-grid');
    for (let row = 0; row < 10; row++) {
        for (let col = 0; col < 10; col++) {
            const cell = opponentGrid.children[row * 10 + col];
            // Remove existing markers
            cell.innerHTML = '';
            
            if (myShots[row][col]) {
                const marker = document.createElement('div');
                marker.className = 'shot-marker';
                const result = getShotResult([row, col]);
                marker.classList.add(result);
                cell.appendChild(marker);
            } else if (flags[row][col]) {
                const flag = document.createElement('div');
                flag.className = 'flag';
                cell.appendChild(flag);
            }
        }
    }
}

function getShotResult(shot) {
    const [row, col] = shot;
    const key = `${row},${col}`;
    return shotResults[key] || 'miss';
}

function createAirplane(x, y, orientation) {
    const positions = [];
    if (orientation === 'up') {
        positions.push([y, x], [y+1, x], [y+1, x-2], [y+1, x-1], [y+1, x+1], 
                     [y+1, x+2], [y+2, x], [y+3, x], [y+3, x-1], [y+3, x+1]);
    } else if (orientation === 'down') {
        positions.push([y, x], [y-1, x], [y-1, x-2], [y-1, x-1], [y-1, x+1],
                     [y-1, x+2], [y-2, x], [y-3, x], [y-3, x-1], [y-3, x+1]);
    } else if (orientation === 'right') {
        positions.push([y, x], [y, x-1], [y-2, x-1], [y-1, x-1], [y+1, x-1],
                     [y+2, x-1], [y, x-2], [y, x-3], [y-1, x-3], [y+1, x-3]);
    } else if (orientation === 'left') {
        positions.push([y, x], [y, x+1], [y-2, x+1], [y-1, x+1], [y+1, x+1],
                     [y+2, x+1], [y, x+2], [y, x+3], [y-1, x+3], [y+1, x+3]);
    }
    return positions;
}

function canPlaceAirplane(positions) {
    return positions.every(([row, col]) => {
        return row >= 0 && row < 10 && col >= 0 && col < 10 &&
               JSON.stringify(myGrid[row][col]) === JSON.stringify(WHITE);
    });
}

function placeAirplane(positions) {
    const color = [
        Math.floor(Math.random() * 256),
        Math.floor(Math.random() * 256),
        Math.floor(Math.random() * 256)
    ];
    positions.forEach(([row, col]) => {
        myGrid[row][col] = color;
    });
}

function sendGameState() {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            grid: myGrid,
            shots: myShots,
            head_positions: headPositions
        }));
    }
}

function updateOpponentShots(opponentShots) {
    const myGridElement = document.getElementById('my-grid');
    opponentShots.forEach(([row, col]) => {
        const cell = myGridElement.children[row * 10 + col];
        // Clear existing markers
        cell.innerHTML = '';
        const marker = document.createElement('div');
        marker.className = 'shot-marker';
        if (headPositions.some(([r, c]) => r === row && c === col)) {
            marker.classList.add('head');
        } else if (JSON.stringify(myGrid[row][col]) !== JSON.stringify(WHITE)) {
            marker.classList.add('hit');
        } else {
            marker.classList.add('miss');
        }
        cell.appendChild(marker);
    });
}

function handleServerMessage(data) {
    if (data.type === 'init') {
        document.getElementById('status').textContent = 'Waiting for opponent...';
    } else if (data.type === 'update' || data.type === 'opponent_update') {
        placementPhase = data.placement_phase;
        myTurn = data.your_turn;
        
        // Store shot results and track hits
        if (data.shot_results) {
            Object.entries(data.shot_results).forEach(([key, result]) => {
                if (!shotResults[key] && (result === 'hit' || result === 'head')) {
                    gameStats.hits++;
                }
            });
            shotResults = { ...shotResults, ...data.shot_results };
        }

        // Update status message
        let status = '';
        if (placementPhase) {
            const myPlanes = data.placement_status?.your_planes || planesPlaced;
            const opponentPlanes = data.placement_status?.opponent_planes || 0;
            
            if (myPlanes < maxAirplanes) {
                status = `Place your planes: ${myPlanes}/${maxAirplanes}`;
            } else if (opponentPlanes < maxAirplanes) {
                status = 'Waiting for opponent to finish placing planes...';
            } else {
                status = 'Game starting...';
            }
        } else {
            if (data.heads_hit >= 3 || data.opponent_heads_hit >= 3) {
                const isWinner = data.heads_hit >= 3;
                showVictoryScreen(isWinner);
                status = isWinner ? 'You win!' : 'Opponent wins!';
            } else {
                status = myTurn ? 'Your turn!' : "Opponent's turn...";
            }
        }
        document.getElementById('status').textContent = status;

        // Update score
        document.getElementById('score').textContent = 
            `Heads Hit - You: ${data.heads_hit || 0} Opponent: ${data.opponent_heads_hit || 0}`;

        // Update shot displays
        if (data.opponent_shots) {
            updateOpponentShots(data.opponent_shots);
        }
        updateShotDisplay();
    }
}

function showVictoryScreen(isWinner) {
    const overlay = document.getElementById('victoryOverlay');
    const title = document.getElementById('victoryTitle');
    const message = overlay.querySelector('.victory-message'); // Add this line if you don't have it

    // Calculate statistics
    const endTime = Date.now();
    const timePlayedSeconds = Math.floor((endTime - gameStats.startTime) / 1000);
    const minutes = Math.floor(timePlayedSeconds / 60);
    const seconds = timePlayedSeconds % 60;
    const hitRatio = gameStats.totalShots > 0 
        ? Math.round((gameStats.hits / gameStats.totalShots) * 100) 
        : 0;

    // Update statistics display
    document.getElementById('totalShots').textContent = gameStats.totalShots;
    document.getElementById('hitRatio').textContent = `${hitRatio}%`;
    document.getElementById('timePlayed').textContent = 
        `${minutes}:${seconds.toString().padStart(2, '0')}`;

    if (isWinner) {
        title.textContent = 'Victory!';
        overlay.classList.remove('defeat');
        createConfetti();
    } else {
        title.textContent = 'Defeat';
        if (message) message.textContent = "You suck!";
        overlay.classList.add('defeat');
    }

    // Show the overlay
    overlay.classList.add('active');
    
    // Set up victory screen buttons
    const playAgainBtn = overlay.querySelector('.play-again');
    const exitBtn = overlay.querySelector('.exit-game');
    
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', restartGame, { once: true });
    }
    if (exitBtn) {
        exitBtn.addEventListener('click', exitGame, { once: true });
    }
}

function createConfetti() {
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'];
    
    for (let i = 0; i < 100; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.left = `${Math.random() * 100}vw`;
        confetti.style.animationDelay = `${Math.random() * 3}s`;
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        
        document.getElementById('victoryOverlay').appendChild(confetti);
        
        // Remove confetti after animation
        setTimeout(() => confetti.remove(), 3000);
    }
}

function disconnectWebSocket() {
    if (ws) {
        // Remove all WebSocket event listeners
        ws.onopen = null;
        ws.onclose = null;
        ws.onmessage = null;
        ws.onerror = null;
        
        // Close the connection
        ws.close();
        ws = null;
    }
}

function removeAllEventListeners() {
    const myGrid = document.getElementById('my-grid');
    const opponentGrid = document.getElementById('opponent-grid');
    
    // Clear any existing preview before removing listeners
    clearAirplanePreview();
    
    // Clone and replace grids to remove all event listeners
    const newMyGrid = myGrid.cloneNode(true);
    const newOpponentGrid = opponentGrid.cloneNode(true);
    myGrid.parentNode.replaceChild(newMyGrid, myGrid);
    opponentGrid.parentNode.replaceChild(newOpponentGrid, opponentGrid);
    
    // Remove rotation control listeners
    ['rotate-up', 'rotate-right', 'rotate-down', 'rotate-left'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            const newElement = element.cloneNode(true);
            element.parentNode.replaceChild(newElement, element);
        }
    });
}

function setupRotationControls() {
    ['up', 'right', 'down', 'left'].forEach(direction => {
        const element = document.getElementById(`rotate-${direction}`);
        if (element) {
            const newElement = element.cloneNode(true);
            element.parentNode.replaceChild(newElement, element);
            newElement.addEventListener('click', () => {
                currentOrientation = direction;
                // Update preview if mouse is over grid
                const hoveredCell = document.querySelector('.preview-cell')?.parentElement;
                if (hoveredCell) {
                    const row = parseInt(hoveredCell.dataset.row);
                    const col = parseInt(hoveredCell.dataset.col);
                    clearAirplanePreview();
                    showAirplanePreview(row, col);
                }
            });
        }
    });
}

function exitGame() {
    // You can customize this to redirect to a menu or close the game
    window.close();
    // Fallback if window.close() is blocked
    document.body.innerHTML = '<div style="text-align: center; padding: 50px;"><h1>Thanks for playing!</h1><p>You can close this window now.</p></div>';
}

// Main initialization function
function initializeGame() {
    createGrid('my-grid');
    createGrid('opponent-grid', true);
    setupRotationControls();
    initializeWebSocket();
    
    // Add mouseover effects for opponent grid
    const opponentGrid = document.getElementById('opponent-grid');
    opponentGrid.addEventListener('mouseover', (e) => {
        const cell = e.target;
        if (cell.classList.contains('cell')) {
            const row = parseInt(cell.dataset.row);
            const col = parseInt(cell.dataset.col);
            if (!myShots[row][col]) {
                cell.style.cursor = 'pointer';
            }
        }
    });
}

function restartGame() {
    // Disconnect current WebSocket
    disconnectWebSocket();
    removeAllEventListeners();

    // Reset all game state variables
    currentOrientation = 'up';
    placementPhase = true;
    myTurn = false;
    planesPlaced = 0;
    myGrid = Array(10).fill().map(() => Array(10).fill().map(() => WHITE));
    myShots = Array(10).fill().map(() => Array(10).fill(false));
    flags = Array(10).fill().map(() => Array(10).fill(false));
    headPositions = [];
    opponentShots = new Set();
    shotResults = {};

    // Reset game statistics
    gameStats = {
        startTime: Date.now(),
        totalShots: 0,
        hits: 0
    };

    // Hide victory overlay and remove all confetti
    const victoryOverlay = document.getElementById('victoryOverlay');
    victoryOverlay.classList.remove('active');
    victoryOverlay.querySelectorAll('.confetti').forEach(el => el.remove());

    // Reset UI elements
    document.getElementById('status').textContent = 'Connecting to server...';
    document.getElementById('score').textContent = 'Heads Hit - You: 0 Opponent: 0';

    // Use the same initialization as the initial game setup
    initializeGame();
}

// Single initialization point
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeGame);
} else {
    initializeGame();
}

// Add window unload handler
window.addEventListener('beforeunload', () => {
    disconnectWebSocket();
});