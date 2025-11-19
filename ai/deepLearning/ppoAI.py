from copy import deepcopy
import torch
from ai.deepLearning.AntiyoyEnv import AntiyoyEnv
from ai.deepLearning.ppoModel import ActorCritic
from ai.deepLearning.ppoModel import train_ppo, run_trained_policy, get_turn_moves

def playTurn(scenario, faction, train=False):
    # print(f"{faction.name}'s turn: index {scenario.factions.index(faction)}")
    env = AntiyoyEnv(scenario, scenario.factions.index(faction))

    ### Uncomment this out to train model
    if train:
        train_ppo(checkpoint_path="800kmark1.pth")
        return []
    
    obs_dim = env._get_observation().shape[0]

    policy = ActorCritic(obs_dim, env.action_space_size)
    checkpoint = torch.load("800kmark1.pth")
    policy.load_state_dict(checkpoint['policy_state_dict'])

    moves_this_turn = get_turn_moves(env, policy, scenario.factions.index(faction))
    # print("Moves selected this turn:", moves_this_turn)
  
    return moves_this_turn
