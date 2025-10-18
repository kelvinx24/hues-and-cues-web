import React, { useState, useEffect } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
  const [gameState, setGameState] = useState('menu') // menu, lobby, playing
  const [gameId, setGameId] = useState('')
  const [playerId, setPlayerId] = useState('')
  const [playerName, setPlayerName] = useState('')
  const [joinGameId, setJoinGameId] = useState('')
  const [gameData, setGameData] = useState(null)
  const [colors, setColors] = useState([])
  const [clueText, setClueText] = useState('')
  const [selectedColor, setSelectedColor] = useState(null)

  useEffect(() => {
    fetchColors()
  }, [])

  useEffect(() => {
    if (gameId && playerId && gameState !== 'menu') {
      const interval = setInterval(() => {
        fetchGameState()
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [gameId, playerId, gameState])

  const fetchColors = async () => {
    try {
      const response = await fetch(`${API_URL}/colors`)
      const data = await response.json()
      setColors(data.colors)
    } catch (error) {
      console.error('Failed to fetch colors:', error)
    }
  }

  const fetchGameState = async () => {
    try {
      const response = await fetch(`${API_URL}/game/${gameId}?player_id=${playerId}`)
      const data = await response.json()
      setGameData(data)
    } catch (error) {
      console.error('Failed to fetch game state:', error)
    }
  }

  const createGame = async () => {
    if (!playerName.trim()) {
      alert('Please enter your name')
      return
    }

    try {
      const response = await fetch(`${API_URL}/game/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: playerName })
      })
      const data = await response.json()
      setGameId(data.game_id)
      setPlayerId(data.player_id)
      setGameState('lobby')
      fetchGameState()
    } catch (error) {
      console.error('Failed to create game:', error)
      alert('Failed to create game')
    }
  }

  const joinGame = async () => {
    if (!playerName.trim() || !joinGameId.trim()) {
      alert('Please enter your name and game ID')
      return
    }

    try {
      const response = await fetch(`${API_URL}/game/${joinGameId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: playerName })
      })
      
      if (!response.ok) {
        throw new Error('Failed to join game')
      }
      
      const data = await response.json()
      setGameId(data.game_id)
      setPlayerId(data.player_id)
      setGameState('lobby')
      fetchGameState()
    } catch (error) {
      console.error('Failed to join game:', error)
      alert('Failed to join game. Check the game ID and try again.')
    }
  }

  const startGame = async () => {
    try {
      await fetch(`${API_URL}/game/${gameId}/start?player_id=${playerId}`, {
        method: 'POST'
      })
      setGameState('playing')
      fetchGameState()
    } catch (error) {
      console.error('Failed to start game:', error)
      alert('Failed to start game. Make sure you have at least 2 players.')
    }
  }

  const giveClue = async () => {
    if (!clueText.trim()) {
      alert('Please enter a clue')
      return
    }

    try {
      await fetch(`${API_URL}/game/${gameId}/clue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId, clue_text: clueText })
      })
      setClueText('')
      fetchGameState()
    } catch (error) {
      console.error('Failed to give clue:', error)
      alert('Failed to give clue')
    }
  }

  const makeGuess = async (row, col) => {
    try {
      const response = await fetch(`${API_URL}/game/${gameId}/guess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          player_id: playerId, 
          color_position: [row, col] 
        })
      })
      const data = await response.json()
      
      if (data.correct) {
        alert('Correct! 🎉')
      } else {
        alert(`Distance from target: ${data.distance}`)
      }
      
      fetchGameState()
    } catch (error) {
      console.error('Failed to make guess:', error)
      alert('Failed to make guess')
    }
  }

  const renderMenu = () => (
    <div className="menu-container">
      <h1 className="game-title">🎨 Hues and Cues</h1>
      <p className="game-subtitle">A vibrant color guessing game</p>
      
      <div className="menu-card">
        <input
          type="text"
          placeholder="Enter your name"
          value={playerName}
          onChange={(e) => setPlayerName(e.target.value)}
          className="input-field"
        />
        
        <button onClick={createGame} className="btn btn-primary">
          Create New Game
        </button>
        
        <div className="divider">OR</div>
        
        <input
          type="text"
          placeholder="Enter Game ID"
          value={joinGameId}
          onChange={(e) => setJoinGameId(e.target.value)}
          className="input-field"
        />
        
        <button onClick={joinGame} className="btn btn-secondary">
          Join Game
        </button>
      </div>
    </div>
  )

  const renderLobby = () => (
    <div className="lobby-container">
      <h1>Game Lobby</h1>
      
      <div className="game-info">
        <p className="game-id">Game ID: <strong>{gameId}</strong></p>
        <p className="share-text">Share this ID with friends to join!</p>
      </div>
      
      <div className="players-section">
        <h2>Players ({gameData?.players?.length || 0})</h2>
        <div className="players-list">
          {gameData?.players?.map((player, index) => (
            <div key={player.id} className="player-card">
              <span className="player-number">{index + 1}</span>
              <span className="player-name">{player.name}</span>
              {player.id === playerId && <span className="you-badge">YOU</span>}
            </div>
          ))}
        </div>
      </div>
      
      <button 
        onClick={startGame} 
        className="btn btn-primary"
        disabled={!gameData || gameData.players?.length < 2}
      >
        Start Game
      </button>
      
      <button onClick={() => setGameState('menu')} className="btn btn-secondary">
        Leave Game
      </button>
    </div>
  )

  const renderGame = () => {
    const isCurrentPlayer = gameData?.current_player === playerId
    const targetColor = gameData?.target_color

    return (
      <div className="game-container">
        <div className="game-header">
          <h1>🎨 Hues and Cues</h1>
          <div className="game-info-bar">
            <span>Game ID: {gameId}</span>
            <span>Players: {gameData?.players?.length}</span>
          </div>
        </div>

        <div className="game-content">
          <div className="sidebar">
            <div className="current-turn">
              {isCurrentPlayer ? (
                <div className="your-turn">
                  <h3>🎯 Your Turn!</h3>
                  <p>Give clues to help others guess your color</p>
                  {targetColor && (
                    <div 
                      className="target-color-preview"
                      style={{ backgroundColor: colors[targetColor[0]]?.[targetColor[1]] }}
                    >
                      Your Target Color
                    </div>
                  )}
                </div>
              ) : (
                <div className="others-turn">
                  <h3>Waiting...</h3>
                  <p>
                    {gameData?.players?.find(p => p.id === gameData?.current_player)?.name || 'Someone'}'s turn
                  </p>
                </div>
              )}
            </div>

            <div className="clues-section">
              <h3>Clues</h3>
              {isCurrentPlayer && (
                <div className="clue-input-group">
                  <input
                    type="text"
                    placeholder="Enter a color clue..."
                    value={clueText}
                    onChange={(e) => setClueText(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && giveClue()}
                    className="input-field"
                  />
                  <button onClick={giveClue} className="btn btn-small">
                    Send
                  </button>
                </div>
              )}
              <div className="clues-list">
                {gameData?.clues?.map((clue, index) => (
                  <div key={index} className="clue-item">
                    <strong>{clue.player_name}:</strong> {clue.clue_text}
                  </div>
                ))}
              </div>
            </div>

            <div className="scores-section">
              <h3>Scores</h3>
              <div className="scores-list">
                {Object.entries(gameData?.scores || {}).map(([pid, score]) => {
                  const player = gameData?.players?.find(p => p.id === pid)
                  return (
                    <div key={pid} className="score-item">
                      <span>{player?.name}</span>
                      <span className="score">{score}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="guesses-section">
              <h3>Recent Guesses</h3>
              <div className="guesses-list">
                {gameData?.guesses?.slice(-5).reverse().map((guess, index) => (
                  <div key={index} className="guess-item">
                    <strong>{guess.player_name}:</strong> 
                    {guess.correct ? (
                      <span className="correct"> ✓ Correct!</span>
                    ) : (
                      <span className="distance"> Distance: {guess.distance}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="board-container">
            <h2>Color Board</h2>
            <p className="board-instruction">
              {isCurrentPlayer ? 'This is your target color board' : 'Click a color to make a guess'}
            </p>
            <div className="color-grid">
              {colors.map((row, rowIndex) => (
                <div key={rowIndex} className="color-row">
                  {row.map((color, colIndex) => {
                    const isTarget = targetColor && targetColor[0] === rowIndex && targetColor[1] === colIndex
                    const wasGuessed = gameData?.guesses?.some(
                      g => g.position[0] === rowIndex && g.position[1] === colIndex
                    )
                    
                    return (
                      <div
                        key={`${rowIndex}-${colIndex}`}
                        className={`color-cell ${isTarget ? 'target' : ''} ${wasGuessed ? 'guessed' : ''}`}
                        style={{ backgroundColor: color }}
                        onClick={() => !isCurrentPlayer && makeGuess(rowIndex, colIndex)}
                        title={`(${rowIndex}, ${colIndex})`}
                      >
                        {isTarget && <span className="target-marker">🎯</span>}
                        {wasGuessed && <span className="guess-marker">●</span>}
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {gameState === 'menu' && renderMenu()}
      {gameState === 'lobby' && renderLobby()}
      {gameState === 'playing' && renderGame()}
    </div>
  )
}

export default App
