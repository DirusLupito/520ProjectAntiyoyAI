#!/usr/bin/env python3
"""Trace a single MCTS path to see why it doesn't terminate"""

import sys
import numpy as np
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Simulating a Single MCTS-like Path ===")
print("(Taking the first valid action repeatedly)\n")

visited_states = set()
for step in range(210):
    # Check if game ended
    result = game.getGameEnded(board, 1)
    if result != 0:
        print(f"✓ Game ended at step {step}: result={result}")
        break

    # Get state info
    b = Board.from_numpy(board, 1)
    state_hash = game.stringRepresentation(board)

    # Check for state loops
    if state_hash in visited_states:
        print(f"✗ STATE LOOP detected at step {step}! Revisiting a previous state.")
        print(f"   turn_count={b.turn_count}")
        break
    visited_states.add(state_hash)

    # Print periodic status
    if step % 20 == 0 or step > 195:
        print(f"Step {step}: turn_count={b.turn_count}, unique_states={len(visited_states)}")

    # Get valid moves
    valid = game.getValidMoves(board, 1)
    valid_actions = [i for i, v in enumerate(valid) if v > 0]

    if not valid_actions:
        print(f"✗ No valid actions at step {step}!")
        break

    # Take first valid action (like untrained MCTS might)
    action = valid_actions[0]

    if step < 3:
        action_type = "END_TURN" if action == game.getActionSize() - 1 else \
                     "MOVE" if action < 720 else "BUILD"
        print(f"  Valid actions: {len(valid_actions)}, First few: {valid_actions[:5]}")
        print(f"  Taking action {action} ({action_type}), is_valid={valid[action]}")

    # Apply action
    board_before = board.copy()
    board, player = game.getNextState(board, 1, action)
    board = game.getCanonicalForm(board, player)

    # Check if state actually changed
    if step < 3:
        if np.array_equal(board, board_before):
            print(f"  ✗ Board state UNCHANGED after action!")
            b_before = Board.from_numpy(board_before, 1)
            b_after = Board.from_numpy(board, 1)
            print(f"  turn_count: {b_before.turn_count} -> {b_after.turn_count}")
        else:
            print(f"  ✓ Board state changed")
else:
    print(f"\n✗ Reached step 210 without game ending!")
    b = Board.from_numpy(board, 1)
    print(f"Final turn_count: {b.turn_count}")
    print(f"Unique states visited: {len(visited_states)}")
    result = game.getGameEnded(board, 1)
    print(f"getGameEnded result: {result}")
