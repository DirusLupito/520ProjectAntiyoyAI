import random
from typing import List, Optional

class TournamentSeedPicker:
    """
    Controls how random seeds are assigned to each tournament game.
    The seed mode can be one of the following:
    - "fixed": All games use the same fixed seed. For instance, if fixedSeed=2, all games use seed 2.
    - "sequential": Seeds are taken in order from a provided list. If there are more games than seeds,
      the list is cycled through as many times as needed. For instance, if seedList=[1,2,3] and there are 5 games,
      the seed for game 1 is 1, game 2 is 2, game 3 is 3, game 4 is 1, and game 5 is 2.
    - "randomFromPool": Seeds are randomly chosen from a provided list of seeds. If the list is empty but randomPoolSize > 0,
      a pool of random seeds is generated to choose from. For instance, if seedList=[10,20,30], each game's seed is randomly picked from these three values.
      So if there are 4 games, possible seeds could be [20,10,30,20]. If seedList=[] and randomPoolSize=5,
      a pool of 5 random seeds is generated and each game's seed is randomly picked from that pool.
    - "fullyRandom": Each game uses a completely random seed, meaning no specific seed is assigned and scenarioGenerator.generateRandomScenario
      will be called with randomSeed=None.
    """

    def __init__(
        self,
        seedMode: str = "fullyRandom",
        fixedSeed: Optional[int] = None,
        seedList: Optional[List[int]] = None,
        randomPoolSize: int = 0
    ) -> None:
        """
        Initializes the seed picker with the specified mode and parameters.

        Args:
            seedMode (str): The mode for selecting seeds. One of "fixed", "sequential", "randomFromPool", "fullyRandom".
            fixedSeed (Optional[int]): The fixed seed to use if seedMode is "fixed".
            seedList (Optional[List[int]]): The list of seeds to use if seedMode is "sequential" or "randomFromPool".
            randomPoolSize (int): The size of the random pool to generate if seedMode is "randomFromPool" and seedList is empty.

        Raises:
            ValueError: If an invalid seed mode is provided.
        """

        validModes = {"fixed", "sequential", "randomFromPool", "fullyRandom"}
        # Better be in valid modes or else
        if seedMode not in validModes:
            raise ValueError(f"Invalid seed mode '{seedMode}'. Valid modes: {validModes}.")
        
        self.seedMode = seedMode
        self.fixedSeed = fixedSeed
        self.seedList = list(seedList) if seedList else []
        self.randomPoolSize = randomPoolSize
        self.randomPool: List[int] = []

    def generateSeeds(self, roundCount: int) -> List[Optional[int]]:
        """
        Produces a list of seeds, one per round.
        This is based on the seed mode and parameters provided at initialization.

        Args:
            roundCount (int): The number of rounds/games to generate seeds for.

        Returns:
            List[Optional[int]]: A list of seeds for each round. None indicates a fully random seed.
        """
        seeds: List[Optional[int]] = []
        if self.seedMode == "fixed":

            # If the fixed seed is set to None, yet we are in fixed mode, that's an error
            if self.fixedSeed is None:
                raise ValueError("Fixed seed mode requires a fixed seed value.")
            
            # Set every game to the fixed seed
            seeds = [self.fixedSeed for _ in range(roundCount)]
        elif self.seedMode == "sequential":

            # If the seed list is empty, yet we are in sequential mode, that's an error
            if not self.seedList:
                raise ValueError("Sequential seed mode requires a non-empty seed list.")
            
            # Cycle through the seed list circularly to assign seeds
            for index in range(roundCount):
                seeds.append(self.seedList[index % len(self.seedList)])
        elif self.seedMode == "randomFromPool":
            # Build the pool of seeds to choose from
            pool = list(self.seedList)

            # In case no seeds were provided, generate a random pool
            # We will use seeds between 0 and 2^31-1 to give the maximum range of possible seeds
            if not pool and self.randomPoolSize > 0:
                pool = [random.randint(0, 2 ** 31 - 1) for _ in range(self.randomPoolSize)]

            # If we have neither provided seeds nor a pool size, yet we are in random pool mode, that's an error
            if not pool:
                raise ValueError("Random pool seed mode requires seeds or a pool size.")
            
            for _ in range(roundCount):
                # Randomly pick a seed from the pool for each game
                # This is random selection with replacement,
                # so we could pick the same seed multiple times
                seeds.append(random.choice(pool))

            self.randomPool = pool
        else:
            # Fully random mode: all seeds are None
            seeds = [None for _ in range(roundCount)]
        return seeds

    def describe(self) -> str:
        """
        Generates a human-readable description of the seed configuration.
        Used for the final tournament summary generated when a tournament completes.

        Returns:
            str: A description of the seed configuration.
        """
        if self.seedMode == "fixed":
            return f"fixed seed {self.fixedSeed}"
        if self.seedMode == "sequential":
            return f"sequential seeds {self.seedList}"
        if self.seedMode == "randomFromPool":
            if self.seedList:
                return f"randomly chosen from {self.seedList}"
            if self.randomPool:
                return f"randomly chosen from {self.randomPool}"
            return f"randomly chosen from generated pool of {self.randomPoolSize} seeds"
        return "fully randomized seeds"
