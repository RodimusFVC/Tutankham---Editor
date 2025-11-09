import numpy as np
import matplotlib.pyplot as plt

# Define the ROM file and offsets
rom_paths = ["./c1.1i", "./c2.2i", "./c3.3i", "./c4.4i", "./c5.5i", "./c8.8i"]  # Including c8.8i for maze layout
tile_size = 16 * 8  # 16x8 pixels, based on your previous tiles
tiles_per_row = 16  # Adjust this based on the size of the ROM and desired grid width

# Define the palette (adjusted ARGB format)
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

# Read the ROM file
def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

# Extract a single tile from the ROM
def extract_tile(rom_data, offset, width=8, height=16):
    tile = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        byte_row = rom_data[offset + (y * width) : offset + ((y + 1) * width)]
        tile[y, :] = [bit for bit in byte_row]  # Store the row
    return tile

# Rotate the tile 90 degrees counterclockwise
def rotate_tile(tile):
    return np.rot90(tile, k=1)  # k=1 means 90 degrees counterclockwise

# Apply the color palette to a tile
def apply_palette_to_tile(tile, palette):
    height, width = tile.shape
    color_tile = np.zeros((height, width, 4), dtype=np.uint8)  # 4 channels for RGBA
    for y in range(height):
        for x in range(width):
            color_index = max(0, min(tile[y, x] - 1, 255)) // 16
            if 0 <= color_index < len(palette):  # Ensure the index is valid
                color_tile[y, x] = [
                    palette[color_index][1],  # Red
                    palette[color_index][2],  # Green
                    palette[color_index][3],  # Blue
                    palette[color_index][0]   # Alpha
                ]
            else:
                print(f"Warning: Invalid color index {color_index} at ({x}, {y})")
    return color_tile

# Load all tile sprites (from c1.1i to c5.5i)
def load_all_tiles(rom_paths):
    tiles = []
    for rom_path in rom_paths[:5]:  # Only load the first five files (tile files)
        rom_data = read_rom(rom_path)
        num_tiles = len(rom_data) // tile_size
        for i in range(num_tiles):
            offset = i * tile_size
            tile = extract_tile(rom_data, offset)
            rotated_tile = rotate_tile(tile)
            color_tile = apply_palette_to_tile(rotated_tile, palette)
            tiles.append(color_tile)
    return tiles

# Load the maze layout from c8.8i
def load_maze_layout(maze_rom_path):
    rom_data = read_rom(maze_rom_path)
    maze_layout = np.zeros((16, 12), dtype=np.uint8)  # Assuming the maze is 12 bytes wide, 16 rows
    for row in range(16):
        for col in range(12):
            byte = rom_data[row * 12 + col]  # Adjust this index based on how the data is structured
            maze_layout[row, col] = byte
    return maze_layout

# Map maze data to sprite tiles
def map_maze_to_sprites(maze_layout, tile_sprites):
    maze_with_tiles = np.zeros((16, 12, 16, 8, 4), dtype=np.uint8)  # Adjust for sprite tile dimensions
    for row in range(16):
        for col in range(12):
            sprite_index = maze_layout[row, col]  # Map to the corresponding tile
            maze_with_tiles[row, col] = tile_sprites[sprite_index]
    return maze_with_tiles

# Display the maze
def display_maze(maze_with_tiles):
    fig, ax = plt.subplots(16, 12, figsize=(12, 16))
    ax = ax.flatten()  # Flatten the axis array for easy iteration
    for i in range(16 * 12):
        row = i // 12
        col = i % 12
        ax[i].imshow(maze_with_tiles[row, col])
        ax[i].axis('off')  # Hide axis for cleaner display
    plt.tight_layout()
    plt.show()

# Main execution
tile_sprites = load_all_tiles(rom_paths)  # Load all tiles
maze_layout = load_maze_layout(rom_paths[5])  # Load the maze layout from c8.8i
maze_with_tiles = map_maze_to_sprites(maze_layout, tile_sprites)  # Map maze data to sprite tiles
display_maze(maze_with_tiles)  # Display the maze layout
