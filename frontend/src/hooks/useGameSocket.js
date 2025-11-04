import { useEffect, useRef } from "react";

export default function useGameSocket(gameId, playerId, onMessage) {
  const socketRef = useRef(null);

  useEffect(() => {
    if (!gameId || !playerId) return;

    const ws = new WebSocket(`ws://localhost:8001/ws/${gameId}/${playerId}`);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log("✅ WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📩 Message from server:", data);
        onMessage?.(data); // pass to your handler
      } catch (err) {
        console.error("Bad WS message", err);
      }
    };

    ws.onclose = () => {
      console.log("❌ WebSocket disconnected");
    };

    return () => {
      ws.close();
    };
  }, [gameId, playerId]);

  return socketRef;
}
