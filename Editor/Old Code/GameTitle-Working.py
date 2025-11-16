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
def display_GameTitle():

    zoom_factor=30 

# WORKING
#    rom_path = "../MameTest/untouched/c8.8i"
#    offset = 0x0C00  # Relative file offset for Upper Case *T* in Game Title - PERFECT
#    sprite_width=30    
#    sprite_height=25   

#    rom_path = "../MameTest/untouched/c8.8i"
#    offset = 0x0D77  # Relative file offset for Lower Case *u* in Game Title - PERFECT
#    sprite_width=20
#    sprite_height=20 

#    rom_path = "../MameTest/untouched/c6.6i"
#    offset = 0x0E00  # Relative file offset for Lower Case *a* in Game Title - PERFECT
#    sprite_width=20   
#    sprite_height=20  

#    rom_path = "../MameTest/untouched/c7.7i"
#    offset = 0x0E00  # Relative file offset for Lower Case *n* in Game Title - PERFECT
#    sprite_width=20    
#    sprite_height=20 

#    rom_path = "../MameTest/untouched/c6.6i"
#    offset = 0x0EC8  # Relative file offset for Lower Case *k* in Game Title - PERFECT
#    sprite_width=30
#    sprite_height=20

#    rom_path = "../MameTest/untouched/c7.7i"
#    offset = 0x0EC8  # Relative file offset for Lower Case *h* in Game Title - PERFECT
#   sprite_width=30    
#   sprite_height=20 

#    rom_path = "../MameTest/untouched/c8.8i"
#    offset = 0x0EF5  # Relative file offset for Lower Case *m* in Game Title - PERFECT
#    sprite_width=20
#    sprite_height=26 

# NOT WORKING / MISSING = t

    rom_path = "../MameTest/untouched/c8.8i"
#    offset = 0x0E40  # Relative file offset for Lower Case *t* in Game Title - Not quite right...
    offset = 0xE3F
    sprite_width=26
    sprite_height=14

    rom_data = read_rom(rom_path)
    if len(rom_data) != 4096:
        raise ValueError(f"Expected 4096 bytes in {rom_path}, got {len(rom_data)}")
    root = tk.Tk()
    root.title("Tutankham Game Title Graphics")

    sprite = extract_pixels(rom_data, offset, height=sprite_height, width=sprite_width)

    sprite = np.rot90(sprite, k=1)  # Rotate 90° clockwise based on your note
    color_sprite = apply_palette_to_sprite(sprite, palette)
    img = Image.fromarray(color_sprite[:, :, :3], "RGB").resize((sprite_height*zoom_factor, sprite_width*zoom_factor), Image.NEAREST)
    photo = ImageTk.PhotoImage(img)
    canvas = tk.Canvas(root, width=sprite_height*zoom_factor, height=sprite_width*zoom_factor, bg="#2b2b2b")  # 32×4, 35×4
    canvas.pack(pady=10)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.image_refs = [photo]  # Keep reference to avoid garbage collection

    root.mainloop()

# Run
if __name__ == "__main__":
    display_GameTitle()