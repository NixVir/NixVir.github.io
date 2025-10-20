#!/usr/bin/env python3
"""
Create favicon from NixVir logo
"""
from PIL import Image
import os

# Input and output paths
input_path = "static/images/nixvirlogo.png"
output_ico = "static/favicon.ico"
output_16 = "static/images/favicon-16x16.png"
output_32 = "static/images/favicon-32x32.png"
output_apple = "static/images/apple-touch-icon.png"

try:
    # Open the logo
    print(f"Opening {input_path}...")
    img = Image.open(input_path)
    print(f"Original size: {img.size[0]}x{img.size[1]} pixels")

    # Create different sizes
    sizes = [
        (16, 16, output_16, "16x16 favicon"),
        (32, 32, output_32, "32x32 favicon"),
        (180, 180, output_apple, "Apple touch icon"),
    ]

    images = []
    for width, height, path, desc in sizes:
        print(f"Creating {desc}...")
        resized = img.resize((width, height), Image.Resampling.LANCZOS)
        resized.save(path, 'PNG', optimize=True)
        print(f"  Saved: {path}")

        # Collect for ICO file (16 and 32 only)
        if width in [16, 32]:
            images.append(resized)

    # Create multi-size ICO file
    print(f"Creating {output_ico}...")
    images[0].save(output_ico, format='ICO', sizes=[(16, 16), (32, 32)])
    print(f"  Saved: {output_ico}")

    print("\n✓ Favicon creation complete!")
    print(f"\nFiles created:")
    print(f"  - {output_ico} (multi-size .ico)")
    print(f"  - {output_16} (16x16 PNG)")
    print(f"  - {output_32} (32x32 PNG)")
    print(f"  - {output_apple} (180x180 Apple touch icon)")

    print(f"\nUpdate config.toml:")
    print(f'  favicon = "/favicon.ico"')

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
