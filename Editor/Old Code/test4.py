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

# Inspect raw data at a given offset
def inspect_tile_data_at_offset(rom_data, offset, num_bytes=64):
    """ Inspect raw data at a given offset """
    byte_data = rom_data[offset:offset+num_bytes]
    print(f"Data at offset {hex(offset)}:")
    print(byte_data)

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

# Inspect the raw data starting at 0x500 (adjust the number of bytes as needed)
inspect_tile_data_at_offset(rom_data, 0x500)

# Optionally, extract and display a tile to verify it's being correctly interpreted
tile = extract_tile(rom_data, tile_offset)
rotated_tile = rotate_tile(tile)

# Display the rotated tile (if needed)
plt.imshow(rotated_tile, cmap="gray", interpolation="nearest")
plt.title("Extracted and Rotated Tile")
plt.show()
