// /static/menu/GameIntegration.js

const GameIntegration = () => {
    const [gameState, setGameState] = React.useState('menu');
    const [playerConfig, setPlayerConfig] = React.useState({
        callsign: '',
        colorScheme: 'naval'
    });

    // Initialize the game with the selected configuration
    const startGame = (config) => {
        setPlayerConfig(config);
        setGameState('game');
        
        // Hide the React container and show the game container
        document.getElementById('react-container').style.display = 'none';
        document.getElementById('game-container').style.display = 'flex';
        
        // Initialize the game with the configuration
        initializeGame(config);
    };

    // Return to menu
    const returnToMenu = () => {
        setGameState('menu');
        
        // Show the React container and hide the game container
        document.getElementById('react-container').style.display = 'flex';
        document.getElementById('game-container').style.display = 'none';
        
        // Cleanup the existing game
        if (typeof disconnectWebSocket === 'function') {
            disconnectWebSocket();
        }
        if (typeof removeAllEventListeners === 'function') {
            removeAllEventListeners();
        }
    };

    // Modified game initialization
    const initializeGame = (config) => {
        // Color schemes definition
        const colorSchemes = {
            naval: {
                colors: [
                    ['#1F4E79', '#2E74B5', '#4472C4'],
                    ['#203864', '#2F5597', '#4472C4'],
                    ['#1C3D5A', '#2A5A8C', '#3E7AB6']
                ]
            },
            desert: {
                colors: [
                    ['#C4A484', '#D4B59E', '#E6CCBB'],
                    ['#8B7355', '#A68B6C', '#C1A383'],
                    ['#B4916C', '#C9A785', '#DEC19E']
                ]
            },
            // ... other schemes
        };

        // Store selected color scheme globally for the game
        window.selectedColorScheme = colorSchemes[config.colorScheme].colors;

        // Initialize game components using your existing functions
        if (typeof createGrid === 'function') {
            createGrid('my-grid');
            createGrid('opponent-grid', true);
        }
        if (typeof setupRotationControls === 'function') {
            setupRotationControls();
        }
        if (typeof initializeWebSocket === 'function') {
            initializeWebSocket();
        }

        // Update status with player callsign
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = `Welcome, ${config.callsign}! Waiting for opponent...`;
        }
    };

    return React.createElement(
        React.Fragment,
        null,
        React.createElement(
            'div',
            {
                id: 'react-container',
                style: { 
                    display: gameState === 'menu' ? 'flex' : 'none',
                    minHeight: '100vh',
                    width: '100%'
                }
            },
            React.createElement(GameMenu, { onStartGame: startGame })
        ),
        React.createElement(
            'div',
            {
                id: 'game-container',
                style: { display: gameState === 'game' ? 'flex' : 'none' }
            }
            // Game container content is already in your HTML
        )
    );
};

// Export for use in the page
window.GameIntegration = GameIntegration;