#!/usr/bin/env python3
"""Debug if getCanonicalForm is causing issues"""

import sys
import numpy as np
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Testing action 797 with canonical form ===")

# Get valid moves
valid = game.getValidMoves(board, 1)
valid_actions = [i for i, v in enumerate(valid) if v > 0]
print(f"Valid actions: {len(valid_actions)}")
print(f"First valid action: {valid_actions[0]}")

# Save board before
board_before = board.copy()
b_before = Board.from_numpy(board_before, 1)
print(f"\nBefore action:")
print(f"  turn_count: {b_before.turn_count}")
print(f"  player: 1")

# Apply action
action = valid_actions[0]
board_after, next_player = game.getNextState(board, 1, action)

b_after_pre_canonical = Board.from_numpy(board_after, 1)
print(f"\nAfter getNextState (before canonical):")
print(f"  turn_count: {b_after_pre_canonical.turn_count}")
print(f"  next_player: {next_player}")
print(f"  board changed: {not np.array_equal(board_before, board_after)}")

# Apply canonical form
board_canonical = game.getCanonicalForm(board_after, next_player)

b_canonical = Board.from_numpy(board_canonical, 1)
print(f"\nAfter getCanonicalForm:")
print(f"  turn_count: {b_canonical.turn_count}")
print(f"  board changed from before: {not np.array_equal(board_before, board_canonical)}")

# Check if canonical form made it identical to original
if np.array_equal(board_before, board_canonical):
    print("\n✗ CANONICAL FORM RETURNED TO ORIGINAL STATE!")
    print("This would cause state loops in MCTS!")

    # Check the actual board differences
    diff = board_canonical - board_before
    print(f"\nBoard difference sum: {np.sum(np.abs(diff))}")
    print(f"Non-zero differences: {np.count_nonzero(diff)}")
else:
    print("\n✓ Board state properly changed")

    # Show turn count progression
    print(f"\nTurn count: {b_before.turn_count} -> {b_after_pre_canonical.turn_count} -> {b_canonical.turn_count}")

    # Check state hash
    hash_before = game.stringRepresentation(board_before)
    hash_canonical = game.stringRepresentation(board_canonical)
    print(f"State hashes equal: {hash_before == hash_canonical}")
