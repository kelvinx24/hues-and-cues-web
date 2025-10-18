# 🎨 Hues and Cues Web

A web-based derivative version of the popular board game "Hues and Cues" built with Python, FastAPI, and React.

## About the Game

Hues and Cues is a vibrant guessing game where players give color-based clues to help others guess a specific color on a game board. One player is the "Cue Giver" who knows the target color and provides creative clues, while other players try to guess the correct color based on those clues.

## Features

- 🎮 **Real-time Multiplayer**: Play with 2-10 players
- 🎨 **480 Color Grid**: A vibrant board with diverse color options
- 💬 **Clue System**: Give creative color hints to your teammates
- 🏆 **Scoring System**: Points for correct guesses and successful clue-giving
- 🔄 **Turn-based Gameplay**: Take turns being the Cue Giver
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

### Backend
- **Python 3.8+**
- **FastAPI**: Modern, fast web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI library
- **Vite**: Build tool and dev server
- **Modern CSS**: Responsive design with gradients and animations

## Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:
```bash
python main.py
```

The backend API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install npm dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## How to Play

1. **Create or Join a Game**:
   - Enter your name
   - Click "Create New Game" to start a new room
   - Or enter a Game ID to join an existing game

2. **Wait in Lobby**:
   - Share the Game ID with friends
   - Wait for at least 2 players to join
   - Click "Start Game" when ready

3. **Play the Game**:
   - **Cue Giver**: You'll see your target color. Give creative clues to help others guess it!
   - **Guessers**: Read the clues and click on the color grid to make your guess
   - Points are awarded for correct guesses (5 points) and successful clue-giving (3 points)

4. **Scoring**:
   - Guesser gets 5 points for a correct guess
   - Cue Giver gets 3 points when someone guesses correctly
   - The distance from your guess to the target is shown for feedback

## API Endpoints

- `GET /` - API health check
- `POST /game/create` - Create a new game
- `POST /game/{game_id}/join` - Join an existing game
- `POST /game/{game_id}/start` - Start the game
- `GET /game/{game_id}` - Get game state
- `POST /game/{game_id}/clue` - Give a clue
- `POST /game/{game_id}/guess` - Make a guess
- `GET /colors` - Get the color board

## Development

### Running Tests
Currently, this project focuses on functionality. Test infrastructure can be added in future iterations.

### Building for Production

**Frontend**:
```bash
cd frontend
npm run build
```

The production build will be in `frontend/dist/`

### Project Structure
```
hues-and-cues-web/
├── backend/
│   ├── main.py              # FastAPI application
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   ├── App.css         # Styling
│   │   ├── main.jsx        # React entry point
│   │   └── index.css       # Global styles
│   ├── index.html          # HTML template
│   ├── vite.config.js      # Vite configuration
│   └── package.json        # npm dependencies
└── README.md               # This file
```

## Future Enhancements

- WebSocket support for real-time updates
- Persistent storage (database)
- Multiple game rooms management
- Chat system
- Game history and statistics
- Mobile app version
- Sound effects and animations
- Different game modes

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

Inspired by the board game "Hues and Cues" by The Op Games.