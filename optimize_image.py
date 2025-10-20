#!/usr/bin/env python3
"""
Optimize BoulderCOVID image from 8.9 MB to ~500 KB
"""
from PIL import Image
import os

# Input and output paths
input_path = "static/images/BoulderCOVID-031620.png"
output_path = "static/images/BoulderCOVID-031620-optimized.jpg"
backup_path = "static/images/BoulderCOVID-031620-original.png"

try:
    # Open the image
    print(f"Opening {input_path}...")
    img = Image.open(input_path)

    # Get original size
    original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
    print(f"Original size: {original_size:.2f} MB")
    print(f"Original dimensions: {img.size[0]}x{img.size[1]} pixels")

    # Resize to reasonable web size (max 1920px wide)
    max_width = 1920
    if img.size[0] > max_width:
        ratio = max_width / img.size[0]
        new_size = (max_width, int(img.size[1] * ratio))
        print(f"Resizing to: {new_size[0]}x{new_size[1]} pixels")
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Convert RGBA to RGB if needed (for JPEG)
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background

    # Save as optimized JPEG
    print(f"Saving optimized version to {output_path}...")
    img.save(output_path, 'JPEG', quality=85, optimize=True)

    # Get new size
    new_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    reduction = ((original_size - new_size) / original_size) * 100

    print(f"\nOptimization complete!")
    print(f"New size: {new_size:.2f} MB")
    print(f"Reduction: {reduction:.1f}%")

    # Backup original
    if not os.path.exists(backup_path):
        os.rename(input_path, backup_path)
        os.rename(output_path, input_path.replace('.png', '.jpg'))
        print(f"\nOriginal backed up to: {backup_path}")
        print(f"Optimized version saved as: {input_path.replace('.png', '.jpg')}")
    else:
        print(f"\nOptimized version saved as: {output_path}")
        print(f"To replace original, manually rename files")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
