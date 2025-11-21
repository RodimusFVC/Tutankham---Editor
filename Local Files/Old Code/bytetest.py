def search_bytes(filename, target):
    with open(filename, "rb") as f:
        data = f.read()

    target = bytes([target])  # ensure single byte
    results = []
    for i in range(len(data)):
        if data[i:i+1] == target:
            start = max(0, i - 3)
            end = min(len(data), i + 4)  # +4 because slice end is exclusive
            snippet = data[start:end]
            results.append((i, snippet))
    return results


# Example usage:
filename = "./c8.8i"
target_hex = 0x70  # the value to search
matches = search_bytes(filename, target_hex)

for index, snippet in matches:
    print(f"Found at offset {index}: ", " ".join(f"{b:02X}" for b in snippet))
