import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import shutil
from datetime import datetime
import logging
from colorlog import ColoredFormatter
import zipfile
import tempfile

#########################################
# Logging Setup
#########################################
# Create handler
handler = logging.StreamHandler()
# Set up the colored formatter
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)s: %(message)s",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
handler.setFormatter(formatter)
# Get the root logger
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

#########################################
# Editor Setup
#########################################
# Editor Version Number
EDITOR_VERSION = "V14"
# Palette ROM configuration
PALETTE_ROM_PATH = "./m1.1h"
PALETTE_FILE_OFFSETS = [0x2D1, 0x2E1, 0x2F1, 0x301, 0x311, 0x321, 0x331]
# ROM file structure - centralized definition
ROM_CONFIG = {
    'tile_roms': ['c1.1i', 'c2.2i', 'c3.3i', 'c4.4i', 'c5.5i'],
    'visual_map_rom': 'c8.8i',
    'logical_map_roms': ['c6.6i', 'c7.7i'],
    'object_roms': ['m1.1h', 'm2.2h'],
    'high_score_rom': 'm1.1h',
    'palette_rom': 'm1.1h',}
# All ROM files with paths
ROM_FILES = {
    'c1.1i': './c1.1i',
    'c2.2i': './c2.2i',
    'c3.3i': './c3.3i',
    'c4.4i': './c4.4i',
    'c5.5i': './c5.5i',
    'c6.6i': './c6.6i',
    'c7.7i': './c7.7i',
    'c8.8i': './c8.8i',
    'c9.9i': './c9.9i',
    'm1.1h': './m1.1h',
    'm2.2h': './m2.2h',
    'm4.4h': './m4.4h',
    'm5.5h': './m5.5h',
    '3j.3h': './3j.3h',
    'j6.6h': './j6.6h',}
# Global ROM cache - loaded once at startup
rom_cache          = {}
# Constants
tile_size          = 16 * 16 // 2 # Tile Size
num_maps           = 4       # Number Of Maps in Game
map_width          = 64      # Map Width  by Tile Count
map_height         = 12      # Map Height by Tile Count
visual_map_size    = 0x300   # Visual  Map Byte Size In ROM
logical_map_size   = 0x700   # Logical Map Byte Size In ROM
empty_path_tile    = 0x26    # Blank Path - Where Player/Monsters Can Move Freely
# Object data constants
CONFIG_BASE_OFFSET = 0x061E  # Config data for each map/difficulty block
CONFIG_BLOCK_SIZE  = 11      # 11 bytes of config data per block
OBJECT_BASE_OFFSET = CONFIG_BASE_OFFSET + CONFIG_BLOCK_SIZE  # Object data follows config
OBJECT_BLOCK_SIZE  = 0x0148  # Block Size 
NUM_DIFFICULTIES   = 4       # Four Difficulties
NUM_ITEMS          = 14      # Max Items - Keys, Treasure Boxes, Rings, Keyholes
NUM_TELEPORTS      = 6       # Max Number Of Teleporter Pairs
NUM_SPAWNS         = 7       # Max Number Of Enemy Spawn Points
NUM_RESPAWNS       = 3       # Max Number Of Player Respawn Points
# High Score data constants
HIGH_SCORE_OFFSET  = 0x04A0  # Offset for high score data in m1.1h
HIGH_STAGE_OFFSET  = HIGH_SCORE_OFFSET + 0x2D
NUM_HIGH_SCORES    = 7       # 7 high score entries
# Tile filter categories
PATH_TILES     = [0x26]      # Blank Path - Where Player/Monsters Can Move Freely
SPAWN_TILES    = [0x17,]     # 23 - Player Respawn flame (Editor Representation Only!  Not Saved To Map/Code)
WALL_TILES     = [
    *range(0x00, 0x0F), 
    0x11, 0x13, 
    *range(0x1F, 0x21), 
    0x27, 0x28,]             # Walls
TREASURE_TILES = [
    0x21, 0x6F,              # Ring Box     (Empty, Filled)
    0x22, 0x70,              # Key Box      (Empty, Filled)
    0x4A, 0x62,              # Treasure Box (Empty, Filled)
    0x72,]                   # Keyhole
# Composite block definitions
TELEPORTER_TILES = np.array([
   [100], [38], [101]])      # Left Pillar, Blank Space, Right Pillar
TELEPORTER_LOGICAL = np.array([
  [[0x55,0x55]],             # Wall Block
  [[0x00,0x00]],             # Empty Block
  [[0x55,0x55]]])            # Wall Block
DOOR_TILES = np.array([
   [115, 116, 117],          # Door Top Tiles
   [118, 119, 120],          # Door Middle Tiles
   [121, 122, 123]])         # Door Bottom Tiles
DOOR_LOGICAL = np.array([
  [[0x00,0x00],              # Door Top Left Logical Bytes
   [0x00,0x06],              # Door Top Middle Logical Bytes
   [0x00,0x00]],             # Door Top Right Logical Bytes
  [[0x55,0x06],              # Door Center Left Logical Bytes
   [0xF6,0x6E],              # Door Center Middle Logical Bytes
   [0xF6,0x06]],             # Door Center Right Logical Bytes
  [[0x00,0x00],              # Door Bottom Left Logical Bytes
   [0xF0,0x66],              # Door Bottom Middle Logical Bytes
   [0xF0,0x00]]])            # Door Bottom Right Logical Bytes
SPAWNER_CONFIGS = {
    'right': {
        'tiles': np.array([[29, 15], [27, 38], [24, 21]]),
        'logical': np.array([[[0x55,0x55], [0x55,0x55]],
                            [[0x55,0x55], [0x00,0x00]],
                            [[0x55,0x55], [0x55,0x55]]])
    },
    'left': {
        'tiles': np.array([[15, 16], [38, 18], [21, 20]]),
        'logical': np.array([[[0x55,0x55], [0x55,0x55]],
                            [[0x00,0x00], [0x55,0x55]],
                            [[0x55,0x55], [0x55,0x55]]])
    },
    'up': {
        'tiles': np.array([[27, 38, 18], [24, 21, 20]]),
        'logical': np.array([[[0x55,0x55], [0x00,0x00], [0x55,0x55]],
                            [[0x55,0x55], [0x55,0x55], [0x55,0x55]]])
    },
    'down': {
        'tiles': np.array([[29, 15, 16], [27, 38, 18]]),
        'logical': np.array([[[0x55,0x55], [0x55,0x55], [0x55,0x55]],
                            [[0x55,0x55], [0x00,0x00], [0x55,0x55]]])
    }
}

# Item tile constraints
ITEM_TILES = {
    0x70: 0x22,  # Key -> side-accessible box
    0x62: 0x4A,  # Treasure -> bottom-accessible box
    0x6F: 0x21,  # Ring -> top-accessible box
    0x72: None   # Keyhole -> no constraint
}

# Empty to filled box mapping
EMPTY_TO_FILLED = {
    0x22: 0x70,  # Key box
    0x4A: 0x62,  # Treasure box
    0x21: 0x6F,  # Ring box
}

FILLED_TO_EMPTY = {v: k for k, v in EMPTY_TO_FILLED.items()}

#########################################
# Code Starts Here
#########################################

#########################################
# Main Functions
#########################################

def create_window_icon(root, all_tiles, palettes):
    """Create window icon from Tut mask tile"""
    try:
        from PIL import Image, ImageTk  # ensure these are imported

        # Use middle Tut mask tile (0x87)
        tile_idx = 0x87

        if tile_idx < len(all_tiles):
            tile = all_tiles[tile_idx]
            palette = palettes[0]  # Use Map 1 palette
            color_tile = apply_palette_to_tile(tile, palette)

            # Convert to PIL Image
            icon_rgb = color_tile[:, :, :3]
            icon_pil = Image.fromarray(icon_rgb.astype('uint8')).convert('RGB')

            # Resize to standard icon size (32x32)
            icon_pil = icon_pil.resize((32, 32), Image.NEAREST)

            # Convert to PhotoImage and set as icon
            icon_photo = ImageTk.PhotoImage(icon_pil)
            root.iconphoto(True, icon_photo)

            # Keep reference to prevent garbage collection
            root._icon_ref = icon_photo  # store it in root
    except Exception:
        logging.warning("Couldn't set window icon", exc_info=True)

#########################################
# Rom Handling Functions
#########################################

def load_all(location=None):
    # Load all ROMs into memory first
    if location == "Zip":
        load_roms_from_zip()
    elif location == "Folder":
            folder = filedialog.askdirectory(
                title="Select Folder That Contains Your Extracted Tutankham ROMs",
                initialdir=os.path.abspath("."))
            if not folder:
                raise RuntimeError("Folder Selection Cancelled")
            load_roms_from_folder(folder)
    else:
        load_all_roms()

    # Load all data
    all_tiles = load_tiles()
    visual_maps = load_visual_maps()
    logical_maps = load_logical_maps()
    palettes = load_palettes_from_rom()
    high_scores = load_high_scores()
    logging.info(
            "Data loaded – %d tiles, %d visual maps, %d logical maps, %d palettes, %d high_scores",
            len(all_tiles), len(visual_maps), len(logical_maps), len(palettes), len(high_scores)
        )

    return all_tiles, visual_maps, logical_maps, palettes, high_scores

def load_all_roms():
    """Load all ROM files into memory at startup"""
    global rom_cache
    for rom_name, rom_path in ROM_FILES.items():
        try:
            with open(rom_path, 'rb') as f:
                rom_cache[rom_name] = bytearray(f.read())
            logging.info("Loaded %s: %d bytes", rom_name, len(rom_cache[rom_name]))
        except Exception as e:
            logging.critical("Error loading %s", rom_name)

def load_roms_from_folder(folder_path: str):
    """Temporarily repoint ROM_FILES and call load_all_roms()."""
    original = ROM_FILES.copy()
    try:
        for name in ROM_FILES:
            p = os.path.join(folder_path, name)
            if not os.path.isfile(p):
                raise FileNotFoundError(f"Missing {name} in {folder_path}")
            ROM_FILES[name] = p
        load_all_roms()
        logging.info("ROMs loaded from folder: %s", folder_path)
    finally:
        ROM_FILES.clear()
        ROM_FILES.update(original)

def load_roms_from_zip():
    """Load ROMs from a known zip file in the application directory."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        zip_path = os.path.join(app_dir, "tutankhm.zip")

        if not os.path.exists(zip_path):
            messagebox.showerror("Error", f"Zip file not found:\n{zip_path}")
            return

        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logging.info(f"Extracted ROMs from: {zip_path}")

            # Point ROM_FILES to extracted versions
            updated_paths = {}
            for name in ROM_FILES:
                extracted_path = os.path.join(extract_dir, name)
                if os.path.exists(extracted_path):
                    updated_paths[name] = extracted_path

            # Only temporarily override ROM_FILES
            original_paths = ROM_FILES.copy()
            ROM_FILES.update(updated_paths)

            # Load the ROMs
            load_all_roms()
            logging.info("ROMs loaded successfully from zip file.")

            # Restore ROM_FILES to original paths
            ROM_FILES.clear()
            ROM_FILES.update(original_paths)

            # Temporary directory auto-deletes here
    except Exception as e:
        logging.error(f"Error loading from zip: {e}")
        messagebox.showerror("Error", f"Failed to load ROMs from zip:\n{e}")

def save_all_roms(target_directory=None):
    """Write all modified ROMs back to disk
    
    Args:
        target_directory: Optional directory path. If None, saves to original ROM_FILES paths.
                         If specified, saves all ROMs to that directory with original names.
    """
    for rom_name, rom_data in rom_cache.items():
        try:
            if target_directory:
                rom_path = os.path.join(target_directory, rom_name)
            else:
                rom_path = ROM_FILES[rom_name]
            
            with open(rom_path, 'wb') as f:
                f.write(rom_data)
            logging.info("Saved %s to %s", rom_name, rom_path)
        except Exception as e:
            logging.critical("Error saving %s: %s", rom_name, e)

def read_byte_from_roms(offset):
    """Read a single byte from the combined ROM space"""
    rom_index = offset // 0x1000
    rom_offset = offset % 0x1000
    
    if rom_index >= len(ROM_CONFIG['object_roms']):
        raise ValueError(f"Offset 0x{offset:04X} beyond available ROMs")
    
    # Get ROM name and read from cache
    rom_name = ROM_CONFIG['object_roms'][rom_index]
    return rom_cache[rom_name][rom_offset]

def write_byte_to_roms(offset, value):
    """Write a single byte to the global ROM cache"""
    rom_index = offset // 0x1000
    rom_offset = offset % 0x1000
    
    if rom_index >= len(ROM_CONFIG['object_roms']):
        raise ValueError(f"Offset 0x{offset:04X} beyond available ROMs")
    
    # Write directly to global rom_cache
    rom_name = ROM_CONFIG['object_roms'][rom_index]
    rom_cache[rom_name][rom_offset] = value

def backup_file(filepath):
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        return backup_path
    return None

#########################################
# Palette Handling Functions
#########################################

def load_palettes_from_rom():
    """Load all 7 palettes from ROM (4 maps + 3 unknowns)"""
    palettes = []
    
    rom_data = rom_cache[ROM_CONFIG['palette_rom']]
    for offset in PALETTE_FILE_OFFSETS:
        palette = []
        for i in range(16):  # 16 colors per palette
            byte_val = rom_data[offset + i]
            r, g, b = decode_palette_byte(byte_val)
            palette.append((255, r, g, b))  # Keep ARGB format for compatibility
        palettes.append(palette)
    
    return palettes

def decode_palette_byte(byte_val):
    """
    Decode a single palette byte to RGB.
    Format: BBGGGRRR (bits 7-0)
    """
    r = (byte_val & 0b00000111)      # bits 0-2
    g = (byte_val & 0b00111000) >> 3 # bits 3-5
    b = (byte_val & 0b11000000) >> 6 # bits 6-7
    
    # Scale to 0-255 range
    r_scaled = int(r * 255 / 7)
    g_scaled = int(g * 255 / 7)
    b_scaled = int(b * 255 / 3)
    
    return (r_scaled, g_scaled, b_scaled)

def encode_palette_byte(r, g, b):
    """
    Encode RGB values back to palette byte format.
    """
    r_bits = int(round(r * 7 / 255)) & 0b111
    g_bits = int(round(g * 7 / 255)) & 0b111
    b_bits = int(round(b * 3 / 255)) & 0b11
    
    return r_bits | (g_bits << 3) | (b_bits << 6)

#########################################
# Copyright Checksum Handling Functions
#########################################

def calculate_copyright_checksum():
    """Calculate and return the copyright graphic checksum"""
    rom_data = rom_cache['j6.6h']
    base_addr = 0x5C0
    byte_count = 0x66
    
    A = B = 0x00
    X = base_addr
    
    for _ in range(byte_count):
        byte_val = rom_data[X]
        B_sum = B + byte_val
        carry_out = 1 if B_sum >= 0x100 else 0
        B = B_sum & 0xFF
        X += 1
        A = (A + carry_out) & 0xFF
    
    return (A << 8) | B

def update_copyright_checksum():
    """Calculate and write the copyright checksum to ROM"""
    checksum = calculate_copyright_checksum()
    
    # Checksum stored at 0xCE25-0xCE26 in 3j.3h (big-endian)
    rom_cache['3j.3h'][0xE25] = (checksum >> 8) & 0xFF  # High byte
    rom_cache['3j.3h'][0xE26] = checksum & 0xFF         # Low byte
    logging.info("Copyright checksum updated: 0x%04X", checksum)

#########################################
# Tile Handling Functions
#########################################

def extract_tile(rom_data, offset, width=16, height=16):
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

def rotate_tile(tile):
    return np.rot90(tile, k=1)

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

def load_tiles():
    all_tiles = []
    for rom_name in ROM_CONFIG['tile_roms']:
        rom_data = rom_cache[rom_name]
        num_tiles = len(rom_data) // tile_size
        for i in range(num_tiles):
            offset = i * tile_size
            tile = extract_tile(rom_data, offset)
            rotated_tile = rotate_tile(tile)
            all_tiles.append(rotated_tile)
    return all_tiles

#########################################
# Map Handling Functions
#########################################

def load_visual_maps():
    map_data = rom_cache[ROM_CONFIG['visual_map_rom']]
    maps = []
    for map_index in range(num_maps):
        start_offset = map_index * visual_map_size
        map_layout = np.zeros((map_height, map_width), dtype=np.uint8)
        for byte_index in range(visual_map_size):
            row = (byte_index % map_height)
            col = (byte_index // map_height)
            flipped_row = map_height - 1 - row
            map_layout[flipped_row, col] = map_data[start_offset + byte_index]
        maps.append(map_layout)
    return maps

def save_visual_maps_to_rom(maps):
    """Save visual maps to ROM cache"""
    map_data = bytearray()
    for map_index in range(len(maps)):
        map_layout = maps[map_index]
        for byte_index in range(visual_map_size):
            row = (byte_index % map_height)
            col = (byte_index // map_height)
            flipped_row = map_height - 1 - row
            map_data.append(map_layout[flipped_row, col])
    rom_cache[ROM_CONFIG['visual_map_rom']][:len(map_data)] = map_data

def load_logical_maps():
    logical_maps = []
    for rom_name in ROM_CONFIG['logical_map_roms']:
        rom_data = rom_cache[rom_name]
        for map_in_rom in range(2):
            start_offset = map_in_rom * logical_map_size
            map_layout = np.zeros((64, 14, 2), dtype=np.uint8)
            for tile_row in range(64):
                row_offset = start_offset + (tile_row * 28)
                for tile_col in range(14):
                    map_layout[tile_row, tile_col, 0] = rom_data[row_offset + tile_col]
                    map_layout[tile_row, tile_col, 1] = rom_data[row_offset + 14 + tile_col]
            logical_maps.append(map_layout)
    return logical_maps

def save_logical_maps_to_rom(logical_maps):
    """Save logical maps to ROM cache"""
    for rom_index, rom_name in enumerate(ROM_CONFIG['logical_map_roms']):
        rom_data = bytearray()
        for map_in_rom in range(2):
            map_index = rom_index * 2 + map_in_rom
            logical_map = logical_maps[map_index]
            for tile_row in range(64):
                for tile_col in range(14):
                    rom_data.append(logical_map[tile_row, tile_col, 0])
                for tile_col in range(14):
                    rom_data.append(logical_map[tile_row, tile_col, 1])
        rom_cache[rom_name][:len(rom_data)] = rom_data

#########################################
# Map Object Handling Functions
#########################################

def load_object_data(map_index, difficulty=0):
    """Load object data for a specific map and difficulty - handles ROM boundaries"""
    block_number = (difficulty * 4) + map_index
    offset = OBJECT_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
    objects = {
        'player_start': {'y': 0, 'x': 0},
        'respawns': [],
        'respawn_count': 0,
        'items': [],
        'teleports': [],
        'spawns': []
    }
    
    # Read player start (3 bytes: YY YY XX)
    pos = offset

    objects['player_start'] = {
        'y': (read_byte_from_roms(pos) << 8) | read_byte_from_roms(pos + 1),
        'x': read_byte_from_roms(pos + 2)
    }
    pos += 3

    # Read respawn points (3 × 3 bytes each)
    for i in range(NUM_RESPAWNS):
        respawn = {
            'y': (read_byte_from_roms(pos) << 8) | read_byte_from_roms(pos + 1),
            'x': read_byte_from_roms(pos + 2)
        }
        objects['respawns'].append(respawn)
        pos += 3

    # Read respawn count
    objects['respawn_count'] = read_byte_from_roms(pos)
    pos += 1

    # Read items (14 × 16 bytes)
    for i in range(NUM_ITEMS):
        item = {
            'active': read_byte_from_roms(pos) == 0x01,
            'y': (read_byte_from_roms(pos + 5) << 8) | read_byte_from_roms(pos + 6),
            'x': read_byte_from_roms(pos + 7),
            'tile_id': read_byte_from_roms(pos + 15)
        }
        objects['items'].append(item)
        pos += 16
    
    pos += 1  # Skip separator

    # Read teleports (6 × 8 bytes: 4 data + 4 padding)
    for i in range(NUM_TELEPORTS):
        teleport = {
            'y': (read_byte_from_roms(pos) << 8) | read_byte_from_roms(pos + 1),
            'bottom_row': read_byte_from_roms(pos + 2),
            'top_row': read_byte_from_roms(pos + 3)
        }
        objects['teleports'].append(teleport)
        pos += 8
    
    # Read spawns (7 × 4 bytes: 3 data + 1 padding)
    for i in range(NUM_SPAWNS):
        spawn = {
            'y': (read_byte_from_roms(pos) << 8) | read_byte_from_roms(pos + 1),
            'x': read_byte_from_roms(pos + 2)
        }
        objects['spawns'].append(spawn)
        pos += 4
    
    return objects

def save_object_data(objects, map_index, difficulty=0):
    """Save object data back to ROM - handles ROM boundaries"""
    block_number = (difficulty * 4) + map_index
    offset = OBJECT_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
    pos = offset
    # Write player start
    write_byte_to_roms(pos, objects['player_start']['y'] & 0xFF)
    write_byte_to_roms(pos + 1, (objects['player_start']['y'] >> 8) & 0xFF)
    write_byte_to_roms(pos + 2, objects['player_start']['x'])
    pos += 3
    
    # Write respawns
    for respawn in objects['respawns']:
        write_byte_to_roms(pos, respawn['y'] & 0xFF)
        write_byte_to_roms(pos + 1, (respawn['y'] >> 8) & 0xFF)
        write_byte_to_roms(pos + 2, respawn['x'])
        pos += 3
    
    # Write respawn count
    write_byte_to_roms(pos, objects['respawn_count'])
    pos += 1
    
    # Write items
    for item in objects['items']:
        write_byte_to_roms(pos, 0x01 if item['active'] else 0x00)
        for i in range(1, 5):
            write_byte_to_roms(pos + i, 0x00)
        write_byte_to_roms(pos + 5, item['y'] & 0xFF)
        write_byte_to_roms(pos + 6, (item['y'] >> 8) & 0xFF)
        write_byte_to_roms(pos + 7, item['x'])
        for i in range(8, 15):
            write_byte_to_roms(pos + i, 0x00)
        write_byte_to_roms(pos + 15, item['tile_id'])
        pos += 16
    
    write_byte_to_roms(pos, 0x00)
    pos += 1
    
    # Write teleports
    for teleport in objects['teleports']:
        write_byte_to_roms(pos, teleport['y'] & 0xFF)
        write_byte_to_roms(pos + 1, (teleport['y'] >> 8) & 0xFF)
        write_byte_to_roms(pos + 2, teleport['bottom_row'])
        write_byte_to_roms(pos + 3, teleport['top_row'])
        for i in range(4, 8):
            write_byte_to_roms(pos + i, 0x00)
        pos += 8
    
    # Write spawns
    for spawn in objects['spawns']:
        write_byte_to_roms(pos, spawn['y'] & 0xFF)
        write_byte_to_roms(pos + 1, (spawn['y'] >> 8) & 0xFF)
        write_byte_to_roms(pos + 2, spawn['x'])
        write_byte_to_roms(pos + 3, 0x00)
        pos += 4
    
#########################################
# High Score Handling Functions
#########################################

def load_high_scores():
    """Load high score data from ROM"""
    rom_data = rom_cache[ROM_CONFIG['high_score_rom']]
    high_scores = []
    # Read HIGH SCORE (first entry)
    high_scores.append({
        'score': [rom_data[HIGH_SCORE_OFFSET + j] for j in range(3)],
        'name': '',
        'stage': 0})
    # Read 7 ranked entries
    for i in range(HIGH_SCORE_OFFSET + 3, HIGH_SCORE_OFFSET + 3 + NUM_HIGH_SCORES * 6, 6):
        score_bytes = rom_data[i:i+3]
        name_bytes = rom_data[i+3:i+6]
        # Convert name bytes to ASCII string
        name = ''.join([chr(b) if 32 <= b < 127 else '?' for b in name_bytes])
        high_scores.append({
            'score': score_bytes,
            'name': name,
            'stage': 0})  # Stage comes later
    # Read 7 stages for ranked entries
    for i in range(NUM_HIGH_SCORES):
        high_scores[i + 1]['stage'] = rom_data[HIGH_STAGE_OFFSET + i]
    return high_scores

def save_high_scores(high_scores):
    """Save high score data back to ROM"""
    rom_data = rom_cache[ROM_CONFIG['high_score_rom']]
    # Write HIGH SCORE (first entry - score only, no name/stage)
    for j, byte_val in enumerate(high_scores[0]['score']):
        rom_data[HIGH_SCORE_OFFSET + j] = byte_val
    # Write 7 ranked entries (score + name)
    for i in range(HIGH_SCORE_OFFSET + 3, HIGH_SCORE_OFFSET + 3 + NUM_HIGH_SCORES * 6, 6):
        entry = high_scores[((i - HIGH_SCORE_OFFSET - 3) // 6) + 1]
        # Write score bytes
        for j, byte_val in enumerate(entry['score']):
            rom_data[i + j] = byte_val
        # Write name bytes (convert to ASCII)
        name_padded = (entry['name'] + '   ')[:3]  # Pad or truncate to 3 chars
        for j, char in enumerate(name_padded):
            rom_data[i + 3 + j] = ord(char.upper())
    # Write stages
    for i in range(NUM_HIGH_SCORES):
        rom_data[HIGH_STAGE_OFFSET + i] = high_scores[i + 1]['stage']
    
def bcd_to_int(bcd_bytes):
    """Convert 3-byte BCD to integer (e.g., [0x03, 0x58, 0x40] -> 35840)"""
    result = 0
    for byte_val in bcd_bytes:
        result = result * 100 + ((byte_val >> 4) * 10) + (byte_val & 0x0F)
    return result

def int_to_bcd(value):
    """Convert integer to 3-byte BCD (e.g., 35840 -> [0x03, 0x58, 0x40])"""
    # Clamp to max 999999
    value = min(999999, max(0, value))
    
    bcd_bytes = []
    for _ in range(3):
        low_digit = value % 10
        value //= 10
        high_digit = value % 10
        value //= 10
        bcd_bytes.insert(0, (high_digit << 4) | low_digit)
    
    return bcd_bytes


root = tk.Tk()
root.title("Multiple Menus Example")

menubar = tk.Menu(root)

# --- File Menu ---
filemenu = tk.Menu(menubar, tearoff=False)
filemenu.add_command(label="-- File Operations --", state="disabled")
filemenu.add_separator()
filemenu.add_command(label="-- Loading --", state="disabled")
filemenu.add_command(label="Reload Original ROMs From Zip", command=lambda: load_all("Zip"))
filemenu.add_command(label="Open ROMs", command=lambda: load_all())
filemenu.add_command(label="Open ROMs From Folder", command=lambda: load_all("Folder"))
filemenu.add_separator()
filemenu.add_command(label="-- Saving --", state="disabled")
filemenu.add_command(label="Save ROMs", command=lambda: print("Save ROMS!"))
filemenu.add_command(label="Save ROMs To Folder", command=lambda: print("Save ROMS To Specified Folder!"))
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

# --- Project Menu ---
projectmenu = tk.Menu(menubar, tearoff=False)
projectmenu.add_command(label="-- Map Editor --", state="disabled")
projectmenu.add_command(label="Edit Maps", command=lambda: print("Edit Maps!"))
projectmenu.add_separator()
projectmenu.add_command(label="-- Tile / Graphics Editor --", state="disabled")
projectmenu.add_command(label="Edit Tiles", command=lambda: print("Edit Tiles!"))
projectmenu.add_command(label="Edit Fonts", command=lambda: print("Edit Fonts!"))
projectmenu.add_command(label="Edit UI Graphics", command=lambda: print("Edit UI Graphics!"))
projectmenu.add_command(label="Edit Treasures", command=lambda: print("Edit Treastures!"))
projectmenu.add_separator()
projectmenu.add_command(label="-- Data Editor --", state="disabled")
projectmenu.add_command(label="High Scores", command=lambda: print("Edit High Scores"))
projectmenu.add_command(label="Palette", command=lambda: print("Edit Palette"))
menubar.add_cascade(label="Editor", menu=projectmenu)

# --- Help Menu ---
helpmenu = tk.Menu(menubar, tearoff=False)
helpmenu.add_command(label="About", command=lambda: print("About..."))
menubar.add_cascade(label="Help", menu=helpmenu)

# Attach to window
root.config(menu=menubar)
all_tiles, visual_maps, logical_maps, palettes, high_scores = load_all("Zip")
create_window_icon(root, all_tiles, palettes)

root.mainloop()