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

# Object data constants
OBJECT_BASE_OFFSET = 0x0636
OBJECT_BLOCK_SIZE = 0x0148
NUM_ITEMS = 14
NUM_TELEPORTS = 6
NUM_SPAWNS = 7

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
    """Load object data for a specific map and difficulty"""
    block_number = (difficulty * 4) + map_index
    offset = OBJECT_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
    # Determine which ROM file
    rom_index = 0 if offset < 0x1000 else 1
    rom_offset = offset if rom_index == 0 else offset - 0x1000
    
    rom_data = read_rom(object_rom_paths[rom_index])
    
    objects = {
        'items': [],
        'teleports': [],
        'spawns': []
    }
    
    # Read items (14 × 16 bytes)
    pos = rom_offset
    for i in range(NUM_ITEMS):
        item = {
            'active': rom_data[pos] == 0x01,
            'y': (rom_data[pos + 6] << 8) | rom_data[pos + 5],
            'x': rom_data[pos + 7],
            'tile_id': rom_data[pos + 15]
        }
        objects['items'].append(item)
        pos += 16
    
    pos += 1  # Skip separator
    
    # Read teleports (6 × 8 bytes: 4 data + 4 padding)
    for i in range(NUM_TELEPORTS):
        teleport = {
            'y': (rom_data[pos + 1] << 8) | rom_data[pos],
            'bottom_row': rom_data[pos + 2],
            'top_row': rom_data[pos + 3]
        }
        objects['teleports'].append(teleport)
        pos += 8
    
    pos += 1  # Skip separator
    
    # Read spawns (7 × 4 bytes: 3 data + 1 padding)
    for i in range(NUM_SPAWNS):
        spawn = {
            'y': (rom_data[pos + 1] << 8) | rom_data[pos],
            'x': rom_data[pos + 2]
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
    """Save object data back to ROM"""
    block_number = (difficulty * 4) + map_index
    offset = OBJECT_BASE_OFFSET + (block_number * OBJECT_BLOCK_SIZE)
    
    rom_index = 0 if offset < 0x1000 else 1
    rom_offset = offset if rom_index == 0 else offset - 0x1000
    
    rom_data = read_rom(object_rom_paths[rom_index])
    
    pos = rom_offset
    
    # Write items
    for item in objects['items']:
        rom_data[pos] = 0x01 if item['active'] else 0x00
        for i in range(1, 5):
            rom_data[pos + i] = 0x00
        rom_data[pos + 5] = item['y'] & 0xFF
        rom_data[pos + 6] = (item['y'] >> 8) & 0xFF
        rom_data[pos + 7] = item['x']
        for i in range(8, 15):
            rom_data[pos + i] = 0x00
        rom_data[pos + 15] = item['tile_id']
        pos += 16
    
    rom_data[pos] = 0x00
    pos += 1
    
    # Write teleports
    for teleport in objects['teleports']:
        rom_data[pos] = teleport['y'] & 0xFF
        rom_data[pos + 1] = (teleport['y'] >> 8) & 0xFF
        rom_data[pos + 2] = teleport['bottom_row']
        rom_data[pos + 3] = teleport['top_row']
        for i in range(4, 8):
            rom_data[pos + i] = 0x00
        pos += 8
    
    rom_data[pos] = 0x00
    pos += 1
    
    # Write spawns
    for spawn in objects['spawns']:
        rom_data[pos] = spawn['y'] & 0xFF
        rom_data[pos + 1] = (spawn['y'] >> 8) & 0xFF
        rom_data[pos + 2] = spawn['x']
        rom_data[pos + 3] = 0x00
        pos += 4
    
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
        
        # Load object data
        self.object_data = {}
        for i in range(num_maps):
            self.object_data[i] = load_object_data(i, self.difficulty)
        
        self.root = tk.Tk()
        self.root.title("Tutankham Map Editor - Enhanced")
        self.root.geometry("1600x900")
        
        # Create tkinter variables AFTER root window
        self.show_hex = tk.BooleanVar(value=True)
        self.edit_mode = tk.StringVar(value="tile")
        self.selected_spawner_dir = tk.StringVar(value="right")
        self.show_grid = tk.BooleanVar(value=False)
        self.show_objects = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.coord_var = tk.StringVar(value="")
        
        self.setup_ui()
        self.render_tile_palette()
        self.display_map()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - controls
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)
        
        # Map selection
        ttk.Label(left_panel, text="Map Selection", font=('Arial', 10, 'bold')).pack(pady=5)
        for i in range(num_maps):
            btn = ttk.Button(left_panel, text=f"Map {i + 1}", 
                           command=lambda i=i: self.on_map_select(i))
            btn.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Difficulty selection
        ttk.Label(left_panel, text="Difficulty", font=('Arial', 10, 'bold')).pack(pady=5)
        diff_frame = ttk.Frame(left_panel)
        diff_frame.pack(fill=tk.X, padx=5)
        for i in range(3):
            btn = ttk.Button(diff_frame, text=str(i+1), width=5,
                           command=lambda i=i: self.set_difficulty(i))
            btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Edit mode
        ttk.Label(left_panel, text="Edit Mode", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Radiobutton(left_panel, text="Tile Editing", variable=self.edit_mode, 
                       value="tile").pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(left_panel, text="Place Door", variable=self.edit_mode, 
                       value="door").pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(left_panel, text="Place Teleporter", variable=self.edit_mode, 
                       value="teleporter").pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(left_panel, text="Place Spawner", variable=self.edit_mode, 
                       value="spawner").pack(anchor=tk.W, padx=5)
        
        # Spawner direction (only visible when spawner mode)
        spawner_frame = ttk.LabelFrame(left_panel, text="Spawner Direction")
        spawner_frame.pack(fill=tk.X, padx=5, pady=5)
        for direction in ['right', 'left', 'up', 'down']:
            ttk.Radiobutton(spawner_frame, text=direction.capitalize(), 
                          variable=self.selected_spawner_dir, 
                          value=direction).pack(anchor=tk.W, padx=5)
        
        ttk.Radiobutton(left_panel, text="Place Item", variable=self.edit_mode, 
                       value="item").pack(anchor=tk.W, padx=5)
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Display options
        ttk.Label(left_panel, text="Display", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Checkbutton(left_panel, text="Show Grid", variable=self.show_grid, 
                       command=self.display_map).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(left_panel, text="Show Objects", variable=self.show_objects, 
                       command=self.display_map).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(left_panel, text="Hex Tile IDs", variable=self.show_hex, 
                       command=self.render_tile_palette).pack(anchor=tk.W, padx=5)
        
        # Zoom
        zoom_frame = ttk.Frame(left_panel)
        zoom_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="-", width=3, command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text=f"{int(self.zoom_level)}x")
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="+", width=3, command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        
        # Right side - map and palette
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Top - map canvas
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
        
        # Coordinate display
        coord_frame = ttk.Frame(map_frame)
        coord_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(coord_frame, text="Coordinates:").pack(side=tk.LEFT)
        ttk.Label(coord_frame, textvariable=self.coord_var, font=('Courier', 9)).pack(side=tk.LEFT, padx=5)
        
        # Bottom - tile palette
        palette_frame = ttk.LabelFrame(right_panel, text="Tile Palette")
        palette_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=5, pady=5)
        
        self.tile_info_var = tk.StringVar(value="Selected: 0x00")
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
        
        # Status bar
        status_frame = ttk.Frame(right_panel)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save As...", command=self.save_file_as).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)
        
    def set_difficulty(self, diff):
        self.difficulty = diff
        # Reload object data for new difficulty
        for i in range(num_maps):
            self.object_data[i] = load_object_data(i, self.difficulty)
        self.display_map()
        self.status_var.set(f"Switched to Difficulty {diff + 1}")
        
    def render_tile_palette(self):
        tiles_per_row = 32
        tile_spacing = 4
        tile_display_size = int(16 * self.zoom_level)
        palette = self.palettes[self.selected_map]
        
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        
        for i, tile in enumerate(self.all_tiles):
            color_tile = apply_palette_to_tile(tile, palette)
            scale_factor = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale_factor, axis=0), 
                                        scale_factor, axis=1)
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb, 'RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            self.tile_images.append(tile_photo)
            
            row = i // tiles_per_row
            col = i % tiles_per_row
            x = col * (tile_display_size + tile_spacing) + tile_spacing
            y = row * (tile_display_size + tile_spacing) + tile_spacing
            
            tile_id = self.palette_canvas.create_image(x, y, image=tile_photo, anchor='nw')
            self.palette_canvas.tag_bind(tile_id, '<Button-1>', 
                                        lambda e, idx=i: self.on_tile_click(idx))
        
        self.palette_canvas.create_rectangle(tile_spacing-2, tile_spacing-2, 
                                            tile_spacing+tile_display_size+2, 
                                            tile_spacing+tile_display_size+2,
                                            outline='yellow', width=2, tags='selection_border')
        self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all"))
        self.update_tile_info()
        
    def update_tile_info(self):
        if self.show_hex.get():
            self.tile_info_var.set(f"Selected: 0x{self.selected_tile:02X}")
        else:
            self.tile_info_var.set(f"Selected: Tile {self.selected_tile}")
    
    def on_tile_click(self, tile_index):
        self.palette_canvas.delete('selection_border')
        self.selected_tile = tile_index
        self.update_tile_info()
        
        tiles_per_row = 32
        tile_spacing = 4
        tile_display_size = int(16 * self.zoom_level)
        
        row = tile_index // tiles_per_row
        col = tile_index % tiles_per_row
        x = col * (tile_display_size + tile_spacing) + tile_spacing
        y = row * (tile_display_size + tile_spacing) + tile_spacing
        
        self.palette_canvas.create_rectangle(x-2, y-2, 
                                            x+tile_display_size+2, 
                                            y+tile_display_size+2,
                                            outline='yellow', width=2, tags='selection_border')
        
    def on_map_select(self, map_index):
        self.selected_map = map_index
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        self.render_tile_palette()
        self.display_map()
        
    def on_map_hover(self, event):
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            # Convert to game coordinates
            x_coord = row * 0x08
            y_coord = col * 0x08
            self.coord_var.set(f"XX=0x{x_coord:02X}  YYYY=0x{y_coord:04X}  (Row={row}, Col={col})")
        else:
            self.coord_var.set("")
        
    def on_map_click(self, event):
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            mode = self.edit_mode.get()
            
            if mode == "tile":
                self.place_tile(row, col)
            elif mode == "door":
                self.place_door(row, col)
            elif mode == "teleporter":
                self.place_teleporter(row, col)
            elif mode == "spawner":
                self.place_spawner(row, col)
            elif mode == "item":
                self.place_item(row, col)
    
    def place_tile(self, row, col):
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
        self.modified = True
        self.root.title("Tutankham Map Editor - *Unsaved*")
        hex_id = f"0x{self.selected_tile:02X}" if self.show_hex.get() else str(self.selected_tile)
        self.status_var.set(f"Placed tile {hex_id} at ({col}, {row})")
    
    def place_composite_block(self, row, col, tiles, logical):
        """Generic function to place composite blocks"""
        h, w = tiles.shape
        
        if row + h > map_height or col + w > map_width:
            messagebox.showwarning("Invalid Placement", "Block doesn't fit at this location")
            return False
        
        visual_map = self.visual_maps[self.selected_map]
        logical_map = self.logical_maps[self.selected_map]
        
        for r in range(h):
            for c in range(w):
                visual_map[row + r, col + c] = tiles[r, c]
                logical_row = col + c
                logical_col = row + r + 1
                logical_map[logical_row, logical_col] = logical[r, c]
        
        self.display_map()
        self.modified = True
        self.root.title("Tutankham Map Editor - *Unsaved*")
        return True
    
    def place_door(self, row, col):
        if self.place_composite_block(row, col, DOOR_TILES, DOOR_LOGICAL):
            self.status_var.set(f"Placed door at ({col}, {row})")
    
    def place_teleporter(self, row, col):
        if self.place_composite_block(row, col, TELEPORTER_TILES, TELEPORTER_LOGICAL):
            # Add teleporter to object data
            x_coord = row * 0x08
            y_coord = col * 0x08
            
            # Find empty teleporter slot
            teleports = self.object_data[self.selected_map]['teleports']
            for i, tp in enumerate(teleports):
                if tp['y'] == 0 and tp['bottom_row'] == 0:
                    tp['y'] = y_coord
                    tp['bottom_row'] = x_coord + 0x10  # 2 tiles down
                    tp['top_row'] = x_coord
                    self.status_var.set(f"Placed teleporter at ({col}, {row}) - Remember to place pair!")
                    return
            
            messagebox.showwarning("No Slots", "No empty teleporter slots available")
    
    def place_spawner(self, row, col):
        direction = self.selected_spawner_dir.get()
        config = SPAWNER_CONFIGS[direction]
        
        if self.place_composite_block(row, col, config['tiles'], config['logical']):
            # Add spawner to object data
            x_coord = row * 0x08
            y_coord = col * 0x08
            
            spawns = self.object_data[self.selected_map]['spawns']
            for i, spawn in enumerate(spawns):
                if spawn['y'] == 0 and spawn['x'] == 0:
                    spawn['y'] = y_coord
                    spawn['x'] = x_coord
                    self.status_var.set(f"Placed {direction} spawner at ({col}, {row})")
                    return
            
            messagebox.showwarning("No Slots", "No empty spawner slots available")
    
    def place_item(self, row, col):
        """Interactive item placement - asks user which item type"""
        item_window = tk.Toplevel(self.root)
        item_window.title("Place Item")
        item_window.geometry("300x200")
        
        ttk.Label(item_window, text="Select Item Type:", font=('Arial', 10, 'bold')).pack(pady=10)
        
        item_type = tk.IntVar(value=0x62)
        
        ttk.Radiobutton(item_window, text="Treasure Box (0x62)", variable=item_type, 
                       value=0x62).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(item_window, text="Ring (0x6F)", variable=item_type, 
                       value=0x6F).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(item_window, text="Key (0x70)", variable=item_type, 
                       value=0x70).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(item_window, text="Keyhole (0x72)", variable=item_type, 
                       value=0x72).pack(anchor=tk.W, padx=20)
        
        def place():
            tile_id = item_type.get()
            
            # Check if correct tile is at location
            if tile_id in ITEM_TILES and ITEM_TILES[tile_id] is not None:
                current_tile = self.visual_maps[self.selected_map][row, col]
                if current_tile != ITEM_TILES[tile_id]:
                    messagebox.showwarning("Invalid Tile", 
                        f"Item 0x{tile_id:02X} requires tile 0x{ITEM_TILES[tile_id]:02X} at this location")
                    return
            
            # Add item to object data
            x_coord = row * 0x08
            y_coord = col * 0x08
            
            items = self.object_data[self.selected_map]['items']
            for i, item in enumerate(items):
                if not item['active']:
                    item['active'] = True
                    item['x'] = x_coord
                    item['y'] = y_coord
                    item['tile_id'] = tile_id
                    self.status_var.set(f"Placed item 0x{tile_id:02X} at ({col}, {row})")
                    self.display_map()
                    item_window.destroy()
                    return
            
            messagebox.showwarning("No Slots", "No empty item slots available (max 14)")
        
        ttk.Button(item_window, text="Place", command=place).pack(pady=20)
        ttk.Button(item_window, text="Cancel", command=item_window.destroy).pack()
    
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
        
        # Draw objects overlay
        if self.show_objects.get():
            self.draw_objects_overlay()
        
        # Draw grid
        if self.show_grid.get():
            for x in range(0, int(map_width * 16 * self.zoom_level), int(16 * self.zoom_level)):
                self.map_canvas.create_line(x, 0, x, int(map_height * 16 * self.zoom_level), 
                                           fill='#444444')
            for y in range(0, int(map_height * 16 * self.zoom_level), int(16 * self.zoom_level)):
                self.map_canvas.create_line(0, y, int(map_width * 16 * self.zoom_level), y, 
                                           fill='#444444')
        
        self.map_canvas.configure(scrollregion=(0, 0, 
                                               int(map_width * 16 * self.zoom_level), 
                                               int(map_height * 16 * self.zoom_level)))
    
    def draw_objects_overlay(self):
        """Draw visual indicators for placed objects"""
        objects = self.object_data[self.selected_map]
        
        # Draw items
        for item in objects['items']:
            if item['active']:
                col = item['y'] // 0x08
                row = item['x'] // 0x08
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 8 * self.zoom_level
                
                # Different colors for different item types
                color_map = {0x62: 'gold', 0x6F: 'cyan', 0x70: 'yellow', 0x72: 'red'}
                color = color_map.get(item['tile_id'], 'white')
                
                self.map_canvas.create_rectangle(x+2, y+2, x+size-2, y+size-2,
                                                outline=color, width=2, tags='object_overlay')
        
        # Draw teleporters
        for tp in objects['teleports']:
            if tp['y'] != 0:
                col = tp['y'] // 0x08
                row_top = tp['top_row'] // 0x08
                row_bottom = tp['bottom_row'] // 0x08
                
                x = col * 16 * self.zoom_level
                y_top = row_top * 16 * self.zoom_level
                y_bottom = row_bottom * 16 * self.zoom_level
                
                self.map_canvas.create_rectangle(x, y_top, x + 16*self.zoom_level, y_bottom + 16*self.zoom_level,
                                                outline='magenta', width=2, tags='object_overlay')
        
        # Draw spawners
        for spawn in objects['spawns']:
            if spawn['y'] != 0:
                col = spawn['y'] // 0x08
                row = spawn['x'] // 0x08
                x = col * 16 * self.zoom_level
                y = row * 16 * self.zoom_level
                size = 16 * self.zoom_level
                
                self.map_canvas.create_oval(x, y, x+size, y+size,
                                           outline='orange', width=2, tags='object_overlay')
        
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
            
            # Save object data for all maps
            for i in range(num_maps):
                save_object_data(self.object_data[i], i, self.difficulty)
            
            self.modified = False
            self.root.title("Tutankham Map Editor - Enhanced")
            messagebox.showinfo("Success", 
                              f"All data saved successfully!\n"
                              f"Visual: {visual_map_rom_path}\n"
                              f"Logical: {', '.join(logical_map_rom_paths)}\n"
                              f"Objects: {', '.join(object_rom_paths)}\n\n"
                              f"Backups: {len(backups)} files")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            
    def save_file_as(self):
        directory = filedialog.askdirectory(title="Select directory to save ROM files")
        if not directory:
            return
            
        try:
            # Copy and modify files
            visual_path = os.path.join(directory, "c8_modified.8i")
            save_visual_maps_to_rom(self.visual_maps, visual_path, preserve_extra=False)
            
            # Save logical maps
            for rom_idx, rom_path in enumerate(logical_map_rom_paths):
                dest_path = os.path.join(directory, f"c{6+rom_idx}_modified.{6+rom_idx}i")
                shutil.copy2(rom_path, dest_path)
            
            save_logical_maps_to_rom(self.logical_maps, preserve_extra=False)
            
            # Save object ROMs
            for rom_idx, rom_path in enumerate(object_rom_paths):
                dest_path = os.path.join(directory, f"m{rom_idx+1}_modified.{rom_idx+1}h")
                shutil.copy2(rom_path, dest_path)
            
            for i in range(num_maps):
                save_object_data(self.object_data[i], i, self.difficulty)
            
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