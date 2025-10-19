from game.Action import Action
from game.world.units import Unit
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
from collections import deque

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
        Advances the turn to the next faction in the list.
        Loops back to the first faction after the last one.
        """
        if len(self.factions) == 0:
            return
        self.indexOfFactionToPlay = (self.indexOfFactionToPlay + 1) % len(self.factions)

    def printMap(self):
        """
        Prints the board state as an ASCII art picture.
        For example, the following would represent a 2x5 grid:
             ___     ___     ___
            /0,0\___/0,2\___/0,4\
            \___/0,1\___/0,3\___/
            /1,0\___/1,2\___/1,4\
            \___/1,1\___/1,3\___/
                \___/   \___/
        """
        if not self.mapData:
            print("Empty map")
            return

        # Determine dimensions
        num_rows = len(self.mapData)
        num_cols = max(len(row) for row in self.mapData) if num_rows > 0 else 0

        # Print the top line
        print("     ", end="")
        for col in range(0, num_cols, 2):
            print("___     ", end="")
        print()

            

        # Print the hexagonal grid
        for row in range(num_rows):
            # Top half of even columns and connections to odd columns
            line1 = "    "
            for col in range(num_cols):
                if col % 2 == 0:  # Even column
                    line1 += f"/{row},{col}\\"
                    if col + 1 < len(self.mapData[row]):
                        line1 += "___"
                    if row > 0 and col == num_cols - 2:
                        line1 += "/"
            print(line1)

            # Bottom half of hexagons
            line2 = "    "
            for col in range(num_cols):
                if col % 2 == 1:  # Odd column
                    if col == 1:
                        line2 += "\\"
                    line2 += f"___/{row},{col}\\"
                    if col == num_cols - 2:
                        line2 += "___/"
                # Exception for the 1 column case
                elif num_cols == 1:
                    line2 += "\\___/"
            print(line2)

        # Print the bottom line
        print("        ", end="")
        for col in range(1, num_cols, 2):
            print("\\___/   ", end="")
        print()

    def getAllTilesWithinMovementRange(self, startRow, startCol):
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
            for neighborIndex, neighbor in enumerate(currentTile.neighbors):
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


    def moveUnit(self, initialHexRow, initialHexCol, finalHexRow, finalHexCol):
        """
        Moves a unit from the initial hex coordinates to the final hex coordinates.
        Returns an Action instance representing this move,
        which can be used to invert the move later if needed.

        Errors are raised if the move is invalid, such as:
        - No unit at the initial hex
        - Final hex not a valid movement target for the unit
        """
        # Validate coordinates
        if not (0 <= initialHexRow < len(self.mapData)) or not (0 <= initialHexCol < len(self.mapData[initialHexRow])):
            raise ValueError("Invalid initial hex coordinates.")
        if not (0 <= finalHexRow < len(self.mapData)) or not (0 <= finalHexCol < len(self.mapData[finalHexRow])):
            raise ValueError("Invalid final hex coordinates.")
        
        initialTile = self.mapData[initialHexRow][initialHexCol]
        finalTile = self.mapData[finalHexRow][finalHexCol]
        
        # Validate presence of a mobile unit at the initial hex
        if initialTile.unit is None or not initialTile.unit.canMove:
            raise ValueError("No mobile unit at the initial hex to move.")

        unitToMove = initialTile.unit

        # Validate that the final hex is within movement range
        validMovementTiles = self.getAllTilesWithinMovementRange(initialHexRow, initialHexCol)
        if (finalHexRow, finalHexCol) not in validMovementTiles:
            raise ValueError("Final hex is not a valid movement target for the unit.")
        
        # If we are moving onto a tile controlled by the same province,
        # and there is a unit there, we need to perform additional checks
        if finalTile.owner == initialTile.owner:
            if finalTile.unit is not None:
                # Can't move onto a structure
                if isinstance(finalTile.unit, Structure):
                    raise ValueError("Cannot move onto a tile with a structure.")
                # You can only merge soldiers if the sum of their tiers is <= 4
                # So a tier 1 soldier can merge with tier 1, 2, or 3 soldiers but not tier 4,
                # tier 2 can merge with tier 1 or 2 soldiers but not tier 3 or 4,
                # tier 3 can only merge with tier 1 soldiers,
                # and tier 4 soldiers cannot merge with any other soldiers.
                if isinstance(unitToMove, Soldier) and isinstance(finalTile.unit, Soldier):
                    if unitToMove.tier + finalTile.unit.tier > 4:
                        raise ValueError("Cannot merge soldiers: tier sum exceeds 4.")
                    else:
                        # Merge is done in the applyAction method
                        # We just need to prepare the Action instance here
                        # which says to move the initial soldier to the final tile
                        # and the applyAction method will handle the merging.
                        previousInitialHexState = {
                            "unit": initialTile.unit,
                            "owner": initialTile.owner
                        }
                        previousFinalHexState = {
                            "unit": finalTile.unit,
                            "owner": finalTile.owner
                        }

                        actionData = {
                            "initialHexCoordinates": (initialHexRow, initialHexCol),
                            "finalHexCoordinates": (finalHexRow, finalHexCol),
                            "previousInitialHexState": previousInitialHexState,
                            "previousFinalHexState": previousFinalHexState,
                            "incomeFromMove": 0
                        }
                        return Action(actionType="moveUnit", data=actionData)   

                # Handle the case of a tree getting chopped down
                if isinstance(finalTile.unit, Tree):
                    # Prepare previous states for inversion
                    previousInitialHexState = {
                        "unit": initialTile.unit,
                        "owner": initialTile.owner
                    }
                    previousFinalHexState = {
                        "unit": finalTile.unit,
                        "owner": finalTile.owner
                    }
                    
                    # Create and return the Action instance
                    actionData = {
                        "initialHexCoordinates": (initialHexRow, initialHexCol),
                        "finalHexCoordinates": (finalHexRow, finalHexCol),
                        "previousInitialHexState": previousInitialHexState,
                        "previousFinalHexState": previousFinalHexState,
                        "incomeFromMove": 3 # Income from chopping down a tree
                    }
                    
                    return Action(actionType="moveUnit", data=actionData)
                
        # Prepare previous states for inversion
        previousInitialHexState = {
            "unit": initialTile.unit,
            "owner": initialTile.owner
        }
        previousFinalHexState = {
            "unit": finalTile.unit,
            "owner": finalTile.owner
        }

        actionData = {
            "initialHexCoordinates": (initialHexRow, initialHexCol),
            "finalHexCoordinates": (finalHexRow, finalHexCol),
            "previousInitialHexState": previousInitialHexState,
            "previousFinalHexState": previousFinalHexState,
            "incomeFromMove": 0
        }

        return Action(actionType="moveUnit", data=actionData)
    
    def buildUnitOnTile(self, row, col, unit, province):
        """
        Builds the given unit on the specified tile.
        Returns an Action instance representing this tile change,
        which can be used to invert the action later if needed.

        Errors are raised if the build is invalid, such as:
        - Tile is water
        - Tile already has a unit, with some exceptions
          a) If a soldier is being built on top of a valid merge target
             (another soldier of the same faction where the sum of tiers is <= 4)
          b) If a soldier is being built on top of a tree (chopping down the tree
             and consuming the soldier's move for the turn)
         - Tile is not owned by the province provided, except if
           the move is to build a soldier on a tile which is a valid
           capture target for the soldier of that level (it must be directly
           adjacent to a tile owned by the province, and neither
           the target tile nor any neighboring tiles owned by the same
           province as the target tile can have units with defensePower
           greater than the soldier's attackPower)
         - Any building is being placed on a tile with a unit already on it
           except for placing a tower2 on top of a tower1
        - Province does not have enough resources to build the unit
        """
        # Validate coordinates
        if not (0 <= row < len(self.mapData)) or not (0 <= col < len(self.mapData[row])):
            raise ValueError("Invalid hex coordinates.")
        
        tile = self.mapData[row][col]
        
        # Validate that the tile is not water
        if tile.isWater:
            raise ValueError("Cannot build on water tiles.")
        
        # Validate that the province has enough resources
        if province.resources < unit.cost:
            raise ValueError("Province does not have enough resources to build the unit.")
        
        # Prepare previous state for inversion
        previousTileState = {
            "unit": tile.unit,
            "owner": tile.owner
        }
        
        costOfAction = unit.cost
        
        # Validate that the province owns the tile or it's a valid capture target
        if tile.owner != province:
            # Check if it's a valid capture target for a soldier
            if not (isinstance(unit, Soldier)):
                raise ValueError("Tile is not owned by the province and unit is not a soldier.")
            # Check if the tile is adjacent to a tile owned by the province
            isAdjacentToProvince = False
            for neighbor in tile.neighbors:
                if neighbor is not None and neighbor.owner == province:
                    isAdjacentToProvince = True
                    break
            if not isAdjacentToProvince:
                raise ValueError("Tile is not owned by the province and is not adjacent to any tile owned by the province.")
            # Check defensePower conditions
            maxDefensePowerOfNeighbors = tile.unit.defensePower if tile.unit is not None else 0
            for neighbor in tile.neighbors:
                if neighbor is not None and neighbor.owner == tile.owner and neighbor.unit is not None:
                    if neighbor.unit.defensePower > maxDefensePowerOfNeighbors:
                        maxDefensePowerOfNeighbors = neighbor.unit.defensePower
            if maxDefensePowerOfNeighbors >= unit.attackPower:
                raise ValueError("Tile or its neighboring tiles have units with defensePower greater than or equal to the soldier's attackPower.")
            
            # At this point, we know it's a valid capture target
            actionData = {
                "hexCoordinates": (row, col),
                "newTileState": {
                    "unit": unit,
                    "owner": province
                },
                "previousTileState": previousTileState,
                "costOfAction": costOfAction
            }

            return Action(actionType="tileChange", data=actionData)

        # If we reach here, the province owns the tile
        # Handle placing units on tiles with existing units
        if tile.unit is not None and isinstance(tile.unit, Soldier) and unit is not None and isinstance(unit, Soldier):
            # Check if they can be merged
            if unit.tier + tile.unit.tier <= 4:
                # Create the new merged soldier
                newSoldier = Soldier(tier=unit.tier + tile.unit.tier, owner=unit.owner)
                newTileState = {
                    "unit": newSoldier,
                    "owner": province
                }
            else:
                raise ValueError("Cannot build soldier: merging with existing soldier would exceed tier 4.")
        elif tile.unit is not None and isinstance(tile.unit, Tree) and unit is not None and isinstance(unit, Soldier):
            # Building a soldier on top of a tree in the same province as the soldier will chop it down,
            # thereby reducing the cost of the action by 3 (income from chopping the tree)
            newTileState = {
                "unit": unit,
                "owner": province
            }
            costOfAction -= 3  # Reduce cost by 3 for chopping the tree
        elif tile.unit is not None and tile.unit.unitType == "tower1" and unit is not None and unit.unitType == "tower2":
            # Upgrading tower1 to tower2
            newTileState = {
                "unit": unit,
                "owner": province
            }
        elif tile.unit is not None:
            # If the tile already has a unit and none of the special cases apply, raise an error
            raise ValueError("Cannot build unit: tile already has a unit.")
        else:
            # Default case, no existing unit on tile
            newTileState = {
                "unit": unit,
                "owner": province
            }

            
        actionData = {
            "hexCoordinates": (row, col),
            "newTileState": newTileState,
            "previousTileState": previousTileState,
            "costOfAction": costOfAction
        }
        
        return Action(actionType="tileChange", data=actionData)
        

    def applyAction(self, action, provinceDoingAction=None):
        """
        Applies the given action to the scenario,
        mutating the scenario's state accordingly.
        The action should be an instance of the Action class.
        See the documentation of the Action class for details.

        Some actions, such as moving a unit, may result in
        yet more actions being performed, like a capital
        spawning if a province loses its capital tile
        or is split up. These additional actions are handled
        within this method as well, and they are returned
        so that a comprehensive list of all actions performed
        as a result of this action can be obtained.
        """
        if not isinstance(action, Action):
            raise ValueError("Invalid action type.")
        
        consequenceActions = []
        
        if action.actionType == "moveUnit":
            # Extract the coordinates
            initRow, initCol = action.data["initialHexCoordinates"]
            finalRow, finalCol = action.data["finalHexCoordinates"]
            
            # Get the tiles
            initTile = self.mapData[initRow][initCol]
            finalTile = self.mapData[finalRow][finalCol]
            
            movingUnit = initTile.unit
            
            # Check if this move involves capturing a tile
            isCaptureMove = False
            if finalTile.owner is not None and initTile.owner is not None:
                if finalTile.owner.faction != initTile.owner.faction:
                    isCaptureMove = True
        
            # Check if this is a soldier merge (same faction soldiers on same tile)
            isMergeMove = False
            if (finalTile.owner == initTile.owner and 
                finalTile.unit is not None and 
                isinstance(finalTile.unit, Soldier) and 
                isinstance(movingUnit, Soldier)):
                isMergeMove = True
                
            # Handle soldier merging
            if isMergeMove:
                # Calculate the new tier (sum of both tiers)
                newTier = movingUnit.tier + finalTile.unit.tier
                
                # Create the new, higher-tier soldier on the destination tile
                finalTile.unit = Soldier(tier=newTier, owner=movingUnit.owner)
                
                # Clear the source tile
                initTile.unit = None
            else:
                # Standard unit movement
                finalTile.unit = movingUnit
                initTile.unit = None
            
            movingUnit.canMove = False  # Mark the unit as having moved this turn

            # Handle income from chopping trees
            if action.data["incomeFromMove"] != 0 and initTile.owner:
                # Can only get income from cutting down a tree if
                # the tree belongs to your own province
                if finalTile.owner == initTile.owner:
                    finalTile.owner.resources += action.data["incomeFromMove"]
            
            # Handle tile capture if needed
            if isCaptureMove:
                # Get the conquering province (the province that owns the unit)
                conqueringProvince = initTile.owner
                
                # Get the province that's losing a tile
                losingProvince = finalTile.owner
                
                # Remove the tile from the losing province and add to conquering province
                captureActions = losingProvince.removeTile(finalTile, conqueringProvince)
                
                # Apply each capture-related action
                for captureAction in captureActions:
                    # Apply the action
                    moreConsequences = self.applyAction(captureAction)
                    # Add this action and any further consequences to our list
                    consequenceActions.append(captureAction)
                    consequenceActions.extend(moreConsequences)

            # If the final tile has no province, then we only need to add
            # the tile to the conquering province without removing it from anywhere
            elif finalTile.owner is None:
                # Get the conquering province (the province that owns the unit)
                conqueringProvince = initTile.owner

                # Add the tile to the conquering province
                captureActions = conqueringProvince.addTile(finalTile)

                # Apply each capture-related action
                for captureAction in captureActions:
                    # Apply the action
                    moreConsequences = self.applyAction(captureAction)
                    # Add this action and any further consequences to our list
                    consequenceActions.append(captureAction)
                    consequenceActions.extend(moreConsequences)
                    
        elif action.actionType == "tileChange":
            row, col = action.data["hexCoordinates"]
            tile = self.mapData[row][col]
            
            # Apply tile state changes
            if "unit" in action.data["newTileState"]:
                tile.unit = action.data["newTileState"]["unit"]
            
            if "owner" in action.data["newTileState"]:
                tile.owner = action.data["newTileState"]["owner"]

            # Special case: If a soldier is built on top of a tree,
            # or if a soldier is built on top of a tile not owned by
            # the province passed in, we need to mark the soldier as having moved
            # for this turn.
            if (isinstance(action.data["previousTileState"]["unit"], Tree) and 
                isinstance(tile.unit, Soldier)):
                tile.unit.canMove = False
            elif (action.data["previousTileState"]["owner"] != action.data["newTileState"]["owner"] and
                  isinstance(tile.unit, Soldier)):
                tile.unit.canMove = False
                
            # Update resources if this action has a cost
            if action.data["costOfAction"] != 0:
                # faction = self.getFactionToPlay()
                faction = provinceDoingAction.faction if provinceDoingAction else None
                if not faction:
                    faction = self.getFactionToPlay()
                if faction:
                    # Find the province that should be charged
                    for province in faction.provinces:
                        if tile in province.tiles:
                            province.resources -= action.data["costOfAction"]
                            break
    
        # Return all the consequence actions so they can be tracked
        return consequenceActions
