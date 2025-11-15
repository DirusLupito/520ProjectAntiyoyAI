#!/usr/bin/env python3
"""Debug action 832 - why is it valid but fails?"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

# Take action 804 to reach step 1
valid = game.getValidMoves(board, 1)
board, player = game.getNextState(board, 1, 804)
board = game.getCanonicalForm(board, player)

print("=== After taking action 804 ===")
b = Board.from_numpy(board, 1)
print(f"turn_count: {b.turn_count}")
print(f"actions_this_turn: {b.actions_this_turn}")
print(f"Current faction index: {b.scenario.indexOfFactionToPlay}")

# Check action 832
valid = game.getValidMoves(board, 1)
print(f"\n=== Action 832 Analysis ===")
print(f"Is marked as valid: {valid[832] > 0}")

# Decode it
build_result = b.decode_build_action(832)
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

    # Try to apply
    print(f"\n=== Attempting to apply action 832 ===")
    board_copy = board.copy()
    b_test = Board.from_numpy(board_copy, 1)

    # Enable logging to see what fails
    import logging
    logging.basicConfig(level=logging.DEBUG)

    success = b_test.apply_action(832)
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")

    if not success and tile.owner is None:
        print(f"\nAction failed because tile has no owner!")
        print(f"This should not be marked as valid in getValidMoves!")
