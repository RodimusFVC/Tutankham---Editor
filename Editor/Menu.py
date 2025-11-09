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
import subprocess
import sys

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
# Menu Data Setup
#########################################

EDITOR_VERSION = "V17"		# Editor Version Number
open_windows = {			# Window Tracking - ensure only one instance of each editor
    'map_editor': None,
    'tile_editor': None,
    'font_editor': None,
    'ui_graphics': None,
    'treasure_editor': None,
    'high_score': None,
    'palette': None}

#########################################
# Tutankham Data Setup
#########################################

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
# Level Data Constants
CONFIG_BASE_OFFSET = 0x061E  # Config data for each map/difficulty block
CONFIG_BLOCK_SIZE  = 11      # 11 bytes of config data per block
MAP_CONFIG_OFFSETS = {
    'logical_map_ptr': 0,
    'visual_map_ptr':  2,
    'spawn_rate':      4,
    'time_limit':      5,
    'unknown_bytes': (6, 11)}# 5 bytes from offset 6-10
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
    0x4A, 0x62,              # Crown Box    (Empty, Filled)
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
    0x62: 0x4A,  # Crown -> bottom-accessible box
    0x6F: 0x21,  # Ring -> top-accessible box
    0x72: None   # Keyhole -> no constraint
}

# Empty to filled box mapping
EMPTY_TO_FILLED = {
    0x22: 0x70,  # Key box
    0x4A: 0x62,  # Crown box
    0x21: 0x6F,  # Ring box
}

FILLED_TO_EMPTY = {v: k for k, v in EMPTY_TO_FILLED.items()}

# Tile names for display (0x00 - 0x9F, 160 tiles total)
TILE_NAMES = {
    # Empty Path
    0x26: "Empty Path",
    # Adventurer
    0x23: "Man Down 1",      0x24: "Man Down 2",        0x25: "Man Down 3",
    0x29: "Man Down 4",      0x2A: "Man Up 1",          0x2B: "Man Up 2",
    0x2C: "Man Up 3",        0x2D: "Man Up 4",          0x2E: "Man Left 1",
    0x2F: "Man Left 2",      0x30: "Man Left 3",        0x31: "Man Left 4",
    0x3A: "Man Right 1",     0x3B: "Man Right 2",       0x3C: "Man Right 3", 
    0x3D: "Man Right 4",
    # Adventurer Carrying Key
    0x4E: "Man+Key Down 1",   0x4F: "Man+Key Down 2",     0x50: "Man+Key Down 3",
    0x51: "Man+Key Down 4",   0x52: "Man+Key Up 1",       0x53: "Man+Key Up 2",
    0x54: "Man+Key Up 3",     0x55: "Man+Key Up 4",       0x5A: "Man+Key Left 1", 
    0x5B: "Man+Key Left 2",   0x5C: "Man+Key Left 3",     0x5D: "Man+Key Left 4", 
    0x5E: "Man+Key Right 1",  0x5F: "Man+Key Right 2",    0x60: "Man+Key Right 3", 
    0x61: "Man+Key Right 4",
    # Walls 
    0x00: "Wall 01",          0x01: "Wall 02",            0x02: "Wall 03", 
    0x03: "Wall 04",          0x04: "Wall 05",            0x05: "Wall 06", 
    0x06: "Wall 07",          0x07: "Wall 08",            0x08: "Wall 09", 
    0x09: "Wall 10",          0x0A: "Wall 11",            0x0B: "Wall 12",
    0x0C: "Wall 13",          0x0D: "Wall 14",            0x0E: "Wall 15", 
    0x11: "Wall 16",          0x13: "Wall 17",            0x1F: "Wall 18", 
    0x20: "Wall 19",          0x27: "Wall 20",            0x28: "Wall 21",
    # Monster Spawn Cloud
    0x56: "Spawn Cloud 1",    0x57: "Spawn Cloud 2",      0x58: "Spawn Cloud 3", 
    0x59: "Spawn Cloud 4",    0x63: "Spawn Cloud 5", 
    # Adventurer Death (Skull)
    0x67: "Man Death 1",      0x68: "Man Death 2",        0x69: "Man Death 3", 
    0x6A: "Man Death 4",
    # Monster Death (Particles)
    0x6B: "Monster Death 1",  0x6C: "Monster Death 2",    0x6D: "Monster Death 3",
    0x6E: "Monster Death 4", 
    # Object Boxes 
    0x4A: "Empty Crown Box",  0x21: "Empty Ring Box",     0x22: "Empty Key Box",
    0x62: "Full Crown Box",   0x6F: "Full Ring Box",      0x70: "Full Key Box",
    # Score Boxes
    0x80: "Score Box - 500",  0x81: "Score Box - 1000",   0x82: "Score Box - 1500",
    0x83: "Score Box - 2000", 0x84: "Score Box - 3000",   0x85: "Score Box - 4000",
    # Teleport Pillars
    0x64: "Teleport Left",    0x65: "Teleport Right",
    # Monster Spawner Walls
    0x1D: "Spawn Top Left",   0x0F: "Spawn Top Center",   0x10: "Spawn Top Right", 
    0x1B: "Spawn Middle Left",                            0x12: "Spawn Middle Right", 
    0x18: "Spawn Bottom Left",0x15: "Spawn Bottom Center",0x14: "Spawn Bottom Right",
    # Keyhole
    0x72: "Keyhole 1",        0x16: "Keyhole 2",          0x1E: "Keyhole 3",
    0x4D: "Keyhole 4",        0x66: "Keyhole 5",          0x71: "Keyhole 6",
    # Big Door
    0x73: "Door Top Left",    0x74: "Door Top Center",    0x75: "Door Top Right", 
    0x76: "Door Middle Left", 0x77: "Door Middle Center", 0x78: "Door Middle Right", 
    0x79: "Door Bottom Left", 0x7A: "Door Bottom Center", 0x7B: "Door Bottom Right",
    # Tut Mask
    0x86: "Tut Mask Left",    0x87: "Tut Mask Right",     0x88: "Tut Mask Center",
    # Cobra
    0x36: "Cobra Left 1",     0x37: "Cobra Left 2",       0x38: "Cobra Left 3", 
    0x39: "Cobra Left 4",     0x46: "Cobra Right 1",      0x47: "Cobra Right 2", 
    0x48: "Cobra Right 3",    0x49: "Cobra Right 4", 
    # Vulture
    0x3E: "Vulture Left 1",   0x3F: "Vulture Left 2",     0x40: "Vulture Left 3",
    0x41: "Vulture Left 4",   0x42: "Vulture Right 1",    0x43: "Vulture Right 2",
    0x44: "Vulture Right 3",  0x45: "Vulture Right 4", 
    # Bat
    0x32: "Bat 1",            0x33: "Bat 2",              0x34: "Bat 3", 
    0x35: "Bat 4",            0x7C: "Bat 5",              0x7D: "Bat 6", 
    0x7E: "Bat 7", 
    # Dragon
    0x89: "Dragon Left 1",    0x8A: "Dragon Left 2",      0x8B: "Dragon Left 3",
    0x8C: "Dragon Left ",     0x8D: "Dragon Right 1",     0x8E: "Dragon Right 2",
    0x8F: "Dragon Right 3",   0x90: "Dragon Right 4",
    # Gryphon
    0x91: "Gryphon Left 1",   0x92: "Gryphon Left 2",     0x93: "Gryphon Left 3",
    0x94: "Gryphon Left 4",   0x95: "Gryphon Right 1",    0x96: "Gryphon Right 2",
    0x97: "Gryphon Right 3",  0x98: "Gryphon Right 4",
    # Glaive
    0x99: "Glaive 1",         0x9A: "Glaive 2",           0x9B: "Glaive 3",
    0x9C: "Glaive 4",         0x9D: "Glaive 5",           0x9E: "Glaive 6",
    0x9F: "Glaive 7",
   # Unknown/Unused
    0x17: "Flame 1 (Unused)",
    0x19: "Flame 2 (Unused)", 
    0x1A: "Flame 3 (Unused)",
    0x1C: "Flame 4 (Unused)", 
    0x4B: "Score Box - 2000 (Unused)", 
    0x4C: "Score Box - 3000 (Unused)",
    0x7F: "Rock? (Unused)"
}

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
    global all_tiles, visual_maps, logical_maps, palettes, high_scores
    
    try:
        # Load all ROMs into memory first
        if location == "Zip":
            load_roms_from_zip()
        elif location == "Folder":
                folder = filedialog.askdirectory(
                    title="Select Folder That Contains Your Extracted Tutankham ROMs",
                    initialdir=os.path.abspath("."))
                if not folder:
                    return  # User cancelled
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
                "Data loaded — %d tiles, %d visual maps, %d logical maps, %d palettes, %d high_scores",
                len(all_tiles), len(visual_maps), len(logical_maps), len(palettes), len(high_scores)
            )
    except Exception as e:
        logging.error(f"Error loading ROMs: {e}")
        messagebox.showerror("Error", f"Failed to load ROMs:\n{e}")

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

def save_roms(target_directory):
    """Save all ROMs"""
    try:
        # Update checksums before saving
        update_copyright_checksum()
        
        # Save to cache
        save_visual_maps_to_rom(visual_maps)
        save_logical_maps_to_rom(logical_maps)

        # High Scores and Palettes are already written to the rom_cache - DO NOT SAVE STALE STRUCTURES!!!!

        # Write to disk
        save_all_roms(target_directory)
        
        messagebox.showinfo("Success", "ROMs saved successfully")
    except Exception as e:
        logging.error(f"Error saving ROMs: {e}")
        messagebox.showerror("Error", f"Failed to save ROMs:\n{e}")

def save_roms_to_folder():
    """Save ROMs to a selected folder"""
    directory = filedialog.askdirectory(title="Select directory to save ROM files")
    if directory:
        save_roms(directory)

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

def get_tile_name(tile_id):
    """Get human-readable name for a tile"""
    return TILE_NAMES.get(tile_id, f"Tile {tile_id:02X}")

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
# Map Configuration Functions
#########################################

def load_map_config(map_index, difficulty=0):
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

def save_map_config(map_index, difficulty, config):
    """Save map configuration block back to ROM"""
    block_number = (difficulty * 4) + map_index
    offset = CONFIG_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
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
# Menu Launch Functions
#########################################

def launch_map_editor():
    """Launch the map editor in a new window"""
    global open_windows
    
    # Check if window already exists and is still open
    if open_windows['map_editor'] is not None:
        try:
            open_windows['map_editor'].lift()  # Bring to front
            open_windows['map_editor'].focus_force()  # Give it focus
            return
        except tk.TclError:
            # Window was destroyed but reference wasn't cleared
            open_windows['map_editor'] = None
    
    try:
        # Create new window
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham Map Editor {EDITOR_VERSION}")
        editor_window.geometry("1800x1000")
        
        # Store reference
        open_windows['map_editor'] = editor_window
        
        # Clear reference when window is closed
        def on_close():
            open_windows['map_editor'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Import the MapEditor class from Editor15.py
        # For now, show a message
        messagebox.showinfo("Map Editor", "Map Editor will be launched here")
        
    except Exception as e:
        logging.error(f"Error launching map editor: {e}")
        messagebox.showerror("Error", f"Failed to launch map editor:\n{e}")
        open_windows['map_editor'] = None

# Add this to the launch functions section (around line 380):

def launch_tile_editor():
    """Launch the tile/graphics editor"""
    global open_windows
    
    if open_windows['tile_editor'] is not None:
        try:
            open_windows['tile_editor'].lift()
            open_windows['tile_editor'].focus_force()
            return
        except tk.TclError:
            open_windows['tile_editor'] = None
    
    try:
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham Tile Editor {EDITOR_VERSION}")
        editor_window.geometry("1800x1000")
        
        open_windows['tile_editor'] = editor_window
        
        def on_close():
            open_windows['tile_editor'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build tile editor UI
        build_tile_editor_window(editor_window)
        
    except Exception as e:
        logging.error(f"Error launching tile editor: {e}")
        messagebox.showerror("Error", f"Failed to launch tile editor:\n{e}")
        open_windows['tile_editor'] = None

def launch_font_editor():
    """Launch the font editor"""
    messagebox.showinfo("Font Editor", "Font Editor - Coming soon!")

def launch_ui_graphics_editor():
    """Launch the UI graphics editor"""
    messagebox.showinfo("UI Graphics", "UI Graphics Editor - Coming soon!")

def launch_treasure_editor():
    """Launch the treasure graphics editor"""
    messagebox.showinfo("Treasure Editor", "Treasure Editor - Coming soon!")

def launch_high_score_editor():
    """Launch the high score data editor"""
    global open_windows
    
    if open_windows['high_score'] is not None:
        try:
            open_windows['high_score'].lift()
            open_windows['high_score'].focus_force()
            return
        except tk.TclError:
            open_windows['high_score'] = None
    
    try:
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham High Score Editor {EDITOR_VERSION}")
        editor_window.geometry("420x600")
        
        open_windows['high_score'] = editor_window
        
        def on_close():
            open_windows['high_score'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build high score editor UI
        build_high_score_window(editor_window)
        
    except Exception as e:
        logging.error(f"Error launching high score editor: {e}")
        messagebox.showerror("Error", f"Failed to launch high score editor:\n{e}")
        open_windows['high_score'] = None
        
def launch_palette_editor():
    """Launch the palette editor"""
    global open_windows
    
    if open_windows['palette'] is not None:
        try:
            open_windows['palette'].lift()
            open_windows['palette'].focus_force()
            return
        except tk.TclError:
            open_windows['palette'] = None
    
    try:
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham Palette Editor {EDITOR_VERSION}")
        editor_window.geometry("780x1040")
        
        open_windows['palette'] = editor_window
        
        def on_close():
            open_windows['palette'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build palette editor UI
        build_palette_window(editor_window)
        
    except Exception as e:
        logging.error(f"Error launching palette editor: {e}")
        messagebox.showerror("Error", f"Failed to launch palette editor:\n{e}")
        open_windows['palette'] = None

#########################################
# Map Tile Editor Functions
#########################################

# Add this after the palette editor functions (around line 700):

def build_tile_editor_window(window):
    """Build the tile editor interface"""
    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = ttk.Label(main_frame, text="Tutankham Tile Editor", 
                            font=('Arial', 16, 'bold'))
    title_label.pack(pady=10)
    
    # Control frame
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill=tk.X, pady=5)
    
    # Palette selector
    ttk.Label(control_frame, text="Palette:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    palette_names = ["Map 1 Walls", "Map 2 Walls", "Map 3 Walls", "Map 4 Walls",
                    "Unknown 1", "Unknown 2", "Unknown 3"]
    
    window.selected_palette_idx = tk.IntVar(value=0)
    palette_dropdown = ttk.Combobox(control_frame, 
                                   values=palette_names,
                                   state="readonly", 
                                   width=20)
    palette_dropdown.current(0)
    palette_dropdown.pack(side=tk.LEFT, padx=5)
    palette_dropdown.bind("<<ComboboxSelected>>", 
                         lambda e: rebuild_tile_grid(window))
    
    window._palette_dropdown = palette_dropdown

    ttk.Button(control_frame, text="Close", 
              command=window.destroy).pack(side=tk.RIGHT, padx=5)

    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Tile grid frame (no scrolling, just display all tiles)
    tile_frame = ttk.Frame(main_frame)
    tile_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    # Store references
    window._tile_frame = tile_frame
    window._tile_images = []
   
    # Status frame
    window.tile_status_frame = ttk.Frame(main_frame)
    window.tile_status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    window.tile_status_label = ttk.Label(window.tile_status_frame, 
                                        text="Ready - Click Any Tile To Edit", 
                                        relief=tk.SUNKEN, anchor=tk.W)
    window.tile_status_label.pack(fill=tk.X, padx=5, pady=2)
    
    # Build initial tile grid
    rebuild_tile_grid(window)

def rebuild_tile_grid(window):
    """Rebuild the tile grid with current palette"""
    tile_frame = window._tile_frame
    window._tile_images.clear()
    
    # Clear existing widgets
    for widget in tile_frame.winfo_children():
        widget.destroy()
    
    # Get current palette
    palette_idx = window._palette_dropdown.current()
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Grid configuration
    tiles_per_row = 20
    tile_spacing = 10
    tile_scale = 3  # Display at 3x (48x48 pixels) - bigger for better visibility
    
    # Configure grid to expand
    for i in range(tiles_per_row):
        tile_frame.grid_columnconfigure(i, weight=1)
    
    # Create grid of all 160 tiles
    for tile_idx in range(len(all_tiles)):
        row = tile_idx // tiles_per_row
        col = tile_idx % tiles_per_row
        
        # Create frame for this tile
        tile_container = ttk.Frame(tile_frame, relief=tk.RAISED, borderwidth=1)
        tile_container.grid(row=row, column=col, padx=tile_spacing, pady=tile_spacing, sticky='nsew')
        
        # Hex ID label above
        hex_label = ttk.Label(tile_container, text=f"0x{tile_idx:02X}", 
                             font=('Courier', 9, 'bold'), foreground='#000000')
        hex_label.pack(pady=(5, 2))
        
        # Tile image
        tile = all_tiles[tile_idx]
        color_tile = apply_palette_to_tile(tile, palette)
        
        # Scale up
        tile_scaled = np.repeat(np.repeat(color_tile, tile_scale, axis=0), tile_scale, axis=1)
        tile_rgb = tile_scaled[:, :, :3]
        tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
        tile_photo = ImageTk.PhotoImage(tile_img)
        
        # Store reference
        window._tile_images.append(tile_photo)
        
        # Clickable label with border for visibility
        tile_label = tk.Label(tile_container, image=tile_photo, 
                             bg='#2b2b2b', cursor='hand2',
                             relief=tk.SUNKEN, borderwidth=2)
        tile_label.pack(pady=2)
        tile_label.bind('<Button-1>', 
                       lambda e, tid=tile_idx: open_tile_editor(window, tid))
        
    # Log to confirm it's working
    logging.info(f"Rebuilt tile grid with {len(all_tiles)} tiles using palette {palette_idx}")

def open_tile_editor(window, tile_idx):
    """Open tile editor dialog for a specific tile"""
    # Get current palette
    palette_idx = window._palette_dropdown.current()
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Create dialog
    dialog = tk.Toplevel(window)
    dialog.title(f"Edit Tile 0x{tile_idx:02X} - {get_tile_name(tile_idx)}")
    dialog.geometry("400x500")
    dialog.transient(window)
    dialog.update_idletasks()  # Ensure window is ready
    dialog.grab_set()
    
    main_frame = ttk.Frame(dialog, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    ttk.Label(main_frame, 
             text=f"Tile 0x{tile_idx:02X}: {get_tile_name(tile_idx)}",
             font=('Arial', 12, 'bold')).pack(pady=10)
    
    # TODO: Add pixel editor canvas here (160x160 pixels, 10x zoom)
    # TODO: Add color palette selector
    # TODO: Add save/cancel buttons
    
    ttk.Label(main_frame, text="Tile editor coming next...", 
             font=('Arial', 10, 'italic')).pack(pady=50)
    
    ttk.Button(main_frame, text="Close", 
              command=dialog.destroy).pack(pady=10)

#########################################
# High Score Editor Functions
#########################################

def build_high_score_window(window):
    """Build the high score editor interface"""
    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = ttk.Label(main_frame, text="Tutankham High Score Editor", 
                            font=('Arial', 16, 'bold'))
    title_label.pack(pady=10)
    
    # Instructions
    info_label = ttk.Label(main_frame, 
                          text="Edit High Scores Below",
                          font=('Arial', 9))
    info_label.pack(pady=5)
    
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Content frame (no scrollbar needed - 8 entries fit easily)
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill=tk.BOTH, expand=True)
    
    # Store reference
    window._content_frame = content_frame
    
    # Build the entries
    rebuild_high_score_entries(window)

    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

    # Utility buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(button_frame, text="Reset to Defaults", 
              command=lambda: reset_high_scores(window)).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Close", 
              command=window.destroy).pack(side=tk.RIGHT, padx=5)

    # Add a status frame
    window.hs_status_frame = ttk.Frame(main_frame)
    window.hs_status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    window.hs_status_label = ttk.Label(window.hs_status_frame, text="Ready To Edit High Scores", 
                        relief=tk.SUNKEN, anchor=tk.W)
    window.hs_status_label.pack(fill=tk.X, padx=5, pady=2)

def rebuild_high_score_entries(window):
    """Rebuild all high score entry widgets"""
    content_frame = window._content_frame
    
    # Clear existing widgets
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    high_scores = load_high_scores()
    
    # HIGH SCORE entry (read-only) - make it stand out
    hs_frame = ttk.LabelFrame(content_frame, text="HIGH SCORE", 
                              padding=10)
    hs_frame.pack(fill=tk.X, padx=5, pady=5)
    
    score_int = bcd_to_int(high_scores[0]['score'])
    ttk.Label(hs_frame, text=f"{score_int}", 
             font=('Courier', 16, 'bold'), 
             foreground='blue').pack()
    
    ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Regular entries in a grid
    rank_names = ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH"]
    
    # Header row
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill=tk.X, padx=5, pady=5)
    
    ttk.Label(header_frame, text="Rank", font=('Arial', 9, 'bold'), width=6).grid(row=0, column=0, padx=5)
    ttk.Label(header_frame, text="Score", font=('Arial', 9, 'bold'), width=10).grid(row=0, column=1, padx=5)
    ttk.Label(header_frame, text="Name", font=('Arial', 9, 'bold'), width=8).grid(row=0, column=2, padx=5)
    ttk.Label(header_frame, text="Stage", font=('Arial', 9, 'bold'), width=8).grid(row=0, column=3, padx=5)
    ttk.Label(header_frame, text="", width=8).grid(row=0, column=4, padx=5)  # Update button column
    
    # Data rows
    for i in range(NUM_HIGH_SCORES):
        build_high_score_row_grid(window, content_frame, high_scores, i + 1, rank_names[i], i + 1)

def build_high_score_row_grid(window, parent, high_scores, index, label, row):
    """Build a single high score entry row in grid format"""
    entry = high_scores[index]
    score_int = bcd_to_int(entry['score'])
    
    # Create frame for this row
    row_frame = ttk.Frame(parent)
    row_frame.pack(fill=tk.X, padx=5, pady=2)
    
    # Rank label
    ttk.Label(row_frame, text=label, font=('Arial', 10, 'bold'), width=6).grid(row=0, column=0, padx=5)
    
    # Score entry
    score_var = tk.StringVar(value=str(score_int))
    score_entry = ttk.Entry(row_frame, textvariable=score_var, width=10, font=('Courier', 10))
    score_entry.grid(row=0, column=1, padx=5)
    
    # Name entry
    name_var = tk.StringVar(value=entry['name'])
    name_entry = ttk.Entry(row_frame, textvariable=name_var, width=5, font=('Courier', 10))
    name_entry.grid(row=0, column=2, padx=5)
    
    # Stage spinbox
    stage_var = tk.StringVar(value=str(entry['stage']))
    stage_spinbox = ttk.Spinbox(row_frame, textvariable=stage_var, 
                                from_=0, to=255, width=6)
    stage_spinbox.grid(row=0, column=3, padx=5)
    
    # Update button
    update_btn = ttk.Button(row_frame, text="Update", 
                           command=lambda: update_high_score_entry(
                               index, score_var, name_var, stage_var, window))
    update_btn.grid(row=0, column=4, padx=5)

def update_high_score_entry(index, score_var, name_var, stage_var, window):
    """Update a single high score entry"""
    try:
        high_scores = load_high_scores()
        
        # Validate and update score
        score_int = int(score_var.get())
        if score_int < 0 or score_int > 999999:
            messagebox.showwarning("Invalid Score", "Score must be between 0 and 999,999")
            return
        
        high_scores[index]['score'] = int_to_bcd(score_int)

        # Update name
        name = name_var.get().upper()[:3]
        if not all(32 <= ord(c) < 127 for c in name):
            messagebox.showwarning("Invalid Name", "Name must contain only ASCII characters")
            return
        high_scores[index]['name'] = name
        
        # Update stage
        stage = int(stage_var.get())
        if stage < 0 or stage > 255:
            messagebox.showwarning("Invalid Stage", "Stage must be between 0 and 255")
            return
        high_scores[index]['stage'] = stage
        
        sort_high_scores(high_scores)               	# Sort High Scores
        sync_high_score(high_scores)		            # Sync High Score With 1ST Place
        save_high_scores(high_scores)		            # Save High Scores
        rebuild_high_score_entries(window)              # Rebuild UI to show changes

        window.hs_status_label.config(text=f"Successfully Updated Entry {index}")
        
    except ValueError:
        messagebox.showwarning("Invalid Input", "Please enter valid numbers")

def sync_high_score(high_scores):
    """Sync HIGH SCORE with highest ranked score"""
    if len(high_scores) < 2:
        return
    max_score = max(bcd_to_int(entry['score']) for entry in high_scores[1:])
    high_scores[0]['score'] = int_to_bcd(max_score)

def sort_high_scores(high_scores):
    """Sort high scores in descending order"""
    ranked_entries = high_scores[1:]
    ranked_entries.sort(key=lambda x: bcd_to_int(x['score']), reverse=True)
    high_scores[1:] = ranked_entries
    return high_scores


def reset_high_scores(window):
    """Reset high scores to defaults"""
    if not messagebox.askyesno("Confirm Reset", 
                               "Reset all high scores to defaults?",
                               parent=window):
        return
    
    default_scores = [
        {'score': int_to_bcd(35840), 'name':    '', 'stage': 0},
        {'score': int_to_bcd(35840), 'name': 'HTA', 'stage': 2},
        {'score': int_to_bcd(34060), 'name': 'MNU', 'stage': 2},
        {'score': int_to_bcd(33860), 'name': 'SIS', 'stage': 2},
        {'score': int_to_bcd(29660), 'name': 'KKO', 'stage': 1},
        {'score': int_to_bcd(23460), 'name': 'YNA', 'stage': 1},
        {'score': int_to_bcd(15860), 'name': 'FUJ', 'stage': 1},
        {'score': int_to_bcd(12060), 'name': 'MAT', 'stage': 1},
    ]
    
    save_high_scores(default_scores)
    rebuild_high_score_entries(window)
    window.hs_status_label.config(text=f"Restored Factory Default High Scores")

#########################################
# Palette Editor Functions
#########################################

def build_palette_window(window):
    """Build the palette editor interface"""
    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = ttk.Label(main_frame, text="Tutankham Palette Editor", 
                            font=('Arial', 16, 'bold'))
    title_label.pack(pady=10)
    
    # Instructions
    info_label = ttk.Label(main_frame, 
                          text="Click any color swatch to edit.",
                          font=('Arial', 9))
    info_label.pack(pady=5)
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill=tk.BOTH, expand=True)
    
    # Store reference
    window._content_frame = content_frame
    window._palette_images = []  # Store PhotoImage references
    
    # Build the palette grid
    rebuild_palette_grid(window)
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Utility buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(button_frame, text="Reset to Defaults", 
              command=lambda: reset_palettes(window)).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Close", 
              command=window.destroy).pack(side=tk.RIGHT, padx=5)
    
    # Status frame
    window.pal_status_frame = ttk.Frame(main_frame)
    window.pal_status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    window.pal_status_label = ttk.Label(window.pal_status_frame, 
                                        text="Ready - Click Any Color To Edit", 
                                        relief=tk.SUNKEN, anchor=tk.W)
    window.pal_status_label.pack(fill=tk.X, padx=5, pady=2)

def rebuild_palette_grid(window):
    """Rebuild the palette grid showing all 7 palettes"""
    content_frame = window._content_frame
    window._palette_images.clear()
    
    # Clear existing widgets
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    palettes = load_palettes_from_rom()
    
    palette_names = [
        "Map 1 Walls",
        "Map 2 Walls", 
        "Map 3 Walls",
        "Map 4 Walls",
        "Unknown 1",
        "Unknown 2",
        "Unknown 3"
    ]
    
    # Build each palette row
    for pal_idx, pal_name in enumerate(palette_names):
        build_palette_row(window, content_frame, palettes, pal_idx, pal_name)
        
        # Add separator between palettes
        if pal_idx < len(palette_names) - 1:
            ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

def build_palette_row(window, parent, palettes, palette_idx, palette_name):
    """Build a single palette row with 15 color swatches"""
    # Row frame
    row_frame = ttk.LabelFrame(parent, text=palette_name, padding=5)
    row_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Color swatches frame
    swatches_frame = ttk.Frame(row_frame)
    swatches_frame.pack(fill=tk.X)
    
    palette = palettes[palette_idx]
    
    # Create 15 color swatches (index 0-14, skip 15 which is always 0x00)
    for color_idx in range(15):
        color_frame = ttk.Frame(swatches_frame)
        color_frame.grid(row=0, column=color_idx, padx=2, pady=2)
        
        # Get RGB values
        r, g, b = palette[color_idx][1], palette[color_idx][2], palette[color_idx][3]
        hex_color = f'#{r:02x}{g:02x}{b:02x}'
        
        # Create color swatch as a canvas
        swatch = tk.Canvas(color_frame, width=40, height=40, 
                          bg=hex_color, highlightthickness=2, 
                          highlightbackground='gray')
        swatch.pack()
        
        # Label below swatch
        ttk.Label(color_frame, text=str(color_idx), 
                 font=('Arial', 8)).pack()
        
        # Bind click event
        swatch.bind('<Button-1>', 
                   lambda e, p=palette_idx, c=color_idx: edit_palette_color(window, p, c))
        
        # Store reference
        window._palette_images.append(swatch)

def edit_palette_color(window, palette_idx, color_idx):
    """Open color editor dialog for a specific palette color"""
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Get current RGB values
    r, g, b = palette[color_idx][1], palette[color_idx][2], palette[color_idx][3]
    
    # Create dialog
    dialog = tk.Toplevel(window)
    dialog.title(f"Edit Color {color_idx}")
    dialog.geometry("350x400")
    dialog.transient(window)
    dialog.update_idletasks()  # Ensure window is ready
    dialog.grab_set()
    
    main_frame = ttk.Frame(dialog, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    palette_names = ["Map 1 Walls", "Map 2 Walls", "Map 3 Walls", "Map 4 Walls",
                    "Unknown 1", "Unknown 2", "Unknown 3"]
    
    ttk.Label(main_frame, 
             text=f"{palette_names[palette_idx]} - Color {color_idx}",
             font=('Arial', 12, 'bold')).pack(pady=10)
    
    # Preview frame
    preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding=10)
    preview_frame.pack(fill=tk.X, pady=10)
    
    preview_canvas = tk.Canvas(preview_frame, width=80, height=80, 
                              bg=f'#{r:02x}{g:02x}{b:02x}')
    preview_canvas.pack()
    
    # RGB sliders
    sliders_frame = ttk.Frame(main_frame)
    sliders_frame.pack(fill=tk.X, pady=10)
    
    # Convert to bit values
    r_bits = int(round(r * 7 / 255))
    g_bits = int(round(g * 7 / 255))
    b_bits = int(round(b * 3 / 255))
    
    # Red slider (3-bit: 0-7)
    red_frame = ttk.Frame(sliders_frame)
    red_frame.pack(fill=tk.X, pady=5)
    ttk.Label(red_frame, text="Red (0-7):", width=10).pack(side=tk.LEFT)
    red_var = tk.IntVar(value=r_bits)
    red_scale = ttk.Scale(red_frame, from_=0, to=7, orient=tk.HORIZONTAL,
                         variable=red_var, 
                         command=lambda v: update_color_preview(preview_canvas, 
                                                                red_var, green_var, blue_var))
    red_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    red_label = ttk.Label(red_frame, text=str(r_bits), width=3)
    red_label.pack(side=tk.LEFT)
    
    # Green slider (3-bit: 0-7)
    green_frame = ttk.Frame(sliders_frame)
    green_frame.pack(fill=tk.X, pady=5)
    ttk.Label(green_frame, text="Green (0-7):", width=10).pack(side=tk.LEFT)
    green_var = tk.IntVar(value=g_bits)
    green_scale = ttk.Scale(green_frame, from_=0, to=7, orient=tk.HORIZONTAL,
                           variable=green_var,
                           command=lambda v: update_color_preview(preview_canvas, 
                                                                  red_var, green_var, blue_var))
    green_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    green_label = ttk.Label(green_frame, text=str(g_bits), width=3)
    green_label.pack(side=tk.LEFT)
    
    # Blue slider (2-bit: 0-3)
    blue_frame = ttk.Frame(sliders_frame)
    blue_frame.pack(fill=tk.X, pady=5)
    ttk.Label(blue_frame, text="Blue (0-3):", width=10).pack(side=tk.LEFT)
    blue_var = tk.IntVar(value=b_bits)
    blue_scale = ttk.Scale(blue_frame, from_=0, to=3, orient=tk.HORIZONTAL,
                          variable=blue_var,
                          command=lambda v: update_color_preview(preview_canvas, 
                                                                 red_var, green_var, blue_var))
    blue_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    blue_label = ttk.Label(blue_frame, text=str(b_bits), width=3)
    blue_label.pack(side=tk.LEFT)
    
    # Store label references for updates
    dialog._red_label = red_label
    dialog._green_label = green_label
    dialog._blue_label = blue_label
    
    # Button frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=10)
    
    ttk.Button(button_frame, text="Apply", 
              command=lambda: apply_palette_color(window, dialog, palette_idx, color_idx,
                                                  red_var, green_var, blue_var)).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Cancel", 
              command=dialog.destroy).pack(side=tk.LEFT, padx=5)

def update_color_preview(canvas, red_var, green_var, blue_var):
    """Update the color preview canvas"""
    # Get bit values
    r_bits = int(red_var.get())
    g_bits = int(green_var.get())
    b_bits = int(blue_var.get())
    
    # Scale to 0-255
    r = int(r_bits * 255 / 7)
    g = int(g_bits * 255 / 7)
    b = int(b_bits * 255 / 3)
    
    hex_color = f'#{r:02x}{g:02x}{b:02x}'
    canvas.configure(bg=hex_color)
    
    # Update labels if they exist
    dialog = canvas.master.master
    if hasattr(dialog, '_red_label'):
        dialog._red_label.config(text=str(r_bits))
    if hasattr(dialog, '_green_label'):
        dialog._green_label.config(text=str(g_bits))
    if hasattr(dialog, '_blue_label'):
        dialog._blue_label.config(text=str(b_bits))

def apply_palette_color(window, dialog, palette_idx, color_idx, red_var, green_var, blue_var):
    """Apply the edited color to the palette"""
    try:
        # Get bit values
        r_bits = int(red_var.get())
        g_bits = int(green_var.get())
        b_bits = int(blue_var.get())
        
        # Scale to 0-255
        r = int(r_bits * 255 / 7)
        g = int(g_bits * 255 / 7)
        b = int(b_bits * 255 / 3)
        
        # Update palette in memory
        palettes = load_palettes_from_rom()
        palettes[palette_idx][color_idx] = (255, r, g, b)
        
        # Write to ROM cache
        palette_offset = PALETTE_FILE_OFFSETS[palette_idx]
        palette_byte = encode_palette_byte(r, g, b)
        rom_cache[ROM_CONFIG['palette_rom']][palette_offset + color_idx] = palette_byte
        
        # Close dialog
        dialog.destroy()
        
        # Rebuild palette grid
        rebuild_palette_grid(window)
        
        palette_names = ["Map 1", "Map 2", "Map 3", "Map 4", "Unknown 1", "Unknown 2", "Unknown 3"]
        window.pal_status_label.config(text=f"Updated {palette_names[palette_idx]} color {color_idx}")
        
    except Exception as e:
        logging.error(f"Error applying color: {e}")
        messagebox.showerror("Error", f"Failed to apply color:\n{e}")

def reset_palettes(window):
    """Reset all palettes to factory defaults"""
    if not messagebox.askyesno("Confirm Reset", 
                               "Reset all palettes to factory defaults?",
                               parent=window):
        return
    
    # Factory default palette values (from original Tutankham ROM)
    default_palettes = [
        # Map 1
        [0x00, 0x80, 0x38, 0xA4, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x0D, 0x27, 0x87, 0xC0, 0xF2, 0xFF, 0x00],
        # Map 2
        [0x00, 0x80, 0x38, 0xC5, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x25, 0x27, 0x87, 0xC0, 0xF2, 0xFF, 0x00],
        # Map 3
        [0x00, 0x53, 0x38, 0x25, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x0D, 0xF2, 0x87, 0xC0, 0xF2, 0xFF, 0x00],
        # Map 4
        [0x00, 0x00, 0x38, 0xC0, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x0D, 0x27, 0x87, 0xC0, 0xF2, 0xFF, 0x00],
        # Unknown 1
        [0x00, 0x00, 0x38, 0xA4, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x0D, 0x27, 0x87, 0xC0, 0xF2, 0xFF, 0x00],
        # Unknown 2
        [0x00, 0x80, 0x38, 0xA4, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x0D, 0x27, 0x87, 0xC0, 0xF2, 0xFF, 0x00],
        # Unknown 3
        [0x00, 0x80, 0x38, 0xA4, 0xAF, 0xC5, 0x07, 0xA4, 0x3F, 0x0D, 0x27, 0x87, 0xC0, 0xF2, 0xFF, 0x00]
    ]
    
    # Write defaults to ROM cache
    rom_data = rom_cache[ROM_CONFIG['palette_rom']]
    for pal_idx, palette_bytes in enumerate(default_palettes):
        offset = PALETTE_FILE_OFFSETS[pal_idx]
        for color_idx, byte_val in enumerate(palette_bytes):
            rom_data[offset + color_idx] = byte_val
    
    rebuild_palette_grid(window)
    window.pal_status_label.config(text="Restored factory default palettes")

#########################################
# About Menu Functions
#########################################

def show_about():
    """Show about dialog"""
    messagebox.showinfo(
        "About",
        f"Tutankham ROM Editor {EDITOR_VERSION}\n\n"
        f"A comprehensive editor for Tutankham arcade ROM files.\n\n"
        f"Features:\n"
        f"- Map Editor\n"
        f"- Graphics/Tile Editor\n"
        f"- High Score Editor\n"
        f"- Palette Editor\n\n"
        f"Original Game:\n"
        f"- Tutankham © 1982 Konami\n"
        f"- Licensed to Stern Electronics for US distribution\n\n"
        f"ROM Analysis:\n"
        f"- MAME project for ROM definitions and memory maps\n"
        f"- Arcade hardware documentation community\n\n"
        f"Editor Development:\n"
        f"- Main development by Rodimus\n"
        f"- Collaboration with Claude (Anthropic)\n"
        f"- Assistance from Grok (xAI) for checksum implementation\n"
        f"- Assistance from ChatGPT (OpenAI) for code fixes\n"
        f"- Implemented in Python using NumPy, Tkinter, Pillow, and Colorlog\n\n"
        f"Special Thanks:\n"
        f"- MAME developers for emulation and debugging tools\n"
        f"- Arcade preservation community\n"
        f"- Tutankham speedrunning and high-score community"
    )

#########################################
# Initialize Main TK Window
#########################################

root = tk.Tk()
root.title(f"Tutankham ROM Editor {EDITOR_VERSION}")
root.geometry("400x300")

#########################################
# Create Dropdown Menus
#########################################

menubar = tk.Menu(root)
# --- File Menu ---
filemenu = tk.Menu(menubar, tearoff=False)
filemenu.add_command(label="-- File Operations --", state="disabled")
filemenu.add_separator()
filemenu.add_command(label="-- Loading --", state="disabled")
filemenu.add_command(label="Reload Original ROMs From Zip", 
                    command=lambda: load_all("Zip"))
filemenu.add_command(label="Open ROMs From Current Directory", 
                    command=lambda: load_all(None))
filemenu.add_command(label="Open ROMs From Folder", 
                    command=lambda: load_all("Folder"))
filemenu.add_separator()
filemenu.add_command(label="-- Saving --", state="disabled")
filemenu.add_command(label="Save ROMs", 
                    command=lambda: save_roms(None))
filemenu.add_command(label="Save ROMs To Folder", 
                    command=lambda: save_roms_to_folder())
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)
# --- Editor Menu ---
editormenu = tk.Menu(menubar, tearoff=False)
editormenu.add_command(label="-- Map Editor --", state="disabled")
editormenu.add_command(label="Edit Maps", command=launch_map_editor)
editormenu.add_separator()
editormenu.add_command(label="-- Tile / Graphics Editor --", state="disabled")
editormenu.add_command(label="Edit Tiles", command=launch_tile_editor)
editormenu.add_command(label="Edit Fonts", command=launch_font_editor)
editormenu.add_command(label="Edit UI Graphics", command=launch_ui_graphics_editor)
editormenu.add_command(label="Edit Treasures", command=launch_treasure_editor)
editormenu.add_separator()
editormenu.add_command(label="-- Data Editor --", state="disabled")
editormenu.add_command(label="High Scores", command=launch_high_score_editor)
editormenu.add_command(label="Palette", command=launch_palette_editor)
menubar.add_cascade(label="Editors", menu=editormenu)
# --- Help Menu ---
helpmenu = tk.Menu(menubar, tearoff=False)
helpmenu.add_command(label="About", 
                    command=lambda: show_about())
menubar.add_cascade(label="Help", menu=helpmenu)

#########################################
# Main Code
#########################################

root.config(menu=menubar)				# Attach to window
all_tiles = visual_maps = logical_maps = None		# Initialize Global Variables
palettes = high_scores = None				# Initialize Global Variables
load_all("Zip")						# Load initial data from zip
create_window_icon(root, all_tiles, palettes)		# Create Window Icon


# Add a status label to main window
status_frame = ttk.Frame(root)
status_frame.pack(side=tk.BOTTOM, fill=tk.X)
status_label = ttk.Label(status_frame, text="Ready - Select an editor from the menu", 
                        relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(fill=tk.X, padx=5, pady=2)

# Add a welcome message to main window
welcome_frame = ttk.Frame(root, padding=20)
welcome_frame.pack(expand=True)
ttk.Label(welcome_frame, text=f"Tutankham ROM Editor {EDITOR_VERSION}", 
         font=('Arial', 18, 'bold')).pack(pady=10)
ttk.Label(welcome_frame, text="Select a function from the menu to begin", 
         font=('Arial', 12)).pack(pady=5)
ttk.Label(welcome_frame, text="Always remember to SAVE your work after editing", 
         font=('Arial', 12)).pack(pady=5)

root.mainloop()