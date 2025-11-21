#!/usr/bin/env python3
"""
M6809 Checksum - Konami (j6.6h) & Stern (a6.6h) Support
Validated: j6.6h @ 0x5C0 → 0x14A3, a6.6h @ 0x5C0 → 0x1A4C
"""

import sys
import argparse
import os
import hashlib

# If x6.6h rom is edited for the copyright symbol between 0x5C0+66 - Updated Checksum must be written to x3.3h ROM at 0xE25/0xE26

def calculate_m6809_checksum(rom_data, base_addr=0x5C0, byte_count=0x66):
    """Exact M6809 checksum emulation"""
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

def main():
    parser = argparse.ArgumentParser(
        description="M6809 Checksum for Konami/Stern ROMs",
        epilog="""
VALIDATED:
- Konami j6.6h @ 0x5C0 → 0x14A3 (MD5: 347fa9be8a139b097de5ae12162c1501)
- Stern a6.6h @ 0x5C0 → 0x1A4C (MD5: 651827924404392035e93ce6db9b2c4f)
ROMs load at 0xC000, checksum 102 bytes
        """
    )
    parser.add_argument("rom_file", help="Input ROM file (j6.6h or a6.6h)")
    parser.add_argument("-o", "--offset", type=lambda x: int(x, 0), 
                       default=0x5C0, help="File offset (default: 0x5C0)")
    parser.add_argument("-c", "--count", type=lambda x: int(x, 0), 
                       default=0x66, help="Byte count (default: 0x66)")
    parser.add_argument("-e", "--expected", type=lambda x: int(x, 0), 
                       default=None, help="Expected checksum (default: auto-detect)")
    parser.add_argument("--dump", action="store_true", help="Dump 102 bytes")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.rom_file):
        print(f"ERROR: '{args.rom_file}' not found!")
        sys.exit(1)
    
    try:
        with open(args.rom_file, 'rb') as f:
            rom_data = bytearray(f.read())
        
        rom_size = len(rom_data)
        end_addr = args.offset + args.count
        
        if end_addr > rom_size:
            print(f"ERROR: Range 0x{args.offset:04X}-{end_addr-1:04X} exceeds {rom_size}!")
            sys.exit(1)
        
        # Auto-detect ROM type by MD5
        md5_hash = hashlib.md5(rom_data).hexdigest()
        if md5_hash == "347fa9be8a139b097de5ae12162c1501":
            rom_type = "Konami j6.6h"
            default_expected = 0x14A3
        elif md5_hash == "651827924404392035e93ce6db9b2c4f":
            rom_type = "Stern a6.6h"
            default_expected = 0x1A4C
        else:
            rom_type = "Unknown"
            default_expected = None
        
        expected = args.expected if args.expected is not None else default_expected
        
        print(f"\n=== M6809 Checksum ===")
        print(f"ROM: {args.rom_file} ({rom_size} bytes)")
        print(f"Type: {rom_type}")
        print(f"MD5: {md5_hash}")
        print(f"Memory: 0x{args.offset+0xC000:04X} - 0x{end_addr-1+0xC000:04X}")
        print(f"File:   0x{args.offset:04X} - 0x{end_addr-1:04X}")
        
        if args.dump:
            print(f"\nBYTES @ 0x{args.offset:04X}:")
            for i in range(0, args.count, 16):
                line = [f"{rom_data[args.offset+j]:02X}" for j in range(16) 
                       if args.offset+j < rom_size]
                print(" ".join(line))
        
        checksum = calculate_m6809_checksum(rom_data, args.offset, args.count)
        
        print(f"\n=== RESULTS ===")
        print(f"Checksum: 0x{checksum:04X} ({checksum})")
        print(f"Expected: 0x{expected:04X} ({expected})" if expected is not None else "Expected: Unknown")
        print(f"Status:   {'✓ PASS' if expected is not None and checksum == expected else '✗ FAIL'}")
        
        if rom_type != "Unknown" and checksum == expected:
            print(f"\n🎮 VALID {rom_type} ROM! Ready for hacking!")
        
        sys.exit(0 if expected is not None and checksum == expected else 1)
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()