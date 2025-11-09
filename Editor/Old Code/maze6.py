import numpy as np
import matplotlib.pyplot as plt

# Define the ROM file paths
map_rom_path = "./c8.8i"
tile_rom_paths = ["./c1.1i", "./c2.2i", "./c3.3i", "./c4.4i", "./c5.5i"]

tile_width = 8
tile_height = 16
map_width = 64  # 64 tiles wide
map_height = 12  # 12 tiles tall
num_maps = 4
map_size = 0x300  # 768 bytes per map

def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

# Load and extract all tiles from the tile ROMs
def load_all_tiles():
    all_tiles = []
    for rom_path in tile_rom_paths:
        rom_data = read_rom(rom_path)
        num_tiles = len(rom_data) // (tile_width * tile_height)
        for i in range(num_tiles):
            offset = i * tile_width * tile_height
            tile = extract_tile(rom_data, offset)
            all_tiles.append(tile)
    return all_tiles

# Extract a single tile from the ROM
def extract_tile(rom_data, offset):
    tile = np.zeros((tile_height, tile_width), dtype=np.uint8)
    for y in range(tile_height):
        byte_row = rom_data[offset + (y * tile_width): offset + ((y + 1) * tile_width)]
        tile[y, :] = [bit for bit in byte_row]
    return np.rot90(tile, k=1)  # Rotate 90 degrees to correct orientation

# Load and parse the maze data
def load_maze_data():
    rom_data = read_rom(map_rom_path)
    maps = []
    for i in range(num_maps):
        map_data = np.zeros((map_height, map_width), dtype=np.uint8)
        map_offset = i * map_size
        for col in range(map_width):  # Read 12-byte columns and store as rows
            for row in range(map_height):
                map_data[row, col] = rom_data[map_offset + col * map_height + row]
        maps.append(map_data)
    return maps

# Apply the color palette to a tile
def apply_palette_to_tile(tile, palette):
    height, width = tile.shape
    color_tile = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            color_index = max(0, min(tile[y, x] - 1, 255)) // 16
            if 0 <= color_index < len(palette):
                color_tile[y, x] = [palette[color_index][1], palette[color_index][2], palette[color_index][3], palette[color_index][0]]
    return color_tile

# Define the color palette
palette = [
    (255, 0, 0, 0),    # 00 - Black
    (255, 0, 0, 148),  # 01 - Dark Blue
    (255, 0, 224, 0),  # 02 - Green
    (255, 133, 133, 148), # 03 - Grey
    (255, 224, 162, 148), # 04 - Flesh
    (255, 162, 0, 217), # 05 - Purple
    (255, 224, 0, 0),  # 06 - Red
    (255, 133, 133, 148), # 07 - Grey
    (255, 224, 224, 0), # 08 - Yellow
    (255, 162, 29, 0),  # 09 - Dark Red
    (255, 224, 133, 0), # 10 - Orange
    (255, 224, 0, 148), # 11 - Pink
    (255, 0, 0, 217),  # 12 - Blue
    (255, 62, 195, 217), # 13 - Teal
    (255, 224, 224, 217), # 14 - White
    (255, 91, 162, 69)  # 15 - Dark Green
]

# Display the maze using extracted tiles
def display_map(maps, all_tiles):
    for map_index, maze in enumerate(maps):
        map_image = np.zeros((map_height * tile_height, map_width * tile_width, 4), dtype=np.uint8)
        for row in range(map_height):
            for col in range(map_width):
                tile_index = maze[row, col]
                if tile_index < len(all_tiles):
                    map_image[row * tile_height:(row + 1) * tile_height, col * tile_width:(col + 1) * tile_width] = apply_palette_to_tile(all_tiles[tile_index], palette)
        plt.figure(figsize=(10, 5))
        plt.imshow(map_image)
        plt.axis('off')
        plt.title(f"Maze {map_index + 1}")
        plt.show()

# Main execution
all_tiles = load_all_tiles()
maps = load_maze_data()
display_map(maps, all_tiles)
