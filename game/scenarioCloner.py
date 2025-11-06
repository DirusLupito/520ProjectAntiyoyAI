from game.Scenario import Scenario
from game.world.factions.Faction import Faction
from game.world.factions.Province import Province
from game.world.HexTile import HexTile
from game.world.units.Unit import Unit
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree


class ScenarioCloner:
    """
    Utility class for cloning running game state objects.

    Provides the ScenarioCloner helper which deep copies Scenario instances
    and keeps track of the mapping between original and cloned game objects.
    This supports game tree search algorithms like minimax that need to explore multiple
    possible futures without mutating the live Scenario.
    """

    def __init__(self, originalScenario):
        """
        Initializes the cloner with the Scenario that will be duplicated.

        Args:
            originalScenario (Scenario): The Scenario instance to be cloned.
        """
        if originalScenario is None:
            raise ValueError("originalScenario cannot be None")

        # Keeps track of the scenario this cloner is duplicating.
        self.originalScenario = originalScenario
        
        # Keeps track of the clone created by this cloner
        self.clonedScenario = None

        # Maps original game Factions to their clones.
        # The key will be an original Faction,
        # and the value will be the corresponding cloned Faction.
        self.factionMap = {}
        
        # Maps original game Provinces to their clones.
        # The key will be an original Province,
        # and the value will be the corresponding cloned Province.
        self.provinceMap = {}
        
        # Maps original game HexTiles to their clones.
        # The key will be an original HexTile,
        # and the value will be the corresponding cloned HexTile.
        self.tileMap = {}
        
        # Maps original game Units to their clones.
        # The key will be an original Unit,
        # and the value will be the corresponding cloned Unit.
        self.unitMap = {}

    def cloneScenario(self):
        """
        Creates and returns a deep copy of the original Scenario.
        
        Returns:
            Scenario: A deep copy of the original Scenario instance.
        """
        # If reusing the same ScenarioCloner instance,
        # avoid re-cloning.
        if self.clonedScenario is not None:
            return self.clonedScenario
        
        # Otherwise, perform the cloning process from scratch.
        newFactions = self._cloneFactions()
        newMapData = self._cloneMap()

        # At this point all components have been cloned.
        # Now we can assemble the new Scenario instance.
        self.clonedScenario = Scenario(
            name=self.originalScenario.name,
            mapData=newMapData,
            factions=newFactions,
            indexOfFactionToPlay=self.originalScenario.indexOfFactionToPlay
        )
        return self.clonedScenario

    def getScenarioClone(self):
        """
        Returns the cloned Scenario, cloning on demand if needed.
        Meant to be called by outside code so that inside rearrangement 
        of cloning logic can be easily reorganized and refactored
        without affecting outside callers.

        Returns:
            Scenario: The cloned Scenario instance.
        """
        return self.cloneScenario()

    def getFactionClone(self, originalFaction):
        """
        Provides the cloned faction corresponding to the given original.
        If cloneScenario has not yet been called, it will be invoked
        to create the cloned scenario. Otherwise, the existing cloned scenario's 
        data will be used to look up the cloned object.

        Args:
            originalFaction (Faction): The original Faction instance to be cloned.

        Returns:
            Faction: The cloned Faction instance.
        """
        if originalFaction is None:
            return None
        
        if self.clonedScenario is None:
            self.cloneScenario()
            
        return self.factionMap.get(originalFaction)

    def getProvinceClone(self, originalProvince):
        """
        Provides the cloned province corresponding to the given original.
        If cloneScenario has not yet been called, it will be invoked
        to create the cloned scenario. Otherwise, the existing cloned scenario's 
        data will be used to look up the cloned object.

        Args:
            originalProvince (Province): The original Province instance to be cloned.

        Returns:
            Province: The cloned Province instance.
        """
        if originalProvince is None:
            return None
        
        if self.clonedScenario is None:
            self.cloneScenario()
            
        return self.provinceMap.get(originalProvince)

    def getTileClone(self, originalTile):
        """
        Provides the cloned hex tile corresponding to the given original.
        If cloneScenario has not yet been called, it will be invoked
        to create the cloned scenario. Otherwise, the existing cloned scenario's 
        data will be used to look up the cloned object.

        Args:
            originalTile (HexTile): The original HexTile instance to be cloned.

        Returns:
            HexTile: The cloned HexTile instance.
        """
        if originalTile is None:
            return None
        
        if self.clonedScenario is None:
            self.cloneScenario()
            
        return self.tileMap.get(originalTile)

    def getUnitClone(self, originalUnit):
        """
        Provides the cloned unit corresponding to the given original.
        If cloneScenario has not yet been called, it will be invoked
        to create the cloned scenario. Otherwise, the existing cloned scenario's 
        data will be used to look up the cloned object.

        Args:
            originalUnit (Unit): The original Unit instance to be cloned.

        Returns:
            Unit: The cloned Unit instance.
        """
        if originalUnit is None:
            return None
        
        if self.clonedScenario is None:
            self.cloneScenario()
            
        return self.unitMap.get(originalUnit)

    def _cloneFactions(self):
        """
        Clones all factions, creating province shell objects for later population.

        Returns:
            List[Faction]: A list of cloned Faction instances.
        """
        # First, we shall create empty shells for each faction,
        # to be filled in later.
        newFactions = []
        for originalFaction in self.originalScenario.factions:
            
            # We construct the new faction with everything that we can immediately copy,
            # but leave the provinces empty for now since those are not simple objects.
            newFaction = Faction(
                name=originalFaction.name,
                color=originalFaction.color,
                provinces=[],
                playerType=originalFaction.playerType,
                aiType=originalFaction.aiType
            )
            
            # We also need to keep track of what exact Faction object
            # the cloned object corresponds to for later lookups.
            self.factionMap[originalFaction] = newFaction
            newFactions.append(newFaction)

        # Now that we have all factions created, we can create the provinces.
        # Still, the provinces will be mostly empty shells for now.
        for originalFaction in self.originalScenario.factions:
            
            # What's the cloned faction corresponding to this original one?
            newFaction = self.factionMap[originalFaction]
            
            # We now know who the cloned faction is,
            # so now we can get to work on creating the provinces.
            newFaction.provinces = []
            
            # Much like how factions are initially created as empty shells
            # except for basic data which can be copied directly,
            # we do the same for provinces. Their HexTile objects
            # are nontrivial and must have purpose built cloning logic.
            for originalProvince in originalFaction.provinces:
                newProvince = Province(
                    tiles=[],
                    resources=originalProvince.resources,
                    faction=newFaction
                )
                
                # We also need to keep track of what exact Province object
                # the cloned object corresponds to for later lookups.
                self.provinceMap[originalProvince] = newProvince
                newFaction.provinces.append(newProvince)
                
        # We're all done with cloning everything except for the map tiles,
        # which will be handled in _cloneMap.
        return newFactions

    def _cloneMap(self):
        """
        Clones the map tiles, their neighbors, owners, and units.
        Populates the provinces created in _cloneFactions.

        Returns:
            List[List[HexTile]]: A 2D list representing the cloned map data.
        """
        originalMapData = self.originalScenario.mapData
        
        # We shall iterate over every single tile in the original map data,
        # creating a new tile for each one and recording the mapping.
        # Its nontrivial properties (neighbors, owner, unit) will be filled in later.
        newMapData = []
        for originalRow in originalMapData:
            newRow = []
            for originalTile in originalRow:
                newTile = HexTile(
                    row=originalTile.row,
                    col=originalTile.col,
                    neighbors=None,
                    owner=None,
                    unit=None,
                    isWater=originalTile.isWater
                )
                self.tileMap[originalTile] = newTile
                newRow.append(newTile)
            newMapData.append(newRow)

        # Now that we have cloned all pre-existing tiles
        # and factions and provinces, we can go back and 
        # fill in all the fields that required these cloned
        # objects to already exist in order to be filled in.
        for originalRow in originalMapData:
            for originalTile in originalRow:
                clonedTile = self.tileMap[originalTile]
                clonedTile.neighbors = [
                    self.tileMap.get(originalNeighbor)
                    for originalNeighbor in originalTile.neighbors
                ]
                
                # We make sure the owner of this tile
                # is the one which corresponds to the original owner.
                if originalTile.owner is not None:
                    clonedOwner = self.provinceMap[originalTile.owner]
                    clonedTile.owner = clonedOwner
                    clonedOwner.tiles.append(clonedTile)
                    
                # If there is a unit on this tile,
                # we need to clone it as well.
                if originalTile.unit is not None:
                    clonedTile.unit = self._cloneUnit(originalTile.unit)
                    
        # We finally go through all the provinces
        # and set their active status to complete the cloning process.
        for originalProvince, clonedProvince in self.provinceMap.items():
            clonedProvince.active = originalProvince.active
            
        return newMapData

    def _cloneUnit(self, originalUnit):
        """
        Clones a unit and records it in the unit map for later lookup.
        If the unit has already been cloned, returns the existing clone.
        Otherwise, we create a new clone and record it.
        
        Args:
            originalUnit (Unit): The original Unit instance to be cloned.

        Returns:
            Unit: The cloned Unit instance.
        """
        if originalUnit in self.unitMap:
            return self.unitMap[originalUnit]

        # This function better not be called before _cloneFactions,
        # since we need the faction map to be populated already.
        clonedOwner = self.factionMap.get(originalUnit.owner)
        if isinstance(originalUnit, Soldier):
            clonedUnit = Soldier(tier=originalUnit.tier, owner=clonedOwner)
        elif isinstance(originalUnit, Structure):
            clonedUnit = Structure(structureType=originalUnit.unitType, owner=clonedOwner)
        elif isinstance(originalUnit, Tree):
            isGravestone = originalUnit.unitType == "gravestone"
            clonedUnit = Tree(isGravestone=isGravestone, owner=clonedOwner)
        else:
            # Should be impossible to reach here,
            # but just in case an unidentified Unit
            # subclass is encountered, we handle it gracefully.
            clonedUnit = Unit(
                unitType=originalUnit.unitType,
                attackPower=originalUnit.attackPower,
                defensePower=originalUnit.defensePower,
                upkeep=originalUnit.upkeep,
                cost=originalUnit.cost,
                canMove=originalUnit.canMove,
                owner=clonedOwner
            )
        
        # While the constructor should have already handled
        # everything except for canMove, we set all the fields
        # of all the units here explicitly for safety.
        clonedUnit.attackPower = originalUnit.attackPower
        clonedUnit.defensePower = originalUnit.defensePower
        clonedUnit.upkeep = originalUnit.upkeep
        clonedUnit.cost = originalUnit.cost
        clonedUnit.canMove = originalUnit.canMove
        clonedUnit.owner = clonedOwner
        
        # In the case of Soldier units, we also need to copy the tier.
        if hasattr(originalUnit, "tier"):
            clonedUnit.tier = originalUnit.tier
            
        # We're done, record the mapping and return the cloned unit.
        self.unitMap[originalUnit] = clonedUnit
        return clonedUnit
