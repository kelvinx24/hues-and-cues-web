import React, { useState, useEffect } from "react";
import { useSocket } from "../context/WebSocketContext";


export default function Game({ gameId, playerId, onLeave }) {
  const { socket, messages, sendMessage, connected } = useSocket();
  const [gameData, setGameData] = useState(null);
  const [hintText, setHintText] = useState('');
  const [timeText, setTimeText] = useState('');
  const [colors, setColors] = useState([]);

  useEffect(() => {
      if (messages.length === 0) return;
      const msg = messages[messages.length - 1];
  
      if (msg.event === "game_update") {
        // Add player to list
        setGameData(msg.data);
        
      } 
      else if (msg.event === "game_start") {
        console.log("Game START")
        setGameData(msg.data);
        setColors(msg.data.colors);
      }
    }, [messages]
  );

  const giveHint = async () => {
    if (!hintText.trim()) {
      alert('Please enter a clue');
      return;
    }

    try {
      await sendMessage({
        event: "give_hint",
        sender: playerId,
        data: {
          hint: hintText
        }
      });
      setClueText('');
    } catch (error) {
      console.error('Failed to give clue:', error);
      alert('Failed to give clue');
    }
  }

  const makeGuess = async (row, col) => {
    try {
      await sendMessage({
        event: "make_guess",
        sender: playerId,
        data: {
          row: row,
          col: col
        }
      });

    } catch (error) {
      console.error('Failed to make guess:', error);
      alert('Failed to make guess');
    }
  }

  const renderGame = () => {
    const isCurrentPlayer = gameData?.current_player === playerId;
    const targetColor = gameData?.target_color;

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
                  {targetColor && colors && (
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
                    {gameData?.players?.find(p => p.player_id === gameData?.current_player)?.name || 'Someone'}'s turn
                  </p>
                </div>
              )}
            </div>

            <div className="hints-section">
              <h3>Hints</h3>
              {isCurrentPlayer && (
                <div className="hint-input-group">
                  <input
                    type="text"
                    placeholder="Enter a color clue..."
                    value={hintText}
                    onChange={(e) => setHintText(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && giveHint()}
                    className="input-field"
                  />
                  <button onClick={giveHint} className="btn btn-small">
                    Send
                  </button>
                </div>
              )}
              <div className="hints-section">
                <h3>Clues</h3>
                <div className="hints-list">
                  {gameData?.hints?.map((clue, index) => (
                    <div key={index} className="hint-item">
                      {clue}
                    </div>
                  ))}
                </div>
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
                    <strong>{guess.player_name}:</strong> {guess.guess}
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
            {Array.isArray(colors) && colors.length > 0 ? (
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
            ) : (
              <p>Loading board...</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  const renderGameTest = () => {
      return (
    <div>
      <h2>Game in progress</h2>
      <p>Connection: {connected ? "🟢 Connected" : "🔴 Disconnected"}</p>
    </div>
  );
  }


  return renderGame();
}
