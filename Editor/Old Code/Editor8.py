import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import shutil
from datetime import datetime

# Define ROM files and offsets
tile_roms = ["./c1.1i", "./c2.2i", "./c3.3i", "./c4.4i", "./c5.5i"]
visual_map_rom_path = "./c8.8i"
logical_map_rom_paths = ["./c6.6i", "./c7.7i"]
object_rom_paths = ["./m1.1h", "./m2.2h"]

# Constants
tile_size = 16 * 16 // 2
num_maps = 4
map_width = 64
map_height = 12
visual_map_size = 0x300
logical_map_size = 0x700
empty_path_tile = 0x26

# Tile filter - organized by category
WALL_TILES = [
    *range(0x00, 0x0F),  # 0-14 (excluding 0x0F spawner)
    0x11,  # 17
    0x13,  # 19
    *range(0x1F, 0x23),  # 31-34
    0x27, 0x28,  # 39-40
]

SPAWN_TILES = [
    0x29,  # 41 - player start
    0x17,  # 23 - respawn flame
]

TREASURE_TILES = [
    0x21, 0x6F,  # 33, 111 - Ring box (empty, filled)
    0x22, 0x70,  # 34, 112 - Key box (empty, filled)
    0x4A, 0x62,  # 74, 98 - Treasure box (empty, filled)
]

# Path tile (critical!)
PATH_TILES = [0x26]

# Object data constants - CORRECTED OFFSET!
OBJECT_BASE_OFFSET = 0x0629  # Was 0x0636 - this was wrong!
OBJECT_BLOCK_SIZE = 0x0148
NUM_DIFFICULTIES = 4  # Changed from 3!
NUM_ITEMS = 14
NUM_TELEPORTS = 6
NUM_SPAWNS = 7
NUM_RESPAWNS = 3

# Composite block definitions
DOOR_TILES = np.array([[115, 116, 117], [118, 119, 120], [121, 122, 123]])
DOOR_LOGICAL = np.array([[[0x00,0x00], [0x00,0x06], [0x00,0x00]],
                         [[0x55,0x06], [0xF6,0x6E], [0xF6,0x06]],
                         [[0x00,0x00], [0xF0,0x66], [0xF0,0x00]]])

TELEPORTER_TILES = np.array([[100], [38], [101]])
TELEPORTER_LOGICAL = np.array([[[0x55,0x55]], [[0x00,0x00]], [[0x55,0x55]]])

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

# Palettes for each map
palettes = [
    [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 133, 133, 148), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 91, 162, 69)],
    [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 162, 000, 217), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 133, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 29, 195, 148)],
    [(255, 000, 000, 000), (255, 91, 62, 69), (255, 000, 224, 000), (255, 162, 133, 000), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 62, 195, 217), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 224, 29, 148)],
    [(255, 000, 000, 000), (255, 000, 000, 000), (255, 000, 224, 000), (255, 000, 000, 217), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 000, 000, 000)]
]

def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

def read_byte_from_roms(offset):
    """Read a single byte from the combined ROM space"""
    rom_index = offset // 0x1000
    rom_offset = offset % 0x1000
    
    if rom_index >= len(object_rom_paths):
        raise ValueError(f"Offset 0x{offset:04X} beyond available ROMs")
    
    rom_data = read_rom(object_rom_paths[rom_index])
    return rom_data[rom_offset]

def write_byte_to_roms(offset, value, rom_data_cache):
    """Write a single byte to the ROM cache"""
    rom_index = offset // 0x1000
    rom_offset = offset % 0x1000
    
    if rom_index not in rom_data_cache:
        rom_data_cache[rom_index] = read_rom(object_rom_paths[rom_index])
    
    rom_data_cache[rom_index][rom_offset] = value

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
    for rom in tile_roms:
        rom_data = read_rom(rom)
        num_tiles = len(rom_data) // tile_size
        for i in range(num_tiles):
            offset = i * tile_size
            tile = extract_tile(rom_data, offset)
            rotated_tile = rotate_tile(tile)
            all_tiles.append(rotated_tile)
    return all_tiles

def load_visual_maps():
    map_data = read_rom(visual_map_rom_path)
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

def load_logical_maps():
    logical_maps = []
    for rom_index, rom_path in enumerate(logical_map_rom_paths):
        rom_data = read_rom(rom_path)
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
        'y': (read_byte_from_roms(pos + 1) << 8) | read_byte_from_roms(pos),
        'x': read_byte_from_roms(pos + 2)
    }
    pos += 3
    
    # Read respawn points (3 × 3 bytes each)
    for i in range(NUM_RESPAWNS):
        respawn = {
            'y': (read_byte_from_roms(pos + 1) << 8) | read_byte_from_roms(pos),
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
            'y': (read_byte_from_roms(pos + 6) << 8) | read_byte_from_roms(pos + 5),
            'x': read_byte_from_roms(pos + 7),
            'tile_id': read_byte_from_roms(pos + 15)
        }
        objects['items'].append(item)
        pos += 16
    
    pos += 1  # Skip separator
    
    # Read teleports (6 × 8 bytes: 4 data + 4 padding)
    for i in range(NUM_TELEPORTS):
        teleport = {
            'y': (read_byte_from_roms(pos + 1) << 8) | read_byte_from_roms(pos),
            'bottom_row': read_byte_from_roms(pos + 2),
            'top_row': read_byte_from_roms(pos + 3)
        }
        objects['teleports'].append(teleport)
        pos += 8
    
    pos += 1  # Skip separator
    
    # Read spawns (7 × 4 bytes: 3 data + 1 padding)
    for i in range(NUM_SPAWNS):
        spawn = {
            'y': (read_byte_from_roms(pos + 1) << 8) | read_byte_from_roms(pos),
            'x': read_byte_from_roms(pos + 2)
        }
        objects['spawns'].append(spawn)
        pos += 4
    
    return objects

def save_visual_maps_to_rom(maps, output_path, preserve_extra=True):
    if preserve_extra and os.path.exists(output_path):
        original_data = read_rom(output_path)
    else:
        original_data = bytearray()
    
    map_data = bytearray()
    for map_index in range(len(maps)):
        map_layout = maps[map_index]
        for byte_index in range(visual_map_size):
            row = (byte_index % map_height)
            col = (byte_index // map_height)
            flipped_row = map_height - 1 - row
            map_data.append(map_layout[flipped_row, col])
    
    if preserve_extra and len(original_data) > len(map_data):
        map_data.extend(original_data[len(map_data):])
    
    with open(output_path, "wb") as f:
        f.write(map_data)

def save_logical_maps_to_rom(logical_maps, preserve_extra=True):
    for rom_index, rom_path in enumerate(logical_map_rom_paths):
        if preserve_extra and os.path.exists(rom_path):
            original_data = read_rom(rom_path)
        else:
            original_data = bytearray()
        
        rom_data = bytearray()
        for map_in_rom in range(2):
            map_index = rom_index * 2 + map_in_rom
            logical_map = logical_maps[map_index]
            for tile_row in range(64):
                for tile_col in range(14):
                    rom_data.append(logical_map[tile_row, tile_col, 0])
                for tile_col in range(14):
                    rom_data.append(logical_map[tile_row, tile_col, 1])
        
        if preserve_extra and len(original_data) > len(rom_data):
            rom_data.extend(original_data[len(rom_data):])
        
        with open(rom_path, "wb") as f:
            f.write(rom_data)

def save_object_data(objects, map_index, difficulty=0):
    """Save object data back to ROM - handles ROM boundaries"""
    block_number = (difficulty * 4) + map_index
    offset = OBJECT_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
    # Build cache of ROM data
    rom_data_cache = {}
    
    pos = offset
    
    # Write player start
    write_byte_to_roms(pos, objects['player_start']['y'] & 0xFF, rom_data_cache)
    write_byte_to_roms(pos + 1, (objects['player_start']['y'] >> 8) & 0xFF, rom_data_cache)
    write_byte_to_roms(pos + 2, objects['player_start']['x'], rom_data_cache)
    pos += 3
    
    # Write respawns
    for respawn in objects['respawns']:
        write_byte_to_roms(pos, respawn['y'] & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 1, (respawn['y'] >> 8) & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 2, respawn['x'], rom_data_cache)
        pos += 3
    
    # Write respawn count
    write_byte_to_roms(pos, objects['respawn_count'], rom_data_cache)
    pos += 1
    
    # Write items
    for item in objects['items']:
        write_byte_to_roms(pos, 0x01 if item['active'] else 0x00, rom_data_cache)
        for i in range(1, 5):
            write_byte_to_roms(pos + i, 0x00, rom_data_cache)
        write_byte_to_roms(pos + 5, item['y'] & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 6, (item['y'] >> 8) & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 7, item['x'], rom_data_cache)
        for i in range(8, 15):
            write_byte_to_roms(pos + i, 0x00, rom_data_cache)
        write_byte_to_roms(pos + 15, item['tile_id'], rom_data_cache)
        pos += 16
    
    write_byte_to_roms(pos, 0x00, rom_data_cache)
    pos += 1
    
    # Write teleports
    for teleport in objects['teleports']:
        write_byte_to_roms(pos, teleport['y'] & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 1, (teleport['y'] >> 8) & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 2, teleport['bottom_row'], rom_data_cache)
        write_byte_to_roms(pos + 3, teleport['top_row'], rom_data_cache)
        for i in range(4, 8):
            write_byte_to_roms(pos + i, 0x00, rom_data_cache)
        pos += 8
    
    write_byte_to_roms(pos, 0x00, rom_data_cache)
    pos += 1
    
    # Write spawns
    for spawn in objects['spawns']:
        write_byte_to_roms(pos, spawn['y'] & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 1, (spawn['y'] >> 8) & 0xFF, rom_data_cache)
        write_byte_to_roms(pos + 2, spawn['x'], rom_data_cache)
        write_byte_to_roms(pos + 3, 0x00, rom_data_cache)
        pos += 4
    
    # Write back all modified ROMs
    for rom_index, rom_data in rom_data_cache.items():
        with open(object_rom_paths[rom_index], "wb") as f:
            f.write(rom_data)

def backup_file(filepath):
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        return backup_path
    return None

class MapEditor:
    def __init__(self, visual_maps, logical_maps, all_tiles, palettes):
        self.visual_maps = visual_maps
        self.logical_maps = logical_maps
        self.all_tiles = all_tiles
        self.palettes = palettes
        self.selected_tile = 0
        self.selected_map = 0
        self.difficulty = 0
        self.tile_images = []
        self.zoom_level = 2.0
        self.modified = False
        
        # Composite object selection
        self.selected_composite = None
        self.selected_spawner_dir = 'right'
        
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
        
        # Find doors
        for i in range(num_maps):
            self.door_positions[i] = self.find_door(i)

        # Find spawners
        self.spawner_positions = {}
        for i in range(num_maps):
            self.spawner_positions[i] = self.find_spawners(i)
        
        # Find teleporters - ADD THIS
        self.teleporter_positions = {}
        for i in range(num_maps):
            self.teleporter_positions[i] = self.find_teleporters(i)

        # Validate and fix filled boxes on load
        self.validate_filled_boxes()
        
        self.root = tk.Tk()
        self.root.title("Tutankham Map Editor V6")
        self.root.geometry("1600x900")
        
        # Create tkinter variables
        self.show_hex = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=False)
        self.show_objects = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.coord_var = tk.StringVar(value="")
        
        self.setup_ui()
        self.render_tile_palette()
        self.display_map()
        self.update_counters()
        
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
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)
        
        ttk.Label(left_panel, text="Map Selection", font=('Arial', 10, 'bold')).pack(pady=5)
        for i in range(num_maps):
            btn = ttk.Button(left_panel, text=f"Map {i + 1}", 
                           command=lambda i=i: self.on_map_select(i))
            btn.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(left_panel, text="Difficulty", font=('Arial', 10, 'bold')).pack(pady=5)
        diff_frame = ttk.Frame(left_panel)
        diff_frame.pack(fill=tk.X, padx=5)
        for i in range(NUM_DIFFICULTIES):
            btn = ttk.Button(diff_frame, text=str(i+1), width=5,
                           command=lambda i=i: self.set_difficulty(i))
            btn.pack(side=tk.LEFT, padx=2)
        
        self.diff_lock_label = ttk.Label(left_panel, text="", foreground="red", 
                                        font=('Arial', 8))
        self.diff_lock_label.pack()
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(left_panel, text="Object Counts", font=('Arial', 10, 'bold')).pack(pady=5)
        self.counter_frame = ttk.Frame(left_panel)
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
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(left_panel, text="Display", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Checkbutton(left_panel, text="Show Grid", variable=self.show_grid, 
                       command=self.display_map).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(left_panel, text="Show Objects", variable=self.show_objects, 
                       command=self.display_map).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(left_panel, text="Hex Tile IDs", variable=self.show_hex, 
                       command=self.render_tile_palette).pack(anchor=tk.W, padx=5)
        
        zoom_frame = ttk.Frame(left_panel)
        zoom_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="-", width=3, command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text=f"{int(self.zoom_level)}x")
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="+", width=3, command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        
        # Right panel
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        map_frame = ttk.LabelFrame(right_panel, text="Map View")
        map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        canvas_frame = ttk.Frame(map_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.map_canvas = tk.Canvas(canvas_frame, bg='black')
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
        
        coord_frame = ttk.Frame(map_frame)
        coord_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(coord_frame, text="Coordinates:").pack(side=tk.LEFT)
        ttk.Label(coord_frame, textvariable=self.coord_var, font=('Courier', 9)).pack(side=tk.LEFT, padx=5)
        
        palette_frame = ttk.LabelFrame(right_panel, text="Tile Palette")
        palette_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=5, pady=5)
        
        self.tile_info_var = tk.StringVar(value="Selected: None")
        ttk.Label(palette_frame, textvariable=self.tile_info_var).pack(side=tk.TOP, pady=2)
        
        palette_canvas_frame = ttk.Frame(palette_frame)
        palette_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.palette_canvas = tk.Canvas(palette_canvas_frame, height=150, bg='#2b2b2b')
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
        
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Save All", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Export...", command=self.save_file_as).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)

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
        
        if self.difficulty > 0:
            self.diff_lock_label.config(text="Map editing locked (Diff 2-4)")
        else:
            self.diff_lock_label.config(text="")
    
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
        self.update_counters()
        self.status_var.set(f"Switched to Difficulty {diff + 1}")
    
    def on_escape(self, event):
        if self.teleporter_first_pos is not None:
            self.teleporter_first_pos = None
            self.display_map()
            self.status_var.set("Teleporter placement cancelled")
    
    def render_tile_palette(self):
        tile_spacing = 4
        tile_display_size = int(16 * self.zoom_level)
        palette = self.palettes[self.selected_map]
        
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        
        y_pos = tile_spacing
        
        # COMPOSITE OBJECTS
        self.palette_canvas.create_text(tile_spacing, y_pos, text="COMPOSITE OBJECTS", 
                                       anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        # Build teleporter display (side-by-side pillars)
        teleporter_display = np.array([[100, 100], [38, 38], [101, 101]])
        composite_objects = [
            ('door', DOOR_TILES),
            ('teleporter', teleporter_display),
            ('spawner_right', SPAWNER_CONFIGS['right']['tiles']),
            ('spawner_left', SPAWNER_CONFIGS['left']['tiles']),
            ('spawner_up', SPAWNER_CONFIGS['up']['tiles']),
            ('spawner_down', SPAWNER_CONFIGS['down']['tiles'])
        ]

        x_pos = tile_spacing
        max_height = 0  # Track tallest composite in this row

        for comp_id, comp_tiles in composite_objects:
            h, w = comp_tiles.shape  # h = rows, w = cols
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
            comp_pil = Image.fromarray(comp_rgb_scaled, 'RGB')
            comp_photo = ImageTk.PhotoImage(comp_pil)
            
            self.tile_images.append((comp_id, comp_photo))
            
            comp_width = w * 16 * scale
            comp_height = h * 16 * scale
    
            # Track the tallest composite
            max_height = max(max_height, comp_height)
            
            img_id = self.palette_canvas.create_image(x_pos, y_pos, image=comp_photo, anchor='nw')
            self.palette_canvas.tag_bind(img_id, '<Button-1>', 
                                        lambda e, cid=comp_id: self.on_composite_click(cid))
    
            label_y = y_pos + comp_height + 2
            self.palette_canvas.create_text(x_pos + comp_width//2, label_y,
                                          text=comp_id.replace('_', '\n'), 
                                          anchor='n', fill='lightgray', font=('Arial', 7))
    
            x_pos += comp_width + tile_spacing * 3

        # Advance y_pos by the tallest composite + label space
        y_pos += max_height + 30
        
        # WALLS
        self.palette_canvas.create_text(tile_spacing, y_pos, text="WALLS", 
                                       anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        x_pos = tile_spacing
        for tile_id in WALL_TILES + PATH_TILES:
            if tile_id >= len(self.all_tiles):
                continue
            tile = self.all_tiles[tile_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb, 'RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            self.tile_images.append((tile_id, tile_photo))
            
            tile_img_id = self.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            self.palette_canvas.tag_bind(tile_img_id, '<Button-1>', 
                                        lambda e, idx=tile_id: self.on_tile_click(idx))
            
            x_pos += tile_display_size + tile_spacing
            if x_pos > 800:
                x_pos = tile_spacing
                y_pos += tile_display_size + tile_spacing
        
        y_pos += tile_display_size + 20
        
        # SPAWN POINTS
        self.palette_canvas.create_text(tile_spacing, y_pos, text="SPAWN POINTS", 
                                       anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        x_pos = tile_spacing
        for tile_id in SPAWN_TILES:
            if tile_id >= len(self.all_tiles):
                continue
            tile = self.all_tiles[tile_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb, 'RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            self.tile_images.append((tile_id, tile_photo))
            
            tile_img_id = self.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            self.palette_canvas.tag_bind(tile_img_id, '<Button-1>', 
                                        lambda e, idx=tile_id: self.on_tile_click(idx))
            
            x_pos += tile_display_size + tile_spacing
        
        y_pos += tile_display_size + 20
        
        # TREASURES
        self.palette_canvas.create_text(tile_spacing, y_pos, text="TREASURES (Empty | Filled)", 
                                       anchor='nw', fill='white', font=('Arial', 9, 'bold'))
        y_pos += 20
        
        x_pos = tile_spacing
        treasure_pairs = [(0x21, 0x6F), (0x22, 0x70), (0x4A, 0x62)]
        
        for empty_id, filled_id in treasure_pairs:
            tile = self.all_tiles[empty_id]
            color_tile = apply_palette_to_tile(tile, palette)
            scale = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb, 'RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            self.tile_images.append((empty_id, tile_photo))
            
            tile_img_id = self.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            self.palette_canvas.tag_bind(tile_img_id, '<Button-1>', 
                                        lambda e, idx=empty_id: self.on_tile_click(idx))
            x_pos += tile_display_size + tile_spacing
            
            tile = self.all_tiles[filled_id]
            color_tile = apply_palette_to_tile(tile, palette)
            color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb, 'RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            self.tile_images.append((filled_id, tile_photo))
            
            tile_img_id = self.palette_canvas.create_image(x_pos, y_pos, image=tile_photo, anchor='nw')
            self.palette_canvas.tag_bind(tile_img_id, '<Button-1>', 
                                        lambda e, idx=filled_id: self.on_tile_click(idx))
            
            x_pos += tile_display_size + tile_spacing * 3
        
        self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all"))
        self.update_tile_info()
    
    def update_tile_info(self):
        if self.selected_composite:
            self.tile_info_var.set(f"Selected: {self.selected_composite}")
        elif self.selected_tile is not None:
            if self.show_hex.get():
                self.tile_info_var.set(f"Selected: 0x{self.selected_tile:02X}")
            else:
                self.tile_info_var.set(f"Selected: Tile {self.selected_tile}")
        else:
            self.tile_info_var.set("Selected: None")
    
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
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        self.render_tile_palette()
        self.display_map()
        self.update_counters()
    
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
            if self.is_door_tile(row, col):
                if not self.can_edit_map():
                    return
                door_pos = self.door_positions[self.selected_map]
                self.selected_door = door_pos
                self.door_drag_start = (row, col)
                self.status_var.set("Door selected - drag to move")
                self.display_map()
                return

            # Check if clicking on spawner
            spawner = self.is_spawner_tile(row, col)
            if spawner:
                messagebox.showinfo("Spawner", f"This is a {spawner['direction']} spawner. Right-click to delete.")
                return
            
            if self.selected_composite:
                if self.selected_composite == 'door':
                    self.place_door(row, col)
                elif self.selected_composite == 'teleporter':
                    self.place_teleporter_step(row, col)
                elif self.selected_composite.startswith('spawner_'):
                    self.place_spawner(row, col)
            elif self.selected_tile is not None:
                if self.selected_tile in FILLED_TO_EMPTY:
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
        if self.selected_door is None:
            return
        
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            self.door_ghost_pos = (row, col)
            self.display_map()
    
    def on_map_release(self, event):
        if self.selected_door is None:
            return
        
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
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
    
    def mark_modified(self):
        self.modified = True
        self.root.title("Tutankham Map Editor V6 - *Unsaved*")
    
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
        hex_id = f"0x{self.selected_tile:02X}" if self.show_hex.get() else str(self.selected_tile)
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
        
        x = row * 0x08
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
            if row + 3 > map_height or col + 1 > map_width:
                messagebox.showwarning("Invalid Placement", "Teleporter doesn't fit")
                return
        
            # Check if column already has a teleporter
            teleporter_cols = self.teleporter_positions.get(self.selected_map, [])
            if col in teleporter_cols:
                messagebox.showwarning("Invalid Placement", f"Column {col} already has a teleporter")
                return
        
            self.teleporter_first_pos = (row, col)
            self.status_var.set(f"First teleporter at ({col}, {row}) - place second in SAME COLUMN (ESC to cancel)")
        else:
            first_row, first_col = self.teleporter_first_pos
        
            if col != first_col:
                messagebox.showwarning("Invalid Placement", 
                    f"Second teleporter must be in column {first_col} (same as first)")
                return
        
            if row + 3 > map_height:
                messagebox.showwarning("Invalid Placement", "Teleporter doesn't fit")
                return
        
            if not self.can_edit_map():
                self.teleporter_first_pos = None
                return
        
            visual_map = self.visual_maps[self.selected_map]
            logical_map = self.logical_maps[self.selected_map]
        
            for dr in range(3):
                visual_map[first_row + dr, first_col] = TELEPORTER_TILES[dr, 0]
                logical_row = first_col
                logical_col = first_row + dr + 1
                logical_map[logical_row, logical_col] = TELEPORTER_LOGICAL[dr, 0]
        
        for dr in range(3):
            visual_map[row + dr, col] = TELEPORTER_TILES[dr, 0]
            logical_row = col
            logical_col = row + dr + 1
            logical_map[logical_row, logical_col] = TELEPORTER_LOGICAL[dr, 0]
        
            y_coord = col * 0x08
            top_row = min(first_row, row) * 0x08
            bottom_row = max(first_row, row) * 0x08 + 0x10
        
            objects = self.object_data[self.difficulty][self.selected_map]
            for tp in objects['teleports']:
                if tp['y'] == 0:
                    tp['y'] = y_coord
                    tp['top_row'] = top_row
                    tp['bottom_row'] = bottom_row
                
                    # Add to teleporter positions
                    if self.selected_map not in self.teleporter_positions:
                        self.teleporter_positions[self.selected_map] = []
                    self.teleporter_positions[self.selected_map].append(col)
                
                    self.display_map()
                    self.update_counters()
                    self.mark_modified()
                    self.status_var.set(f"Placed teleporter pair in column {col}")
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
            self.current_map_image = Image.fromarray(map_image_rgb, 'RGB').resize(
                (new_width, new_height), Image.NEAREST)
        else:
            self.current_map_image = Image.fromarray(map_image_rgb, 'RGB')
        
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
            row = ps['x'] // 0x08
            x = col * 16 * self.zoom_level
            y = row * 16 * self.zoom_level
            size = 16 * self.zoom_level
            
            self.map_canvas.create_rectangle(x, y, x+size, y+size,
                                           outline='lime', width=3, tags='object_overlay')
            self.map_canvas.create_text(x + size//2, y + size//2, text="START",
                                       fill='lime', font=('Arial', int(8*self.zoom_level), 'bold'),
                                       tags='object_overlay')
        
        # Respawns
        for i in range(objects['respawn_count']):
            respawn = objects['respawns'][i]
            if respawn['y'] != 0:
                col = respawn['y'] // 0x08
                row = respawn['x'] // 0x08
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 16 * self.zoom_level
                
                self.map_canvas.create_oval(x, y, x+size, y+size,
                                           outline='yellow', width=2, tags='object_overlay')
                self.map_canvas.create_text(x + size//2, y + size//2, text=f"R{i+1}",
                                           fill='yellow', font=('Arial', int(8*self.zoom_level), 'bold'),
                                           tags='object_overlay')
        
        # Items with filled box overlay
        if not hasattr(self, '_overlay_images'):
            self._overlay_images = []
        self._overlay_images.clear()
        
        for item in objects['items']:
            if item['active']:
                col = item['y'] // 0x08
                row = item['x'] // 0x08
                
                if item['tile_id'] in FILLED_TO_EMPTY:
                    tile_idx = item['tile_id']
                    if tile_idx < len(self.all_tiles):
                        tile = self.all_tiles[tile_idx]
                        palette = self.palettes[self.selected_map]
                        color_tile = apply_palette_to_tile(tile, palette)
                        
                        scale = int(self.zoom_level)
                        color_tile_large = np.repeat(np.repeat(color_tile, scale, axis=0), scale, axis=1)
                        tile_rgb = color_tile_large[:, :, :3]
                        
                        tile_img = Image.fromarray(tile_rgb, 'RGB')
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
                    size = 8 * self.zoom_level
                    
                    color_map = {0x62: 'gold', 0x6F: 'cyan', 0x70: 'yellow', 0x72: 'red'}
                    color = color_map.get(item['tile_id'], 'white')
                    
                    self.map_canvas.create_rectangle(x+2, y+2, x+size-2, y+size-2,
                                                    outline=color, width=2, tags='object_overlay')
        
        # Teleporters
        for tp in objects['teleports']:
            if tp['y'] != 0:
                col = tp['y'] // 0x08
                row_top = tp['top_row'] // 0x08
                row_bottom = tp['bottom_row'] // 0x08
                
                x = col * 16 * self.zoom_level
                y_top = row_top * 16 * self.zoom_level
                y_bottom = row_bottom * 16 * self.zoom_level
                
                self.map_canvas.create_line(x + 8*self.zoom_level, y_top + 8*self.zoom_level,
                                           x + 8*self.zoom_level, y_bottom + 8*self.zoom_level,
                                           fill='magenta', width=2, dash=(4, 4), tags='object_overlay')
        
        # Spawners
        for spawn in objects['spawns']:
            if spawn['y'] != 0:
                col = spawn['y'] // 0x08
                row = spawn['x'] // 0x08
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 16 * self.zoom_level
                
                self.map_canvas.create_oval(x, y, x+size, y+size,
                                           outline='orange', width=2, tags='object_overlay')

        # ADD THIS - Show spawn point tiles (player start and respawn flames)
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
                        label = 'P'
                    else:  # Respawn flame
                        color = 'yellow'
                        label = 'F'
            
                    self.map_canvas.create_rectangle(x, y, x+size, y+size,
                                               outline=color, width=2, tags='object_overlay')
                    self.map_canvas.create_text(x + size//2, y + size//2, text=label,
                                               fill=color, font=('Arial', int(8*self.zoom_level), 'bold'),
                                               tags='object_overlay')

    def save_file(self):
        try:
            backups = []
            all_paths = [visual_map_rom_path] + logical_map_rom_paths + object_rom_paths
            for path in all_paths:
                backup_path = backup_file(path)
                if backup_path:
                    backups.append(os.path.basename(backup_path))
            
            save_visual_maps_to_rom(self.visual_maps, visual_map_rom_path, preserve_extra=True)
            save_logical_maps_to_rom(self.logical_maps, preserve_extra=True)
            
            for diff in range(NUM_DIFFICULTIES):
                for i in range(num_maps):
                    save_object_data(self.object_data[diff][i], i, diff)
            
            self.modified = False
            self.root.title("Tutankham Map Editor V6")
            messagebox.showinfo("Success", 
                              f"All data saved successfully!\n"
                              f"Visual: {visual_map_rom_path}\n"
                              f"Logical: {', '.join(logical_map_rom_paths)}\n"
                              f"Objects: {', '.join(object_rom_paths)}\n"
                              f"Difficulties: All {NUM_DIFFICULTIES}\n\n"
                              f"Backups: {len(backups)} files")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def save_file_as(self):
        directory = filedialog.askdirectory(title="Select directory to export ROM files")
        if not directory:
            return
        
        try:
            visual_path = os.path.join(directory, "c8_modified.8i")
            save_visual_maps_to_rom(self.visual_maps, visual_path, preserve_extra=False)
            
            for rom_idx, rom_path in enumerate(logical_map_rom_paths):
                dest_path = os.path.join(directory, f"c{6+rom_idx}_modified.{6+rom_idx}i")
                shutil.copy2(rom_path, dest_path)
            
            save_logical_maps_to_rom(self.logical_maps, preserve_extra=False)
            
            for rom_idx, rom_path in enumerate(object_rom_paths):
                dest_path = os.path.join(directory, f"m{rom_idx+1}_modified.{rom_idx+1}h")
                shutil.copy2(rom_path, dest_path)
            
            for diff in range(NUM_DIFFICULTIES):
                for i in range(num_maps):
                    save_object_data(self.object_data[diff][i], i, diff)
            
            self.modified = False
            messagebox.showinfo("Success", f"All files exported to {directory}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def run(self):
        self.root.mainloop()

# Load all data
all_tiles = load_tiles()
visual_maps = load_visual_maps()
logical_maps = load_logical_maps()

# Create and run editor
editor = MapEditor(visual_maps, logical_maps, all_tiles, palettes)
editor.run()