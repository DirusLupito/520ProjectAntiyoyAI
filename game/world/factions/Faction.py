class Faction:
    """
    Represents a faction in the game.
    A faction has a name, a color, and list of provinces it controls,
    """
    def __init__(self, name=None, color=None, provinces=None):
        self.name = name  # String, Name of the faction
        self.color = color  # String, Color of the faction (e.g. 'red', 'blue', etc.)
        self.provinces = provinces if provinces is not None else []  # List of Province instances controlled by the faction
    