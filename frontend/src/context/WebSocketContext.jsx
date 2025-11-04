import React, { createContext, useContext, useEffect, useRef, useState } from 'react';

const SocketContext = createContext(null);

export const SocketProvider = ({ gameId, playerId, children }) => {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!gameId || !playerId) return; // Don't connect if not in game

    const ws = new WebSocket(`ws://localhost:8001/ws/${gameId}/${playerId}`);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log("✅ WebSocket connected")
      setConnected(true);

    };
      ;
    ws.onclose = () => console.log("❌ WebSocket disconnected");
    ws.onerror = (err) => console.error("WebSocket error:", err);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📩 Message received:", data);
      setMessages((prev) => [...prev, data]);
    };

    // Cleanup on unmount or when player leaves
    return () => {
      ws.close();
      socketRef.current = null;
    };
  }, [gameId, playerId]);

  // Send helper
  const sendMessage = (data) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data));
    }
  };

  return (
    <SocketContext.Provider value={{ socket: socketRef.current, messages, sendMessage, connected }}>
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = () => useContext(SocketContext);
