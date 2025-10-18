class Scenario:
    """
    Represents a game scenario with its settings and configurations.
    So far, only the base antiyoy game is implemented, with no
    Diplomacy or Fog of War or Slay rules. Victory conditions
    are also no implemented, with the game ending when one player
    is alone remaining.
    
    A scenario both represents a map that can be played/started
    and the current state of a game in progress.
    Scenarios understand whose turn it is, have datastructures
    for the underlying map with its HexTiles and Provinces
    and factions, and have methods for performing game actions.
    """
    def __init__(self, name, mapData=None, factions=None, indexOfFactionToPlay=0):
        # Name of the scenario. Could also be the description.
        # It's just a string, and only used for display purposes.
        self.name = name
        # mapData is a 2D array of HexTile objects representing the map.
        # We do a simple map between the 2D "rectangular" array and
        # the hexagonal grid by using offset coordinates.
        # So for example, consider the following 2 by 5 grid:
        # ASCII representation of hex grid:
        #     ___     ___     ___
        #    /0,0\___/0,2\___/0,4\
        #    \___/0,1\___/0,3\___/
        #    /1,0\___/1,2\___/1,4\
        #    \___/1,1\___/1,3\___/
        #        \___/   \___/
        #            
        # In this case, mapData[0][0] is hex tile (0,0),
        # mapData[0][1] is hex tile (0,1), and so on.
        # Basically, if we label columns of the hexagonal grid as "q" 
        # and row as "r", then the hex tile at (r, q) is stored in
        # mapData[r][q].
        # 
        # Due to how hexagons are arranged, rows may rise and fall a 
        # bit, but columns remain straight (see the diagram above).
        # Also note that if 0,1 were above 0,0 rather than below it,
        # the neighbor relationships would be different, 
        # so it's important to understand that we start at 0,0
        # with 0,0 being raised above 0,1.
        # 
        # With this in mind, we can realize that if we have
        # the i,j hex tile in mapData[i][j], and we want to find
        # its neighbors, we can do so as follows:
        # - If j is even (0, 2, 4, ...):
        #   - North:     (i-1, j)
        #   - Northeast: (i-1, j+1)
        #   - Southeast: (i, j+1)
        #   - South:     (i+1, j)
        #   - Southwest: (i, j-1)
        #   - Northwest: (i-1, j-1)
        # - If j is odd (1, 3, 5, ...):
        #   - North:     (i-1, j)
        #   - Northeast: (i, j+1)
        #   - Southeast: (i+1, j+1)
        #   - South:     (i+1, j)
        #   - Southwest: (i, j-1)
        #   - Northwest: (i-1, j)
        
        self.mapData = mapData if mapData is not None else []
        
        # List of Faction instances participating in the scenario.
        # The first faction to get a turn is at index indexOfFactionToPlay.
        # Or just 0 if indexOfFactionToPlay is out of range or unspecified.
        self.factions = factions if factions is not None else []
        self.indexOfFactionToPlay = indexOfFactionToPlay if 0 <= indexOfFactionToPlay < len(self.factions) else 0
        
    def getFactionToPlay(self):
        """Returns the Faction instance whose turn it is to play."""
        if 0 <= self.indexOfFactionToPlay < len(self.factions):
            return self.factions[self.indexOfFactionToPlay]
        return None
    
    def advanceTurn(self):
        """
        Advances the turn to the next faction in the list.
        Loops back to the first faction after the last one.
        """
        if len(self.factions) == 0:
            return
        self.indexOfFactionToPlay = (self.indexOfFactionToPlay + 1) % len(self.factions)

    def printMap(self):
        """
        Prints the board state as an ASCII art picture.
        For example, the following would represent a 2x5 grid:
             ___     ___     ___
            /0,0\___/0,2\___/0,4\
            \___/0,1\___/0,3\___/
            /1,0\___/1,2\___/1,4\
            \___/1,1\___/1,3\___/
                \___/   \___/
        """
        if not self.mapData:
            print("Empty map")
            return

        # Determine dimensions
        num_rows = len(self.mapData)
        num_cols = max(len(row) for row in self.mapData) if num_rows > 0 else 0

        # Print the top line
        print("     ", end="")
        for col in range(0, num_cols, 2):
            print("___     ", end="")
        print()

            

        # Print the hexagonal grid
        for row in range(num_rows):
            # Top half of even columns and connections to odd columns
            line1 = "    "
            for col in range(num_cols):
                if col % 2 == 0:  # Even column
                    line1 += f"/{row},{col}\\"
                    if col + 1 < len(self.mapData[row]):
                        line1 += "___"
                    if row > 0 and col == num_cols - 2:
                        line1 += "/"
            print(line1)

            # Bottom half of hexagons
            line2 = "    "
            for col in range(num_cols):
                if col % 2 == 1:  # Odd column
                    if col == 1:
                        line2 += "\\"
                    line2 += f"___/{row},{col}\\"
                    if col == num_cols - 2:
                        line2 += "___/"
                # Exception for the 1 column case
                elif num_cols == 1:
                    line2 += "\\___/"
            print(line2)

        # Print the bottom line
        print("        ", end="")
        for col in range(1, num_cols, 2):
            print("\\___/   ", end="")
        print()
