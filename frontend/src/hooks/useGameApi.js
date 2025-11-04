export function useGameAPI(apiUrl) {
  const getGame = (gameId, playerId) =>
    fetch(`${apiUrl}/game/${gameId}?player_id=${playerId}`).then((r) => r.json())

  const startGame = (gameId, playerId) =>
    fetch(`${apiUrl}/game/${gameId}/start?player_id=${playerId}`, { method: 'POST' })

  return { getGame, startGame }
}
