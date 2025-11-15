#!/usr/bin/env python3
"""Test if numpy encoding/decoding preserves tile ownership"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board_np = game.getInitBoard()

print("=== Testing Round-Trip Encoding/Decoding ===\n")

# Create Board from numpy
b = Board.from_numpy(board_np, 1)

# Check ownership of tile (3, 1)
tile_before = b.scenario.mapData[3][1]
print(f"Tile (3,1) before re-encoding:")
print(f"  Owner: {tile_before.owner}")
print(f"  Owner is None: {tile_before.owner is None}")

# Check what the numpy array says
print(f"\nNumpy array channels at (3,1):")
print(f"  Channel 0 (Player 1): {board_np[0, 3, 1]}")
print(f"  Channel 1 (Player 2): {board_np[1, 3, 1]}")
print(f"  Channel 2 (Water): {board_np[2, 3, 1]}")

# Re-encode to numpy
board_np2 = b.get_numpy_board()

print(f"\nAfter re-encoding to numpy:")
print(f"  Channel 0 (Player 1): {board_np2[0, 3, 1]}")
print(f"  Channel 1 (Player 2): {board_np2[1, 3, 1]}")
print(f"  Channel 2 (Water): {board_np2[2, 3, 1]}")

# Decode again
b2 = Board.from_numpy(board_np2, 1)
tile_after = b2.scenario.mapData[3][1]

print(f"\nTile (3,1) after round-trip:")
print(f"  Owner: {tile_after.owner}")
print(f"  Owner is None: {tile_after.owner is None}")

# Check ALL tiles
print(f"\n=== Checking all non-water tiles ===")
owned_count_original = 0
owned_count_after = 0

for row in range(6):
    for col in range(6):
        if board_np[2, row, col] == 0:  # Not water
            tile_orig = b.scenario.mapData[row][col]
            tile_new = b2.scenario.mapData[row][col]

            if tile_orig.owner is not None:
                owned_count_original += 1
            if tile_new.owner is not None:
                owned_count_after += 1

            if (tile_orig.owner is None) != (tile_new.owner is None):
                print(f"  MISMATCH at ({row},{col}): original owner={tile_orig.owner}, after owner={tile_new.owner}")

print(f"\nOriginal: {owned_count_original} tiles with owners")
print(f"After round-trip: {owned_count_after} tiles with owners")
