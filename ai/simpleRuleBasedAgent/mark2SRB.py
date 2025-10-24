"""
Represents a simple rule-based agent which plays 
a replica of Antiyoy.

As with all AIs designed for this project,
they must implement one simple function called
playTurn which takes in the various variables
representing the game state and returns a list
of Actions and the associated province to run
those actions on.

Mark 2 version: Very basic playing strategy, with some improvements.
Uses the same rules as Mark 1, but with differently implemented logic.
2 Improvements:
1) Arguably not an improvement, but should hopefully make it collapse
   its economy less often: The AI will now consider tiles with units
   on them as invalid targets for movement or more unit construction
   to avoid accumulating too many expensive high-tier units that it cannot
   afford to maintain.
2) Will consider trees on already claimed tiles the same as unclaimed tiles
   when deciding where to move its units.
"""

import random
from ai.utils.commonAIUtilityFunctions import findPathToClosestTileAvoidingGivenTiles
from ai.utils.commonAIUtilityFunctions import getAllMovableUnitTilesInProvince
from ai.utils.commonAIUtilityFunctions import getFrontierTiles
from ai.utils.commonAIUtilityFunctions import getTilesInProvinceWhichContainGivenUnitTypes
from ai.utils.commonAIUtilityFunctions import getTilesWhichUnitCanBeBuiltOnGivenTiles
import pdb

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

    # Rather than the potentially unsafe method of going through all provinces
    # at once in the Mark 1, we shall instead create actions similar to how
    # a human player would, by selecting an individual province, doing all
    # the actions for that province (including potentially extra actions
    # if a merge happens which allows for more funding and more unit movement),
    # and then moving on to the next province, taking care to skip inactive provinces
    # and provinces eradicated by potential merges of previous actions.
    notDoneWithCurrentProvince = len(faction.provinces) > 0
    provinceIndex = 0
    moveAUnitThisIteration = False
    buildAUnitThisIteration = False
    while notDoneWithCurrentProvince:
        if provinceIndex >= len(faction.provinces):
            break # No more provinces to process
        province = faction.provinces[provinceIndex]
        provinceIndex += 1

        # Keeps track of whether we moved or built a unit this iteration
        # and therefore if a merge might have happened.
        # If we have moveable units after an iteration where we never
        # moved or built a unit, then we probably can't move a unit,
        # so we need to move on to the next province.
        moveAUnitThisIteration = False
        buildAUnitThisIteration = False

        if not province or not province.active:
            continue # Skip inactive provinces

        # Similar to rule 1 from Mark 1: Move units
        # We shall either move to the closest unclaimed tile or tree tile,
        # or move towards the closest such tile if out of range.
        movableUnits = getAllMovableUnitTilesInProvince(province)

        treeTiles = getTilesInProvinceWhichContainGivenUnitTypes(province, ["tree"])

        frontierTiles = getFrontierTiles(province)

        validTargets = set(frontierTiles).union(set(treeTiles))

        soldierTilesToAvoid = set(getTilesInProvinceWhichContainGivenUnitTypes(province, ["soldierTier1", "soldierTier2", "soldierTier3", "soldierTier4"]))

        for unitTile, _ in movableUnits:
            path = findPathToClosestTileAvoidingGivenTiles(unitTile, validTargets, soldierTilesToAvoid)
            if path and len(path) > 1:
                # Find the furthest tile we can reach along the path
                movementRange = scenario.getAllTilesWithinMovementRange(unitTile.row, unitTile.col)
                for i in range(len(path) - 1, 0, -1):
                    step = path[i]
                    # Remember that scenario.getAllTilesWithinMovementRange(unitTile.row, unitTile.col)
                    # returns a list of (row, col) tuples rather than actual tile objects
                    if (step.row, step.col) in movementRange:
                        moveAUnitThisIteration = True
                        moveActions = scenario.moveUnit(unitTile.row, unitTile.col, step.row, step.col)
                        for moveAction in moveActions:
                            allActions.append((moveAction, province))
                        # Apply the actions immediately to update the scenario state
                        for moveAction in moveActions:
                            scenario.applyAction(moveAction, province)
                        # With the scenario updated, we need to recompute frontier tiles
                        # and soldier tiles to avoid no matter what, and as a result, valid targets
                        frontierTiles = getFrontierTiles(province)
                        validTargets = set(frontierTiles).union(set(getTilesInProvinceWhichContainGivenUnitTypes(province, ["tree"])))
                        soldierTilesToAvoid = set(getTilesInProvinceWhichContainGivenUnitTypes(province, ["soldierTier1", "soldierTier2", "soldierTier3", "soldierTier4"]))
                        break

        # Similar to rule 2 from Mark 1: Build soldier units
        # We shall build a soldier unit on a frontier tile or
        # tree tile if we can afford it.
        # We want to try to build cheaper units first,
        # so we will attempt to build soldierTier1 units
        # then soldierTier2 units, etc.
        canBuildMoreUnits = True
        while province.resources >= 10 and canBuildMoreUnits:
            frontierTiles = getFrontierTiles(province)
            treeTiles = getTilesInProvinceWhichContainGivenUnitTypes(province, ["tree"])
            candidateBuildTiles = set(frontierTiles).union(set(treeTiles))
            buildableTilesForTier1 = getTilesWhichUnitCanBeBuiltOnGivenTiles(scenario, province, "soldierTier1", list(candidateBuildTiles))
            # If we can build a soldierTier1, do so
            if buildableTilesForTier1:
                buildAUnitThisIteration = True
                buildTile = random.choice(buildableTilesForTier1)
                buildActions = scenario.buildUnitOnTile(buildTile.row, buildTile.col, "soldierTier1", province)
                for buildAction in buildActions:
                    allActions.append((buildAction, province))
                # Apply the actions immediately to update the scenario state
                for buildAction in buildActions:
                    scenario.applyAction(buildAction, province)
                # Now let's continue the loop to see if we can build more units
                continue
            # Try soldierTier2
            buildableTilesForTier2 = getTilesWhichUnitCanBeBuiltOnGivenTiles(scenario, province, "soldierTier2", list(candidateBuildTiles))
            if buildableTilesForTier2:
                buildAUnitThisIteration = True
                buildTile = random.choice(buildableTilesForTier2)
                buildActions = scenario.buildUnitOnTile(buildTile.row, buildTile.col, "soldierTier2", province)
                for buildAction in buildActions:
                    allActions.append((buildAction, province))
                for buildAction in buildActions:
                    scenario.applyAction(buildAction, province)
                continue
            # Tier 3
            buildableTilesForTier3 = getTilesWhichUnitCanBeBuiltOnGivenTiles(scenario, province, "soldierTier3", list(candidateBuildTiles))
            if buildableTilesForTier3:
                buildAUnitThisIteration = True
                buildTile = random.choice(buildableTilesForTier3)
                buildActions = scenario.buildUnitOnTile(buildTile.row, buildTile.col, "soldierTier3", province)
                for buildAction in buildActions:
                    allActions.append((buildAction, province))
                for buildAction in buildActions:
                    scenario.applyAction(buildAction, province)
                continue
            # Tier 4
            buildableTilesForTier4 = getTilesWhichUnitCanBeBuiltOnGivenTiles(scenario, province, "soldierTier4", list(candidateBuildTiles))
            if buildableTilesForTier4:
                buildAUnitThisIteration = True
                buildTile = random.choice(buildableTilesForTier4)
                buildActions = scenario.buildUnitOnTile(buildTile.row, buildTile.col, "soldierTier4", province)
                for buildAction in buildActions:
                    allActions.append((buildAction, province))
                for buildAction in buildActions:
                    scenario.applyAction(buildAction, province)
                continue
            # If we reach here, we cannot build any more units
            canBuildMoreUnits = False

        # At this point, we might have merged provinces,
        # giving us new movable units. The resources
        # should have been drained by that while loop above,
        # so we just need to check for movable units again.
        notDoneWithCurrentProvince = len(getAllMovableUnitTilesInProvince(province)) > 0 and (moveAUnitThisIteration or buildAUnitThisIteration)
        if notDoneWithCurrentProvince:
            # Reset provinceIndex to reprocess this province
            provinceIndex -= 1 
        # Otherwise, we move on to the next province automatically
        

    # Invert all actions to restore the original scenario state
    for action, province in reversed(allActions):
        scenario.applyAction(action.invert(), province)

    return allActions
