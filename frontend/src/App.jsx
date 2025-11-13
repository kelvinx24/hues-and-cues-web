// App.jsx
import React, { useState } from "react";
import Menu from "./components/Menu";
import Lobby from "./components/Lobby";
import Game from "./components/GameBoard";
import { SocketProvider } from "./context/WebSocketContext";

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [view, setView] = useState("menu"); // "menu" | "lobby" | "game"

  const handleCreateOrJoin = async (name, joinId = null) => {
    const endpoint = joinId ? `/session/${joinId}/join` : `/session/create`;
    const res = await fetch(`http://localhost:8001${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });

    const data = await res.json();
    setTimeout(() => {
    setSessionId(data.session_id);
    setPlayerId(data.you);
    setView("lobby");
}, 200);
  };

  const handleStartGame = () => setView("game");
  const handleLeave = async () => {
    const res = await fetch(`http://localhost:8001/session/${sessionId}/leave`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({'player_id':playerId}),
    });

    setSessionId(null);
    setPlayerId(null);
    setView("menu");
  };

  if (view === "menu") return <Menu onJoinOrCreate={handleCreateOrJoin} />;

  return (
    <SocketProvider sessionId={sessionId} playerId={playerId}>
      {view === "lobby" && <Lobby sessionId={sessionId} playerId={playerId} onStart={handleStartGame} onLeave={handleLeave} />}
      {view === "game" && <Game sessionId={sessionId} playerId={playerId} onLeave={handleLeave} />}
    </SocketProvider>
  );
}

export default App;
