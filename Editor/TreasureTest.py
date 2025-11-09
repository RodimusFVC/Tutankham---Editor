import numpy as np
from PIL import Image, ImageTk
import tkinter as tk

# Palette (from your editor, Map 1)
palette = [
    (255, 0, 0, 0), (255, 0, 0, 148), (255, 0, 224, 0), (255, 133, 133, 148),
    (255, 224, 162, 148), (255, 162, 0, 217), (255, 224, 0, 0), (255, 133, 133, 148),
    (255, 224, 224, 0), (255, 162, 29, 0), (255, 224, 133, 0), (255, 224, 0, 148),
    (255, 0, 0, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 91, 162, 69)
]

# Read ROM
def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

# Apply palette to sprite
def apply_palette_to_sprite(sprite, palette):
    height, width = sprite.shape
    color_sprite = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            color_index = sprite[y, x] % 16
            if 0 <= color_index < len(palette):
                color_sprite[y, x] = [
                    palette[color_index][1],
                    palette[color_index][2],
                    palette[color_index][3],
                    palette[color_index][0]
                ]
    return color_sprite

def hex_dump(rom, start, length=0x480):
    return ' '.join(f'{rom[i]:02X}' for i in range(start, min(start+length, len(rom))))


def extract_giant_graphic(rom, treasure_index):
    offset = treasure_index * 0x3DD
    size = 0x3DD
    data = rom[offset:offset+size]
    width = 128  # try common power-of-two width
    total_pixels = len(data) * 2
    height = total_pixels // width

    sprite = np.zeros((height, width), dtype=np.uint8)
    idx = 0
    for y in range(height):
        for x in range(0, width, 2):
            if idx >= len(data): break
            byte = data[idx]
            sprite[y, x+1] = (byte >> 4) & 0xF
            sprite[y, x]   = byte & 0xF
            idx += 1
    return sprite

def extract_interleaved_4bpp(rom, offset, size, width):
    data = rom[offset:offset+size]
    total_pixels = len(data) * 2
    height = total_pixels // width
    sprite = np.zeros((height, width), dtype=np.uint8)

    # split lower 2 bitplanes and upper 2 bitplanes
    half = len(data) // 2
    low = data[:half]
    high = data[half:]
    for i in range(half):
        lo = low[i]
        hi = high[i]
        for bit in range(8):
            pixel = ((hi >> (7-bit)) & 1) << 1 | ((lo >> (7-bit)) & 1)
            x = (i*8 + bit) % width
            y = (i*8 + bit) // width
            sprite[y, x] = pixel
    return sprite

def extract_tutankham_48x48(rom, offset):
    width, height = 48, 48
    bytes_per_tile = 32  # 4bpp, 8x8 pixels
    tiles_per_row = 6
    sprite = np.zeros((height, width), dtype=np.uint8)

    for tile_y in range(6):
        for tile_x in range(6):
            tile_index = tile_y * tiles_per_row + tile_x
            tile_offset = offset + tile_index * bytes_per_tile
            tile = rom[tile_offset:tile_offset + bytes_per_tile]

            # In Konami format, planes interleave as pairs of bytes per row
            for row in range(8):
                b0 = tile[row * 2]
                b1 = tile[row * 2 + 1]
                b2 = tile[16 + row * 2]
                b3 = tile[16 + row * 2 + 1]

                for bit in range(8):
                    color = ((b3 >> (7 - bit)) & 1) << 3 | \
                            ((b2 >> (7 - bit)) & 1) << 2 | \
                            ((b1 >> (7 - bit)) & 1) << 1 | \
                            ((b0 >> (7 - bit)) & 1)
                    px = tile_x * 8 + bit
                    py = tile_y * 8 + row
                    sprite[py, px] = color
    return sprite

def extract_tutankham_direct_4bpp(rom, offset):
    width, height = 48, 48
    size = width * height // 2  # 2 pixels per byte
    data = rom[offset : offset + size]

    sprite = np.zeros((height, width), dtype=np.uint8)
    idx = 0
    for y in range(height):
        for x in range(0, width, 2):
            if idx >= len(data):
                break
            byte = data[idx]
            # High nibble = left pixel, low nibble = right pixel
            left = (byte >> 4) & 0xF
            right = byte & 0xF
            sprite[y, x] = left
            sprite[y, x + 1] = right
            idx += 1
    return sprite

# Main display function
def display_copyright():
    rom_path = "./c9.9i"
    treasure_index = 0  # 0 to 3
    TREASURE_SIZE = 0x480  # corrected size for 48×48×4bpp
    offset = treasure_index * TREASURE_SIZE
    sprite_width = 48
    sprite_height = 48
    zoom_factor = 10

    rom_data = read_rom(rom_path)
    if len(rom_data) != 4096:
        raise ValueError(f"Expected 4096 bytes in {rom_path}, got {len(rom_data)}")
    root = tk.Tk()
    root.title("Tutankham j6.6h Copyright Graphic")

    canvas = tk.Canvas(root, width=sprite_width*zoom_factor, height=sprite_height*zoom_factor, bg="#2b2b2b")
    canvas.pack(pady=10)

    print("Treasure 0 - first 0x480 bytes:")
    print(hex_dump(rom_data, 0))

    sprite = extract_tutankham_direct_4bpp(rom_data, offset)
    sprite = np.rot90(sprite, k=1)  # Rotate 90° clockwise based on your note
    color_sprite = apply_palette_to_sprite(sprite, palette)
    img = Image.fromarray(color_sprite[:, :, :3], "RGB").resize(
        (sprite_width * zoom_factor, sprite_height * zoom_factor), Image.NEAREST
    )
    photo = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.image_refs = [photo]  # Keep reference to avoid garbage collection

    for i in range(4):
        print(f"Treasure {i}: offset 0x{i*0x3DD:04X}")

    root.mainloop()

# Run
if __name__ == "__main__":
    display_copyright()