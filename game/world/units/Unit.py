class Unit:
    """
    Abstract base class for all units in the game.
    A unit can be a soldier, a tree, or a building.
    
    Contains basic attributes and methods common to all units.
    """
    def __init__(self, unitType=None, attackPower=0, defensePower=0, upkeep=0, cost=0, canMove=False, owner=None):
        self.unitType = unitType  # String, Type of the unit (e.g. 'soldierTier1', 'tree', 'capital', etc.)
        # attackPower must be > defensePower to move onto a tile with an enemy unit
        # or onto a tile adjacent to an enemy unit
        self.attackPower = attackPower  # Integer, Attack power of the unit
        self.defensePower = defensePower  # Integer, Defense power of the unit
        self.upkeep = upkeep  # Integer, Upkeep cost of the unit
        self.cost = cost  # Integer, Cost to build the unit
        self.canMove = canMove  # Boolean indicating if the unit can move. Also indicates if a soldier has moved this turn.
        self.owner = owner  # Faction that owns the unit
