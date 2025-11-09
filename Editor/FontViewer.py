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

# Extract 8×8px, 4bpp tile (32 bytes)
def extract_tile(rom_data, offset, width=8, height=8):
    tile = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            byte_offset = offset + y * (width // 2) + (x // 2)
            byte_val = rom_data[byte_offset]
            if x % 2 == 0:
                tile[y, x] = byte_val & 0x0F
            else:
                tile[y, x] = (byte_val >> 4) & 0x0F
    return tile

# Apply palette to tile
def apply_palette_to_tile(tile, palette):
    height, width = tile.shape
    color_tile = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            color_index = tile[y, x] % 16
            if 0 <= color_index < len(palette):
                color_tile[y, x] = [
                    palette[color_index][1],
                    palette[color_index][2],
                    palette[color_index][3],
                    palette[color_index][0]
                ]
    return color_tile

# Main display function
def display_graphics():
    rom_data = read_rom(rom_path)
    if len(rom_data) != 4096:
        raise ValueError(f"Expected 4096 bytes in {rom_path}, got {len(rom_data)}")
    root = tk.Tk()
    root.title("Tutankham j6.6h Font Viewer")
    canvas = tk.Canvas(root, width=800, height=400, bg="#2b2b2b")
    canvas.pack(pady=10)

    # Display digits (0x0000–0x013F, 10 tiles, 32 bytes each)
    digits = []
    for i in range(10):  # 0–9
        offset = 0x0000 + (i * 32)  # Relative to file start
        tile = extract_tile(rom_data, offset, 8, 8)
        tile = np.rot90(tile, k=1)  # Rotate to correct sideways orientation
        color_tile = apply_palette_to_tile(tile, palette)
        img = Image.fromarray(color_tile[:, :, :3], "RGB").resize((32, 32), Image.NEAREST)  # 4x zoom
        digits.append(ImageTk.PhotoImage(img))

    # Display special tiles (0x0140–0x021F, 7 tiles, 32 bytes each)
    # 1 - © - Copyright Symbol
    # 2 - ☐ - Open Box
    # 3 - . - Period
    # 4 - ! - Exclamation Mark
    # 5 - ? - Question Mark
    # 6 - ♪ - Musical Note
    # 7 -   - Blank Space 

    gap_tiles = []
    for i in range(7):  # Special Characters 1–7
        offset = 0x0140 + (i * 32)  # Relative to file start
        tile = extract_tile(rom_data, offset, 8, 8)
        tile = np.rot90(tile, k=1)  # Rotate to correct sideways orientation
        color_tile = apply_palette_to_tile(tile, palette)
        img = Image.fromarray(color_tile[:, :, :3], "RGB").resize((32, 32), Image.NEAREST)  # 4x zoom
        gap_tiles.append(ImageTk.PhotoImage(img))

    # Display alphabet (0x0220–0x055F, 26 tiles, 32 bytes each)
    alphabet = []
    for i in range(26):  # A–Z
        offset = 0x0220 + (i * 32)  # Relative to file start
        tile = extract_tile(rom_data, offset, 8, 8)
        tile = np.rot90(tile, k=1)  # Rotate to correct sideways orientation
        color_tile = apply_palette_to_tile(tile, palette)
        img = Image.fromarray(color_tile[:, :, :3], "RGB").resize((32, 32), Image.NEAREST)  # 4x zoom
        alphabet.append(ImageTk.PhotoImage(img))

    # Render digits (0–9)
    for i, img in enumerate(digits):
        x = 20 + (i * 40)
        y = 20
        canvas.create_image(x, y, image=img, anchor="nw")
        canvas.create_text(x + 16, y + 40, text=str(i), fill="white", font=("Arial", 10))

    # Render gap tiles (Special Characters 1–7)
    for i, img in enumerate(gap_tiles):
        x = 20 + (i * 40)
        y = 260
        canvas.create_image(x, y, image=img, anchor="nw")
        canvas.create_text(x + 16, y + 40, text=f"U{i+1}", fill="white", font=("Arial", 10))

    # Render alphabet (A–Z)
    for i, img in enumerate(alphabet):
        x = 20 + (i % 13) * 40  # Two rows, 13 letters each
        y = 100 if i < 13 else 180
        canvas.create_image(x, y, image=img, anchor="nw")
        canvas.create_text(x + 16, y + 40, text=chr(65 + i), fill="white", font=("Arial", 10))

    canvas.image_refs = digits + gap_tiles + alphabet  # Keep references to avoid garbage collection
    root.mainloop()

# Run
if __name__ == "__main__":
    display_graphics()