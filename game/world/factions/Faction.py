class Faction:
    """
    Represents a faction in the game.
    A faction has a name, a color, and list of provinces it controls,
    """
    def __init__(self, name=None, color=None, provinces=None):
        self.name = name  # String, Name of the faction
        self.color = color  # String, Color of the faction (e.g. 'red', 'blue', etc.)
        self.provinces = provinces if provinces is not None else []  # List of Province instances controlled by the faction

    def getFactionColorString(self):
        """
        Returns a string that if printed to a terminal supporting ANSI colors,
        will change subsequent text to the faction's color.
        If the faction's color does not map to a known ANSI code, this 
        will instead return an empty string.
        """
        color_codes = {
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[37m'
        }
        return color_codes.get(self.color.lower(), '')
    