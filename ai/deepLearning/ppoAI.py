from copy import deepcopy
import torch
from ai.deepLearning.AntiyoyEnv import AntiyoyEnv
from ai.deepLearning.ppoModel import ActorCritic
from ai.deepLearning.ppoModel import train_ppo, run_trained_policy, get_turn_moves


def playTurn(scenario, faction):
    env = AntiyoyEnv(scenario, 0)

    ### Uncomment this out to train model
    # train_ppo()
    # return []
    
    obs_dim = env._get_observation().shape[0]
    num_tiles = len(env.scenario.mapData) * len(env.scenario.mapData[0])
    num_move_actions = num_tiles * 6
    num_build_actions = num_tiles * 7
    action_dim = num_move_actions + num_build_actions + 1

    policy = ActorCritic(obs_dim, action_dim)
    policy.load_state_dict(torch.load("ppo_policy_final.pth"))

    moves_this_turn = get_turn_moves(env, policy)
    print("Moves selected this turn:", moves_this_turn)
  
    return moves_this_turn