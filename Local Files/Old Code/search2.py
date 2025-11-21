import struct

# Known object positions
objects = [
#Map 1
    {"tile": 0x62, "row": 0x38, "col": 0x10, "name": "Map 1 : Treasure Box"},
    {"tile": 0x70, "row": 0x78, "col": 0x50, "name": "Map 1 : Key"},
    {"tile": 0x6F, "row": 0xE8, "col": 0x20, "name": "Map 1 : Ring 1"},
    {"tile": 0x6F, "row": 0xA0, "col": 0x18, "name": "Map 1 : Ring 2"},
    {"tile": 0x72, "row": 0xD0, "col": 0x10, "name": "Map 1 : Keyhole"},
    {"tile": 0x00, "row": 0x58, "col": 0x38, "name": "Map 1 : Spawn 1"},
    {"tile": 0x00, "row": 0x88, "col": 0x48, "name": "Map 1 : Spawn 2"},
    {"tile": 0x00, "row": 0xD8, "col": 0x30, "name": "Map 1 : Spawn 3"},
    {"tile": 0x00, "row": 0x60, "col": 0x48, "name": "Map 1 : Teleport 1 (Top)"},
    {"tile": 0x00, "row": 0x60, "col": 0x10, "name": "Map 1 : Teleport 1 (Bottom)"},
#Map 2
    {"tile": 0x6F, "row": 8, "col": 14, "name": "Map 2 : Ring 1"},
    {"tile": 0x62, "row": 3, "col": 19, "name": "Map 2 : Treasure Box 1"},
    {"tile": 0x70, "row": 2, "col": 21, "name": "Map 2 : Key 1"},
    {"tile": 0x6F, "row": 8, "col": 28, "name": "Map 2 : Ring 2"},
    {"tile": 0x70, "row": 11, "col": 31, "name": "Map 2 : Key 1"},
    {"tile": 0x6F, "row": 4, "col": 35, "name": "Map 2 : Ring 3"},
    {"tile": 0x72, "row": 2, "col": 39, "name": "Map 2 : Keyhole 1"},
    {"tile": 0x6F, "row": 7, "col": 44, "name": "Map 2 : Ring 4"},
    {"tile": 0x62, "row": 3, "col": 55, "name": "Map 2 : Treasure Box 2"},
    {"tile": 0x72, "row": 10, "col": 59, "name": "Map 2 : Keyhole 2"}
    {"tile": 0x00, "row": 0x60, "col": 0x50, "name": "Map 1 : Teleport 1 (Top)"},
    {"tile": 0x00, "row": 0x60, "col": 0x10, "name": "Map 1 : Teleport 1 (Bottom)"},
    {"tile": 0x00, "row": 0xC0, "col": 0x48, "name": "Map 1 : Teleport 2 (Top)"},
    {"tile": 0x00, "row": 0xC0, "col": 0x10, "name": "Map 1 : Teleport 2 (Bottom)"},
    {"tile": 0x00, "row": 0x1000, "col": 0x50, "name": "Map 1 : Teleport 2 (Top)"},
    {"tile": 0x00, "row": 0x1000, "col": 0x08, "name": "Map 1 : Teleport 2 (Bottom)"},
]

# Load the ROM
with open("m1.1h", "rb") as f:
    rom_data = f.read()

print(f"ROM size: {len(rom_data)} bytes\n")

# For each object, find where its tile index appears
for obj in objects:
    tile = obj["tile"]
    row = obj["row"]
    col = obj["col"]
    
    print(f"\n{'='*60}")
    print(f"Searching for {obj['name']}: tile 0x{tile:02X} at (row={row}, col={col})")
    print(f"{'='*60}")
    
    # Find all occurrences of this tile index
    positions = [i for i in range(len(rom_data)) if rom_data[i] == tile]
    
    print(f"Found {len(positions)} occurrences of byte 0x{tile:02X}")
    
    for pos in positions:
        # Show surrounding bytes (14 bytes before, the tile byte, 14 bytes after)
        start = max(0, pos - 14)
        end = min(len(rom_data), pos + 15)
        context = rom_data[start:end]
        
        print(f"\nOffset 0x{pos:04X}:")
        print(f"  Hex: {context.hex(' ')}")
        
        # Try to extract potential coordinate pairs before the tile index
        if pos >= 2:
            byte1 = rom_data[pos-2]
            byte2 = rom_data[pos-1]
            print(f"  2 bytes before: 0x{byte1:02X} 0x{byte2:02X} = ({byte1}, {byte2})")
            
        if pos >= 7:
            # Check for coordinates 5-6 bytes before
            byte1 = rom_data[pos-7]
            byte2 = rom_data[pos-6]
            print(f"  7-6 bytes before: 0x{byte1:02X} 0x{byte2:02X} = ({byte1}, {byte2})")
            
        if pos >= 9:
            # Check for coordinates 8-9 bytes before  
            byte1 = rom_data[pos-9]
            byte2 = rom_data[pos-8]
            print(f"  9-8 bytes before: 0x{byte1:02X} 0x{byte2:02X} = ({byte1}, {byte2})")

print("\n" + "="*60)
print("Analysis complete. Look for patterns in the byte pairs above.")