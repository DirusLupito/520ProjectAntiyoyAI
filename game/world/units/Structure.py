from game.world.units.Unit import Unit

class Structure(Unit):
    """
    Represents a structure unit in the game.
    Structures are either defensive buildings like a capital or a tier 1 or 2 tower,
    or a farm which increases the resource production of the tile on which it is built
    by 4 resources per turn.
    Friendly soldiers cannot move onto tiles with structures, but enemy soldiers can attack them
    which will destroy the structure on the captured tile.
    Structures cannot be built on tiles with trees.
    Structures do not move or attack.
    """
    def __init__(self, structureType=None, owner=None, numFarms=0):
        if structureType == "capital":
            super().__init__(unitType="capital", attackPower=0, defensePower=1, upkeep=0, cost=0, canMove=False, owner=owner)
        elif structureType == "tower1":
            super().__init__(unitType="tower1", attackPower=0, defensePower=2, upkeep=1, cost=15, canMove=False, owner=owner)
        elif structureType == "tower2":
            super().__init__(unitType="tower2", attackPower=0, defensePower=3, upkeep=6, cost=35, canMove=False, owner=owner)
        elif structureType == "farm":
            super().__init__(unitType="farm", attackPower=0, defensePower=0, upkeep=-4, cost=12 + numFarms * 2, canMove=False, owner=owner)
        else:
            raise ValueError("Invalid structure type. Must be 'capital', 'tower1', 'tower2', or 'farm'.")
