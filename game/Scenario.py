from game.Action import Action
from game.world.units import Unit
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
from collections import deque
from game.world.HexTile import HexTile
from game.world.factions.Province import Province

class Scenario:
    """
    Represents a game scenario with its settings and configurations.
    So far, only the base antiyoy game is implemented, with no
    Diplomacy or Fog of War or Slay rules. Victory conditions
    are also no implemented, with the game ending when one player
    is alone remaining.
    
    A scenario both represents a map that can be played/started
    and the current state of a game in progress.
    Scenarios understand whose turn it is, have datastructures
    for the underlying map with its HexTiles and Provinces
    and factions, and have methods for performing game actions.
    """
    def __init__(self, name, mapData=None, factions=None, indexOfFactionToPlay=0):
        # Name of the scenario. Could also be the description.
        # It's just a string, and only used for display purposes.
        self.name = name
        # mapData is a 2D array of HexTile objects representing the map.
        # We do a simple map between the 2D "rectangular" array and
        # the hexagonal grid by using offset coordinates.
        # So for example, consider the following 2 by 5 grid:
        # ASCII representation of hex grid:
        #     ___     ___     ___
        #    /0,0\___/0,2\___/0,4\
        #    \___/0,1\___/0,3\___/
        #    /1,0\___/1,2\___/1,4\
        #    \___/1,1\___/1,3\___/
        #        \___/   \___/
        #            
        # In this case, mapData[0][0] is hex tile (0,0),
        # mapData[0][1] is hex tile (0,1), and so on.
        # Basically, if we label columns of the hexagonal grid as "q" 
        # and row as "r", then the hex tile at (r, q) is stored in
        # mapData[r][q].
        # 
        # Due to how hexagons are arranged, rows may rise and fall a 
        # bit, but columns remain straight (see the diagram above).
        # Also note that if 0,1 were above 0,0 rather than below it,
        # the neighbor relationships would be different, 
        # so it's important to understand that we start at 0,0
        # with 0,0 being raised above 0,1.
        # 
        # With this in mind, we can realize that if we have
        # the i,j hex tile in mapData[i][j], and we want to find
        # its neighbors, we can do so as follows:
        # - If j is even (0, 2, 4, ...):
        #   - North:     (i-1, j)
        #   - Northeast: (i-1, j+1)
        #   - Southeast: (i, j+1)
        #   - South:     (i+1, j)
        #   - Southwest: (i, j-1)
        #   - Northwest: (i-1, j-1)
        # - If j is odd (1, 3, 5, ...):
        #   - North:     (i-1, j)
        #   - Northeast: (i, j+1)
        #   - Southeast: (i+1, j+1)
        #   - South:     (i+1, j)
        #   - Southwest: (i, j-1)
        #   - Northwest: (i-1, j)
        
        self.mapData = mapData if mapData is not None else []
        
        # List of Faction instances participating in the scenario.
        # The first faction to get a turn is at index indexOfFactionToPlay.
        # Or just 0 if indexOfFactionToPlay is out of range or unspecified.
        self.factions = factions if factions is not None else []
        self.indexOfFactionToPlay = indexOfFactionToPlay if 0 <= indexOfFactionToPlay < len(self.factions) else 0
        
    def getFactionToPlay(self):
        """Returns the Faction instance whose turn it is to play."""
        if 0 <= self.indexOfFactionToPlay < len(self.factions):
            return self.factions[self.indexOfFactionToPlay]
        return None
    
    def advanceTurn(self):
        """
        Updates the current faction to play and loops back to the first faction after the last one.
        Advances the turn to the next faction and returns all the actions needed to perform
        the various mutations of game state that occur at the start and end of a faction's turn.
        The returned list contains (Action, Province) tuples applied during the advance.
        """
        turnAdvanceActions = []
        if len(self.factions) == 0:
            return turnAdvanceActions

        currentFaction = self.getFactionToPlay()
        if currentFaction:
            for province in list(currentFaction.provinces):
                for action, provinceContext in province.updateAfterTurn():
                    self.applyAction(action, provinceContext)
                    turnAdvanceActions.append((action, provinceContext))

        self.indexOfFactionToPlay = (self.indexOfFactionToPlay + 1) % len(self.factions)
        currentFaction = self.getFactionToPlay()
        if currentFaction:
            for province in list(currentFaction.provinces):
                for action, provinceContext in province.updateBeforeTurn():
                    self.applyAction(action, provinceContext)
                    turnAdvanceActions.append((action, provinceContext))

        return turnAdvanceActions

    def displayMap(self):
        """
        Encapsulates displaying the current state of the map.
        Can be changed depending on how we want to visualize the map.
        """
        self.printMap()

    def printMap(self):
        """
        Alternative method to print the board.
        This version prints such that no two hexagons share an ASCII line.
        For example, this would represent a 2x3 grid:
            
           /‾‾‾‾‾‾‾\           /‾‾‾‾‾‾‾\
          /         \         /         \
          \         //‾‾‾‾‾‾‾\\         /
           \_______//         \\_______/
           /‾‾‾‾‾‾‾\\         //‾‾‾‾‾‾‾\
          /         \\_______//         \
          \         //‾‾‾‾‾‾‾\\         /
           \_______//         \\_______/
                    \         /
                     \_______/

        Uses an approach where first the string is formulated as a 2D array of characters,
        which is filled in by calculating where each hexagon / each hexagon's ASCII symbols
        should go, and then printing the resulting 2D array of characters.
        Used the nonstandard '‾' character to represent the top of hexagons.
        
        The inner part of each hexagon contains the coordinates of the hexagon
        and a detail string representing the tile's unit and owner.
        """
        if not self.mapData:
            print("Empty map")
            return
        
        # Determine dimensions of the character grid
        # Each hexagon is 11 characters wide and 4 characters tall
        # We also pad the grid with 4 spaces on the left
        # and 1 space on the bottom and 1 on the top
        print()
        numRows = len(self.mapData)
        numCols = max(len(row) for row in self.mapData) if numRows > 0 else 0
        gridWidth = numCols * 11 + 4
        gridHeight = numRows * 4 + 2
        charGrid = [[' ' for _ in range(gridWidth)] for _ in range(gridHeight)]
        # The color grid holds either empty strings or ANSI color codes for each character
        # in the charGrid, to color the printed output accordingly.
        colorGrid = [['' for _ in range(gridWidth)] for _ in range(gridHeight)]
        # Now that we have the character grid, fill it in with hexagons
        for r in range(numRows):
            for c in range(len(self.mapData[r])):
                # ASCII representation will depend on where the hexagon is located
                # We need to get the faction color for the owner of the hex tile,
                # or use \e[0;94m for water (blue), or no color for unowned land
                hexTile = self.mapData[r][c]
                charColorStr = ""
                if hexTile.owner is not None:
                    charColorStr = hexTile.owner.faction.getFactionColorString()
                elif hexTile.isWater:
                    charColorStr = "\033[94m"  # Blue for water
                # Now we can fill in the ASCII representation of the hexagon
                if c % 2 == 0:
                    topLeftX = c * 10 + 4
                    topLeftY = r * 4
                    charGrid[topLeftY][topLeftX + 1] = '/'
                    colorGrid[topLeftY][topLeftX + 1] = charColorStr
                    charGrid[topLeftY][topLeftX + 2] = '‾'
                    colorGrid[topLeftY][topLeftX + 2] = charColorStr
                    charGrid[topLeftY][topLeftX + 3] = '‾'
                    colorGrid[topLeftY][topLeftX + 3] = charColorStr
                    charGrid[topLeftY][topLeftX + 4] = '‾'
                    colorGrid[topLeftY][topLeftX + 4] = charColorStr
                    charGrid[topLeftY][topLeftX + 5] = '‾'
                    colorGrid[topLeftY][topLeftX + 5] = charColorStr
                    charGrid[topLeftY][topLeftX + 6] = '‾'
                    colorGrid[topLeftY][topLeftX + 6] = charColorStr
                    charGrid[topLeftY][topLeftX + 7] = '‾'
                    colorGrid[topLeftY][topLeftX + 7] = charColorStr
                    charGrid[topLeftY][topLeftX + 8] = '‾'
                    colorGrid[topLeftY][topLeftX + 8] = charColorStr
                    charGrid[topLeftY][topLeftX + 9] = '\\'
                    colorGrid[topLeftY][topLeftX + 9] = charColorStr
                    charGrid[topLeftY + 1][topLeftX] = '/'
                    colorGrid[topLeftY + 1][topLeftX] = charColorStr
                    charGrid[topLeftY + 1][topLeftX + 10] = '\\'
                    colorGrid[topLeftY + 1][topLeftX + 10] = charColorStr
                    charGrid[topLeftY + 2][topLeftX] = '\\'
                    colorGrid[topLeftY + 2][topLeftX] = charColorStr
                    charGrid[topLeftY + 2][topLeftX + 10] = '/'
                    colorGrid[topLeftY + 2][topLeftX + 10] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 1] = '\\'
                    colorGrid[topLeftY + 3][topLeftX + 1] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 2] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 2] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 3] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 3] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 4] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 4] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 5] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 5] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 6] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 6] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 7] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 7] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 8] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 8] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 9] = '/'
                    colorGrid[topLeftY + 3][topLeftX + 9] = charColorStr
                    # We fill the inside of the hexagon with the coordinates
                    # and a detail string giving info about the tile
                    coordStr = f"{r},{c}"
                    detailStr = ""
                    if hexTile.isWater:
                        detailStr = "~" * 9
                    else:
                        unitStr = hexTile.unit.unitType if hexTile.unit is not None else ""
                        ownerStr = hexTile.owner.faction.name[0] if hexTile.owner is not None else ""
                        # Format: first and last letter of unit type + first letter of owner color
                        # If unitStr is non-empty. Otherwise, leave that part blank.
                        # If ownerStr is empty, leave that part blank too.
                        if unitStr and ownerStr:
                            detailStr = f"{unitStr[0]}{unitStr[-1]}{ownerStr}"
                        elif unitStr:
                            detailStr = f"{unitStr[0]}{unitStr[-1]}"
                        elif ownerStr:
                            detailStr = f"{ownerStr}"
                        else:
                            detailStr = ""

                    # 9 spaces above are for the coordinates
                    # 9 spaces below are for the detail string
                    # We try to center both strings
                    # Odd length can be perfectly centered, even length
                    # is left-biased centered
                    # If the strings are too long, they overflow and overwrite parts of the hexagon,
                    # so we truncate them if needed
                    coordStr = coordStr[:9]
                    detailStr = detailStr[:9]
                    coordStartX = topLeftX + 1 + (9 - len(coordStr)) // 2
                    detailStartX = topLeftX + 1 + (9 - len(detailStr)) // 2
                    charGrid[topLeftY + 1][coordStartX:coordStartX + len(coordStr)] = list(coordStr)
                    charGrid[topLeftY + 2][detailStartX:detailStartX + len(detailStr)] = list(detailStr)
                    # The setting of the colorGrid is much easier, 
                    # we just mark these 9 + 9 = 18 characters with the color string
                    # Upper
                    for i in range(len(coordStr)):
                        colorGrid[topLeftY + 1][coordStartX + i] = charColorStr
                    # Lower
                    for i in range(len(detailStr)):
                        colorGrid[topLeftY + 2][detailStartX + i] = charColorStr
                else:
                    topLeftX = c * 10 + 4
                    topLeftY = r * 4 + 2
                    charGrid[topLeftY][topLeftX + 1] = '/'
                    colorGrid[topLeftY][topLeftX + 1] = charColorStr
                    charGrid[topLeftY][topLeftX + 2] = '‾'
                    colorGrid[topLeftY][topLeftX + 2] = charColorStr
                    charGrid[topLeftY][topLeftX + 3] = '‾'
                    colorGrid[topLeftY][topLeftX + 3] = charColorStr
                    charGrid[topLeftY][topLeftX + 4] = '‾'
                    colorGrid[topLeftY][topLeftX + 4] = charColorStr
                    charGrid[topLeftY][topLeftX + 5] = '‾'
                    colorGrid[topLeftY][topLeftX + 5] = charColorStr
                    charGrid[topLeftY][topLeftX + 6] = '‾'
                    colorGrid[topLeftY][topLeftX + 6] = charColorStr
                    charGrid[topLeftY][topLeftX + 7] = '‾'
                    colorGrid[topLeftY][topLeftX + 7] = charColorStr
                    charGrid[topLeftY][topLeftX + 8] = '‾'
                    colorGrid[topLeftY][topLeftX + 8] = charColorStr
                    charGrid[topLeftY][topLeftX + 9] = '\\'
                    colorGrid[topLeftY][topLeftX + 9] = charColorStr
                    charGrid[topLeftY + 1][topLeftX] = '/'
                    colorGrid[topLeftY + 1][topLeftX] = charColorStr
                    charGrid[topLeftY + 1][topLeftX + 10] = '\\'
                    colorGrid[topLeftY + 1][topLeftX + 10] = charColorStr
                    charGrid[topLeftY + 2][topLeftX] = '\\'
                    colorGrid[topLeftY + 2][topLeftX] = charColorStr
                    charGrid[topLeftY + 2][topLeftX + 10] = '/'
                    colorGrid[topLeftY + 2][topLeftX + 10] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 1] = '\\'
                    colorGrid[topLeftY + 3][topLeftX + 1] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 2] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 2] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 3] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 3] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 4] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 4] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 5] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 5] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 6] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 6] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 7] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 7] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 8] = '_'
                    colorGrid[topLeftY + 3][topLeftX + 8] = charColorStr
                    charGrid[topLeftY + 3][topLeftX + 9] = '/'
                    colorGrid[topLeftY + 3][topLeftX + 9] = charColorStr
                    # We fill the inside of the hexagon with the coordinates
                    # and a detail string giving info about the tile
                    coordStr = f"{r},{c}"
                    detailStr = ""
                    if hexTile.isWater:
                        detailStr = "~" * 9
                    else:
                        unitStr = hexTile.unit.unitType if hexTile.unit is not None else ""
                        ownerStr = hexTile.owner.faction.name[0] if hexTile.owner is not None else ""
                        # Format: first and last letter of unit type + first letter of owner color
                        # If unitStr is non-empty. Otherwise, leave that part blank.
                        # If ownerStr is empty, leave that part blank too.
                        if unitStr and ownerStr:
                            detailStr = f"{unitStr[0]}{unitStr[-1]}{ownerStr}"
                        elif unitStr:
                            detailStr = f"{unitStr[0]}{unitStr[-1]}"
                        elif ownerStr:
                            detailStr = f"{ownerStr}"
                        else:
                            detailStr = ""
                    # 9 spaces above are for the coordinates
                    # 9 spaces below are for the detail string
                    # We try to center both strings
                    # Odd length can be perfectly centered, even length
                    # is left-biased centered
                    # If the strings are too long, they overflow and overwrite parts of the hexagon,
                    # so we truncate them if needed
                    coordStr = coordStr[:9]
                    detailStr = detailStr[:9]
                    coordStartX = topLeftX + 1 + (9 - len(coordStr)) // 2
                    detailStartX = topLeftX + 1 + (9 - len(detailStr)) // 2
                    charGrid[topLeftY + 1][coordStartX:coordStartX + len(coordStr)] = list(coordStr)
                    charGrid[topLeftY + 2][detailStartX:detailStartX + len(detailStr)] = list(detailStr)
                    # The setting of the colorGrid is much easier, 
                    # we just mark these 9 + 9 = 18 characters with the color string
                    # Upper
                    for i in range(len(coordStr)):
                        colorGrid[topLeftY + 1][coordStartX + i] = charColorStr
                    # Lower
                    for i in range(len(detailStr)):
                        colorGrid[topLeftY + 2][detailStartX + i] = charColorStr
                        
        # Print the character grid
        resetCode = '\033[0m'
        for row in charGrid:
            # print("".join(row))
            for i in range(len(row)):
                char = row[i]
                colorStr = colorGrid[charGrid.index(row)][i]
                if colorStr:
                    print(f"{colorStr}{char}{resetCode}", end="")
                else:
                    print(char, end="")
            print(resetCode)

    def getAllTilesWithinMovementRange(self, startRow, startCol):
        """
        Returns a list of (row, col) tuples representing all hex tiles
        that a mobile unit at the given startRow and startCol could move to,
        provided no other units or structures block movement at the target tiles.

        Args:
            startRow: The row index of the starting hex tile.
            startCol: The column index of the starting hex tile.

        Returns:
            A list of (row, col) tuples representing all reachable hex tiles
            within movement range.
        """
        # Validate coordinates
        if not (0 <= startRow < len(self.mapData)) or not (0 <= startCol < len(self.mapData[startRow])):
            raise ValueError("Invalid start hex coordinates.")
        
        startTile = self.mapData[startRow][startCol]
        
        soldierProvince = startTile.owner
        movementRange = 4  # Maximum movement range for any mobile unit
        visited = set()
        validTiles = []

        # BFS queue: stores (currentRow, currentCol, distanceFromStart)
        queue = deque([(startRow, startCol, 0)])
        visited.add((startRow, startCol))

        while queue:
            currentRow, currentCol, distance = queue.popleft()

            # Add the current tile to the valid tiles list
            validTiles.append((currentRow, currentCol))

            # Stop expanding if we've reached the movement range limit,
            # 4 if the tile is controlled by the soldier's province,
            # or immediately if the tile is enemy-controlled or neutral.
            if distance >= movementRange or (self.mapData[currentRow][currentCol].owner != soldierProvince):
                continue

            # Get the current tile
            currentTile = self.mapData[currentRow][currentCol]

            # Iterate over neighbors
            for _, neighbor in enumerate(currentTile.neighbors):
                if neighbor is None or neighbor.isWater:  # Skip water tiles and out-of-bound neighbors
                    continue

                neighborRow, neighborCol = neighbor.row, neighbor.col

                # Skip already visited tiles
                if (neighborRow, neighborCol) in visited:
                    continue

                # Expand only neighbor tiles controlled by the soldier's province
                visited.add((neighborRow, neighborCol))
                queue.append((neighborRow, neighborCol, distance + 1))

        return validTiles

    def getAllTilesWithinMovementRangeFiltered(self, startRow, startCol):
        """
        Returns a list of (row, col) tuples representing all hex tiles
        that a soldier unit at the given startRow and startCol can move to.
        
        Soldiers units have essentially 3 movement rules:
        1. They cannot move onto water tiles.
        2. They can only move to tiles controlled by their own province
           if those tiles are only 4 hex neighbors away or less.
           That is, only 4 edges away in terms of hex adjacency
           (can be easily checked with BFS/DFS). 
           (Also those tiles can't have other units on them unless it's a tree
           or you're trying to merge certain type of soldiers, but that's handled elsewhere.)
        3. They can move onto enemy-controlled tiles or neutral tiles
           if those tiles satisfy
           a) They are adjacent to a tile controlled by the soldier's province
              which is at most 3 hex neighbors away from the soldier's starting tile.
           b) Neither the target tile nor any of the neighboring tiles of the target tile
              controlled by the same province as the target tile have any units with a
              unit possessing a defensePower strictly greater than (>) the attackPower
              of the soldier attempting to move there.
        """
        # Validate coordinates
        if not (0 <= startRow < len(self.mapData)) or not (0 <= startCol < len(self.mapData[startRow])):
            raise ValueError("Invalid start hex coordinates.")
        
        startTile = self.mapData[startRow][startCol]
        
        soldierProvince = startTile.owner
        validTiles = self.getAllTilesWithinMovementRange(startRow, startCol)

        # Finally, remove all friendly tiles which have other soldiers with an incompatible tier
        # on them, or structures on them except for trees. 
        # Also remove neutral and enemy tiles which either posess a unit with too high defense power
        # or are adjacent to a tile owned by the same province which has a unit with too high defense power.
        filteredTiles = []
        for row, col in validTiles:
            tile = self.mapData[row][col]
            if tile.owner == soldierProvince:
                # Friendly tile
                if tile.unit is None or isinstance(tile.unit, Tree):
                    filteredTiles.append((row, col))
                elif isinstance(tile.unit, Soldier):
                    movingSoldier = startTile.unit
                    if movingSoldier is not None and (movingSoldier.tier + tile.unit.tier) <= 4:
                        filteredTiles.append((row, col))
                # Structures block movement
            else:
                # Neutral or enemy tile
                blocked = False
                if tile.unit is not None:
                    if tile.unit.defensePower > startTile.unit.attackPower:
                        blocked = True
                if not blocked:
                    for neighbor in tile.neighbors:
                        if neighbor is not None and neighbor.owner == tile.owner and neighbor.unit is not None:
                            if neighbor.unit.defensePower > startTile.unit.attackPower:
                                blocked = True
                                break
                if not blocked:
                    filteredTiles.append((row, col))

        # And remove the tile the soldier is currently on
        if (startRow, startCol) in filteredTiles:
            filteredTiles.remove((startRow, startCol))

        return filteredTiles


    def moveUnit(self, initialHexRow, initialHexCol, finalHexRow, finalHexCol):
        """
        Moves a unit from the initial hex coordinates to the final hex coordinates.
        Errors are raised if the move is invalid, such as:
        - No unit at the initial hex
        - Final hex not a valid movement target for the unit

        Returns a list of Action instances representing this move and all its consequences,
        which can be applied in sequence to properly update the game state.
        """
        # Validate coordinates
        if not (0 <= initialHexRow < len(self.mapData)) or not (0 <= initialHexCol < len(self.mapData[initialHexRow])):
            raise ValueError("Invalid initial hex coordinates.")
        if not (0 <= finalHexRow < len(self.mapData)) or not (0 <= finalHexCol < len(self.mapData[finalHexRow])):
            raise ValueError("Invalid final hex coordinates.")
        
        initialTile = self.mapData[initialHexRow][initialHexCol]
        finalTile = self.mapData[finalHexRow][finalHexCol]
        
        # Validate presence of a mobile unit
        if initialTile.unit is None or not initialTile.unit.canMove:
            raise ValueError("No mobile unit at the initial hex to move.")
        
        # Validate that the initial tile has an owner
        # and that the owner is active
        if initialTile.owner is None or not initialTile.owner.active:
            raise ValueError("Initial hex does not belong to an active province.")
            
        unitToMove = initialTile.unit
        
        # Validate movement range
        validMovementTiles = self.getAllTilesWithinMovementRangeFiltered(initialHexRow, initialHexCol)
        if (finalHexRow, finalHexCol) not in validMovementTiles:
            raise ValueError("Final hex is not a valid movement target for the unit.")
        
        # Additional validations for specific cases (structures, soldier merging)
        if finalTile.owner == initialTile.owner and finalTile.unit is not None:
            if isinstance(finalTile.unit, Structure):
                raise ValueError("Cannot move onto a tile with a structure.")
                
            if isinstance(unitToMove, Soldier) and isinstance(finalTile.unit, Soldier):
                if unitToMove.tier + finalTile.unit.tier > 4:
                    raise ValueError("Cannot merge soldiers: tier sum exceeds 4.")
        
        # Create list to store all actions
        actions = []
        
        # Create the primary movement action
        incomeFromMove = 0
        if isinstance(finalTile.unit, Tree) and finalTile.owner == initialTile.owner:
            incomeFromMove = 3  # Income from tree
        
        # Check if this is a soldier merge
        resultantUnit = unitToMove
        if (finalTile.owner == initialTile.owner and
            finalTile.unit is not None and
            isinstance(finalTile.unit, Soldier) and
            isinstance(unitToMove, Soldier)):
            resultantUnit = Soldier(unitToMove.tier + finalTile.unit.tier)
        
        previousInitialHexState = {
            "unit": unitToMove,
            "owner": initialTile.owner
        }
        previousFinalHexState = {
            "unit": finalTile.unit,
            "owner": finalTile.owner
        }
        
        resultantInitialHexState = {
            "unit": None,
            "owner": initialTile.owner
        }

        resultantFinalHexState = {
            "unit": resultantUnit,
            "owner": initialTile.owner
        }

        moveAction = Action("moveUnit", {
            "initialHexCoordinates": (initialHexRow, initialHexCol),
            "finalHexCoordinates": (finalHexRow, finalHexCol),
            "previousInitialHexState": previousInitialHexState,
            "previousFinalHexState": previousFinalHexState,
            "resultantInitialHexState": resultantInitialHexState,
            "resultantFinalHexState": resultantFinalHexState,
            "unitMoved": unitToMove,
            "incomeFromMove": incomeFromMove
        })
        
        actions.append(moveAction)
        
        # Add consequence actions for tile capture if needed
        if finalTile.owner is not None and initialTile.owner is not None:
            if finalTile.owner.faction != initialTile.owner.faction:
                # This is a capture move
                conqueringProvince = initialTile.owner
                losingProvince = finalTile.owner
                
                # Get actions for province changes
                captureActions = losingProvince.removeTile(finalTile, conqueringProvince)
                actions.extend(captureActions)
        
        # If moving to a neutral tile, claim it
        elif finalTile.owner is None and initialTile.owner is not None:
            conqueringProvince = initialTile.owner
            addActions = conqueringProvince.addTile(finalTile)
            actions.extend(addActions)
        
        return actions
    

    def getBuildableUnitsOnTile(self, row, col, province):
        """
        Returns a list of unitType strings that are valid for construction
        on the specified tile for the given province.

        Valid unitTypes include: "soldierTier1", "soldierTier2", "soldierTier3", "soldierTier4",
                                 "farm", "tower1", "tower2"

        Rules for building:
        - Cannot build on water tiles
        - Province must have enough resources
        - Farms can only be built adjacent to a capital or another farm
        - Soldiers can be built on enemy tiles if conditions are met
            a) Tile is adjacent to a tile owned by the province
            b) Neither the target tile nor any neighboring tiles owned by the same province
               as the target tile have any units with a unit possessing a
               defensePower strictly greater than (>) the attackPower
               of the soldier attempting to be built there.
        - Units cannot be built on tiles with other units, except:
            a) Soldiers can be built on trees (chopping them down)
            b) Soldiers can merge with other soldiers of the same faction
               if their combined tier <= 4
            c) Tower2 can be built on top of Tower1
        - Otherwise, can only build on empty tiles owned by the province
        """
        buildableUnits = []

        # Validate coordinates
        if not (0 <= row < len(self.mapData)) or not (0 <= col < len(self.mapData[row])):
            return buildableUnits  # Empty list if coordinates are invalid
        
        # Validate that the province is not none and is active
        if province is None or not province.active:
            return buildableUnits

        tile = self.mapData[row][col]

        # Cannot build on water tiles
        if tile.isWater:
            return buildableUnits

        # Check if province owns the tile
        if tile.owner == province:
            # Check what's on the tile
            if tile.unit is None:
                # Empty tile - can build any unit if resources permit
                if province.resources >= 10:
                    buildableUnits.append("soldierTier1")
                if province.resources >= 20:
                    buildableUnits.append("soldierTier2")
                if province.resources >= 30:
                    buildableUnits.append("soldierTier3")
                if province.resources >= 40:
                    buildableUnits.append("soldierTier4")

                # For farms, check if adjacent to capital or farm
                canBuildFarm = False
                for neighbor in tile.neighbors:
                    if (neighbor is not None and 
                        neighbor.owner == province and 
                        neighbor.unit is not None and 
                        (neighbor.unit.unitType == "capital" or neighbor.unit.unitType == "farm")):
                        canBuildFarm = True
                        break

                if canBuildFarm and province.resources >= 12:
                    # Calculate farm cost based on existing farms
                    farmCount = sum(1 for t in province.tiles if t.unit is not None and t.unit.unitType == "farm")
                    farmCost = 12 + farmCount * 2
                    if province.resources >= farmCost:
                        buildableUnits.append("farm")

                if province.resources >= 15:
                    buildableUnits.append("tower1")

                if province.resources >= 35:
                    buildableUnits.append("tower2")

            elif tile.unit.unitType == "tower1" and province.resources >= 35:
                # Can upgrade tower1 to tower2
                buildableUnits.append("tower2")

            elif tile.unit.unitType == "tree":
                # Can build soldiers on trees
                if province.resources >= 7:  # 10 - 3 (income from tree)
                    buildableUnits.append("soldierTier1")
                if province.resources >= 17:  # 20 - 3
                    buildableUnits.append("soldierTier2")
                if province.resources >= 27:  # 30 - 3
                    buildableUnits.append("soldierTier3")
                if province.resources >= 37:  # 40 - 3
                    buildableUnits.append("soldierTier4")

            elif isinstance(tile.unit, Soldier):
                # Check if we can merge with this soldier
                existingTier = tile.unit.tier
                for tier in range(1, 5):
                    if existingTier + tier <= 4 and province.resources >= tier * 10:
                        buildableUnits.append(f"soldierTier{tier}")

        else:
            # For tiles not owned by the province, we can only build soldiers as capture
            # The tile must be adjacent to a tile owned by the province
            isAdjacentToProvince = False
            for neighbor in tile.neighbors:
                if neighbor is not None and neighbor.owner == province:
                    isAdjacentToProvince = True
                    break

            if not isAdjacentToProvince:
                return buildableUnits

            # Check defensePower conditions
            maxDefensePower = tile.unit.defensePower if tile.unit is not None else 0
            for neighbor in tile.neighbors:
                if neighbor is not None and neighbor.owner == tile.owner and neighbor.unit is not None:
                    if neighbor.unit.defensePower > maxDefensePower:
                        maxDefensePower = neighbor.unit.defensePower

            # Add soldier tiers that can capture this tile
            for tier in range(1, 5):
                attackPower = tier
                if attackPower >= maxDefensePower and province.resources >= tier * 10:
                    buildableUnits.append(f"soldierTier{tier}")

        return buildableUnits

    def buildUnitOnTile(self, row, col, unitType, province):
        """
        Builds a unit of the specified type on the given tile.
        Returns an Action instance representing this tile change,
        as well as all actions consequent to this action,
        or raises an error if the build is invalid.

        Delegates validation of whether the unit can be built
        on the specified tile to getBuildableUnitsOnTile.
        """
        # Get all buildable units for this tile
        buildableUnits = self.getBuildableUnitsOnTile(row, col, province)

        # Check if the requested unitType is buildable
        if unitType not in buildableUnits:
            raise ValueError(f"Cannot build {unitType} on the specified tile.")

        tile = self.mapData[row][col]

        # Calculate cost of action
        # Done here in case a merge happens,
        # which would change the unit object used for cost calculation
        tempUnit = None
        if unitType.startswith("soldier"):
            tier = int(unitType[-1]) # Tier is always the last character for soldier types
            tempUnit = Soldier(tier=tier, owner=province.faction)
        elif unitType == "farm":
            farmCount = sum(1 for t in province.tiles if t.unit is not None and t.unit.unitType == "farm")
            tempUnit = Structure(structureType="farm", owner=province.faction, numFarms=farmCount)
        elif unitType == "tower1":
            tempUnit = Structure(structureType="tower1", owner=province.faction)
        elif unitType == "tower2":
            tempUnit = Structure(structureType="tower2", owner=province.faction)
        else:
            # Shouldn't be reachable due to prior validation
            raise ValueError(f"Unknown unit type: {unitType}")
        costOfAction = tempUnit.cost

        unit = None
        # Handle a merge if building a soldier on top of another soldier
        if tempUnit is not None and isinstance(tempUnit, Soldier):
            tier = tempUnit.tier
            if isinstance(tile.unit, Soldier) and tile.unit.owner == province.faction:
                # No need for error checking here, as it's already validated
                # in getBuildableUnitsOnTile
                tier = tile.unit.tier + tier
            unit = Soldier(tier=tier, owner=province.faction)
        else:
            unit = tempUnit

        # Prepare previous state for inversion
        previousTileState = {
            "unit": tile.unit,
            "owner": tile.owner
        }

        # Special cases for cost adjustment
        if isinstance(tile.unit, Tree) and isinstance(unit, Soldier) and tile.owner == province:
            costOfAction -= 3  # Reduce cost by 3 for chopping the tree

        # Prepare the new tile state
        newTileState = {
            "unit": unit,
            "owner": province
        }

        # Create the main action
        actionData = {
            "hexCoordinates": (row, col),
            "newTileState": newTileState,
            "previousTileState": previousTileState,
            "costOfAction": costOfAction
        }
        actions = [Action(actionType="tileChange", data=actionData)]

        # If we're building a soldier on a tile controlled by another province,
        # we need to handle the tile capture as well
        # We need to simulate the cost deduction before capturing,
        # in case a merger happens
        # TODO: do this more cleanly
        province.resources -= costOfAction
        if tile.owner is not None and tile.owner != province:
            captureActions = tile.owner.removeTile(tile, province)
            actions.extend(captureActions)
        # If we're building on a neutral tile, we need to add the tile to our province
        elif tile.owner is None:
            addActions = province.addTile(tile)
            actions.extend(addActions)
            
        # Reset province resources to original value before returning
        province.resources += costOfAction
        return actions
        

    def applyAction(self, action, provinceDoingAction=None):
        """
        Applies the given action to the scenario,
        mutating the scenario's state accordingly.
        The action should be an instance of the Action class.
        See the documentation of the Action class for details.

        This method ONLY applies the exact action specified and does not
        generate any consequence actions. Consequence actions must be
        generated separately and applied in the correct order.
        """
        if not isinstance(action, Action):
            raise ValueError("Invalid action type.")
        
        if action.actionType == "moveUnit":
            # Extract the coordinates
            initRow, initCol = action.data["initialHexCoordinates"]
            finalRow, finalCol = action.data["finalHexCoordinates"]
            
            # Get the tiles
            initTile = self.mapData[initRow][initCol]
            finalTile = self.mapData[finalRow][finalCol]
            
            # Basically this is like two tile changes:
            # The initial tile gets turned into whatever resultantInitialHexState says
            # The final tile gets turned into whatever resultantFinalHexState says

            # Update initial tile
            if "unit" in action.data["resultantInitialHexState"]:
                initTile.unit = action.data["resultantInitialHexState"]["unit"]
            if "owner" in action.data["resultantInitialHexState"]:
                # Before updating the tile, we also need to check if
                # the owner is changing, and if so, update the new and old province's tile lists
                if initTile.owner is not None and initTile in initTile.owner.tiles:
                    initTile.owner.tiles.remove(initTile)
                initTile.owner = action.data["resultantInitialHexState"]["owner"]
                if initTile.owner is not None and initTile not in initTile.owner.tiles:
                    initTile.owner.tiles.append(initTile)

            # Update final tile
            if "unit" in action.data["resultantFinalHexState"]:
                finalTile.unit = action.data["resultantFinalHexState"]["unit"]
            if "owner" in action.data["resultantFinalHexState"]:
                # Before updating the tile, we also need to check if
                # the owner is changing, and if so, update the province's tile list
                if finalTile.owner is not None and finalTile in finalTile.owner.tiles:
                    finalTile.owner.tiles.remove(finalTile)
                finalTile.owner = action.data["resultantFinalHexState"]["owner"]
                if finalTile.owner is not None and finalTile not in finalTile.owner.tiles:
                    finalTile.owner.tiles.append(finalTile)
            
            # We simply invert the canMove status of the unit moved
            # This way we both mark units who have moved as unable to move,
            # and undo that status when inverting the action
            if action.data["unitMoved"] is not None:
                action.data["unitMoved"].canMove = not action.data["unitMoved"].canMove

            # Handle income from chopping trees
            if action.data["incomeFromMove"] != 0 and initTile.owner:
                # Can only get income from cutting down a tree if
                # the tree belongs to your own province
                if finalTile.owner == initTile.owner:
                    finalTile.owner.resources += action.data["incomeFromMove"]
                
        elif action.actionType == "tileChange":
            row, col = action.data["hexCoordinates"]
            tile = self.mapData[row][col]
            
            # Apply tile state changes
            if "unit" in action.data["newTileState"]:
                tile.unit = action.data["newTileState"]["unit"]
            
            if "owner" in action.data["newTileState"]:
                # First, if the tile had a previous owner different from the new owner,
                # remove the tile from that province
                if tile.owner is not None and tile in tile.owner.tiles and tile.owner != action.data["newTileState"]["owner"]:
                    tile.owner.tiles.remove(tile)
                # Now we can set the new owner
                tile.owner = action.data["newTileState"]["owner"]
                
                if tile.owner is not None and tile not in tile.owner.tiles:
                    tile.owner.tiles.append(tile)

            # Special case: If a soldier is built on top of a tree,
            # or if a soldier is built on top of a tile not owned by
            # the province passed in, we need to mark the soldier as having moved
            # for this turn.
            if ("unit" in action.data["newTileState"] and
                isinstance(action.data["previousTileState"]["unit"], Tree) and 
                isinstance(tile.unit, Soldier)):
                tile.unit.canMove = False
            elif ("owner" in action.data["newTileState"] and
                  action.data["previousTileState"]["owner"] != action.data["newTileState"]["owner"] and
                  isinstance(tile.unit, Soldier)):
                tile.unit.canMove = False
                
            # Update resources if this action has a cost
            if action.data["costOfAction"] != 0:
                if provinceDoingAction:
                    provinceDoingAction.resources -= action.data["costOfAction"]
                else:
                    faction = self.getFactionToPlay()
                    if faction:
                        for province in faction.provinces:
                            if tile in province.tiles:
                                province.resources -= action.data["costOfAction"]
                                break
    
        elif action.actionType == "provinceCreate":
            faction = action.data["faction"]
            province = action.data["province"]
            
            # Add the province to the faction
            if province not in faction.provinces:
                faction.provinces.append(province)
                
            # If initial tiles were specified, assign them to this province
            if "initialTiles" in action.data:
                for tile in action.data["initialTiles"]:
                    if tile not in province.tiles:
                        province.tiles.append(tile)
                        tile.owner = province
                        # Check the old tile owner and remove the tile from their list if needed
                        oldTile = self.mapData[tile.row][tile.col]
                        if oldTile.owner is not None and oldTile in oldTile.owner.tiles and oldTile.owner != province:
                            oldTile.owner.tiles.remove(oldTile)
                        # Now we can update the map's version of the tile to match
                        self.mapData[tile.row][tile.col] = tile
        
        elif action.actionType == "provinceDelete":
            faction = action.data["faction"]
            province = action.data["province"]
            
            # Remove the province from the faction
            if province in faction.provinces:
                faction.provinces.remove(province)
        
        elif action.actionType == "provinceResourceChange":
            province = action.data["province"]
            newResources = action.data["newResources"]
            
            # Update the province's resources
            province.resources = newResources
        
        elif action.actionType == "provinceActivationChange":
            province = action.data["province"]
            newActiveState = action.data["newActiveState"]
            
            # Update the province's active status
            province.active = newActiveState
