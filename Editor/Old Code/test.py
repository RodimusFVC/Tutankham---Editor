import numpy as np
from PIL import Image

def extract_tiles(rom_path, tile_width=16, tile_height=8, rotate=True):
    """
    Extracts 16x8 tiles from the ROM file.

    :param rom_path: Path to the ROM file.
    :param tile_width: Width of each tile in pixels.
    :param tile_height: Height of each tile in pixels.
    :param rotate: Whether to rotate the tiles by 90 degrees.
    :return: List of tiles as numpy arrays.
    """
    with open(rom_path, 'rb') as f:
        rom_data = f.read()

    # Each byte represents 8 pixels (1 bit per pixel)
    bytes_per_tile = (tile_width * tile_height) // 8
    num_tiles = len(rom_data) // bytes_per_tile

    tiles = []
    for i in range(num_tiles):
        tile_data = rom_data[i * bytes_per_tile:(i + 1) * bytes_per_tile]
        tile = np.zeros((tile_height, tile_width), dtype=np.uint8)
        for y in range(tile_height):
            byte1 = tile_data[y * 2]     # First byte (left side)
            byte2 = tile_data[y * 2 + 1] # Second byte (right side)
            for x in range(8):
                tile[y, 7 - x] = (byte1 >> x) & 1  # Left side (8 pixels)
                tile[y, 15 - x] = (byte2 >> x) & 1  # Right side (8 pixels)
        
        # Scale values to 0-255 for image display
        tile = tile * 255  

        # Rotate if needed
        if rotate:
            tile = np.rot90(tile)

        tiles.append(tile)

    return tiles

def save_tiles_as_image(tiles, tiles_per_row, output_image_path):
    """
    Saves the extracted tiles as a single image.

    :param tiles: List of tiles as numpy arrays.
    :param tiles_per_row: Number of tiles per row in the output image.
    :param output_image_path: Path to save the output image.
    """
    if not tiles:
        print("No tiles to display.")
        return

    tile_height, tile_width = tiles[0].shape
    num_tiles = len(tiles)
    num_rows = (num_tiles + tiles_per_row - 1) // tiles_per_row

    # Create a blank canvas
    image = Image.new('L', (tiles_per_row * tile_width, num_rows * tile_height))

    for idx, tile in enumerate(tiles):
        x = (idx % tiles_per_row) * tile_width
        y = (idx // tiles_per_row) * tile_height
        tile_image = Image.fromarray(tile)
        image.paste(tile_image, (x, y))

    image.save(output_image_path)
    print(f"Tiles saved as {output_image_path}")

# Example usage:
rom_path = './c1.1i'  # Update this with the actual path to your c3.3i file
tiles = extract_tiles(rom_path, rotate=True)
save_tiles_as_image(tiles, tiles_per_row=16, output_image_path='extracted_tiles.png')
