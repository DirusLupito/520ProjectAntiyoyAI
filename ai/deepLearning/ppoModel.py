import math
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np

from ai.deepLearning.AntiyoyEnv import AntiyoyEnv
from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction

class ActorCritic(nn.Module):
    def __init__(self, obs_dim, action_dim):
        super().__init__()
        self.fc1 = nn.Linear(obs_dim, 512)
        self.fc2 = nn.Linear(512, 256)

        self.action_head = nn.Linear(256, action_dim)
        self.value_head = nn.Linear(256, 1)

    def forward(self, x, valid_action_mask=None):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))

        logits = self.action_head(x)
        if valid_action_mask is not None:
            logits = logits.masked_fill(~valid_action_mask, -1e9)  # mask invalid actions

        value = self.value_head(x).squeeze(-1)
        return logits, value

def compute_gae(rewards, values, masks, gamma=0.99, lam=0.95):
    returns = []
    advantages = []
    gae = 0
    next_value = 0
    for step in reversed(range(len(rewards))):
        delta = rewards[step] + gamma * next_value * masks[step] - values[step]
        gae = delta + gamma * lam * masks[step] * gae
        advantages.insert(0, gae)
        next_value = values[step]
        returns.insert(0, gae + values[step])
    return returns, advantages

def ppo_update(policy, optimizer, states, actions, old_log_probs, returns, advantages, valid_masks,
               clip_epsilon=0.2, epochs=4, batch_size=64):
    policy.train()
    states = torch.cat(states)
    actions = torch.cat(actions)
    old_log_probs = torch.cat(old_log_probs)
    returns = torch.tensor(returns, dtype=torch.float32)
    advantages = torch.tensor(advantages, dtype=torch.float32)
    valid_masks = torch.cat(valid_masks)

    if advantages.numel() <= 1:
        # No normalization possible; just zero it out
        advantages = torch.zeros_like(advantages)
    else:
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    dataset_size = states.size(0)
    for _ in range(epochs):
        for start in range(0, dataset_size, batch_size):
            end = start + batch_size
            batch_states = states[start:end]
            batch_actions = actions[start:end]
            batch_old_log_probs = old_log_probs[start:end]
            batch_returns = returns[start:end]
            batch_advantages = advantages[start:end]
            batch_masks = valid_masks[start:end]

            logits, values = policy(batch_states, valid_action_mask=batch_masks)
            dist = Categorical(logits=logits)

            new_log_probs = dist.log_prob(batch_actions)
            entropy = dist.entropy().mean()

            ratio = torch.exp(new_log_probs - batch_old_log_probs)
            surr1 = ratio * batch_advantages
            surr2 = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * batch_advantages
            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = F.mse_loss(values, batch_returns)
            loss = actor_loss + 0.5 * critic_loss - 0.05 * entropy

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

def train_ppo(num_episodes=400000, max_steps=50, checkpoint_path=""):
    factions = []
    factions.append(Faction(name="Red", color="Red", playerType="ai", aiType="ppo"))
    factions.append(Faction(name="Blue", color="Blue", playerType="ai", aiType="mark2srb"))
    scenario = generateRandomScenario(4, 16, factions, 4, 1)
    env = AntiyoyEnv(scenario, 0)

    obs_dim = env._get_observation().shape[0]

    policy = ActorCritic(obs_dim, env.action_space_size)
    optimizer = optim.Adam(policy.parameters(), lr=3e-4)

    # Load checkpoint if exists to continue training
    if os.path.exists(checkpoint_path):
        print(f"Loading checkpoint from {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path)
        policy.load_state_dict(checkpoint['policy_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        # start_episode = checkpoint.get('episode', 0) + 1
        # print(f"Resuming training from episode {start_episode}")
    else:
        # start_episode = 0
        print("Starting training from scratch")

    gamma = 0.99
    lam = 0.95

    won = 0
    tie = 0

    for episode in range(num_episodes):
        factions = []
        # Generate new game every episode
        if episode % 2 == 0:
            factions.append(Faction(name="Red", color="Red", playerType="ai", aiType="ppo"))
            factions.append(Faction(name="Blue", color="Blue", playerType="ai", aiType="mark2srb"))
            scenario = generateRandomScenario(4, 16, factions, 4, randomSeed=episode) # we can fix this seed if we want to train on the same board
            env = AntiyoyEnv(scenario, 0)
        else:
            factions.append(Faction(name="Blue", color="Blue", playerType="ai", aiType="mark2srb"))
            factions.append(Faction(name="Red", color="Red", playerType="ai", aiType="ppo"))
            scenario = generateRandomScenario(4, 16, factions, 4, randomSeed=episode) # we can fix this seed if we want to train on the same board
            env = AntiyoyEnv(scenario, 1)

        obs = env._get_observation()
        done = False
        step = 0

        states = []
        actions = []
        rewards = []
        masks = []
        old_log_probs = []
        valid_masks = []
        values = []

        while not done and step < max_steps:
            obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
            mask_tensor = env.compute_valid_action_mask()
            logits, value = policy(obs_tensor, valid_action_mask=mask_tensor.unsqueeze(0))
            dist = Categorical(logits=logits)

            action = dist.sample()
            log_prob = dist.log_prob(action)

            next_obs, reward, done, info, m = env.step(action.item())

            # env.render()

            winner = None
            if done:
                for faction in factions:
                    if any(province.active for province in faction.provinces):
                        winner = faction
                        break
                
                if winner:
                    win_bonus = 30.0
                    lose_penalty = 10.0
                    progress = 1.0 - (step / max_steps)
                    reward_bonus = win_bonus * progress
                    T = len(rewards)

                    # Linear weights: 1, 2, 3, ..., T
                    weights = torch.arange(1, T + 1, dtype=torch.float32)
                    weights = weights / weights.sum()  # normalize to sum to 1
                    # Add winner bonus that decreases as games go longer
                    if winner.name == "Red":
                        # Apply weighted bonus
                        for i in range(T):
                            rewards[i] += reward_bonus * weights[i].item()
                        # bonus_per_step = reward_bonus / len(rewards)

                        # for i in range(len(rewards)):
                        #     rewards[i] += bonus_per_step
                    else:
                        for i in range(T):
                            rewards[i] -= lose_penalty * weights[i].item()
            # elif step == max_steps - 1:
            #     rewards[-1] -= 1000.0

            # Store step info
            states.append(obs_tensor)
            actions.append(action)
            rewards.append(reward)
            masks.append(1 - done)
            old_log_probs.append(log_prob.detach())
            valid_masks.append(mask_tensor.unsqueeze(0))
            values.append(value.item())

            obs = next_obs
            step += 1
            env.turn += 1

        # If max steps hit without done, forcibly end episode
        if step == max_steps and not done:
            done = True
            print(f"\033[33mEpisode {episode + 1} max steps reached, total reward: {sum(rewards)}")
            tie += 1
        else:
            winner = None
            for faction in factions:
                if any(province.active for province in faction.provinces):
                    winner = faction
                    break
            
            if winner:
                if winner.name == "Red":
                    won += 1
                    print(f"\033[32mEpisode {episode + 1} complete, total reward: {sum(rewards)}")
                else:
                    print(f"\033[31mEpisode {episode + 1} complete, total reward: {sum(rewards)}")

        # Compute returns and advantages
        if math.isnan(reward) or math.isinf(reward):
            reward = 0.0
        returns, advantages = compute_gae(rewards, values, masks, gamma, lam)

        # PPO update
        ppo_update(policy, optimizer, states, actions, old_log_probs, returns, advantages, valid_masks)

        

    # Final save
    print(f"\033[0mNumber of games won by PPO: {won}. Number of games tied: {tie}. Winrate: {float(won)/float(num_episodes-tie)}")
    torch.save({
        "policy_state_dict": policy.state_dict(),
        "optimizer_state_dict": optimizer.state_dict()
    }, "ppo_checkpoint.pth")
    print("Training complete. Model saved to ppo_policy_final.pth")

def run_trained_policy(env, model_path, max_steps=100):
    obs_dim = env._get_observation().shape[0]
    num_tiles = len(env.scenario.mapData) * len(env.scenario.mapData[0])

    policy = ActorCritic(obs_dim, env.action_space_size)
    policy.load_state_dict(torch.load(model_path))
    policy.eval()  # Set to eval mode

    obs = env._get_observation()
    done = False
    step = 0
    total_reward = 0

    while not done and step < max_steps:
        obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
        mask_tensor = env.compute_valid_action_mask()
        with torch.no_grad():
            logits, _ = policy(obs_tensor, valid_action_mask=mask_tensor.unsqueeze(0))
            dist = torch.distributions.Categorical(logits=logits)
            action = dist.sample()

        next_obs, reward, done, info, _ = env.step(action.item())
        env.render()

        obs = next_obs
        total_reward += reward
        step += 1

    print(f"Episode finished after {step} steps with total reward {total_reward}")

def get_turn_moves(env, policy, faction):
    """
    Runs the policy on the given env, collecting moves until the end-turn action is selected.
    Returns a list of actions taken this turn.
    """
    policy.eval()
    moves = []
    obs = env._get_observation()
    done = False
    actions = []

    while not done:
        obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
        mask_tensor = env.compute_valid_action_mask()
        with torch.no_grad():
            logits, _ = policy(obs_tensor, valid_action_mask=mask_tensor.unsqueeze(0))
            dist = torch.distributions.Categorical(logits=logits)
            action = dist.sample().item()

        if action == len(mask_tensor) - 1:  # End turn action (last index)
            # Stop collecting moves this turn
            done = True
            for action, province in reversed(actions):
                # print(env.scenario.factions[0].provinces[0].resources)
                if province is None:
                    env.scenario.applyAction(action.invert())
                else:
                    env.scenario.applyAction(action.invert(), provinceDoingAction=province)
            # env.render()
        else:
            moves.append(action)
            # Apply the action but do NOT advance turns or do other factions yet
            obs, reward, done_flag, info, a = env.step(action)
            actions.extend(a)
            # print(mask_tensor)
            # env.render()

            done = done_flag  # Should be False here until turn ends or game ends

    return actions

if __name__ == "__main__":
    train_ppo(checkpoint_path="500kmark1.pth")
