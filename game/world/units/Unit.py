class Unit:
    """
    Abstract base class for all units in the game.
    A unit can be a soldier, a tree, or a building.
    
    Contains basic attributes and methods common to all units.
    """
    def __init__(self, unit_type=None, attack_power=0, defense_power=0, upkeep=0, cost=0, can_move=False, owner=None):
        self.unit_type = unit_type  # String, Type of the unit (e.g. 'soldier_tier1', 'tree', 'capital', etc.)
        self.attack_power = attack_power  # Integer, Attack power of the unit
        self.defense_power = defense_power  # Integer, Defense power of the unit
        self.upkeep = upkeep  # Integer, Upkeep cost of the unit
        self.cost = cost  # Integer, Cost to build the unit
        self.can_move = can_move  # Boolean indicating if the unit can move
        self.owner = owner  # Faction that owns the unit