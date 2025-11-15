#!/usr/bin/env python3
"""Test MCTS recursion depth issue"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

# Create game
game = AntiyoyGame()
board = game.getInitBoard()

print("=== Initial Board ===")
b = Board.from_numpy(board, 1)
print(f"Turn count: {b.turn_count}")
print(f"Max turns: {b.MAX_GAME_TURNS}")

# Test game ending
result = b.check_game_ended(1, debug=True)
print(f"Game ended result: {result}\n")

# Simulate taking END_TURN actions repeatedly (using canonical form like MCTS)
print("=== Simulating turns (first 5 with debug) ===")
player = 1  # Always use player 1 in canonical form
for i in range(60):
    # Check if game ended (always check from player 1's perspective in canonical form)
    result = game.getGameEnded(board, 1)
    if result != 0:
        print(f"\nGame ended at turn {i}: result={result}")
        break

    # Get valid moves (always from player 1's perspective)
    valid = game.getValidMoves(board, 1)

    # Take END_TURN action (last action)
    end_turn_action = game.getActionSize() - 1

    # Apply it (debug first 5)
    debug = (i < 5)
    if debug:
        print(f"\n--- Turn {i}: canonical player=1, action=END_TURN ---")
    next_board, next_player = game.getNextState(board, 1, end_turn_action, debug=debug)

    # Convert to canonical form (like MCTS does)
    board = game.getCanonicalForm(next_board, next_player)

    # Check turn count every 10 turns
    if i % 10 == 0:
        b = Board.from_numpy(board, 1)  # Always player 1 in canonical form
        faction_idx = b.scenario.indexOfFactionToPlay
        print(f"After {i} END_TURN actions: turn_count={b.turn_count}, faction_idx={faction_idx}")

print("\n=== Final state ===")
b = Board.from_numpy(board, 1)
print(f"Final turn count: {b.turn_count}")
result = b.check_game_ended(1, debug=True)
print(f"Final result: {result}")
