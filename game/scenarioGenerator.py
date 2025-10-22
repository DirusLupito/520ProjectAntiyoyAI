from game.world.units.Structure import Structure
from game.world.HexTile import HexTile
from game.Scenario import Scenario
from game.world.factions.Province import Province
import random

def generateRandomScenario(dimension, targetNumberOfLandTiles, factions, initialProvinceSize, randomSeed=None):
    """
    Generates a random scenario with a contiguous island of land tiles divided among factions.

    Args:
        dimension: Size of the square grid (dimension x dimension)
        targetNumberOfLandTiles: Number of non-water tiles to create
        factions: List of Faction objects to include in the scenario
        initialProvinceSize: Number of tiles to assign to each province initially
        randomSeed: Optional seed for random number generator for reproducibility

    Returns:
        A new Scenario object with the generated map
    """
    # Validate inputs
    if len(factions) >= targetNumberOfLandTiles / 2:
        raise ValueError("Number of factions must be less than half the target number of land tiles")
    if targetNumberOfLandTiles > dimension * dimension:
        raise ValueError("Target number of land tiles must be less or equal to than the square of dimension")
    if len(factions) * initialProvinceSize > targetNumberOfLandTiles:
        raise ValueError("Not enough land tiles to allocate initial provinces for all factions")
    if initialProvinceSize < 2:
        raise ValueError("Initial province size must be at least 2")
    if randomSeed is not None:
        random.seed(randomSeed)

    # Create a grid of water tiles
    mapData = []
    for row in range(dimension):
        mapRow = []
        for col in range(dimension):
            # Create a water tile
            tile = HexTile(row, col, isWater=True)
            mapRow.append(tile)
        mapData.append(mapRow)

    # Set up neighbors for all tiles
    _setupHexNeighbors(mapData)

    # Generate a contiguous island
    landTiles = _generateContiguousIsland(mapData, targetNumberOfLandTiles)

    # Distribute land tiles among factions
    _distributeTilesToFactions(landTiles, factions, initialProvinceSize)

    # Create the scenario with the generated map
    scenario = Scenario("Random Generated Map", mapData, factions)

    return scenario

def _setupHexNeighbors(mapData):
    """
    Sets up the neighbor relationships for all tiles in the map.
    See the top comment near the init function for details on hex neighbor indexing.
    """
    dimension = len(mapData)
    for row in range(dimension):
        for col in range(dimension):
            tile = mapData[row][col]
            neighbors = [None] * 6  # Initialize with 6 None values

            # Determine neighbors based on even/odd column
            if col % 2 == 0:  # Even column
                # North: (row-1, col)
                if row > 0:
                    neighbors[0] = mapData[row-1][col]
                # Northeast: (row-1, col+1)
                if row > 0 and col < dimension - 1:
                    neighbors[1] = mapData[row-1][col+1]
                # Southeast: (row, col+1)
                if col < dimension - 1:
                    neighbors[2] = mapData[row][col+1]
                # South: (row+1, col)
                if row < dimension - 1:
                    neighbors[3] = mapData[row+1][col]
                # Southwest: (row, col-1)
                if col > 0:
                    neighbors[4] = mapData[row][col-1]
                # Northwest: (row-1, col-1)
                if row > 0 and col > 0:
                    neighbors[5] = mapData[row-1][col-1]
            else:  # Odd column
                # North: (row-1, col)
                if row > 0:
                    neighbors[0] = mapData[row-1][col]
                # Northeast: (row, col+1)
                if col < dimension - 1:
                    neighbors[1] = mapData[row][col+1]
                # Southeast: (row+1, col+1)
                if row < dimension - 1 and col < dimension - 1:
                    neighbors[2] = mapData[row+1][col+1]
                # South: (row+1, col)
                if row < dimension - 1:
                    neighbors[3] = mapData[row+1][col]
                # Southwest: (row+1, col-1)
                if row < dimension - 1 and col > 0:
                    neighbors[4] = mapData[row+1][col-1]
                # Northwest: (row, col-1)
                if col > 0:
                    neighbors[5] = mapData[row][col-1]

            tile.neighbors = neighbors

def _generateContiguousIsland(mapData, targetNumberOfLandTiles):
    """
    Generates a contiguous island of land tiles using a frontier-based growth algorithm.
    The general idea is as follows:
    1. Start with a random tile and convert it to land. We pick a tile near the center
       of the map to encourage better island shapes, but this is random.
    2. Maintain a frontier list of water tiles that are adjacent to at least one land tile.
    3. While we have not reached the target number of land tiles:
        a) Randomly select a tile from the frontier.
        b) Convert it to land.
        c) Add any of its water neighbors to the frontier if they are not already present.
    4. Return the list of land tiles created.
    
    Args:
        mapData: 2D list of HexTile objects initialized as water tiles
        targetNumberOfLandTiles: Number of land tiles to create

    Returns:
        List of HexTile objects that are land tiles
    """
    dimension = len(mapData)
    landTiles = []

    # Start with a random tile near the center for better island shape
    centerRow = dimension // 2
    centerCol = dimension // 2
    startRow = random.randint(centerRow - dimension//4, centerRow + dimension//4)
    startCol = random.randint(centerCol - dimension//4, centerCol + dimension//4)

    # Make sure it's within bounds
    startRow = max(0, min(startRow, dimension-1))
    startCol = max(0, min(startCol, dimension-1))

    startTile = mapData[startRow][startCol]
    startTile.isWater = False
    landTiles.append(startTile)

    # Keep track of the frontier - water tiles adjacent to at least one land tile
    frontier = []
    for neighbor in startTile.neighbors:
        if neighbor is not None and neighbor.isWater:
            frontier.append(neighbor)

    # Convert water tiles to land until we reach the target
    while len(landTiles) < targetNumberOfLandTiles and frontier:
        # Pick a random tile from the frontier
        index = random.randint(0, len(frontier)-1)
        tile = frontier.pop(index)

        # Convert to land
        tile.isWater = False
        landTiles.append(tile)

        # Add water neighbors to frontier
        for neighbor in tile.neighbors:
            if neighbor is not None and neighbor.isWater and neighbor not in frontier:
                frontier.append(neighbor)

    return landTiles

def _distributeTilesToFactions(landTiles, factions, initialProvinceSize):
    """
    Distributes land tiles among factions, ensuring each faction gets a contiguous province.
    The idea here is to:
    1. Pick a starting tile for each faction, spaced apart from each other.
    2. Create a province for each faction starting with just that tile.
    3. Maintain a frontier of available tiles adjacent to each province.
    4. Take turns expanding each province by adding random tiles from its frontier
       until all land tiles are assigned or until the provinces can no longer expand,
       or until each province reaches the initialProvinceSize.
    5. Finally, place capitals for each province.

    Args:
        landTiles: List of HexTile objects that are land tiles
        factions: List of Faction objects to distribute tiles among

    Returns:
        List of Province objects created for each faction
    """
    # Create a copy of landTiles we can modify
    availableTiles = set(landTiles)

    # Pick starting tiles for each faction - try to space them out
    startingTiles = _pickSpacedStartingTiles(landTiles, len(factions))
    for tile in startingTiles:
        availableTiles.remove(tile)

    # Create a province for each faction with just the starting tile
    provinces = []
    frontiers = []

    for i, faction in enumerate(factions):
        startTile = startingTiles[i]
        # Provinces start with 10 resources in random scenarios
        province = Province(tiles=[startTile], resources=10, faction=faction)
        startTile.owner = province
        provinces.append(province)
        faction.provinces = [province]

        # Add adjacent available tiles to frontier
        frontier = []
        for neighbor in startTile.neighbors:
            if neighbor in availableTiles:
                frontier.append(neighbor)
        frontiers.append(frontier)

    # Take turns adding tiles to each province until all tiles are assigned
    # or until all provinces reach initialProvinceSize
    while availableTiles and any(frontiers) and any(len(province.tiles) < initialProvinceSize for province in provinces):
        for i, province in enumerate(provinces):
            if not frontiers[i] or len(province.tiles) >= initialProvinceSize:
                continue  # Skip if this province has no more frontier or has reached initial size limit
            
            # Pick a random tile from the frontier
            if len(frontiers[i]) == 0:
                continue

            index = random.randint(0, len(frontiers[i])-1)
            tile = frontiers[i].pop(index)

            # Skip if tile is no longer available
            if tile not in availableTiles:
                continue

            # Add tile to province
            province.tiles.append(tile)
            tile.owner = province
            availableTiles.remove(tile)

            # Add new neighbors to frontier
            for neighbor in tile.neighbors:
                if neighbor in availableTiles and neighbor not in frontiers[i]:
                    frontiers[i].append(neighbor)

            # Break if no more tiles available
            if not availableTiles:
                break
            
    # Place capitals
    for province in provinces:
        # Make sure the province has at least 2 tiles to be active
        if len(province.tiles) >= 2:
            province.active = True
            # Use the existing placeCapital method to select a good tile and create the action
            capitalTile, _ = province.placeCapital(province.tiles)
            # Actually place the capital without using the action
            capitalTile.unit = Structure(structureType="capital", owner=province.faction)

    return provinces

def _pickSpacedStartingTiles(landTiles, numFactions):
    """
    Pick starting tiles for factions that are reasonably spaced apart.
    Uses a simple distance-based algorithm to maximize separation between faction starting points.
    Basically:
    1. Pick the first tile randomly.
    2. For each subsequent faction, pick the tile that maximizes the minimum distance
       to all previously chosen starting tiles.

    Args:
        landTiles: List of HexTile objects that are land tiles
        numFactions: Number of factions to pick starting tiles for

    Returns:
        List of HexTile objects chosen as starting tiles

    """
    if numFactions <= 0 or not landTiles:
        return []

    startingTiles = []

    # Pick the first tile randomly
    startingTiles.append(random.choice(landTiles))

    # For each remaining faction
    for _ in range(1, numFactions):
        maxMinDistance = -1
        bestTile = None

        # Try each remaining land tile
        for tile in landTiles:
            if tile in startingTiles:
                continue

            # Find minimum distance to any existing starting tile
            minDistance = float('inf')
            for startTile in startingTiles:
                # Calculate simple distance as just row + col difference
                # rather than hex distance for simplicity (will be imperfect)
                distance = abs(tile.row - startTile.row) + abs(tile.col - startTile.col)
                minDistance = min(minDistance, distance)

            # Keep track of the tile with the maximum minimum distance
            if minDistance > maxMinDistance:
                maxMinDistance = minDistance
                bestTile = tile

        startingTiles.append(bestTile)

    return startingTiles
