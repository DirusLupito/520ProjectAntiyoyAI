from game.world.HexTile import HexTile
from game.world.factions.Faction import Faction
from game.world.units.Unit import Unit
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
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
        
    def addTile(self, tile):
        """
        Adds a tile to the province, and to the tile's owner.
        This will also check to see if the tile is adjacent to any other provinces
        owned by the same faction, and if so, merge those provinces into this one,
        cleaning up any references to the old provinces.
        Merging provinces is done by adding all tiles from the other province
        to this province, updating those HexTile's owner to this province,
        removing the other province from the faction's list of provinces,
        deleting the capital unit of the other province, 
        and merging the resources of the other province's treasury into this province's treasury.
        """
        if tile in self.tiles:
            return  # Tile is already in the province, nothing to do
        if tile.isWater:
            raise ValueError("Cannot add a water tile to a province.")
        if tile.owner is not None and tile.owner != self and tile.owner.faction == self.faction:
            # This should be impossible if the game logic is correct,
            # but just in case, we handle it gracefully by merging the provinces
            self.mergeProvinces(tile.owner)
        self.tiles.append(tile)
        tile.owner = self
        # Check for adjacent provinces owned by the same faction to merge
        for neighbor in tile.neighbors:
            if neighbor is not None and neighbor.owner is not None and neighbor.owner != self and neighbor.owner.faction == self.faction:
                self.mergeProvinces(neighbor.owner)
            
    def mergeProvinces(self, otherProvince):
        """
        Merges another province into this one.
        This involves adding all tiles from the other province
        to this province, updating those HexTile's owner to this province,
        removing the other province from the faction's list of provinces,
        deleting the capital unit of the other province, 
        and merging the resources of the other province's treasury into this province's treasury.
        """
        if otherProvince == self:
            return  # Cannot merge a province with itself
        if otherProvince.faction != self.faction:
            raise ValueError("Cannot merge provinces controlled by different factions.")
        for tile in otherProvince.tiles:
            if tile not in self.tiles:
                self.tiles.append(tile)
                tile.owner = self
        self.resources += otherProvince.resources
        if otherProvince in self.faction.provinces:
            self.faction.provinces.remove(otherProvince)
        # Remove the capital unit of the other province, if it exists
        for tile in otherProvince.tiles:
            if tile.unit is not None and tile.unit.unitType == "capital":
                tile.unit = None  # Capital is destroyed upon merging
                break
        # Clear the other province's tiles to help with garbage collection
        otherProvince.tiles.clear()
        
    def removeTile(self, tile, conqueringProvince):
        """
        Removes a tile from the province, and from the tile's owner.
        Adds the tile to the conquering province, which is handled in addTile.
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
        if tile not in self.tiles:
            return  # Tile is not in this province, nothing to do
        if conqueringProvince == None:
            raise ValueError("A conquering province must be provided when removing a tile.")
        if conqueringProvince.faction == self.faction:
            raise ValueError("The conquering province must be controlled by a different faction.")

        # Remove the tile from this province
        self.tiles.remove(tile)
        tile.owner = None

        # If province now has 0 tiles, remove it entirely
        if len(self.tiles) == 0:
            if self in self.faction.provinces:
                self.faction.provinces.remove(self)
            conqueringProvince.addTile(tile)
            return

        # If province now has 1 tile, mark as inactive and reset treasury
        if len(self.tiles) == 1:
            self.active = False
            self.resources = 0
            conqueringProvince.addTile(tile)
            return

        # Check if province is still contiguous after removing the tile
        # Use BFS to find all contiguous groups of tiles
        contiguousGroups = self.findContiguousGroups()

        # If there's only one group, the province is still contiguous
        if len(contiguousGroups) == 1:
            self.active = True  # Ensure province is marked as active
            # Add the tile to the conquering province if provided
            conqueringProvince.addTile(tile)
            return

        # Province is no longer contiguous, need to split it
        self.splitProvince(contiguousGroups)

        # Add the tile to the conquering province
        conqueringProvince.addTile(tile)

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

    def splitProvince(self, contiguousGroups):
        """
        Split this province into multiple provinces based on contiguous groups.
        The largest group keeps the original province data (resources, capital).
        Other groups form new provinces with new capitals and 0 resources.
        """

        # Find the largest group - it will keep the original province
        largestGroup = max(contiguousGroups, key=len)

        # Update this province to only contain the largest group
        self.tiles = largestGroup
        for tile in largestGroup:
            tile.owner = self

        # Create new provinces for the other groups
        for group in contiguousGroups:
            if group == largestGroup:
                continue  # Skip the largest group as it's handled above
            
            # Create a new province
            newProvince = Province(tiles=[], resources=0, faction=self.faction)
            self.faction.provinces.append(newProvince)

            # Add tiles to the new province
            for tile in group:
                newProvince.tiles.append(tile)
                tile.owner = newProvince

            # Set the new province as active if it has 2 or more tiles
            newProvince.active = len(group) >= 2

            # If the new province is inactive (1 tile), 
            # rather than place a capital, we need to either
            # delete or transform the unit on that tile
            if not newProvince.active:
                singleTile = group[0]
                if singleTile.unit is not None and singleTile.unit.unitType == "capital":
                    # If the single tile has a capital, turn it into a tree
                    singleTile.unit = Tree(owner=self.faction)
                # If it has a tower or farm, just remove it
                elif singleTile.unit is not None and (singleTile.unit.unitType == "tower1" or 
                                                      singleTile.unit.unitType == "tower2" or 
                                                      singleTile.unit.unitType == "farm"):
                    singleTile.unit = None
                    # If it has a soldier or tree, leave it as is
                    # ... no code needed here

                # Skip placing a capital for inactive provinces
                continue
            
            # Place a new capital unit in the new province
            # Try to find an empty tile first
            emptyTiles = [t for t in group if t.unit is None]
            farmTiles = [t for t in group if t.unit is not None and t.unit.unitType == "farm"]

            # If we can find an empty tile, use it
            if emptyTiles:
                capitalTile = random.choice(emptyTiles)
            # Otherwise, if we can find a farm tile, use it 
            elif farmTiles:
                capitalTile = random.choice(farmTiles)
            # Otherwise, just pick any tile in the group
            else:
                capitalTile = random.choice(group)

            # Place capital on the chosen tile
            capitalTile.unit = Structure(structureType="capital", owner=self.faction)
            
            
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
        
        # Randomly grow trees onto empty adjacent tiles
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
