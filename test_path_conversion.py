#!/usr/bin/env python3
import os

def convert_path_for_current_os(snapshot_path):
    """Test function để chuyển đổi đường dẫn"""
    converted_snapshot_path = snapshot_path
    if snapshot_path:
        if snapshot_path.startswith('/mnt/'):
            # WSL path → Windows path
            parts = snapshot_path.split('/')
            if len(parts) >= 3:
                drive_letter = parts[2].upper()
                converted_snapshot_path = f"{drive_letter}:\\" + "\\".join(parts[3:])
                print(f"Converted WSL path {snapshot_path} to Windows path {converted_snapshot_path}")
        elif len(snapshot_path) > 3 and snapshot_path[1:3] == ':\\':
            # Windows path → WSL path
            drive_letter = snapshot_path[0].lower()
            wsl_path = f"/mnt/{drive_letter}/" + snapshot_path[3:].replace('\\', '/')
            converted_snapshot_path = wsl_path
            print(f"Converted Windows path {snapshot_path} to WSL path {converted_snapshot_path}")
    return converted_snapshot_path

# Test cases
test_paths = [
    "E:\\Docs\\Pplaptrinh\\video_surveillance_system\\data\\snapshots\\snapshot_video_video2_20250701_114432_129.jpg",
    "/mnt/e/Docs/Pplaptrinh/video_surveillance_system/data/snapshots/snapshot_video_video2_20250701_114432_129.jpg",
    "data/snapshots/test.jpg"
]

print("=== TESTING PATH CONVERSION ===")
for path in test_paths:
    print(f"\nOriginal: {path}")
    converted = convert_path_for_current_os(path)
    print(f"Converted: {converted}")
    print(f"File exists: {os.path.exists(converted)}")
    print("-" * 50) 