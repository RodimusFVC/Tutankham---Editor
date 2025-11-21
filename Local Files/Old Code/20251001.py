import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import shutil
from datetime import datetime

# Define the ROM file and offsets
tile_roms = ["./c1.1i", "./c2.2i", "./c3.3i", "./c4.4i", "./c5.5i"]
map_rom_path = "./c8.8i"
tile_size = 16 * 16 // 2  # 16x16 pixels, 4-bit color = 128 bytes
num_maps = 4
map_width = 64
map_height = 12
map_size = 0x300  # 768 bytes per map

# Define the palettes for each map
palettes = [
    # Palette for map 1
    [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 133, 133, 148), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 91, 162, 69)],
    # Palette for map 2
    [(255, 000, 000, 000), (255, 000, 000, 148), (255, 000, 224, 000), (255, 162, 000, 217), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 133, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 29, 195, 148)],
    # Map 3 Palette
    [(255, 000, 000, 000), (255, 91, 62, 69), (255, 000, 224, 000), (255, 162, 133, 000), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 62, 195, 217), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 224, 29, 148)],
    # Map 4 Palette
    [(255, 000, 000, 000), (255, 000, 000, 000), (255, 000, 224, 000), (255, 000, 000, 217), 
     (255, 224, 162, 148), (255, 162, 000, 217), (255, 224, 000, 000), (255, 133, 133, 148), 
     (255, 224, 224, 000), (255, 162, 29, 000), (255, 224, 133, 000), (255, 224, 000, 148), 
     (255, 000, 000, 217), (255, 62, 195, 217), (255, 224, 224, 217), (255, 000, 000, 000)]
]

# Read the ROM file
def read_rom(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())

# Extract a single tile from the ROM - FIXED to properly unpack 4-bit pixels
def extract_tile(rom_data, offset, width=16, height=16):
    tile = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            byte_offset = offset + y * (width // 2) + (x // 2)
            byte_val = rom_data[byte_offset]
            # Unpack nibbles - 2 pixels per byte
            if x % 2 == 0:
                tile[y, x] = byte_val & 0x0F  # Low nibble
            else:
                tile[y, x] = (byte_val >> 4) & 0x0F  # High nibble
    return tile

# Rotate the tile 90 degrees counterclockwise
def rotate_tile(tile):
    return np.rot90(tile, k=1)

# Apply the color palette to a tile
def apply_palette_to_tile(tile, palette):
    height, width = tile.shape
    color_tile = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            color_index = tile[y, x] % 16
            if 0 <= color_index < len(palette):
                color_tile[y, x] = [
                    palette[color_index][1],  # Red
                    palette[color_index][2],  # Green
                    palette[color_index][3],  # Blue
                    palette[color_index][0]   # Alpha
                ]
    return color_tile

# Load all the tile ROMs and extract tiles
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

# Extract the 4 maps from the map ROM (c8.8i)
def load_maps():
    map_data = read_rom(map_rom_path)
    maps = []
    
    for map_index in range(num_maps):
        start_offset = map_index * map_size
        map_layout = np.zeros((map_height, map_width), dtype=np.uint8)
        
        for byte_index in range(map_size):
            row = (byte_index % map_height)
            col = (byte_index // map_height)
            flipped_row = map_height - 1 - row
            map_layout[flipped_row, col] = map_data[start_offset + byte_index]
        
        maps.append(map_layout)
    return maps

# Save maps back to ROM file
def save_maps_to_rom(maps, output_path):
    """Convert maps back to ROM format and save"""
    map_data = bytearray()
    
    for map_index in range(len(maps)):
        map_layout = maps[map_index]
        
        # Convert back to ROM format (reverse the loading process)
        for byte_index in range(map_size):
            row = (byte_index % map_height)
            col = (byte_index // map_height)
            flipped_row = map_height - 1 - row
            map_data.append(map_layout[flipped_row, col])
    
    # Write to file
    with open(output_path, "wb") as f:
        f.write(map_data)

def backup_file(filepath):
    """Create a backup of the original file"""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        return backup_path
    return None

# Create the GUI for map editing
class MapEditor:
    def __init__(self, maps, all_tiles, palettes):
        self.maps = maps
        self.all_tiles = all_tiles
        self.palettes = palettes
        self.selected_tile = 0
        self.selected_map = 0
        self.tile_images = []
        self.zoom_level = 2.0  # Start at 2x zoom
        self.modified = False
        
        self.root = tk.Tk()
        self.root.title("Tutankham Tilemap Editor")
        self.root.geometry("1400x700")
        
        self.show_grid = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        
        self.setup_ui()
        
        self.root.bind('<Configure>', self.on_window_resize)
        self.last_width = self.root.winfo_width()
        self.last_height = self.root.winfo_height()
        
        self.render_tile_palette()
        self.display_map()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top panel - Map canvas
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Map canvas with scrollbars
        canvas_frame = ttk.Frame(top_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.map_canvas = tk.Canvas(canvas_frame, width=1024, height=384, bg='black')
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.map_canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.map_canvas.yview)
        
        self.map_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        self.map_canvas.grid(row=0, column=0, sticky='nsew')
        h_scroll.grid(row=1, column=0, sticky='ew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.map_canvas.bind("<Button-1>", self.on_map_click)
        
        # Control panel
        control_frame = ttk.Frame(top_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="Select Map:").pack(side=tk.LEFT, padx=5)
        for i in range(num_maps):
            btn = ttk.Button(control_frame, text=f"Map {i + 1}", 
                           command=lambda i=i: self.on_map_select(i))
            btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Checkbutton(control_frame, text="Show Grid", 
                       variable=self.show_grid, 
                       command=self.display_map).pack(side=tk.LEFT, padx=10)
        
        ttk.Label(control_frame, text="Zoom:").pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="-", width=3, 
                  command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(control_frame, text=f"{int(self.zoom_level)}x")
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="+", width=3, 
                  command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        
        # File operations
        file_frame = ttk.Frame(top_frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Save As...", command=self.save_file_as).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Export All Maps...", command=self.export_all).pack(side=tk.LEFT, padx=2)
        
        status_bar = ttk.Label(top_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=5, pady=2)
        
        # Bottom panel - Tile palette
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH)
        
        palette_label_frame = ttk.Frame(bottom_frame)
        palette_label_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(palette_label_frame, text="Tile Palette", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=10)
        
        self.tile_info_var = tk.StringVar(value="Selected: Tile 0")
        ttk.Label(palette_label_frame, textvariable=self.tile_info_var).pack(side=tk.LEFT, padx=20)
        
        palette_frame = ttk.Frame(bottom_frame)
        palette_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.palette_canvas = tk.Canvas(palette_frame, height=200, bg='#2b2b2b')
        palette_scroll_h = ttk.Scrollbar(palette_frame, orient=tk.HORIZONTAL, 
                                      command=self.palette_canvas.xview)
        palette_scroll_v = ttk.Scrollbar(palette_frame, orient=tk.VERTICAL,
                                      command=self.palette_canvas.yview)
        
        self.palette_canvas.configure(xscrollcommand=palette_scroll_h.set,
                                     yscrollcommand=palette_scroll_v.set)
        self.palette_canvas.grid(row=0, column=0, sticky='nsew')
        palette_scroll_h.grid(row=1, column=0, sticky='ew')
        palette_scroll_v.grid(row=0, column=1, sticky='ns')
        
        palette_frame.grid_rowconfigure(0, weight=1)
        palette_frame.grid_columnconfigure(0, weight=1)
        
    def render_tile_palette(self):
        """Render all tiles as clickable images in the palette"""
        tiles_per_row = 32
        tile_spacing = 4
        
        # Tiles are now 16x16 after rotation
        tile_display_width = int(16 * self.zoom_level)
        tile_display_height = int(16 * self.zoom_level)
        
        palette = self.palettes[self.selected_map]
        
        self.tile_images.clear()
        
        for i, tile in enumerate(self.all_tiles):
            color_tile = apply_palette_to_tile(tile, palette)
            
            # Scale based on zoom level
            scale_factor = int(self.zoom_level)
            color_tile_large = np.repeat(np.repeat(color_tile, scale_factor, axis=0), 
                                        scale_factor, axis=1)
            
            tile_rgb = color_tile_large[:, :, :3]
            tile_img = Image.fromarray(tile_rgb, 'RGB')
            tile_photo = ImageTk.PhotoImage(tile_img)
            self.tile_images.append(tile_photo)
            
            row = i // tiles_per_row
            col = i % tiles_per_row
            
            x = col * (tile_display_width + tile_spacing) + tile_spacing
            y = row * (tile_display_height + tile_spacing) + tile_spacing
            
            tile_id = self.palette_canvas.create_image(x, y, image=tile_photo, anchor='nw')
            
            self.palette_canvas.tag_bind(tile_id, '<Button-1>', 
                                        lambda e, idx=i: self.on_tile_click(idx))
            
            if i == 0:
                self.palette_canvas.create_rectangle(x-2, y-2, 
                                                    x+tile_display_width+2, 
                                                    y+tile_display_height+2,
                                                    outline='yellow', width=2, 
                                                    tags=f'border_{i}')
        
        self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all"))
        
    def on_tile_click(self, tile_index):
        """Handle tile selection from palette"""
        self.palette_canvas.delete('selection_border')
        
        self.selected_tile = tile_index
        self.tile_info_var.set(f"Selected: Tile {self.selected_tile}")
        
        tiles_per_row = 32
        tile_spacing = 4
        tile_display_width = int(16 * self.zoom_level)
        tile_display_height = int(16 * self.zoom_level)
        
        row = tile_index // tiles_per_row
        col = tile_index % tiles_per_row
        
        x = col * (tile_display_width + tile_spacing) + tile_spacing
        y = row * (tile_display_height + tile_spacing) + tile_spacing
        
        self.palette_canvas.create_rectangle(x-2, y-2, 
                                            x+tile_display_width+2, 
                                            y+tile_display_height+2,
                                            outline='yellow', width=2, 
                                            tags='selection_border')
        
    def on_map_select(self, map_index):
        """Switch to different map"""
        self.selected_map = map_index
        self.tile_images.clear()
        self.palette_canvas.delete('all')
        self.render_tile_palette()
        self.display_map()
        
    def on_map_click(self, event):
        """Handle clicks on the map canvas"""
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)
        
        # Tiles are 16x16
        col = int(canvas_x // (16 * self.zoom_level))
        row = int(canvas_y // (16 * self.zoom_level))
        
        if 0 <= row < map_height and 0 <= col < map_width:
            self.maps[self.selected_map][row, col] = self.selected_tile
            self.display_map()
            self.modified = True
            self.root.title("Tutankham Tilemap Editor - *Unsaved*")
            self.status_var.set(f"Placed tile {self.selected_tile} at ({col}, {row})")
    
    def zoom_in(self):
        """Increase zoom level"""
        if self.zoom_level < 8:
            self.zoom_level += 1
            self.zoom_label.config(text=f"{int(self.zoom_level)}x")
            self.display_map()
            self.palette_canvas.delete('all')
            self.render_tile_palette()
    
    def zoom_out(self):
        """Decrease zoom level"""
        if self.zoom_level > 1:
            self.zoom_level -= 1
            self.zoom_label.config(text=f"{int(self.zoom_level)}x")
            self.display_map()
            self.palette_canvas.delete('all')
            self.render_tile_palette()
        
    def display_map(self):
        """Render the current map"""
        raw_map_layout = self.maps[self.selected_map]
        # Tiles are 16x16 after rotation
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
        
        # Scale the image based on zoom level
        if self.zoom_level != 1:
            new_height = int(map_image_rgb.shape[0] * self.zoom_level)
            new_width = int(map_image_rgb.shape[1] * self.zoom_level)
            self.current_map_image = Image.fromarray(map_image_rgb, 'RGB').resize(
                (new_width, new_height), 
                Image.NEAREST
            )
        else:
            self.current_map_image = Image.fromarray(map_image_rgb, 'RGB')
        
        map_image_tk = ImageTk.PhotoImage(self.current_map_image)
        
        self.map_canvas.delete('all')
        self.map_canvas.create_image(0, 0, image=map_image_tk, anchor='nw')
        self.map_canvas.image = map_image_tk
        
        # Draw grid if enabled
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
    
    def on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            new_width = self.root.winfo_width()
            new_height = self.root.winfo_height()
            
            if abs(new_width - self.last_width) > 10 or abs(new_height - self.last_height) > 10:
                self.last_width = new_width
                self.last_height = new_height
                self.display_map()
        
    def save_file(self):
        """Save to original ROM file (with backup)"""
        try:
            backup_path = backup_file(map_rom_path)
            if backup_path:
                self.status_var.set(f"Backup created: {os.path.basename(backup_path)}")
            
            save_maps_to_rom(self.maps, map_rom_path)
            self.modified = False
            self.root.title("Tutankham Tilemap Editor")
            messagebox.showinfo("Success", f"Maps saved to {map_rom_path}\nBackup: {backup_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            
    def save_file_as(self):
        """Save to a new file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".8i",
            filetypes=[("ROM files", "*.8i"), ("All files", "*.*")],
            initialfile="c8_modified.8i"
        )
        
        if filepath:
            try:
                save_maps_to_rom(self.maps, filepath)
                self.modified = False
                messagebox.showinfo("Success", f"Maps saved to {filepath}")
                self.status_var.set(f"Saved to {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
                
    def export_all(self):
        """Export all maps to separate files"""
        directory = filedialog.askdirectory(title="Select export directory")
        
        if directory:
            try:
                for i, single_map in enumerate(self.maps):
                    filepath = os.path.join(directory, f"map_{i+1}.bin")
                    save_maps_to_rom([single_map], filepath)
                
                messagebox.showinfo("Success", f"Exported {len(self.maps)} maps to {directory}")
                self.status_var.set(f"Exported {len(self.maps)} maps")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
                
    def run(self):
        self.root.mainloop()

# Load all tiles and maps
all_tiles = load_tiles()
maps = load_maps()

# Create and run the editor
editor = MapEditor(maps, all_tiles, palettes)
editor.run()