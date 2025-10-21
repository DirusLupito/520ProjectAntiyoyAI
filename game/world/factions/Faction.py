class Faction:
    """
    Represents a faction in the game.
    A faction has a name, a color, and list of provinces it controls,
    """
    def __init__(self, name=None, color=None, provinces=None):
        self.name = name  # String, Name of the faction
        self.color = color  # String, Color of the faction (e.g. 'red', 'blue', etc.)
        self.provinces = provinces if provinces is not None else []  # List of Province instances controlled by the faction

    def printWithFactionColor(self, text):
        """
        Prints the given text in the faction's color,
        if the given color matches an ANSI color code.
        """
        color_codes = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m'
        }
        # If the faction's color is a valid ANSI color, use it
        if self.color in color_codes:
            print(f"{color_codes[self.color]}{text}{color_codes['reset']}")
        else:
            # Otherwise, print normally
            print(text)
