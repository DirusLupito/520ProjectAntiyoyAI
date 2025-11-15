#!/usr/bin/env python3
"""Check which tiles are owned in the initial board"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board_np = game.getInitBoard()
b = Board.from_numpy(board_np, 1)

print("=== Initial Board State ===\n")

print("Player 1 province:")
faction1 = b.scenario.factions[0]
for prov in faction1.provinces:
    print(f"  Province: {len(prov.tiles)} tiles, {prov.resources} resources, active={prov.active}")
    for tile in prov.tiles:
        print(f"    Tile ({tile.row},{tile.col}), unit={tile.unit}")

print("\nPlayer 2 province:")
faction2 = b.scenario.factions[1]
for prov in faction2.provinces:
    print(f"  Province: {len(prov.tiles)} tiles, {prov.resources} resources, active={prov.active}")
    for tile in prov.tiles:
        print(f"    Tile ({tile.row},{tile.col}), unit={tile.unit}")

print("\n=== Testing getValidMoves ===")
valid = b.get_valid_moves_vector(debug=True)

print(f"\n=== Testing if action 853 should be valid ===")
build_result = b.decode_build_action(853)
if build_result:
    row, col, unit_type = build_result
    print(f"Action 853 = BUILD {unit_type} at ({row},{col})")

    tile = b.scenario.mapData[row][col]
    print(f"Tile ({row},{col}) owner: {tile.owner}")

    # Check if this tile is in any province's tiles list
    in_faction1 = any(t.row == row and t.col == col for prov in faction1.provinces for t in prov.tiles)
    in_faction2 = any(t.row == row and t.col == col for prov in faction2.provinces for t in prov.tiles)

    print(f"Tile in faction1 provinces: {in_faction1}")
    print(f"Tile in faction2 provinces: {in_faction2}")
