import numpy as np
from PIL import Image, ImageTk
import tkinter as tk

# ROM path
rom_path = "./j6.6h"

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

# Extract 4bpp sprite from full range (560 bytes)
def extract_sprite(rom, offset, width=100, height=16):
    """
    Decodes 4bpp sprite with 16-byte blocks where:
      - bytes 0..7 -> even scanlines of the block
      - bytes 8..15 -> odd scanlines of the block
    Handles odd height by decoding the final single scanline if present.
    """
    sprite = np.zeros((height, width), dtype=np.uint8)
    bytes_per_row = width // 2  # 50 for 100px width
    block_height = 16  # bytes-per-block (8 even + 8 odd) -> covers 16 rows conceptually
    # Each pair of scanlines consumes 16 source bytes. Row-group index = y // 2
    for y in range(height):
        pair_index = y // 2
        # base of the 16-byte chunk for this pair of rows
        base = offset + pair_index * bytes_per_row
        # if y is even -> use bytes base+0..base+7 (even scanline)
        # if y is odd -> use bytes base+8..base+15 (odd scanline)
        half = 0 if (y % 2 == 0) else 8
        for b in range(bytes_per_row // 2):  # 25 iterations -> 50 pixels
            src_off = base + half + b
            if src_off >= offset + 560:  # Limit to 0x05C0–0x08EF
                val = 0
            else:
                val = rom[src_off]
            x = b * 2
            if x < width:
                sprite[y, x] = val & 0x0F
                if x + 1 < width:
                    sprite[y, x + 1] = (val >> 4) & 0x0F
    return sprite

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

# Main display function
def display_copyright():
    rom_data = read_rom(rom_path)
    if len(rom_data) != 4096:
        raise ValueError(f"Expected 4096 bytes in {rom_path}, got {len(rom_data)}")
    root = tk.Tk()
    root.title("Tutankham j6.6h Copyright Graphic")
    canvas = tk.Canvas(root, width=400, height=64, bg="#2b2b2b")  # 100×4, 16×4
    canvas.pack(pady=10)

    # Extract and display copyright sprite (0x05C0–0x08EF, 560 bytes)
    offset = 0x05C0  # Relative file offset
    sprite = extract_sprite(rom_data, offset, width=100, height=16)
    sprite = np.rot90(sprite, k=1)  # Rotate 90° clockwise
    color_sprite = apply_palette_to_sprite(sprite, palette)
    img = Image.fromarray(color_sprite[:, :, :3], "RGB").resize((400, 64), Image.NEAREST)  # 4x zoom
    photo = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.image_refs = [photo]  # Keep reference to avoid garbage collection

    root.mainloop()

# Run
if __name__ == "__main__":
    display_copyright()