import numpy as np
import matplotlib.pyplot as plt

# Define the ROM file and offsets
tile_roms = ["./c1.1i", "./c2.2i", "./c3.3i", "./c4.4i", "./c5.5i"]
map_rom_path = "./c8.8i"
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
            color_index = (tile[y, x] - 1) // 16  # Adjusted color index mapping
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

# Load all the tile ROMs and extract tiles
def load_tiles():
    all_tiles = []
    for rom in tile_roms:
        rom_data = read_rom(rom)
        num_tiles = len(rom_data) // tile_size
        for i in range(num_tiles):
            offset = i * tile_size
            tile = extract_tile(rom_data, offset)
            rotated_tile = rotate_tile(tile)
            color_tile = apply_palette_to_tile(rotated_tile, palette)
            all_tiles.append(color_tile)
    return all_tiles

# Extract the 4 maps from the map ROM (c8.8i)
def load_maps():
    map_data = read_rom(map_rom_path)
    maps = []
    for map_index in range(4):  # There are 4 maps
        start_offset = map_index * 0x300  # Each map is 0x300 bytes
        map_layout = np.zeros((12, 16), dtype=np.uint8)  # 12 tiles wide, 16 tiles tall
        for i in range(12):  # Read 12 bytes for each row (12 tiles wide)
            map_layout[i] = map_data[start_offset + i * 16 : start_offset + (i + 1) * 16]
        maps.append(map_layout)
    return maps

# Rotate the tile 90 degrees counterclockwise (to match map rotation)
def rotate_tile(tile):
    return np.rot90(tile, k=3)  # k=3 means 270 degrees counterclockwise (matching 90-degree map rotation)

# Display the map using the tiles
def display_map(maps, all_tiles):
    fig, ax = plt.subplots(4, 1, figsize=(12, 24))  # Display 4 maps in one column
    
    for map_index, map_layout in enumerate(maps):
        ax[map_index].axis('off')  # Hide axis for cleaner display
        map_image = np.zeros((map_layout.shape[0] * 8, map_layout.shape[1] * 16, 4), dtype=np.uint8)  # 8x16 per tile
        
        for row in range(map_layout.shape[0]):
            for col in range(map_layout.shape[1]):
                tile_index = map_layout[row, col]  # This is the tile index in the ROM
                tile = all_tiles[tile_index]
                # Place the rotated tile in the corresponding position on the map
                map_image[row*8:(row+1)*8, col*16:(col+1)*16] = tile
        
        ax[map_index].imshow(map_image)
        ax[map_index].set_title(f"Map {map_index + 1}")
    
    plt.tight_layout()
    plt.show()


# Main execution
all_tiles = load_tiles()
maps = load_maps()
display_map(maps, all_tiles)
