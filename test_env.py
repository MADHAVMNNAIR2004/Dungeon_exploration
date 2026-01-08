# test_env.py

import os
import sys
import random
import pygame
from dungeon_env import DungeonEnv

# ----------------- CONFIG -----------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TILES_DIR = os.path.join(PROJECT_DIR, "kenney_tiny-dungeon", "Tiles")

MAP_W, MAP_H = 48, 36         # grid size (columns, rows)
TILE_SIZE = 16                # tile pixel size (matches sheet)

# Pick tiles from kenney_tiny-dungeon/Tiles
FLOOR_TILE = "tile_0000.png"
PATH_TILE = "tile_0016.png"
WALL_TILE = "tile_0024.png"
CASTLE_TILE = "tile_0085.png"
TREE_TILE = "tile_0035.png"
HERO_TILE = "tile_0098.png"
VILLAIN_TILE = "tile_0099.png"

OUTPUT_SNAPSHOT = os.path.join(PROJECT_DIR, "generated_map.png")
SEED = 42                     # change or None for randomness

# Room generation
N_ROOMS = 12
ROOM_MIN_W, ROOM_MAX_W = 5, 12
ROOM_MIN_H, ROOM_MAX_H = 4, 9

# ------------------------------------------

def load_tile(name):
    path = os.path.join(TILES_DIR, name)
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            if img.get_size() != (TILE_SIZE, TILE_SIZE):
                img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            return img
        except Exception as e:
            print("Failed to load", path, "->", e)
    return None

def rects_overlap(a, b, padding=1):
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw - 1, ay1 + ah - 1
    bx2, by2 = bx1 + bw - 1, by1 + bh - 1
    return not (ax2 + padding < bx1 or bx2 + padding < ax1 or ay2 + padding < by1 or by2 + padding < ay1)

def carve_h_corridor(grid, x1, x2, y, tile):
    for x in range(min(x1, x2), max(x1, x2)+1):
        grid[y][x] = tile

def carve_v_corridor(grid, y1, y2, x, tile):
    for y in range(min(y1, y2), max(y1, y2)+1):
        grid[y][x] = tile

def create_rooms_and_corridors(grid, floor_tile, path_tile):
    rooms = []
    attempts = 0
    while len(rooms) < N_ROOMS and attempts < N_ROOMS * 12:
        w = random.randint(ROOM_MIN_W, ROOM_MAX_W)
        h = random.randint(ROOM_MIN_H, ROOM_MAX_H)
        x = random.randint(1, MAP_W - w - 2)
        y = random.randint(1, MAP_H - h - 2)
        new_rect = (x, y, w, h)
        if any(rects_overlap(new_rect, r) for r in rooms):
            attempts += 1
            continue
        # carve room (floor)
        for ry in range(y, y+h):
            for rx in range(x, x+w):
                grid[ry][rx] = floor_tile
        rooms.append(new_rect)
        attempts += 1

    # connect rooms with corridors between centers
    for i in range(1, len(rooms)):
        (x1, y1, w1, h1) = rooms[i-1]
        (x2, y2, w2, h2) = rooms[i]
        c1 = (x1 + w1//2, y1 + h1//2)
        c2 = (x2 + w2//2, y2 + h2//2)
        if random.choice([True, False]):
            carve_h_corridor(grid, c1[0], c2[0], c1[1], path_tile)
            carve_v_corridor(grid, c1[1], c2[1], c2[0], path_tile)
        else:
            carve_v_corridor(grid, c1[1], c2[1], c1[0], path_tile)
            carve_h_corridor(grid, c1[0], c2[0], c2[1], path_tile)

    return rooms

def place_castle(grid, origin, castle_tile):
    ox, oy = origin
    size = 4
    for j in range(size):
        for i in range(size):
            x = ox + i
            y = oy + j
            if 0 <= x < MAP_W and 0 <= y < MAP_H:
                grid[y][x] = castle_tile

def add_decorations(grid, tree_tile, density=0.01):
    for y in range(MAP_H):
        for x in range(MAP_W):
            if random.random() < density and tree_tile:
                # don't overwrite path or rooms heavily; only place on floor (None or floor)
                grid[y][x] = tree_tile

def save_snapshot(surface, path):
    try:
        pygame.image.save(surface, path)
        print("Saved snapshot to", path)
    except Exception as e:
        print("Failed to save snapshot:", e)

def print_stats(obs):
    print(f"Position: ({obs['agent_pos'][0]}, {obs['agent_pos'][1]})")
    print(f"Health: {obs['health']}")
    print(f"Attack: {obs['attack_stat']}")
    print(f"Villain: {'Alive' if obs['villain_alive'] else 'Defeated'}")
    print("-" * 20)

def main():
    if SEED is not None:
        random.seed(SEED)

    pygame.init()
    screen = pygame.display.set_mode((MAP_W * TILE_SIZE, MAP_H * TILE_SIZE))
    pygame.display.set_caption("Improved Generated Map")
    clock = pygame.time.Clock()

    # load tiles
    floor_img = load_tile(FLOOR_TILE) or None
    path_img = load_tile(PATH_TILE) or None
    wall_img = load_tile(WALL_TILE) or None
    castle_img = load_tile(CASTLE_TILE) or None
    tree_img = load_tile(TREE_TILE) or None
    hero_img = load_tile(HERO_TILE)
    villain_img = load_tile(VILLAIN_TILE)

    # fallback colored surfaces
    def fallback(color):
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        s.fill(color)
        return s

    if floor_img is None: floor_img = fallback((100, 90, 60))
    if path_img is None: path_img = fallback((150, 130, 90))
    if castle_img is None: castle_img = fallback((120, 120, 200))
    if tree_img is None: tree_img = fallback((20, 100, 20))
    if hero_img is not None:
        hero_img = pygame.transform.scale(hero_img, (TILE_SIZE, TILE_SIZE))
    if villain_img is not None:
        villain_img = pygame.transform.scale(villain_img, (TILE_SIZE, TILE_SIZE))

    # initialize grid filled with a default darker floor
    grid = [[fallback((70, 60, 40)) for _ in range(MAP_W)] for _ in range(MAP_H)]

    rooms = create_rooms_and_corridors(grid, floor_img, path_img)

    # place two castles in two largest rooms (if available)
    if len(rooms) >= 2:
        # sort rooms by area descending
        rooms_sorted = sorted(rooms, key=lambda r: r[2]*r[3], reverse=True)
        # place castles near centers
        r1 = rooms_sorted[0]
        r2 = rooms_sorted[1]
        c1 = (r1[0] + r1[2]//2 - 1, r1[1] + r1[3]//2 - 1)
        c2 = (r2[0] + r2[2]//2 - 1, r2[1] + r2[3]//2 - 1)
        place_castle(grid, c1, castle_img)
        place_castle(grid, c2, castle_img)

    # decorations
    add_decorations(grid, tree_img, density=0.02)

    # spawn hero in first room center and villains in other room centers
    spawns = []
    if rooms:
        for idx, r in enumerate(rooms[:6]):
            cx = r[0] + r[2]//2
            cy = r[1] + r[3]//2
            spawns.append((cx, cy))
    hero_pos = list(spawns[0]) if spawns else [MAP_W//2, MAP_H//2]
    villain_positions = [list(p) for p in spawns[1:4]]

    running = True
    show_grid = True
    print("Generated map with", len(rooms), "rooms. Hero at", hero_pos, "villains:", villain_positions)
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_g:
                    show_grid = not show_grid
                elif ev.key == pygame.K_s:
                    save_snapshot(screen, OUTPUT_SNAPSHOT)
                elif ev.key == pygame.K_LEFT:
                    hero_pos[0] = max(0, hero_pos[0]-1)
                elif ev.key == pygame.K_RIGHT:
                    hero_pos[0] = min(MAP_W-1, hero_pos[0]+1)
                elif ev.key == pygame.K_UP:
                    hero_pos[1] = max(0, hero_pos[1]-1)
                elif ev.key == pygame.K_DOWN:
                    hero_pos[1] = min(MAP_H-1, hero_pos[1]+1)

        # draw grid tiles
        for y in range(MAP_H):
            for x in range(MAP_W):
                screen.blit(grid[y][x], (x*TILE_SIZE, y*TILE_SIZE))

        # draw villains and hero
        if villain_img:
            for vx, vy in villain_positions:
                screen.blit(villain_img, (vx*TILE_SIZE, vy*TILE_SIZE))
        else:
            for vx, vy in villain_positions:
                pygame.draw.rect(screen, (200, 20, 20), (vx*TILE_SIZE, vy*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        if hero_img:
            screen.blit(hero_img, (hero_pos[0]*TILE_SIZE, hero_pos[1]*TILE_SIZE))
        else:
            pygame.draw.rect(screen, (20, 200, 20), (hero_pos[0]*TILE_SIZE, hero_pos[1]*TILE_SIZE, TILE_SIZE, TILE_SIZE))

        if show_grid:
            color = (60, 60, 60)
            for gx in range(MAP_W + 1):
                pygame.draw.line(screen, color, (gx*TILE_SIZE, 0), (gx*TILE_SIZE, MAP_H*TILE_SIZE))
            for gy in range(MAP_H + 1):
                pygame.draw.line(screen, color, (0, gy*TILE_SIZE), (MAP_W*TILE_SIZE, gy*TILE_SIZE))

        pygame.display.flip()
        clock.tick(60)

    # save final snapshot on exit
    save_snapshot(screen, OUTPUT_SNAPSHOT)
    pygame.quit()
    print("Exited.")

if __name__ == "__main__":
    main()

def print_stats(obs):
    print(f"Position: ({obs['agent_pos'][0]}, {obs['agent_pos'][1]})")
    print(f"Health: {obs['health']}")
    print(f"Attack: {obs['attack_stat']}")
    print(f"Villain: {'Alive' if obs['villain_alive'] else 'Defeated'}")
    print("-" * 20)

if __name__ == '__main__':
    env = DungeonEnv(render_mode="human")
    obs, info = env.reset()
    done = False
    KEY_ACTION_MAP = {pygame.K_UP: 0, pygame.K_DOWN: 1, pygame.K_LEFT: 2, pygame.K_RIGHT: 3}

    print("Dungeon Environment - Test Controls:")
    print("  Arrow Keys = Move | R = Reset | ESC = Exit\n")
    print("Game Objective:")
    print("  - Find the sword to increase your attack")
    print("  - Find the potion to restore health")
    print("  - Defeat the villain, then find the exit to win!")
    print("-" * 40 + "\nStarting game...\n")
    print("Initial game state:")
    print_stats(obs)

    while True:
        env.render()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                env.close()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    obs, info = env.reset()
                    done = False
                    print("\n🔄 Environment Reset! 🔄\nNew game state:")
                    print_stats(obs)
                elif event.key in KEY_ACTION_MAP and not done:
                    action = KEY_ACTION_MAP[event.key]
                    obs, reward, done, truncated, info = env.step(action)
                    action_names = {0: "Up", 1: "Down", 2: "Left", 3: "Right"}
                    print(f"Action: {action_names.get(action, 'Unknown')}, Reward: {reward}")
                    print_stats(obs)
                    if done:
                        if env.health <= 0:
                            print("💀 Game Over! You were defeated. Press 'R' to try again. 💀")
                        elif env.steps_taken >= env.max_steps:
                            print("⏰ Time's up! Press 'R' to try again. ⏰")
                        else:
                            print("🎉 Victory! You've completed the dungeon! 🎉")