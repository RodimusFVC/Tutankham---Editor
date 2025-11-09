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

# Extract 4bpp sprite from full range (560 bytes)
def extract_sprite(rom, offset, width=35, height=16):
    """
    Decodes 4bpp sprite with 16-byte blocks where:
      - bytes 0..7 -> even scanlines of the block
      - bytes 8..15 -> odd scanlines of the block
    Handles odd height by decoding the final single scanline if present.
    """
    bytes_per_row = width // 2  # 16 for 32px width
    sprite = np.zeros((height, bytes_per_row), dtype=np.uint8)

    # Each pair of scanlines consumes 16 source bytes. Row-group index = y // 2
    for y in range(height):
        pair_index = y // 2
        # base of the 16-byte chunk for this pair of rows
        base = offset + pair_index * (bytes_per_row)
        # if y is even -> use bytes base+0..base+7  (even scanline)
        # if y is odd  -> use bytes base+8..base+15 (odd scanline)
        half = 0 if (y % 2 == 0) else 8

        for b in range(bytes_per_row // 2):  # 8 iterations -> 16 pixels
            src_off = base + half + b
            if src_off >= len(rom):
                val = 0
            else:
                val = rom[src_off]
            x = b * 2
            sprite[y, x]     = val & 0x0F
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

#    rom_path = "./j6.6h"
#    offset = 0x05C0  # Relative file offset for Copyright
#    sprite_width=32    # Copyright Width
#    sprite_height=102  # Copyright Height

#    rom_path = "./j6.6h"
#    offset = 0x0B70  # Relative file offset for Genie Lamp Smart Bomb Marker
#    sprite_width=32    # Genie Lamp Width
#    sprite_height=14   # Genie Lamp Height

    rom_path = "./c6.6i"
    offset = 0x0E00  # Relative file offset for Timer Banner
    sprite_height = 24  # Calculated: (0xB6F - 0x8F0 + 1) / (32 / 2) = 688 / 16 = 43, but adjust for visible area
    sprite_width = 500 // sprite_height  # Placeholder width, adjust based on graphic

    zoom_factor=10 

    rom_data = read_rom(rom_path)
    if len(rom_data) != 4096:
        raise ValueError(f"Expected 4096 bytes in {rom_path}, got {len(rom_data)}")
    root = tk.Tk()
    root.title("Tutankham j6.6h Copyright Graphic")

    canvas = tk.Canvas(root, width=sprite_width*zoom_factor, height=sprite_width*zoom_factor, bg="#2b2b2b")  # 32×4, 35×4
    canvas.pack(pady=10)

    sprite = extract_sprite(rom_data, offset, width=sprite_width, height=sprite_height)
    sprite = np.rot90(sprite, k=1)  # Rotate 90° clockwise based on your note
    color_sprite = apply_palette_to_sprite(sprite, palette)
    img = Image.fromarray(color_sprite[:, :, :3], "RGB").resize((sprite_width*zoom_factor, sprite_width*zoom_factor), Image.NEAREST)
    photo = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.image_refs = [photo]  # Keep reference to avoid garbage collection

    root.mainloop()

# Run
if __name__ == "__main__":
    display_copyright()