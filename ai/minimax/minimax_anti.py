# MINIMAX ALGORITHM
#Mac Gagne

import math
from typing import List, Tuple

from ai.utils.commonAIUtilityFunctions import getAllMovableUnitTilesInProvince
from ai.utils.commonAIUtilityFunctions import getFrontierTiles
from game.Action import Action
from game.world.factions.Province import Province
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
from game.world.units.Unit import Unit


# Represents the basic type for what a player
# could do on a turn in the form of a sequence of 
# actions and their associated provinces.
ActionChain = List[Tuple[Action, Province]]

def playTurn(originalScenario, originalFaction):
    """
    Wrapper for compatibility with the rest of the codebase.
    Used a fixed search depth which can be easily modified here.

    Args:
        originalScenario: The current game Scenario object.
        originalFaction: The Faction object for which to play the turn.

    Returns:
        A list of (Action, province) tuples to be executed.
    """
    fixedSearchDepth = 1  # Modify this value to change the search depth
    return playTurnWithSearchDepth(originalScenario, originalFaction, fixedSearchDepth)

def playTurnWithSearchDepth(originalScenario, originalFaction, searchDepth):
    """
    Runs alpha-beta minimax search to plan moves 
    for the provided faction at the requested depth.

    Args:
        originalScenario: The current game Scenario object.
        originalFaction: The Faction object for which to play the turn.

    Returns:
        A list of (Action, province) tuples to be executed.
    """
    # We make sure that the provided search depth is valid.
    # If it isn't, we return no actions.
    evaluatedDepth = 0
    try:
        evaluatedDepth = max(0, int(searchDepth))
    except (TypeError, ValueError):
        evaluatedDepth = 0
    if evaluatedDepth <= 0:
        return []

    # We will clone the original scenario
    # so that way we can simulate different action sequences
    # and make turns without affecting the original scenario.
    scenarioCloner = originalScenario.clone()
    planningScenario = scenarioCloner.getScenarioClone()
    planningFaction = scenarioCloner.factionMap.get(originalFaction)
    if planningFaction is None:
        return []

    # alphaBetaSearch performs the actual minimax search
    # If nothing is found, we return no actions.
    _, chosenSequence = alphaBetaSearch(planningScenario, planningFaction, evaluatedDepth, -math.inf, math.inf)
    if not chosenSequence:
        return []

    # If we did find a sequence, we need to translate it
    # back to the original scenario's objects (since any and all actions
    # made in the context of a cloned scenario use cloned objects).
    translateSequence = buildSequenceTranslator(originalScenario, scenarioCloner)
    return translateSequence(chosenSequence)


def alphaBetaSearch(planningScenario, maximizerFaction, remainingDepth, alphaValue, betaValue):
    """
    Performs alpha-beta search rooted at the provided scenario.
    Args:
        planningScenario: The Scenario object representing the current planning state.
        maximizerFaction: The Faction object representing the AI faction we are optimizing for.
        remainingDepth: The number of plies remaining to search.
        alphaValue: The current alpha value for pruning.
        betaValue: The current beta value for pruning.
        
    Returns:
        A tuple containing the evaluation score and the best sequence of actions.
    """

    # Base case: if we have reached the maximum search depth
    # or if the scenario is in a terminal state, we evaluate the board.
    if remainingDepth <= 0 or isTerminalState(planningScenario):
        return boardEvaluation(planningScenario, maximizerFaction), []

    # Recursive case: explore possible action sequences
    actingFaction = planningScenario.getFactionToPlay()
    if actingFaction is None:
        return boardEvaluation(planningScenario, maximizerFaction), []

    # Contains the best sequence of actions found at this level.
    # Could be used to get the returned sequence of actions that the player should take.
    bestSequence: ActionChain = []

    # If playing faction is the maximizer, we try to maximize the score.
    if actingFaction == maximizerFaction:
        bestValue = -math.inf
        for sequence, branchScenario, mappedMaximizer in generateTurnBranches(planningScenario, maximizerFaction):
            # Advance the cloned scenario to the next faction before exploring deeper plies,
            # since each level of recursion represents a full turn by a faction different from the last 
            # (unless somehow the game only has one faction left).
            branchScenario.advanceTurn()
            branchValue, _ = alphaBetaSearch(branchScenario, mappedMaximizer, remainingDepth - 1, alphaValue, betaValue)
            if branchValue > bestValue:
                bestValue = branchValue
                bestSequence = list(sequence)

            # Pruning out branches that cannot improve the outcome
            alphaValue = max(alphaValue, bestValue)
            if alphaValue >= betaValue:
                break

        return bestValue, bestSequence

    # We basically assume that all the opponents want to
    # minimize our score, rather than trying to maximize their own.
    worstValue = math.inf
    for sequence, branchScenario, mappedMaximizer in generateTurnBranches(planningScenario, maximizerFaction):
        # Even opponents need to end their turn on their branch clone before evaluation.
        branchScenario.advanceTurn()
        branchValue, _ = alphaBetaSearch(branchScenario, mappedMaximizer, remainingDepth - 1, alphaValue, betaValue)
        if branchValue < worstValue:
            worstValue = branchValue

        # Pruning out branches that cannot improve the outcome
        betaValue = min(betaValue, worstValue)
        if betaValue <= alphaValue:
            break

    return worstValue, []


def generateTurnBranches(planningScenario, maximizerFaction):
    """
    Enumerates all permutations of actions for the current faction.
    Used to get all the branches from the current node in the minimax ``tree''.
    We yield each branch as we generate it to avoid storing them all in memory at once.
    This is done using depth-first traversal.
    Consider the size taken up if we actually stored all branches in memory at once.
    With 10 units that we might move in any order, and which may have around 6^4 possible moves each,
    we could have around (6^4)^10 = 6^40 > 2^80 possible branches. Even a simple indexing of these
    actions would not fit in a single long integer.
    
    Args:
        planningScenario: The Scenario object representing the current planning state.
        maximizerFaction: The Faction object representing the AI faction we are optimizing for.
        
    Yields:
        Tuples of (action sequence, scenario clone after actions, mapped maximizer faction).
    """
    sequence: ActionChain = []

    def depthFirstEnumerate():
        actingFaction = planningScenario.getFactionToPlay()
        # Clone the current planning state so each yielded branch is isolated.
        # We don't want planning in one independent branch to affect another.
        branchCloner = planningScenario.clone()
        branchScenario = branchCloner.getScenarioClone()
        mappedMaximizer = branchCloner.factionMap.get(maximizerFaction, maximizerFaction)
        
        # Yield the current sequence as a valid branch.
        # This represents the case where the faction ends their turn here
        # without taking any further actions.
        yield list(sequence), branchScenario, mappedMaximizer

        # Otherwise, we try to extend the sequence with more actions
        # by recursively exploring all single-step actions.
        # collectSingleStepActions gets all possible individual actions
        # the faction could take at this point.
        for actionChain in collectSingleStepActions(planningScenario):
            # We apply the action chain to the planning scenario
            # so that we can explore further actions from this new state.
            applyActionChain(planningScenario, actionChain)
            # We also extend the current sequence with the new actions.
            sequence.extend(actionChain)
            
            # We recursively explore further actions from this new state.
            yield from depthFirstEnumerate()
            
            # After exploring, we need to revert the scenario
            # and the sequence back to the previous state
            # so we can try other action chains.
            for _ in actionChain:
                sequence.pop()
            revertActionChain(planningScenario, actionChain)

    # Start the depth-first enumeration of action sequences
    # (initial call to the recursive function).
    yield from depthFirstEnumerate()


def collectSingleStepActions(planningScenario):
    """
    Collects all individual move or build options for the faction to act on next.
    Will go through every province owned by the faction and gather every possible
    single-step action (moving a unit or building a new unit are assumed to be
    the only single-step actions).
    
    Args:
        planningScenario: The Scenario object representing the current planning state.
        
    Returns:
        A list of action chains, each representing a single-step action.
    """
    
    # List to hold all possible single-step action chains.
    actions: List[ActionChain] = []
    
    # Who is the faction currently playing at this simulated turn?
    actingFaction = planningScenario.getFactionToPlay()
    if actingFaction is None:
        return actions

    # We go through every province owned by the faction
    # and figure out everything each individual province can do.
    # Since we're only doing single-step actions, we don't
    # really need to worry about merges.
    
    # Also, since we aren't applying any actions yet, the provinces
    # will stay in the same state, allowing us to safely iterate over them
    # and generate actions for modifying them, without worrying about
    # reverting any changes.
    for province in list(actingFaction.provinces):
        # getattr is safer than province.active directly,
        # since the latter could raise an exception if province is None.
        if province is None or not getattr(province, "active", False):
            continue

        # First, we gather all movable units in the province
        # and see where they can go.
        movableTiles = getAllMovableUnitTilesInProvince(province)
        for tile, originProvince in movableTiles:
            # getAllTilesWithinMovementRangeFiltered could raise ValueError
            # if somehow tile is out of bounds. Should be impossible here,
            # but just in case, we catch and skip.
            try:
                destinations = planningScenario.getAllTilesWithinMovementRangeFiltered(tile.row, tile.col)
            except ValueError:
                continue
            
            for targetRow, targetCol in destinations:
                # Likewise, moveUnit could raise ValueError
                # if the target tile is invalid. We catch and skip.
                try:
                    moveActions = planningScenario.moveUnit(tile.row, tile.col, targetRow, targetCol)
                except ValueError:
                    continue
                
                # If we actually made any valid move actions, we add them
                # to our list of possible single-step action chains.
                if moveActions:
                    actions.append([(action, originProvince) for action in moveActions])

        # The only place that a province can build units is on its frontier tiles,
        # and on tiles that are part of the province.
        # Thus we only consider those tiles for building.
        potentialBuildTiles = list(province.tiles)
        frontierTiles = getFrontierTiles(province)
        potentialBuildTiles.extend(frontierTiles)
        for tile in potentialBuildTiles:
            
            # Like before, we catch ValueErrors from these methods
            # just in case something unexpected happens.
            try:
                buildableUnits = planningScenario.getBuildableUnitsOnTile(tile.row, tile.col, province)
            except ValueError:
                continue
            
            for unitType in buildableUnits:
                try:
                    buildActions = planningScenario.buildUnitOnTile(tile.row, tile.col, unitType, province)
                except ValueError:
                    continue
                
                # If we actually made any valid build actions, we add them
                # to our list of possible single-step action chains.
                if buildActions:
                    actions.append([(action, province) for action in buildActions])

    return actions


def applyActionChain(planningScenario, actionChain):
    """
    Applies every action in the chain to the scenario for simulation.
    
    Args:
        planningScenario: The Scenario object representing the current planning state.
        actionChain: The list of (Action, province) tuples to apply.
    """
    for action, province in actionChain:
        planningScenario.applyAction(action, province)


def revertActionChain(planningScenario, actionChain):
    """
    Reverts the provided action chain in reverse order to restore
    the given planning scenario to its previous state before the actions were applied.
    
    Args:
        planningScenario: The Scenario object representing the current planning state.
        actionChain: The list of (Action, province) tuples to revert.
    """
    for action, province in reversed(actionChain):
        planningScenario.applyAction(action.invert(), province)


def boardEvaluation(planningScenario, maximizerFaction):
    """
    Scores the scenario at the current state from the perspective of the maximizer faction.
    Called in the terminal nodes of the minimax search.
    
    This evaluation function computes the ratio of the maximizer faction's income
    to the total income of all factions. This encourages the AI to not only maximize its own income
    but also to make the opponents weaker. It also doesn't take into account unit upkeep costs,
    so that building an army is not penalized.
    
    Args:
        planningScenario: The Scenario object representing the current planning state.    
        maximizerFaction: The faction for which the score is being calculated.
    """
    # maximizerIncome / totalIncome
    totalIncome = 0
    maximizerIncome = 0
    
    # We compute income for each faction
    # using the formula defined in calculateFactionIncome.
    for faction in planningScenario.factions:
        factionIncome = calculateFactionIncome(faction)
        totalIncome += factionIncome
        
        if faction == maximizerFaction:
            maximizerIncome = factionIncome
    
    # Should not be possible to have zero total income
    # unless the game is over, but just in case we want
    # to avoid division by zero.
    if totalIncome <= 0:
        return 0.0
    
    return maximizerIncome / totalIncome


def calculateFactionIncome(faction):
    """
    Computes tile-based income including farms for a faction.
    We use the formula: income = numTiles + 4 * numFarms,
    since each controlled tile provides 1 income,
    and each farm unit provides an additional 4 income.
    
    We also subtract out tree tiles, since a tile with a tree
    does not provide income.
    
    Inactive provinces do not contribute to income either.
    
    Args:
        faction: The Faction object for which to calculate income.
        
    Returns:
        int: The calculated income for the faction.
    """
    tileCount = 0
    farmCount = 0
    # getattr is safer than faction.provinces or province.tiles, or... etc directly,
    # since the latter could raise an exception if our objects are None.
    # We first iterate over every province owned by the faction.
    for province in getattr(faction, "provinces", []):
        # Invalid provinces do not contribute to income.
        if province is None or not getattr(province, "active", False):
            continue
        
        # Within each valid province, we count tiles and farms,
        # and subtract out tree tiles.
        for tile in getattr(province, "tiles", []):
            if tile is None:
                continue
            
            tileCount += 1
            if tile.unit is not None and tile.unit.unitType == "farm":
                farmCount += 1
                
            if tile.unit is not None and tile.unit.unitType == "tree":
                tileCount -= 1  # Trees negate the income from the tile
                
    return tileCount + (4 * farmCount)


def isTerminalState(planningScenario):
    """
    Detects whether the scenario is in a terminal end-game condition.
    A terminal state is defined as having only one faction with active territory remaining.
    
    Args:
        planningScenario: The Scenario object representing the current planning state.
        
    Returns:
        bool: True if the scenario is in a terminal state, False otherwise.
    """
    # Initially we assume no factions have territory
    # until proven otherwise.
    activeFactionCount = 0
    
    # We go through every faction object and
    # see who's still alive and kicking.
    for faction in planningScenario.factions:
        
        hasTerritory = False
        
        # If a faction has at least one active province
        # with tiles, we consider them to still have territory.
        for province in getattr(faction, "provinces", []):
            if province and getattr(province, "active", False) and province.tiles:
                hasTerritory = True
                break
            
        if hasTerritory:
            activeFactionCount += 1
            
            # We can short-circuit here since
            # more than one active faction means
            # we are not in a terminal state.
            if activeFactionCount > 1:
                return False
            
    return True


def buildSequenceTranslator(originalScenario, scenarioCloner):
    """
    Creates a mapping function that moves actions from the clone back to the original scenario.
    This allows us to generate actions in the cloned scenario context, then translate them
    back to the original scenario context for execution.
    
    Args:
        originalScenario: The original Scenario object before cloning.
        scenarioCloner: The object responsible for cloning the scenario.
        
    Returns:
        A function that takes an action sequence in the cloned context
        and translates it back to the original scenario context.
    """
    # These maps define bijective mappings from cloned objects
    # back to their original counterparts.
    factionReverseMap = {clone: original for original, clone in scenarioCloner.factionMap.items()}
    provinceReverseMap = {clone: original for original, clone in scenarioCloner.provinceMap.items()}
    tileReverseMap = {clone: original for original, clone in scenarioCloner.tileMap.items()}
    unitReverseMap = {clone: original for original, clone in scenarioCloner.unitMap.items()}

    # We also keep track of created provinces and units
    # during translation to avoid duplicating them.
    createdProvinceMap = {}
    createdUnitMap = {}

    # Translates a faction from the cloned context back to the original.
    def translateFaction(factionObj):
        if factionObj is None:
            return None
        
        return factionReverseMap.get(factionObj, factionObj)

    # Translates a tile from the cloned context back to the original.
    def translateTile(tileObj):
        if tileObj is None:
            return None
        
        # We first try to map the tile using the reverse map.
        if tileObj in tileReverseMap:
            return tileReverseMap[tileObj]
        
        # Otherwise, all tiles should be locatable by their coordinates,
        # assuming nothing crazy happened during cloning and we wound
        # up with a bigger or smaller map.
        if hasattr(tileObj, "row") and hasattr(tileObj, "col"):
            if 0 <= tileObj.row < len(originalScenario.mapData) and 0 <= tileObj.col < len(originalScenario.mapData[tileObj.row]):
                return originalScenario.mapData[tileObj.row][tileObj.col]
            
        return tileObj

    # Translates a province from the cloned context back to the original.
    def translateProvince(provinceObj):
        if provinceObj is None:
            return None
        
        # First try to map using the reverse map.
        if provinceObj in provinceReverseMap:
            return provinceReverseMap[provinceObj]
        
        # Then check if we already created this province during translation.
        if provinceObj in createdProvinceMap:
            return createdProvinceMap[provinceObj]
        
        # Otherwise, we need to create a new province object
        # by translating its tiles and faction.
        
        # We first try to translate the owning faction,
        # and if that fails, we just return the original province object.
        factionObj = translateFaction(getattr(provinceObj, "faction", None))
        if factionObj is None:
            return provinceObj
        
        # Now we construct the new province in the original context
        # by translating its tiles and then transferring over the resources.
        translatedTiles = [translateTile(tile) for tile in getattr(provinceObj, "tiles", [])]
        resources = getattr(provinceObj, "resources", 0)
        
        # We're ready to create the new province now that we have the tile object clones
        # translated back to the original scenario.
        newProvince = Province(tiles=list(translatedTiles), resources=resources, faction=factionObj)
        newProvince.active = getattr(provinceObj, "active", False)
        
        # We track this created province to avoid duplicating it later.
        createdProvinceMap[provinceObj] = newProvince
        return newProvince

    # Translates a unit from the cloned context back to the original.
    def translateUnit(unitObj):
        # Like with other translators, we first check for None,
        # then try to use the reverse map, then check created units,
        # and if all else fails, we create a new unit in the original context.
        if unitObj is None:
            return None
        
        if unitObj in unitReverseMap:
            return unitReverseMap[unitObj]
        
        if unitObj in createdUnitMap:
            return createdUnitMap[unitObj]
        
        ownerFaction = translateFaction(getattr(unitObj, "owner", None))
        
        # We use the dedicated constructors for known unit types.
        # Currently this covers all known unit subclasses,
        # and in the default case we create a generic Unit.
        if isinstance(unitObj, Soldier):
            newUnit = Soldier(tier=getattr(unitObj, "tier", 1), owner=ownerFaction)
        elif isinstance(unitObj, Structure):
            newUnit = Structure(structureType=unitObj.unitType, owner=ownerFaction)
        elif isinstance(unitObj, Tree):
            newUnit = Tree(isGravestone=(unitObj.unitType == "gravestone"), owner=ownerFaction)
        else:
            newUnit = Unit(
                unitType=getattr(unitObj, "unitType", None),
                attackPower=getattr(unitObj, "attackPower", 0),
                defensePower=getattr(unitObj, "defensePower", 0),
                upkeep=getattr(unitObj, "upkeep", 0),
                cost=getattr(unitObj, "cost", 0),
                canMove=getattr(unitObj, "canMove", False),
                owner=ownerFaction
            )
        # We specifically make sure to copy over the canMove
        # attribute, since it may be false, but the constructor
        # would default it to true.
        newUnit.canMove = getattr(unitObj, "canMove", newUnit.canMove)
        
        # We track this created unit to avoid duplicating it later.
        createdUnitMap[unitObj] = newUnit
        return newUnit

    # Translates a hex state dictionary from the cloned context back to the original.
    # Helper for translating hex states in action data.
    def translateHexState(stateDict):
        if stateDict is None:
            return {}
        
        translated = {}
        # For every key-value pair, we translate units and owners specifically,
        # while leaving other data unchanged, since those are the only
        # complex objects that need to be translated in order to avoid reference issues.
        for key, value in stateDict.items():
            if key == "unit":
                translated[key] = translateUnit(value)
            elif key == "owner":
                translated[key] = translateProvince(value)
            else:
                translated[key] = value
                
        return translated

    # Translates an action from the cloned context back to the original.
    def translateAction(actionObj):
        # Currently we handle every known action type specifically,
        # and for unknown action types we do a generic translation
        # using common fields from previously handled action types.
        # In each case, we translate any complex objects
        # that need to be mapped back to the original context.
        if actionObj.actionType == "moveUnit":
            newData = {
                "initialHexCoordinates": actionObj.data["initialHexCoordinates"],
                "finalHexCoordinates": actionObj.data["finalHexCoordinates"],
                "previousInitialHexState": translateHexState(actionObj.data["previousInitialHexState"]),
                "previousFinalHexState": translateHexState(actionObj.data["previousFinalHexState"]),
                "resultantInitialHexState": translateHexState(actionObj.data["resultantInitialHexState"]),
                "resultantFinalHexState": translateHexState(actionObj.data["resultantFinalHexState"]),
                "unitMoved": translateUnit(actionObj.data.get("unitMoved")),
                "incomeFromMove": actionObj.data.get("incomeFromMove", 0)
            }
        elif actionObj.actionType == "tileChange":
            newData = {
                "hexCoordinates": actionObj.data["hexCoordinates"],
                "newTileState": translateHexState(actionObj.data["newTileState"]),
                "previousTileState": translateHexState(actionObj.data["previousTileState"]),
                "costOfAction": actionObj.data.get("costOfAction", 0)
            }
        elif actionObj.actionType == "provinceCreate":
            newData = {
                "faction": translateFaction(actionObj.data["faction"]),
                "province": translateProvince(actionObj.data["province"])
            }
            if "initialTiles" in actionObj.data:
                newData["initialTiles"] = [translateTile(tile) for tile in actionObj.data["initialTiles"]]
        elif actionObj.actionType == "provinceDelete":
            newData = {
                "faction": translateFaction(actionObj.data["faction"]),
                "province": translateProvince(actionObj.data["province"])
            }
            if "provinceState" in actionObj.data:
                provinceState = actionObj.data["provinceState"]
                newData["provinceState"] = {
                    "tiles": [translateTile(tile) for tile in provinceState.get("tiles", [])],
                    "resources": provinceState.get("resources", 0),
                    "active": provinceState.get("active", False)
                }
        elif actionObj.actionType == "provinceResourceChange":
            newData = {
                "province": translateProvince(actionObj.data["province"]),
                "previousResources": actionObj.data.get("previousResources", 0),
                "newResources": actionObj.data.get("newResources", 0)
            }
        elif actionObj.actionType == "provinceActivationChange":
            newData = {
                "province": translateProvince(actionObj.data["province"]),
                "previousActiveState": actionObj.data.get("previousActiveState", False),
                "newActiveState": actionObj.data.get("newActiveState", False)
            }
        else:
            # Generic translation for unknown action types.
            # Hopefully shouldn't be called ever.
            print(f"Warning: Translating unknown action type '{actionObj.actionType}' generically.")
            newData = {}
            for key, value in actionObj.data.items():
                if key == "province":
                    newData[key] = translateProvince(value)
                elif key == "faction":
                    newData[key] = translateFaction(value)
                elif key == "unit":
                    newData[key] = translateUnit(value)
                elif key == "tiles" and isinstance(value, list):
                    newData[key] = [translateTile(tile) for tile in value]
                else:
                    newData[key] = value
                    
        return Action(actionObj.actionType, newData, actionObj.isDirectConsequenceOfAnotherAction)

    # Translates an entire action sequence from the cloned context back to the original.
    # We can use all our other helpers to translate the detailed components.
    def translateSequence(actionSequence: ActionChain):
        mappedSequence: ActionChain = []
        # The ordering of actions matters, but should be the same
        # in both the cloned and original contexts.
        for action, province in actionSequence:
            mappedSequence.append((translateAction(action), translateProvince(province)))
            
        return mappedSequence

    return translateSequence
