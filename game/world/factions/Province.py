from game.world.HexTile import HexTile
from game.world.factions.Faction import Faction
from game.world.units.Unit import Unit
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
from game.Action import Action
import random

class Province:
    """
    Represents a contiguous group of hexagonal tiles
    controlled by a single faction.
    A province has a list of tiles it controls,
    a number of resources it has in its treasury,
    and a single faction that controls the province.
    Uncontrolled tiles are not typically part of any province,
    so it is invalid to create a province with no faction.
    A province requires at least two tiles to not be considered an inactive province.
    Otherwise, an inactive province is one which has exactly one tile,
    but which has no capital unit, has its treasury locked at 0 resources,
    and cannot be used during a turn except by being merged back into a normal province
    if another normal province of the same faction becomes adjacent to it.
    When two provinces controlled by the same faction become adjacent,
    like through conquest of some intermediary tile, they merge into a single province.
    When a province loses tiles, like through conquest by another faction,
    it is possible that the province will no longer be contiguous.
    In that case, the province splits into multiple provinces,
    each of which will come from one of the contiguous groups of tiles
    formed by the split.
    """
    def __init__(self, tiles=None, resources=0, faction=None):
        self.tiles = tiles if tiles is not None else []
        if faction is None:
            raise ValueError("A province must have a controlling faction.")
        if len(self.tiles) < 2:
            self.active = False  # Province is inactive if it has less than 2 tiles
        else:
            self.active = True  # Province is active if it has 2 or more tiles
        self.resources = resources  # Integer, Resources in the province's treasury
        self.faction = faction  # Faction that controls the province

    def placeCapital(self, tiles):
        """
        Creates an action to place a capital unit on one of the provided tiles using the following priority:
        1. Empty tiles
        2. Farm tiles
        3. Any tile in the group
        Returns a tuple with the tile where the capital should be placed and the action.
        """
        # Try to find an empty tile first
        emptyTiles = [t for t in tiles if t.unit is None]
        farmTiles = [t for t in tiles if t.unit is not None and t.unit.unitType == "farm"]

        # Ensures deterministic behavior if the same set of tiles is provided
        random.seed(len(tiles))

        # If we can find an empty tile, use it
        if emptyTiles:
            capitalTile = random.choice(emptyTiles)
        # Otherwise, if we can find a farm tile, use it 
        elif farmTiles:
            capitalTile = random.choice(farmTiles)
        # Otherwise, just pick any tile in the group
        else:
            capitalTile = random.choice(tiles)

        # Create action for placing a capital (store previous unit for invertibility)
        previousState = {"unit": capitalTile.unit}
        newState = {"unit": Structure(structureType="capital", owner=self.faction)}
        
        action = Action("tileChange", {
            "hexCoordinates": (capitalTile.row, capitalTile.col),
            "newTileState": newState,
            "previousTileState": previousState,
            "costOfAction": 0
        }, isDirectConsequenceOfAnotherAction=True)
        
        return capitalTile, [action]

    def addTile(self, tile):
        """
        Creates actions to add a tile to the province.
        This will also check to see if the tile is adjacent to any other provinces
        owned by the same faction, and if so, create actions to merge those provinces.
        Returns a list of actions for applying the changes.

        Merging provinces is done by adding all tiles from the other province
        to this province, updating those HexTile's owner to this province,
        removing the other province from the faction's list of provinces,
        deleting the capital unit of the other province, 
        and merging the resources of the other province's treasury into this province's treasury.
        
        This method only creates actions, it doesn't modify the game state.
        The game state will be modified when these actions are applied.
        """
        actions = []
        
        if tile in self.tiles:
            return actions  # Tile is already in the province, nothing to do
            
        if tile.isWater:
            raise ValueError("Cannot add a water tile to a province.")
            
        # Create action for changing tile ownership
        previousState = {"owner": tile.owner}
        newState = {"owner": self}
        
        action = Action("tileChange", {
            "hexCoordinates": (tile.row, tile.col),
            "newTileState": newState,
            "previousTileState": previousState,
            "costOfAction": 0
        }, isDirectConsequenceOfAnotherAction=True)
        
        actions.append(action)
        
        # Province merging logic 
        mergeableProvinces = []
        
        # Check if the tile belongs to another province of the same faction
        if tile.owner is not None and tile.owner != self and tile.owner.faction == self.faction:
            # This should be impossible if the game logic is correct,
            # but just in case, we handle it gracefully by merging the provinces
            mergeableProvinces.append(tile.owner)
        
        # Check for adjacent provinces owned by the same faction to merge
        for neighbor in tile.neighbors:
            if (neighbor is not None and 
                neighbor.owner is not None and 
                neighbor.owner != self and 
                neighbor.owner.faction == self.faction and
                neighbor.owner not in mergeableProvinces):
                mergeableProvinces.append(neighbor.owner)
        
        # Create merge actions for each mergeable province
        for province in mergeableProvinces:
            mergeActions = self.mergeProvinces(province)
            actions.extend(mergeActions)
            
        return actions

    def mergeProvinces(self, otherProvince):
        """
        Merges another province into this one and returns a list of actions.

        This involves adding all tiles from the other province
        to this province, updating those HexTile's owner to this province,
        removing the other province from the faction's list of provinces,
        deleting the capital unit of the other province, 
        and merging the resources of the other province's treasury into this province's treasury.

        However, nothing will actually be changed until the returned actions
        are applied to the game state.
        """
        actions = []
        
        if otherProvince == self:
            return actions
        
        if otherProvince.faction != self.faction:
            raise ValueError("Cannot merge provinces controlled by different factions.")
        
        # Create resource change action to document the change
        resourceChangeAction = Action("provinceResourceChange", {
            "province": self,
            "previousResources": self.resources,
            "newResources": self.resources + otherProvince.resources
        }, isDirectConsequenceOfAnotherAction=True)
        actions.append(resourceChangeAction)
        
        # Create province deletion action
        deleteAction = Action("provinceDelete", {
            "faction": otherProvince.faction,
            "province": otherProvince,
            "provinceState": {
                "tiles": otherProvince.tiles.copy(),
                "resources": otherProvince.resources,
                "active": otherProvince.active
            }
        }, isDirectConsequenceOfAnotherAction=True)
        actions.append(deleteAction)
        
        # Create tile ownership change actions
        for tile in otherProvince.tiles:
            if tile not in self.tiles:
                tileAction = Action("tileChange", {
                    "hexCoordinates": (tile.row, tile.col),
                    "newTileState": {"owner": self},
                    "previousTileState": {"owner": otherProvince},
                    "costOfAction": 0
                }, isDirectConsequenceOfAnotherAction=True)
                actions.append(tileAction)
        
        # Create capital removal action if needed
        for tile in otherProvince.tiles:
            if tile.unit is not None and tile.unit.unitType == "capital":
                capitalAction = Action("tileChange", {
                    "hexCoordinates": (tile.row, tile.col),
                    "newTileState": {"unit": None},
                    "previousTileState": {"unit": tile.unit},
                    "costOfAction": 0
                }, isDirectConsequenceOfAnotherAction=True)
                actions.append(capitalAction)
                break
        
        return actions

    def removeTile(self, tile, conqueringProvince):
        """
        Creates actions to remove a tile from the province and add it to another province.
        Returns a list of actions for applying the changes.

        This will also check to see if the province is still contiguous,
        and if not, split the province into multiple provinces,
        each of which will come from one of the contiguous groups of tiles
        formed by the split.

        Splitting a province will result in the largest contiguous group of tiles
        retaining its capital unit and all resources, while the other groups
        will randomly select an empty tile to place a new capital unit on,
        or if no empty tile exists, the capital unit will be placed on a tile with a farm,
        or if no such tile exists, the capital unit will be placed on any tile in the group
        at random. No resources will be transferred to the new provinces, they will start with 0 resources.
        If removing the tile would result in the province having less than 2 tiles,
        the entire province is marked as inactive, and its treasury is reset to 0 resources.
        If removing the tile would result in the province having 0 tiles,
        the entire province is removed instead. 
        """
        actions = []
        
        if tile not in self.tiles:
            return actions  # Tile is not in this province, nothing to do
            
        if conqueringProvince == None:
            raise ValueError("A conquering province must be provided when removing a tile.")
            
        if conqueringProvince.faction == self.faction:
            raise ValueError("The conquering province must be controlled by a different faction.")
            
        # Create action for removing ownership
        previousState = {"owner": self}
        newState = {"owner": None}  # Marked as None because conquering province will take it in addTile
        
        action = Action("tileChange", {
            "hexCoordinates": (tile.row, tile.col),
            "newTileState": newState,
            "previousTileState": previousState,
            "costOfAction": 0
        }, isDirectConsequenceOfAnotherAction=True)
        
        actions.append(action)
        
        # Handle province with 0 tiles after removal - create province deletion action
        if len(self.tiles) == 1 and self.tiles[0] == tile:
            deleteAction = Action("provinceDelete", {
                "faction": self.faction,
                "province": self,
                "provinceState": {
                    "tiles": self.tiles.copy(),
                    "resources": self.resources,
                    "active": self.active
                }
            }, isDirectConsequenceOfAnotherAction=True)
            actions.append(deleteAction)
            
            # Create actions for conquering province to add the tile
            conquerActions = conqueringProvince.addTile(tile)
            actions.extend(conquerActions)
            return actions
        
        # Handle province with 1 tile after removal - mark as inactive and reset the treasury
        if len(self.tiles) == 2 and tile in self.tiles:
            # After removing this tile, the province will have 1 tile
            # Create action to mark province as inactive
            activationAction = Action("provinceActivationChange", {
                "province": self,
                "previousActiveState": self.active,
                "newActiveState": False
            }, isDirectConsequenceOfAnotherAction=True)
            actions.append(activationAction)
            
            # Create action to reset resources
            resourceAction = Action("provinceResourceChange", {
                "province": self,
                "previousResources": self.resources,
                "newResources": 0
            }, isDirectConsequenceOfAnotherAction=True)
            actions.append(resourceAction)
            
            # Create actions for conquering province to add the tile
            conquerActions = conqueringProvince.addTile(tile)
            actions.extend(conquerActions)
            return actions
            
        # Check if province will still be contiguous after removal
        # Need to simulate tile removal to find contiguous groups
        remainingTiles = [t for t in self.tiles if t != tile]
        contiguousGroups = self._findContiguousGroups(remainingTiles)
        
        # If there's only one group, the province will still be contiguous
        if len(contiguousGroups) == 1:
            # Create activation action (ensure province remains active)
            if not self.active:
                activationAction = Action("provinceActivationChange", {
                    "province": self,
                    "previousActiveState": self.active,
                    "newActiveState": True
                }, isDirectConsequenceOfAnotherAction=True)
                actions.append(activationAction)
            
            # Create actions for conquering province to add the tile
            conquerActions = conqueringProvince.addTile(tile)
            actions.extend(conquerActions)
            
            # Check if capital will be removed
            if tile.unit is not None and tile.unit.unitType == "capital":
                # Create actions to place a new capital
                _, capitalActions = self.placeCapital(remainingTiles)
                actions.extend(capitalActions)
                
            return actions
            
        # Province needs to be split - create split actions
        splitActions = self._createSplitActions(contiguousGroups)
        actions.extend(splitActions)
        
        # Create actions for conquering province to add the tile
        conquerActions = conqueringProvince.addTile(tile)
        actions.extend(conquerActions)
        
        return actions
    
    def _createSplitActions(self, contiguousGroups):
        """
        Creates actions to split the province into multiple provinces
        based on the provided contiguous groups of tiles.
        The largest group retains the original province's resources and capital,
        while the other groups become new provinces with 0 resources
        and a newly placed capital.
        Returns a list of actions for applying the split.
        """
        actions = []
        
        # Sort groups by size (largest first)
        contiguousGroups.sort(key=len, reverse=True)

        # The first group retains the original province's resources and capital
        mainGroup = contiguousGroups[0]
        otherGroups = contiguousGroups[1:]
        
        # Ensure the main group remains active if it has 2 or more tiles
        activationAction = Action("provinceActivationChange", {
            "province": self,
            "previousActiveState": self.active,
            "newActiveState": mainGroup if len(mainGroup) >= 2 else False
        }, isDirectConsequenceOfAnotherAction=True)
        actions.append(activationAction)

        # Ensure the main group still has a capital
        # Handles edge case where the tile removed
        # to cause the split had the capital on it
        capitalExists = any(tile.unit is not None and tile.unit.unitType == "capital" for tile in mainGroup)
        if not capitalExists:
            _, capitalActions = self.placeCapital(mainGroup)
            actions.extend(capitalActions)
        
        # Create new provinces for other groups
        for group in otherGroups:
            newProvince = Province(tiles=group, resources=0, faction=self.faction)
            
            # Create province creation action
            createAction = Action("provinceCreate", {
                "faction": self.faction,
                "province": newProvince
            }, isDirectConsequenceOfAnotherAction=True)
            actions.append(createAction)
            
            # Create tile ownership change actions
            for tile in group:
                tileAction = Action("tileChange", {
                    "hexCoordinates": (tile.row, tile.col),
                    "newTileState": {"owner": newProvince},
                    "previousTileState": {"owner": self},
                    "costOfAction": 0
                }, isDirectConsequenceOfAnotherAction=True)
                actions.append(tileAction)
            
            # Create actions to place a capital in the new province
            # if the group has two or more tiles
            # _, capitalActions = newProvince.placeCapital(group)
            if len(group) >= 2:
                _, capitalActions = newProvince.placeCapital(group)
                actions.extend(capitalActions)
            # If the group has exactly one tile and its unit is a capital,
            # turn that into a tree
            # If the single tile unit is any other structure, delete it.
            # And if it's some other unit (tree or soldier), leave it alone.
            elif len(group) == 1:
                singleTile = group[0]
                unitTypesToDelete = ["farm", "tower1", "tower2"]
                if singleTile.unit is not None and singleTile.unit.unitType == "capital":
                    previousState = {"unit": singleTile.unit}
                    newState = {"unit": Tree(owner=self.faction)}
                    
                    treeAction = Action("tileChange", {
                        "hexCoordinates": (singleTile.row, singleTile.col),
                        "newTileState": newState,
                        "previousTileState": previousState,
                        "costOfAction": 0
                    }, isDirectConsequenceOfAnotherAction=True)
                    
                    actions.append(treeAction)
                elif singleTile.unit is not None and singleTile.unit.unitType in unitTypesToDelete:
                    previousState = {"unit": singleTile.unit}
                    newState = {"unit": None}
                    
                    deleteAction = Action("tileChange", {
                        "hexCoordinates": (singleTile.row, singleTile.col),
                        "newTileState": newState,
                        "previousTileState": previousState,
                        "costOfAction": 0
                    }, isDirectConsequenceOfAnotherAction=True)
                    
                    actions.append(deleteAction)
        
        return actions
    
    def _findContiguousGroups(self, tiles):
        """
        Find all contiguous groups of tiles in the provided list of tiles.
        Returns a list of lists, where each inner list is a group of contiguous tiles.
        """
        contiguousGroups = []
        unvisited = set(tiles)

        while unvisited:
            # Start a new contiguous group
            startTile = next(iter(unvisited))
            group = []
            queue = [startTile]
            visited = set([startTile])

            # BFS to find all tiles in this contiguous group
            while queue:
                current = queue.pop(0)
                group.append(current)

                for i, neighbor in enumerate(current.neighbors):
                    if (neighbor is not None and 
                        neighbor in unvisited and 
                        neighbor not in visited and 
                        neighbor.owner == self):
                        queue.append(neighbor)
                        visited.add(neighbor)

            # Add this group to our list of contiguous groups
            contiguousGroups.append(group)

            # Remove these tiles from the unvisited set
            unvisited -= set(group)

        return contiguousGroups
    
    def computeIncome(self):
        """
        Computes the income of the province based on its tiles and units.
        Each tile gives 1 resource.
        Each unit gives or takes resources based on its upkeep (negative upkeep gives resources).
        Returns the total income as an integer.
        """
        income = 0
        for tile in self.tiles:
            income += 1  # Each tile gives 1 resource
            if tile.unit is not None:
                income -= tile.unit.upkeep  # Subtract upkeep (negative upkeep adds resources)
        return income
    
    def updateBeforeTurn(self):
        """
        Updates the province before a turn.
        Currently, this is identical to updateAfterTurn,
        except for when it is called and for the fact
        that it will not actually change the resources,
        instead using a temporary variable to hold the new resources.
        Also, it will not make trees grow.
        """
        income = self.computeIncome()
        temporaryResources = self.resources + income

        if temporaryResources < 0:
            temporaryResources = 0

        # Inactivity check here so that soldiers still die on inactive provinces
        if not self.active:
            temporaryResources = 0

        # Turn all preexisting gravestones into normal trees
        # Done before turning soldiers into gravestones to avoid 
        # immediate conversion back to normal trees
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType == "gravestone":
                tile.unit = Tree(owner=self.faction)

        if temporaryResources == 0:
            # All soldier units become gravestones
            for tile in self.tiles:
                if tile.unit is not None and tile.unit.unitType.startswith("soldier"):
                    tile.unit = Tree(isGravestone=True, owner=self.faction)
        
        # Reset soldier units to be able to move again next turn
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType.startswith("soldier"):
                tile.unit.canMove = True
    
    def updateAfterTurn(self):
        """
        Updates the province after a turn.
        This involves computing the income and updating the resources.
        If the province is inactive, its resources remain at 0.
        If the province has soldier units, they are reset to be able to move again next turn.
        If the province has < 0 resources, it is reset to 0. 
        If the province has <= 0 resources after income calculation, all soldier units become gravestones.
        All prexisting gravestones turn into normal trees.
        All trees randomly grow onto empty adjacent tiles regardless of province ownership.
        """
        income = self.computeIncome()
        self.resources += income
        
        if self.resources < 0:
            self.resources = 0

        # Inactivity check here so that soldiers still die on inactive provinces
        if not self.active:
            self.resources = 0
        
        # Turn all preexisting gravestones into normal trees
        # Done before turning soldiers into gravestones to avoid 
        # immediate conversion back to normal trees
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType == "gravestone":
                tile.unit = Tree(owner=self.faction)
        
        if self.resources == 0:
            # All soldier units become gravestones
            for tile in self.tiles:
                if tile.unit is not None and tile.unit.unitType.startswith("soldier"):
                    tile.unit = Tree(isGravestone=True, owner=self.faction)
        
        # Reset soldier units to be able to move again next turn
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType.startswith("soldier"):
                tile.unit.canMove = True

        # Handle random tree growth
        self._growTrees()

    def _growTrees(self):
        """
        Handles random tree growth.
        """
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType == "tree":
                for neighbor in tile.neighbors:
                    if (neighbor is not None and 
                        neighbor.owner is not None and 
                        neighbor.owner.faction == self.faction and 
                        neighbor.unit is None and 
                        not neighbor.isWater):
                        if random.random() < 0.2:  # 20% chance to grow a tree
                            neighbor.unit = Tree(owner=self.faction)

    # def __eq__(self, other):
    #     if not isinstance(other, Province):
    #         return False
    #     return self.faction == other.faction and self.tiles == other.tiles

    def __str__(self):
        return f"Province controlled by {self.faction.name} with {len(self.tiles)} tiles and {self.resources} resources. Active: {self.active}"
