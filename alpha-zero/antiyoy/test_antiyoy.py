"""
test_antiyoy.py - Basic tests for Antiyoy alpha-zero-general integration

This script tests the basic functionality of the Antiyoy game implementation.
"""

import sys
import os
import numpy as np

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
alpha_zero_dir = os.path.join(project_root, 'alpha-zero')
sys.path.append(project_root)
sys.path.append(alpha_zero_dir)

from antiyoy.AntiyoyGame import AntiyoyGame


def test_basic_game():
    """Test basic game functionality."""
    print("=" * 60)
    print("TEST: Basic Game Functionality")
    print("=" * 60)

    # Create game
    print("\n1. Creating game...")
    game = AntiyoyGame()
    print(f"   Board size: {game.getBoardSize()}")
    print(f"   Action size: {game.getActionSize()}")

    # Get initial board
    print("\n2. Getting initial board...")
    board = game.getInitBoard()
    print(f"   Board shape: {board.shape}")
    print(f"   Board dtype: {board.dtype}")

    # Display initial board
    print("\n3. Initial board state:")
    game.display(board)

    # Get valid moves
    print("\n4. Getting valid moves for player 1...")
    player = 1
    valid_moves = game.getValidMoves(board, player)
    num_valid = np.sum(valid_moves)
    print(f"   Number of valid moves: {int(num_valid)}")

    # Get indices of valid moves
    valid_indices = np.where(valid_moves > 0)[0]
    print(f"   First 10 valid move indices: {valid_indices[:10]}")

    # Check game status
    print("\n5. Checking if game ended...")
    result = game.getGameEnded(board, player)
    print(f"   Game ended result: {result}")
    if result == 0:
        print("   Game is still ongoing (expected)")

    # Test canonical form
    print("\n6. Testing canonical form...")
    canonical_p1 = game.getCanonicalForm(board, 1)
    canonical_p2 = game.getCanonicalForm(board, -1)
    print(f"   Canonical form for P1 same as board: {np.array_equal(canonical_p1, board)}")
    print(f"   Canonical form for P2 different from board: {not np.array_equal(canonical_p2, board)}")

    # Test string representation
    print("\n7. Testing string representation...")
    board_str = game.stringRepresentation(board)
    print(f"   String representation length: {len(board_str)} bytes")

    print("\n" + "=" * 60)
    print("Basic tests completed successfully!")
    print("=" * 60)


def test_play_moves():
    """Test playing a few random moves."""
    print("\n" + "=" * 60)
    print("TEST: Playing Random Moves")
    print("=" * 60)

    game = AntiyoyGame()
    board = game.getInitBoard()
    player = 1

    print("\nPlaying 5 random moves...")

    for i in range(5):
        print(f"\n--- Move {i + 1} ---")

        # Get valid moves
        valid_moves = game.getValidMoves(board, player)
        valid_indices = np.where(valid_moves > 0)[0]

        if len(valid_indices) == 0:
            print("   No valid moves available!")
            break

        # Choose a random valid move
        action = np.random.choice(valid_indices)
        print(f"   Player {player} plays action {action}")

        # Check if it's end turn
        if action == game.getActionSize() - 1:
            print("   Action is: END TURN")
        elif action < game.height * game.width * 20:
            print("   Action is: MOVE")
        else:
            print("   Action is: BUILD")

        # Apply move
        next_board, next_player = game.getNextState(board, player, action)

        # Check if player changed
        if next_player != player:
            print(f"   Turn ended, next player: {next_player}")
        else:
            print(f"   Same player continues: {next_player}")

        # Update state
        board = next_board
        player = next_player

        # Check if game ended
        result = game.getGameEnded(board, player)
        if result != 0:
            print(f"   Game ended! Result for player {player}: {result}")
            break

    # Display final board
    print("\nFinal board state:")
    game.display(board)

    print("\n" + "=" * 60)
    print("Move tests completed!")
    print("=" * 60)


def test_encoding_decoding():
    """Test that encoding and decoding works correctly."""
    print("\n" + "=" * 60)
    print("TEST: Encoding/Decoding Roundtrip")
    print("=" * 60)

    from antiyoy.AntiyoyLogic import Board

    print("\n1. Creating initial board...")
    board1 = Board()

    print("\n2. Encoding to numpy...")
    numpy_board = board1.get_numpy_board()
    print(f"   Numpy shape: {numpy_board.shape}")

    print("\n3. Decoding from numpy...")
    board2 = Board.from_numpy(numpy_board, current_player=1)

    print("\n4. Re-encoding...")
    numpy_board2 = board2.get_numpy_board()

    print("\n5. Comparing numpy arrays...")
    are_equal = np.allclose(numpy_board, numpy_board2, atol=0.01)
    print(f"   Arrays are equal: {are_equal}")

    if are_equal:
        print("   ✓ Encoding/decoding roundtrip successful!")
    else:
        print("   ✗ Encoding/decoding roundtrip failed!")
        print(f"   Max difference: {np.max(np.abs(numpy_board - numpy_board2))}")

    print("\n" + "=" * 60)
    print("Encoding/decoding tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ANTIYOY ALPHA-ZERO-GENERAL INTEGRATION TESTS")
    print("=" * 60)

    try:
        test_basic_game()
        test_play_moves()
        test_encoding_decoding()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
