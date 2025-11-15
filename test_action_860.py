#!/usr/bin/env python3
"""Investigate why action 860 is valid but fails"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

# Take first action to get to step 1
valid = game.getValidMoves(board, 1)
action1 = [i for i, v in enumerate(valid) if v > 0][0]
board, player = game.getNextState(board, 1, action1)
board = game.getCanonicalForm(board, player)

print("=== Investigating Action 860 ===")
b = Board.from_numpy(board, 1)
print(f"Current turn_count: {b.turn_count}")
print(f"Current faction: {b.scenario.indexOfFactionToPlay}")

# Check if action 860 is valid
valid = game.getValidMoves(board, 1)
print(f"\nAction 860 is valid: {valid[860] > 0}")

# Decode action 860
build_result = b.decode_build_action(860)
if build_result:
    row, col, unit_type = build_result
    print(f"Action 860 decodes to: BUILD {unit_type} at ({row}, {col})")

    # Check tile state
    tile = b.scenario.mapData[row][col]
    print(f"\nTile ({row}, {col}) state:")
    print(f"  Owner: {tile.owner}")
    print(f"  Unit: {tile.unit}")
    print(f"  Is water: {tile.isWater}")

    # Try to apply the action manually
    print(f"\nAttempting to apply action 860...")
    board_copy = board.copy()
    success = b.apply_action(860)
    print(f"  Result: {'SUCCESS' if success else 'FAILED'}")

    if not success:
        # Try to understand why it failed
        print(f"\n  Checking why it failed:")
        print(f"  - Tile owner: {tile.owner}")
        print(f"  - Current faction provinces: {len(b.scenario.getFactionToPlay().provinces) if b.scenario.getFactionToPlay() else 0}")

        if tile.owner:
            print(f"  - Tile owner faction: {tile.owner.faction.name if tile.owner.faction else 'None'}")
            print(f"  - Current faction: {b.scenario.getFactionToPlay().name if b.scenario.getFactionToPlay() else 'None'}")
            print(f"  - Tile belongs to current faction: {tile.owner.faction == b.scenario.getFactionToPlay() if (tile.owner and tile.owner.faction and b.scenario.getFactionToPlay()) else False}")
