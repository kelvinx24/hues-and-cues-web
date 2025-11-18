import React, { useState, useEffect } from "react";
import { useSocket } from "../context/WebSocketContext";
import "../App.css";


export default function Game({ gameId, playerId, onLeave }) {
  const { socket, messages, lastMessage, latestGameState,sendMessage, connected } = useSocket();
  const [gameData, setGameData] = useState(null);
  const [hintText, setHintText] = useState('');
  const [timeLeft, setTimeLeft] = useState(gameData?.phase_time_remaining ?? 0);
  const [colors, setColors] = useState([]);

  
  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.event) {
      case "game_update":
        setGameData(lastMessage.data);
        break;

      case "game_start":
        console.log("Game START");
        setGameData(lastMessage.data);
        break;
    }
  }, [lastMessage]);

  useEffect(() => {
    if (!connected) return;

    sendMessage({
      event: "request_game_state",
      player_id: playerId,
    });
  }, [connected]);

  useEffect(() => {
    if (gameData?.colors) {
      setColors(gameData.colors);
    }
  }, [gameData]);

  function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  useEffect(() => {
  // whenever server updates the time, reset local timer
  setTimeLeft(gameData?.phase_time_remaining ?? 0);
}, [gameData?.phase_time_remaining]);

  useEffect(() => {
    if (timeLeft <= 0) return;

    const interval = setInterval(() => {
      setTimeLeft(prev => Math.max(prev - 1, 0));
    }, 1000);

    return () => clearInterval(interval);
  }, [timeLeft]);


  const giveHint = async () => {
    if (!hintText.trim()) {
      alert('Please enter a clue');
      return;
    }

    try {
      await sendMessage({
        event: "give_hint",
        player_id: playerId,
        data: {
          hint: hintText
        }
      });
      setHintText('');
    } catch (error) {
      console.error('Failed to give clue:', error);
      alert('Failed to give clue');
    }
  }

  const makeGuess = async (row, col) => {
    try {
      await sendMessage({
        event: "make_guess",
        player_id: playerId,
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

  const choiceEnd = async () => {
    try {
      await sendMessage({
        event: "make_choice",
        player_id: playerId,
        data: {
          choice: "end"
        }
      });

    } catch (error) {
      console.error('Failed to make end choice:', error);
      alert('Failed to make end choice');
    }
  }
  
  const choiceContinue = async () => {
    try {
      await sendMessage({
        event: "make_choice",
        player_id: playerId,
        data: {
          choice: "continue"
        }
      });

    } catch (error) {
      console.error('Failed to make continue choice:', error);
      alert('Failed to make continue choice');
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
            <div className="phase-info">
            <h3>Phase: {gameData?.current_phase || "Unknown"}</h3>

            <div className="timer">
              Time remaining: <strong>{formatTime(timeLeft)}</strong>
            </div>
          </div>
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
                {Object.entries(gameData?.player_data || {}).map(([pid, data]) => {
                  return (
                    <div key={pid} className="score-item">
                      <span>{data.player.name}</span>
                      <span className="score">{data.score}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="guesses-section">
              <h3>Recent Guesses</h3>
                <div className="guesses-list">
                  {gameData?.guesses?.slice(-5).reverse().map((guess, index) => {
                    const [r, c] = guess.position || [];
                    const color = colors?.[r]?.[c];

                    return (
                      <div key={index} className="guess-item">
                        <strong>{guess.player.name}:</strong>

                        {/* Small color preview square */}
                        {color && (
                          <span
                            className="guess-color-square"
                            style={{
                              display: "inline-block",
                              width: "16px",
                              height: "16px",
                              borderRadius: "3px",
                              backgroundColor: color,
                              marginLeft: "8px",
                              verticalAlign: "middle"
                            }}
                          />
                        )}
                      </div>
                    );
                  })}
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
                      const wasGuessed = Object.values(gameData?.player_data ?? {}).some(
                        p => p.guess && p.guess[0] === rowIndex && p.guess[1] === colIndex
                      );
                      
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

  

  if (gameData?.current_phase === "startup") {
    return (
      <div className="startup-phase-container">
        <h1 className="startup-title">🎮 Get Ready!</h1>
        <h2 className="startup-subtitle">Game starts in</h2>

        <div className="startup-timer">
          {formatTime(timeLeft)}
        </div>

        <p className="startup-hint">Waiting for all players…</p>
      </div>
    );
  }

  // Choice Phase UI (only for the hinter)
  else if (gameData?.current_phase === "choice") {
    const isHinter = playerId === gameData.current_player;

    return (
      <div className="choice-phase-container">
        <h2>Choice Phase</h2>

        {isHinter ? (
          <>
            <p>You are the hinter. Choose how to proceed:</p>

            <button
              className="choice-button end-round"
              onClick={choiceEnd}
            >
              End Round
            </button>

            <button
              className="choice-button continue-round"
              onClick={choiceContinue}
            >
              Continue Round
            </button>
          </>
        ) : (
          <p>The hinter is deciding whether the round continues…</p>
        )}
      </div>
    );
  }

  else {
    return renderGame();
  }
}
