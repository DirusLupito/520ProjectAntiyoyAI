from typing import Optional

class GameOutcome:
    """Represents the result of a single tournament game."""

    def __init__(self, winnerName: Optional[str], winnerColor: Optional[str], seed: Optional[int], numberOfTurns: int) -> None:
        """
        Initializes a new GameOutcome with the given parameters.

        Args:
            winnerName (Optional[str]): The display name of the winning AI personality, or None if there was no winner.
            winnerColor (Optional[str]): The color of the winning faction, or None if there was no winner.
            seed (Optional[int]): The random seed used for the game, or None if a random seed was used.
            numberOfTurns (int): The total number of turns played in the game.
        """
        self.winnerName = winnerName
        self.winnerColor = winnerColor
        self.seed = seed
        self.numberOfTurns = numberOfTurns
