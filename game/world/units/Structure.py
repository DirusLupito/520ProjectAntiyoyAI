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
    def __init__(self, structure_type=None, owner=None):
        if structure_type == "capital":
            super().__init__(unit_type="capital", attack_power=0, defense_power=2, upkeep=1, cost=0, can_move=False, owner=owner)
        elif structure_type == "tower1":
            super().__init__(unit_type="tower1", attack_power=0, defense_power=3, upkeep=2, cost=0, can_move=False, owner=owner)
        elif structure_type == "tower2":
            super().__init__(unit_type="tower2", attack_power=0, defense_power=4, upkeep=3, cost=0, can_move=False, owner=owner)
        elif structure_type == "farm":
            super().__init__(unit_type="farm", attack_power=0, defense_power=0, upkeep=1, cost=0, can_move=False, owner=owner)
        else:
            raise ValueError("Invalid structure type. Must be 'capital', 'tower1', 'tower2', or 'farm'.")