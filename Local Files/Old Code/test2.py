import numpy as np
import matplotlib.pyplot as plt

# Define the ROM file and offsets
rom_path = "./c3.3i"
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

# Rotate the tile 90 degrees counterclockwise
def rotate_tile(tile):
    return np.rot90(tile, k=1)  # k=1 means 90 degrees counterclockwise

# Main execution
rom_data = read_rom(rom_path)
tile = extract_tile(rom_data, tile_offset)
rotated_tile = rotate_tile(tile)

# Display the rotated tile
plt.imshow(rotated_tile, cmap="gray", interpolation="nearest")
plt.title("Extracted and Rotated Tile")
plt.show()
