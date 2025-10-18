"""
Comprehensive test suite for Hues and Cues Game API

This test suite directly tests the FastAPI endpoint functions to avoid
dependency issues with httpx/TestClient.
"""
import pytest
from main import (
    games, players, COLORS,
    read_root, create_game, join_game, start_game, get_game,
    give_clue, make_guess, get_colors,
    Player, Guess, Clue
)
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def reset_game_state():
    """Reset game state before each test"""
    games.clear()
    players.clear()
    yield
    games.clear()
    players.clear()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_endpoint_returns_success(self):
        """Test that root endpoint returns success message"""
        result = read_root()
        assert "message" in result
        assert "status" in result
        assert result["status"] == "running"


class TestGameCreation:
    """Tests for game creation endpoint"""
    
    def test_create_game_success(self):
        """Test successful game creation"""
        result = create_game(Player(name="Alice"))
        assert "game_id" in result
        assert "player_id" in result
        assert "player_name" in result
        assert result["player_name"] == "Alice"
        assert len(result["game_id"]) == 8
        assert len(result["player_id"]) == 8
    
    def test_create_game_stores_state(self):
        """Test that game creation stores state correctly"""
        result = create_game(Player(name="Bob"))
        game_id = result["game_id"]
        player_id = result["player_id"]
        
        # Verify game is in games dict
        assert game_id in games
        game = games[game_id]
        assert game["status"] == "waiting"
        assert len(game["players"]) == 1
        assert game["players"][0]["name"] == "Bob"
        assert game["players"][0]["id"] == player_id
        
        # Verify player is in players dict
        assert player_id in players
        assert players[player_id]["name"] == "Bob"


class TestJoinGame:
    """Tests for joining a game"""
    
    def test_join_existing_game(self):
        """Test joining an existing game"""
        # Create a game first
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        
        # Join the game
        join_result = join_game(game_id, Player(name="Bob"))
        assert join_result["game_id"] == game_id
        assert join_result["player_name"] == "Bob"
        assert "player_id" in join_result
        
        # Verify game has 2 players
        game = games[game_id]
        assert len(game["players"]) == 2
    
    def test_join_nonexistent_game(self):
        """Test joining a game that doesn't exist"""
        with pytest.raises(HTTPException) as exc_info:
            join_game("fakegame", Player(name="Charlie"))
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
    
    def test_join_full_game(self):
        """Test joining a game that is full (10 players)"""
        # Create a game
        create_result = create_game(Player(name="Player1"))
        game_id = create_result["game_id"]
        
        # Add 9 more players to reach the limit
        for i in range(2, 11):
            join_game(game_id, Player(name=f"Player{i}"))
        
        # Try to add 11th player
        with pytest.raises(HTTPException) as exc_info:
            join_game(game_id, Player(name="Player11"))
        assert exc_info.value.status_code == 400
        assert "full" in exc_info.value.detail.lower()


class TestStartGame:
    """Tests for starting a game"""
    
    def test_start_game_with_enough_players(self):
        """Test starting a game with at least 2 players"""
        # Create game and add player
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player_id = create_result["player_id"]
        
        # Add second player
        join_game(game_id, Player(name="Bob"))
        
        # Start the game
        result = start_game(game_id, player_id)
        assert "message" in result
        assert "current_player" in result
        
        # Verify game state
        game = games[game_id]
        assert game["status"] == "playing"
        assert game["target_color"] is not None
        assert game["current_player"] is not None
    
    def test_start_game_with_insufficient_players(self):
        """Test starting a game with less than 2 players"""
        # Create game with only 1 player
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player_id = create_result["player_id"]
        
        # Try to start the game
        with pytest.raises(HTTPException) as exc_info:
            start_game(game_id, player_id)
        assert exc_info.value.status_code == 400
        assert "at least 2 players" in exc_info.value.detail.lower()
    
    def test_start_nonexistent_game(self):
        """Test starting a game that doesn't exist"""
        with pytest.raises(HTTPException) as exc_info:
            start_game("fakegame", "fakeplayerid")
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestGetGameState:
    """Tests for getting game state"""
    
    def test_get_game_state_before_start(self):
        """Test getting game state before game starts"""
        # Create game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player_id = create_result["player_id"]
        
        # Get game state
        result = get_game(game_id, player_id)
        assert result["game_id"] == game_id
        assert result["status"] == "waiting"
        assert len(result["players"]) == 1
        assert result["current_player"] is None
    
    def test_get_game_state_current_player_sees_target(self):
        """Test that current player can see target color"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get current player
        game = games[game_id]
        current_player = game["current_player"]
        
        # Current player should see target color
        result = get_game(game_id, current_player)
        assert "target_color" in result
        assert result["target_color"] is not None
    
    def test_get_game_state_other_player_no_target(self):
        """Test that non-current player cannot see target color"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get current player
        game = games[game_id]
        current_player = game["current_player"]
        other_player = player1_id if current_player == player2_id else player2_id
        
        # Other player should not see target color
        result = get_game(game_id, other_player)
        assert "target_color" not in result
    
    def test_get_nonexistent_game(self):
        """Test getting state of non-existent game"""
        with pytest.raises(HTTPException) as exc_info:
            get_game("fakegame", "fakeplayerid")
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestGiveClue:
    """Tests for giving clues"""
    
    def test_give_clue_as_current_player(self):
        """Test giving a clue as the current player"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_game(game_id, Player(name="Bob"))
        start_game(game_id, player1_id)
        
        # Get current player
        game = games[game_id]
        current_player = game["current_player"]
        
        # Give clue
        result = give_clue(game_id, Clue(player_id=current_player, clue_text="Ocean blue"))
        assert "message" in result
        
        # Verify clue was added
        game = games[game_id]
        assert len(game["clues"]) == 1
        assert game["clues"][0]["clue_text"] == "Ocean blue"
        assert game["clues"][0]["player_id"] == current_player
    
    def test_give_clue_as_non_current_player(self):
        """Test that non-current player cannot give a clue"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get non-current player
        game = games[game_id]
        current_player = game["current_player"]
        other_player = player1_id if current_player == player2_id else player2_id
        
        # Try to give clue as non-current player
        with pytest.raises(HTTPException) as exc_info:
            give_clue(game_id, Clue(player_id=other_player, clue_text="Ocean blue"))
        assert exc_info.value.status_code == 403
        assert "not your turn" in exc_info.value.detail.lower()
    
    def test_give_clue_to_nonexistent_game(self):
        """Test giving clue to non-existent game"""
        with pytest.raises(HTTPException) as exc_info:
            give_clue("fakegame", Clue(player_id="fakeplayerid", clue_text="Test clue"))
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestMakeGuess:
    """Tests for making guesses"""
    
    def test_correct_guess(self):
        """Test making a correct guess"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get target color
        game = games[game_id]
        target_row, target_col = game["target_color"]
        current_player_before = game["current_player"]
        guesser = player1_id if current_player_before == player2_id else player2_id
        
        # Make correct guess
        result = make_guess(game_id, Guess(player_id=guesser, color_position=(target_row, target_col)))
        assert result["correct"] is True
        assert result["distance"] == 0
        assert "new_round" in result
        assert result["new_round"] is True
        
        # Verify scores were updated
        game = games[game_id]
        assert game["scores"][guesser] == 5  # Guesser gets 5 points
    
    def test_incorrect_guess(self):
        """Test making an incorrect guess"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get target color and make wrong guess
        game = games[game_id]
        target_row, target_col = game["target_color"]
        guesser = player1_id if game["current_player"] == player2_id else player2_id
        
        # Make incorrect guess (different position)
        wrong_row = (target_row + 1) % len(COLORS)
        wrong_col = (target_col + 1) % len(COLORS[0])
        
        result = make_guess(game_id, Guess(player_id=guesser, color_position=(wrong_row, wrong_col)))
        assert result["correct"] is False
        assert result["distance"] > 0
    
    def test_guess_distance_calculation(self):
        """Test that distance is calculated correctly"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get target and calculate expected distance
        game = games[game_id]
        target_row, target_col = game["target_color"]
        guesser = player1_id if game["current_player"] == player2_id else player2_id
        
        guess_row = 0
        guess_col = 0
        expected_distance = abs(guess_row - target_row) + abs(guess_col - target_col)
        
        result = make_guess(game_id, Guess(player_id=guesser, color_position=(guess_row, guess_col)))
        assert result["distance"] == expected_distance
    
    def test_guess_in_nonexistent_game(self):
        """Test making guess in non-existent game"""
        with pytest.raises(HTTPException) as exc_info:
            make_guess("fakegame", Guess(player_id="fakeplayerid", color_position=(0, 0)))
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
    
    def test_guess_before_game_starts(self):
        """Test making guess before game starts"""
        # Create game but don't start it
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player_id = create_result["player_id"]
        
        # Try to make guess
        with pytest.raises(HTTPException) as exc_info:
            make_guess(game_id, Guess(player_id=player_id, color_position=(0, 0)))
        assert exc_info.value.status_code == 400
        assert "not in playing state" in exc_info.value.detail.lower()


class TestGetColors:
    """Tests for getting the color board"""
    
    def test_get_colors(self):
        """Test getting the color board"""
        result = get_colors()
        assert "colors" in result
        assert len(result["colors"]) == len(COLORS)
        assert len(result["colors"][0]) == 10
    
    def test_colors_are_valid_hex(self):
        """Test that all colors are valid hex codes"""
        result = get_colors()
        colors = result["colors"]
        
        for row in colors:
            for color in row:
                # Check if it's a valid hex color
                assert color.startswith("#")
                assert len(color) == 7
                # Check that rest is valid hex
                hex_part = color[1:]
                try:
                    int(hex_part, 16)
                except ValueError:
                    pytest.fail(f"Invalid hex color: {color}")


class TestScoring:
    """Tests for scoring system"""
    
    def test_scoring_after_correct_guess(self):
        """Test that scores are updated correctly after correct guess"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Get target and make correct guess
        game = games[game_id]
        target_row, target_col = game["target_color"]
        current_player = game["current_player"]
        guesser = player1_id if current_player == player2_id else player2_id
        
        initial_guesser_score = game["scores"][guesser]
        initial_current_score = game["scores"][current_player]
        
        make_guess(game_id, Guess(player_id=guesser, color_position=(target_row, target_col)))
        
        # Note: After correct guess, current player rotates
        # So we need to check the old current player's score
        assert games[game_id]["scores"][guesser] == initial_guesser_score + 5
        # The old current player (who gave the clues) got 3 points
        assert games[game_id]["scores"][current_player] == initial_current_score + 3


class TestRoundProgression:
    """Tests for round progression"""
    
    def test_new_round_after_correct_guess(self):
        """Test that a new round starts after correct guess"""
        # Create and start game
        create_result = create_game(Player(name="Alice"))
        game_id = create_result["game_id"]
        player1_id = create_result["player_id"]
        
        join_result = join_game(game_id, Player(name="Bob"))
        player2_id = join_result["player_id"]
        
        start_game(game_id, player1_id)
        
        # Store initial state
        game = games[game_id]
        old_current_player = game["current_player"]
        old_target = game["target_color"]
        
        # Add a clue
        give_clue(game_id, Clue(player_id=old_current_player, clue_text="Test clue"))
        
        # Make correct guess
        target_row, target_col = old_target
        guesser = player1_id if old_current_player == player2_id else player2_id
        
        make_guess(game_id, Guess(player_id=guesser, color_position=(target_row, target_col)))
        
        # Verify new round
        game = games[game_id]
        assert game["current_player"] != old_current_player
        assert game["target_color"] != old_target
        assert len(game["clues"]) == 0  # Clues cleared
        assert len(game["guesses"]) == 0  # Guesses cleared
