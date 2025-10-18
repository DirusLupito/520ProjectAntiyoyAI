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
        owned by the same faction, and if so, merge those provinces into this one.
        Returns a list of actions for applying the changes.

        Merging provinces is done by adding all tiles from the other province
        to this province, updating those HexTile's owner to this province,
        removing the other province from the faction's list of provinces,
        deleting the capital unit of the other province, 
        and merging the resources of the other province's treasury into this province's treasury.
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
        
        # Actually perform the tile addition first
        self.tiles.append(tile)
        
        # Then perform merges (which will generate more actions)
        for province in mergeableProvinces:
            merge_actions = self._createMergeActions(province)
            actions.extend(merge_actions)
            
        return actions

    def _createMergeActions(self, otherProvince):
        """
        Helper method to create actions for merging another province into this one.
        Returns a list of actions for applying the changes.
        """
        actions = []
        
        if otherProvince == self:
            return actions  # Cannot merge a province with itself
            
        if otherProvince.faction != self.faction:
            raise ValueError("Cannot merge provinces controlled by different factions.")
        
        # Create actions for changing ownership of tiles
        for tile in otherProvince.tiles:
            if tile not in self.tiles:
                previousState = {"owner": tile.owner}
                newState = {"owner": self}
                
                action = Action("tileChange", {
                    "hexCoordinates": (tile.row, tile.col),
                    "newTileState": newState,
                    "previousTileState": previousState,
                    "costOfAction": 0
                }, isDirectConsequenceOfAnotherAction=True)
                
                actions.append(action)
        
        # Create action for removing the capital unit of the other province, if it exists
        for tile in otherProvince.tiles:
            if tile.unit is not None and tile.unit.unitType == "capital":
                previousState = {"unit": tile.unit}
                newState = {"unit": None}
                
                action = Action("tileChange", {
                    "hexCoordinates": (tile.row, tile.col),
                    "newTileState": newState,
                    "previousTileState": previousState,
                    "costOfAction": 0
                }, isDirectConsequenceOfAnotherAction=True)

                actions.append(action)
                break
                
        return actions

    def mergeProvinces(self, otherProvince):
        """
        Merges another province into this one and returns a list of actions.

        This involves adding all tiles from the other province
        to this province, updating those HexTile's owner to this province,
        removing the other province from the faction's list of provinces,
        deleting the capital unit of the other province, 
        and merging the resources of the other province's treasury into this province's treasury.
        """
        # Create the actions first
        actions = self._createMergeActions(otherProvince)
        
        # Now actually perform the merge
        if otherProvince == self:
            return actions
            
        if otherProvince.faction != self.faction:
            raise ValueError("Cannot merge provinces controlled by different factions.")
            
        # Add tiles
        for tile in otherProvince.tiles:
            if tile not in self.tiles:
                self.tiles.append(tile)
                tile.owner = self
                
        # Merge resources
        self.resources += otherProvince.resources
        
        # Remove from faction's provinces list
        if otherProvince in self.faction.provinces:
            self.faction.provinces.remove(otherProvince)
            
        # Remove capital
        for tile in otherProvince.tiles:
            if tile.unit is not None and tile.unit.unitType == "capital":
                tile.unit = None
                break
                
        # Clear the other province's tiles
        otherProvince.tiles.clear()
        
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
        newState = {"owner": None}  # Temporarily set to None before conquering province takes it
        
        action = Action("tileChange", {
            "hexCoordinates": (tile.row, tile.col),
            "newTileState": newState,
            "previousTileState": previousState,
            "costOfAction": 0
        }, isDirectConsequenceOfAnotherAction=True)
        
        actions.append(action)
        
        # Actually remove the tile
        self.tiles.remove(tile)
        tile.owner = None
        
        # Handle province with 0 tiles - remove it entirely
        if len(self.tiles) == 0:
            if self in self.faction.provinces:
                self.faction.provinces.remove(self)
            # Add tile to conquering province and get the resulting actions
            conquerActions = conqueringProvince.addTile(tile)
            actions.extend(conquerActions)
            return actions
            
        # Handle province with 1 tile - mark as inactive and reset treasury
        if len(self.tiles) == 1:
            self.active = False
            self.resources = 0
            # Add tile to conquering province and get the resulting actions
            conquerActions = conqueringProvince.addTile(tile)
            actions.extend(conquerActions)
            return actions
            
        # Check if province is still contiguous
        # Uses BFS to find all contiguous groups of tiles
        contiguousGroups = self.findContiguousGroups()
        
        # If there's only one group, the province is still contiguous
        if len(contiguousGroups) == 1:
            self.active = True
            
            # Add tile to conquering province and get the resulting actions
            conquerActions = conqueringProvince.addTile(tile)
            actions.extend(conquerActions)
            
            # If this province lost its capital, we need to place a new one
            capitalExists = any(t.unit is not None and t.unit.unitType == "capital" for t in self.tiles)
            if not capitalExists:
                _, capital_actions = self.placeCapital(self.tiles)
                actions.extend(capital_actions)
            return actions
            
        # Province needs to be split
        split_actions = self._splitProvinceActions(contiguousGroups)
        actions.extend(split_actions)
        
        # Actually perform the split
        self.splitProvince(contiguousGroups)
        
        # Add tile to conquering province and get the resulting actions
        conquerActions = conqueringProvince.addTile(tile)
        actions.extend(conquerActions)
        
        return actions
    
    def findContiguousGroups(self):
        """
        Find all contiguous groups of tiles in this province using BFS.
        Returns a list of lists, where each inner list is a group of contiguous tiles.
        """
        contiguousGroups = []
        unvisited = set(self.tiles)

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

    def _splitProvinceActions(self, contiguousGroups):
        """
        Helper method to create actions for splitting a province.
        The largest group keeps the original province data (resources, capital).
        Other groups form new provinces with new capitals and 0 resources.

        Returns a list of actions for applying the changes.
        """
        actions = []
        
        # Find the largest group
        largestGroup = max(contiguousGroups, key=len)
        
        # Create actions for all groups except the largest
        for group in contiguousGroups:
            if group == largestGroup:
                continue
                
            # Set province as active if it has 2+ tiles
            newProvince = Province(tiles=[], resources=0, faction=self.faction)
            newProvince.active = len(group) >= 2
            
            # Create actions for inactive provinces (1 tile)
            # If the new province is inactive (1 tile), 
            # rather than place a capital, we need to either
            # delete or transform the unit on that tile
            if not newProvince.active:
                singleTile = group[0]
                
                if singleTile.unit is not None and singleTile.unit.unitType == "capital":
                    # If the single tile has a capital, turn it into a tree
                    previousState = {"unit": singleTile.unit}
                    newState = {"unit": Tree(owner=self.faction)}
                    
                    action = Action("tileChange", {
                        "hexCoordinates": (singleTile.row, singleTile.col),
                        "newTileState": newState,
                        "previousTileState": previousState,
                        "costOfAction": 0
                    }, isDirectConsequenceOfAnotherAction=True)
                    
                    actions.append(action)
                    
                # If it has a tower or farm, just remove it
                elif singleTile.unit is not None and (singleTile.unit.unitType == "tower1" or 
                                                     singleTile.unit.unitType == "tower2" or 
                                                     singleTile.unit.unitType == "farm"):
                    # Remove tower or farm
                    previousState = {"unit": singleTile.unit}
                    newState = {"unit": None}
                    
                    action = Action("tileChange", {
                        "hexCoordinates": (singleTile.row, singleTile.col),
                        "newTileState": newState,
                        "previousTileState": previousState,
                        "costOfAction": 0
                    }, isDirectConsequenceOfAnotherAction=True)
                    
                    actions.append(action)
                    
                # If it has a soldier or tree, leave it as is
                # ... no code needed here
                    
            else:
                # For active provinces, place a new capital
                _, capital_actions = newProvince.placeCapital(group)
                actions.extend(capital_actions)
                
        return actions
    
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
        
        if self.resources == 0:
            # All soldier units become gravestones
            for tile in self.tiles:
                if tile.unit is not None and tile.unit.unitType.startswith("soldier"):
                    tile.unit = Tree(isGravestone=True, owner=self.faction)
        
        # Reset soldier units to be able to move again next turn
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType.startswith("soldier"):
                tile.unit.canMove = True
        
        # Turn all preexisting gravestones into normal trees
        for tile in self.tiles:
            if tile.unit is not None and tile.unit.unitType == "gravestone":
                tile.unit = Tree(owner=self.faction)

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
            
    def isActive(self):
        """
        Returns True if the province is active (2 or more tiles), False otherwise.
        """
        return self.active

    # def __eq__(self, other):
    #     if not isinstance(other, Province):
    #         return False
    #     return self.faction == other.faction and self.tiles == other.tiles

    def __str__(self):
        return f"Province controlled by {self.faction.name} with {len(self.tiles)} tiles and {self.resources} resources. Active: {self.active}"
