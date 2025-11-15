#!/usr/bin/env python3
"""Debug why action 797 is marked valid but doesn't change the board"""

import sys
import numpy as np
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Initial State ===")
b = Board.from_numpy(board, 1)
print(f"turn_count: {b.turn_count}")
print(f"actions_this_turn: {b.actions_this_turn}")

# Check action 797
valid = game.getValidMoves(board, 1)
print(f"\n=== Action 797 ===")
print(f"Is marked as valid: {valid[797] > 0}")

# Decode it
build_result = b.decode_build_action(797)
if build_result:
    row, col, unit_type = build_result
    print(f"Decodes to: BUILD {unit_type} at ({row}, {col})")

    # Check tile
    tile = b.scenario.mapData[row][col]
    print(f"\nTile ({row}, {col}) state:")
    print(f"  Is water: {tile.isWater}")
    print(f"  Owner: {tile.owner}")
    print(f"  Unit: {tile.unit}")

    if tile.owner:
        print(f"  Owner province: active={tile.owner.active}, tiles={len(tile.owner.tiles)}, resources={tile.owner.resources}")
        print(f"  Owner faction: {tile.owner.faction.name}")

    # Check current faction
    current_faction = b.scenario.getFactionToPlay()
    if current_faction:
        print(f"\nCurrent faction: {current_faction.name}")
        print(f"  Provinces: {len(current_faction.provinces)}")
        for i, prov in enumerate(current_faction.provinces):
            print(f"    Province {i}: tiles={len(prov.tiles)}, resources={prov.resources}, active={prov.active}")

    # Try to apply the action
    print(f"\n=== Attempting to apply action 797 ===")
    board_before = board.copy()
    board_after, next_player = game.getNextState(board, 1, 797)

    if np.array_equal(board_before, board_after):
        print("✗ BOARD STATE UNCHANGED!")

        # Apply directly to Board object to see what fails
        print("\n=== Applying directly to Board object ===")
        b_test = Board.from_numpy(board_before, 1)
        success = b_test.apply_action(797)
        print(f"apply_action returned: {success}")

        # Check if getValidMoves logic matches apply_action logic
        print("\n=== Checking why getValidMoves thinks it's valid ===")
        print(f"  Tile owner exists: {tile.owner is not None}")
        if tile.owner:
            print(f"  Owner belongs to current faction: {tile.owner.faction == current_faction}")
            print(f"  Province has enough resources: {tile.owner.resources >= 10}")
    else:
        print("✓ Board state changed")
        b_after = Board.from_numpy(board_after, 1)
        print(f"  turn_count: {b.turn_count} -> {b_after.turn_count}")
