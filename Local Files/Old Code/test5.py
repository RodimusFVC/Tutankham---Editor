import numpy as np
import matplotlib.pyplot as plt

# Define the 16-color palette (in RGBA format)
palette = [
    (255, 0, 0, 255),    # 00 - A:FF R:00 G:00 B:00 - Black
    (255, 0, 148, 148),  # 01 - A:FF R:00 G:00 B:94 - Dark Blue
    (255, 0, 224, 0),    # 02 - A:FF R:00 G:E0 B:00 - Green
    (255, 133, 133, 148),  # 03 - A:FF R:85 G:85 B:94 - Grey
    (255, 224, 162, 148),  # 04 - A:FF R:E0 G:A2 B:94 - Flesh
    (255, 162, 0, 217),    # 05 - A:FF R:A2 G:00 B:D9 - Purple
    (255, 224, 0, 0),      # 06 - A:FF R:E0 G:00 B:00 - Red
    (255, 133, 133, 148),  # 07 - A:FF R:85 G:85 B:94 - Grey
    (255, 224, 224, 0),    # 08 - A:FF R:E0 G:E0 B:00 - Yellow
    (255, 162, 29, 0),     # 09 - A:FF R:A2 G:1D B:00 - Dark Red
    (255, 224, 133, 0),    # 10 - A:FF R:E0 G:85 B:00 - Orange
    (255, 224, 0, 148),    # 11 - A:FF R:E0 G:00 B:94 - Pink
    (255, 0, 0, 217),      # 12 - A:FF R:00 G:00 B:D9 - Blue
    (255, 62, 195, 217),   # 13 - A:FF R:3E G:C3 B:D9 - Teal
    (255, 224, 224, 217),  # 14 - A:FF R:E0 G:E0 B:D9 - White
    (255, 91, 162, 69)     # 15 - A:FF R:5B G:A2 B:45 - Dark Green
]

# Define the ROM file and offsets
rom_path = "./c3.3i"  # Update with your actual ROM path
tile_offset = 0x500  # Starting offset of the known tile
tile_size = 16 * 8  # 16x8 pixels

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

# Apply the palette to the tile (convert indices to RGBA values)
def apply_palette_to_tile(tile_data, palette):
    height, width = tile_data.shape
    color_tile = np.zeros((height, width, 4), dtype=np.uint8)  # Create an RGBA tile

    for y in range(height):
        for x in range(width):
            color_index = tile_data[y, x]  # Get the color index for each pixel
            
            if color_index < len(palette):  # Ensure the index is within the palette range
                color_tile[y, x] = palette[color_index]  # Map the index to the palette color
            else:
                print(f"Warning: Invalid color index {color_index} at ({x}, {y})")  # Handle invalid index

    return color_tile

# Rotate the tile 90 degrees counterclockwise
def rotate_tile(tile):
    return np.rot90(tile, k=1)  # k=1 means 90 degrees counterclockwise

# Display the tile with the correct aspect ratio
def display_tile_with_aspect_ratio(tile, aspect_ratio=2):
    """ Display a tile with adjusted aspect ratio """
    plt.imshow(tile, interpolation="nearest")
    plt.gca().set_aspect(aspect_ratio)  # Adjust the aspect ratio
    plt.title("Extracted and Adjusted Tile")
    plt.show()

# Main execution
rom_data = read_rom(rom_path)
tile = extract_tile(rom_data, tile_offset)
rotated_tile = rotate_tile(tile)
color_tile = apply_palette_to_tile(rotated_tile, palette)

# Display the adjusted tile with color
display_tile_with_aspect_ratio(color_tile, aspect_ratio=2)
