# Fixes Applied to Antiyoy Alpha-Zero Implementation

## Issue 1: Infinite Recursion in MCTS

### Problem
MCTS was hitting Python's recursion limit (RecursionError) during search. This happened because:
1. Multi-action turns allowed players to take multiple actions before ending turn
2. Games could go on indefinitely without terminal conditions
3. Starting positions had no resources/units, so players could only pass turns
4. MCTS would search 1000+ levels deep before hitting recursion limit

### Solutions Applied

#### Solution 1: Action Counter with Forced End-Turn
- Added `MAX_ACTIONS_PER_TURN` limit (currently set to 1)
- Tracks `actions_this_turn` counter in Board class
- Forces end-turn after reaching the limit
- Prevents infinite action sequences within a turn

**Files Modified:**
- `AntiyoyLogic.py`: Added action counter tracking
- `AntiyoyGame.py`: Updated to detect forced end-turns

#### Solution 2: Updated State Encoding
- Added channel 23 to encode action counter
- Ensures action count is preserved across board reconstructions
- Updated `NUM_CHANNELS` from 22 to 23

**Files Modified:**
- `AntiyoyLogic.py`: Encoding/decoding action counter
- `AntiyoyGame.py`: Updated board size

#### Solution 3: Faction Tracking for Turn Detection
- Changed turn detection to check faction index before/after action
- Handles both explicit and forced end-turns correctly

**Files Modified:**
- `AntiyoyGame.py`: `getNextState()` now tracks faction changes

### Remaining Issue
Even with action limits, games can still run indefinitely if:
- Both players keep passing turns (end-turn action only)
- No terminal condition is reached (both factions stay alive)
- Initial position has no attackable units or resources to build

### Next Fix Needed: Maximum Game Length
Need to add a turn counter and force draw after N turns to prevent infinite games.

## Recommended Next Steps

1. **Add Turn Counter**: Track total turns in game
2. **Maximum Game Length**: Force draw after 200-300 turns
3. **Better Starting Positions**: Ensure initial scenarios have resources/units
4. **Terminal Detection**: Improve game-end detection for draws

## Temporary Workaround

Set `MAX_ACTIONS_PER_TURN = 1` to simplify gameplay and reduce search depth.
This makes the game more like traditional board games but loses the multi-action aspect of Antiyoy.
