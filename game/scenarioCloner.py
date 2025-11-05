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
        self.originalScenario = originalScenario
        self.clonedScenario = None
        self.factionMap = {}
        self.provinceMap = {}
        self.tileMap = {}
        self.unitMap = {}

    def cloneScenario(self):
        """
        Creates and returns a deep copy of the original Scenario.
        
        Returns:
            Scenario: A deep copy of the original Scenario instance.
        """
        if self.clonedScenario is not None:
            return self.clonedScenario
        newFactions = self._cloneFactions()
        newMapData = self._cloneMap()

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
        
        args:
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
        newFactions = []
        for originalFaction in self.originalScenario.factions:
            newFaction = Faction(
                name=originalFaction.name,
                color=originalFaction.color,
                provinces=[],
                playerType=originalFaction.playerType,
                aiType=originalFaction.aiType
            )
            self.factionMap[originalFaction] = newFaction
            newFactions.append(newFaction)

        for originalFaction in self.originalScenario.factions:
            newFaction = self.factionMap[originalFaction]
            newFaction.provinces = []
            for originalProvince in originalFaction.provinces:
                newProvince = Province(
                    tiles=[],
                    resources=originalProvince.resources,
                    faction=newFaction
                )
                newProvince.active = originalProvince.active
                self.provinceMap[originalProvince] = newProvince
                newFaction.provinces.append(newProvince)
        return newFactions

    def _cloneMap(self):
        """
        Clones the map tiles, their neighbors, owners, and units.
        Populates the provinces created in _cloneFactions.

        Returns:
            List[List[HexTile]]: A 2D list representing the cloned map data.
        """
        originalMapData = self.originalScenario.mapData
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

        for originalRow in originalMapData:
            for originalTile in originalRow:
                clonedTile = self.tileMap[originalTile]
                clonedTile.neighbors = [
                    self.tileMap.get(originalNeighbor)
                    for originalNeighbor in originalTile.neighbors
                ]
                if originalTile.owner is not None:
                    clonedOwner = self.provinceMap[originalTile.owner]
                    clonedTile.owner = clonedOwner
                    clonedOwner.tiles.append(clonedTile)
                if originalTile.unit is not None:
                    clonedTile.unit = self._cloneUnit(originalTile.unit)
        for originalProvince, clonedProvince in self.provinceMap.items():
            clonedProvince.active = originalProvince.active
        return newMapData

    def _cloneUnit(self, originalUnit):
        """
        Clones a unit and records it in the unit map for later lookup.
        
        Args:
            originalUnit (Unit): The original Unit instance to be cloned.

        Returns:
            Unit: The cloned Unit instance.
        """
        if originalUnit in self.unitMap:
            return self.unitMap[originalUnit]

        clonedOwner = self.factionMap.get(originalUnit.owner)
        if isinstance(originalUnit, Soldier):
            clonedUnit = Soldier(tier=originalUnit.tier, owner=clonedOwner)
        elif isinstance(originalUnit, Structure):
            clonedUnit = Structure(structureType=originalUnit.unitType, owner=clonedOwner)
        elif isinstance(originalUnit, Tree):
            isGravestone = originalUnit.unitType == "gravestone"
            clonedUnit = Tree(isGravestone=isGravestone, owner=clonedOwner)
        else:
            clonedUnit = Unit(
                unitType=originalUnit.unitType,
                attackPower=originalUnit.attackPower,
                defensePower=originalUnit.defensePower,
                upkeep=originalUnit.upkeep,
                cost=originalUnit.cost,
                canMove=originalUnit.canMove,
                owner=clonedOwner
            )

        clonedUnit.attackPower = originalUnit.attackPower
        clonedUnit.defensePower = originalUnit.defensePower
        clonedUnit.upkeep = originalUnit.upkeep
        clonedUnit.cost = originalUnit.cost
        clonedUnit.canMove = originalUnit.canMove
        clonedUnit.owner = clonedOwner
        if hasattr(originalUnit, "tier"):
            clonedUnit.tier = originalUnit.tier
        self.unitMap[originalUnit] = clonedUnit
        return clonedUnit
