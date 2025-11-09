import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

def load_palette():
    # Define a placeholder palette (modify this to match the game's actual colors)
    return np.array([
        [0, 0, 0], [255, 255, 255], [128, 128, 128], [255, 0, 0],
        [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 165, 0],
        [128, 0, 128], [0, 255, 255], [192, 192, 192], [64, 64, 64],
        [128, 128, 0], [0, 128, 128], [128, 0, 0], [0, 128, 0]
    ], dtype=np.uint8)

def apply_palette_to_tile(tile, palette):
    return palette[tile]

def load_tile_rom(filename):
    with open(filename, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return data.reshape(-1, 8, 16)  # Tiles are 8x16 pixels

def load_map_rom(filename):
    with open(filename, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    maps = data.reshape(4, 64, 12)  # 4 maps, 64 columns, 12 rows
    return np.transpose(maps, (0, 2, 1))  # Rotate 90 degrees

def display_map(maps, all_tiles):
    palette = load_palette()
    tile_width, tile_height = 8, 16
    map_image = np.zeros((12 * tile_height, 64 * tile_width, 3), dtype=np.uint8)
    
    for row in range(12):
        for col in range(64):
            tile_index = maps[0, row, col]  # Display first map
            tile_image = apply_palette_to_tile(all_tiles[tile_index], palette)
            map_image[row * tile_height:(row + 1) * tile_height, col * tile_width:(col + 1) * tile_width] = tile_image
    
    plt.imshow(map_image)
    plt.axis("off")
    plt.show()

# Load data
all_tiles = np.concatenate([load_tile_rom(f'c{i}.{i}i') for i in range(1, 6)])
maps = load_map_rom('./c8.8i')

display_map(maps, all_tiles)
