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
    Gravestones are a special type of tree that spawn when a soldier dies due to insufficient
    resources to pay its upkeep. Gravestones can be removed like how trees can be chopped down,
    but they do not provide any resources when removed. After 1 turn, a gravestone will
    turn into a normal tree.
    """
    def __init__(self, isGravestone=False, owner=None):
        if isGravestone:
            super().__init__(unitType="gravestone", attackPower=0, defensePower=0, upkeep=0, cost=0, canMove=False, owner=owner)
        else:
            super().__init__(unitType="tree", attackPower=0, defensePower=0, upkeep=1, cost=0, canMove=False, owner=owner)
        