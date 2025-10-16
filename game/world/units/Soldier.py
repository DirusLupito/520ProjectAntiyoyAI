from game.world.units.Unit import Unit

class Soldier(Unit):
    """
    Represents a soldier unit in the game.
    Soldiers can move to adjacent uncontrolled tiles,
    or move up to 4 tiles away based on Manhattan distance/
    number of edges crossed to reach the destination tile
    Soldiers come in 4 tiers, which equal their attack and defense power,
    though their defense power is always 1 higher than their attack power
    except for tier 4 soldiers which have equal attack and defense power.
    This prevents equal tier soldier from destroying each other,
    except for tier 4 soldiers which can destroy each other.
    """
    def __init__(self, tier=1, owner=None):
        if tier == 1:
            super().__init__(unitType="soldierTier1", attackPower=1, defensePower=2, upkeep=2, cost=10, canMove=True, owner=owner)
        elif tier == 2:
            super().__init__(unitType="soldierTier2", attackPower=2, defensePower=3, upkeep=6, cost=20, canMove=True, owner=owner)
        elif tier == 3:
            super().__init__(unitType="soldierTier3", attackPower=3, defensePower=4, upkeep=18, cost=30, canMove=True, owner=owner)
        elif tier == 4:
            super().__init__(unitType="soldierTier4", attackPower=4, defensePower=4, upkeep=36, cost=40, canMove=True, owner=owner)
        else:
            raise ValueError("Invalid soldier tier. Must be 1, 2, 3, or 4.")
