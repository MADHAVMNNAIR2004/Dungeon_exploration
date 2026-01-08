# FILE: map_env.py
import gymnasium as gym
import numpy as np
import pytmx
import pygame
import math

class MapEnv(gym.Env):
    def __init__(self, tmx_file, player_start_tile, enemy_gids, walkable_gids):
        super(MapEnv, self).__init__()
        
        self.tiled_map = pytmx.load_pygame(tmx_file)
        self.map_width = self.tiled_map.width
        self.map_height = self.tiled_map.height

        self.action_space = gym.spaces.Discrete(4) 
        self.observation_space = gym.spaces.Box(
            low=0, high=255, 
            shape=(3, self.map_height, self.map_width),
            dtype=np.uint8
        )
        
        self.start_pos = player_start_tile
        self.player_pos = self.start_pos
        
        self.enemy_locations = []
        
        self.wall_matrix = np.ones((self.map_height, self.map_width), dtype=np.uint8)
        self.goal_matrix = np.zeros((self.map_height, self.map_width), dtype=np.uint8)

        for layer in self.tiled_map.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    if gid in walkable_gids:
                        self.wall_matrix[y, x] = 0
                    elif gid in enemy_gids:
                        self.wall_matrix[y, x] = 0
                        self.goal_matrix[y, x] = 255
                        self.enemy_locations.append((x, y))
                    else:
                        # Mark all other tiles as walls
                        self.wall_matrix[y, x] = 1

        self.last_distance = self._get_distance_to_nearest_enemy()

    def _get_distance_to_nearest_enemy(self):
        player_x, player_y = self.player_pos
        if not self.enemy_locations: return float('inf')
        distances = [math.sqrt((player_x - ex)**2 + (player_y - ey)**2) for ex, ey in self.enemy_locations]
        return min(distances)

    def _get_observation(self):
        player_matrix = np.zeros((self.map_height, self.map_width), dtype=np.uint8)
        px, py = self.player_pos
        if 0 <= py < self.map_height and 0 <= px < self.map_width:
            player_matrix[py, px] = 255
        return np.stack([self.wall_matrix * 255, player_matrix, self.goal_matrix])

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.player_pos = self.start_pos
        self.last_distance = self._get_distance_to_nearest_enemy()
        return self._get_observation(), {}

    def step(self, action):
        x, y = self.player_pos
        print(f"Step called with action: {action}, current position: {self.player_pos}")  # Debug
        if action == 0: y -= 1
        elif action == 1: y += 1
        elif action == 2: x -= 1
        elif action == 3: x += 1
            
        done = False
        
        if not (0 <= y < self.map_height and 0 <= x < self.map_width):
            print(f"Attempted move out of bounds to {(x,y)}")  # Debug
            reward = -5
        elif self.wall_matrix[y, x] == 1:
            print(f"Attempted move into wall at {(x,y)}")  # Debug
            reward = -5
        else:
            self.player_pos = (x, y)
            new_distance = self._get_distance_to_nearest_enemy()
            print(f"Moved to {(x,y)}, new distance to enemy: {new_distance}, last distance: {self.last_distance}")  # Debug
            
            if new_distance < self.last_distance:
                reward = 1.0 
            else:
                reward = -0.5
            
            self.last_distance = new_distance

        if self.goal_matrix[self.player_pos[1], self.player_pos[0]] == 255:
            reward = 100.0 
            done = True

        return self._get_observation(), reward, done, False, {}

    def save_vision_map(self, filename="debug_map.png"):
        vision_map = np.full((self.map_height, self.map_width, 3), 255, dtype=np.uint8)
        vision_map[self.wall_matrix == 1] = [0, 0, 0]
        vision_map[self.goal_matrix == 255] = [255, 0, 0]
        surf = pygame.surfarray.make_surface(np.transpose(vision_map, (1, 0, 2)))
        pygame.image.save(surf, filename)
        print(f"--- Saved AI vision map to {filename} ---")