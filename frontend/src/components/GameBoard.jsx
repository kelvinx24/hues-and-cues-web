import React from "react";
import { useSocket } from "../context/WebSocketContext";

export default function Game({ gameId, playerId, onLeave }) {
  const { messages, connected } = useSocket();

  return (
    <div>
      <h2>Game in progress</h2>
      <p>Connection: {connected ? "🟢 Connected" : "🔴 Disconnected"}</p>
    </div>
  );
}
