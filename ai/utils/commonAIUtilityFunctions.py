"""
Holds several common utility functions used across AI modules
such as a function for calculating the most optimal way to move a unit
to reach a target tile if the move must take multiple turns.
"""

from collections import deque
from math import ceil

def checkTimeToBankruptProvince(province):
    """
    This function returns the number of turns it would take
    for a province to have 0 or less resources assuming no new resources are acquired 
    and the upkeep formula for the province remains the same (so no units die
    or are built, no farms are built, etc).
    If province.computeIncome() return a value >= 0, then this function will return None,
    since the province will never go bankrupt under those conditions. 
    Otherwise, if province.computeIncome() returns a negative value, 
    then this function will return the number of turns it would take for the 
    income times the number of turns plus the current resources to be less than or equal to 0.
    For instance, if the province's current resources are 5 and its income is -200, 
    then the function will return 1, since after 1 turn the province would have 
    5 + (-200 * 1) = -195.
    
    This function can be used after an action is applied to a province
    to check if that action would cause the province to go bankrupt in the next turn or in a few turns,
    which can be useful for determining whether or not to perform that action in the first place.
    
    Args:
        province: The Province object to check for bankruptcy.
        
    Returns:
        An integer representing the number of turns until the province goes bankrupt, 
        or None if it never does.
    """
    income = province.computeIncome()
    
    # If a province has 0 resources and 0 income this is a special case where the province 
    # is essentially already bankrupt, so we return 0 to indicate that whatever action was
    # taken to get the province to this state has resulted in it being bankrupt immediately.
    if income == 0 and province.resources <= 0:
        return 0
    
    if income >= 0:
        return None  # Province will never go bankrupt

    currentResources = province.resources
    # Calculate the number of turns until resources are <= 0
    # We want to find the smallest integer n such that:
    # currentResources + income * n <= 0
    # Rearranging gives:
    # income * n <= -currentResources
    # n >= -currentResources / income
    # Since income is negative, -currentResources / income will be positive.
    turns = ceil(-currentResources / income) 

    return turns

def isEnemyTile(tile, faction):
    """
    Tests if the tile is controlled by a faction other than the provided one.

    Args:
        tile: The HexTile to check.
        faction: The Faction to compare against.

    Returns:
        True if the tile is controlled by a different faction than the specified one, False otherwise.
    """
    return tile.owner is not None and tile.owner.faction != faction


def getReachableTilesAsObjects(scenario, movementCoordinates):
    """
    Converts a list of (int, int) movement coordinates into a list of HexTile objects.
    Interprets the coordinates as (row, col) pairs.
    Usually used with scenario.getAllTilesWithinMovementRangeFiltered() or scenario.getAllTilesWithinMovementRange()

    Args:
        scenario: The current game Scenario object.
        movementCoordinates: A list of (row, col) tuples representing tile coordinates.

    Returns:
        A list of HexTile objects corresponding to the provided coordinates.
    """
    tiles = []
    for row, col in movementCoordinates:
        tiles.append(scenario.mapData[row][col])
    return tiles

def findPathToClosestTile(startTile, targetTiles):
    """
    Finds the shortest path from a start tile to any of the target tiles using BFS.
    This is a BFS implementation that explores the grid layer by layer
    from the starting tile. It keeps track of the path taken to reach each tile.
    When it first encounters a tile that is in the set of target tiles,
    it returns the path to that tile, which is guaranteed to be one of the shortest.
    This function does NOT account for shorter paths that may exist in terms
    of turns, as it does not consider how a unit can move across multiple tiles
    claimed by its owner in a single turn, while it can only traverse one tile per turn
    when moving through neutral or enemy territory.

    Args:
        startTile: The HexTile to start the search from.
        targetTiles: A set of HexTiles to search for.

    Returns:
        A list of HexTile objects representing the path, or None if no path is found.
    """
    if not targetTiles:
        return None

    # The queue will store tuples of (tile, pathToTile)
    queue = deque([(startTile, [startTile])])
    visited = {startTile}

    # If the starting tile is already a target, we're done.
    if startTile in targetTiles:
        return [startTile]

    while queue:
        currentTile, path = queue.popleft()

        for neighbor in currentTile.neighbors:
            if neighbor and not neighbor.isWater and neighbor not in visited:
                newPath = path + [neighbor]
                # If we found a target, return the path immediately.
                if neighbor in targetTiles:
                    return newPath
                
                visited.add(neighbor)
                queue.append((neighbor, newPath))

    return None # No path found

def findPathToClosestTileAvoidingGivenTiles(startTile, targetTiles, avoidedTiles):
    """
    Similar to findPathToClosestTile, but ensures no tiles in the path
    are in the avoidedTiles set.

    args:
        startTile: The HexTile to start the search from.
        targetTiles: A set of HexTiles to search for.
        avoidedTiles: A set of HexTiles to avoid in the path.

    Returns:    
        A list of HexTile objects representing the path, or None if no path is found.
    """
    if not targetTiles:
        return None

    # The queue will store tuples of (tile, pathToTile)
    queue = deque([(startTile, [startTile])])
    visited = {startTile}

    # If the starting tile is already a target, we're done.
    if startTile in targetTiles and startTile not in avoidedTiles:
        return [startTile]

    while queue:
        currentTile, path = queue.popleft()

        for neighbor in currentTile.neighbors:
            if (neighbor and not neighbor.isWater and 
                neighbor not in visited and 
                neighbor not in avoidedTiles):
                
                newPath = path + [neighbor]
                # If we found a target, return the path immediately.
                if neighbor in targetTiles:
                    return newPath
                
                visited.add(neighbor)
                queue.append((neighbor, newPath))

    return None # No path found

def getAllUncontrolledTiles(scenario, faction):
    """
    Retrieves all tiles on the map that are either unclaimed or claimed by
    factions other than the specified faction.

    Args:
        scenario: The current game Scenario object.
        faction: The Faction object for which to find uncontrolled tiles.

    Returns:
        A list of HexTile objects that are uncontrolled by the specified faction.
    """
    uncontrolledTiles = [
        tile for row in scenario.mapData for tile in row 
        if not tile.isWater and (tile.owner is None or tile.owner.faction != faction)
    ]
    return uncontrolledTiles

def getAllMovableUnitTilesInProvince(province):
    """
    Retrieves all tiles containing movable soldier units within a given province.

    Args:
        province: The Province object to search for movable units.

    Returns:
        A list of tuples (tile, province) where tile contains a movable soldier unit.
    """
    movableUnitTiles = []
    for tile in province.tiles:
        if tile.unit and tile.unit.canMove and tile.unit.unitType.startswith("soldier"):
            movableUnitTiles.append((tile, province))
    return movableUnitTiles

def getFrontierTiles(province):
    """
    Retrieves all frontier tiles adjacent to the given province.
    Frontier tiles are defined as unclaimed tiles or tiles claimed by
    other factions that are adjacent to the province's tiles
    which are not water tiles.

    Args:
        province: The Province object to find frontier tiles for.

    Returns:
        A set of HexTile objects that are frontier tiles.
    """
    frontierTiles = {
        neighbor for tile in province.tiles 
        for neighbor in tile.neighbors 
        if neighbor and not neighbor.isWater 
        and (neighbor.owner is None or neighbor.owner.faction != province.faction)
    }
    return frontierTiles

def getEnemyTilesInRangeOfTile(scenario, tile, province):
    """
    Retrieves all enemy tiles within the one turn movement range of the given tile.

    Args:
        scenario: The current game Scenario object.
        tile: The HexTile to check from.
        province: The Province object to determine enemy factions.

    Returns:
        A list of HexTile objects that are enemy tiles within range.
    """
    # Let's first figure out all the tiles within the movement range of the tile
    movementRangeTilesCoords = scenario.getAllTilesWithinMovementRange(tile.row, tile.col)

    # Now let's convert those coordinates to HexTile objects
    movementRangeTiles = getReachableTilesAsObjects(scenario, movementRangeTilesCoords)

    # Now we filter to only enemy tiles
    enemyTilesInRange = [tile for tile in movementRangeTiles if tile.owner and tile.owner.faction != province.faction]

    return enemyTilesInRange
    

def getTilesWhichUnitCanBeBuiltOn(scenario, province, unitType):
    """
    Retrieves all tiles within or bordering the given province
    where a unit of the specified type can be built.
    Delegates logic to getTilesWhichUnitCanBeBuiltOnGivenTiles

    Args:
        province: The Province object to search for buildable tiles.
        unitType: The type of unit to be built (e.g., "

    Returns:
        A list of HexTile objects where units of the specified type can be built.
    """
    # First we get all the tiles we want to check, that being
    # all tiles in the province and all frontier tiles
    candidateTiles = list(province.tiles) + list(getFrontierTiles(province))

    # Then we delegate to the more general function with our candidate tiles
    return getTilesWhichUnitCanBeBuiltOnGivenTiles(scenario, province, unitType, candidateTiles)

def getTilesWhichUnitCanBeBuiltOnGivenTiles(scenario, province, unitType, candidateTiles):
    """
    Retrieves all tiles from the candidateTiles list
    where a unit of the specified type can be built
    by the given province.

    Args:
        scenario: The current game Scenario object.
        province: The Province object to search for buildable tiles.
        unitType: The type of unit to be built (e.g., "soldierTier1").
        candidateTiles: A list of HexTile objects to check for buildability.

    Returns:
        A list of HexTile objects from candidateTiles where units of the specified type can be built.
    """
    buildableTiles = []
    for tile in candidateTiles:
        buildableTypes = scenario.getBuildableUnitsOnTile(tile.row, tile.col, province)
        if unitType in buildableTypes:
            buildableTiles.append(tile)

    return buildableTiles

def getTilesInProvinceWhichContainGivenUnitTypes(province, unitTypes):
    """
    Retrieves all tiles within the given province that contain a unit of the specified type.

    Args:
        province: The Province object to search for units.
        unitTypes: A list of unit types to search for.

    Returns:
        A list of HexTile objects that contain a unit of the specified type.
    """
    matchingTiles = []
    for tile in province.tiles:
        if tile.unit and tile.unit.unitType in unitTypes:
            matchingTiles.append(tile)
    return matchingTiles

def getDefenseRatingOfTile(tile):
    """
    Calculates a defense rating for a given tile based on the
    strongest unit either on or adjacent to that tile which
    belongs to the same province as the tile (includes None).

    Args:
        tile: The HexTile object to evaluate.
    Returns:
        An integer representing the defense rating of the tile.
    """
    defenseRating = 0

    # Check the unit on the tile itself
    if tile.unit and tile.unit.defensePower:
        defenseRating = max(defenseRating, tile.unit.defensePower)

    # Check neighboring tiles
    for neighbor in tile.neighbors:
        if neighbor and neighbor.owner == tile.owner:
            if neighbor.unit and neighbor.unit.defensePower:
                defenseRating = max(defenseRating, neighbor.unit.defensePower)

    return defenseRating

def getSubsetOfTilesWithMatchingDefenseRating(tiles, rating):
    """
    Filters a list of tiles to only those whose defense rating
    satisfies the given rating function.

    Args:
        tiles: A list of HexTile objects to filter.
        rating: A function (probably a lambda) that takes an integer defense rating
                and returns True if the tile should be included.

    Returns:
        A list of HexTile objects whose defense rating satisfies the rating function.
    """
    matchingTiles = []
    for tile in tiles:
        defenseRating = getDefenseRatingOfTile(tile)
        if rating(defenseRating):
            matchingTiles.append(tile)
    return matchingTiles
