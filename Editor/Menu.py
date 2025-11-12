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

EDITOR_VERSION = "v0.19"	# Editor Version Number
open_windows = {			# Window Tracking - ensure only one instance of each editor
    'map_editor': None,
    'tile_editor': None,
    'font_editor': None,
    'ui_graphics': None,
    'treasure_editor': None,
    'high_score': None,
    'palette': None}
state_callbacks = {         # Callback registry for cross-window updates
    'palette_changed': [],
    'tile_changed': [],
    'font_changed': []
}

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

# UI Graphics configuration
UI_GRAPHICS_CONFIG = {
    "Copyright Notice": {
        'rom': 'j6.6h',
        'offset': 0x05C0,
        'width': 16,
        'height': 102,
        'mode': 'sprite',
        'bytes_per_row': 16,
        'rotate': True,
        'zoom': 5,
        'description': 'Copyright symbol displayed on title screen'
    },
    "Timer Banner": {
        'rom': 'j6.6h',
        'offset': 0x08F0,
        'width': 32,
        'height': 39,
        'mode': 'tile',
        'rotate': True,
        'zoom': 6,
        'description': 'Timer display banner at top of screen'
    },
    "Player Counter": {
        'rom': 'j6.6h',
        'offset': 0x05A0,
        'width': 8,
        'height': 8,
        'mode': 'sprite',
        'bytes_per_row': 8,
        'rotate': True,
        'zoom': 10,
        'description': 'Player life counter icon'
    },
    "Smart Bomb Counter": {
        'rom': 'j6.6h',
        'offset': 0x0B70,
        'width': 16,
        'height': 14,
        'mode': 'sprite',
        'bytes_per_row': 16,
        'rotate': True,
        'zoom': 10,
        'description': 'Genie lamp/smart bomb counter icon'
    },
    "Stage Banner": {
        'rom': 'j6.6h',
        'offset': 0x0C60,
        'width': 30,
        'height': 32,
        'mode': 'tile',
        'rotate': True,
        'zoom': 10,
        'description': 'Stage number banner display'
    }
}

# Treasure graphics configuration (separate from UI graphics)
TREASURE_GRAPHICS_CONFIG = {
    "Treasure 1 (Map)": {
        'rom': 'c9.9i',
        'offset': 0x0000,
        'width': 44,
        'height': 44,
        'mode': 'tile',
        'rotate': True,
        'zoom': 10,
        'description': 'End of level treasure - World Map'
    },
    "Treasure 2 (Genie Lamp)": {
        'rom': 'c9.9i',
        'offset': 0x03DE,
        'width': 44,
        'height': 44,
        'mode': 'tile',
        'rotate': True,
        'zoom': 10,
        'description': 'End of level treasure - Genie Lamp'
    },
    "Treasure 3 (Treasure Chest)": {
        'rom': 'c9.9i',
        'offset': 0x07BC,
        'width': 44,
        'height': 44,
        'mode': 'tile',
        'rotate': True,
        'zoom': 10,
        'description': 'End of level treasure - Treasure Chest'
    },
    "Treasure 4 (Tut Mask)": {
        'rom': 'c9.9i',
        'offset': 0x0B9A,
        'width': 44,
        'height': 44,
        'mode': 'tile',
        'rotate': True,
        'zoom': 10,
        'description': 'End of level treasure - Tutankhamun Mask'
    }
}

FONT_NAMES = {
    # Digits (0x0000-0x013F, 10 chars × 32 bytes)
    0: "0",   1: "1",  2: "2",  3: "3",  4: "4",
    5: "5",   6: "6",  7: "7",  8: "8",  9: "9",
    # Special characters (0x0140-0x021F, 7 chars × 32 bytes)
    10: "©", 11: "□", 12: ".", 13: "!", 14: "?",
    15: "♪", 16: " ",
    # Alphabet (0x0220-0x055F, 26 chars × 32 bytes)
    17: "A", 18: "B", 19: "C", 20: "D", 21: "E", 
    22: "F", 23: "G", 24: "H", 25: "I", 26: "J", 
    27: "K", 28: "L", 29: "M", 30: "N", 31: "O", 
    32: "P", 33: "Q", 34: "R", 35: "S", 36: "T", 
    37: "U", 38: "V", 39: "W", 40: "X", 41: "Y", 
    42: "Z"
}
PALETTE_NAMES = [
    "Map 1 Colors",
    "Map 2 Colors", 
    "Map 3 Colors",
    "Map 4 Colors",
    "Unknown 1",
    "Unknown 2",
    "Unknown 3"
]

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

def register_callback(event_type, callback):
    """Register a callback for a state change event"""
    if event_type in state_callbacks:
        state_callbacks[event_type].append(callback)

def trigger_callback(event_type, *args, **kwargs):
    """Trigger all callbacks for an event type"""
    if event_type in state_callbacks:
        for callback in state_callbacks[event_type]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logging.error(f"Callback error for {event_type}: {e}")

#########################################
# Rom Handling Functions
#########################################

def load_all(location=None):
    global all_tiles, all_fonts, palettes, high_scores
    
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
        all_fonts = load_fonts()
        palettes = load_palettes_from_rom()
        high_scores = load_high_scores()
        logging.info(
                "Data loaded — %d tiles, %d palettes, %d high_scores",
                len(all_tiles), len(palettes), len(high_scores)
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
            sys.exit(1)

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
        
        # Visual maps and logical maps are already in rom_cache from direct writes
        # High Scores and Palettes are already written to rom_cache
        # Object data is already written to rom_cache via write_byte_to_roms()

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
# Font Handling Functions
#########################################

def load_fonts():
    """Load all 43 font characters from j6.6h ROM"""
    all_fonts = []
    rom_data = rom_cache['j6.6h']
    
    # Digits 0-9 (10 chars × 32 bytes)
    for i in range(10):
        offset = 0x0000 + (i * 32)
        font = extract_pixels(rom_data, offset, 8, 8)
        rotated_font = rotate_tile(font)
        all_fonts.append(rotated_font)
    
    # Special characters (7 chars × 32 bytes)
    for i in range(7):
        offset = 0x0140 + (i * 32)
        font = extract_pixels(rom_data, offset, 8, 8)
        rotated_font = rotate_tile(font)
        all_fonts.append(rotated_font)
    
    # Alphabet A-Z (26 chars × 32 bytes)
    for i in range(26):
        offset = 0x0220 + (i * 32)
        font = extract_pixels(rom_data, offset, 8, 8)
        rotated_font = rotate_tile(font)
        all_fonts.append(rotated_font)
    
    return all_fonts

def get_font_name(font_id):
    """Get human-readable name for a font character"""
    return FONT_NAMES.get(font_id, f"Font {font_id}")

#########################################
# Tile Handling Functions
#########################################

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
            tile = extract_pixels(rom_data, offset, height=16, width=16)
            rotated_tile = rotate_tile(tile)
            all_tiles.append(rotated_tile)
    return all_tiles

def get_tile_name(tile_id):
    """Get human-readable name for a tile"""
    return TILE_NAMES.get(tile_id, f"Tile {tile_id:02X}")

#########################################
# Map Handling Functions
#########################################

def load_visual_map_from_cache(map_index):
    """Load a single visual map directly from ROM cache"""
    map_data = rom_cache[ROM_CONFIG['visual_map_rom']]
    start_offset = map_index * visual_map_size
    map_layout = np.zeros((map_height, map_width), dtype=np.uint8)
    
    for byte_index in range(visual_map_size):
        row = (byte_index % map_height)
        col = (byte_index // map_height)
        flipped_row = map_height - 1 - row
        map_layout[flipped_row, col] = map_data[start_offset + byte_index]
    
    return map_layout

def write_visual_tile_to_cache(map_index, row, col, tile_id):
    """Write a single tile directly to ROM cache"""
    map_data = rom_cache[ROM_CONFIG['visual_map_rom']]
    
    flipped_row = map_height - 1 - row
    byte_index = col * map_height + flipped_row
    offset = map_index * visual_map_size + byte_index
    
    map_data[offset] = tile_id

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

def load_logical_map_from_cache(map_index):
    """Load a single logical map directly from ROM cache"""
    rom_index = map_index // 2
    map_in_rom = map_index % 2
    
    rom_name = ROM_CONFIG['logical_map_roms'][rom_index]
    rom_data = rom_cache[rom_name]
    
    start_offset = map_in_rom * logical_map_size
    map_layout = np.zeros((64, 14, 2), dtype=np.uint8)
    
    for tile_row in range(64):
        row_offset = start_offset + (tile_row * 28)
        for tile_col in range(14):
            map_layout[tile_row, tile_col, 0] = rom_data[row_offset + tile_col]
            map_layout[tile_row, tile_col, 1] = rom_data[row_offset + 14 + tile_col]
    
    return map_layout

def write_logical_tile_to_cache(map_index, logical_row, logical_col, byte_pair):
    """Write logical bytes directly to ROM cache"""
    rom_index = map_index // 2
    map_in_rom = map_index % 2
    
    rom_name = ROM_CONFIG['logical_map_roms'][rom_index]
    rom_data = rom_cache[rom_name]
    
    start_offset = map_in_rom * logical_map_size
    row_offset = start_offset + (logical_row * 28)
    
    rom_data[row_offset + logical_col] = byte_pair[0]
    rom_data[row_offset + 14 + logical_col] = byte_pair[1]

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
# Map Editor Helper Functions
#########################################

def find_door(map_index):
    """Find door position on a map - reads directly from ROM cache"""
    visual_map = load_visual_map_from_cache(map_index)
    
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

def find_spawners(map_index):
    """Find all spawner positions on a map - reads directly from ROM cache"""
    visual_map = load_visual_map_from_cache(map_index)
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

def find_teleporters(map_index):
    """Find all teleporter columns - reads directly from ROM cache"""
    visual_map = load_visual_map_from_cache(map_index)
    teleporter_cols = []
    
    for col in range(map_width):
        for row in range(map_height):
            if visual_map[row, col] in [100, 101]:  # Teleporter pillar tiles
                if col not in teleporter_cols:
                    teleporter_cols.append(col)
                break
    
    return teleporter_cols

def validate_teleporters(window):
    """Remove teleporter entries that don't have matching visual tiles"""
    for map_idx in range(num_maps):
        visual_map = load_visual_map_from_cache(map_idx)
        
        # Check all difficulties for this map
        for diff in range(NUM_DIFFICULTIES):
            objects = window.object_data[diff][map_idx]
            
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

def place_spawn_visualization_tiles(window):
    """Place spawn tiles in visual maps based on object data - writes directly to ROM cache"""
    for map_idx in range(num_maps):
        objects = window.object_data[0][map_idx]  # Use difficulty 0 as reference
        
        # Place player start tile
        if objects['player_start']['y'] != 0:
            row_from_bottom = objects['player_start']['x'] // 0x08
            row = (map_height - 1) - row_from_bottom
            col = objects['player_start']['y'] // 0x08
            
            if 0 <= row < map_height and 0 <= col < map_width:
                write_visual_tile_to_cache(map_idx, row, col, 0x29)
        
        # Place respawn flame tiles
        for i in range(objects['respawn_count']):
            respawn = objects['respawns'][i]
            if respawn['y'] != 0:
                row_from_bottom = respawn['x'] // 0x08
                row = (map_height - 1) - row_from_bottom
                col = respawn['y'] // 0x08
                if 0 <= row < map_height and 0 <= col < map_width:
                    write_visual_tile_to_cache(map_idx, row, col, 0x17)
        
        # Place keyhole tiles
        for item in objects['items']:
            if item['active'] and item['tile_id'] == 0x72:
                col = item['y'] // 0x08
                row_from_bottom = item['x'] // 0x08
                row = (map_height - 1) - row_from_bottom
                if 0 <= row < map_height and 0 <= col < map_width:
                    write_visual_tile_to_cache(map_idx, row, col, 0x72)

def validate_filled_boxes(window):
    """Check for filled boxes on visual layer and fix them - writes directly to ROM cache"""
    for map_idx in range(num_maps):
        visual_map = load_visual_map_from_cache(map_idx)
        for row in range(map_height):
            for col in range(map_width):
                tile = visual_map[row, col]
                if tile in FILLED_TO_EMPTY:
                    x = row * 0x08
                    y = col * 0x08
                    
                    has_object = False
                    for item in window.object_data[0][map_idx]['items']:
                        if item['active'] and item['x'] == x and item['y'] == y:
                            has_object = True
                            break
                    
                    if has_object:
                        write_visual_tile_to_cache(map_idx, row, col, FILLED_TO_EMPTY[tile])
                    else:
                        write_visual_tile_to_cache(map_idx, row, col, empty_path_tile)

def initialize_map_editor_state(window):
    """Initialize all state variables for the map editor"""
    
    # Selection state
    window.selected_map = 0
    window.selected_tile = 0
    window.difficulty = 0
    window.selected_object_type = None  # 'spawner', 'teleporter', 'player_start', etc.
    
    # Object placement state
    window.teleporter_first_pos = None
    window.dragging_object = None
    window.drag_ghost_pos = None
    window.selected_door = None
    window.door_drag_start = None
    window.door_ghost_pos = None
    window.selected_player_start = None
    window.player_start_ghost_pos = None
    
    # Display settings
    window.zoom_level = 3.0
    window.show_grid = tk.BooleanVar(value=False)
    window.show_objects = tk.BooleanVar(value=True)
    
    # Status variables
    window.status_var = tk.StringVar(value="Ready")
    window.coord_var = tk.StringVar(value="")
    
    # Modification tracking
    window.modified = False
    
    # Image references (prevent garbage collection)
    window.tile_images = []
    window._overlay_images = []
    window.current_map_image = None
    
    # Button references for highlighting
    window.map_buttons = {}
    
    # Load object data for ALL difficulties
    window.object_data = {}
    for diff in range(NUM_DIFFICULTIES):
        window.object_data[diff] = {}
        for i in range(num_maps):
            window.object_data[diff][i] = load_object_data(i, diff)
    
    # Load map configuration data
    window.map_config = {}
    for diff in range(NUM_DIFFICULTIES):
        window.map_config[diff] = {}
        for map_idx in range(num_maps):
            window.map_config[diff][map_idx] = load_map_config(map_idx, diff)
    
    # Validate and fix invalid teleporters
    validate_teleporters(window)
    
    # Place spawn tiles in visual maps (use difficulty 0 as reference)
    place_spawn_visualization_tiles(window)
    
    # Find composite objects
    window.door_positions = {}
    window.spawner_positions = {}
    window.teleporter_positions = {}
    for i in range(num_maps):
        window.door_positions[i] = find_door(i)
        window.spawner_positions[i] = find_spawners(i)
        window.teleporter_positions[i] = find_teleporters(i)
    
    # Validate filled boxes
    validate_filled_boxes(window)
    
    logging.info("Map editor state initialized")

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
    
    # Check if window already exists
    if open_windows['map_editor'] is not None:
        try:
            open_windows['map_editor'].lift()
            open_windows['map_editor'].focus_force()
            return
        except tk.TclError:
            open_windows['map_editor'] = None
    
    try:
        # Create new window
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham Map Editor {EDITOR_VERSION}")
        
        # Calculate window size based on map at 3x zoom
        map_display_width = map_width * 16 * 3  # 3072
        map_display_height = map_height * 16 * 3  # 576
        left_panel_width = 300
        palette_height = 250
        
        window_width = left_panel_width + map_display_width + 40
        window_height = map_display_height + palette_height + 100
        
        editor_window.geometry(f"{window_width}x{window_height}")
        
        # Store reference
        open_windows['map_editor'] = editor_window
        
        # Initialize editor state
        initialize_map_editor_state(editor_window)
        
        # Register callbacks for palette/tile changes
        def on_palette_changed(palette_idx):
            # Reload palettes
            palettes = load_palettes_from_rom()
            # If this affects our current map, refresh
            if palette_idx < 4:  # Map palettes
                if editor_window.selected_map == palette_idx:
                    render_map_view(editor_window)
                    render_tile_palette(editor_window)
            else:  # Unknown palettes - refresh anyway
                render_map_view(editor_window)
                render_tile_palette(editor_window)
        
        def on_tile_changed(tile_idx):
            # Tile changed, refresh displays
            render_map_view(editor_window)
            render_tile_palette(editor_window)
        
        register_callback('palette_changed', on_palette_changed)
        register_callback('tile_changed', on_tile_changed)
        
        # Store callback references for cleanup
        editor_window._callbacks = [on_palette_changed, on_tile_changed]
        
        # Clear reference when window is closed
        def on_close():
            # Unregister callbacks
            if hasattr(editor_window, '_callbacks'):
                for cb in editor_window._callbacks:
                    for event_type in state_callbacks:
                        if cb in state_callbacks[event_type]:
                            state_callbacks[event_type].remove(cb)
            
            open_windows['map_editor'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build the UI
        build_map_editor_ui(editor_window)
        
        # Display initial state
        render_map_view(editor_window)
        render_tile_palette(editor_window)
        update_map_counters(editor_window)
        update_map_config_display(editor_window)
        update_tile_info(editor_window)
        
        # Set window icon
        create_window_icon(editor_window, all_tiles, palettes)
        
        logging.info("Map editor launched successfully")
        
    except Exception as e:
        logging.error(f"Error launching map editor: {e}")
        messagebox.showerror("Error", f"Failed to launch map editor:\n{e}")
        open_windows['map_editor'] = None

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
    global open_windows
    
    if open_windows['font_editor'] is not None:
        try:
            open_windows['font_editor'].lift()
            open_windows['font_editor'].focus_force()
            return
        except tk.TclError:
            open_windows['font_editor'] = None
    
    try:
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham Font Editor {EDITOR_VERSION}")
        editor_window.geometry("1800x650")
        
        open_windows['font_editor'] = editor_window
        
        def on_close():
            open_windows['font_editor'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build font editor UI
        build_font_editor_window(editor_window)
        
    except Exception as e:
        logging.error(f"Error launching font editor: {e}")
        messagebox.showerror("Error", f"Failed to launch font editor:\n{e}")
        open_windows['font_editor'] = None

def launch_ui_graphics_editor():
    """Launch the UI graphics editor"""
    global open_windows
    
    if open_windows['ui_graphics'] is not None:
        try:
            open_windows['ui_graphics'].lift()
            open_windows['ui_graphics'].focus_force()
            return
        except tk.TclError:
            open_windows['ui_graphics'] = None
    
    try:
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham UI Graphics Editor {EDITOR_VERSION}")
        editor_window.geometry("800x900")
        
        open_windows['ui_graphics'] = editor_window
        
        def on_close():
            open_windows['ui_graphics'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build UI graphics editor
        build_ui_graphics_window(editor_window)
        
    except Exception as e:
        logging.error(f"Error launching UI graphics editor: {e}")
        messagebox.showerror("Error", f"Failed to launch UI graphics editor:\n{e}")
        open_windows['ui_graphics'] = None

def launch_treasure_editor():
    """Launch the treasure graphics editor"""
    global open_windows
    
    if open_windows['treasure_editor'] is not None:
        try:
            open_windows['treasure_editor'].lift()
            open_windows['treasure_editor'].focus_force()
            return
        except tk.TclError:
            open_windows['treasure_editor'] = None
    
    try:
        editor_window = tk.Toplevel(root)
        editor_window.title(f"Tutankham Treasure Editor {EDITOR_VERSION}")
        editor_window.geometry("800x900")
        
        open_windows['treasure_editor'] = editor_window
        
        def on_close():
            open_windows['treasure_editor'] = None
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Build treasure editor
        build_treasure_window(editor_window)
        
    except Exception as e:
        logging.error(f"Error launching treasure editor: {e}")
        messagebox.showerror("Error", f"Failed to launch treasure editor:\n{e}")
        open_windows['treasure_editor'] = None

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
# Map Editor Functions
#########################################

def build_map_editor_ui(window):
    """Build the map editor user interface"""
    
    # Main container
    main_frame = ttk.Frame(window)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Left panel (controls)
    window.left_panel = ttk.Frame(main_frame, width=300)
    window.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
    window.left_panel.pack_propagate(False)
    
    # Right panel (map and palette)
    right_panel = ttk.Frame(main_frame)
    right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Map frame (top of right panel)
    map_frame = ttk.LabelFrame(right_panel, text="Map Editor")
    map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Canvas frame with scrollbars
    canvas_frame = ttk.Frame(map_frame)
    canvas_frame.pack(fill=tk.BOTH, expand=True)
    
    # Calculate map display size
    map_display_width = map_width * 16 * int(window.zoom_level)
    map_display_height = map_height * 16 * int(window.zoom_level)
    
    # Map canvas
    window.map_canvas = tk.Canvas(canvas_frame, bg='black', 
                                  width=map_display_width, 
                                  height=map_display_height)
    h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, 
                            command=window.map_canvas.xview)
    v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, 
                            command=window.map_canvas.yview)
    
    window.map_canvas.configure(xscrollcommand=h_scroll.set, 
                               yscrollcommand=v_scroll.set)
    window.map_canvas.grid(row=0, column=0, sticky='nsew')
    h_scroll.grid(row=1, column=0, sticky='ew')
    v_scroll.grid(row=0, column=1, sticky='ns')
    
    canvas_frame.grid_rowconfigure(0, weight=1)
    canvas_frame.grid_columnconfigure(0, weight=1)
    
    # Bind events to map canvas
    window.map_canvas.bind("<Button-1>", lambda e: on_map_click(e, window))
    window.map_canvas.bind("<Motion>", lambda e: on_map_hover(e, window))
    window.map_canvas.bind("<B1-Motion>", lambda e: on_map_drag(e, window))
    window.map_canvas.bind("<ButtonRelease-1>", lambda e: on_map_release(e, window))
    window.map_canvas.bind("<Button-3>", lambda e: on_map_right_click(e, window))
    window.bind("<Escape>", lambda e: on_escape_key(e, window))
    
    # Palette frame (bottom of right panel)
    palette_frame = ttk.LabelFrame(right_panel, text="Tile Palette")
    palette_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=5, pady=5)
    
    # Palette canvas with scrollbars
    palette_canvas_frame = ttk.Frame(palette_frame)
    palette_canvas_frame.pack(fill=tk.BOTH, expand=True)
    
    window.palette_canvas = tk.Canvas(palette_canvas_frame, height=250, bg='#2b2b2b')
    palette_scroll_h = ttk.Scrollbar(palette_canvas_frame, orient=tk.HORIZONTAL,
                                    command=window.palette_canvas.xview)
    palette_scroll_v = ttk.Scrollbar(palette_canvas_frame, orient=tk.VERTICAL,
                                    command=window.palette_canvas.yview)
    
    window.palette_canvas.configure(xscrollcommand=palette_scroll_h.set,
                                   yscrollcommand=palette_scroll_v.set)
    window.palette_canvas.grid(row=0, column=0, sticky='nsew')
    palette_scroll_h.grid(row=1, column=0, sticky='ew')
    palette_scroll_v.grid(row=0, column=1, sticky='ns')
    
    palette_canvas_frame.grid_rowconfigure(0, weight=1)
    palette_canvas_frame.grid_columnconfigure(0, weight=1)
    
    # Build left panel contents
    build_left_panel(window)
    
    logging.info("Map editor UI built")

def build_left_panel(window):
    """Build the left control panel"""
    
    # Map/Difficulty Selection
    ttk.Label(window.left_panel, text="Map/Difficulty Selection", 
             font=('Arial', 10, 'bold')).pack(pady=5)
    
    # Map buttons with difficulty sub-buttons
    for i in range(num_maps):
        map_frame = ttk.Frame(window.left_panel)
        map_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Map button
        map_btn = ttk.Button(map_frame, text=f"Map {i + 1}", width=7,
                            command=lambda idx=i: on_map_select(idx, window))
        map_btn.pack(side=tk.LEFT, padx=2)
        window.map_buttons[('map', i)] = map_btn
        
        # Difficulty buttons
        for d in range(NUM_DIFFICULTIES):
            diff_btn = ttk.Button(map_frame, text=str(d+1), width=2,
                                 command=lambda idx=i, diff=d: select_map_and_difficulty(idx, diff, window))
            diff_btn.pack(side=tk.LEFT, padx=1)
            window.map_buttons[(i, d)] = diff_btn
    
    update_selection_highlight(window)
    
    ttk.Separator(window.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Map Config
    ttk.Label(window.left_panel, text="Map Config", 
             font=('Arial', 10, 'bold')).pack(pady=5)
    config_frame = ttk.Frame(window.left_panel)
    config_frame.pack(fill=tk.X, padx=5)
    
    # Time Limit
    time_frame = ttk.Frame(config_frame)
    time_frame.pack(fill=tk.X, pady=2)
    ttk.Label(time_frame, text="Time:").pack(side=tk.LEFT)
    window.time_limit_var = tk.StringVar()
    time_entry = ttk.Entry(time_frame, textvariable=window.time_limit_var, width=5)
    time_entry.pack(side=tk.LEFT, padx=5)
    ttk.Label(time_frame, text="sec").pack(side=tk.LEFT)
    ttk.Button(time_frame, text="Set", width=5, 
              command=lambda: set_time_limit(window)).pack(side=tk.LEFT, padx=5)
    
    # Spawn Rate
    spawn_frame = ttk.Frame(config_frame)
    spawn_frame.pack(fill=tk.X, pady=2)
    ttk.Label(spawn_frame, text="Spawn:").pack(side=tk.LEFT)
    window.spawn_rate_var = tk.StringVar()
    spawn_entry = ttk.Entry(spawn_frame, textvariable=window.spawn_rate_var, width=5)
    spawn_entry.pack(side=tk.LEFT, padx=5)
    ttk.Label(spawn_frame, text="(1-14)").pack(side=tk.LEFT)
    ttk.Button(spawn_frame, text="Set", width=5,
              command=lambda: set_spawn_rate(window)).pack(side=tk.LEFT, padx=5)
    
    ttk.Separator(window.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Object Counts
    ttk.Label(window.left_panel, text="Object Counts", 
             font=('Arial', 10, 'bold')).pack(pady=5)
    window.counter_frame = ttk.Frame(window.left_panel)
    window.counter_frame.pack(fill=tk.X, padx=5)
    
    window.items_label = ttk.Label(window.counter_frame, text="Items: 0/14")
    window.items_label.pack(anchor=tk.W)
    window.teleports_label = ttk.Label(window.counter_frame, text="Teleports: 0/6")
    window.teleports_label.pack(anchor=tk.W)
    window.spawners_label = ttk.Label(window.counter_frame, text="Spawners: 0/7")
    window.spawners_label.pack(anchor=tk.W)
    window.respawns_label = ttk.Label(window.counter_frame, text="Respawns: 0/3")
    window.respawns_label.pack(anchor=tk.W)
    
    window.validation_label = ttk.Label(window.counter_frame, text="", 
                                       foreground="red",
                                       font=('Arial', 8, 'bold'))
    window.validation_label.pack(anchor=tk.W, pady=5)
    
    ttk.Separator(window.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Display Options
    ttk.Label(window.left_panel, text="Display", 
             font=('Arial', 10, 'bold')).pack(pady=5)
    ttk.Checkbutton(window.left_panel, text="Show Grid", 
                   variable=window.show_grid,
                   command=lambda: render_map_view(window)).pack(anchor=tk.W, padx=5)
    ttk.Checkbutton(window.left_panel, text="Show Objects",
                   variable=window.show_objects,
                   command=lambda: render_map_view(window)).pack(anchor=tk.W, padx=5)
    
    # Coordinates display
    coord_frame = ttk.Frame(window.left_panel)
    coord_frame.pack(fill=tk.X, padx=5, pady=2)
    ttk.Label(coord_frame, text="Coords:").pack(side=tk.LEFT)
    ttk.Label(coord_frame, textvariable=window.coord_var).pack(side=tk.LEFT, padx=5)
    
    # Zoom controls
    zoom_frame = ttk.Frame(window.left_panel)
    zoom_frame.pack(fill=tk.X, padx=5, pady=10)
    ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
    ttk.Button(zoom_frame, text="-", width=3, 
              command=lambda: zoom_out(window)).pack(side=tk.LEFT, padx=2)
    window.zoom_label = ttk.Label(zoom_frame, text=f"{int(window.zoom_level)}x")
    window.zoom_label.pack(side=tk.LEFT, padx=2)
    ttk.Button(zoom_frame, text="+", width=3,
              command=lambda: zoom_in(window)).pack(side=tk.LEFT, padx=2)
    
    # Selected tile preview
    selected_frame = ttk.Frame(window.left_panel)
    selected_frame.pack(fill=tk.X, padx=5, pady=10)
    window.tile_info_var = tk.StringVar(value="Selected: None")
    ttk.Label(selected_frame, textvariable=window.tile_info_var).pack(side=tk.LEFT, pady=2)
    window.selected_tile_preview = tk.Label(selected_frame, bg='#2b2b2b')
    window.selected_tile_preview.pack(side=tk.LEFT, padx=10)
    
    ttk.Separator(window.left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Status bar at bottom
    status_frame = ttk.Frame(window.left_panel)
    status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    ttk.Label(status_frame, textvariable=window.status_var, 
             relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)

def update_selection_highlight(window):
    """Update button states to show current selection"""
    # Reset all buttons to normal state
    for key, btn in window.map_buttons.items():
        btn.state(['!pressed'])
    
    # Highlight selected map button
    if ('map', window.selected_map) in window.map_buttons:
        window.map_buttons[('map', window.selected_map)].state(['pressed'])
    
    # Highlight selected difficulty button
    if (window.selected_map, window.difficulty) in window.map_buttons:
        window.map_buttons[(window.selected_map, window.difficulty)].state(['pressed'])

def on_map_select(map_idx, window):
    """Handle map selection"""
    window.selected_map = map_idx
    update_selection_highlight(window)
    
    # Refresh composite positions for the new map
    window.door_positions[map_idx] = find_door(map_idx)
    window.spawner_positions[map_idx] = find_spawners(map_idx)
    window.teleporter_positions[map_idx] = find_teleporters(map_idx)
    
    window.tile_images.clear()
    window.palette_canvas.delete('all')
    render_tile_palette(window)
    render_map_view(window)
    update_map_config_display(window)
    update_map_counters(window)

def select_map_and_difficulty(map_idx, diff, window):
    """Handle map and difficulty selection"""
    window.selected_map = map_idx
    window.difficulty = diff
    
    update_selection_highlight(window)
    
    # Refresh everything
    window.door_positions[map_idx] = find_door(map_idx)
    window.spawner_positions[map_idx] = find_spawners(map_idx)
    window.teleporter_positions[map_idx] = find_teleporters(map_idx)
    
    window.tile_images.clear()
    window.palette_canvas.delete('all')
    render_tile_palette(window)
    render_map_view(window)
    update_map_config_display(window)
    update_map_counters(window)

def set_time_limit(window):
    """Set time limit for current map/difficulty"""
    try:
        new_limit = int(window.time_limit_var.get())
        if new_limit < 0 or new_limit > 255:
            messagebox.showwarning("Invalid Value", "Time limit must be 0-255 seconds")
            return
        
        window.map_config[window.difficulty][window.selected_map]['time_limit'] = new_limit
        mark_modified(window)
        window.status_var.set(f"Time limit set to {new_limit} seconds")
    except ValueError:
        messagebox.showwarning("Invalid Value", "Please enter a valid number")

def set_spawn_rate(window):
    """Set spawn rate for current map/difficulty"""
    try:
        new_rate = int(window.spawn_rate_var.get())
        if new_rate < 1 or new_rate > 14:
            messagebox.showwarning("Invalid Value", 
                "Spawn rate must be 1-14 (game uses 5-8, higher values may crash)")
            return
        
        window.map_config[window.difficulty][window.selected_map]['spawn_rate'] = new_rate
        mark_modified(window)
        window.status_var.set(f"Spawn rate set to {new_rate}")
    except ValueError:
        messagebox.showwarning("Invalid Value", "Please enter a valid number")

def mark_modified(window):
    """Mark the editor as having unsaved changes"""
    if not window.modified:
        window.modified = True
        current_title = window.winfo_toplevel().title()
        if not current_title.endswith("*"):
            window.winfo_toplevel().title(current_title + " *")

def zoom_in(window):
    """Zoom in on map"""
    if window.zoom_level < 8:
        window.zoom_level += 1
        window.zoom_label.config(text=f"{int(window.zoom_level)}x")
        render_map_view(window)
        window.palette_canvas.delete('all')
        render_tile_palette(window)

def zoom_out(window):
    """Zoom out on map"""
    if window.zoom_level > 1:
        window.zoom_level -= 1
        window.zoom_label.config(text=f"{int(window.zoom_level)}x")
        render_map_view(window)
        window.palette_canvas.delete('all')
        render_tile_palette(window)

def on_map_click(event, window):
    """Handle map canvas click"""
    try:
        canvas_x = window.map_canvas.canvasx(event.x)
        canvas_y = window.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * window.zoom_level))
        row = int(canvas_y // (16 * window.zoom_level))
        
        if not (0 <= row < map_height and 0 <= col < map_width):
            return
        
        visual_map = load_visual_map_from_cache(window.selected_map)
        
        # Check if clicking on door
        if is_door_tile(row, col, window):
            if window.difficulty > 0:
                messagebox.showwarning("Edit Locked", 
                    "Visual/logical map editing is only allowed in Difficulty 1.")
                return
            door_pos = window.door_positions[window.selected_map]
            window.selected_door = door_pos
            window.door_drag_start = (row, col)
            window.status_var.set("Door selected - drag to move")
            render_map_view(window)
            return
        
        # Check if clicking on player start marker
        if visual_map[row, col] == 0x29:
            if window.difficulty > 0:
                messagebox.showwarning("Edit Locked", 
                    "Visual/logical map editing is only allowed in Difficulty 1.")
                return
            window.selected_player_start = (row, col)
            window.status_var.set("Player start selected - drag to move")
            render_map_view(window)
            return
        
        # Check if clicking on spawner
        spawner = is_spawner_tile(row, col, window)
        if spawner:
            messagebox.showinfo("Spawner", 
                f"This is a {spawner['direction']} spawner. Right-click to delete.")
            return
        
        # Handle composite object placement
        if window.selected_composite:
            if window.selected_composite == 'teleporter':
                place_teleporter_step(row, col, window)
            elif window.selected_composite.startswith('spawner_'):
                place_spawner(row, col, window)
            return
        
        # Handle object marker placement
        if window.selected_object_type:
            place_object_marker(row, col, window)
            return
        
        # Handle tile placement
        if window.selected_tile is not None:
            place_tile(row, col, window)
        
    except Exception as e:
        logging.error(f"Error in map click: {e}")

def is_door_tile(row, col, window):
    """Check if a position is part of the door"""
    door_pos = window.door_positions.get(window.selected_map)
    if door_pos is None:
        return False
    
    door_row, door_col = door_pos
    return (door_row <= row < door_row + 3 and 
            door_col <= col < door_col + 3)

def is_spawner_tile(row, col, window):
    """Check if a tile position is part of a spawner"""
    spawners = window.spawner_positions.get(window.selected_map, [])
    for spawner in spawners:
        if (spawner['row'] <= row < spawner['row'] + spawner['height'] and 
            spawner['col'] <= col < spawner['col'] + spawner['width']):
            return spawner
    return None

def clear_door(row, col, window):
    """Clear door from position - writes directly to ROM cache"""
    for dr in range(3):
        for dc in range(3):
            # Clear visual tile
            write_visual_tile_to_cache(window.selected_map, row + dr, col + dc, empty_path_tile)
            
            # Clear logical bytes
            logical_row = col + dc
            logical_col = row + dr + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, [0x00, 0x00])

def place_door_at(row, col, window):
    """Place door at position - writes directly to ROM cache"""
    if row + 3 > map_height or col + 3 > map_width:
        return False
    
    for dr in range(3):
        for dc in range(3):
            # Write visual tile
            write_visual_tile_to_cache(window.selected_map, row + dr, col + dc, DOOR_TILES[dr, dc])
            
            # Write logical bytes
            logical_row = col + dc
            logical_col = row + dr + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, DOOR_LOGICAL[dr, dc])
    
    return True

def place_object_marker(row, col, window):
    """Place an object marker on the map"""
    try:
        # Convert to game coordinates
        row_from_bottom = (map_height - 1) - row
        x = row_from_bottom * 0x08
        y = col * 0x08
        
        objects = window.object_data[window.difficulty][window.selected_map]
        
        if window.selected_object_type == 'respawn':
            # Check if we have room
            if objects['respawn_count'] >= NUM_RESPAWNS:
                messagebox.showwarning("Limit Reached", 
                    f"Maximum {NUM_RESPAWNS} respawn points allowed")
                return
            
            # Add respawn
            for respawn in objects['respawns']:
                if respawn['y'] == 0:  # Empty slot
                    respawn['x'] = x
                    respawn['y'] = y
                    objects['respawn_count'] += 1
                    break
            
            mark_modified(window)
            window.status_var.set(f"Placed respawn at ({col}, {row})")
            render_map_view(window)
            update_map_counters(window)
        
        elif window.selected_object_type == 'player_start':
            # Can't place player start, only move it
            messagebox.showinfo("Player Start", 
                "Player start cannot be placed - it already exists.\n"
                "Click on the existing player start marker to drag it to a new location.")
        
    except Exception as e:
        logging.error(f"Error placing object marker: {e}")

def place_tile(row, col, window):
    """Place a tile on the map - writes directly to ROM cache"""
    try:
        # Check if this is a door tile
        if is_door_tile(row, col, window):
            messagebox.showwarning("Protected", 
                "This tile is part of the door. Use drag-and-drop to move the door.")
            return
        
        # Write visual tile directly to cache
        write_visual_tile_to_cache(window.selected_map, row, col, window.selected_tile)
        
        # Write logical bytes directly to cache
        logical_row = col
        logical_col = row + 1
        
        if window.selected_tile == empty_path_tile:
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, [0x00, 0x00])
        else:
            # Check existing logical bytes
            logical_map = load_logical_map_from_cache(window.selected_map)
            existing_pair = logical_map[logical_row, logical_col]
            if np.array_equal(existing_pair, [0x00, 0x00]) or np.array_equal(existing_pair, [0x55, 0x55]):
                write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, [0x55, 0x55])
        
        mark_modified(window)
        render_map_view(window)
        window.status_var.set(f"Placed tile 0x{window.selected_tile:02X} at ({col}, {row})")
        
    except Exception as e:
        logging.error(f"Error placing tile: {e}")

def place_spawner(row, col, window):
    """Place a spawner on the map - writes directly to ROM cache"""
    if window.difficulty > 0:
        messagebox.showwarning("Edit Locked", 
            "Visual/logical map editing is only allowed in Difficulty 1.")
        return
    
    direction = window.selected_spawner_dir
    config = SPAWNER_CONFIGS[direction]
    
    h, w = config['tiles'].shape
    if row + h > map_height or col + w > map_width:
        messagebox.showwarning("Invalid Placement", "Spawner doesn't fit")
        return
    
    # Check for overlaps with other composites
    for dr in range(h):
        for dc in range(w):
            check_row = row + dr
            check_col = col + dc
            
            if is_door_tile(check_row, check_col, window):
                messagebox.showwarning("Invalid Placement", "Would overlap with door")
                return
            
            teleporter_cols = window.teleporter_positions.get(window.selected_map, [])
            if check_col in teleporter_cols:
                messagebox.showwarning("Invalid Placement", "Would overlap with teleporter")
                return
    
    # Place spawner tiles
    for r in range(h):
        for c in range(w):
            tile_id = config['tiles'][r, c]
            write_visual_tile_to_cache(window.selected_map, row + r, col + c, tile_id)
            
            # Place logical bytes
            logical_row = col + c
            logical_col = row + r + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, config['logical'][r, c])
    
    # Add to object data
    x_coord = row * 0x08
    y_coord = col * 0x08
    
    objects = window.object_data[window.difficulty][window.selected_map]
    for spawn in objects['spawns']:
        if spawn['y'] == 0:
            spawn['y'] = y_coord
            spawn['x'] = x_coord
            
            # Write to ROM cache immediately
            save_object_data(objects, window.selected_map, window.difficulty)
            
            mark_modified(window)
            render_map_view(window)
            update_map_counters(window)
            window.status_var.set(f"Placed {direction} spawner at ({col}, {row})")
            
            # Update spawner positions cache
            window.spawner_positions[window.selected_map] = find_spawners(window.selected_map)
            return
    
    messagebox.showwarning("No Slots", "No empty spawner slots (max 7)")

def delete_spawner(row, col, window):
    """Delete a spawner at the given position"""
    if window.difficulty > 0:
        messagebox.showwarning("Edit Locked", 
            "Visual/logical map editing is only allowed in Difficulty 1.")
        return
    
    # Find which spawner this tile belongs to
    spawner = None
    for s in window.spawner_positions.get(window.selected_map, []):
        if (s['row'] <= row < s['row'] + s['height'] and 
            s['col'] <= col < s['col'] + s['width']):
            spawner = s
            break
    
    if not spawner:
        return
    
    # Clear the spawner tiles
    for dr in range(spawner['height']):
        for dc in range(spawner['width']):
            write_visual_tile_to_cache(window.selected_map, 
                                       spawner['row'] + dr, 
                                       spawner['col'] + dc, 
                                       empty_path_tile)
            
            logical_row = spawner['col'] + dc
            logical_col = spawner['row'] + dr + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, [0x00, 0x00])
    
    # Remove from object data
    x = spawner['row'] * 0x08
    y = spawner['col'] * 0x08
    objects = window.object_data[window.difficulty][window.selected_map]
    for spawn in objects['spawns']:
        if spawn['x'] == x and spawn['y'] == y:
            spawn['x'] = 0
            spawn['y'] = 0
            
            # Write to ROM cache immediately
            save_object_data(objects, window.selected_map, window.difficulty)
            break
    
    mark_modified(window)
    render_map_view(window)
    update_map_counters(window)
    window.status_var.set(f"Deleted {spawner['direction']} spawner")
    
    # Update spawner positions cache
    window.spawner_positions[window.selected_map] = find_spawners(window.selected_map)

def place_teleporter_step(row, col, window):
    """Two-phase teleporter placement - writes directly to ROM cache"""
    if window.difficulty > 0:
        messagebox.showwarning("Edit Locked", 
            "Visual/logical map editing is only allowed in Difficulty 1.")
        return
    
    if window.teleporter_first_pos is None:
        # First click - place first horizontal pillar
        if col - 1 < 0 or col + 1 >= map_width:
            messagebox.showwarning("Invalid Placement", 
                "Teleporter must have space for 3 columns (center ±1)")
            return
        
        # Check if these columns already have a teleporter
        left_col = col - 1
        right_col = col + 1
        teleporter_cols = window.teleporter_positions.get(window.selected_map, [])
        for check_col in [left_col, col, right_col]:
            if check_col in teleporter_cols:
                messagebox.showwarning("Invalid Placement", 
                    f"Column {check_col} already has a teleporter")
                return
        
        # Place first horizontal pillar across 3 columns at this row
        pillar_pattern = [100, 38, 101]
        pillar_logical = [[0x55, 0x55], [0x00, 0x00], [0x55, 0x55]]
        
        for dc, tile_col in enumerate([left_col, col, right_col]):
            write_visual_tile_to_cache(window.selected_map, row, tile_col, pillar_pattern[dc])
            
            logical_row = tile_col
            logical_col = row + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, pillar_logical[dc])
        
        window.teleporter_first_pos = (row, col)  # Store row and center column
        mark_modified(window)
        render_map_view(window)
        window.status_var.set(
            f"First pillar at row {row}, columns {left_col}-{right_col}. "
            f"Place second in SAME COLUMNS, different row (ESC to cancel)")
    
    else:
        # Second click - must be same center column, different row
        first_row, first_col = window.teleporter_first_pos
        
        if col != first_col:
            messagebox.showwarning("Invalid Placement", 
                f"Second pillar must be at column {first_col} (same center column as first)")
            return
        
        if row == first_row:
            messagebox.showwarning("Invalid Placement", 
                "Second pillar must be at a different row")
            return
        
        if col - 1 < 0 or col + 1 >= map_width:
            messagebox.showwarning("Invalid Placement", "Teleporter doesn't fit")
            return
        
        # Place second horizontal pillar
        left_col = col - 1
        right_col = col + 1
        pillar_pattern = [100, 38, 101]
        pillar_logical = [[0x55, 0x55], [0x00, 0x00], [0x55, 0x55]]
        
        for dc, tile_col in enumerate([left_col, col, right_col]):
            write_visual_tile_to_cache(window.selected_map, row, tile_col, pillar_pattern[dc])
            
            logical_row = tile_col
            logical_col = row + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, pillar_logical[dc])
        
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
        objects = window.object_data[window.difficulty][window.selected_map]
        for tp in objects['teleports']:
            if tp['y'] == 0:
                tp['y'] = y_coord
                tp['bottom_row'] = bottom_row_coord
                tp['top_row'] = top_row_coord
                
                # Write to ROM cache immediately
                save_object_data(objects, window.selected_map, window.difficulty)
                
                # Update teleporter positions cache
                if window.selected_map not in window.teleporter_positions:
                    window.teleporter_positions[window.selected_map] = []
                if col not in window.teleporter_positions[window.selected_map]:
                    window.teleporter_positions[window.selected_map].append(col)
                
                mark_modified(window)
                render_map_view(window)
                update_map_counters(window)
                window.status_var.set(
                    f"Placed teleporter pair at column {col}, rows {first_row} and {row}")
                window.teleporter_first_pos = None
                return
        
        messagebox.showwarning("No Slots", "No empty teleporter slots (max 6)")
        window.teleporter_first_pos = None

def delete_teleporter(col, window):
    """Delete a teleporter pair in the given column"""
    if window.difficulty > 0:
        messagebox.showwarning("Edit Locked", 
            "Visual/logical map editing is only allowed in Difficulty 1.")
        return
    
    teleporter_cols = window.teleporter_positions.get(window.selected_map, [])
    if col not in teleporter_cols:
        return
    
    # Clear all teleporter tiles in this column and adjacent columns
    left_col = col - 1
    right_col = col + 1
    
    if left_col < 0 or right_col >= map_width:
        return
    
    for row in range(map_height):
        for check_col in [left_col, col, right_col]:
            tile_id = load_visual_map_from_cache(window.selected_map)[row, check_col]
            if tile_id in [100, 38, 101]:  # Teleporter tiles
                write_visual_tile_to_cache(window.selected_map, row, check_col, empty_path_tile)
                
                logical_row = check_col
                logical_col = row + 1
                write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, [0x00, 0x00])
    
    # Remove from object data
    y_coord = col * 0x08
    objects = window.object_data[window.difficulty][window.selected_map]
    for tp in objects['teleports']:
        if tp['y'] == y_coord:
            tp['y'] = 0
            tp['bottom_row'] = 0
            tp['top_row'] = 0
            
            # Write to ROM cache immediately
            save_object_data(objects, window.selected_map, window.difficulty)
            break
    
    # Remove from teleporter positions cache
    window.teleporter_positions[window.selected_map].remove(col)
    
    mark_modified(window)
    render_map_view(window)
    update_map_counters(window)
    window.status_var.set(f"Deleted teleporter pair in column {col}")

def on_map_hover(event, window):
    """Handle map canvas hover"""
    try:
        canvas_x = window.map_canvas.canvasx(event.x)
        canvas_y = window.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * window.zoom_level))
        row = int(canvas_y // (16 * window.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            x_coord = row * 0x08
            y_coord = col * 0x08
            window.coord_var.set(f"XX=0x{x_coord:02X}  YYYY=0x{y_coord:04X}  (R{row}, C{col})")
        else:
            window.coord_var.set("")
    except Exception as e:
        logging.error(f"Error in hover: {e}")

def on_map_drag(event, window):
    """Handle map canvas drag"""
    try:
        if window.selected_door is None:
            return
        
        canvas_x = window.map_canvas.canvasx(event.x)
        canvas_y = window.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * window.zoom_level))
        row = int(canvas_y // (16 * window.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            window.door_ghost_pos = (row, col)
            render_map_view(window)
    except Exception as e:
        logging.error(f"Error in map drag: {e}")

def on_map_release(event, window):
    """Handle map canvas button release"""
    try:
        canvas_x = window.map_canvas.canvasx(event.x)
        canvas_y = window.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * window.zoom_level))
        row = int(canvas_y // (16 * window.zoom_level))
        
        # Handle door release
        if window.selected_door is not None:
            if 0 <= row < map_height and 0 <= col < map_width:
                if row + 3 <= map_height and col + 3 <= map_width:
                    # Clear old door position
                    clear_door(window.selected_door[0], window.selected_door[1], window)
                    
                    # Place at new position
                    if place_door_at(row, col, window):
                        window.door_positions[window.selected_map] = (row, col)
                        mark_modified(window)
                        window.status_var.set(f"Door moved to ({col}, {row})")
                    else:
                        # Failed - restore old position
                        place_door_at(window.selected_door[0], window.selected_door[1], window)
                        window.status_var.set("Invalid door placement")
                else:
                    window.status_var.set("Door doesn't fit at that location")
            
            window.selected_door = None
            window.door_drag_start = None
            window.door_ghost_pos = None
            render_map_view(window)
            return
            
    except Exception as e:
        logging.error(f"Error in map release: {e}")

def on_map_right_click(event, window):
    """Handle map canvas right click"""
    try:
        canvas_x = window.map_canvas.canvasx(event.x)
        canvas_y = window.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * window.zoom_level))
        row = int(canvas_y // (16 * window.zoom_level))
        
        if not (0 <= row < map_height and 0 <= col < map_width):
            return
        
        # Check if clicking on spawner
        spawner = is_spawner_tile(row, col, window)
        if spawner:
            delete_spawner(row, col, window)
            return
        
        # Check if clicking on teleporter column
        teleporter_cols = window.teleporter_positions.get(window.selected_map, [])
        if col in teleporter_cols:
            delete_teleporter(col, window)
            return
        
        # Convert to game coordinates (with proper flip)
        row_from_bottom = (map_height - 1) - row  # Flip row
        x = row_from_bottom * 0x08
        y = col * 0x08
        
        objects = window.object_data[window.difficulty][window.selected_map]
        
        # Check for items at this position
        for item in objects['items']:
            if item['active'] and item['x'] == x and item['y'] == y:
                item['active'] = False
                # Write to ROM cache immediately
                save_object_data(objects, window.selected_map, window.difficulty)
                mark_modified(window)
                window.status_var.set(f"Deleted item at ({col}, {row})")
                render_map_view(window)
                update_map_counters(window)
                return
        
        # Check for respawns
        for i, respawn in enumerate(objects['respawns']):
            if respawn['x'] == x and respawn['y'] == y:
                # Shift remaining respawns down
                for j in range(i, NUM_RESPAWNS - 1):
                    objects['respawns'][j] = objects['respawns'][j + 1].copy()
                objects['respawns'][-1] = {'x': 0, 'y': 0}
                objects['respawn_count'] = max(0, objects['respawn_count'] - 1)
                # Write to ROM cache immediately
                save_object_data(objects, window.selected_map, window.difficulty)
                mark_modified(window)
                window.status_var.set(f"Deleted respawn point at ({col}, {row})")
                render_map_view(window)
                update_map_counters(window)
                return
        
        # Check for spawners (object data)
        for spawn in objects['spawns']:
            if spawn['x'] == x and spawn['y'] == y:
                spawn['x'] = 0
                spawn['y'] = 0
                # Write to ROM cache immediately
                save_object_data(objects, window.selected_map, window.difficulty)
                mark_modified(window)
                window.status_var.set(f"Deleted spawner at ({col}, {row})")
                render_map_view(window)
                update_map_counters(window)
                return
        
        # Can't delete player start
        if objects['player_start']['x'] == x and objects['player_start']['y'] == y:
            messagebox.showwarning("Cannot Delete", "Cannot delete player start position")
            return
            
    except Exception as e:
        logging.error(f"Error in right click: {e}")

def on_escape_key(event, window):
    """Handle escape key"""
    # Cancel teleporter placement
    if window.teleporter_first_pos is not None:
        # Restore the original tiles where we placed the first pillar
        first_row, first_col = window.teleporter_first_pos
        
        left_col = first_col - 1
        right_col = first_col + 1
        
        # Clear the pillar tiles back to empty path
        for tile_col in [left_col, first_col, right_col]:
            write_visual_tile_to_cache(window.selected_map, first_row, tile_col, empty_path_tile)
            
            logical_row = tile_col
            logical_col = first_row + 1
            write_logical_tile_to_cache(window.selected_map, logical_row, logical_col, [0x00, 0x00])
        
        window.teleporter_first_pos = None
        render_map_view(window)
        window.status_var.set("Teleporter placement cancelled")
    
    # Cancel door drag
    elif window.selected_door is not None:
        window.selected_door = None
        window.door_drag_start = None
        window.door_ghost_pos = None
        render_map_view(window)
        window.status_var.set("Door movement cancelled")
    
    # Cancel player start drag
    elif window.selected_player_start is not None:
        window.selected_player_start = None
        window.player_start_ghost_pos = None
        render_map_view(window)
        window.status_var.set("Player start movement cancelled")

def on_composite_click(composite_id, window):
    """Handle clicking a composite object in the palette"""
    window.selected_tile = None
    window.selected_object_type = None
    window.selected_composite = composite_id
    
    if composite_id.startswith('spawner_'):
        window.selected_spawner_dir = composite_id.split('_')[1]
    
    update_tile_info(window)
    window.status_var.set(f"Selected {composite_id} - click map to place")

def render_map_view(window):
    """Render the map display - reads directly from ROM cache"""
    try:
        # Load map directly from cache
        visual_map = load_visual_map_from_cache(window.selected_map)
        
        map_image = np.zeros((visual_map.shape[0] * 16, visual_map.shape[1] * 16, 4), 
                            dtype=np.uint8)
        
        palette = palettes[window.selected_map]
        
        # Render each tile
        for row in range(visual_map.shape[0]):
            for col in range(visual_map.shape[1]):
                tile_index = visual_map[row, col]
                if tile_index < len(all_tiles):
                    tile = all_tiles[tile_index]
                    color_tile = apply_palette_to_tile(tile, palette)
                    map_image[row * 16 : (row + 1) * 16, col * 16 : (col + 1) * 16, :] = color_tile
        
        # Convert to RGB
        map_image_rgb = map_image[:, :, :3]
        
        # Apply zoom
        if window.zoom_level != 1:
            new_height = int(map_image_rgb.shape[0] * window.zoom_level)
            new_width = int(map_image_rgb.shape[1] * window.zoom_level)
            window.current_map_image = Image.fromarray(map_image_rgb.astype('uint8')).convert('RGB').resize(
                (new_width, new_height), Image.NEAREST)
        else:
            window.current_map_image = Image.fromarray(map_image_rgb.astype('uint8')).convert('RGB')
        
        map_image_tk = ImageTk.PhotoImage(window.current_map_image)
        
        # Clear and redraw
        window.map_canvas.delete('all')
        window.map_canvas.create_image(0, 0, image=map_image_tk, anchor='nw')
        window.map_canvas.image = map_image_tk
        
        # Draw object overlays if enabled
        if window.show_objects.get():
            draw_objects_overlay(window)
        
        # Draw grid if enabled
        if window.show_grid.get():
            for x in range(0, int(map_width * 16 * window.zoom_level), int(16 * window.zoom_level)):
                window.map_canvas.create_line(x, 0, x, int(map_height * 16 * window.zoom_level), 
                                             fill='#444444')
            for y in range(0, int(map_height * 16 * window.zoom_level), int(16 * window.zoom_level)):
                window.map_canvas.create_line(0, y, int(map_width * 16 * window.zoom_level), y, 
                                             fill='#444444')
        
        # Draw door highlight if selected
        if window.selected_door is not None:
            row, col = window.selected_door
            x = col * 16 * window.zoom_level
            y = row * 16 * window.zoom_level
            size = 3 * 16 * window.zoom_level
            window.map_canvas.create_rectangle(x-2, y-2, x+size+2, y+size+2,
                                             outline='cyan', width=3, tags='door_highlight')
        
        # Draw door ghost if dragging
        if window.door_ghost_pos is not None:
            row, col = window.door_ghost_pos
            if row + 3 <= map_height and col + 3 <= map_width:
                x = col * 16 * window.zoom_level
                y = row * 16 * window.zoom_level
                size = 3 * 16 * window.zoom_level
                window.map_canvas.create_rectangle(x, y, x+size, y+size,
                                                 outline='yellow', width=2, dash=(4, 4),
                                                 tags='door_ghost')
        
        # Update scroll region
        window.map_canvas.configure(scrollregion=(0, 0, 
                                                 int(map_width * 16 * window.zoom_level), 
                                                 int(map_height * 16 * window.zoom_level)))
        
    except Exception as e:
        logging.error(f"Error rendering map: {e}")

def draw_objects_overlay(window):
    """Draw object overlays on the map"""
    global palettes  # Access global palettes
    
    objects = window.object_data[window.difficulty][window.selected_map]
    
    # Clear existing overlay images
    window._overlay_images.clear()
    
    # Player start
    ps = objects['player_start']
    if ps['y'] != 0:
        col = ps['y'] // 0x08
        row_from_bottom = ps['x'] // 0x08
        row = (map_height - 1) - row_from_bottom
        x = col * 16 * window.zoom_level
        y = row * 16 * window.zoom_level
        size = 16 * window.zoom_level
        
        window.map_canvas.create_rectangle(x, y, x+size, y+size,
                                         outline='lime', width=3, tags='object_overlay')
    
    # Respawns
    for i in range(objects['respawn_count']):
        respawn = objects['respawns'][i]
        if respawn['y'] != 0:
            col = respawn['y'] // 0x08
            row_from_bottom = respawn['x'] // 0x08
            row = (map_height - 1) - row_from_bottom
            x = col * 16 * window.zoom_level
            y = row * 16 * window.zoom_level
            size = 16 * window.zoom_level
            
            window.map_canvas.create_oval(x, y, x+size, y+size,
                                         outline='yellow', width=2, tags='object_overlay')
    
    # Items
    for item in objects['items']:
        if item['active']:
            col = item['y'] // 0x08
            row_from_bottom = item['x'] // 0x08
            row = (map_height - 1) - row_from_bottom
            x = col * 16 * window.zoom_level
            y = row * 16 * window.zoom_level
            size = 16 * window.zoom_level
            
            window.map_canvas.create_rectangle(x, y, x+size, y+size,
                                             outline='green', width=3, tags='object_overlay')
            
            # Draw filled box overlay if applicable
            if item['tile_id'] in FILLED_TO_EMPTY:
                tile_idx = item['tile_id']
                if tile_idx < len(all_tiles):
                    tile = all_tiles[tile_idx]
                    palette = palettes[window.selected_map]
                    color_tile = apply_palette_to_tile(tile, palette)
                    
                    scale = int(window.zoom_level)
                    color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
                    tile_rgb = color_tile_large[:, :, :3]
                    
                    tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
                    tile_img.putalpha(180)
                    tile_photo = ImageTk.PhotoImage(tile_img)
                    
                    window._overlay_images.append(tile_photo)
                    
                    window.map_canvas.create_image(x, y, image=tile_photo, anchor='nw',
                                                  tags='object_overlay')
    
    # Teleporters
    for tp in objects['teleports']:
        if tp['y'] != 0:
            col = tp['y'] // 0x08
            row_from_bottom = tp['top_row'] // 0x08
            row_top = (map_height - 1) - row_from_bottom
            row_from_bottom = tp['bottom_row'] // 0x08
            row_bottom = (map_height - 1) - row_from_bottom
            
            x = col * 16 * window.zoom_level
            y_top = row_top * 16 * window.zoom_level
            y_bottom = row_bottom * 16 * window.zoom_level
            
            window.map_canvas.create_line(x + 8*window.zoom_level, y_top + 8*window.zoom_level,
                                         x + 8*window.zoom_level, y_bottom + 8*window.zoom_level,
                                         fill='magenta', width=2, dash=(4, 4), tags='object_overlay')
    
    # Spawners
    for spawn in objects['spawns']:
        if spawn['y'] != 0:
            col = spawn['y'] // 0x08
            row_from_bottom = spawn['x'] // 0x08
            row = (map_height - 1) - row_from_bottom
            
            x = col * 16 * window.zoom_level
            y = row * 16 * window.zoom_level
            size = 16 * window.zoom_level
            
            window.map_canvas.create_oval(x, y, x+size, y+size,
                                         outline='red', width=2, tags='object_overlay')

def render_tile_palette(window):
    """Render the tile palette"""
    try:
        tile_spacing = 5
        tile_display_size = int(16 * window.zoom_level)
        palette = palettes[window.selected_map]
        
        window.tile_images.clear()
        window.palette_canvas.delete('all')
        
        y_pos = tile_spacing
        
        # COMPOSITE OBJECTS section
        window.palette_canvas.create_text(tile_spacing, y_pos, text='COMPOSITE OBJECTS',
                                         anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        x_pos = tile_spacing
        max_y_in_row = y_pos
        
        # Teleporter (display as horizontal: 100-38-101)
        teleporter_display = np.array([[100, 38, 101]])
        comp_img = np.zeros((16, 48, 4), dtype=np.uint8)
        for c in range(3):
            tile_idx = teleporter_display[0, c]
            if tile_idx < len(all_tiles):
                tile = all_tiles[tile_idx]
                color_tile = apply_palette_to_tile(tile, palette)
                comp_img[:, c*16:(c+1)*16] = color_tile
        
        scale = int(window.zoom_level)
        comp_rgb = comp_img[:, :, :3]
        comp_rgb_scaled = np.repeat(np.repeat(comp_rgb, scale, axis=0), scale, axis=1)
        comp_pil = Image.fromarray(comp_rgb_scaled.astype('uint8')).convert('RGB')
        comp_photo = ImageTk.PhotoImage(comp_pil)
        
        window.tile_images.append(('teleporter', comp_photo))
        
        img_id = window.palette_canvas.create_image(x_pos, y_pos, image=comp_photo, anchor='nw')
        window.palette_canvas.tag_bind(img_id, '<Button-1>',
                                      lambda e: on_composite_click('teleporter', window))
        
        label_y = y_pos + 16 * scale + 2
        window.palette_canvas.create_text(x_pos + 24 * scale, label_y,
                                        text="Teleporter", anchor='n', fill='lightgray',
                                        font=('Arial', 7))
        
        max_y_in_row = max(max_y_in_row, label_y + 15)
        x_pos += 48 * scale + tile_spacing * 2
        
        # Spawners (all 4 directions)
        for direction in ['right', 'left', 'up', 'down']:
            config = SPAWNER_CONFIGS[direction]
            tiles = config['tiles']
            h, w = tiles.shape
            
            comp_img = np.zeros((h * 16, w * 16, 4), dtype=np.uint8)
            for r in range(h):
                for c in range(w):
                    tile_idx = tiles[r, c]
                    if tile_idx < len(all_tiles):
                        tile = all_tiles[tile_idx]
                        color_tile = apply_palette_to_tile(tile, palette)
                        comp_img[r*16:(r+1)*16, c*16:(c+1)*16] = color_tile
            
            comp_rgb = comp_img[:, :, :3]
            comp_rgb_scaled = np.repeat(np.repeat(comp_rgb, scale, axis=0), scale, axis=1)
            comp_pil = Image.fromarray(comp_rgb_scaled.astype('uint8')).convert('RGB')
            comp_photo = ImageTk.PhotoImage(comp_pil)
            
            window.tile_images.append((f'spawner_{direction}', comp_photo))
            
            img_id = window.palette_canvas.create_image(x_pos, y_pos, image=comp_photo, anchor='nw')
            window.palette_canvas.tag_bind(img_id, '<Button-1>',
                                          lambda e, d=direction: on_composite_click(f'spawner_{d}', window))
            
            label_y = y_pos + h * 16 * scale + 2
            window.palette_canvas.create_text(x_pos + w * 8 * scale, label_y,
                                            text=f"Spawner\n{direction.title()}", anchor='n', 
                                            fill='lightgray', font=('Arial', 7))
            
            max_y_in_row = max(max_y_in_row, label_y + 25)
            x_pos += w * 16 * scale + tile_spacing * 2
        
        y_pos = max_y_in_row + 10
        
        # TREASURES section
        window.palette_canvas.create_text(tile_spacing, y_pos, text='TREASURES',
                                         anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        x_pos = tile_spacing
        max_y_in_row = y_pos
        
        # Show empty and filled pairs + keyhole
        treasure_pairs = [(0x21, 0x6F), (0x22, 0x70), (0x4A, 0x62)]
        for empty_id, filled_id in treasure_pairs:
            # Empty box
            tile = all_tiles[empty_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(window.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            
            window.tile_images.append((empty_id, tile_photo))
            
            img_id = window.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            window.palette_canvas.tag_bind(img_id, '<Button-1>',
                                          lambda e, tid=empty_id: on_tile_click(tid, window))
            
            label_y = y_pos + tile_display_size + 2
            window.palette_canvas.create_text(x_pos + tile_display_size//2, label_y,
                                            text=f"0x{empty_id:02X}", anchor='n', fill='lightgray',
                                            font=('Arial', 7))
            
            x_pos += tile_display_size + tile_spacing
            
            # Filled box
            tile = all_tiles[filled_id]
            color_tile = apply_palette_to_tile(tile, palette)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            
            window.tile_images.append((filled_id, tile_photo))
            
            img_id = window.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            window.palette_canvas.tag_bind(img_id, '<Button-1>',
                                          lambda e, tid=filled_id: on_tile_click(tid, window))
            
            window.palette_canvas.create_text(x_pos + tile_display_size//2, label_y,
                                            text=f"0x{filled_id:02X}", anchor='n', fill='lightgray',
                                            font=('Arial', 7))
            
            max_y_in_row = max(max_y_in_row, label_y + 15)
            x_pos += tile_display_size + tile_spacing * 2
        
        # Add keyhole
        tile = all_tiles[0x72]
        color_tile = apply_palette_to_tile(tile, palette)
        scale = int(window.zoom_level)
        color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
        tile_rgb = color_tile_large[:, :, :3]
        tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
        tile_photo = ImageTk.PhotoImage(tile_img)
        
        window.tile_images.append((0x72, tile_photo))
        
        img_id = window.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
        window.palette_canvas.tag_bind(img_id, '<Button-1>',
                                      lambda e: on_tile_click(0x72, window))
        
        label_y = y_pos + tile_display_size + 2
        window.palette_canvas.create_text(x_pos + tile_display_size//2, label_y,
                                        text="0x72", anchor='n', fill='lightgray',
                                        font=('Arial', 7))
        
        max_y_in_row = max(max_y_in_row, label_y + 15)
        
        y_pos = max_y_in_row + 10
        
        # OBJECTS section
        window.palette_canvas.create_text(tile_spacing, y_pos, text='OBJECTS',
                                         anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        x_pos = tile_spacing
        max_y_in_row = y_pos
        
        # Object markers
        object_markers = [
            (0x29, 'player_start', 'Player Start'),
            (0x17, 'respawn', 'Respawn Point')
        ]
        
        for tile_id, obj_type, label_text in object_markers:
            tile = all_tiles[tile_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(window.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            
            window.tile_images.append((tile_id, tile_photo))
            
            img_id = window.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            window.palette_canvas.tag_bind(img_id, '<Button-1>',
                                          lambda e, otype=obj_type: on_object_marker_click(otype, window))
            
            label_y = y_pos + tile_display_size + 2
            window.palette_canvas.create_text(x_pos + tile_display_size//2, label_y,
                                            text=label_text, anchor='n', fill='lightgray',
                                            font=('Arial', 7))
            
            max_y_in_row = max(max_y_in_row, label_y + 15)
            x_pos += tile_display_size + tile_spacing * 2
        
        window.palette_canvas.configure(scrollregion=window.palette_canvas.bbox("all"))
        
    except Exception as e:
        logging.error(f"Error rendering palette: {e}")

def on_object_marker_click(object_type, window):
    """Handle clicking an object marker in the palette"""
    window.selected_tile = None
    window.selected_object_type = object_type
    update_tile_info(window)
    window.status_var.set(f"Selected {object_type} - click map to place")

def on_tile_click(tile_id, window):
    """Handle tile palette click"""
    window.selected_tile = tile_id
    window.selected_object_type = None
    update_tile_info(window)
    window.status_var.set(f"Selected tile 0x{tile_id:02X}")

def update_map_counters(window):
    """Update object counters"""
    try:
        objects = window.object_data[window.difficulty][window.selected_map]
        
        active_items = sum(1 for item in objects['items'] if item['active'])
        window.items_label.config(text=f"Items: {active_items}/14")
        
        active_teleports = sum(1 for tp in objects['teleports'] if tp['y'] != 0)
        window.teleports_label.config(text=f"Teleports: {active_teleports}/6")
        
        active_spawners = sum(1 for spawn in objects['spawns'] if spawn['y'] != 0)
        window.spawners_label.config(text=f"Spawners: {active_spawners}/7")
        
        window.respawns_label.config(text=f"Respawns: {objects['respawn_count']}/3")
        
        # Validate keys vs keyholes
        keys = sum(1 for item in objects['items'] if item['active'] and item['tile_id'] == 0x70)
        keyholes = sum(1 for item in objects['items'] if item['active'] and item['tile_id'] == 0x72)
        
        if keyholes > keys:
            window.validation_label.config(text=f"⚠ WARNING: {keyholes} keyholes but only {keys} keys!")
        else:
            window.validation_label.config(text="")
            
    except Exception as e:
        logging.error(f"Error updating counters: {e}")

def update_map_config_display(window):
    """Update map config display"""
    try:
        config = window.map_config[window.difficulty][window.selected_map]
        window.time_limit_var.set(str(config['time_limit']))
        window.spawn_rate_var.set(str(config['spawn_rate']))
    except Exception as e:
        logging.error(f"Error updating config display: {e}")

def update_tile_info(window):
    """Update selected tile info"""
    try:
        if window.selected_object_type:
            window.tile_info_var.set(f"Selected: {window.selected_object_type}")
            window.selected_tile_preview.config(image='')
        elif window.selected_tile is not None:
            window.tile_info_var.set(f"Selected: 0x{window.selected_tile:02X}")
            
            # Show tile preview
            if window.selected_tile < len(all_tiles):
                tile = all_tiles[window.selected_tile]
                palette = palettes[window.selected_map]
                color_tile = apply_palette_to_tile(tile, palette)
                
                # Scale 2x for visibility
                color_tile_large = np.repeat(np.repeat(color_tile, 2, axis=0), 2, axis=1)
                tile_rgb = color_tile_large[:, :, :3]
                tile_img = Image.fromarray(tile_rgb.astype('uint8')).convert('RGB')
                tile_photo = ImageTk.PhotoImage(tile_img)
                
                window.selected_tile_preview.config(image=tile_photo)
                window.selected_tile_preview.image = tile_photo
            else:
                window.selected_tile_preview.config(image='')
        else:
            window.tile_info_var.set("Selected: None")
            window.selected_tile_preview.config(image='')
    except Exception as e:
        logging.error(f"Error updating tile info: {e}")

#########################################
# UI Graphics Editor Functions
#########################################

def build_ui_graphics_window(window):
    """Build unified UI graphics editor"""
    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    ttk.Label(main_frame, text="Tutankham UI Graphics Editor", 
             font=('Arial', 16, 'bold')).pack(pady=10)
    
    # Instructions
    info_label = ttk.Label(main_frame, 
                          text="Select a UI graphic to view and edit",
                          font=('Arial', 9))
    info_label.pack(pady=5)
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Control frame
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill=tk.X, pady=5)
    
    # Graphic selector
    ttk.Label(control_frame, text="Graphic:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    graphic_types = list(UI_GRAPHICS_CONFIG.keys())
    
    window.selected_graphic = tk.StringVar(value=graphic_types[0])
    graphic_dropdown = ttk.Combobox(control_frame, 
                                   textvariable=window.selected_graphic,
                                   values=graphic_types,
                                   state="readonly", 
                                   width=25)
    graphic_dropdown.pack(side=tk.LEFT, padx=5)
    graphic_dropdown.bind("<<ComboboxSelected>>", 
                         lambda e: rebuild_ui_graphic_display(window))
    
    window._graphic_dropdown = graphic_dropdown
    
    # Palette selector
    ttk.Label(control_frame, text="Palette:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    window.selected_palette_idx = tk.IntVar(value=0)
    palette_dropdown = ttk.Combobox(control_frame, 
                                   values=PALETTE_NAMES,
                                   state="readonly", 
                                   width=15)
    palette_dropdown.current(0)
    palette_dropdown.pack(side=tk.LEFT, padx=5)
    palette_dropdown.bind("<<ComboboxSelected>>", 
                         lambda e: rebuild_ui_graphic_display(window))
    window._palette_dropdown = palette_dropdown
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Info frame (shows description)
    info_frame = ttk.Frame(main_frame)
    info_frame.pack(fill=tk.X, pady=5)
    window._info_label = ttk.Label(info_frame, text="", 
                                   font=('Arial', 9, 'italic'),
                                   foreground='gray')
    window._info_label.pack()
    
    # Display frame
    display_frame = ttk.Frame(main_frame)
    display_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    window._display_frame = display_frame
    window._display_image = None
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Button frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(button_frame, text="Close", 
              command=window.destroy).pack(side=tk.RIGHT, padx=5)
    
    # Status
    window.ui_status_frame = ttk.Frame(main_frame)
    window.ui_status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    window.ui_status_label = ttk.Label(window.ui_status_frame, 
                                       text="Select a graphic to view", 
                                       relief=tk.SUNKEN, anchor=tk.W)
    window.ui_status_label.pack(fill=tk.X, padx=5, pady=2)
    
    # Initial display
    rebuild_ui_graphic_display(window)

def rebuild_ui_graphic_display(window):
    """Rebuild display with selected graphic"""
    display_frame = window._display_frame
    
    # Clear existing
    for widget in display_frame.winfo_children():
        widget.destroy()
    
    # Get config
    graphic_name = window.selected_graphic.get()
    config = UI_GRAPHICS_CONFIG.get(graphic_name)
    if not config:
        ttk.Label(display_frame, text="Configuration missing for this graphic",
                 font=('Arial', 12, 'italic')).pack(pady=50)
        return
    
    # Update info label
    window._info_label.config(text=config.get('description', ''))
    
    # Get palette
    palette_idx = window._palette_dropdown.current()
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Extract pixels
    rom_data = rom_cache[config['rom']]
    pixels = extract_pixels(rom_data, config['offset'], 
                           height=config['height'], 
                           width=config['width'],
                           mode=config['mode'],
                           bytes_per_row=config.get('bytes_per_row'))
    
    # Rotate if needed
    if config.get('rotate'):
        pixels = np.rot90(pixels, k=1)
    
    # Apply palette
    color_sprite = apply_palette_to_tile(pixels, palette)
    
    # Scale
    zoom = config.get('zoom', 5)
    sprite_scaled = np.repeat(np.repeat(color_sprite, zoom, axis=0), zoom, axis=1)
    sprite_rgb = sprite_scaled[:, :, :3]
    
    # Convert to image
    img = Image.fromarray(sprite_rgb.astype('uint8')).convert('RGB')
    photo = ImageTk.PhotoImage(img)
    
    # Display
    canvas = tk.Canvas(display_frame, width=img.width, height=img.height, 
                      bg='#2b2b2b', cursor='hand2')
    canvas.pack(pady=10)
    canvas.create_image(0, 0, image=photo, anchor='nw')
    
    # Store reference
    window._display_image = photo
    
    # Add click handler for future editing
    canvas.bind('<Button-1>', lambda e: open_ui_graphic_editor(window, graphic_name))
    
    window.ui_status_label.config(text=f"Displaying: {graphic_name} - Click to edit (coming soon)")

def open_ui_graphic_editor(window, graphic_name):
    """Open pixel editor for a UI graphic"""
    # TODO: Implement pixel-level editor
    messagebox.showinfo("UI Graphics Editor", 
                       f"Pixel editor for {graphic_name} coming soon!\n\n"
                       f"This will allow you to edit individual pixels.")

#########################################
# Treasure Graphics Editor Functions
#########################################

def build_treasure_window(window):
    """Build treasure graphics editor (similar to UI graphics but for treasures)"""
    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    ttk.Label(main_frame, text="Tutankham Treasure Editor", 
             font=('Arial', 16, 'bold')).pack(pady=10)
    
    # Instructions
    info_label = ttk.Label(main_frame, 
                          text="Select an end-of-level treasure to view and edit",
                          font=('Arial', 9))
    info_label.pack(pady=5)
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Control frame
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill=tk.X, pady=5)
    
    # Treasure selector
    ttk.Label(control_frame, text="Treasure:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    treasure_types = list(TREASURE_GRAPHICS_CONFIG.keys())
    
    window.selected_treasure = tk.StringVar(value=treasure_types[0])
    treasure_dropdown = ttk.Combobox(control_frame, 
                                    textvariable=window.selected_treasure,
                                    values=treasure_types,
                                    state="readonly", 
                                    width=30)
    treasure_dropdown.pack(side=tk.LEFT, padx=5)
    treasure_dropdown.bind("<<ComboboxSelected>>", 
                          lambda e: rebuild_treasure_display(window))
    
    window._treasure_dropdown = treasure_dropdown
    
    # Palette selector
    ttk.Label(control_frame, text="Palette:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    window.selected_palette_idx = tk.IntVar(value=0)
    palette_dropdown = ttk.Combobox(control_frame, 
                                   values=PALETTE_NAMES,
                                   state="readonly", 
                                   width=15)
    palette_dropdown.current(0)
    palette_dropdown.pack(side=tk.LEFT, padx=5)
    palette_dropdown.bind("<<ComboboxSelected>>", 
                         lambda e: rebuild_treasure_display(window))
    window._palette_dropdown = palette_dropdown
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Info frame
    info_frame = ttk.Frame(main_frame)
    info_frame.pack(fill=tk.X, pady=5)
    window._info_label = ttk.Label(info_frame, text="", 
                                   font=('Arial', 9, 'italic'),
                                   foreground='gray')
    window._info_label.pack()
    
    # Display frame
    display_frame = ttk.Frame(main_frame)
    display_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    window._display_frame = display_frame
    window._display_image = None
    
    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Button frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(button_frame, text="Close", 
              command=window.destroy).pack(side=tk.RIGHT, padx=5)
    
    # Status
    window.treasure_status_frame = ttk.Frame(main_frame)
    window.treasure_status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    window.treasure_status_label = ttk.Label(window.treasure_status_frame, 
                                             text="Select a treasure to view", 
                                             relief=tk.SUNKEN, anchor=tk.W)
    window.treasure_status_label.pack(fill=tk.X, padx=5, pady=2)
    
    # Initial display
    rebuild_treasure_display(window)

def rebuild_treasure_display(window):
    """Rebuild display with selected treasure"""
    display_frame = window._display_frame
    
    # Clear existing
    for widget in display_frame.winfo_children():
        widget.destroy()
    
    # Get config
    treasure_name = window.selected_treasure.get()
    config = TREASURE_GRAPHICS_CONFIG.get(treasure_name)
    if not config:
        ttk.Label(display_frame, text="Configuration missing for this treasure",
                 font=('Arial', 12, 'italic')).pack(pady=50)
        return
    
    # Update info label
    window._info_label.config(text=config.get('description', ''))
    
    # Get palette
    palette_idx = window._palette_dropdown.current()
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Extract pixels
    rom_data = rom_cache[config['rom']]
    pixels = extract_pixels(rom_data, config['offset'], 
                           height=config['height'], 
                           width=config['width'],
                           mode=config['mode'],
                           bytes_per_row=config.get('bytes_per_row'))
    
    # Rotate if needed
    if config.get('rotate'):
        pixels = np.rot90(pixels, k=1)
    
    # Apply palette
    color_sprite = apply_palette_to_tile(pixels, palette)
    
    # Scale
    zoom = config.get('zoom', 5)
    sprite_scaled = np.repeat(np.repeat(color_sprite, zoom, axis=0), zoom, axis=1)
    sprite_rgb = sprite_scaled[:, :, :3]
    
    # Convert to image
    img = Image.fromarray(sprite_rgb.astype('uint8')).convert('RGB')
    photo = ImageTk.PhotoImage(img)
    
    # Display
    canvas = tk.Canvas(display_frame, width=img.width, height=img.height, 
                      bg='#2b2b2b', cursor='hand2')
    canvas.pack(pady=10)
    canvas.create_image(0, 0, image=photo, anchor='nw')
    
    # Store reference
    window._display_image = photo
    
    # Add click handler for future editing
    canvas.bind('<Button-1>', lambda e: open_treasure_editor(window, treasure_name))
    
    window.treasure_status_label.config(text=f"Displaying: {treasure_name} - Click to edit (coming soon)")

def open_treasure_editor(window, treasure_name):
    """Open pixel editor for a treasure graphic"""
    # TODO: Implement pixel-level editor
    messagebox.showinfo("Treasure Editor", 
                       f"Pixel editor for {treasure_name} coming soon!\n\n"
                       f"This will allow you to edit individual pixels.")


#########################################
# Font Editor Functions
#########################################

def build_font_editor_window(window):
    """Build the font editor interface"""
    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = ttk.Label(main_frame, text="Tutankham Font Editor", 
                            font=('Arial', 16, 'bold'))
    title_label.pack(pady=10)
    
    # Control frame
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill=tk.X, pady=5)
    
    # Palette selector
    ttk.Label(control_frame, text="Palette:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    window.selected_palette_idx = tk.IntVar(value=0)
    palette_dropdown = ttk.Combobox(control_frame, 
                                   values=PALETTE_NAMES,
                                   state="readonly", 
                                   width=20)
    palette_dropdown.current(0)
    palette_dropdown.pack(side=tk.LEFT, padx=5)
    palette_dropdown.bind("<<ComboboxSelected>>", 
                         lambda e: rebuild_font_grid(window))
    
    window._palette_dropdown = palette_dropdown

    ttk.Button(control_frame, text="Close", 
              command=window.destroy).pack(side=tk.RIGHT, padx=5)

    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    
    # Font grid frame
    font_frame = ttk.Frame(main_frame)
    font_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    # Store references
    window._font_frame = font_frame
    window._font_images = []
   
    # Status frame
    window.font_status_frame = ttk.Frame(main_frame)
    window.font_status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    window.font_status_label = ttk.Label(window.font_status_frame, 
                                        text="Ready - Click Any Character To Edit", 
                                        relief=tk.SUNKEN, anchor=tk.W)
    window.font_status_label.pack(fill=tk.X, padx=5, pady=2)
    
    # Build initial font grid
    rebuild_font_grid(window)

def rebuild_font_grid(window):
    """Rebuild the font grid with current palette"""
    font_frame = window._font_frame
    window._font_images.clear()
    
    # Clear existing widgets
    for widget in font_frame.winfo_children():
        widget.destroy()
    
    # Get current palette
    palette_idx = window._palette_dropdown.current()
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Grid configuration
    fonts_per_row = 15
    font_spacing = 10
    font_scale = 10  # Display at 10x (80x80 pixels) - fonts are 8x8
    
    # Configure grid to expand
    for i in range(fonts_per_row):
        font_frame.grid_columnconfigure(i, weight=1)
    
    # Create grid of all 43 font characters
    for font_idx in range(len(all_fonts)):
        row = font_idx // fonts_per_row
        col = font_idx % fonts_per_row
        
        # Create frame for this font
        font_container = ttk.Frame(font_frame, relief=tk.RAISED, borderwidth=1)
        font_container.grid(row=row, column=col, padx=font_spacing, pady=font_spacing, sticky='nsew')
        
        # Character name label above
        char_label = ttk.Label(font_container, text=get_font_name(font_idx), 
                             font=('Arial', 24, 'bold'), foreground='#000000')
        char_label.pack(pady=(5, 2))
        
        # Font image
        font = all_fonts[font_idx]

        preview_tile = font.copy()

        # Due to the colors for EVERY Palette for 0 and 15 being black, we need to remap to make visible:
        # leave background black, remap foreground (15) → 3 (grey)
        preview_tile[preview_tile == 0] = 0
        preview_tile[preview_tile == 15] = 3

        color_font = apply_palette_to_tile(preview_tile, palette)

        # Scale up
        font_scaled = np.repeat(np.repeat(color_font, font_scale, axis=0), font_scale, axis=1)
        font_rgb = font_scaled[:, :, :3]
        font_img = Image.fromarray(font_rgb.astype('uint8')).convert('RGB')
        font_photo = ImageTk.PhotoImage(font_img)
        
        # Store reference
        window._font_images.append(font_photo)
        
        # Clickable label with border for visibility
        font_label = tk.Label(font_container, image=font_photo,
                             bg='#2b2b2b', cursor='hand2',
                             relief=tk.SUNKEN, borderwidth=2)
        font_label.pack(pady=2)
        font_label.bind('<Button-1>', 
                       lambda e, fid=font_idx: open_font_editor(window, fid))
    
    # Log to confirm it's working
    logging.info(f"Rebuilt font grid with {len(all_fonts)} characters using palette {palette_idx}")

def open_font_editor(window, font_idx):
    """Open font editor dialog for a specific character"""
    # Get current palette
    palette_idx = window._palette_dropdown.current()
    palettes = load_palettes_from_rom()
    palette = palettes[palette_idx]
    
    # Create dialog
    dialog = tk.Toplevel(window)
    dialog.title(f"Edit Font Character: {get_font_name(font_idx)}")
    dialog.geometry("400x500")
    dialog.transient(window)
    dialog.update_idletasks()
    dialog.grab_set()
    
    main_frame = ttk.Frame(dialog, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    ttk.Label(main_frame, 
             text=f"Character: {get_font_name(font_idx)}",
             font=('Arial', 12, 'bold')).pack(pady=10)
    
    # TODO: Add 8x8 pixel editor canvas here (64x64 pixels, 8x zoom)
    # TODO: Add color palette selector
    # TODO: Add save/cancel buttons
    
    ttk.Label(main_frame, text="Font editor coming next...", 
             font=('Arial', 10, 'italic')).pack(pady=50)
    
    ttk.Button(main_frame, text="Close", 
              command=dialog.destroy).pack(pady=10)

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
    
    window.selected_palette_idx = tk.IntVar(value=0)
    palette_dropdown = ttk.Combobox(control_frame, 
                                   values=PALETTE_NAMES,
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
    
    # Build each palette row
    for pal_idx, pal_name in enumerate(PALETTE_NAMES):
        build_palette_row(window, content_frame, palettes, pal_idx, pal_name)
        
        # Add separator between palettes
        if pal_idx < len(PALETTE_NAMES) - 1:
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
    
    ttk.Label(main_frame, 
             text=f"{PALETTE_NAMES[palette_idx]} - Color {color_idx}",
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
        
        window.pal_status_label.config(text=f"Updated {PALETTE_NAMES[palette_idx]} color {color_idx}")

        # NOTIFY OTHER WINDOWS
        trigger_callback('palette_changed', palette_idx)

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

root.config(menu=menubar)				            # Attach to window
all_tiles = all_fonts = None                        # Initialize Global Variables
visual_maps = logical_maps = None		            # Initialize Global Variables
palettes = high_scores = None			            # Initialize Global Variables
load_all("Zip")						                # Load initial data from zip
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