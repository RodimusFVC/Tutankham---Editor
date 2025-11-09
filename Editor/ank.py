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

# Extract 4bpp sprite with simple even/odd interleaving
def extract_sprite(rom, offset, width=40, height=24):
    """
    Decodes 4bpp sprite with even/odd scanline pairing, no 16-byte blocks.
    Each byte provides 2 pixels (4 bits each).
    """
    bytes_per_row = width // 2  # 20 for 40px width
    sprite = np.zeros((height, bytes_per_row * 2), dtype=np.uint8)  # 40 pixels wide
    for y in range(0, height, 2):  # Process in pairs
        print(f"Pair {y//2} (Rows {y}-{y+1}): ", end="")
        base = offset + (y // 2) * bytes_per_row * 2  # Offset for each pair
        for b in range(bytes_per_row):
            src_off_even = base + b
            src_off_odd = base + b + bytes_per_row
            if src_off_even >= len(rom) or src_off_even > 0x0FF3:
                val_even = 0
            else:
                val_even = rom[src_off_even]
            if src_off_odd >= len(rom) or src_off_odd > 0x0FF3:
                val_odd = 0
            else:
                val_odd = rom[src_off_odd]
            print(f"{val_even:02x} {val_odd:02x} ", end="")
            x = b * 2
            sprite[y, x] = val_even & 0x0F
            sprite[y, x + 1] = (val_even >> 4) & 0x0F
            if y + 1 < height:
                sprite[y + 1, x] = val_odd & 0x0F
                sprite[y + 1, x + 1] = (val_odd >> 4) & 0x0F
        print()  # New line after each pair
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
def display_unknown_banner():
    
    rom_path = "./c6.6i"
    rom_data = read_rom(rom_path)
    if len(rom_data) != 4096:  # Adjust if c6.6i size differs
        raise ValueError(f"Expected 4096 bytes in {rom_path}, got {len(rom_data)}")
    root = tk.Tk()
    root.title("Tutankham c6.6i Unknown Banner Graphic")
    offset = 0x0E00  # Relative file offset for Unknown Banner
    sprite_width = 40  # As provided
    sprite_height = 24  # Adjusted to fit 500 bytes
    zoom_factor = 10
    canvas = tk.Canvas(root, width=sprite_width * zoom_factor, height=sprite_height * zoom_factor, bg="#2b2b2b")
    canvas.pack(pady=10)
    sprite = extract_sprite(rom_data, offset, width=sprite_width, height=sprite_height)
    sprite = np.rot90(sprite, k=1)  # Rotate 90° clockwise, adjust if needed
    color_sprite = apply_palette_to_sprite(sprite, palette)
    img = Image.fromarray(color_sprite[:, :, :3], "RGB").resize((sprite_width * zoom_factor, sprite_height * zoom_factor), Image.NEAREST)
    photo = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.image_refs = [photo]  # Keep reference to avoid garbage collection
    root.mainloop()

# Run
if __name__ == "__main__":
    display_unknown_banner()