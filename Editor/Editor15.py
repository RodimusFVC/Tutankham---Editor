import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import shutil
from datetime import datetime
import logging
from colorlog import ColoredFormatter

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
# Rom Handling Functions
#########################################

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

#########################################
# Editor Class + Functions
#########################################

class MapEditor:
    def __init__(self, visual_maps, logical_maps, all_tiles, palettes):
        self.visual_maps = visual_maps
        self.logical_maps = logical_maps
        self.all_tiles = all_tiles
        self.palettes = palettes
        self.high_scores = load_high_scores()
        self.selected_tile = 0
        self.selected_map = 0
        self.difficulty = 0
        self.tile_images = []
        self.zoom_level = 3.0
        self.modified = False
        
        # Composite object selection
        self.selected_composite = None
        self.selected_spawner_dir = 'right'

        # Player start tracking
        self.selected_player_start = None
        self.player_start_ghost_pos = None

        # Palette editor tracking
        self.selected_color_idx = None

        # Map/Difficulty tracking
        self.map_buttons = {}  # Store references to map/difficulty buttons
        self.selected_map_btn = None
        self.selected_diff_btn = None
        
        # Door tracking
        self.door_positions = {}
        self.selected_door = None
        self.door_drag_start = None
        self.door_ghost_pos = None
        
        # Teleporter placement state
        self.teleporter_first_pos = None
        
        # Load object data for ALL difficulties
        self.object_data = {}
        for diff in range(NUM_DIFFICULTIES):
            self.object_data[diff] = {}
            for i in range(num_maps):
                self.object_data[diff][i] = load_object_data(i, diff)

        # Load map configuration data (spawn rate, time limit, unknown bytes)
        self.map_config = {}
        for diff in range(NUM_DIFFICULTIES):
            self.map_config[diff] = {}
            for map_idx in range(num_maps):
                self.map_config[diff][map_idx] = self.load_map_config(map_idx, diff)

        # Validate and fix invalid teleporters (ROM bug cleanup)
        self.validate_teleporters()

        # Place spawn tiles in visual maps based on object data (use difficulty 0 as reference)
        for map_idx in range(num_maps):
            objects = self.object_data[0][map_idx]

            # Place player start tile
            if objects['player_start']['y'] != 0:
                row_from_bottom = objects['player_start']['x'] // 0x08  # Row from bottom
                row = (map_height - 1) - row_from_bottom  # Flip to top-indexed
                col = objects['player_start']['y'] // 0x08

                if 0 <= row < map_height and 0 <= col < map_width:
                    self.visual_maps[map_idx][row, col] = 0x29

            # Place respawn flame tiles
            for i in range(objects['respawn_count']):
                respawn = objects['respawns'][i]
                if respawn['y'] != 0:
                    row_from_bottom = respawn['x'] // 0x08
                    row = (map_height - 1) - row_from_bottom  # Flip to top-indexed
                    col = respawn['y'] // 0x08
                    if 0 <= row < map_height and 0 <= col < map_width:
                        self.visual_maps[map_idx][row, col] = 0x17

            # Place keyhole tiles
            for item in objects['items']:
                if item['active'] and item['tile_id'] == 0x72:
                    col = item['y'] // 0x08
                    row_from_bottom = item['x'] // 0x08
                    row = (map_height - 1) - row_from_bottom
                    if 0 <= row < map_height and 0 <= col < map_width:
                        self.visual_maps[map_idx][row, col] = 0x72
       
        # Find doors
        for i in range(num_maps):
            self.door_positions[i] = self.find_door(i)

        # Find spawners
        self.spawner_positions = {}
        for i in range(num_maps):
            self.spawner_positions[i] = self.find_spawners(i)
        
        # Find teleporters
        self.teleporter_positions = {}
        for i in range(num_maps):
            self.teleporter_positions[i] = self.find_teleporters(i)

        # Validate and fix filled boxes on load
        self.validate_filled_boxes()
        
        self.root = tk.Tk()
        self.root.title(f"Tutankham Map Editor {EDITOR_VERSION}")
        self.root.geometry("1800x1000")
        
        # Create tkinter variables
        self.show_grid = tk.BooleanVar(value=False)
        self.show_objects = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.coord_var = tk.StringVar(value="")
        
        self.setup_ui()
        self.render_tile_palette()
        self.display_map()
        self.update_config_display()
        self.update_counters()
        self.create_window_icon()
        
    def validate_filled_boxes(self):
        """Check for filled boxes on visual layer and fix them"""
        for map_idx in range(num_maps):
            visual_map = self.visual_maps[map_idx]
            for row in range(map_height):
                for col in range(map_width):
                    tile = visual_map[row, col]
                    if tile in FILLED_TO_EMPTY:
                        x = row * 0x08
                        y = col * 0x08
                        
                        has_object = False
                        for item in self.object_data[0][map_idx]['items']:
                            if item['active'] and item['x'] == x and item['y'] == y:
                                has_object = True
                                break
                        
                        if has_object:
                            visual_map[row, col] = FILLED_TO_EMPTY[tile]
                        else:
                            visual_map[row, col] = empty_path_tile

    def validate_teleporters(self):
        """Remove teleporter entries that don't have matching visual tiles"""
        for map_idx in range(num_maps):
            visual_map = self.visual_maps[map_idx]
        
            # Check all difficulties for this map
            for diff in range(NUM_DIFFICULTIES):
                objects = self.object_data[diff][map_idx]
            
                for tp_idx, tp in enumerate(objects['teleports']):
                    if tp['y'] == 0:
                        continue  # Already empty
                
                    # Center column
                    center_col = tp['y'] // 0x08
                
                    # Columns span: center-1, center, center+1
                    left_col = (tp['y'] - 0x08) // 0x08
                    right_col = (tp['y'] + 0x08) // 0x08
                
                    # Rows
                    bottom_row = tp['bottom_row'] // 0x08
                    top_row = tp['top_row'] // 0x08
                
                    # Skip if columns are out of bounds
                    if left_col < 0 or right_col >= map_width:
                        tp['y'] = 0
                        tp['top_row'] = 0
                        tp['bottom_row'] = 0
                        continue
                
                    # Expected pattern across columns: [100, 38, 101]
                    expected_pattern = [100, 38, 101]
                    columns = [left_col, center_col, right_col]
                
                    valid = True
                
                    # Check bottom pillar
                    bottom_row_flipped = (map_height - 1) - bottom_row
                    if bottom_row_flipped < 0 or bottom_row_flipped >= map_height:
                        valid = False
                    else:
                        for i, col in enumerate(columns):
                            actual_tile = visual_map[bottom_row_flipped, col]
                            expected_tile = expected_pattern[i]
                            if actual_tile != expected_tile:
                                valid = False
                
                    # Check top pillar
                    if valid:
                        top_row_flipped = (map_height - 1) - top_row
                        if top_row_flipped < 0 or top_row_flipped >= map_height:
                            valid = False
                        else:
                            for i, col in enumerate(columns):
                                actual_tile = visual_map[top_row_flipped, col]
                                expected_tile = expected_pattern[i]
                                if actual_tile != expected_tile:
                                    valid = False
                
                    if not valid:
                        tp['y'] = 0
                        tp['top_row'] = 0
                        tp['bottom_row'] = 0

    def load_map_config(self, map_index, difficulty=0):
        """Load map configuration block (first 11 bytes of object block)"""
        block_number = (difficulty * 4) + map_index
        offset = CONFIG_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
        config = {
            'logical_map_ptr': (read_byte_from_roms(offset) << 8) | read_byte_from_roms(offset + 1),
            'visual_map_ptr': (read_byte_from_roms(offset + 2) << 8) | read_byte_from_roms(offset + 3),
            'spawn_rate': read_byte_from_roms(offset + 4),
            'time_limit': read_byte_from_roms(offset + 5),
            'unknown_bytes': [
                read_byte_from_roms(offset + 6),
                read_byte_from_roms(offset + 7),
                read_byte_from_roms(offset + 8),
                read_byte_from_roms(offset + 9),
                read_byte_from_roms(offset + 10)
            ]
        }
    
        return config

    def save_map_config(self, map_index, difficulty=0):
        """Save map configuration block back to ROM"""
        block_number = (difficulty * 4) + map_index
        offset = CONFIG_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
        config = self.map_config[difficulty][map_index]
    
        # Write map pointers
        write_byte_to_roms(offset, (config['logical_map_ptr'] >> 8) & 0xFF)
        write_byte_to_roms(offset + 1, config['logical_map_ptr'] & 0xFF)
        write_byte_to_roms(offset + 2, (config['visual_map_ptr'] >> 8) & 0xFF)
        write_byte_to_roms(offset + 3, config['visual_map_ptr'] & 0xFF)
    
        # Write spawn rate and time limit
        write_byte_to_roms(offset + 4, config['spawn_rate'])
        write_byte_to_roms(offset + 5, config['time_limit'])
    
        # Write unknown bytes
        for i, byte_val in enumerate(config['unknown_bytes']):
            write_byte_to_roms(offset + 6 + i, byte_val)
    
    def setup_ui(self):
        # Calculate window size based on map at 3x zoom
        map_display_width = map_width * 16 * 3  # 64 * 16 * 3 = 3072
        map_display_height = map_height * 16 * 3  # 12 * 16 * 3 = 576
    
        left_panel_width = 255
        palette_height = 250
    
        window_width = left_panel_width + map_display_width + 40  # Add padding
        window_height = map_display_height + palette_height + 100  # Add space for controls
    
        self.root.geometry(f"{window_width}x{window_height}")
    
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel
        self.left_panel = ttk.Frame(main_frame, width=left_panel_width)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.left_panel.pack_propagate(False)

        # Build mode selector and initial UI
        self.build_mode_selector()
        self.rebuild_left_panel_for_map_editor()

        # Right panel
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        map_frame = ttk.LabelFrame(right_panel, text="Map Editor")
        map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        canvas_frame = ttk.Frame(map_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.map_canvas = tk.Canvas(canvas_frame, bg='black', width=map_display_width, height=map_display_height)
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.map_canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.map_canvas.yview)
        
        self.map_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.map_canvas.grid(row=0, column=0, sticky='nsew')
        h_scroll.grid(row=1, column=0, sticky='ew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.map_canvas.bind("<Button-1>", self.on_map_click)
        self.map_canvas.bind("<Motion>", self.on_map_hover)
        self.map_canvas.bind("<B1-Motion>", self.on_map_drag)
        self.map_canvas.bind("<ButtonRelease-1>", self.on_map_release)
        self.map_canvas.bind("<Button-3>", self.on_map_right_click)
        self.root.bind("<Escape>", self.on_escape)
        
        palette_frame = ttk.LabelFrame(right_panel, text="Tile Palette")
        palette_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=5, pady=5)
        
        palette_canvas_frame = ttk.Frame(palette_frame)
        palette_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.palette_canvas = tk.Canvas(palette_canvas_frame, height=palette_height, bg='#2b2b2b')
        palette_scroll_h = ttk.Scrollbar(palette_canvas_frame, orient=tk.HORIZONTAL, 
                                        command=self.palette_canvas.xview)
        palette_scroll_v = ttk.Scrollbar(palette_canvas_frame, orient=tk.VERTICAL,
                                        command=self.palette_canvas.yview)
        
        self.palette_canvas.configure(xscrollcommand=palette_scroll_h.set,
                                     yscrollcommand=palette_scroll_v.set)
        self.palette_canvas.grid(row=0, column=0, sticky='nsew')
        palette_scroll_h.grid(row=1, column=0, sticky='ew')
        palette_scroll_v.grid(row=0, column=1, sticky='ns')
        
        palette_canvas_frame.grid_rowconfigure(0, weight=1)
        palette_canvas_frame.grid_columnconfigure(0, weight=1)
        
        status_frame = ttk.Frame(right_panel)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

    def update_config_display(self):
        """Update config UI with current map/difficulty values"""
        config = self.map_config[self.difficulty][self.selected_map]
        self.time_limit_var.set(str(config['time_limit']))
        self.spawn_rate_var.set(str(config['spawn_rate']))

    def update_counters(self):
        """Update all object counters and validation"""
        objects = self.object_data[self.difficulty][self.selected_map]
        
        active_items = sum(1 for item in objects['items'] if item['active'])
        self.items_label.config(text=f"Items: {active_items}/14")
        
        active_teleports = sum(1 for tp in objects['teleports'] if tp['y'] != 0)
        self.teleports_label.config(text=f"Teleports: {active_teleports}/6")
        
        active_spawners = sum(1 for spawn in objects['spawns'] if spawn['y'] != 0)
        self.spawners_label.config(text=f"Spawners: {active_spawners}/7")
        
        self.respawns_label.config(text=f"Respawns: {objects['respawn_count']}/3")
        
        keys = sum(1 for item in objects['items'] if item['active'] and item['tile_id'] == 0x70)
        keyholes = sum(1 for item in objects['items'] if item['active'] and item['tile_id'] == 0x72)
        
        if keyholes > keys:
            self.validation_label.config(text=f"⚠ WARNING: {keyholes} keyholes but only {keys} keys!")
        else:
            self.validation_label.config(text="")
    
    def can_edit_map(self):
        if self.difficulty > 0:
            messagebox.showwarning("Edit Locked", 
                "Visual/logical map editing is only allowed in Difficulty 1.\n"
                "Higher difficulties only allow enabling/disabling objects.")
            return False
        return True
    
    def find_door(self, map_index):
        visual_map = self.visual_maps[map_index]
        
        for row in range(map_height - 2):
            for col in range(map_width - 2):
                is_door = True
                for dr in range(3):
                    for dc in range(3):
                        expected_tile = DOOR_TILES[dr, dc]
                        actual_tile = visual_map[row + dr, col + dc]
                        if expected_tile != actual_tile:
                            is_door = False
                            break
                    if not is_door:
                        break
                
                if is_door:
                    return (row, col)
        
        return None

    def find_spawners(self, map_index):
        """Find all spawner positions on a map by scanning for patterns"""
        visual_map = self.visual_maps[map_index]
        spawners = []
    
        # Check each spawner configuration
        for direction, config in SPAWNER_CONFIGS.items():
            tiles = config['tiles']
            h, w = tiles.shape
        
            for row in range(map_height - h + 1):
                for col in range(map_width - w + 1):
                    # Check if this position contains the spawner pattern
                    is_spawner = True
                    for dr in range(h):
                        for dc in range(w):
                            expected_tile = tiles[dr, dc]
                            actual_tile = visual_map[row + dr, col + dc]
                            if expected_tile != actual_tile:
                                is_spawner = False
                                break
                        if not is_spawner:
                            break
                
                    if is_spawner:
                        spawners.append({
                            'row': row,
                            'col': col,
                            'width': w,
                            'height': h,
                            'direction': direction
                        })
    
        return spawners

    def find_teleporters(self, map_index):
        """Find all teleporter columns by checking object data"""
        objects = self.object_data[0][map_index]  # Use difficulty 0 as reference
        teleporter_cols = []
    
        for tp in objects['teleports']:
            if tp['y'] != 0:
                col = tp['y'] // 0x08
                if col not in teleporter_cols:
                    teleporter_cols.append(col)
    
        return teleporter_cols

    
    def is_door_tile(self, row, col):
        door_pos = self.door_positions.get(self.selected_map)
        if door_pos is None:
            return False
        
        door_row, door_col = door_pos
        return (door_row <= row < door_row + 3 and 
                door_col <= col < door_col + 3)

    def is_spawner_tile(self, row, col):
        """Check if a tile position is part of a spawner"""
        spawners = self.spawner_positions.get(self.selected_map, [])
        for spawner in spawners:
            if (spawner['row'] <= row < spawner['row'] + spawner['height'] and 
                spawner['col'] <= col < spawner['col'] + spawner['width']):
                return spawner
        return None
    
    def clear_door(self, row, col):
        visual_map = self.visual_maps[self.selected_map]
        logical_map = self.logical_maps[self.selected_map]
        
        for dr in range(3):
            for dc in range(3):
                visual_map[row + dr, col + dc] = empty_path_tile
                logical_row = col + dc
                logical_col = row + dr + 1
                logical_map[logical_row, logical_col] = [0x00, 0x00]
    
    def place_door_at(self, row, col):
        if row + 3 > map_height or col + 3 > map_width:
            return False
        
        visual_map = self.visual_maps[self.selected_map]
        logical_map = self.logical_maps[self.selected_map]
        
        for dr in range(3):
            for dc in range(3):
                visual_map[row + dr, col + dc] = DOOR_TILES[dr, dc]
                logical_row = col + dc
                logical_col = row + dr + 1
                logical_map[logical_row, logical_col] = DOOR_LOGICAL[dr, dc]
        
        return True
    
    def set_difficulty(self, diff):
        self.difficulty = diff
        self.display_map()
        self.update_config_display()
        self.update_counters()
        self.status_var.set(f"Switched to Difficulty {diff + 1}")

    def set_time_limit(self):
        """Set time limit for current map/difficulty"""
        try:
            new_limit = int(self.time_limit_var.get())
            if new_limit < 0 or new_limit > 255:
                messagebox.showwarning("Invalid Value", "Time limit must be 0-255 seconds")
                return
            
            self.map_config[self.difficulty][self.selected_map]['time_limit'] = new_limit
            self.mark_modified()
            self.status_var.set(f"Time limit set to {new_limit} seconds")
        except ValueError:
            messagebox.showwarning("Invalid Value", "Please enter a valid number")

    def set_spawn_rate(self):
        """Set spawn rate for current map/difficulty"""
        try:
            new_rate = int(self.spawn_rate_var.get())
            if new_rate < 1 or new_rate > 14:
                messagebox.showwarning("Invalid Value", 
                    "Spawn rate must be 1-14 (game uses 5-8, higher values may crash)")
                return
            
            self.map_config[self.difficulty][self.selected_map]['spawn_rate'] = new_rate
            self.mark_modified()
            self.status_var.set(f"Spawn rate set to {new_rate}")
        except ValueError:
            messagebox.showwarning("Invalid Value", "Please enter a valid number")

    def on_mode_change(self, event=None):
        mode = self.editor_mode.get()
        if mode == "Map Editor":
            self.show_map_editor()
            # TODO: Show map editor UI
        elif mode == "Graphics Editor":
            self.show_graphics_editor()
            # TODO: Show graphics editor UI
        elif mode == "Data Editor":
            self.show_data_editor()
            # TODO: Show Data editor UI

    def show_map_editor(self):
        """Show Map Editor UI"""
        # Clear left panel (except mode selector)
        self.rebuild_left_panel_for_map_editor()
        self.display_map()
        self.status_var.set("Map Editor mode")

    def show_graphics_editor(self):
        """Show Graphics Editor UI"""
        self.rebuild_left_panel_for_graphics_editor()
        self.status_var.set("Graphics Editor mode")

    def show_data_editor(self):
        """Show Data Editor UI"""
        self.rebuild_left_panel_for_data_editor()
        self.display_data_editor()
        self.status_var.set("Data Editor mode")

    def rebuild_left_panel_for_map_editor(self):
        """Rebuild left panel with map editor controls"""
        # Destroy all children except the mode selector at the top (first 3 widgets)
        children = list(self.left_panel.winfo_children())
        for widget in children[3:]:
            widget.destroy()
    
        # Map Selection
        ttk.Label(self.left_panel, text="Map/Difficulty Selection", font=('Arial', 10, 'bold')).pack(pady=5)
    
        # Recreate map buttons
        self.map_buttons = {}
        for i in range(num_maps):
            map_frame = ttk.Frame(self.left_panel)
            map_frame.pack(fill=tk.X, padx=5, pady=2)
            
            map_btn = ttk.Button(map_frame, text=f"Map {i + 1}", width=7,
                                command=lambda i=i: self.on_map_select(i))
            map_btn.pack(side=tk.LEFT, padx=2)
            self.map_buttons[('map', i)] = map_btn
            
            for d in range(NUM_DIFFICULTIES):
                diff_btn = ttk.Button(map_frame, text=str(d+1), width=2,
                                     command=lambda i=i, d=d: self.select_map_and_difficulty(i, d))
                diff_btn.pack(side=tk.LEFT, padx=1)
                self.map_buttons[(i, d)] = diff_btn
    
        self.update_selection_highlight()
    
        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
        # Map Config
        ttk.Label(self.left_panel, text="Map Config", font=('Arial', 10, 'bold')).pack(pady=5)
        config_frame = ttk.Frame(self.left_panel)
        config_frame.pack(fill=tk.X, padx=5)
    
        # Time Limit
        time_frame = ttk.Frame(config_frame)
        time_frame.pack(fill=tk.X, pady=2)
        ttk.Label(time_frame, text="Time Limit:").pack(side=tk.LEFT)
        self.time_limit_var = tk.StringVar()
        time_entry = ttk.Entry(time_frame, textvariable=self.time_limit_var, width=5)
        time_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(time_frame, text="seconds").pack(side=tk.LEFT)
        ttk.Button(time_frame, text="Set", width=5, command=self.set_time_limit).pack(side=tk.LEFT, padx=5)
    
        # Spawn Rate
        spawn_frame = ttk.Frame(config_frame)
        spawn_frame.pack(fill=tk.X, pady=2)
        ttk.Label(spawn_frame, text="Spawn Rate:").pack(side=tk.LEFT)
        self.spawn_rate_var = tk.StringVar()
        spawn_entry = ttk.Entry(spawn_frame, textvariable=self.spawn_rate_var, width=5)
        spawn_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(spawn_frame, text="(1-14)").pack(side=tk.LEFT)
        ttk.Button(spawn_frame, text="Set", width=5, command=self.set_spawn_rate).pack(side=tk.LEFT, padx=5)
    
        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
        # Object Counts
        ttk.Label(self.left_panel, text="Object Counts", font=('Arial', 10, 'bold')).pack(pady=5)
        self.counter_frame = ttk.Frame(self.left_panel)
        self.counter_frame.pack(fill=tk.X, padx=5)
    
        self.items_label = ttk.Label(self.counter_frame, text="Items: 0/14")
        self.items_label.pack(anchor=tk.W)
        self.teleports_label = ttk.Label(self.counter_frame, text="Teleports: 0/6")
        self.teleports_label.pack(anchor=tk.W)
        self.spawners_label = ttk.Label(self.counter_frame, text="Spawners: 0/7")
        self.spawners_label.pack(anchor=tk.W)
        self.respawns_label = ttk.Label(self.counter_frame, text="Respawns: 0/3")
        self.respawns_label.pack(anchor=tk.W)
    
        self.validation_label = ttk.Label(self.counter_frame, text="", foreground="red",
                                         font=('Arial', 8, 'bold'))
        self.validation_label.pack(anchor=tk.W, pady=5)
        
        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
        # Display
        ttk.Label(self.left_panel, text="Display", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Checkbutton(self.left_panel, text="Show Grid", variable=self.show_grid,
                       command=self.display_map).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(self.left_panel, text="Show Objects", variable=self.show_objects,
                       command=self.display_map).pack(anchor=tk.W, padx=5)
    
        coord_frame = ttk.Frame(self.left_panel)
        coord_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(coord_frame, text="Coordinates:").pack(side=tk.LEFT)
        ttk.Label(coord_frame, textvariable=self.coord_var).pack(side=tk.LEFT, padx=5)
    
        zoom_frame = ttk.Frame(self.left_panel)
        zoom_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="-", width=3, command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text=f"{int(self.zoom_level)}x")
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="+", width=3, command=self.zoom_in).pack(side=tk.LEFT, padx=2)
    
        # Show Selected Tile
        selected_frame = ttk.Frame(self.left_panel)
        selected_frame.pack(fill=tk.X, padx=5, pady=10)
        self.tile_info_var = tk.StringVar(value="Selected Tile: None")
        ttk.Label(selected_frame, textvariable=self.tile_info_var).pack(side=tk.LEFT, pady=2)
        self.selected_tile_preview = tk.Label(selected_frame, bg='#2b2b2b')
        self.selected_tile_preview.pack(side=tk.LEFT, padx=10)
    
        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
        # Save buttons at bottom
        status_frame = ttk.Frame(self.left_panel)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_frame, text="Write Files", font=('Arial', 10, 'bold')).pack(pady=5)
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save As", command=self.save_file_as).pack(side=tk.RIGHT, padx=2)
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)
    
        # Update displays
        self.update_config_display()
        self.update_counters()

    def build_mode_selector(self):
        """Build the mode selection dropdown (always visible at top)"""
        ttk.Label(self.left_panel, text="Editor Mode", font=('Arial', 10, 'bold')).pack(pady=5)
        self.editor_mode = tk.StringVar(value="Map Editor")
        mode_dropdown = ttk.Combobox(self.left_panel, textvariable=self.editor_mode, 
                                     values=["Map Editor", "Graphics Editor", "Data Editor"], 
                                     state="readonly", width=20)
        mode_dropdown.pack(fill=tk.X, padx=5, pady=2)
        mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_change)
    
        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

    def rebuild_left_panel_for_graphics_editor(self):
        """Rebuild left panel with graphics editor controls"""
        # Destroy all children except mode selector
        children = list(self.left_panel.winfo_children())
        for widget in children[3:]:
            widget.destroy()
    
        # Tile Type Selection
        ttk.Label(self.left_panel, text="Tile Type", font=('Arial', 10, 'bold')).pack(pady=5)
        self.graphics_tile_type = tk.StringVar(value="Map Tiles (16x16)")
        tile_type_dropdown = ttk.Combobox(self.left_panel, textvariable=self.graphics_tile_type,
                                         values=["Map Tiles (16x16)", "Font (8x8)"],
                                         state="readonly", width=20)
        tile_type_dropdown.pack(fill=tk.X, padx=5, pady=2)
        tile_type_dropdown.bind("<<ComboboxSelected>>", self.on_graphics_tile_type_change)
        
        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Placeholder for now
        ttk.Label(self.left_panel, text="Graphics Editor", font=('Arial', 10)).pack(pady=20)
        ttk.Label(self.left_panel, text="Coming soon...", font=('Arial', 8)).pack()
    
        # Save buttons at bottom
        status_frame = ttk.Frame(self.left_panel)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_frame, text="Write Files", font=('Arial', 10, 'bold')).pack(pady=5)
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save As", command=self.save_file_as).pack(side=tk.RIGHT, padx=2)
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)

    def rebuild_left_panel_for_data_editor(self):
        """Rebuild left panel with data editor controls"""
        # Destroy all children except mode selector
        children = list(self.left_panel.winfo_children())
        for widget in children[3:]:
            widget.destroy()

        # Data Type Selection
        ttk.Label(self.left_panel, text="Data Type", font=('Arial', 10, 'bold')).pack(pady=5)
        self.data_editor_type = tk.StringVar(value="High Scores")
        data_type_dropdown = ttk.Combobox(self.left_panel, textvariable=self.data_editor_type,
                                        values=["High Scores", "Palettes"],
                                        state="readonly", width=20)
        data_type_dropdown.pack(fill=tk.X, padx=5, pady=2)
        data_type_dropdown.bind("<<ComboboxSelected>>", self.on_data_editor_type_change)

        ttk.Separator(self.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Content frame for data editor (will be rebuilt based on selection)
        self.data_editor_content = ttk.Frame(self.left_panel)
        self.data_editor_content.pack(fill=tk.BOTH, expand=True)

        # Save buttons at bottom
        status_frame = ttk.Frame(self.left_panel)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_frame, text="Write Files", font=('Arial', 10, 'bold')).pack(pady=5)
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save As", command=self.save_file_as).pack(side=tk.RIGHT, padx=2)
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)
        
        # Load initial content
        self.update_data_editor_content()

    def on_graphics_tile_type_change(self, event=None):
        """Handle tile type changes in graphics editor"""
        tile_type = self.graphics_tile_type.get()
        self.status_var.set(f"Switched to {tile_type}")
        # TODO: Update right panel display

    def on_data_editor_type_change(self, event=None):
        """Handle data type changes in data editor"""
        data_type = self.data_editor_type.get()
        self.status_var.set(f"Switched to {data_type}")
        self.update_data_editor_content()

    def update_data_editor_content(self):
        """Update the data editor content area based on selected type"""
        # Clear existing content
        for widget in self.data_editor_content.winfo_children():
            widget.destroy()
        
        data_type = self.data_editor_type.get()
        
        if data_type == "High Scores":
            self.build_high_score_editor()
        elif data_type == "Palettes":
            self.build_palette_editor()
        
        # Update right panel display
        self.display_data_editor()
    
    def build_high_score_editor(self):
        """Build the high score editor interface in the content area"""
        # Instructions
        info_label = ttk.Label(self.data_editor_content, 
                              text="Edit high scores below.\nClick on an entry to edit.",
                              font=('Arial', 8), justify=tk.LEFT)
        info_label.pack(pady=5, padx=5, anchor=tk.W)
        
        # Utility buttons
        button_frame = ttk.Frame(self.data_editor_content)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Sort by Score", 
                  command=self.sort_high_scores).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_high_scores).pack(side=tk.LEFT, padx=2)
        
        # Create scrollable frame for entries
        canvas = tk.Canvas(self.data_editor_content, height=350)
        scrollbar = ttk.Scrollbar(self.data_editor_content, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store entry widgets for later access
        self.high_score_widgets = []
        
        # HIGH SCORE entry (first one, no name/stage)
        self.build_high_score_row(scrollable_frame, 0, "HIGH SCORE", is_top_score=True)
        
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Regular entries (1st through 7th)
        rank_names = ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH"]
        for i in range(NUM_HIGH_SCORES):
            self.build_high_score_row(scrollable_frame, i + 1, rank_names[i])
    
    def build_high_score_row(self, parent, index, label, is_top_score=False):
        """Build a single high score entry row"""
        frame = ttk.LabelFrame(parent, text=label, padding=5)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        entry = self.high_scores[index]
        score_int = bcd_to_int(entry['score'])
        
        if is_top_score:
            # HIGH SCORE is read-only and synced with 1st place
            score_frame = ttk.Frame(frame)
            score_frame.pack(fill=tk.X, pady=2)
            ttk.Label(score_frame, text="Score:", width=8).pack(side=tk.LEFT)
            ttk.Label(score_frame, text=str(score_int), width=10, 
                     font=('Courier', 10, 'bold'), foreground='cyan').pack(side=tk.LEFT, padx=5)
            ttk.Label(score_frame, text="(auto-synced with 1st place)", 
                     font=('Arial', 7), foreground='gray').pack(side=tk.LEFT)
            
            # No update button needed for HIGH SCORE
            return
        
        # Score field (editable for ranked entries)
        score_frame = ttk.Frame(frame)
        score_frame.pack(fill=tk.X, pady=2)
        ttk.Label(score_frame, text="Score:", width=8).pack(side=tk.LEFT)
        score_var = tk.StringVar(value=str(score_int))
        score_entry = ttk.Entry(score_frame, textvariable=score_var, width=10)
        score_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(score_frame, text="(max 999999)", font=('Arial', 7)).pack(side=tk.LEFT)
        
        # Name field
        name_frame = ttk.Frame(frame)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text="Name:", width=8).pack(side=tk.LEFT)
        name_var = tk.StringVar(value=entry['name'])
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=5)
        name_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(name_frame, text="(3 chars)", font=('Arial', 7)).pack(side=tk.LEFT)
        
        # Stage field
        stage_frame = ttk.Frame(frame)
        stage_frame.pack(fill=tk.X, pady=2)
        ttk.Label(stage_frame, text="Stage:", width=8).pack(side=tk.LEFT)
        stage_var = tk.StringVar(value=str(entry['stage']))
        stage_spinbox = ttk.Spinbox(stage_frame, textvariable=stage_var, 
                                   from_=0, to=255, width=5)
        stage_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Update button
        update_btn = ttk.Button(frame, text="Update", 
                               command=lambda: self.update_high_score(index, score_var, 
                                                                      name_var, stage_var))
        update_btn.pack(pady=5)
        
        # Store references
        self.high_score_widgets.append({
            'index': index,
            'score_var': score_var,
            'name_var': name_var,
            'stage_var': stage_var
        })
    
    def update_high_score(self, index, score_var, name_var, stage_var):
        """Update a high score entry"""
        try:
            # Validate and update score
            score_int = int(score_var.get())
            if score_int < 0 or score_int > 999999:
                messagebox.showwarning("Invalid Score", "Score must be between 0 and 999,999")
                return
            
            self.high_scores[index]['score'] = int_to_bcd(score_int)
            
            # Update name
            name = name_var.get().upper()[:3]  # Truncate to 3 chars
            if not all(32 <= ord(c) < 127 for c in name):
                messagebox.showwarning("Invalid Name", "Name must contain only ASCII characters")
                return
            self.high_scores[index]['name'] = name
            
            # Update stage
            stage = int(stage_var.get())
            if stage < 0 or stage > 255:
                messagebox.showwarning("Invalid Stage", "Stage must be between 0 and 255")
                return
            self.high_scores[index]['stage'] = stage
            
            # Sync HIGH SCORE with highest ranked score
            self.sync_high_score()
            
            self.mark_modified()
            self.display_data_editor()
            
            rank_names = ["HIGH SCORE", "1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH"]
            self.status_var.set(f"Updated {rank_names[index]} score")
            
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numbers")
    
    def sync_high_score(self):
        """Sync HIGH SCORE (index 0) with the highest score from ranked entries (1-7)"""
        if len(self.high_scores) < 2:
            return
        
        # Find the highest score among ranked entries
        max_score = max(bcd_to_int(entry['score']) for entry in self.high_scores[1:])
        self.high_scores[0]['score'] = int_to_bcd(max_score)

    def build_palette_editor(self):
        """Build the palette editor interface in the content area"""
        # Instructions
        info_label = ttk.Label(self.data_editor_content, 
                            text="Select a palette to edit.\nClick a color to modify it.",
                            font=('Arial', 8), justify=tk.LEFT)
        info_label.pack(pady=5, padx=5, anchor=tk.W)
        
        # Palette selection
        palette_frame = ttk.LabelFrame(self.data_editor_content, text="Select Palette", padding=5)
        palette_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.selected_palette_idx = tk.IntVar(value=0)
        
        palette_names = [
            "Map 1 Walls",
            "Map 2 Walls", 
            "Map 3 Walls",
            "Map 4 Walls",
            "Unknown 1",
            "Unknown 2",
            "Unknown 3"
        ]
        
        for i, name in enumerate(palette_names):
            ttk.Radiobutton(palette_frame, text=name, 
                        variable=self.selected_palette_idx, 
                        value=i,
                        command=self.on_palette_selection_change).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(self.data_editor_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Color editor (will be shown when a color is selected)
        self.color_editor_frame = ttk.LabelFrame(self.data_editor_content, 
                                                text="Color Editor", 
                                                padding=10)
        self.color_editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(self.color_editor_frame, 
                text="Click a color in the right panel to edit",
                font=('Arial', 9, 'italic'),
                foreground='gray').pack(pady=20)
        
        # Store reference to selected color
        self.selected_color_idx = None

    def on_palette_selection_change(self):
        """Handle palette selection changes"""
        self.selected_color_idx = None
        self.display_data_editor()
        self.status_var.set(f"Selected palette {self.selected_palette_idx.get()}")

    def display_palette_editor_view(self):
        """Display palette editor in the right panel"""
        self.map_canvas.delete('all')
        
        # Store reference to prevent canvas from being recreated
        if not hasattr(self, '_palette_canvas_setup'):
            self._palette_canvas_setup = True
        
        palette_idx = self.selected_palette_idx.get()
        palette = self.palettes[palette_idx]
        
        # Title
        palette_names = ["Map 1 Walls", "Map 2 Walls", "Map 3 Walls", "Map 4 Walls",
                        "Unknown 1", "Unknown 2", "Unknown 3"]
        self.map_canvas.create_text(400, 50, text=f"PALETTE: {palette_names[palette_idx]}", 
                                font=('Arial', 20, 'bold'), fill='white')
        
        # Display color swatches (15 colors, index 0-14)
        y_pos = 120
        swatch_size = 60
        spacing = 10
        cols = 5
        
        # Store swatch images to prevent garbage collection
        if not hasattr(self, '_palette_swatch_images'):
            self._palette_swatch_images = []
        self._palette_swatch_images.clear()
        
        for i in range(15):  # Only 15 editable colors (index 15 is always 0x00)
            row = i // cols
            col = i % cols
            
            x = 150 + (col * (swatch_size + spacing))
            y = y_pos + (row * (swatch_size + spacing + 30))
            
            # Get RGB from palette (skip alpha channel)
            r, g, b = palette[i][1], palette[i][2], palette[i][3]
            
            # Convert to hex color
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            
            # Draw swatch - use a unique tag for each
            swatch_id = self.map_canvas.create_rectangle(x, y, x+swatch_size, y+swatch_size,
                                                        fill=hex_color, outline='white', width=2,
                                                        tags=f'swatch_{i}')
            
            # Highlight selected color
            if self.selected_color_idx == i:
                self.map_canvas.create_rectangle(x-3, y-3, x+swatch_size+3, y+swatch_size+3,
                                            outline='yellow', width=3, tags='selection')
            
            # Add click binding - use lambda with default argument to capture i
            self.map_canvas.tag_bind(f'swatch_{i}', '<Button-1>', 
                                lambda e, idx=i: self.on_color_swatch_click(idx))
            
            # Label
            self.map_canvas.create_text(x + swatch_size//2, y + swatch_size + 15,
                                    text=f"Color {i}", font=('Arial', 9), fill='lightgray')
        
        # Show sample tile using this palette
        y_pos = 450
        self.map_canvas.create_text(320, y_pos, text="Sample Tile Preview", 
                                font=('Arial', 14, 'bold'), fill='white')
        
        # Use a sample tile (e.g., tile 0x00 - first wall tile)
        if len(self.all_tiles) > 0:
            tile = self.all_tiles[0]
            color_tile = apply_palette_to_tile(tile, palette)
            
            # Scale 4x for visibility
            scale = 4
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            
            # Store reference
            if not hasattr(self, '_palette_preview_images'):
                self._palette_preview_images = []
            self._palette_preview_images = [tile_photo]
            
            self.map_canvas.create_image(320 - (16*scale)//2, y_pos + 30, 
                                        image=tile_photo, anchor='nw')

    def on_color_swatch_click(self, color_idx):
        """Handle clicking on a color swatch"""
        self.selected_color_idx = color_idx
        palette_idx = self.selected_palette_idx.get()
        palette = self.palettes[palette_idx]
        
        # Get current RGB values (skip alpha)
        r, g, b = palette[color_idx][1], palette[color_idx][2], palette[color_idx][3]
        
        # Store original color for cancel functionality
        self.original_color = (r, g, b)
        
        # Rebuild color editor with sliders
        for widget in self.color_editor_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.color_editor_frame, 
                text=f"Editing Color {color_idx}",
                font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Create sliders for RGB (using valid bit ranges)
        # Red: 3-bit (0-7)
        red_frame = ttk.Frame(self.color_editor_frame)
        red_frame.pack(fill=tk.X, pady=5)
        ttk.Label(red_frame, text="Red (0-7):", width=10).pack(side=tk.LEFT)
        
        # Convert current value to 3-bit scale
        r_bits = int(round(r * 7 / 255))
        self.red_var = tk.IntVar(value=r_bits)
        red_scale = ttk.Scale(red_frame, from_=0, to=7, orient=tk.HORIZONTAL,
                            variable=self.red_var, command=self.on_color_change)
        red_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.red_label = ttk.Label(red_frame, text=str(r_bits), width=3)
        self.red_label.pack(side=tk.LEFT)
        
        # Green: 3-bit (0-7)
        green_frame = ttk.Frame(self.color_editor_frame)
        green_frame.pack(fill=tk.X, pady=5)
        ttk.Label(green_frame, text="Green (0-7):", width=10).pack(side=tk.LEFT)
        
        g_bits = int(round(g * 7 / 255))
        self.green_var = tk.IntVar(value=g_bits)
        green_scale = ttk.Scale(green_frame, from_=0, to=7, orient=tk.HORIZONTAL,
                            variable=self.green_var, command=self.on_color_change)
        green_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.green_label = ttk.Label(green_frame, text=str(g_bits), width=3)
        self.green_label.pack(side=tk.LEFT)
        
        # Blue: 2-bit (0-3)
        blue_frame = ttk.Frame(self.color_editor_frame)
        blue_frame.pack(fill=tk.X, pady=5)
        ttk.Label(blue_frame, text="Blue (0-3):", width=10).pack(side=tk.LEFT)
        
        b_bits = int(round(b * 3 / 255))
        self.blue_var = tk.IntVar(value=b_bits)
        blue_scale = ttk.Scale(blue_frame, from_=0, to=3, orient=tk.HORIZONTAL,
                            variable=self.blue_var, command=self.on_color_change)
        blue_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.blue_label = ttk.Label(blue_frame, text=str(b_bits), width=3)
        self.blue_label.pack(side=tk.LEFT)
        
        # Preview of current color
        preview_frame = ttk.Frame(self.color_editor_frame)
        preview_frame.pack(fill=tk.X, pady=10)
        ttk.Label(preview_frame, text="Preview:").pack(side=tk.LEFT, padx=5)
        
        self.color_preview_canvas = tk.Canvas(preview_frame, width=60, height=60, bg='black')
        self.color_preview_canvas.pack(side=tk.LEFT, padx=5)
        
        # Draw initial preview
        hex_color = f'#{r:02x}{g:02x}{b:02x}'
        self.color_preview_canvas.create_rectangle(2, 2, 58, 58, fill=hex_color, outline='white')
        
        # Button frame for Apply and Cancel
        button_frame = ttk.Frame(self.color_editor_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Apply Changes", 
                command=self.apply_color_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                command=self.cancel_color_changes).pack(side=tk.LEFT, padx=5)
        
        # Update status only - don't redraw the entire display
        self.status_var.set(f"Editing color {color_idx} - adjust sliders and click Apply or Cancel")

    def on_color_change(self, event=None):
        """Update preview when sliders change"""
        # Get bit values from sliders
        r_bits = int(self.red_var.get())
        g_bits = int(self.green_var.get())
        b_bits = int(self.blue_var.get())
        
        # Update labels
        self.red_label.config(text=str(r_bits))
        self.green_label.config(text=str(g_bits))
        self.blue_label.config(text=str(b_bits))
        
        # Scale to 0-255 range
        r_scaled = int(r_bits * 255 / 7)
        g_scaled = int(g_bits * 255 / 7)
        b_scaled = int(b_bits * 255 / 3)
        
        # Update preview
        hex_color = f'#{r_scaled:02x}{g_scaled:02x}{b_scaled:02x}'
        self.color_preview_canvas.delete('all')
        self.color_preview_canvas.create_rectangle(2, 2, 58, 58, fill=hex_color, outline='white')

    def cancel_color_changes(self):
        """Cancel color editing and restore original color"""
        if self.selected_color_idx is None:
            return
        
        # Restore original color to preview (but don't save to ROM)
        if hasattr(self, 'original_color'):
            r, g, b = self.original_color
            
            # Update preview to show original color
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            if hasattr(self, 'color_preview_canvas'):
                self.color_preview_canvas.delete('all')
                self.color_preview_canvas.create_rectangle(2, 2, 58, 58, fill=hex_color, outline='white')
        
        # Clear selection
        self.selected_color_idx = None
        
        # Clear color editor
        for widget in self.color_editor_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.color_editor_frame, 
                text="Click a color in the right panel to edit",
                font=('Arial', 9, 'italic'),
                foreground='gray').pack(pady=20)
        
        # Refresh display
        self.display_data_editor()
        self.status_var.set("Color editing cancelled")

    def apply_color_changes(self):
        """Apply the edited color to the palette"""
        if self.selected_color_idx is None:
            return
        
        try:
            # Get bit values
            r_bits = int(self.red_var.get())
            g_bits = int(self.green_var.get())
            b_bits = int(self.blue_var.get())
            
            # Scale to 0-255 range
            r_scaled = int(r_bits * 255 / 7)
            g_scaled = int(g_bits * 255 / 7)
            b_scaled = int(b_bits * 255 / 3)
            
            # Update palette in memory
            palette_idx = self.selected_palette_idx.get()
            self.palettes[palette_idx][self.selected_color_idx] = (255, r_scaled, g_scaled, b_scaled)
            
            # Write to ROM cache - get the file offset (not memory address)
            palette_offsets = [0x2D1, 0x2E1, 0x2F1, 0x301, 0x311, 0x321, 0x331]  # File offsets in m1.1h
            offset = palette_offsets[palette_idx]
            palette_byte = encode_palette_byte(r_scaled, g_scaled, b_scaled)
            rom_cache[ROM_CONFIG['palette_rom']][offset + self.selected_color_idx] = palette_byte
            
            self.mark_modified()
            
            palette_names = ["Map 1", "Map 2", "Map 3", "Map 4", "Unknown 1", "Unknown 2", "Unknown 3"]
            self.status_var.set(f"Updated {palette_names[palette_idx]} color {self.selected_color_idx}")
            
            # Clear selection and editor
            self.selected_color_idx = None
            
            # Clear color editor
            for widget in self.color_editor_frame.winfo_children():
                widget.destroy()
            
            ttk.Label(self.color_editor_frame, 
                    text="Click a color in the right panel to edit",
                    font=('Arial', 9, 'italic'),
                    foreground='gray').pack(pady=20)
            
            # Refresh display
            self.display_data_editor()
            
        except Exception as e:
            logging.error(f"Error applying color changes: {e}")
            messagebox.showerror("Error", f"Failed to apply color changes: {str(e)}")

    def display_data_editor(self):
        """Display data editor content in the right panel"""
        # Make sure we're in data editor mode
        if self.editor_mode.get() != "Data Editor":
            return
            
        data_type = self.data_editor_type.get()
        
        # Clear the map canvas
        self.map_canvas.delete('all')
        
        if data_type == "High Scores":
            # Display high scores in a nice table format
            self.display_high_scores_view()
        elif data_type == "Palettes":
            self.display_palette_editor_view()
    
    def display_high_scores_view(self):
        """Display high scores in a formatted table view"""
        self.map_canvas.delete('all')
        
        # Title
        self.map_canvas.create_text(400, 50, text="TUTANKHAM HIGH SCORES", 
                                   font=('Arial', 24, 'bold'), fill='gold')
        
        y_pos = 120
        
        # HIGH SCORE
        entry = self.high_scores[0]
        score_str = f"{bcd_to_int(entry['score']):06d}"
        self.map_canvas.create_text(400, y_pos, text="HIGH SCORE", 
                                   font=('Arial', 16, 'bold'), fill='white')
        self.map_canvas.create_text(400, y_pos + 30, text=score_str, 
                                   font=('Courier', 20, 'bold'), fill='cyan')
        
        y_pos += 80
        
        # Separator
        self.map_canvas.create_line(200, y_pos, 600, y_pos, fill='gray', width=2)
        y_pos += 30
        
        # Header
        self.map_canvas.create_text(220, y_pos, text="RANK", 
                                   font=('Arial', 12, 'bold'), fill='yellow')
        self.map_canvas.create_text(350, y_pos, text="SCORE", 
                                   font=('Arial', 12, 'bold'), fill='yellow')
        self.map_canvas.create_text(500, y_pos, text="NAME", 
                                   font=('Arial', 12, 'bold'), fill='yellow')
        self.map_canvas.create_text(620, y_pos, text="STAGE", 
                                   font=('Arial', 12, 'bold'), fill='yellow')
        
        y_pos += 30
        
        # Entries
        rank_names = ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH"]
        for i in range(NUM_HIGH_SCORES):
            entry = self.high_scores[i + 1]
            score_str = f"{bcd_to_int(entry['score']):06d}"
            
            color = 'white' if i % 2 == 0 else 'lightgray'
            
            self.map_canvas.create_text(220, y_pos, text=rank_names[i], 
                                       font=('Arial', 14), fill=color)
            self.map_canvas.create_text(350, y_pos, text=score_str, 
                                       font=('Courier', 14), fill=color)
            self.map_canvas.create_text(500, y_pos, text=entry['name'], 
                                       font=('Courier', 14, 'bold'), fill='cyan')
            self.map_canvas.create_text(620, y_pos, text=str(entry['stage']), 
                                       font=('Arial', 14), fill=color)
            
            y_pos += 35
        
        # Instructions
        self.map_canvas.create_text(400, y_pos + 40, 
                                   text="Use the left panel to edit high scores", 
                                   font=('Arial', 10, 'italic'), fill='gray')
    
    def sort_high_scores(self):
        """Sort high scores in descending order"""
        # Extract ranked entries (skip HIGH SCORE entry at index 0)
        ranked_entries = self.high_scores[1:]
        
        # Sort by score (descending)
        ranked_entries.sort(key=lambda x: bcd_to_int(x['score']), reverse=True)
        
        # Update high scores list
        self.high_scores[1:] = ranked_entries
        
        # Sync HIGH SCORE with 1st place
        self.sync_high_score()
        
        # Rebuild UI
        self.update_data_editor_content()
        self.mark_modified()
        self.status_var.set("High scores sorted by score")
    
    def reset_high_scores(self):
        """Reset high scores to default values"""
        if not messagebox.askyesno("Confirm Reset", 
                                   "Are you sure you want to reset all high scores to defaults?"):
            return
        
        # Default high scores (from memory map)
        # Note: HIGH SCORE will be auto-synced with 1st place
        self.high_scores = [
            {'score': int_to_bcd(35840), 'name': '', 'stage': 0},      # HIGH SCORE (will be synced)
            {'score': int_to_bcd(35840), 'name': 'HTA', 'stage': 2},   # 1ST
            {'score': int_to_bcd(34060), 'name': 'MNU', 'stage': 2},   # 2ND
            {'score': int_to_bcd(33860), 'name': 'SIS', 'stage': 2},   # 3RD
            {'score': int_to_bcd(29660), 'name': 'KKO', 'stage': 1},   # 4TH
            {'score': int_to_bcd(23460), 'name': 'YNA', 'stage': 1},   # 5TH
            {'score': int_to_bcd(15860), 'name': 'FUJ', 'stage': 1},   # 6TH
            {'score': int_to_bcd(12060), 'name': 'MAT', 'stage': 1},   # 7TH
        ]
        
        # Ensure HIGH SCORE matches 1st place
        self.sync_high_score()
        
        # Rebuild UI
        self.update_data_editor_content()
        self.mark_modified()
        self.status_var.set("High scores reset to defaults")
    
    def on_escape(self, event):
        if self.teleporter_first_pos is not None:
            # Restore the original tiles where we placed the first pillar
            first_row, first_col = self.teleporter_first_pos
            visual_map = self.visual_maps[self.selected_map]
            logical_map = self.logical_maps[self.selected_map]
        
            left_col = first_col - 1
            right_col = first_col + 1
        
            # Clear the pillar tiles back to empty path
            for tile_col in [left_col, first_col, right_col]:
                visual_map[first_row, tile_col] = empty_path_tile
                logical_row = tile_col
                logical_col = first_row + 1
                logical_map[logical_row, logical_col] = [0x00, 0x00]
        
            self.teleporter_first_pos = None
            self.display_map()
            self.status_var.set("Teleporter placement cancelled")
        elif self.selected_player_start:
            self.selected_player_start = None
            self.player_start_ghost_pos = None
            self.status_var.set("Player start movement cancelled")
    
    def render_tile_palette(self):
        tile_spacing = 5
        tile_display_size = int(16 * self.zoom_level)
        palette = self.palettes[self.selected_map]
        
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        
        y_pos = tile_spacing
        
        # COMPOSITE OBJECTS

        # Create 4 columns: Composite, Walls, Spawns, Treasures
        columns = {
            'composite': {'x': tile_spacing, 'width': 700, 'title': 'COMPOSITE', 'items': []},
            'walls': {'x': 700, 'width': 1200, 'title': 'WALLS', 'items': []},
            'spawns': {'x': 1900, 'width': 100, 'title': 'SPAWNS', 'items': []},
            'treasures': {'x': 2000, 'width': 500, 'title': 'TREASURES', 'items': []}
        }

        # Populate composite objects
        teleporter_display = np.array([[100, 38, 101]])
        composite_list = [
            ('teleporter', teleporter_display),
            ('spawner_right', SPAWNER_CONFIGS['right']['tiles']),
            ('spawner_left', SPAWNER_CONFIGS['left']['tiles']),
            ('spawner_up', SPAWNER_CONFIGS['up']['tiles']),
            ('spawner_down', SPAWNER_CONFIGS['down']['tiles'])
        ]

        for comp_id, comp_tiles in composite_list:
            h, w = comp_tiles.shape
            comp_img = np.zeros((h * 16, w * 16, 4), dtype=np.uint8)
    
            for r in range(h):
                for c in range(w):
                    tile_idx = comp_tiles[r, c]
                    if tile_idx < len(self.all_tiles):
                        tile = self.all_tiles[tile_idx]
                        color_tile = apply_palette_to_tile(tile, palette)
                        comp_img[r*16:(r+1)*16, c*16:(c+1)*16] = color_tile
    
            comp_rgb = comp_img[:, :, :3]
            scale = int(self.zoom_level)
            comp_rgb_scaled = np.repeat(np.repeat(comp_rgb, scale, axis=0), scale, axis=1)
            comp_pil = Image.fromarray(comp_rgb_scaled.astype('uint8')).convert('RGB')
            comp_photo = ImageTk.PhotoImage(comp_pil)
    
            columns['composite']['items'].append({
                'id': comp_id,
                'photo': comp_photo,
                'width': w * 16 * scale,
                'height': h * 16 * scale,
                'type': 'composite'
            })

        # Populate walls
        for tile_id in WALL_TILES + PATH_TILES:
            if tile_id >= len(self.all_tiles):
                continue
            tile = self.all_tiles[tile_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
    
            columns['walls']['items'].append({
                'id': tile_id,
                'photo': tile_photo,
                'width': 16 * scale,
                'height': 16 * scale,
                'type': 'tile'
            })

        # Populate spawn points
        for tile_id in SPAWN_TILES:
            if tile_id >= len(self.all_tiles):
                continue
            tile = self.all_tiles[tile_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
    
            columns['spawns']['items'].append({
                'id': tile_id,
                'photo': tile_photo,
                'width': 16 * scale,
                'height': 16 * scale,
                'type': 'tile'
            })

        # Populate treasures (show empty and filled pairs + keyhole)
        treasure_pairs = [(0x21, 0x6F), (0x22, 0x70), (0x4A, 0x62)]
        for empty_id, filled_id in treasure_pairs:
            # Empty box
            tile = self.all_tiles[empty_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
    
            columns['treasures']['items'].append({
                'id': empty_id,
                'photo': tile_photo,
                'width': 16 * scale,
                'height': 16 * scale,
                'type': 'tile'
            })
    
            # Filled box
            tile = self.all_tiles[filled_id]
            color_tile = apply_palette_to_tile(tile, palette)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)

            columns['treasures']['items'].append({
                'id': filled_id,
                'photo': tile_photo,
                'width': 16 * scale,
                'height': 16 * scale,
                'type': 'tile'
            })

        # Add keyhole (no empty/filled pair)
        tile = self.all_tiles[0x72]
        color_tile = apply_palette_to_tile(tile, palette)
        scale = int(self.zoom_level)
        color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
        tile_rgb = color_tile_large[:, :, :3]
        tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
        tile_photo = ImageTk.PhotoImage(tile_img)

        columns['treasures']['items'].append({
                'id': 0x72,
                'photo': tile_photo,
                'width': 16 * scale,
                'height': 16 * scale,
                'type': 'tile'
            })
       
        # Draw all columns
        for col_key, col_data in columns.items():
            x_start = col_data['x']
            x_pos = x_start
            y_pos = tile_spacing
            col_width = col_data['width']  # Width available for each column
            max_y_in_row = 0
    
            # Column title
            self.palette_canvas.create_text(x_start, y_pos, text=col_data['title'],
                                           anchor='nw', fill='white', font=('Arial', 9, 'bold'))
            y_pos += 20
    
            # Draw items with wrapping
            for item in col_data['items']:
                self.tile_images.append((item['id'], item['photo']))
        
                # Check if we need to wrap to next row
                if x_pos + item['width'] > x_start + col_width:
                    x_pos = x_start
                    y_pos = max_y_in_row + 25  # Move to next row
                    max_y_in_row = y_pos
        
                img_id = self.palette_canvas.create_image(x_pos, y_pos, image=item['photo'], anchor='nw')
        
                if item['type'] == 'composite':
                    self.palette_canvas.tag_bind(img_id, '<Button-1>',
                                                lambda e, cid=item['id']: self.on_composite_click(cid))
                    label = item['id'].replace('_', '\n')
                else:
                    self.palette_canvas.tag_bind(img_id, '<Button-1>',
                                                lambda e, tid=item['id']: self.on_tile_click(tid))
                    label = f"0x{item['id']:02X}" 
        
                label_y = y_pos + item['height'] + 2
                self.palette_canvas.create_text(x_pos + item['width']//2, label_y,
                                              text=label, anchor='n', fill='lightgray',
                                              font=('Arial', 7))
        
                # Track position for next item
                max_y_in_row = max(max_y_in_row, label_y + 15)
                x_pos += item['width'] + tile_spacing

        self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all")) 
        self.update_tile_info()
    
    def update_tile_info(self):
        if self.selected_composite:
            self.tile_info_var.set(f"Selected Tile: {self.selected_composite}")
        elif self.selected_tile is not None:
            self.tile_info_var.set(f"Selected Tile: 0x{self.selected_tile:02X}")

            # Show tile preview (scaled up 2x for visibility)
            if self.selected_tile < len(self.all_tiles):
                tile = self.all_tiles[self.selected_tile]
                palette = self.palettes[self.selected_map]
                color_tile = apply_palette_to_tile(tile, palette)
            
                # Scale 2x (16x16 -> 32x32)
                color_tile_large = np.repeat(np.repeat(color_tile, 2, axis=0), 2, axis=1)
                tile_rgb = color_tile_large[:, :, :3]
                tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
                tile_photo = ImageTk.PhotoImage(tile_img)
            
                self.selected_tile_preview.config(image=tile_photo)
                self.selected_tile_preview.image = tile_photo  # Keep reference
            else:
                self.selected_tile_preview.config(image='')

        else:
            self.tile_info_var.set("Selected Tile: None")
            self.selected_tile_preview.config(image='')
    
    def on_composite_click(self, composite_id):
        self.selected_composite = composite_id
        self.selected_tile = None
        if composite_id.startswith('spawner_'):
            self.selected_spawner_dir = composite_id.split('_')[1]
        self.update_tile_info()
        self.status_var.set(f"Selected {composite_id} - click map to place")
    
    def on_tile_click(self, tile_index):
        self.selected_tile = tile_index
        self.selected_composite = None
        self.update_tile_info()
    
    def on_map_select(self, map_index):
        self.selected_map = map_index

        # Update button highlighting
        self.update_selection_highlight()
    
        # Refresh composite positions for the new map
        self.door_positions[map_index] = self.find_door(map_index)
        self.spawner_positions[map_index] = self.find_spawners(map_index)
        self.teleporter_positions[map_index] = self.find_teleporters(map_index)
    
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        self.render_tile_palette()
        self.display_map()
        self.update_config_display()
        self.update_counters()

    def select_map_and_difficulty(self, map_idx, diff):
        self.selected_map = map_idx
        self.difficulty = diff

        # Update button highlighting
        self.update_selection_highlight()
    
        # Refresh everything
        self.door_positions[map_idx] = self.find_door(map_idx)
        self.spawner_positions[map_idx] = self.find_spawners(map_idx)
        self.teleporter_positions[map_idx] = self.find_teleporters(map_idx)
        
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        self.render_tile_palette()
        self.display_map()
        self.update_config_display()
        self.update_counters()

    def update_selection_highlight(self):
        """Update button states to show current selection"""
        # Reset all buttons to normal state
        for key, btn in self.map_buttons.items():
            btn.state(['!pressed'])
    
        # Highlight selected map button
        if ('map', self.selected_map) in self.map_buttons:
            self.map_buttons[('map', self.selected_map)].state(['pressed'])
    
        # Highlight selected difficulty button
        if (self.selected_map, self.difficulty) in self.map_buttons:
            self.map_buttons[(self.selected_map, self.difficulty)].state(['pressed'])
    
    def on_map_hover(self, event):
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            x_coord = row * 0x08
            y_coord = col * 0x08
            
            if self.teleporter_first_pos is not None:
                _, first_col = self.teleporter_first_pos
                if col == first_col:
                    self.coord_var.set(f"XX=0x{x_coord:02X}  YYYY=0x{y_coord:04X}  ✓ SAME COLUMN")
                else:
                    self.coord_var.set(f"XX=0x{x_coord:02X}  YYYY=0x{y_coord:04X}  ✗ MUST BE COL {first_col}")
            else:
                self.coord_var.set(f"XX=0x{x_coord:02X}  YYYY=0x{y_coord:04X}  (Row={row}, Col={col})")
        else:
            self.coord_var.set("")
    
    def on_map_click(self, event):
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
    
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
    
        if 0 <= row < map_height and 0 <= col < map_width:
            visual_map = self.visual_maps[self.selected_map]
        
            # FIRST: Check if we're in player start move mode
            if visual_map[row, col] == 0x29:
                if not self.can_edit_map():
                    return
                self.selected_player_start = (row, col)
                self.status_var.set("Player start selected - drag to move")
                self.display_map()
                return
        
            # SECOND: Check door interactions
            if self.is_door_tile(row, col):
                if not self.can_edit_map():
                    return
                door_pos = self.door_positions[self.selected_map]
                self.selected_door = door_pos
                self.door_drag_start = (row, col)
                self.status_var.set("Door selected - drag to move")
                self.display_map()
                return
        
            # THIRD: Check spawner interactions
            spawner = self.is_spawner_tile(row, col)
            if spawner:
                messagebox.showinfo("Spawner", f"This is a {spawner['direction']} spawner. Right-click to delete.")
                return
        
            # FINALLY: Handle tile/composite placement
            if self.selected_composite:
                if self.selected_composite == 'door':
                    self.place_door(row, col)
                elif self.selected_composite == 'teleporter':
                    self.place_teleporter_step(row, col)
                elif self.selected_composite.startswith('spawner_'):
                    self.place_spawner(row, col)
            elif self.selected_tile is not None:
                if self.selected_tile == 0x72:  # Keyhole
                    self.place_keyhole(row, col)
                elif self.selected_tile in FILLED_TO_EMPTY:
                    self.place_filled_box(row, col)
                else:
                    self.place_tile(row, col)

    
    def on_map_right_click(self, event):
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            # Check if clicking on spawner
            spawner = self.is_spawner_tile(row, col)
            if spawner:
                if not self.can_edit_map():
                    return
            
                # Clear the spawner tiles
                visual_map = self.visual_maps[self.selected_map]
                logical_map = self.logical_maps[self.selected_map]
            
                for dr in range(spawner['height']):
                    for dc in range(spawner['width']):
                        visual_map[spawner['row'] + dr, spawner['col'] + dc] = empty_path_tile
                        logical_row = spawner['col'] + dc
                        logical_col = spawner['row'] + dr + 1
                        logical_map[logical_row, logical_col] = [0x00, 0x00]
            
                # Remove from spawner positions
                self.spawner_positions[self.selected_map].remove(spawner)
            
                # Clear from object data
                x = spawner['row'] * 0x08
                y = spawner['col'] * 0x08
                objects = self.object_data[self.difficulty][self.selected_map]
                for spawn in objects['spawns']:
                    if spawn['x'] == x and spawn['y'] == y:
                        spawn['x'] = 0
                        spawn['y'] = 0
                        break
            
                self.display_map()
                self.update_counters()
                self.mark_modified()
                self.status_var.set(f"Deleted {spawner['direction']} spawner")
                return
        
            x = row * 0x08
            y = col * 0x08
            
            objects = self.object_data[self.difficulty][self.selected_map]
            
            for item in objects['items']:
                if item['active'] and item['x'] == x and item['y'] == y:
                    item['active'] = False
                    self.status_var.set(f"Deleted item at ({col}, {row})")
                    self.display_map()
                    self.update_counters()
                    self.mark_modified()
                    return
            
            # Check if clicking on teleporter column
            teleporter_cols = self.teleporter_positions.get(self.selected_map, [])
            if col in teleporter_cols:
                if not self.can_edit_map():
                    return
    
            # Clear all teleporter tiles in this column
            visual_map = self.visual_maps[self.selected_map]
            logical_map = self.logical_maps[self.selected_map]
    
            for row in range(map_height):
                tile = visual_map[row, col]
            if tile in [100, 38, 101]:  # Teleporter tiles
                visual_map[row, col] = empty_path_tile
                logical_row = col
                logical_col = row + 1
                logical_map[logical_row, logical_col] = [0x00, 0x00]
    
            # Remove from teleporter positions
            self.teleporter_positions[self.selected_map].remove(col)
    
            # Clear from object data
            y_coord = col * 0x08
            objects = self.object_data[self.difficulty][self.selected_map]
            for tp in objects['teleports']:
                if tp['y'] == y_coord:
                    tp['y'] = 0
                    tp['bottom_row'] = 0
                    tp['top_row'] = 0
                    break
    
            self.display_map()
            self.update_counters()
            self.mark_modified()
            self.status_var.set(f"Deleted teleporter pair in column {col}")
            return
            
            for spawn in objects['spawns']:
                if spawn['x'] == x and spawn['y'] == y:
                    spawn['x'] = 0
                    spawn['y'] = 0
                    self.status_var.set(f"Deleted spawner at ({col}, {row})")
                    self.display_map()
                    self.update_counters()
                    self.mark_modified()
                    return
            
            if objects['player_start']['x'] == x and objects['player_start']['y'] == y:
                messagebox.showwarning("Cannot Delete", "Cannot delete player start position")
                return
            
            for i, respawn in enumerate(objects['respawns']):
                if respawn['x'] == x and respawn['y'] == y:
                    for j in range(i, NUM_RESPAWNS - 1):
                        objects['respawns'][j] = objects['respawns'][j + 1].copy()
                    objects['respawns'][-1] = {'x': 0, 'y': 0}
                    objects['respawn_count'] = max(0, objects['respawn_count'] - 1)
                    self.status_var.set(f"Deleted respawn point at ({col}, {row})")
                    self.display_map()
                    self.update_counters()
                    self.mark_modified()
                    return
    
    def on_map_drag(self, event):
        if self.selected_door is None and self.selected_player_start is None:
            return
        
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            if self.selected_door:
                self.door_ghost_pos = (row, col)
            elif self.selected_player_start:
                self.player_start_ghost_pos = (row, col)
            self.display_map()
    
    def on_map_release(self, event):
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)

        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
    
        # Handle door release
        if self.selected_door is not None:
            if 0 <= row < map_height and 0 <= col < map_width:
                if row + 3 <= map_height and col + 3 <= map_width:
                    self.clear_door(self.selected_door[0], self.selected_door[1])
                    
                    if self.place_door_at(row, col):
                        self.door_positions[self.selected_map] = (row, col)
                        self.mark_modified()
                        self.status_var.set(f"Door moved to ({col}, {row})")
                    else:
                        self.place_door_at(self.selected_door[0], self.selected_door[1])
                        self.status_var.set("Invalid door placement")
                else:
                    self.status_var.set("Door doesn't fit at that location")
        
            self.selected_door = None
            self.door_drag_start = None
            self.door_ghost_pos = None
            self.display_map()
            return
    
        # Handle player start release
        if self.selected_player_start is not None:
            if 0 <= row < map_height and 0 <= col < map_width:
                visual_map = self.visual_maps[self.selected_map]
                
                # Clear old position
                old_row, old_col = self.selected_player_start
                visual_map[old_row, old_col] = empty_path_tile
            
                # Place at new position
                visual_map[row, col] = 0x29
            
                # Update object data
                row_from_bottom = (map_height - 1) - row
                x = row_from_bottom * 0x08
                y = col * 0x08
            
                objects = self.object_data[self.difficulty][self.selected_map]
                objects['player_start']['x'] = x
                objects['player_start']['y'] = y
            
                self.mark_modified()
                self.status_var.set(f"Moved player start to ({col}, {row})")
        
            self.selected_player_start = None
            self.player_start_ghost_pos = None
            self.display_map()
    
    def mark_modified(self):
        self.modified = True
        self.root.title(f"Tutankham Map Editor {EDITOR_VERSION} - *Unsaved*")
    
    def place_tile(self, row, col):
        if not self.can_edit_map():
            return
    
        # Check if this tile is part of a door
        if self.is_door_tile(row, col):
            messagebox.showwarning("Protected", "This tile is part of the door. Use drag-and-drop to move the door.")
            return
    
        # Check if this tile is part of a spawner
        spawner = self.is_spawner_tile(row, col)
        if spawner:
            messagebox.showwarning("Protected", f"This tile is part of a {spawner['direction']} spawner. Right-click to delete it.")
            return
    
        # Check if this tile is part of a teleporter
        teleporter_cols = self.teleporter_positions.get(self.selected_map, [])
        if col in teleporter_cols:
            messagebox.showwarning("Protected", f"Column {col} contains a teleporter. Right-click to delete it.")
            return
    
        # Proceed with normal tile placement
        self.visual_maps[self.selected_map][row, col] = self.selected_tile
    
        logical_map = self.logical_maps[self.selected_map]
        logical_row = col
        logical_col = row + 1
    
        if self.selected_tile == empty_path_tile:
            logical_map[logical_row, logical_col] = [0x00, 0x00]
        else:
            existing_pair = logical_map[logical_row, logical_col]
            if np.array_equal(existing_pair, [0x00, 0x00]) or np.array_equal(existing_pair, [0x55, 0x55]):
                logical_map[logical_row, logical_col] = [0x55, 0x55]
    
        self.display_map()
        self.mark_modified()
        hex_id = f"0x{self.selected_tile:02X}"
        self.status_var.set(f"Placed tile {hex_id} at ({col}, {row})")
    
    def place_filled_box(self, row, col):
        if not self.can_edit_map():
            return
        
        filled_tile = self.selected_tile
        empty_tile = FILLED_TO_EMPTY[filled_tile]
        
        self.visual_maps[self.selected_map][row, col] = empty_tile
        
        logical_map = self.logical_maps[self.selected_map]
        logical_row = col
        logical_col = row + 1
        logical_map[logical_row, logical_col] = [0x55, 0x55]
        
        row_from_bottom = (map_height - 1) - row  # Flip to bottom-indexed
        x = row_from_bottom * 0x08
        y = col * 0x08
        
        objects = self.object_data[self.difficulty][self.selected_map]
        for item in objects['items']:
            if not item['active']:
                item['active'] = True
                item['x'] = x
                item['y'] = y
                item['tile_id'] = filled_tile
                self.display_map()
                self.update_counters()
                self.mark_modified()
                self.status_var.set(f"Placed filled box 0x{filled_tile:02X} at ({col}, {row})")
                return
        
        messagebox.showwarning("No Slots", "No empty item slots available (max 14)")

    def place_keyhole(self, row, col):
        if not self.can_edit_map():
            return
    
        # Keyhole doesn't change the visual map - it's just an object
        # But for visualization, we can place it as a regular tile
        self.visual_maps[self.selected_map][row, col] = 0x72
    
        # Set logical map to walkable
        logical_map = self.logical_maps[self.selected_map]
        logical_row = col
        logical_col = row + 1
        logical_map[logical_row, logical_col] = [0x00, 0x00]
    
        # Add to object data
        row_from_bottom = (map_height - 1) - row
        x = row_from_bottom * 0x08
        y = col * 0x08
    
        objects = self.object_data[self.difficulty][self.selected_map]
        for item in objects['items']:
            if not item['active']:
                item['active'] = True
                item['x'] = x
                item['y'] = y
                item['tile_id'] = 0x72
                self.display_map()
                self.update_counters()
                self.mark_modified()
                self.status_var.set(f"Placed keyhole at ({col}, {row})")
                return
    
        messagebox.showwarning("No Slots", "No empty item slots available (max 14)")
    
    def place_door(self, row, col):
        if not self.can_edit_map():
            return
    
        if row + 3 > map_height or col + 3 > map_width:
            messagebox.showwarning("Invalid Placement", "Door doesn't fit at this location")
            return
    
        # Check if placing over other composites
        for dr in range(3):
            for dc in range(3):
                check_row = row + dr
                check_col = col + dc
            
                if self.is_spawner_tile(check_row, check_col):
                    messagebox.showwarning("Invalid Placement", "Would overlap with spawner")
                    return
            
                teleporter_cols = self.teleporter_positions.get(self.selected_map, [])
                if check_col in teleporter_cols:
                    messagebox.showwarning("Invalid Placement", "Would overlap with teleporter")
                    return
    
        old_door = self.door_positions.get(self.selected_map)
        if old_door:
            self.clear_door(old_door[0], old_door[1])
    
        if self.place_door_at(row, col):
            self.door_positions[self.selected_map] = (row, col)
            self.mark_modified()
            self.status_var.set(f"Placed door at ({col}, {row})")
    
    def place_teleporter_step(self, row, col):
        if self.teleporter_first_pos is None:
            # First click - place first horizontal pillar
            if col - 1 < 0 or col + 1 >= map_width:
                messagebox.showwarning("Invalid Placement", "Teleporter must have space for 3 columns (center ±1)")
                return
        
            # Check if these columns already have a teleporter
            left_col = col - 1
            right_col = col + 1
            teleporter_cols = self.teleporter_positions.get(self.selected_map, [])
            for check_col in [left_col, col, right_col]:
                if check_col in teleporter_cols:
                    messagebox.showwarning("Invalid Placement", f"Column {check_col} already has a teleporter")
                    return
        
            if not self.can_edit_map():
                return
        
            # Place first horizontal pillar across 3 columns at this row
            visual_map = self.visual_maps[self.selected_map]
            logical_map = self.logical_maps[self.selected_map]
        
            pillar_pattern = [100, 38, 101]
            pillar_logical = [[0x55, 0x55], [0x00, 0x00], [0x55, 0x55]]
        
            for dc, tile_col in enumerate([left_col, col, right_col]):
                visual_map[row, tile_col] = pillar_pattern[dc]
                logical_row = tile_col
                logical_col = row + 1
                logical_map[logical_row, logical_col] = pillar_logical[dc]
        
            self.teleporter_first_pos = (row, col)  # Store row and center column
            self.display_map()
            self.status_var.set(f"First pillar at row {row}, columns {left_col}-{right_col}. Place second in SAME COLUMNS, different row (ESC to cancel)")
        
        else:
            # Second click - must be same center column, different row
            first_row, first_col = self.teleporter_first_pos
        
            if col != first_col:
                messagebox.showwarning("Invalid Placement", 
                    f"Second pillar must be at column {first_col} (same center column as first)")
                return
        
            if row == first_row:
                messagebox.showwarning("Invalid Placement", "Second pillar must be at a different row")
                return
        
            if col - 1 < 0 or col + 1 >= map_width:
                messagebox.showwarning("Invalid Placement", "Teleporter doesn't fit")
                return
        
            if not self.can_edit_map():
                self.teleporter_first_pos = None
                return
        
            visual_map = self.visual_maps[self.selected_map]
            logical_map = self.logical_maps[self.selected_map]
        
            # Place second horizontal pillar
            left_col = col - 1
            right_col = col + 1
            pillar_pattern = [100, 38, 101]
            pillar_logical = [[0x55, 0x55], [0x00, 0x00], [0x55, 0x55]]
        
            for dc, tile_col in enumerate([left_col, col, right_col]):
                visual_map[row, tile_col] = pillar_pattern[dc]
                logical_row = tile_col
                logical_col = row + 1
                logical_map[logical_row, logical_col] = pillar_logical[dc]
        
            # Calculate object data
            y_coord = col * 0x08  # Center column
        
            # Convert rows to coordinates (from bottom)
            row_from_bottom_1 = (map_height - 1) - first_row
            row_from_bottom_2 = (map_height - 1) - row
        
            row_coord_1 = row_from_bottom_1 * 0x08
            row_coord_2 = row_from_bottom_2 * 0x08
        
            # Determine which is bottom (lower row number) and top (higher row number)
            bottom_row_coord = min(row_coord_1, row_coord_2)
            top_row_coord = max(row_coord_1, row_coord_2)
        
            # Add to object data
            objects = self.object_data[self.difficulty][self.selected_map]
            for tp in objects['teleports']:
                if tp['y'] == 0:
                    tp['y'] = y_coord
                    tp['bottom_row'] = bottom_row_coord
                    tp['top_row'] = top_row_coord
                
                    # Add to teleporter positions
                    if self.selected_map not in self.teleporter_positions:
                        self.teleporter_positions[self.selected_map] = []
                    if col not in self.teleporter_positions[self.selected_map]:
                        self.teleporter_positions[self.selected_map].append(col)
                
                    self.display_map()
                    self.update_counters()
                    self.mark_modified()
                    self.status_var.set(f"Placed teleporter pair at column {col}, rows {first_row} and {row}")
                    self.teleporter_first_pos = None
                    return
        
            messagebox.showwarning("No Slots", "No empty teleporter slots (max 6)")
            self.teleporter_first_pos = None
    
    def place_spawner(self, row, col):
        direction = self.selected_spawner_dir
        config = SPAWNER_CONFIGS[direction]
        
        h, w = config['tiles'].shape
        if row + h > map_height or col + w > map_width:
            messagebox.showwarning("Invalid Placement", "Spawner doesn't fit")
            return
        
        if not self.can_edit_map():
            return
        
        visual_map = self.visual_maps[self.selected_map]
        logical_map = self.logical_maps[self.selected_map]
        
        for r in range(h):
            for c in range(w):
                visual_map[row + r, col + c] = config['tiles'][r, c]
                logical_row = col + c
                logical_col = row + r + 1
                logical_map[logical_row, logical_col] = config['logical'][r, c]
        
        x_coord = row * 0x08
        y_coord = col * 0x08
        
        objects = self.object_data[self.difficulty][self.selected_map]
        for spawn in objects['spawns']:
            if spawn['y'] == 0:
                spawn['y'] = y_coord
                spawn['x'] = x_coord
                self.display_map()
                self.update_counters()
                self.mark_modified()
                self.status_var.set(f"Placed {direction} spawner at ({col}, {row})")
                return
        
        messagebox.showwarning("No Slots", "No empty spawner slots (max 7)")
    
    def zoom_in(self):
        if self.zoom_level < 8:
            self.zoom_level += 1
            self.zoom_label.config(text=f"{int(self.zoom_level)}x")
            self.display_map()
            self.palette_canvas.delete('all')
            self.render_tile_palette()
    
    def zoom_out(self):
        if self.zoom_level > 1:
            self.zoom_level -= 1
            self.zoom_label.config(text=f"{int(self.zoom_level)}x")
            self.display_map()
            self.palette_canvas.delete('all')
            self.render_tile_palette()
    
    def display_map(self):
        raw_map_layout = self.visual_maps[self.selected_map]
        map_image = np.zeros((raw_map_layout.shape[0] * 16, raw_map_layout.shape[1] * 16, 4), 
                            dtype=np.uint8)
        
        palette = self.palettes[self.selected_map]
        
        for row in range(raw_map_layout.shape[0]):
            for col in range(raw_map_layout.shape[1]):
                tile_index = raw_map_layout[row, col]
                if tile_index < len(self.all_tiles):
                    tile = self.all_tiles[tile_index]
                    color_tile = apply_palette_to_tile(tile, palette)
                    map_image[row * 16 : (row + 1) * 16, col * 16 : (col + 1) * 16, :] = color_tile
        
        map_image_rgb = map_image[:, :, :3]
        
        if self.zoom_level != 1:
            new_height = int(map_image_rgb.shape[0] * self.zoom_level)
            new_width = int(map_image_rgb.shape[1] * self.zoom_level)
            self.current_map_image = Image.fromarray(map_image_rgb.astype('uint8')).convert('RGB').resize(
                (new_width, new_height), Image.NEAREST)
        else:
            self.current_map_image = Image.fromarray(map_image_rgb.astype('uint8')).convert('RGB')
        
        map_image_tk = ImageTk.PhotoImage(self.current_map_image)
        
        self.map_canvas.delete('all')
        self.map_canvas.create_image(0, 0, image=map_image_tk, anchor='nw')
        self.map_canvas.image = map_image_tk
        
        if self.show_objects.get():
            self.draw_objects_overlay()
        
        if self.show_grid.get():
            for x in range(0, int(map_width * 16 * self.zoom_level), int(16 * self.zoom_level)):
                self.map_canvas.create_line(x, 0, x, int(map_height * 16 * self.zoom_level), 
                                           fill='#444444')
            for y in range(0, int(map_height * 16 * self.zoom_level), int(16 * self.zoom_level)):
                self.map_canvas.create_line(0, y, int(map_width * 16 * self.zoom_level), y, 
                                           fill='#444444')
        
        if self.selected_door is not None:
            row, col = self.selected_door
            x = col * 16 * self.zoom_level
            y = row * 16 * self.zoom_level
            size = 3 * 16 * self.zoom_level
            self.map_canvas.create_rectangle(x-2, y-2, x+size+2, y+size+2,
                                           outline='cyan', width=3, tags='door_highlight')
        
        if self.door_ghost_pos is not None:
            row, col = self.door_ghost_pos
            if row + 3 <= map_height and col + 3 <= map_width:
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 3 * 16 * self.zoom_level
                self.map_canvas.create_rectangle(x, y, x+size, y+size,
                                               outline='yellow', width=2, dash=(4, 4),
                                               tags='door_ghost')

        if self.selected_player_start is not None:
            row, col = self.selected_player_start
            x = col * 16 * self.zoom_level
            y = row * 16 * self.zoom_level
            size = 16 * self.zoom_level
            self.map_canvas.create_rectangle(x-2, y-2, x+size+2, y+size+2,
                                   outline='lime', width=3, tags='player_start_highlight')

        if self.player_start_ghost_pos is not None:
            row, col = self.player_start_ghost_pos
            x = col * 16 * self.zoom_level
            y = row * 16 * self.zoom_level
            size = 16 * self.zoom_level
            self.map_canvas.create_rectangle(x, y, x+size, y+size,
                                   outline='yellow', width=2, dash=(4, 4),
                                   tags='player_start_ghost')

        if self.teleporter_first_pos is not None:
            first_row, first_col = self.teleporter_first_pos
            x = first_col * 16 * self.zoom_level
            y = first_row * 16 * self.zoom_level
            h = 3 * 16 * self.zoom_level
            w = 16 * self.zoom_level
            self.map_canvas.create_rectangle(x, y, x+w, y+h,
                                           outline='magenta', width=2, dash=(4, 4))
        
        self.map_canvas.configure(scrollregion=(0, 0, 
                                               int(map_width * 16 * self.zoom_level), 
                                               int(map_height * 16 * self.zoom_level)))
    
    def draw_objects_overlay(self):
        objects = self.object_data[self.difficulty][self.selected_map]
        
        # Player start
        ps = objects['player_start']
        if ps['y'] != 0:
            col = ps['y'] // 0x08
            row_from_bottom = ps['x'] // 0x08
            row = (map_height - 1) - row_from_bottom  # Flip to top-indexed
            x = col * 16 * self.zoom_level
            y = row * 16 * self.zoom_level
            size = 16 * self.zoom_level
            
            self.map_canvas.create_rectangle(x, y, x+size, y+size,
                                           outline='teal', width=3, tags='object_overlay')
        
        # Respawns
        for i in range(objects['respawn_count']):
            respawn = objects['respawns'][i]
            if respawn['y'] != 0:
                col = respawn['y'] // 0x08
                row_from_bottom = respawn['x'] // 0x08
                row = (map_height - 1) - row_from_bottom  # Flip to top-indexed
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 16 * self.zoom_level
                
                self.map_canvas.create_oval(x, y, x+size, y+size,
                                           outline='yellow', width=2, tags='object_overlay')
        
        # Items with filled box overlay
        if not hasattr(self, '_overlay_images'):
            self._overlay_images = []
        self._overlay_images.clear()
        
        for item in objects['items']:
            if item['active']:
                col = item['y'] // 0x08
                row_from_bottom = item['x'] // 0x08
                row = (map_height - 1) - row_from_bottom  # Flip to top-indexed
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 16 * self.zoom_level
                self.map_canvas.create_rectangle(x, y, x+size, y+size,
                                           outline='green', width=3, tags='object_overlay')
                
                if item['tile_id'] in FILLED_TO_EMPTY:
                    tile_idx = item['tile_id']
                    if tile_idx < len(self.all_tiles):
                        tile = self.all_tiles[tile_idx]
                        palette = self.palettes[self.selected_map]
                        color_tile = apply_palette_to_tile(tile, palette)
                        
                        scale = int(self.zoom_level)
                        color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
                        tile_rgb = color_tile_large[:, :, :3]
                        
                        tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
                        tile_img.putalpha(180)
                        tile_photo = ImageTk.PhotoImage(tile_img)
                        
                        x = col * 16 * self.zoom_level
                        y = row * 16 * self.zoom_level
                        
                        self._overlay_images.append(tile_photo)
                        
                        self.map_canvas.create_image(x, y, image=tile_photo, anchor='nw',
                                                    tags='object_overlay')
                else:
                    x = col * 16 * self.zoom_level
                    y = row * 16 * self.zoom_level
                    size = 16 * self.zoom_level
                    
                    color_map = {0x62: 'gold', 0x6F: 'cyan', 0x70: 'yellow', 0x72: 'red'}
                    color = color_map.get(item['tile_id'], 'white')
                    
                    self.map_canvas.create_rectangle(x+2, y+2, x+size-2, y+size-2,
                                                    outline=color, width=2, tags='object_overlay')
        
        # Teleporters
        for tp in objects['teleports']:
            if tp['y'] != 0:
                col = tp['y'] // 0x08
                row_from_bottom = tp['top_row'] // 0x08
                row_top = (map_height - 1) - row_from_bottom  # Flip to top-indexed
                row_from_bottom = tp['bottom_row'] // 0x08
                row_bottom = (map_height - 1) - row_from_bottom  # Flip to top-indexed
                
                x = col * 16 * self.zoom_level
                y_top = row_top * 16 * self.zoom_level
                y_bottom = row_bottom * 16 * self.zoom_level
                
                self.map_canvas.create_line(x + 8*self.zoom_level, y_top + 8*self.zoom_level,
                                           x + 8*self.zoom_level, y_bottom + 8*self.zoom_level,
                                           fill='magenta', width=2, dash=(4, 4), tags='object_overlay')

                tile_idx = 0x63  # Poof Cloud For Teleport
                if tile_idx < len(self.all_tiles):
                    tile = self.all_tiles[tile_idx]
                    palette = self.palettes[self.selected_map]
                    color_tile = apply_palette_to_tile(tile, palette)
                    scale = int(self.zoom_level)
                    color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
                    tile_rgb = color_tile_large[:, :, :3]
                    tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
                    tile_img.putalpha(180)
                    tile_photo = ImageTk.PhotoImage(tile_img)
                    self._overlay_images.append(tile_photo)
                    # Overlay at top center
                    self.map_canvas.create_image(x, y_top, image=tile_photo, anchor='nw', tags='object_overlay')
                    # Overlay at bottom center
                    self.map_canvas.create_image(x, y_bottom, image=tile_photo, anchor='nw', tags='object_overlay')

        # Spawners
        for spawn in objects['spawns']:
            if spawn['y'] != 0:
                col = spawn['y'] // 0x08
                row_from_bottom = spawn['x'] // 0x08
                row = (map_height - 1) - row_from_bottom  # Flip to top-indexed

                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 16 * self.zoom_level
                
                self.map_canvas.create_oval(x, y, x+size, y+size,
                                           outline='red', width=2, tags='object_overlay')
                tile_idx = 0x6A  # Poison For Monster Spawner
                if tile_idx < len(self.all_tiles):
                    tile = self.all_tiles[tile_idx]
                    palette = self.palettes[self.selected_map]
                    color_tile = apply_palette_to_tile(tile, palette)
                    scale = int(self.zoom_level)
                    color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
                    tile_rgb = color_tile_large[:, :, :3]
                    tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
                    tile_img.putalpha(180)
                    tile_photo = ImageTk.PhotoImage(tile_img)
                    self._overlay_images.append(tile_photo)
                    self.map_canvas.create_image(x, y, image=tile_photo, anchor='nw', tags='object_overlay')

        # Show spawn point tiles (player start and respawn flames)
        visual_map = self.visual_maps[self.selected_map]
        for row in range(map_height):
            for col in range(map_width):
                tile = visual_map[row, col]
                if tile in SPAWN_TILES:  # 0x29 (player start) or 0x17 (respawn flame)
                    x = col * 16 * self.zoom_level
                    y = row * 16 * self.zoom_level
                    size = 16 * self.zoom_level
            
                    # Different colors for different spawn types
                    if tile == 0x29:  # Player start
                        color = 'lime'
                    else:  # Respawn flame
                        color = 'yellow'

    def save_file(self, target_directory=None):
        try:
            # Create backups first (only when saving to original location)
            backups = []
            if target_directory is None:
                for rom_name in rom_cache.keys():
                    rom_path = ROM_FILES[rom_name]
                    backup_path = backup_file(rom_path)
                    if backup_path:
                        backups.append(os.path.basename(backup_path))
    
            # Save visual and logical maps to cache
            save_visual_maps_to_rom(self.visual_maps)
            save_logical_maps_to_rom(self.logical_maps)
    
            # Save map configs to cache
            for diff in range(NUM_DIFFICULTIES):
                for i in range(num_maps):
                    self.save_map_config(i, diff)

            # Save object data to cache
            for diff in range(NUM_DIFFICULTIES):
                for i in range(num_maps):
                    save_object_data(self.object_data[diff][i], i, diff)

            # Save high scores to cache
            save_high_scores(self.high_scores)

            # Update copyright checksum before saving
            update_copyright_checksum()
    
            # Write all ROMs to disk
            save_all_roms(target_directory=target_directory)
    
            self.modified = False
            self.root.title(f"Tutankham Map Editor {EDITOR_VERSION}")
        
            if target_directory:
                messagebox.showinfo("Success", f"All files exported to {target_directory}")
            else:
                messagebox.showinfo("Success", 
                                  f"All data saved successfully!\n"
                                  f"Backups: {len(backups)} files")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def save_file_as(self):
        directory = filedialog.askdirectory(title="Select directory to export ROM files")
        if not directory:
            return
        self.save_file(target_directory=directory)

    def create_window_icon(self):
        """Create window icon from Tut mask tile"""
        try:
            # Use middle Tut mask tile (0x87)
            tile_idx = 0x87
        
            if tile_idx < len(self.all_tiles):
                tile = self.all_tiles[tile_idx]
                palette = self.palettes[0]  # Use Map 1 palette
                color_tile = apply_palette_to_tile(tile, palette)
            
                # Convert to PIL Image
                icon_rgb = color_tile[:, :, :3]
                icon_pil = Image.fromarray(icon_rgb.astype('uint8')).convert('RGB')
            
                # Resize to standard icon size (32x32)
                icon_pil = icon_pil.resize((32, 32), Image.NEAREST)
            
                # Convert to PhotoImage and set as icon
                icon_photo = ImageTk.PhotoImage(icon_pil)
                self.root.iconphoto(True, icon_photo)
            
                # Keep reference to prevent garbage collection
                self.window_icon = icon_photo
        except Exception:
            logging.warning("Couldn't set window icon", exc_info=True)
    
    def run(self):
        self.root.mainloop()

# Load all ROMs into memory first
load_all_roms()

# Load all data
all_tiles = load_tiles()
visual_maps = load_visual_maps()
logical_maps = load_logical_maps()
palettes = load_palettes_from_rom()

# Create and run editor
editor = MapEditor(visual_maps, logical_maps, all_tiles, palettes)
editor.run()