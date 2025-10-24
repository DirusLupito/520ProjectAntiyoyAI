"""
Holds several common utility functions used across AI modules
such as a function for calculating the most optimal way to move a unit
to reach a target tile if the move must take multiple turns.
"""

from collections import deque

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
