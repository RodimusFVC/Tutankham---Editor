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

def extract_pixels(rom, offset, height, width, mode='tile', bytes_per_row=None):
    """
    Generic 4bpp pixel extractor for ROM sprites/tiles.
    
    Supports two common layouts:
    - 'tile': Standard row-major (8px=4 bytes/row). Default for square tiles.
    - 'sprite': Interleaved even/odd scanlines (16 bytes per 2 rows). Default bytes_per_row=16.
    
    Args:
        rom: bytearray/list/np.array of ROM data.
        offset: Starting byte offset in ROM.
        height: Pixel height.
        width: Pixel width (must be even).
        mode: 'tile' (row-major) or 'sprite' (interleaved scanlines).
        bytes_per_row: For 'sprite' mode only; defaults to width//2 * 2 (padded to even).
    
    Returns:
        (height, width) uint8 array of pixel indices (0-15).
    
    Examples:
        # 8x8 tile (32 bytes)
        tile = extract_pixels(rom, 0x1000, 8, 8)  # mode='tile' auto
        # 16x16 sprite (interleaved, 16 bytes/2rows -> 128 bytes)
        sprite = extract_pixels(rom, 0x2000, 16, 16, mode='sprite')
        # Odd height sprite (17 rows -> final single scanline)
        tall = extract_pixels(rom, 0x3000, 17, 32, mode='sprite', bytes_per_row=16)
    """
    assert width % 2 == 0, "Width must be even for 4bpp"
    pixels = np.zeros((height, width), dtype=np.uint8)
    
    if mode == 'tile':
        bytes_per_row = width // 2
        for y in range(height):
            for x in range(width):
                byte_off = offset + y * bytes_per_row + (x // 2)
                byte_val = 0 if byte_off >= len(rom) else rom[byte_off]
                pixels[y, x] = (byte_val >> (4 * (x % 2))) & 0x0F
    
    elif mode == 'sprite':
        if bytes_per_row is None:
            bytes_per_row = width // 2  # Default: tight pack (e.g. 16px=8 bytes/row)
        for y in range(height):
            pair_idx = y // 2
            base = offset + pair_idx * bytes_per_row
            half = 0 if (y % 2 == 0) else bytes_per_row // 2  # Even: 0..N/2-1, Odd: N/2..N-1
            for b in range(width // 2):
                src_off = base + half + b
                byte_val = 0 if src_off >= len(rom) else rom[src_off]
                x = b * 2
                pixels[y, x] = byte_val & 0x0F
                pixels[y, x + 1] = (byte_val >> 4) & 0x0F
    
    else:
        raise ValueError("mode must be 'tile' or 'sprite'")
    
    return pixels

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
        tile = extract_pixels(rom_data, offset, 8, 8)
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
        tile = extract_pixels(rom_data, offset, 8, 8)
        tile = np.rot90(tile, k=1)  # Rotate to correct sideways orientation
        color_tile = apply_palette_to_tile(tile, palette)
        img = Image.fromarray(color_tile[:, :, :3], "RGB").resize((32, 32), Image.NEAREST)  # 4x zoom
        gap_tiles.append(ImageTk.PhotoImage(img))

    # Display alphabet (0x0220–0x055F, 26 tiles, 32 bytes each)
    alphabet = []
    for i in range(26):  # A–Z
        offset = 0x0220 + (i * 32)  # Relative to file start
        tile = extract_pixels(rom_data, offset, 8, 8)
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