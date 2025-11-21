with open("m2.2h", "rb") as f:
    rom_data = f.read()

print("Searching for keyhole (0x72) in Map 1 section (0x000-0x520):")
for i in range(0x000, 0x520):
    if rom_data[i] == 0x72:
        if i >= 9:
            byte_pair = (rom_data[i-9], rom_data[i-8])
            # Check if second byte is 72 (0-based row 9) or 80 (1-based row 10)
            if byte_pair[1] in [0x48, 0x50]:
                print(f"  Offset 0x{i:03X}: {byte_pair[0]:02X} {byte_pair[1]:02X} ({byte_pair[0]}, {byte_pair[1]})")