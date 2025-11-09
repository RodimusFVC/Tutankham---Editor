import struct

# Known object positions
objects = [
#Map 1
    {"tile": 0x62, "row": 10, "col": 8, "name": "treasure box"},
    {"tile": 0x70, "row": 2, "col": 16, "name": "key"},
    {"tile": 0x6F, "row": 8, "col": 30, "name": "ring 1"},
    {"tile": 0x6F, "row": 9, "col": 22, "name": "ring 2"},
    {"tile": 0x72, "row": 10, "col": 27, "name": "keyhole"},
#Map 2
    {"tile": 0x6F, "row": 8, "col": 14, "name": "ring 1"},
    {"tile": 0x62, "row": 3, "col": 19, "name": "treasure box 1"},
    {"tile": 0x70, "row": 2, "col": 21, "name": "key 1"},
    {"tile": 0x6F, "row": 8, "col": 28, "name": "ring 2"},
    {"tile": 0x70, "row": 11, "col": 31, "name": "key 1"},
    {"tile": 0x6F, "row": 4, "col": 35, "name": "ring 3"},
    {"tile": 0x72, "row": 2, "col": 39, "name": "keyhole 1"},
    {"tile": 0x6F, "row": 7, "col": 44, "name": "ring 4"},
    {"tile": 0x62, "row": 3, "col": 55, "name": "treasure box 2"},
    {"tile": 0x72, "row": 10, "col": 59, "name": "keyhole 2"}
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