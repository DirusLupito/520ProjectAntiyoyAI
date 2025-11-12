# MINIMAX ALGORITHM
#Mac Gagne


"""
Represents a simple minimax agent which reccomends the next maximal move for the current turn in question.

As with all AIs designed for this project,
they must implement one simple function called
playTurn which takes in the various variables
representing the game state and returns a list
of Actions (allActions) and the associated province to run
those actions on.

(1) Built off of Mark2's playTurn
(2) Incoorporates functions:
    (2.1) minimax_decisions operates the full minimax algorithm with recursion
    (2.2) max_value obtains the maximum value for this turn that we need to operate minimax
    (2.3) min_value obtains the minimum value we need to operate minimax 
    (2.4) actions to develop a list of all possible (limited) available actions that can be taken.
          pre-limited actions excuses the need for an is_terminal function in minimax  
    (2.5) result to obtain the amount of resources a particular action obtains
"""


# clone scenario here

import random
from ai.utils.commonAIUtilityFunctions import findPathToClosestTileAvoidingGivenTiles
from ai.utils.commonAIUtilityFunctions import getAllMovableUnitTilesInProvince
from ai.utils.commonAIUtilityFunctions import getFrontierTiles
from ai.utils.commonAIUtilityFunctions import getTilesInProvinceWhichContainGivenUnitTypes
from ai.utils.commonAIUtilityFunctions import getTilesWhichUnitCanBeBuiltOnGivenTiles
from ai.utils.commonAIUtilityFunctions import getSubsetOfTilesWithMatchingDefenseRating
from game.commonAIUtilityFunctions import ScenarioCloner

def playTurn(scenario, faction):
    """
    Generates a list of actions for the AI's turn based on a simple set of rules.

    Args:
        scenario: The current game Scenario object.
        faction: The Faction object for which to play the turn.

    Returns:
        A list of (Action, province) tuples to be executed called allActions.
    """
    allActions = []

    # We start by cloning the input scenario:
    scenario = scenario.clonedScenario


    # Rather than the potentially unsafe method of going through all provinces
    # at once in the Mark 1, we shall instead create actions similar to how
    # a human player would, by selecting an individual province, doing all
    # the actions for that province (including potentially extra actions
    # if a merge happens which allows for more funding and more unit movement),
    # and then moving on to the next province, taking care to skip inactive provinces
    # and provinces eradicated by potential merges of previous actions.
    notDoneWithCurrentProvince = len(faction.provinces) > 0
    provinceIndex = 0
    moveAUnitThisIteration = False
    buildAUnitThisIteration = False
    while notDoneWithCurrentProvince:
        if provinceIndex >= len(faction.provinces):
            break # No more provinces to process
        province = faction.provinces[provinceIndex]
        provinceIndex += 1

        # Keeps track of whether we moved or built a unit this iteration
        # and therefore if a merge might have happened.
        # If we have moveable units after an iteration where we never
        # moved or built a unit, then we probably can't move a unit,
        # so we need to move on to the next province.
        moveAUnitThisIteration = False
        buildAUnitThisIteration = False

        if not province or not province.active:
            continue # Skip inactive provinces

        # Similar to rule 1 from Mark 1: Move units
        # We shall either move to the closest unclaimed tile or tree tile,
        # or move towards the closest such tile if out of range.
        movableUnits = getAllMovableUnitTilesInProvince(province)

        treeTiles = getTilesInProvinceWhichContainGivenUnitTypes(province, ["tree"])

        frontierTiles = getFrontierTiles(province)

        validTargets = set(frontierTiles).union(set(treeTiles))

        soldierTilesToAvoid = set(getTilesInProvinceWhichContainGivenUnitTypes(province, ["soldierTier1", "soldierTier2", "soldierTier3", "soldierTier4"]))

    ############################################################################################################################################################
    # DEFINE MINIMAX FUNCTIONS

    # The core run function for executing minimax
    def minimax_decisions(movableUnits, soldierTilesToAvoid, province):
        v = max_value(movableUnits, soldierTilesToAvoid, province) # run max-value, which iterativly runs min-value recursivly 
        return optival # return the action associated with the minimax derived action

    # Obtains maximized value for current player and sets recursion in action
    def max_value(movableUnits, soldierTilesToAvoid, province):

        v = float('-inf') # set initial v to -infinity

        actions_dictionary = actions(movableUnits, soldierTilesToAvoid, province) # obtain actions dictionary accordingly

        for action in actions_dictionary.keys(): # for possible actions provided in the dictionary as keys...
            mm1 = min_value(result(province, action), soldierTilesToAvoid, province) # run min value to obtain the minimized action paired with its resources quantity
            v = max(v, mm1) # return the maximum, either initialized v or the mm1 value calculated above. 

            global optival
            optival = a 

            return v

    # Continues recursion accordingly, minimizing node-based option
    def min_value(movableUnits, soldierTilesToAvoid, province):

        v = float('inf') # set initial v to infinity

        actions_dictionary = actions(movableUnits, soldierTilesToAvoid, province) #obtain actions dictionary accordingly 

        for action in actions_dictionary.keys(): # for possible actions provided in the dictionary...
            mm2 = max_value(result(province, action), soldierTilesToAvoid, province) # run max value to obtain the maximized action paired with its resources quantity
            v = min(v, mm2) # return the minimum, either initialiized v or the mm2 value calculated above

            return v

    # Given a state and which player is operating, return all possible actions as a key in a dictionary paired with its resulting value
    # By using movableUnits, we're already capping off how many states we will investigate.
    # This means there is no need for an is_terminal function
    def actions(movableUnits, soldierTilesToAvoid, province):

        possible_actions_dict = {}

        for move in movableUnits: #for each possible move in the closed set of movableUnits...
            if move in soldierTilesToAvoid:
                pass #do not consider move if it is in soldierTilesToAvoid, furthernarrowing closed set
            else:
                possible_actions_dict[move] = result(province, move) #add key, value pair to initialized dictionary where action as 'move' as a key is paired with its resulting amount of resources 
    
        return possible_actions_dict

    # Provide the resulting amount of resources for a given action
    def result(province, move):
        
        # enact provided action as 'move' and, based on provided province, obtain the resources gained as a computational score for minimax 
        resulting_action_resources = scenario.applyAction(move, province).resources #move takes the place of buildAction in this scenario.applyAction

        return resulting_action_resources


    ############################################################################################################################################################
    # RUN MINIMAX
    # Below we put the minimax functions initiliazed above into action by running them on the provided elements already outline in playTurn
    
    action_to_take = minimax_decisions(movableUnits, soldierTilesToAvoid, province) # Run minimax decisions, which starts the minimax algorithm running and produces an optimal action to reccomend 
    allActions = action_to_take # alternativly, allActions.append(action_to_take) if want to return a list of possible actions with earlier rules discussed    

    # Invert all actions to restore the original scenario state
    # If we have already cloned the scenario, does this need to be restored/wiped? 
    for action, province in reversed(allActions):
        scenario.applyAction(action.invert(), province)

    return allActions