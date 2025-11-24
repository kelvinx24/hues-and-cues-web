import React, { useEffect, useState } from "react";
import { useSocket } from "../context/WebSocketContext";
import useGameSocket from "../hooks/useGameSocket";


export default function Lobby({ sessionId, playerId, onStart, onLeave }) {
  const { messages, sendMessage, connected } = useSocket();
  const [sessionData, setSessionData] = useState(null);

  const startGame = async () => {
    await fetch(`http://localhost:8001/session/${sessionId}/start?player_id=${playerId}`, {
      method: "POST",
    });
  };

  useEffect(() => {
  const loadSession = async () => {
    try {
      const res = await fetch(`http://localhost:8001/session/${sessionId}`);
      if (!res.ok) {
        onLeave();
        return;
      }

      const json = await res.json();
      setSessionData(json.data);

    } catch (err) {
      console.error(err);
      onLeave();
    }
  };

  loadSession();
}, [sessionId]);


  useEffect(() => {
    if (messages.length === 0) return;
    const msg = messages[messages.length - 1];

    if (msg.event === "player_joined" || msg.event === "player_left" || msg.event === "session_update") {
      // Add player to list
      setSessionData(msg.data)
      
    } else if (msg.event === "game_start") {
      // Game started — move to playing state
      onStart();
    } else if (msg.event === "session_end") {
      onLeave();
    }
  }, [messages]);

  return (
    <div className="lobby-container">
      <h1>Game Lobby</h1>
      
      <div className="session-info">
        <p className="session-id">Session ID: <strong>{sessionId}</strong></p>
        <p className="share-text">Share this ID with friends to join!</p>
      </div>
      
      <div className="players-section">
        <h2>Players ({sessionData?.players?.length || 0})</h2>
        <div className="players-list">
          {sessionData?.players?.map((player, index) => (
            <div key={player.player_id} className="player-card">
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
        disabled={!sessionData || sessionData.players?.length < 2 || sessionData.leader?.player_id != playerId}
      >
        Start Game
      </button>
      
      <button onClick={onLeave} className="btn btn-secondary">
        Leave Game
      </button>
    </div>
  );

   
}
