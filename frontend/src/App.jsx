// App.jsx
import React, { useState } from "react";
import Menu from "./components/Menu";
import Lobby from "./components/Lobby";
import Game from "./components/GameBoard";
import { SocketProvider } from "./context/WebSocketContext";

function App() {
  const [gameId, setGameId] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [view, setView] = useState("menu"); // "menu" | "lobby" | "game"

  const handleCreateOrJoin = async (name, joinId = null) => {
    const endpoint = joinId ? `/game/${joinId}/join` : `/game/create`;
    const res = await fetch(`http://localhost:8001${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });

    const data = await res.json();
    setGameId(data.game_id);
    setPlayerId(data.player_id);
    setView("lobby");
  };

  const handleStartGame = () => setView("game");
  const handleLeave = () => {
    setGameId(null);
    setPlayerId(null);
    setView("menu");
  };

  if (view === "menu") return <Menu onJoinOrCreate={handleCreateOrJoin} />;

  return (
    <SocketProvider gameId={gameId} playerId={playerId}>
      {view === "lobby" && <Lobby gameId={gameId} playerId={playerId} onStart={handleStartGame} onLeave={handleLeave} />}
      {view === "game" && <Game gameId={gameId} playerId={playerId} onLeave={handleLeave} />}
    </SocketProvider>
  );
}

export default App;
