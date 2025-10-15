from game.world.units.Unit import Unit

class Tree(Unit):
    """
    Represents a tree unit in the game.
    Trees are essentially static units that do not move or attack.
    The only way that trees interact with the game is by being chopped down by soldiers
    for 3 resources, and by preventing the tile they are on from giving resources
    to the faction that otherwise owns the tile. Also, buildings cannot be built
    on tiles with trees, though soldier can be placed on them which has the same effect
    as if the tree was chopped down by a soldier moving onto the tile.
    Trees will randomly grow on empty tiles adjacent to other trees that are not water tiles.
    """
    def __init__(self, owner=None):
        super().__init__(unit_type="tree", attack_power=0, defense_power=0, upkeep=1, cost=0, can_move=False, owner=owner)