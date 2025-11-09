import numpy as np
import matplotlib.pyplot as plt

# Define the ROM file and offsets
rom_path = "./c3.3i"
tile_offset = 0x500  # Starting offset of the known tile
tile_size = 16 * 8  # 16x8 pixels
tiles_per_row = 16  # Number of tiles per row in the display grid
tile_width = 8      # Width of a single tile in pixels
tile_height = 16    # Height of a single tile in pixels

# Read the ROM file
def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

# Extract a single tile from the ROM
def extract_tile(rom_data, offset, width=8, height=16):
    tile = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        # Make sure we are within the bounds of the ROM data
        byte_row = rom_data[offset + (y * width) : offset + ((y + 1) * width)]
        if len(byte_row) != width:
            print(f"Warning: Byte row at offset {offset + (y * width)} has unexpected length {len(byte_row)}.")
            continue  # Skip this row if it's empty or incomplete
        tile[y, :] = [bit for bit in byte_row]  # Store the row
    return tile

# Rotate the tile 90 degrees counterclockwise
def rotate_tile(tile):
    return np.rot90(tile, k=1)  # k=1 means 90 degrees counterclockwise

# Function to display a grid of tiles
def display_tiles(rom_data, start_offset, num_tiles, tiles_per_row):
    rom_length = len(rom_data)
    rows = (num_tiles + tiles_per_row - 1) // tiles_per_row  # Calculate rows needed
    fig, axes = plt.subplots(rows, tiles_per_row, figsize=(tiles_per_row*2, rows*2))
    axes = axes.flatten()  # Flatten axes for easy iteration
    
    for i in range(num_tiles):
        offset = start_offset + i * tile_size
        # Ensure we're not going out of bounds
        if offset + tile_size > rom_length:
            print(f"Warning: Reached end of ROM data at offset {offset}. Skipping remaining tiles.")
            break
        
        tile = extract_tile(rom_data, offset)
        rotated_tile = rotate_tile(tile)
        
        ax = axes[i]
        ax.imshow(rotated_tile, cmap="gray", interpolation="nearest")
        ax.axis("off")  # Hide axis for a cleaner look
    
    # Hide any remaining axes
    for i in range(num_tiles, len(axes)):
        axes[i].axis("off")
    
    plt.tight_layout()
    plt.show()

# Main execution
rom_data = read_rom(rom_path)

# Check the ROM length to avoid reading out of bounds
rom_length = len(rom_data)
print(f"ROM length: {rom_length} bytes")

# Determine the total number of tiles to display (e.g., for the first 256 tiles)
num_tiles = 256  # Adjust based on how many tiles you want to preview
display_tiles(rom_data, tile_offset, num_tiles, tiles_per_row)
