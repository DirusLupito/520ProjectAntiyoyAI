"""
Represents a rule-based agent which plays 
a replica of Antiyoy.

As with all AIs designed for this project,
they must implement one function called
playTurn which takes in the various variables
representing the game state and returns a list
of Actions and the associated province to run
those actions on.

Mark 4 version: An optimization of the Mark 3's state machine.
Improves on the Mark 3 with alterations to the following states:
PLAN_INITIAL_ATTACKS
PLAN_RESERVIST_MERGES
PLAN_CANNIBALIZE_MERGES
PLAN_BUILD_UNITS_WITH_LEFTOVER_RESOURCES
In addition, the order of states has be rearranged so that PLAN_BUILD_UNITS_WITH_LEFTOVER_RESOURCES
is the 7th state, PLAN_MOVE_TOWARDS_UNCLAIMED_OR_TREES_OR_ENEMIES is the 8th state,
and PLAN_BUILD_FARMS_WITH_LEFTOVER_RESOURCES is the 9th state.

A full description of each of the altered states is given below.
For unaltered states, please refer to the Mark 3 documentation.

PLAN_INITIAL_ATTACKS:
Iterate through every single movable unit in the province in order of tier descending,
so that higher tier units get to attack first and potentially break through enemy defenses.
If there are any enemy tiles which can be attacked immediately, attack them with a preference for 
attacking the enemy tile with the most value. Here, the idea is to first
``reduce'' the enemy's ability to defend themselves, then to cripple their industry, if such an industry exists,
and then if neither of those are possible, to simply make inroads into the most fortified enemy positions.
The value, or preference order, of enemy tiles is defined as follows:
1. A tile which would isolate any of the tiles 2-9 below from the rest of the enemy's territory as a single tile.
2. Tower2
3. Tower1
4. soldierTier4
5. soldierTier3
6. soldierTier2
7. soldierTier1
8. capital
9. farm
10. All other tiles, which themselves are sorted based on their defense rating, with a higher defense rating being preferred.
If there are no enemy tiles in range which can be attacked immediately,
but there are enemy tiles which could be attacked immediately if the unit had 1
higher attack power, mark the unit as needing a single tier upgrade.
If it needs 2 higher attack power, mark it as needing a double tier upgrade,
If it need 3 higher attack power, mark it as needing a triple tier upgrade.
All single tile provinces, or inactive provinces, are treated as neutral territory for the purposes of this check,
and so they will not be attacked or considered for an attack in this state.
Otherwise at this point if there are still no enemy tiles in range which can be attacked immediately,
it means there are no enemy tiles in range. Hold this unit in reserve for now.

PLAN_RESERVIST_MERGES:
If we go through an entire iteration without moving any units, it is time to move to the next phase.
For all of the units which needed a single tier upgrade to attack an enemy tile,
we check if any of its reachable tiles hold a tier 1 soldier unit which is in the reserve list.
If so, it means that reserve soldier can also reach the one needing the upgrade,
so we move that reserve soldier onto the soldier needing the upgrade to perform the merge.
We then attack the enemy tile with the newly upgraded soldier.
If no such tier 1 soldier could be found, we mark this unit as needing a double tier upgrade.
We repeat this process for double tier upgrades (looking for tier 2 soldiers to merge, 
then 2 tier 1 soldiers to merge in succession), then triple tier upgrades (looking for tier 3 soldiers to merge, 
then 2 tier 1 soldiers to merge in succession, then 3 tier 1 soldiers to merge in succession).
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
We also ensure that no unit which has already recieved an upgrade (or upgrades) in this phase can be itself cannibalized
since such a unit would already be able to attack an enemy tile, 
and for cheaper than if it were to be merged again.

PLAN_TREE_AND_UNCLAIMED_MOVES:
If we go through an entire iteration without moving any units again, merging a reservist,
or merging any soldier to perform an attack, then while it is possible that the remaining
movable units could be used to attack an enemy tile, it would require a 'hopping' trick which
would give minimal benefit compared to using those units to cut down trees and claim unclaimed tiles instead.
Instead, all remaining movable units will first check if there are any tree tiles owned by the same 
province as the unit's province in range which can be moved to immediately, and if so, move to the tree tile to cut down the tree.
Otherwise, if there are no tree tiles in range which can be moved to immediately, but there are
single tile inactive enemy provinces with a defense rating of 1 or lower, then move to those tiles to claim them.
Finally, if neither of those are possible, check for unclaimed tiles in range which can be moved to immediately,
and move to those tiles to claim them if possible.

PLAN_BUILD_UNITS_WITH_LEFTOVER_RESOURCES:
After upgrading leftover units, we attempt to build soldiers on all hostile tiles to conquer them,
so that we have a way of continuing to expand the military presence of the province even
if there are no tree tiles or unclaimed tiles left to build on. In this state, we will also
consider inactive provinces/single tile provinces as valid targets for building soldiers on,
but only if they have a defense rating of 1 or lower, to avoid wasting resources on attacking a
fortified position which will starve out and cease to exist next turn anyway.
If changes are made during this step, we go back to the start of the process.
"""

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
    PLAN_BUILD_UNITS_WITH_LEFTOVER_RESOURCES = 7
    PLAN_MOVE_TOWARDS_UNCLAIMED_OR_TREES_OR_ENEMIES = 8
    PLAN_BUILD_FARMS_WITH_LEFTOVER_RESOURCES = 9
    FINAL_STATE = 10

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
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []

            elif state == PLAN_RESERVIST_MERGES:
                # We need to pass in a copy of upgradeNeeds because it may be modified
                # by planReservistMerges, and we want planCannibalizeMerges to have the original state.
                upgradeNeedsCopy = {1: list(upgradeNeeds[1]), 2: list(upgradeNeeds[2]), 3: list(upgradeNeeds[3])}
                changed = planReservistMerges(scenario, allActions, upgradeNeedsCopy, reserveTiles, province)
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
                # We again pass in a copy of upgradeNeeds, this time to let planUpgradeLeftoverUnits
                # have the original state of upgradeNeeds.
                upgradeNeedsCopy = {1: list(upgradeNeeds[1]), 2: list(upgradeNeeds[2]), 3: list(upgradeNeeds[3])}
                changed = planCannibalizeMerges(scenario, allActions, upgradeNeedsCopy, province)
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
                # Note that we do not pass in a copy of upgradeNeeds here,
                # because there is no further state which uses upgradeNeeds after this one,
                # unless we loop back to PLAN_INITIAL_ATTACKS, in which case upgradeNeeds
                # gets reset anyway.
                changed = planUpgradeLeftoverUnits(scenario, allActions, upgradeNeeds, province)
                if not changed:
                    state = PLAN_BUILD_UNITS_WITH_LEFTOVER_RESOURCES
                else:
                    # If we made changes, we need to reset the upgradeNeeds and reserveTiles
                    # because the game state has changed and some units may no longer need upgrades
                    # or may now be in range of enemy tiles.
                    upgradeNeeds = {1: [], 2: [], 3: []}
                    reserveTiles = []
                    # We might also have merged provinces and have more movable units now,
                    # so we need to go back to the initial attacks state.
                    state = PLAN_INITIAL_ATTACKS

            elif state == PLAN_BUILD_UNITS_WITH_LEFTOVER_RESOURCES:
                changed = planBuildUnitsWithLeftoverResources(scenario, allActions, province)
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
                planMoveTowardsUnclaimedOrTreesOrEnemies(scenario, allActions, province)
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

    # We now sort the movableUnitTiles by unit tier descending, so we can prioritize higher-tier units.
    # If movabile tiles has a tile where either unit is None, or unit.tier is None, this will raise an exception,
    # but that's ok since the only way that could happen is if getAllMovableUnitTilesInProvince is broken,
    # so this would help us catch that bug anyway.
    movableUnitTiles.sort(key=lambda x: x[0].unit.tier, reverse=True)

    for tile, _ in movableUnitTiles:
        unit = tile.unit

        allEnemyTilesInRange = getEnemyTilesInRangeOfTile(scenario, tile, province)

        # Let's filter out all the enemy tiles which belong to single-tile provinces/inactive provinces,
        # since these can be bypassed by our offensive units and cleaned up later once their units
        # have starved to death.
        filteredEnemyTilesInRange = [tile for tile in allEnemyTilesInRange if len(tile.owner.tiles) > 1]

        if filteredEnemyTilesInRange:
            # We know there is at least one enemy tile in range.
            # But now we need to check if we can attack any of them.
            # We need our soldier's attack power to be greater than or equal to
            # the enemy tile's defense rating.
            attackableEnemyTiles = []
            for enemyTile in filteredEnemyTilesInRange:
                if unit.attackPower >= getDefenseRatingOfTile(enemyTile):
                    attackableEnemyTiles.append(enemyTile)

            if attackableEnemyTiles:
                # We can attack at least one enemy tile!
                # Lets figure out the priority order of the tiles we can attack.
                tilePriorityPairs = []
                targetTile = None
                for i in range(len(attackableEnemyTiles)):
                    enemyTile = attackableEnemyTiles[i]
                    priorityValue = _getTileTargetPriorityValue(enemyTile)
                    tilePriorityPairs.append((priorityValue, enemyTile))
                    # If we found a priority 1 tile, we can stop searching.
                    if priorityValue == 1:
                        targetTile = enemyTile
                        break

                # If we didn't find a priority 1 tile, we need to sort the tiles by priority value
                # and pick one of the highest priority ones (at random if there are multiple).
                if not targetTile:
                    # Sort the tilePriorityPairs by priority value ascending
                    tilePriorityPairs.sort(key=lambda x: x[0])
                    highestPriorityValue = tilePriorityPairs[0][0]
                    highestPriorityTiles = [pair[1] for pair in tilePriorityPairs if pair[0] == highestPriorityValue]
                    targetTile = random.choice(highestPriorityTiles)

                # Now that we have selected our target tile, we can move towards it and attack it.
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
                for enemyTile in filteredEnemyTilesInRange:
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

def _getTileTargetPriorityValue(tile):
    """
    This function computes the priority value of a tile as a target for attacks.
    Used as a helper in planInitialAttacks to implement the tile priority system
    described in the documentation.

    Args:
        scenario: The current game Scenario object.
        tile: The HexTile object to evaluate.
        province: The Province currently undergoing action planning.

    Returns:
        An integer representing the priority value of the tile as a target, 
        with 1 being the highest priority, and larger numbers being lower priority.
    """
    # First, we check if the tile is a priority 1 tile, i.e. if it would isolate any
    # of the other priority tiles from the rest of the enemy's territory as a single tile.
    enemyProvince = tile.owner

    priorityRatingMap = {
        'tower2': 2,
        'tower1': 3,
        'soldierTier4': 4,
        'soldierTier3': 5,
        'soldierTier2': 6,
        'soldierTier1': 7,
        'capital': 8,
        'farm': 9
    }

    # Let's see if any of this tile's neighbors belong to the enemy province,
    # and have this tile as their only neighbor also belonging to the enemy province.
    for neighbor in tile.neighbors:
        if neighbor and neighbor.owner == enemyProvince:
            enemyNeighborCount = 0
            for neighborOfNeighbor in neighbor.neighbors:
                if neighborOfNeighbor and neighborOfNeighbor.owner == enemyProvince:
                    enemyNeighborCount += 1

                # No need to continue if we already have 2 or more enemy neighbors
                if enemyNeighborCount >= 2:
                    break

            if enemyNeighborCount == 1:
                # This neighbor would be isolated by attacking this tile,
                # so this is a priority 1 tile.
                return 1
    
    # Now we check for other priority tiles
    if tile.unit and tile.unit.unitType in priorityRatingMap:
        return priorityRatingMap[tile.unit.unitType]
    
    # All other tiles are priority 14 - their defense rating
    # to ensure that higher defense rating tiles are preferred.
    # The reason we use 14 is that the maximum defense rating
    # of any tile is 4, so this ensures that even the highest
    # defense rating tile will have a priority value of at least 10,
    # which is lower priority than all of the special tiles above.
    return 14 - getDefenseRatingOfTile(tile)

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

            # Represents all the tiles which hold reservist units that we will be merging with.
            appropriateTierReservistTiles = []

            # Now let's first figure out if we can merge with just 1 reservist unit 
            # to get to our desired upgrade tier.
            for reservistTile in overlappingReservistTiles:
                reservistUnit = reservistTile.unit
                if reservistUnit.unitType == 'soldierTier' + str(upgradeTier):
                    appropriateTierReservistTiles.append(reservistTile)
                    # We only need one such reservist tile
                    break
            
            # If we couldn't find a single reservist unit of the appropriate tier,
            # let's see if we can find 2 or 3 reservist units of the appropriate tier to merge in succession.
            # In the case of a double tier upgrade, we need 2 tier 1 reservists.
            # In the case of a triple tier upgrade, we need either 1 tier 2 reservist and 1 tier 1 reservist,
            # or 3 tier 1 reservists.
            if not appropriateTierReservistTiles:
                if upgradeTier == 2:
                    # Need 2 tier 1 reservists
                    tier1ReservistTiles = [tile for tile in overlappingReservistTiles if tile.unit.unitType == 'soldierTier1']
                    if len(tier1ReservistTiles) >= 2:
                        appropriateTierReservistTiles.extend(tier1ReservistTiles[:2])
                elif upgradeTier == 3:
                    # Need 1 tier 2 reservist and 1 tier 1 reservist, or 3 tier 1 reservists
                    # We want to prefer using a tier 2 reservist if possible, since it will be
                    # more monetarily efficient.
                    tier2ReservistTiles = [tile for tile in overlappingReservistTiles if tile.unit.unitType == 'soldierTier2']
                    tier1ReservistTiles = [tile for tile in overlappingReservistTiles if tile.unit.unitType == 'soldierTier1']
                    if tier2ReservistTiles and tier1ReservistTiles:
                        appropriateTierReservistTiles.append(tier2ReservistTiles[0])
                        appropriateTierReservistTiles.append(tier1ReservistTiles[0])
                    elif len(tier1ReservistTiles) >= 3 and not tier2ReservistTiles:
                        appropriateTierReservistTiles.extend(tier1ReservistTiles[:3])

            # If we found appropriate tier reservist tiles, we can perform the merge.
            # We must then ensure that the province can afford to perform the merge.
            # Otherwise, we must reverse the changes.
            if appropriateTierReservistTiles:
                allMoveActions = []
                for reservistTile in appropriateTierReservistTiles:
                    # We attempt the merge
                    moveActions = scenario.moveUnit(reservistTile.row, reservistTile.col,
                                                    tileNeedingUpgrade.row, tileNeedingUpgrade.col)
                    # Apply the actions immediately to update the scenario state
                    for moveAction in moveActions:
                        scenario.applyAction(moveAction, province)
                    
                    # Keep track of all move actions for potential reversal later
                    allMoveActions.extend(moveActions)

                # Now after all merges, we check if the province can afford the merge
                timeToBankrupt = checkTimeToBankruptProvince(province)
                if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                    # The province cannot afford the merge, so we must reverse the actions
                    for moveAction in reversed(allMoveActions):
                        scenario.applyAction(moveAction.invert(), province)
                    # The merge did not happen
                else:
                    # The merge was successful, so these actions must be recorded
                    for moveAction in allMoveActions:
                        allActions.append((moveAction, province))
                    # The attack logic will be handled in the next iteration of the state machine,
                    # so all we need to do here is mark that something changed, and clean up
                    # our data structures so that we don't try to reuse the same reservist tiles again.
                    for reservistTile in appropriateTierReservistTiles:
                        reserveTiles.remove(reservistTile)
                    changed = True
                    foundMerge = True
            
            # If we didn't find a merge for this unit, we need to re-add it to the upgradeNeeds
            # for the next upgrade tier, and remove it from the current upgrade tier.
            # We also need to make sure we don't mark a unit as needing an illegal upgrade tier,
            # like an soldierTier3 needing a 2 tier upgrade, as this would cause an exception later
            # on if a soldierTier2 actually tried to merge with that soldierTier3.
            if not foundMerge:
                if tileNeedingUpgrade.unit is not None and upgradeTier + tileNeedingUpgrade.unit.tier < 4:
                    upgradeNeeds[upgradeTier + 1].append(tileNeedingUpgrade)
                upgradeNeeds[upgradeTier].remove(tileNeedingUpgrade)

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

    # We need to forbid cannibalizing any units which have already
    # received an upgrade in this phase, since such units would already
    # be able to attack an enemy tile, and for cheaper than if they
    # were to be merged again.
    alreadyUpgradedTiles = []

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
            # We don't check tile equality by object identity, but rather by row and column,
            # since upgradeNeeds is a deep copy.
            movementRangeTiles = [tile for tile in movementRangeTiles if tile.row != tileNeedingUpgrade.row or tile.col != tileNeedingUpgrade.col]

            # Here's the only difference from planReservistMerges: Rather than looking for just reservist units
            # to merge with, we look for any unit of the appropriate tier which is movable and which has not already been upgraded
            # in this phase.
            appropriateTierUnits = []
            
            # Iterate through all the movement range tiles to find a single appropriate unit.
            for movementRangeTile in movementRangeTiles:
                if (movementRangeTile.unit and movementRangeTile.owner == province and
                    movementRangeTile.unit.canMove and movementRangeTile not in alreadyUpgradedTiles):
                    unit = movementRangeTile.unit
                    if unit.unitType == 'soldierTier' + str(upgradeTier):
                        appropriateTierUnits.append(movementRangeTile)
                        # We only need one such unit
                        break
            
            # If we couldn't find a single unit of the appropriate tier,
            # let's see if we can find 2 or 3 units of the appropriate tier to merge in succession.
            # In the case of a double tier upgrade, we need 2 tier 1 units.
            # In the case of a triple tier upgrade, we need either 1 tier 2 unit and 1 tier 1 unit,
            # or 3 tier 1 units.
            if not appropriateTierUnits:
                if upgradeTier == 2:
                    # Need 2 tier 1 units
                    tier1Units = [tile for tile in movementRangeTiles if (tile.unit and tile.owner == province and
                                                                        tile.unit.canMove and tile not in alreadyUpgradedTiles and
                                                                        tile.unit.unitType == 'soldierTier1')]
                    if len(tier1Units) >= 2:
                        appropriateTierUnits.extend(tier1Units[:2])
                elif upgradeTier == 3:
                    # Need 1 tier 2 unit and 1 tier 1 unit, or 3 tier 1 units
                    # We want to prefer using a tier 2 unit if possible, since it will be
                    # more monetarily efficient.
                    tier2Units = [tile for tile in movementRangeTiles if (tile.unit and tile.owner == province and
                                                                        tile.unit.canMove and tile not in alreadyUpgradedTiles and
                                                                        tile.unit.unitType == 'soldierTier2')]
                    tier1Units = [tile for tile in movementRangeTiles if (tile.unit and tile.owner == province and
                                                                        tile.unit.canMove and tile not in alreadyUpgradedTiles and
                                                                        tile.unit.unitType == 'soldierTier1')]
                    if tier2Units and tier1Units:
                        appropriateTierUnits.append(tier2Units[0])
                        appropriateTierUnits.append(tier1Units[0])
                    elif len(tier1Units) >= 3 and not tier2Units:
                        appropriateTierUnits.extend(tier1Units[:3])

            # If we found appropriate tier units, we can perform the merge.
            # We must then ensure that the province can afford to perform the merge.
            # Otherwise, we must reverse the changes.
            if appropriateTierUnits:
                allMoveActions = []
                for unitTile in appropriateTierUnits:
                    # We attempt the merge
                    moveActions = scenario.moveUnit(unitTile.row, unitTile.col,
                                                    tileNeedingUpgrade.row, tileNeedingUpgrade.col)
                    # Apply the actions immediately to update the scenario state
                    for moveAction in moveActions:
                        scenario.applyAction(moveAction, province)
                    
                    # Keep track of all move actions for potential reversal later
                    allMoveActions.extend(moveActions)

                # Now after all merges, we check if the province can afford the merge
                timeToBankrupt = checkTimeToBankruptProvince(province)
                if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                    # The province cannot afford the merge, so we must reverse the actions
                    for moveAction in reversed(allMoveActions):
                        scenario.applyAction(moveAction.invert(), province)
                    # The merge did not happen
                else:
                    # The merge was successful, so these actions must be recorded
                    for moveAction in allMoveActions:
                        allActions.append((moveAction, province))
                    # The attack logic will be handled in the next iteration of the state machine,
                    # so all we need to do here is mark that something changed.
                    changed = True
                    foundMerge = True
                    # And make sure we don't cannibalize this unit
                    alreadyUpgradedTiles.append(tileNeedingUpgrade)
            
            # If we didn't find a merge for this unit, we need to re-add it to the upgradeNeeds
            # for the next upgrade tier, and remove it from the current upgrade tier.
            # We also need to make sure we don't mark a unit as needing an illegal upgrade tier,
            # like an soldierTier3 needing a 2 tier upgrade, as this would cause an exception later
            # on if a soldierTier2 actually tried to merge with that soldierTier3.
            if not foundMerge:
                if tileNeedingUpgrade.unit is not None and upgradeTier + tileNeedingUpgrade.unit.tier < 4:
                    upgradeNeeds[upgradeTier + 1].append(tileNeedingUpgrade)
                upgradeNeeds[upgradeTier].remove(tileNeedingUpgrade)

    return changed

def planTreeAndUnclaimedMoves(scenario, allActions, province):
    """
    Plans moves to get units onto tree tiles or unclaimed tiles,
    with a priority on tree tiles, then on unclaimed tiles
    belonging to single-tile enemy provinces, then on unclaimed tiles owned by no one.

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
        # We prioritize single-tile provinces controlled by enemies over unclaimed tiles as well,
        # but not over tree tiles.
        # If we find a tree tile, we move there immediately.
        firstUnclaimedTile = None
        firstSingleTileProvince = None
        foundTreeTile = False
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
                foundTreeTile = True
                break  # Move to the next movable unit tile
            # Let's see if there's a single tile province controlled by an enemy we can move to
            # if no trees are found.
            elif (reachableTile.owner is not None and reachableTile.owner != province and
                  len(reachableTile.owner.tiles) == 1 and firstSingleTileProvince is None
                  and getDefenseRatingOfTile(reachableTile) <= tile.unit.attackPower):
                # We found a single-tile province controlled by an enemy.
                # But let's keep looking for tree tiles first.
                firstSingleTileProvince = reachableTile
            elif reachableTile.owner is None and firstUnclaimedTile is None:
                # We found an unclaimed tile, but we keep looking for tree tiles or single-tile provinces.
                firstUnclaimedTile = reachableTile

        # If we didn't find a tree tile but we did find a single-tile province, we move there.
        if not foundTreeTile and firstSingleTileProvince is not None:
            moveActions = scenario.moveUnit(tile.row, tile.col, firstSingleTileProvince.row, firstSingleTileProvince.col)

            for moveAction in moveActions:
                allActions.append((moveAction, province))
            # Apply the actions immediately to update the scenario state
            for moveAction in moveActions:
                scenario.applyAction(moveAction, province)

            changed = True

            continue  # Move to the next movable unit tile

        # If we didn't find a tree tile or a single-tile province, but we did find an unclaimed tile, we move there.
        if not foundTreeTile and firstSingleTileProvince is None and firstUnclaimedTile is not None:
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

def planBuildUnitsWithLeftoverResources(scenario, allActions, province):
    """
    Plans actions to build soldiers on all hostile controlled frontier tiles,
    starting with the cheapest tiles first.

    Args:
        scenario: The current game Scenario object.
        allActions: A list to store all planned actions.
        province: The province that is performing the building.

    Returns:
        A boolean indicating whether any changes were made.
    """
    changed = False
    # Let's first get our frontier, as it will contain as a subset
    # all the hostile controlled tiles we can build on.
    frontierTiles = getFrontierTiles(province)
    hostileFrontierTiles = [tile for tile in frontierTiles if tile.owner is not None and tile.owner != province]

    # Now we shall sort hostileFrontierTiles by attack priority (smaller is better),
    # so that we try to build on the highest priority tiles first.
    tilePriorityPairs = []
    for i in range(len(hostileFrontierTiles)):
        enemyTile = hostileFrontierTiles[i]
        priorityValue = _getTileTargetPriorityValue(enemyTile)
        tilePriorityPairs.append((priorityValue, enemyTile))

    # Sort the hostileFrontierTiles by priority value ascending
    # While the first priority is still cost-based, if two tiles have the same
    # cost, we want to prefer taking over the one that will hurt the enemy the most.
    tilePriorityPairs.sort(key=lambda x: x[0])
    hostileFrontierTiles = [pair[1] for pair in tilePriorityPairs]

    while hostileFrontierTiles and province.resources >= 10:
        # Let's go through the entire hostile frontier and figure out what the cheapest
        # tile to build on is.
        # Of course, if we find a tile that we can put a soldierTier1 on, we will pick that immediately,
        # as no other tile can be cheaper than that.
        cheapestTile = None
        cheapestUnitType = None
        cheapestCost = float('inf')
        for tile in hostileFrontierTiles:
            # We check what soldier types can be built on this tile
            buildableUnitTypes = scenario.getBuildableUnitsOnTile(tile.row, tile.col, province)
            for unitType in buildableUnitTypes:
                if unitType.startswith('soldierTier'):
                    # Tier of soldier will always be the last character of the unit type string
                    tier = int(unitType[-1])
                    unitCost = 10 * tier
                    if unitCost < cheapestCost:
                        cheapestCost = unitCost
                        cheapestTile = tile
                        cheapestUnitType = unitType
                        # If we found a soldierTier1, we can break out of both loops immediately
                        if tier == 1:
                            break
            if cheapestCost == 10:
                break

        if cheapestTile and cheapestUnitType:
            buildActions = scenario.buildUnitOnTile(cheapestTile.row, cheapestTile.col, cheapestUnitType, province)
            # Apply the actions immediately to update the scenario state
            for buildAction in buildActions:
                scenario.applyAction(buildAction, province)

            # Ensure we can afford to build this unit
            timeToBankrupt = checkTimeToBankruptProvince(province)
            if timeToBankrupt is not None and timeToBankrupt < turnsOfIncomeToAffordMerge:
                # The province cannot afford the soldier, so we must reverse the actions
                for buildAction in reversed(buildActions):
                    scenario.applyAction(buildAction.invert(), province)
                # As we picked the cheapest tile to build on, if we can't afford this one,
                # we can't afford any others either, so we stop trying to build more units
                break
            else:
                # The build was successful, so we mark that something changed
                # and record the actions
                for buildAction in buildActions:
                    allActions.append((buildAction, province))
                changed = True
        else:
            # No valid tile to build on was found
            break

        # Recompute frontier tiles and hostileFrontierTiles for the next iteration
        frontierTiles = getFrontierTiles(province)
        hostileFrontierTiles = [tile for tile in frontierTiles if tile.owner is not None and tile.owner != province]

        # Now we shall sort hostileFrontierTiles by attack priority (smaller is better),
        # so that we try to build on the highest priority tiles first.
        tilePriorityPairs = []
        for i in range(len(hostileFrontierTiles)):
            enemyTile = hostileFrontierTiles[i]
            priorityValue = _getTileTargetPriorityValue(enemyTile)
            tilePriorityPairs.append((priorityValue, enemyTile))

        # Sort the hostileFrontierTiles by priority value ascending
        tilePriorityPairs.sort(key=lambda x: x[0])
        hostileFrontierTiles = [pair[1] for pair in tilePriorityPairs]

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

    # In addition to avoiding our own units, and generally avoiding tiles in tilesToAvoid,
    # we also want to avoid all the tiles not under our control as well,
    # since we don't want to either cause an exception by trying to move onto an enemy tile
    # we can't attack, or accidentally make an attack we didn't intend to make.
    avoidedTileLambda = lambda tile: (tile.row, tile.col) in [(t.row, t.col) for t in tilesToAvoid] or tile.owner != province

    # If somehow targetTiles is still empty, there is nothing to move towards.
    # So we can just return.
    if len(targetTiles) == 0:
        return changed

    for tile, _ in movableUnitTiles:
        # We can now just delegate to a helper to find the first move towards the closest target tile,
        # avoiding tiles occupied by our own units.
        destinationTile = getMoveTowardsTargetTileAvoidingGivenTiles(tile, targetTiles, avoidedTileLambda, scenario)

        # This could be None, meaning there is no valid path to any target tile.
        if destinationTile:
            moveActions = scenario.moveUnit(tile.row, tile.col, destinationTile.row, destinationTile.col)
            
            for moveAction in moveActions:
                allActions.append((moveAction, province))
            # Apply the actions immediately to update the scenario state
            for moveAction in moveActions:
                scenario.applyAction(moveAction, province)

            changed = True

            # If a unit moved, we need to update tilesToAvoid to include the new tile
            # and remove the old tile since the unit that was there has moved away to the destination tile.
            tilesToAvoid.remove(tile)
            tilesToAvoid.add(destinationTile)

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
