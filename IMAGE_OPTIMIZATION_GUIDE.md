# Image Optimization Guide

## Current Status

### ✅ Completed
- **Favicon created** from nixvirlogo.png
  - `static/favicon.ico` (938 bytes)
  - `static/images/favicon-16x16.png` (921 bytes)
  - `static/images/favicon-32x32.png` (2.5 KB)
  - `static/images/apple-touch-icon.png` (21 KB)

### ⚠️ Requires Manual Optimization

**Large Image File:**
- **File**: `static/images/BoulderCOVID-031620.png`
- **Current Size**: 8.9 MB (4959×3294 pixels)
- **Target Size**: ~500 KB
- **Used In**: Archived COVID-19 post from 2020

## Manual Optimization Methods

### Option 1: Online Tools (Easiest)

1. **TinyPNG** (https://tinypng.com/)
   - Upload `BoulderCOVID-031620.png`
   - Download optimized version
   - Typically achieves 70-80% reduction

2. **Squoosh** (https://squoosh.app/)
   - Upload image
   - Resize to 1920px width
   - Export as JPEG quality 85
   - Expected: ~400-600 KB

### Option 2: Using GIMP (Free Software)

1. Download GIMP: https://www.gimp.org/
2. Open `BoulderCOVID-031620.png`
3. **Image → Scale Image**
   - Width: 1920 pixels
   - Keep aspect ratio checked
   - Quality: Cubic (best)
4. **File → Export As**
   - Format: JPEG
   - Quality: 85
   - Save as: `BoulderCOVID-031620.jpg`

### Option 3: Using ImageMagick (Command Line)

If you install ImageMagick (https://imagemagick.org/):

```bash
magick static/images/BoulderCOVID-031620.png -resize 1920x1080\> -quality 85 static/images/BoulderCOVID-031620.jpg
```

### Option 4: Using Python (if PIL/Pillow works)

```python
from PIL import Image

img = Image.open('static/images/BoulderCOVID-031620.png')
max_width = 1920
ratio = max_width / img.size[0]
new_size = (max_width, int(img.size[1] * ratio))
img = img.resize(new_size, Image.Resampling.LANCZOS)
img.save('static/images/BoulderCOVID-031620.jpg', 'JPEG', quality=85, optimize=True)
```

## After Optimization

### Update Content File

If you convert to JPEG, update the reference in the archived post:

**File**: `content/post-archive/` (check which file uses this image)

Change:
```markdown
![Description](/images/BoulderCOVID-031620.png)
```

To:
```markdown
![Description](/images/BoulderCOVID-031620.jpg)
```

### Clean Up

After confirming the optimized version works:

```bash
# Backup original (optional)
mv static/images/BoulderCOVID-031620.png static/images/BoulderCOVID-031620-original.png

# Or delete if backup not needed
rm static/images/BoulderCOVID-031620.png
```

## Other Large Images to Consider

| File | Size | Recommendation |
|------|------|----------------|
| COVID-19-and-Travel.png | 1.2 MB | Optimize to ~200 KB |
| snowman.jpg | 640 KB | Resize to 1920px wide (~150 KB) |
| gohugo-default-sample-hero-image.jpg | 384 KB | Already optimized (by JPEGmini) |

## Automated Hugo Image Processing

**Note**: The [config.toml](config.toml#L45-L48) now includes image optimization settings:

```toml
[imaging]
  quality = 85
  resampleFilter = "Lanczos"
```

However, this only works for images processed through Hugo's image processing pipeline (using Hugo's `image` shortcode or `resources.Get`). Static images in `/static/images/` are served as-is.

### To Use Hugo's Automatic Optimization

Move images to `/assets/images/` and reference them using:

```markdown
{{< figure src="/images/myimage.jpg" >}}
```

Instead of:

```markdown
![Alt text](/images/myimage.jpg)
```

## Quick Reference

**Recommended Dimensions for Web:**
- Hero images: 1920×1080 (Full HD)
- Blog post images: 1200×800
- Thumbnails: 400×300
- Icons/logos: 200×200

**Recommended Formats:**
- Photos: JPEG (quality 80-90)
- Graphics/logos: PNG or WebP
- Icons: SVG (if possible)

**Recommended File Sizes:**
- Hero images: < 500 KB
- Blog images: < 200 KB
- Thumbnails: < 50 KB

## Troubleshooting

**Issue**: Automated scripts can't process BoulderCOVID image
- **Cause**: Possible file corruption or unusual PNG encoding
- **Solution**: Use online tools (TinyPNG or Squoosh) which are more robust

**Issue**: Image quality loss after optimization
- **Solution**: Increase quality setting (85 → 90) or reduce resize amount

---

**Status**: Favicon complete ✅ | Large image pending manual optimization ⚠️
