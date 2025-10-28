from ai.doNothingAgent import playTurn as doNothingPlayTurn
from ai.simpleRuleBasedAgent.mark1SRB import playTurn as mark1PlayTurn
from ai.simpleRuleBasedAgent.mark2SRB import playTurn as mark2PlayTurn

class AIPersonality:
    """Represents a single AI personality that can be used to play a faction's turns."""

    # Mapping from all currently supported AI types to their play turn implementations
    implementedAIs = {
        "donothing": doNothingPlayTurn,
        "mark1srb":  mark1PlayTurn,
        "mark2srb":  mark2PlayTurn
    }
    
    def __init__(self, displayName: str, aiType: str) -> None:
        """
        Initializes a new AI personality with the given display name and AI type.

        Args:
            displayName (str): The name to display for this AI personality.
            aiType (str): The type of AI logic to use for this personality.
        
        Raises:
            ValueError: If the AI type is not supported.
        """
        if aiType not in AIPersonality.implementedAIs:
            raise ValueError(f"Unknown AI type '{aiType}'.")
        self.displayName = displayName
        self.aiType = aiType
