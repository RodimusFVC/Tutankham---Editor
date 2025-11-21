import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Define the ROM file and offsets
tile_roms = ["./c1.1i", "./c2.2i", "./c3.3i", "./c4.4i", "./c5.5i"]
map_rom_path = "./c8.8i"
tile_size = 16 * 8  # 16x8 pixels, based on your previous tiles
tiles_per_row = 16  # Adjust this based on the size of the ROM and desired grid width
num_maps = 4        # There Are FOUR maps
map_width = 64      # 64 tiles wide
map_height = 12     # 12 tiles tall
map_size = 0x300    # 768 bytes per map

# Define the palettes for each map
palettes = [
    # Palette for map 1
    [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 133, 133, 148), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 91, 162, 69)],
    # Palette for map 2
    [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 162, 000, 217), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 133, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 29, 195, 148)],
    # Map 3 Palette
    [(255, 000, 000, 000), (255, 91, 62, 69), (255, 000, 224, 000), (255, 162, 133, 000), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 62, 195, 217), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 224, 29, 148)],
    # Map 4 Palette
    [(255, 000, 000, 000), (255, 000, 000, 000), (255, 000, 224, 000), (255, 000, 000, 217), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 000, 000, 000)]
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
            all_tiles.append(rotated_tile)
    return all_tiles

# Extract the 4 maps from the map ROM (c8.8i)
def load_maps():
    map_data = read_rom(map_rom_path)
    maps = []
    
    for map_index in range(num_maps):  # Iterate over the 4 maps
        start_offset = map_index * map_size  # Each map is 0x300 bytes
        map_layout = np.zeros((map_height, map_width), dtype=np.uint8)  # 12 rows, 64 columns
        
        # Process the map byte-by-byte
        for byte_index in range(map_size):
            # Calculate which row and column this byte belongs to
            row = (byte_index % map_height)  # Ranges from 0 to 11 (12 rows)
            col = (byte_index // map_height)  # Ranges from 0 to 63 (64 columns)

            # Flip the rows (flip the row index)
            flipped_row = map_height - 1 - row

            map_layout[flipped_row, col] = map_data[start_offset + byte_index]  # Store the byte in the appropriate row, col
        
        maps.append(map_layout)
    return maps

# Function to update the map with the selected tile
def update_map(selected_tile, row, col, maps, selected_map):
    maps[selected_map][row, col] = selected_tile  # Update the selected map

# Display the map using the tiles
def display_map(maps, all_tiles, palettes, selected_map, canvas):
    raw_map_layout = maps[selected_map]
    rotated_map = raw_map_layout  # rotate_map(raw_map_layout)  # Correct map orientation
    
    map_image = np.zeros((rotated_map.shape[0] * 8, rotated_map.shape[1] * 16, 4), dtype=np.uint8)  # 8x16 per tile
    
    # Get the correct palette for this map
    palette = palettes[selected_map]

    # Loop through each tile in the map and apply the color
    for row in range(rotated_map.shape[0]):
        for col in range(rotated_map.shape[1]):
            tile_index = rotated_map[row, col]
            if tile_index != 0:  # 0 represents no tile (empty)
                tile = all_tiles[tile_index - 1]
                color_tile = apply_palette_to_tile(tile, palette)
                map_image[row * 8 : (row + 1) * 8, col * 16 : (col + 1) * 16, :] = color_tile

    # Create an image and display it on the canvas
    map_image_rgb = np.flip(map_image, axis=2)  # Flip the RGB channels for correct display
    map_image_tk = ImageTk.PhotoImage(image=Image.fromarray(map_image_rgb))
    canvas.create_image(0, 0, image=map_image_tk, anchor='nw')
    canvas.image = map_image_tk

# Create the GUI for map editing
def create_map_editor(maps, all_tiles, palettes):
    root = tk.Tk()
    root.title("Map Editor")
    
    # Set the tile size in the editor window
    TILE_WIDTH = 16
    TILE_HEIGHT = 16
    
    # Store the currently selected tile and map
    selected_tile = 1
    selected_map = 0  # Start with the first map

    def on_tile_click(tile_index):
        nonlocal selected_tile
        selected_tile = tile_index + 1  # Tile indices in the ROM are 1-based
    
    def on_map_select(map_index):
        nonlocal selected_map
        selected_map = map_index
        display_map(maps, all_tiles, palettes, selected_map, canvas)
    
    def on_map_click(event):
        col = event.x // (TILE_WIDTH * 16)
        row = event.y // (TILE_HEIGHT * 8)
        update_map(selected_tile, row, col, maps, selected_map)
        display_map(maps, all_tiles, palettes, selected_map, canvas)
    
    # Create a canvas to display the map
    canvas = tk.Canvas(root, width=TILE_WIDTH * map_width, height=TILE_HEIGHT * map_height)
    canvas.grid(row=0, column=0, columnspan=4)
    canvas.bind("<Button-1>", on_map_click)

    # Map selection buttons
    for i in range(num_maps):
        map_button = tk.Button(root, text=f"Map {i + 1}", command=lambda i=i: on_map_select(i))
        map_button.grid(row=1, column=i)

    # Display tiles as buttons
    for i, tile in enumerate(all_tiles):
        row = i // 10
        col = i % 10
        tile_button = tk.Button(root, text=f"Tile {i+1}", command=lambda i=i: on_tile_click(i))
        tile_button.grid(row=row + 2, column=col)
    
    # Start by displaying the first map
    display_map(maps, all_tiles, palettes, selected_map, canvas)

    root.mainloop()

# Load all tiles and maps
all_tiles = load_tiles()
maps = load_maps()

# Create the editor
create_map_editor(maps, all_tiles, palettes)
