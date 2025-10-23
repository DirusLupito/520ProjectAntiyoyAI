"""
Represents a simple rule-based agent which plays 
a replica of Antiyoy.

As with all AIs designed for this project,
they must implement one simple function called
playTurn which takes in the various variables
representing the game state and returns a list
of Actions and the associated province to run
those actions on.

Mark 1 version: Very basic playing strategy.
Main rules:
1) If any units are idle, pick a random unclaimed tile within its movement range 
and move there, or if those tiles are not within reach, move towards the closest 
unclaimed tile, or do nothing if no unclaimed tiles on the frontier exist.
2) If enough money is available in the treasury, build a new unit
on an unclaimed tile, with a preference for tiles with the lowest
possible production cost (or equivalently, the tile with the lowest
hostile unit defense level).
"""

import random
from collections import deque
from ai.utils.commonAIUtilityFunctions import findPathToClosestTile

def playTurn(scenario, faction):
    """
    Generates a list of actions for the AI's turn based on a simple set of rules.

    Args:
        scenario: The current game Scenario object.
        faction: The Faction object for which to play the turn.

    Returns:
        A list of (Action, province) tuples to be executed.
    """
    allActions = []
    
    # Rule 1: Unit Movement
    # Create a copy of movable units to iterate over, as we will modify their state
    movableUnits = []
    for province in faction.provinces:
        for tile in province.tiles:
            if tile.unit and tile.unit.canMove and tile.unit.unitType.startswith("soldier"):
                movableUnits.append((tile, province))

    # Find all unclaimed tiles on the map
    unclaimedTiles = [
        tile for row in scenario.mapData for tile in row 
        if not tile.isWater and tile.owner != faction
    ]
    
    # Find frontier tiles (unclaimed tiles adjacent to our territory)
    frontierTiles = {
        neighbor for province in faction.provinces for tile in province.tiles 
        for neighbor in tile.neighbors 
        if neighbor and not neighbor.isWater and neighbor.owner != faction
    }

    for unitTile, province in movableUnits:
        # Get all possible moves for the current unit
        validMoveCoords = scenario.getAllTilesWithinMovementRange(unitTile.row, unitTile.col)
        validMoveTiles = [scenario.mapData[r][c] for r, c in validMoveCoords]

        # Prefer moving to an unclaimed tile within immediate reach
        immediateTargets = [t for t in validMoveTiles if t in unclaimedTiles]
        
        targetTile = None
        if immediateTargets:
            # Pick a random unclaimed tile in range
            targetTile = random.choice(immediateTargets)
        elif frontierTiles:
            # If no immediate targets, find path to the closest frontier tile
            path = findPathToClosestTile(unitTile, frontierTiles, scenario.mapData)
            if path and len(path) > 1:
                # Find the furthest tile we can reach along the path
                for i in range(len(path) - 1, 0, -1):
                    step = path[i]
                    if (step.row, step.col) in validMoveCoords:
                        targetTile = step
                        break
        
        if targetTile:
            try:
                moveActions = scenario.moveUnit(unitTile.row, unitTile.col, targetTile.row, targetTile.col)
                for action in moveActions:
                    allActions.append((action, province))
                # Simulate action application to prevent using the same unit/money twice
                for action in moveActions:
                    scenario.applyAction(action, province)
            except ValueError:
                # Ignore invalid moves
                pass

    # Rule 2: Unit Building
    for province in faction.provinces:
        if province.resources >= 10: # Cost of soldierTier1
            # Find potential build locations: unclaimed tiles adjacent to this province
            buildLocations = {
                neighbor for tile in province.tiles for neighbor in tile.neighbors
                if neighbor and not neighbor.isWater and neighbor.owner != faction
            }

            bestTarget = None
            lowestCost = float('inf')
            unitToBeBuilt = None

            for tile in buildLocations:
                # We can extrapolate the cost from the cheapest soldier buildable on that tile
                buildableUnits = scenario.getBuildableUnitsOnTile(tile.row, tile.col, province)
                # The "cost" is the tier of the soldier times 10
                if "soldierTier4" in buildableUnits and 40 < lowestCost:
                    bestTarget = tile
                    lowestCost = 40
                    unitToBeBuilt = "soldierTier4"
                elif "soldierTier3" in buildableUnits and 30 < lowestCost:
                    bestTarget = tile
                    lowestCost = 30
                    unitToBeBuilt = "soldierTier3"
                elif "soldierTier2" in buildableUnits and 20 < lowestCost:
                    bestTarget = tile
                    lowestCost = 20
                    unitToBeBuilt = "soldierTier2"
                elif "soldierTier1" in buildableUnits and 10 < lowestCost:
                    bestTarget = tile
                    lowestCost = 10
                    unitToBeBuilt = "soldierTier1"

            if bestTarget:
                try:
                    buildActions = scenario.buildUnitOnTile(bestTarget.row, bestTarget.col,
                                                             unitToBeBuilt, province)
                    for action in buildActions:
                        allActions.append((action, province))
                    # Simulate action application
                    for action in buildActions:
                        scenario.applyAction(action, province)
                except ValueError:
                    # Ignore invalid builds
                    pass

    # Invert all actions to restore the original scenario state
    for action, province in reversed(allActions):
        scenario.applyAction(action.invert(), province)

    return allActions
