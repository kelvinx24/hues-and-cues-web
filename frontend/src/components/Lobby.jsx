import React, { useEffect } from "react";
import { useSocket } from "../context/WebSocketContext";
import useGameSocket from "../hooks/useGameSocket";


export default function Lobby({ gameId, playerId, onStart, onLeave }) {
  const { messages, sendMessage, connected } = useSocket();

  const startGame = async () => {
    await fetch(`http://localhost:8001/game/${gameId}/start?player_id=${playerId}`, {
      method: "POST",
    });
    onStart();
  };

  useEffect(() => {
    if (messages.length === 0) return;
    const msg = messages[messages.length - 1];

    if (msg.type === "player_joined") {
      // Add player to list

    } else if (msg.type === "game_phase_changed") {
      // Game started — move to playing state
      onStart();
    }
  }, [messages]);

  return (
    <div>
      <h2>Lobby for {gameId}</h2>
      <p>Connection: {connected ? "🟢 Connected" : "🔴 Disconnected"}</p>
      <button onClick={startGame}>Start Game</button>
      <button onClick={onLeave}>Leave Lobby</button>
    </div>
  );
}
