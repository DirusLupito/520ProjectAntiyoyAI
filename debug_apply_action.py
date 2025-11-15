#!/usr/bin/env python3
"""Debug why apply_action is not actually applying actions"""

import sys
import logging
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

# Enable logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Testing why actions don't apply ===\n")

# Get valid moves
valid = game.getValidMoves(board, 1)
valid_actions = [i for i, v in enumerate(valid) if v > 0]
print(f"Found {len(valid_actions)} valid actions")
print(f"First 5: {valid_actions[:5]}\n")

# Test the first valid action
action = valid_actions[0]
print(f"=== Testing action {action} ===")

b = Board.from_numpy(board, 1)
print(f"Before: turn_count={b.turn_count}, actions_this_turn={b.actions_this_turn}")

# Decode the action
if action < 720:
    move_result = b.decode_move_action(action)
    if move_result:
        from_row, from_col, to_row, to_col = move_result
        print(f"Action {action} = MOVE from ({from_row},{from_col}) to ({to_row},{to_col})")
elif action < 900:
    build_result = b.decode_build_action(action)
    if build_result:
        row, col, unit_type = build_result
        print(f"Action {action} = BUILD {unit_type} at ({row},{col})")
else:
    print(f"Action {action} = END_TURN")

# Try to apply it
print(f"\nCalling apply_action({action})...")
success = b.apply_action(action)
print(f"apply_action returned: {success}")
print(f"After: turn_count={b.turn_count}, actions_this_turn={b.actions_this_turn}")

# Now test via getNextState
print(f"\n=== Testing via getNextState ===")
board_before = board.copy()
board_after, next_player = game.getNextState(board_before, 1, action)

import numpy as np
if np.array_equal(board_before, board_after):
    print("✗ getNextState did NOT change the board!")
else:
    print("✓ getNextState changed the board")

b_after = Board.from_numpy(board_after, 1)
print(f"After getNextState: turn_count={b_after.turn_count}, next_player={next_player}")
