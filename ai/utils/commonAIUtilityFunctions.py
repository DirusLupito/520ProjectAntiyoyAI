"""
Holds several common utility functions used across AI modules
such as a function for calculating the most optimal way to move a unit
to reach a target tile if the move must take multiple turns.
"""

from collections import deque

def findPathToClosestTile(startTile, targetTiles):
    """
    Finds the shortest path from a start tile to any of the target tiles using BFS.
    This is a BFS implementation that explores the grid layer by layer
    from the starting tile. It keeps track of the path taken to reach each tile.
    When it first encounters a tile that is in the set of target tiles,
    it returns the path to that tile, which is guaranteed to be one of the shortest.

    Args:
        startTile: The HexTile to start the search from.
        targetTiles: A set of HexTiles to search for.

    Returns:
        A list of HexTile objects representing the path, or None if no path is found.
    """
    if not targetTiles:
        return None

    # The queue will store tuples of (tile, pathToTile)
    queue = deque([(startTile, [startTile])])
    visited = {startTile}

    # If the starting tile is already a target, we're done.
    if startTile in targetTiles:
        return [startTile]

    while queue:
        currentTile, path = queue.popleft()

        for neighbor in currentTile.neighbors:
            if neighbor and not neighbor.isWater and neighbor not in visited:
                newPath = path + [neighbor]
                # If we found a target, return the path immediately.
                if neighbor in targetTiles:
                    return newPath
                
                visited.add(neighbor)
                queue.append((neighbor, newPath))

    return None # No path found
