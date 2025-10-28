class Faction:

    # Mapping of color names to ANSI escape codes for terminal text coloring
    colorCodesMap = {
        'black': '\033[90m',  # Alternative black code
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'black2': '\033[30m\033[47m',   # Regular black with white background for distinction
        'red2': '\033[31m\033[47m',     # Regular red with white background for distinction
        'green2': '\033[32m\033[47m',   # Regular green with white background for distinction
        'yellow2': '\033[33m\033[47m',  # Regular yellow with white background for distinction
        'blue2': '\033[34m\033[47m',    # Regular blue with white background for distinction
        'magenta2': '\033[35m\033[47m', # Regular magenta with white background for distinction
        'cyan2': '\033[36m\033[47m'     # Regular cyan with white background for distinction
    }

    """
    Represents a faction in the game.
    A faction has a name, a color, and list of provinces it controls,
    """
    def __init__(self, name=None, color=None, provinces=None, playerType="human", aiType=None):
        self.name = name  # String, Name of the faction
        # "" and None for name become " "
        if not self.name:
            self.name = " "
        self.color = color  # String, Color of the faction (e.g. 'red', 'blue', etc.)
        self.provinces = provinces if provinces is not None else []  # List of Province instances controlled by the faction
        self.playerType = playerType  # String, Type of the player, either 'human' or 'AI'
        self.aiType = aiType  # String or None, Specifies which AI logic to use, if applicable

    def getFactionColorString(self):
        """
        Returns a string that if printed to a terminal supporting ANSI colors,
        will change subsequent text to the faction's color.
        If the faction's color does not map to a known ANSI code, this 
        will instead return an empty string.
        """
        return Faction.colorCodesMap.get(self.color.lower(), '')
