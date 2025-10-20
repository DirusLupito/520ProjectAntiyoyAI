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
        Advances the turn to the next faction in the list.
        Loops back to the first faction after the last one.
        """
        if len(self.factions) == 0:
            return
        self.indexOfFactionToPlay = (self.indexOfFactionToPlay + 1) % len(self.factions)

    def printMap(self):
        """
        Prints the board state as an ASCII art picture
        where each hex tile has its coordinates shown.
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

    def printMapWithDetails(self):
        """
        Prints the board state as an ASCII art picture
        where each hex tile has the unit on the tile and the color of the faction
        that controls the tile shown, or "~~~" for water tiles.
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
                    hexTile = self.mapData[row][col]
                    detailStr = ""
                    if hexTile.isWater:
                        detailStr = "~~~"
                    else:
                        unitStr = hexTile.unit.unitType if hexTile.unit is not None else "   "
                        ownerStr = hexTile.owner.faction.color[0] if hexTile.owner is not None else " "
                        detailStr = f"{unitStr[0]}{unitStr[-1]}{ownerStr}"
                    line1 += f"/{detailStr}\\"
                    if col + 1 < len(self.mapData[row]):
                        line1 += "___"
                    if row > 0 and col == num_cols - 2:
                        line1 += "/"
            print(line1)

            # Bottom half of hexagons
            line2 = "    "
            for col in range(num_cols):
                if col % 2 == 1:  # Odd column
                    hexTile = self.mapData[row][col]
                    detailStr = ""
                    if hexTile.isWater:
                        detailStr = "~~~"
                    else:
                        unitStr = hexTile.unit.unitType if hexTile.unit is not None else "   "
                        ownerStr = hexTile.owner.faction.color[0] if hexTile.owner is not None else " "
                        detailStr = f"{unitStr[0]}{unitStr[-1]}{ownerStr}"
                    if col == 1:
                        line2 += "\\"
                    line2 += f"___/{detailStr}\\"
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
        buildable_units = []

        # Validate coordinates
        if not (0 <= row < len(self.mapData)) or not (0 <= col < len(self.mapData[row])):
            return buildable_units  # Empty list if coordinates are invalid

        tile = self.mapData[row][col]

        # Cannot build on water tiles
        if tile.isWater:
            return buildable_units

        # Check if province owns the tile
        if tile.owner == province:
            # Check what's on the tile
            if tile.unit is None:
                # Empty tile - can build any unit if resources permit
                if province.resources >= 10:
                    buildable_units.append("soldierTier1")
                if province.resources >= 20:
                    buildable_units.append("soldierTier2")
                if province.resources >= 30:
                    buildable_units.append("soldierTier3")
                if province.resources >= 40:
                    buildable_units.append("soldierTier4")

                # For farms, check if adjacent to capital or farm
                can_build_farm = False
                for neighbor in tile.neighbors:
                    if (neighbor is not None and 
                        neighbor.owner == province and 
                        neighbor.unit is not None and 
                        (neighbor.unit.unitType == "capital" or neighbor.unit.unitType == "farm")):
                        can_build_farm = True
                        break

                if can_build_farm and province.resources >= 12:
                    # Calculate farm cost based on existing farms
                    farm_count = sum(1 for t in province.tiles if t.unit is not None and t.unit.unitType == "farm")
                    farm_cost = 12 + farm_count * 2
                    if province.resources >= farm_cost:
                        buildable_units.append("farm")

                if province.resources >= 15:
                    buildable_units.append("tower1")

                if province.resources >= 35:
                    buildable_units.append("tower2")

            elif tile.unit.unitType == "tower1" and province.resources >= 35:
                # Can upgrade tower1 to tower2
                buildable_units.append("tower2")

            elif tile.unit.unitType == "tree":
                # Can build soldiers on trees
                if province.resources >= 7:  # 10 - 3 (income from tree)
                    buildable_units.append("soldierTier1")
                if province.resources >= 17:  # 20 - 3
                    buildable_units.append("soldierTier2")
                if province.resources >= 27:  # 30 - 3
                    buildable_units.append("soldierTier3")
                if province.resources >= 37:  # 40 - 3
                    buildable_units.append("soldierTier4")

            elif isinstance(tile.unit, Soldier):
                # Check if we can merge with this soldier
                existing_tier = tile.unit.tier
                for tier in range(1, 5):
                    if existing_tier + tier <= 4 and province.resources >= tier * 10:
                        buildable_units.append(f"soldierTier{tier}")

        else:
            # For tiles not owned by the province, we can only build soldiers as capture
            # The tile must be adjacent to a tile owned by the province
            is_adjacent_to_province = False
            for neighbor in tile.neighbors:
                if neighbor is not None and neighbor.owner == province:
                    is_adjacent_to_province = True
                    break

            if not is_adjacent_to_province:
                return buildable_units

            # Check defensePower conditions
            max_defense_power = tile.unit.defensePower if tile.unit is not None else 0
            for neighbor in tile.neighbors:
                if neighbor is not None and neighbor.owner == tile.owner and neighbor.unit is not None:
                    if neighbor.unit.defensePower > max_defense_power:
                        max_defense_power = neighbor.unit.defensePower

            # Add soldier tiers that can capture this tile
            for tier in range(1, 5):
                attack_power = tier
                if attack_power > max_defense_power and province.resources >= tier * 10:
                    buildable_units.append(f"soldierTier{tier}")

        return buildable_units

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
        buildable_units = self.getBuildableUnitsOnTile(row, col, province)

        # Check if the requested unitType is buildable
        if unitType not in buildable_units:
            raise ValueError(f"Cannot build {unitType} on the specified tile.")

        tile = self.mapData[row][col]

        # Create the appropriate unit object based on unitType
        if unitType.startswith("soldier"):
            tier = int(unitType[-1])
            unit = Soldier(tier=tier, owner=province.faction)
        elif unitType == "farm":
            farm_count = sum(1 for t in province.tiles if t.unit is not None and t.unit.unitType == "farm")
            unit = Structure(structureType="farm", owner=province.faction, numFarms=farm_count)
        elif unitType == "tower1":
            unit = Structure(structureType="tower1", owner=province.faction)
        elif unitType == "tower2":
            unit = Structure(structureType="tower2", owner=province.faction)
        else:
            raise ValueError(f"Unknown unit type: {unitType}")

        # Prepare previous state for inversion
        previousTileState = {
            "unit": tile.unit,
            "owner": tile.owner
        }

        # Calculate cost of action
        costOfAction = unit.cost

        # Special cases for cost adjustment
        if isinstance(tile.unit, Tree) and isinstance(unit, Soldier) and tile.owner == province:
            costOfAction -= 3  # Reduce cost by 3 for chopping the tree

        # Prepare the new tile state
        newTileState = {
            "unit": unit,
            "owner": province
        }

        # Create and return the action
        actionData = {
            "hexCoordinates": (row, col),
            "newTileState": newTileState,
            "previousTileState": previousTileState,
            "costOfAction": costOfAction
        }
        actions = [Action(actionType="tileChange", data=actionData)]

        # If we're building a soldier on a tile controlled by another province,
        # we need to handle the tile capture as well
        if tile.owner is not None and tile.owner != province:
            captureActions = tile.owner.removeTile(tile, province)
            actions.extend(captureActions)
        # If we're building on a neutral tile, we need to add the tile to our province
        elif tile.owner is None:
            addActions = province.addTile(tile)
            actions.extend(addActions)
        return actions
        

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
            elif (action.data["previousTileState"]["owner"] != action.data["newTileState"]["owner"] and
                  isinstance(tile.unit, Soldier)):
                tile.unit.canMove = False
                
            # Update resources if this action has a cost
            if action.data["costOfAction"] != 0:
                faction = None
                if provinceDoingAction:
                    provinceDoingAction.resources -= action.data["costOfAction"]
                else:
                    faction = self.getFactionToPlay()
                    if faction:
                        # Find the province that should be changed
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
                        # Also set mapData tiles at the tile's coordinates
                        # to match this tile in order to keep consistency
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
        
        # Return all the consequence actions so they can be tracked
        return consequenceActions
