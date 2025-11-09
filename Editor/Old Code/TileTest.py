import numpy as np
from PIL import Image

tile_roms = ["./c1.1i"]
tile_size = 16 * 8

palette = [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 133, 133, 148), 
           (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
           (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
           (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 91, 162, 69)]

def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

def extract_tile(rom_data, offset, width=16, height=16):
    tile = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            byte_offset = offset + y * (width // 2) + (x // 2)
            byte_val = rom_data[byte_offset]
            if x % 2 == 0:
                tile[y, x] = byte_val & 0x0F  # Low nibble
            else:
                tile[y, x] = (byte_val >> 4) & 0x0F  # High nibble
    return tile

def apply_palette(tile, pal):
    h, w = tile.shape
    color_tile = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            idx = tile[y, x] % 16
            color_tile[y, x] = [pal[idx][1], pal[idx][2], pal[idx][3]]
    return color_tile

# Extract tile 1 (index 0) - no rotation yet
#rom = read_rom("./c1.1i")
#tile_raw = extract_tile(rom, 0)
#print(f"Raw tile shape: {tile_raw.shape}")
#print(f"Raw tile data:\n{tile_raw}")
rom = read_rom("./c1.1i")
tile_raw = extract_tile(rom, 0)
print("First 128 bytes as hex:")
for i in range(0, 128, 16):
    hex_str = ' '.join(f'{rom[i+j]:02x}' for j in range(16))
    print(f"{i:04x}: {hex_str}")

# Apply palette
tile_colored = apply_palette(tile_raw, palette)

# Save without rotation
Image.fromarray(tile_colored).save("tile_no_rotation.png")

# Now rotate and save
tile_rotated = np.rot90(tile_raw, k=1)
print(f"Rotated tile shape: {tile_rotated.shape}")
tile_colored_rotated = apply_palette(tile_rotated, palette)
Image.fromarray(tile_colored_rotated).save("tile_rotated.png")