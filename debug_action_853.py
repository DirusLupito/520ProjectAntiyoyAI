#!/usr/bin/env python3
"""Debug action 853 specifically"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Debugging Action 853 ===\n")

# Get valid moves with debug
b = Board.from_numpy(board, 1)
valid = b.get_valid_moves_vector(debug=True)

print(f"\nAction 853 is valid: {valid[853] > 0}")

# Decode it
build_result = b.decode_build_action(853)
if build_result:
    row, col, unit_type = build_result
    print(f"\nAction 853 = BUILD {unit_type} at ({row}, {col})")

    tile = b.scenario.mapData[row][col]
    print(f"\nTile ({row}, {col}) state:")
    print(f"  Owner: {tile.owner}")
    print(f"  Unit: {tile.unit}")
    print(f"  Is water: {tile.isWater}")

    # Check neighbors
    print(f"\nChecking if this is a neighbor of a province tile...")
    faction = b.scenario.getFactionToPlay()
    for province in faction.provinces:
        for prov_tile in province.tiles:
            for neighbor in prov_tile.neighbors:
                if neighbor and neighbor.row == row and neighbor.col == col:
                    print(f"  ✓ Tile ({row},{col}) is a neighbor of province tile ({prov_tile.row},{prov_tile.col})")
                    print(f"  This is a CAPTURE opportunity (tile owner={tile.owner}, province={province})")
