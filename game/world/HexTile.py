class HexTile:
    """
    Represents a single hexagonal tile in the game world.
    A tile has 6 neighbors, which are other HexTile instances.
    Neighbors are: north, northeast, southeast, south, southwest, northwest.
    A tile has an owner, or faction which controls the tile.
    If no faction controls the tile, the owner is None.
    A tile has a unit on it, which can either represent a soldier of some sort,
    a tree of some sort, or a building of some sort, or be None if the tile is empty.
    
    If the tile is a water tile, it cannot have an owner or a unit.
    Otherwise, if it is a plain tile, it can have an owner and a unit.
    These are the only two types of terrain for now.
    """
    def __init__(self, neighbors=None, owner=None, unit=None, isWater=False):
        # List of 6 neighbors
        # Index 0: northern neighbor,
        # Index 1: northeastern neighbor,
        # Index 2: southeastern neighbor,
        # Index 3: southern neighbor,
        # Index 4: southwestern neighbor,
        # Index 5: northwestern neighbor.
        # If a neighbor does not exist (e.g. edge of map), it is None.
        # This will be treated very similarly to a water tile.
        self.neighbors = neighbors if neighbors is not None else [None] * 6
        self.owner = owner  # Faction that controls the tile
        self.unit = unit  # Unit on the tile (soldier, tree, building, or None)
        self.isWater = isWater  # True if the tile is a water tile, False if plain tile

