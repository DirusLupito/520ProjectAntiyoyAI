#!/usr/bin/env python3
"""Debug why BUILD action fails with exception"""

import sys
import logging
sys.path.insert(0, 'alpha-zero')

# Enable ALL logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

# Test action 853
b = Board.from_numpy(board, 1)
build_result = b.decode_build_action(853)

if build_result:
    row, col, unit_type = build_result
    print(f"=== Attempting to build {unit_type} at ({row}, {col}) ===\n")

    tile = b.scenario.mapData[row][col]
    province = tile.owner

    print(f"Tile owner: {province}")
    print(f"Province is None: {province is None}")

    if province:
        print(f"Province tiles: {len(province.tiles)}")
        print(f"Province resources: {province.resources}")
        print(f"Province active: {province.active}")

    print(f"\nCalling buildUnitOnTile...")
    try:
        actions_to_apply = b.scenario.buildUnitOnTile(row, col, unit_type, province)
        print(f"✓ buildUnitOnTile succeeded, returned {len(actions_to_apply)} actions")
        for i, act in enumerate(actions_to_apply):
            print(f"  Action {i}: {type(act).__name__}")
    except Exception as e:
        print(f"✗ buildUnitOnTile failed with exception:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n=== Now testing apply_action ===")
    success = b.apply_action(853)
    print(f"apply_action returned: {success}")
