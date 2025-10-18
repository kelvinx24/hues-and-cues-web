# Hues and Cues Web - Quick Start Guide

## What is Hues and Cues?

Hues and Cues is a vibrant guessing game where one player (the Cue Giver) tries to help other players guess a specific color on a game board by giving creative color-based clues.

## Quick Start

### 1. Start the Backend Server

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend will run on `http://localhost:8000`

### 2. Start the Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000`

### 3. Play the Game

1. Open `http://localhost:3000` in your browser
2. Enter your name
3. Click "Create New Game" to start a new game room
4. Share the Game ID with friends
5. Wait for at least 2 players to join
6. Click "Start Game"
7. The Cue Giver sees their target color and gives clues
8. Other players click colors on the board to guess
9. Points are awarded for correct guesses!

## Game Rules

- **Cue Giver**: Sees the target color and gives creative clues to help others guess
- **Guessers**: Click on colors they think match the clues
- **Scoring**: 
  - Correct guesser gets 5 points
  - Cue Giver gets 3 points when someone guesses correctly
- **Distance Feedback**: When you guess wrong, you see how far you are from the target

## Features

- 100 unique colors in a 10x10 grid
- Support for 2-10 players
- Real-time game state updates
- Turn-based gameplay
- Visual feedback with target markers
- Score tracking
- Clue history

## Technology Stack

- **Backend**: Python 3.8+, FastAPI, Uvicorn
- **Frontend**: React 18, Vite
- **Styling**: Modern CSS with gradients and animations

## API Documentation

The API is documented and accessible at `http://localhost:8000/docs` when the backend is running.

## Development

### Backend Development
- Modify `backend/main.py` to change game logic
- The server auto-reloads on file changes with uvicorn

### Frontend Development
- Modify files in `frontend/src/`
- Vite provides hot module replacement for instant updates
- Main game logic is in `frontend/src/App.jsx`
- Styling is in `frontend/src/App.css`

## Troubleshooting

**Backend won't start:**
- Make sure you have Python 3.8+ installed
- Install dependencies: `pip install -r requirements.txt`

**Frontend won't start:**
- Make sure you have Node.js 16+ installed
- Delete `node_modules` and run `npm install` again

**Can't connect to backend:**
- Make sure backend is running on port 8000
- Check CORS settings in `backend/main.py`

**Game state not updating:**
- The app polls every 2 seconds - wait a moment for updates
- Refresh the page if needed
- For production, consider implementing WebSockets for real-time updates

## Future Enhancements

- WebSocket support for real-time updates
- Persistent storage with database
- User authentication
- Game history and statistics
- Multiple game modes
- Mobile app version
- Chat system
- Sound effects and animations

Enjoy playing Hues and Cues!
