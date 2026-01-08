import pygame
import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from map_env import MapEnv

# --- NEW: A More Robust Custom Callback for Logging and Plotting ---
class CustomCallback(BaseCallback):
    """
    A robust callback that records and plots training metrics.
    """
    def __init__(self, verbose=0):
        super(CustomCallback, self).__init__(verbose)
        self.timesteps_data = []
        self.rewards_data = []
        self.loss_data = []
        self.variance_data = []

    def _on_step(self) -> bool:
        # This method is called after each step in the environment
        # We check the logger for the mean reward, which is logged periodically
        if 'rollout/ep_rew_mean' in self.logger.name_to_value:
            reward = self.logger.name_to_value['rollout/ep_rew_mean']
            
            # Prevent duplicate entries for the same timestep
            if not self.timesteps_data or self.timesteps_data[-1] != self.num_timesteps:
                self.timesteps_data.append(self.num_timesteps)
                self.rewards_data.append(reward)

                # Training metrics are logged at the same time
                if 'train/loss' in self.logger.name_to_value:
                    self.loss_data.append(self.logger.name_to_value['train/loss'])
                if 'train/explained_variance' in self.logger.name_to_value:
                    self.variance_data.append(self.logger.name_to_value['train/explained_variance'])
        return True

    def plot(self):
        """
        Plots all the recorded metrics and saves to a file.
        """
        fig, axs = plt.subplots(1, 3, figsize=(20, 5))
        fig.suptitle('AI Training Metrics Over Time', fontsize=16)

        # Plot Mean Reward
        axs[0].plot(self.timesteps_data, self.rewards_data)
        axs[0].set_title('Mean Reward per Episode')
        axs[0].set_xlabel('Timesteps')
        axs[0].set_ylabel('Mean Reward')
        
        # Plot Loss
        if self.loss_data:
            axs[1].plot(self.timesteps_data, self.loss_data, color='red')
            axs[1].set_title('Training Loss')
            axs[1].set_xlabel('Timesteps')
            axs[1].set_ylabel('Loss')

        # Plot Explained Variance
        if self.variance_data:
            axs[2].plot(self.timesteps_data, self.variance_data, color='purple')
            axs[2].set_title('Explained Variance (Confidence)')
            axs[2].set_xlabel('Timesteps')
            axs[2].set_ylabel('Variance (1.0 is perfect)')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig("training_graphs.png")
        print("\n--- Training graphs saved to training_graphs.png ---")

# --- (The rest of the file is the same, but uses the callback) ---

# --- Training Configuration ---
PLAYER_START_TILE = (1, 16)
TMX_FILE = "sample1.tmx"
MODEL_SAVE_PATH = "ppo_agent_brain"

# --- YOUR CORRECT GIDs ---
ENEMY_GIDS = {48}
WALKABLE_GID = 8

pygame.init()
pygame.display.set_mode((1, 1))

print("Creating AI environment with final logic...")
env = MapEnv(
    tmx_file=TMX_FILE,
    player_start_tile=PLAYER_START_TILE,
    enemy_gids=ENEMY_GIDS,
    walkable_gid=WALKABLE_GID
)

env.save_vision_map()

# --- Create the callback instance ---
callback = CustomCallback()

print("Creating PPO model with CnnPolicy...")
model = PPO("CnnPolicy", env, verbose=1, gamma=0.95)

print("--- STARTING FINAL TRAINING (This will take several minutes) ---")
# --- Pass the callback to the learn method ---
model.learn(total_timesteps=10000, callback=callback)
print("--- TRAINING COMPLETE ---")

model.save(MODEL_SAVE_PATH)
print(f"Model saved successfully to {MODEL_SAVE_PATH}.zip")

# --- Plot the graphs after training is done ---
callback.plot()

pygame.quit()

