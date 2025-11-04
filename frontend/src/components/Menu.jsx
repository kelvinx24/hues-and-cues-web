import React, { useState } from 'react'

const API_URL = 'http://localhost:8001'

export default function Menu({ onJoinOrCreate }) {
  const [name, setName] = useState("");
  const [joinId, setJoinId] = useState("");

  const handleCreate = () => {
    if (!name.trim()) return alert("Enter a name first!");
    onJoinOrCreate(name); // create new game
  };

  const handleJoin = () => {
    if (!name.trim() || !joinId.trim()) return alert("Enter both name and game ID!");
    onJoinOrCreate(name, joinId); // join existing game
  };

    return (
        <div className="menu-screen" style={{ textAlign: "center", marginTop: "4rem" }}>
        <h1>🎨 Hues and Cues</h1>

        <div style={{ marginBottom: "1rem" }}>
            <input
            type="text"
            placeholder="Enter your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ padding: "0.5rem", width: "200px" }}
            />
        </div>

        <div style={{ marginBottom: "1rem" }}>
            <input
            type="text"
            placeholder="Join existing game ID"
            value={joinId}
            onChange={(e) => setJoinId(e.target.value)}
            style={{ padding: "0.5rem", width: "200px" }}
            />
        </div>

        <div>
            <button onClick={handleCreate} style={{ marginRight: "0.5rem" }}>
            Create New Game
            </button>
            <button onClick={handleJoin}>Join Game</button>
        </div>
        </div>
    );
}


