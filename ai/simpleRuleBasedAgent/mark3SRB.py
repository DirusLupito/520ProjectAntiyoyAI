"""
Represents a rule-based agent which plays 
a replica of Antiyoy.

As with all AIs designed for this project,
they must implement one function called
playTurn which takes in the various variables
representing the game state and returns a list
of Actions and the associated province to run
those actions on.

Mark 3 version: Based on the Mark 2 and by extension, the Mark 1.
Improves on the Mark 2 by taking a much more careful and considered approach
to planning out unit movements, attacks, and structure building.

The approach is as follows:
PLAN_INITIAL_ATTACKS:
Iterate through every single movable unit in the province.
If there are any enemy tiles which can be attacked immediately, attack one of those randomly.
If there are no enemy tiles in range which can be attacked immediately,
but there are enemy tiles which could be attacked immediately if the unit had 1
higher attack power, mark the unit as needing a single tier upgrade.
If it needs 2 higher attack power, mark it as needing a double tier upgrade,
If it need 3 higher attack power, mark it as needing a triple tier upgrade.
Otherwise at this point if there are still no enemy tiles in range which can be attacked immediately,
it means there are no enemy tiles in range. Hold this unit in reserve for now.
We then restart the iteration, because maybe we merged provinces and have more movable units now.

PLAN_RESERVIST_MERGES:
If we go through an entire iteration without moving any units, it is time to move to the next phase.
For all of the units which needed a single tier upgrade to attack an enemy tile,
we check if any of its reachable tiles hold a tier 1 soldier unit which is in the reserve list.
If so, it means that reserve soldier can also reach the one needing the upgrade,
so we move that reserve soldier onto the soldier needing the upgrade to perform the merge.
We then attack the enemy tile with the newly upgraded soldier.
If no such tier 1 soldier could be found, we mark this unit as needing a double tier upgrade.
We repeat this process for double tier upgrades (looking for tier 2 soldiers to merge),
then triple tier upgrades (looking for tier 3 soldiers to merge).
We then restart the whole process again from the start because maybe we merged provinces 
and have more movable units now.

PLAN_CANNIBALIZE_MERGES:
If we go through an entire iteration without moving any units again, and without performing any upgrades,
then we will reset the upgrade requirements back to what they were (so a soldier who only 
needed a single tier upgrade but which got uptiered to a double tier upgrade will be reset
back to only needing a single tier upgrade), and we will now start 'cannibalizing' 
any soldier regardless of whether its a reservist or not to perform upgrades.
Other than the fact we might not be using a reservist, its essentially the same process as before,
where we try to perform first single tier upgrades, then double tier upgrades, then triple tier upgrades.

PLAN_TREE_AND_UNCLAIMED_MOVES:
If we go through an entire iteration without moving any units again, merging a reservist,
or merging any soldier to perform an attack, then while it is possible that the remaining
movable units could be used to attack an enemy tile, it would require a 'hopping' trick which
the Mark 3 will not be programmed to do. Instead, all remaining movable units will first
check if there are any tree tiles owned by the same province as the unit's province 
in range which can be moved to immediately, and if so, move to the tree tile to cut down the tree.
Otherwise, if there are no tree tiles in range which can be moved to immediately, but there are
unclaimed tiles in range which can be moved to immediately, the unit will move to one of those
unclaimed tiles.

PLAN_BUILD_ON_TREES:
At this point, if we go through an entire iteration without moving any units again,
without performing any upgrades, without merging any reservists, 
without merging any soldiers to perform an attack, without moving to a tree tile, 
and without moving to an unclaimed tile, then we will check if there are any tree tiles
anywhere owned by the current province. If there are, we will then try to build
as many soldierTier1s on all the tree tiles until either the province has less than
10 resources left, or there are no more tree tiles to build on (each built soldierTier1
will cost 10 resources and will cut down the tree on the tile which it is built on, 
so the tile will no longer be a tree tile after the soldier is built).

PLAN_BUILD_ON_UNCLAIMED_FRONTIER:
At this point, if we go through an entire iteration without doing any of the above actions,
then we will see if there are any unclaimed tiles on the frontier of the current province,
and first try to build soldierTier1s on those unclaimed tiles until either the province has less than
10 resources left, or there are no more unclaimed tiles which can be built on with a soldierTier1.

PLAN_UPGRADE_LEFTOVER_UNITS:
If we still have resources left after this stage, we will spend them on upgrading units which still
haven't moved because they need some sort of upgrade to be able to attack an enemy tile, 
but which haven't been upgraded yet because they never recieved any reinforcing units to
merge with. We will first try to upgrade those units which only needed a single tier upgrade, 
then those which needed a double tier upgrade, then those which needed a triple tier upgrade, 
until either we have no more resources left, or there are no more units which need upgrading.

PLAN_MOVE_TOWARDS_UNCLAIMED_OR_TREES_OR_ENEMIES:
At this point, any unit which can move but hasn't moved yet will be moved towards the nearest unclaimed
border tile, although by the nature of this process that unclaimed tile wilL be out of reach this turn,
so the unit will just move as close to it as possible. If there are no unclaimed tiles bordering
the current province, then the unit will move towards the nearest tree tile owned by the same province, 
and if there are no tree tiles owned by the same province, then the unit will move towards
the nearest enemy tile or stay still if they're already adjacent to an enemy tile
(they don't move to the enemy tile because either they don't have the attack power to attack it, 
or they're out of range to attack it, so they just move as close to it as possible in the hope 
that in the next turn they will be able to attack it).

PLAN_BUILD_FARMS_WITH_LEFTOVER_RESOURCES:
Any unspent resources at the end of all this will be spent to build a farm (must be either beside
a pre-existing farm or beside the capital) if a farm can be built, or will be saved.

Now after all this, the next province will be processed in the same way, 
and then the next province after that, and so on until all provinces have been processed.
After all provinces have been processed, playTurn is done.

Throughout every single step of this process, unit merges will not be performed unless
the province can afford to perform the merge. Sure, a merge costs nothing now,
but will result in a unit which has a higher upkeep. So 'afford' in this context means
that the province's income times 4 (so 4 turns worth of income) added to the province's 
current resources must be greater than 0 after the merge is performed. 
This will ensure that the province can afford to pay for the upkeep of the new unit
and all its existing units for at least 4 turns after the merge is performed, 
which should hopefully be enough time for enough new tiles or resources to be
acquired to make the merge worthwhile. If the province cannot afford to perform the merge,
then the merge will not be performed and the unit will be left in its current state.
Infinite loops are avoided in the prior steps because we check if anything changed during a whole
iteration of the process, and if nothing changed, we move on to the next step. 
This is important because if we don't check for this, we could end up in an infinite loop where 
we keep trying to perform the same action over and over again without any change in the game state,
which would cause the AI to get stuck and never move on to the next step of the process.

The overall AI is implemented as a state machine, where each iteration of the process
is a state, and if nothing changes during that iteration, we move to the next state.
"""

import pdb
import random
from ai.utils.commonAIUtilityFunctions import getMoveTowardsTargetTileAvoidingGivenTiles
from ai.utils.commonAIUtilityFunctions import checkTimeToBankruptProvince
from ai.utils.commonAIUtilityFunctions import getReachableTilesAsObjects
from ai.utils.commonAIUtilityFunctions import getAllMovableUnitTilesInProvince
from ai.utils.commonAIUtilityFunctions import getEnemyTilesInRangeOfTile
from ai.utils.commonAIUtilityFunctions import getDefenseRatingOfTile
from ai.utils.commonAIUtilityFunctions import getFrontierTiles
from ai.utils.commonAIUtilityFunctions import getTilesInProvinceWhichContainGivenUnitTypes
from ai.utils.commonAIUtilityFunctions import getTilesWhichUnitCanBeBuiltOn

# How many turns worth of income must a province be able to afford
# after performing a merge in order to be allowed to perform that merge.
turnsOfIncomeToAffordMerge = 4

def playTurn(scenario, faction):
    """
    Generates a list of actions for the AI's turn based on its set of rules.

    Args:
        scenario: The current game Scenario object.
        faction: The Faction object for which to play the turn.

    Returns:
        A list of (Action, province) tuples to be executed.
    """
    allActions = []

    # Our states correspond to the various major steps outlined above.
    PLAN_INITIAL_ATTACKS = 0
    PLAN_RESERVIST_MERGES = 1
    PLAN_CANNIBALIZE_MERGES = 2
    PLAN_TREE_AND_UNCLAIMED_MOVES = 3
    PLAN_BUILD_ON_TREES = 4
    PLAN_BUILD_ON_UNCLAIMED_FRONTIER = 5
    PLAN_UPGRADE_LEFTOVER_UNITS = 6
    PLAN_MOVE_TOWARDS_UNCLAIMED_OR_TREES_OR_ENEMIES = 7
    PLAN_BUILD_FARMS_WITH_LEFTOVER_RESOURCES = 8
    FINAL_STATE = 9

    provinceIndex = 0
    # We shall iterate through all provinces one by one,
    # individually completing the execution of their state machines.
    while provinceIndex < len(faction.provinces):
        province = faction.provinces[provinceIndex]
        if not province or not province.active:
            provinceIndex += 1
            continue

        # At this point we've selected a valid province to process.
        # Let's start the state machine from the beginning and set up our
        # various data structures.

        # upgradeNeeds will map from upgrade tier needed (1, 2, or 3)
        # to a list of tiles containing units which need that many upgrades
        upgradeNeeds = {1: [], 2: [], 3: []}

        # reserveTiles will hold tiles containing units which are being held in reserve
        # because they are out of range of any enemy tiles, regardless of how high they might be
        # able to be upgraded.
        reserveTiles = []

        # State is tracked in, you guessed it, 'state'.
        state = PLAN_INITIAL_ATTACKS

        # We will keep iterating through the state machine until we reach
        # the final state where we are done processing this province.
        while state != FINAL_STATE:
            if state == PLAN_INITIAL_ATTACKS:
                changed = planInitialAttacks(scenario, allActions, upgradeNeeds, reserveTiles, province)
                if not changed:
                    state = PLAN_RESERVIST_MERGES

            elif state == PLAN_RESERVIST_MERGES:
                changed = planReservistMerges(scenario, allActions, upgradeNeeds, reserveTiles, province)
                if not changed:
                    state = PLAN_CANNIBALIZE_MERGES
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []
                    # We might also have merged provinces and have more movable units now,
                    # so we need to go back to the initial attacks state.
                    state = PLAN_INITIAL_ATTACKS

            elif state == PLAN_CANNIBALIZE_MERGES:
                changed = planCannibalizeMerges(scenario, allActions, upgradeNeeds, province)
                if not changed:
                    state = PLAN_TREE_AND_UNCLAIMED_MOVES
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []
                    # We might also have merged provinces and have more movable units now,
                    # so we need to go back to the initial attacks state.
                    state = PLAN_INITIAL_ATTACKS

            elif state == PLAN_TREE_AND_UNCLAIMED_MOVES:
                changed = planTreeAndUnclaimedMoves(scenario, allActions, province)
                if not changed:
                    state = PLAN_BUILD_ON_TREES
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []
                    # We might also have merged provinces and have more movable units now,
                    # so we need to go back to the initial attacks state.
                    state = PLAN_INITIAL_ATTACKS

            elif state == PLAN_BUILD_ON_TREES:
                planBuildOnTrees(scenario, allActions, province)
                # The outcome of this state will not cause us to need to repeat any prior states,
                # so we can just move on to the next state directly.
                state = PLAN_BUILD_ON_UNCLAIMED_FRONTIER

            elif state == PLAN_BUILD_ON_UNCLAIMED_FRONTIER:
                changed = planBuildOnUnclaimedFrontier(scenario, allActions, province)
                if not changed:
                    state = PLAN_UPGRADE_LEFTOVER_UNITS
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []
                    # We might also have merged provinces and have more movable units now,
                    # so we need to go back to the initial attacks state.
                    state = PLAN_INITIAL_ATTACKS

            elif state == PLAN_UPGRADE_LEFTOVER_UNITS:
                changed = planUpgradeLeftoverUnits(scenario, allActions, upgradeNeeds, province)
                if not changed:
                    state = PLAN_MOVE_TOWARDS_UNCLAIMED_OR_TREES_OR_ENEMIES
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []
                    # We might also have merged provinces and have more movable units now,
                    # so we need to go back to the initial attacks state.
                    state = PLAN_INITIAL_ATTACKS

            elif state == PLAN_MOVE_TOWARDS_UNCLAIMED_OR_TREES_OR_ENEMIES:
                changed = planMoveTowardsUnclaimedOrTreesOrEnemies(scenario, allActions, province)
                # The outcome of this state will not cause us to need to repeat any prior states,
                # so we can just move on to the next state directly.
                state = PLAN_BUILD_FARMS_WITH_LEFTOVER_RESOURCES

            elif state == PLAN_BUILD_FARMS_WITH_LEFTOVER_RESOURCES:
                planBuildFarmsWithLeftoverResources(scenario, allActions, province)
                # The outcome of this state will not cause us to need to repeat any prior states,
                # so we can just move on to the next state directly.
                state = FINAL_STATE

        # We have finished processing this province, so we move on to the next one.
        provinceIndex += 1

    # Invert all actions to restore the original scenario state
    for action, province in reversed(allActions):
        scenario.applyAction(action.invert(), province)

    return allActions

def planInitialAttacks(scenario, allActions, upgradeNeeds, reserveTiles, province):   
    """
    Plans initial attacks for all movable units in the province.

    Args:
        scenario: The current game Scenario object.
        allActions: The list of all actions to be executed.
        upgradeNeeds: A dictionary mapping upgrade tiers to lists of tiles needing those upgrades.
        reserveTiles: A list of tiles containing units held in reserve.
        province: The Province currently undergoing action planning.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False
    movableUnitTiles = getAllMovableUnitTilesInProvince(province)
    # Note that getAllMovableUnitTilesInProvince returns a tuple of (tile, province),
    # so we need to unpack it.

    for tile, _ in movableUnitTiles:
        unit = tile.unit

        enemyTilesInRange = getEnemyTilesInRangeOfTile(scenario, tile, province)

        if enemyTilesInRange:
            # We know there is at least one enemy tile in range.
            # But now we need to check if we can attack any of them.
            # We need our soldier's attack power to be greater than or equal to
            # the enemy tile's defense rating.
            attackableEnemyTiles = []
            for enemyTile in enemyTilesInRange:
                if unit.attackPower >= getDefenseRatingOfTile(enemyTile):
                    attackableEnemyTiles.append(enemyTile)

            if attackableEnemyTiles:
                # We can attack at least one enemy tile!
                # Let's pick one at random and attack it.
                targetTile = random.choice(attackableEnemyTiles)
                moveActions = scenario.moveUnit(tile.row, tile.col, targetTile.row, targetTile.col)
                for moveAction in moveActions:
                    allActions.append((moveAction, province))
                # Apply the actions immediately to update the scenario state
                for moveAction in moveActions:
                    scenario.applyAction(moveAction, province)

                changed = True
            else:
                # There are enemy tiles in range, but we can't attack any of them.
                # Let's figure out how many upgrades we need to be able to attack one.
                minUpgradeNeeded = 4  # Start with a value higher than the max possible upgrade need

                # Now we check each enemy tile to see what the lowest upgrade needed 
                # to attack any of them is.
                for enemyTile in enemyTilesInRange:
                    defenseRating = getDefenseRatingOfTile(enemyTile)
                    upgradeNeeded = defenseRating - unit.attackPower
                    if upgradeNeeded < minUpgradeNeeded:
                        minUpgradeNeeded = upgradeNeeded

                # This if should always be true, but let's be safe.
                if minUpgradeNeeded >= 1 and minUpgradeNeeded <= 3:
                    # We need to upgrade our unit to be able to attack.
                    upgradeNeeds[minUpgradeNeeded].append(tile)
                else:
                    # We can't attack any enemy tiles even with upgrades.
                    reserveTiles.append(tile)
        else:
            # There are no enemy tiles in range.
            # The unit here must therefore be held in reserve
            # (unless we're already holding it in reserve).
            if tile not in reserveTiles:
                reserveTiles.append(tile)

    return changed

def planReservistMerges(scenario, allActions, upgradeNeeds, reserveTiles, province):
    """
    Plans how to merge appropriate reserve units to units needing upgrades
    in order to let those units in need of upgrades attack enemy tiles.

    Args:
        scenario: The current game Scenario object.
        allActions: The list of all actions to be executed.
        upgradeNeeds: A dictionary mapping upgrade tiers to lists of tiles needing those upgrades.
        reserveTiles: A list of tiles containing units held in reserve.
        province: The Province currently undergoing action planning.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False

    # We will process upgrades in order: first single tier upgrades,
    # then double tier upgrades, then triple tier upgrades.
    for upgradeTier in [1, 2, 3]:
        tilesNeedingUpgrade = upgradeNeeds[upgradeTier]
        for tileNeedingUpgrade in tilesNeedingUpgrade:
            # For each unit needing this upgrade, we will check if any
            # of its reachable tiles contain a reservist unit of the appropriate tier.
            foundMerge = False
            # Let's first figure out all the tiles within the movement range of the tile
            movementRangeTilesCoords = scenario.getAllTilesWithinMovementRange(tileNeedingUpgrade.row, tileNeedingUpgrade.col)

            # Now let's convert those coordinates to HexTile objects
            movementRangeTiles = getReachableTilesAsObjects(scenario, movementRangeTilesCoords)

            # Now we get the set of reservist tiles which overlap with the movement range tiles
            overlappingReservistTiles = [tile for tile in reserveTiles if tile in movementRangeTiles]

            # Finally, we filter those overlapping reservist tiles to only include those
            # which contain a unit of the appropriate tier.
            appropriateTierReservistTile = None
            for reservistTile in overlappingReservistTiles:
                reservistUnit = reservistTile.unit
                if reservistUnit.unitType == 'soldierTier' + str(upgradeTier):
                    appropriateTierReservistTile = reservistTile
                    # We only need one such reservist tile
                    break
        
            # If we found an appropriate tier reservist tile, we can perform the merge.
            # We must then ensure that the province can afford to perform the merge.
            # Otherwise, we must reverse the changes.
            if appropriateTierReservistTile:
                # We attempt the merge
                pdb.set_trace()
                moveActions = scenario.moveUnit(appropriateTierReservistTile.row, appropriateTierReservistTile.col,
                                                tileNeedingUpgrade.row, tileNeedingUpgrade.col)
                # Apply the actions immediately to update the scenario state
                for moveAction in moveActions:
                    scenario.applyAction(moveAction, province)

                # Now we check if the province can afford the merge
                timeToBankrupt = checkTimeToBankruptProvince(province)
                if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                    # The province cannot afford the merge, so we must reverse the actions
                    for moveAction in reversed(moveActions):
                        scenario.applyAction(moveAction.invert(), province)
                    # The merge did not happen
                else:
                    # The merge was successful, so this action must be recorded
                    for moveAction in moveActions:
                        allActions.append((moveAction, province))
                    # The attack logic will be handled in the next iteration of the state machine,
                    # so all we need to do here is mark that something changed, and clean up
                    # our data structures so that we don't try to reuse the same reservist tile again.
                    reserveTiles.remove(appropriateTierReservistTile)
                    changed = True
                    foundMerge = True
            
            # If we didn't find a merge for this unit, we need to re-add it to the upgradeNeeds
            # for the next upgrade tier.
            if not foundMerge:
                if upgradeTier < 3:
                    upgradeNeeds[upgradeTier + 1].append(tileNeedingUpgrade)

    return changed

def planCannibalizeMerges(scenario, allActions, upgradeNeeds, province):
    """
    Plans how to merge any appropriate units to units needing upgrades
    in order to let those units in need of upgrades attack enemy tiles.
    Almost identical to planReservistMerges, but does not restrict merges to reservist units.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        upgradeNeeds: A dictionary mapping upgrade tiers to lists of tiles needing upgrades.
        province: The province that is performing the merges.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False

    # We will process upgrades in order: first single tier upgrades,
    # then double tier upgrades, then triple tier upgrades.
    for upgradeTier in [1, 2, 3]:
        tilesNeedingUpgrade = upgradeNeeds[upgradeTier]
        for tileNeedingUpgrade in tilesNeedingUpgrade:
            # For each unit needing this upgrade, we will check if any
            # of its reachable tiles contain a unit of the appropriate tier.
            foundMerge = False
            # Let's first figure out all the tiles within the movement range of the tile
            movementRangeTilesCoords = scenario.getAllTilesWithinMovementRange(tileNeedingUpgrade.row, tileNeedingUpgrade.col)

            # Now let's convert those coordinates to HexTile objects
            movementRangeTiles = getReachableTilesAsObjects(scenario, movementRangeTilesCoords)

            # Remove the unit's own tile from the movement range tiles
            # This is important because otherwise we might try to merge the unit
            # with itself, which is not allowed.
            movementRangeTiles = [tile for tile in movementRangeTiles if tile != tileNeedingUpgrade]

            # Here's the only difference from planReservistMerges: Rather than looking for just reservist units
            # to merge with, we look for any unit of the appropriate tier which is movable.
            # Iterate through all the movement range tiles to find an appropriate unit.
            appropriateTierUnit = None
            for movementRangeTile in movementRangeTiles:
                if movementRangeTile.unit and movementRangeTile.owner.faction == province.faction and movementRangeTile.unit.canMove:
                    unit = movementRangeTile.unit
                    if unit.unitType == 'soldierTier' + str(upgradeTier):
                        appropriateTierUnit = movementRangeTile
                        # We only need one such unit
                        break
        
            # If we found an appropriate tier unit, we can perform the merge.
            # We must then ensure that the province can afford to perform the merge.
            # Otherwise, we must reverse the changes.
            if appropriateTierUnit:
                # We attempt the merge
                moveActions = scenario.moveUnit(appropriateTierUnit.row, appropriateTierUnit.col,
                                                tileNeedingUpgrade.row, tileNeedingUpgrade.col)
                # Apply the actions immediately to update the scenario state
                for moveAction in moveActions:
                    scenario.applyAction(moveAction, province)

                # Now we check if the province can afford the merge
                timeToBankrupt = checkTimeToBankruptProvince(province)
                if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                    # The province cannot afford the merge, so we must reverse the actions
                    for moveAction in reversed(moveActions):
                        scenario.applyAction(moveAction.invert(), province)
                    # The merge did not happen
                else:
                    # The merge was successful, record the action
                    for moveAction in moveActions:
                        allActions.append((moveAction, province))
                    # The attack logic will be handled in the next iteration of the state machine,
                    # so all we need to do here is mark that something changed.
                    changed = True
                    foundMerge = True
            
            # If we didn't find a merge for this unit, we need to re-add it to the upgradeNeeds
            # for the next upgrade tier.
            if not foundMerge:
                if upgradeTier < 3:
                    upgradeNeeds[upgradeTier + 1].append(tileNeedingUpgrade)

    return changed

def planTreeAndUnclaimedMoves(scenario, allActions, province):
    """
    Plans moves to get units onto tree tiles or unclaimed tiles,
    with a priority on tree tiles.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        province: The province that is performing the moves.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False
    movableUnitTiles = getAllMovableUnitTilesInProvince(province)

    for tile, _ in movableUnitTiles:
        # First, we check what this unit can reach.
        reachableTilesCoords = scenario.getAllTilesWithinMovementRange(tile.row, tile.col)
        reachableTiles = getReachableTilesAsObjects(scenario, reachableTilesCoords)

        # Now we iterate through the reachable tiles, keeping track of the first unclaimed tile
        # we find in case we don't find any tree tiles.
        # We prioritize tree tiles over unclaimed tiles, so even if we find an unclaimed tile first,
        # we keep looking for tree tiles.
        # If we find a tree tile, we move there immediately. 
        firstUnclaimedTile = None
        for reachableTile in reachableTiles:
            # Let's see if there's a tree tile we can move to.
            if reachableTile.unit and reachableTile.unit.unitType == 'tree' and reachableTile.owner == province:
                # We can move to this tree tile to cut down the tree.
                moveActions = scenario.moveUnit(tile.row, tile.col, reachableTile.row, reachableTile.col)
                for moveAction in moveActions:
                    allActions.append((moveAction, province))
                # Apply the actions immediately to update the scenario state
                for moveAction in moveActions:
                    scenario.applyAction(moveAction, province)

                changed = True
                break  # Move to the next movable unit tile
            elif reachableTile.owner is None and firstUnclaimedTile is None:
                # We found an unclaimed tile, but we keep looking for tree tiles.
                firstUnclaimedTile = reachableTile
        
        # If we didn't break out of the loop, it means we didn't find any tree tiles.
        # If we found an unclaimed tile, we move there.
        if firstUnclaimedTile:
            moveActions = scenario.moveUnit(tile.row, tile.col, firstUnclaimedTile.row, firstUnclaimedTile.col)
            for moveAction in moveActions:
                allActions.append((moveAction, province))
            # Apply the actions immediately to update the scenario state
            for moveAction in moveActions:
                scenario.applyAction(moveAction, province)

            changed = True


    return changed

def planBuildOnTrees(scenario, allActions, province):
    """
    Plans building soldierTier1 units on tree tiles owned by the province.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        province: The province that is performing the building.

    Returns:
        None
    """
    treeTiles = getTilesInProvinceWhichContainGivenUnitTypes(province, ["tree"])
    for treeTile in treeTiles:
        if province.resources >= 10:
            buildActions = scenario.buildUnitOnTile(treeTile.row, treeTile.col, "soldierTier1", province)
            # Apply the actions immediately to update the scenario state
            for buildAction in buildActions:
                scenario.applyAction(buildAction, province)
            
            # Ensure we can afford to build this unit
            timeToBankrupt = checkTimeToBankruptProvince(province)
            if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                # The province cannot afford the soldier, so we must reverse the actions
                for buildAction in reversed(buildActions):
                    scenario.applyAction(buildAction.invert(), province)
                # If we can't build this unit, we stop trying to build more units
                break
            else:
                # The build was successful, so we record the actions
                for buildAction in buildActions:
                    allActions.append((buildAction, province))

def planBuildOnUnclaimedFrontier(scenario, allActions, province):
    """
    Plans building soldierTier1 units on unclaimed frontier tiles of the province.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        province: The province that is performing the building.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False
    frontierTiles = getFrontierTiles(province)
    unclaimedFrontierTiles = [tile for tile in frontierTiles if tile.owner is None]

    for unclaimedTile in unclaimedFrontierTiles:
        if province.resources >= 10:
            buildActions = scenario.buildUnitOnTile(unclaimedTile.row, unclaimedTile.col, "soldierTier1", province)
            # Apply the actions immediately to update the scenario state
            for buildAction in buildActions:
                scenario.applyAction(buildAction, province)

            # Ensure we can afford to build this unit
            timeToBankrupt = checkTimeToBankruptProvince(province)
            if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                # The province cannot afford the soldier, so we must reverse the actions
                for buildAction in reversed(buildActions):
                    scenario.applyAction(buildAction.invert(), province)
                
                # If we can't build this unit, we stop trying to build more units
                break
            else:
                # The build was successful, so we mark that something changed
                # and record the actions
                for buildAction in buildActions:
                    allActions.append((buildAction, province))
                changed = True

    return changed

def planUpgradeLeftoverUnits(scenario, allActions, upgradeNeeds, province):
    """
    Plans upgrading leftover units which need upgrades to attack enemy tiles.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        upgradeNeeds: A dictionary mapping upgrade tiers to lists of tiles needing upgrades.
        province: The province that is performing the upgrades.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False

    # We will process upgrades in order: first single tier upgrades,
    # then double tier upgrades, then triple tier upgrades.
    for upgradeTier in [1, 2, 3]:
        tilesNeedingUpgrade = upgradeNeeds[upgradeTier]
        for tileNeedingUpgrade in tilesNeedingUpgrade:
            # Let's attempt to build the necessary soldier to perform the upgrade.
            unitTypeToBuild = 'soldierTier' + str(upgradeTier)
            neededResources = 10 * upgradeTier
            if province.resources >= neededResources:
                pdb.set_trace()
                buildActions = scenario.buildUnitOnTile(tileNeedingUpgrade.row, tileNeedingUpgrade.col, unitTypeToBuild, province)
                # Apply the actions immediately to update the scenario state
                for buildAction in buildActions:
                    scenario.applyAction(buildAction, province)

                # Let's ensure we can afford to build this unit
                timeToBankrupt = checkTimeToBankruptProvince(province)
                if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                    # The province cannot afford the soldier, so we must reverse the actions
                    for buildAction in reversed(buildActions):
                        scenario.applyAction(buildAction.invert(), province)
                else:
                    # The build was successful, so we mark that something changed
                    # and record the actions
                    for buildAction in buildActions:
                        allActions.append((buildAction, province))
                    changed = True

    return changed

def planMoveTowardsUnclaimedOrTreesOrEnemies(scenario, allActions, province):
    """
    Plans moves for units towards the closest unclaimed tile, tree tile, or enemy tile,
    taking care to not accidentally move a unit on top of another unit thereby either
    causing an exception or an unintended merge.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        province: The province that is performing the moves.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False
    movableUnitTiles = getAllMovableUnitTilesInProvince(province)

    # We want to avoid moving onto tiles occupied by our own units,
    # so we build a set of such tiles to avoid.
    tilesToAvoid = set()

    # We shall populate tilesToAvoid with all tiles in the province
    # that contain our own units.
    for tile in province.tiles:
        if tile.unit:
            tilesToAvoid.add(tile)

    # Our target tiles will be unclaimed tiles and tree tiles.
    targetTiles = []
    treeTiles = getTilesInProvinceWhichContainGivenUnitTypes(province, ["tree"])
    targetTiles.extend(treeTiles)
    frontierTiles = getFrontierTiles(province)
    unclaimedFrontierTiles = [tile for tile in frontierTiles if tile.owner is None]
    targetTiles.extend(unclaimedFrontierTiles)

    # If targetTiles is empty, there are no unclaimed or tree tiles to move towards.
    # So that means we must be devoid of trees and only bordering hostile territory.
    # In this case, we will try to move towards the closest enemy tile.
    if len(targetTiles) == 0:
        # We already have frontierTiles computed.
        # And we know that all frontier tiles are enemy tiles in this case.
        targetTiles.extend(frontierTiles)

    # If somehow targetTiles is still empty, there is nothing to move towards.
    # So we can just return.
    if len(targetTiles) == 0:
        return changed

    for tile, _ in movableUnitTiles:
        # We can now just delegate to a helper to find the first move towards the closest target tile,
        # avoiding tiles occupied by our own units.
        destinationTile = getMoveTowardsTargetTileAvoidingGivenTiles(tile, targetTiles, tilesToAvoid, scenario)

        # This could be None, meaning there is no valid path to any target tile.
        if destinationTile:
            moveActions = scenario.moveUnit(tile.row, tile.col, destinationTile.row, destinationTile.col)
            for moveAction in moveActions:
                allActions.append((moveAction, province))
            # Apply the actions immediately to update the scenario state
            for moveAction in moveActions:
                scenario.applyAction(moveAction, province)

            changed = True

    return changed

def planBuildFarmsWithLeftoverResources(scenario, allActions, province):
    """
    Plans actions to build farms if possible.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        province: The province that is performing the building.

    Returns:
        None
    """
    # Let's see if we can even build a farm.
    farmCandidates = getTilesWhichUnitCanBeBuiltOn(scenario, province, "farm")
    # Keep on building farms while we have candidates
    while farmCandidates:
        # We only build one farm at a time since the helper only guarantees
        # enough resources for a single build.
        farmTile = random.choice(farmCandidates)
        # The helper function already ensures we have enough resources to build the farm.
        buildActions = scenario.buildUnitOnTile(farmTile.row, farmTile.col, "farm", province)
        # Apply the actions immediately to update the scenario state
        for buildAction in buildActions:
            scenario.applyAction(buildAction, province)
        
        # Unlike other builds, we don't need to check affordability here,
        # since farms do not cost upkeep and do not get destroyed when a
        # province goes bankrupt.
        for buildAction in buildActions:
            allActions.append((buildAction, province))

        # Recompute farm candidates for the next iteration
        farmCandidates = getTilesWhichUnitCanBeBuiltOn(scenario, province, "farm")
