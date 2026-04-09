# QR Code Art — Session Log & Development Journal
**Date:** 2026-04-09  
**Repo:** https://github.com/fladroid/qrcode-art  
**Live:** https://fladroid.github.io/qrcode-art  

---

## Project Goal

Create a tool that generates:
1. **Artistic QR codes** — a scannable QR code with a visible portrait or landmark image embedded inside
2. **Business card generator** — standard layout with photo left, QR right, contact info below
3. **Future:** CLI Python script with `--mode card/art` arguments and batch processing from CSV

---

## Infrastructure Setup

### Environment
- **Server:** Balsam (`/home/balsam/qrcode-art/`) — working directory
- **Python:** 3.12.3, no pip pre-installed
- **Solution:** Created Python `venv` to avoid `sudo` requirement
  ```bash
  python3 -m venv venv
  venv/bin/pip install qrcode pillow
  ```
- **GitHub:** SSH key authenticated as `fladroid`, repo `fladroid/qrcode-art`
- **Hosting:** GitHub Pages from `/docs` folder

### Project Structure
```
qrcode-art/
├── assets/          # Input images (portrait, silhouettes)
├── docs/            # GitHub Pages (index.html, card.html)
├── output/          # Generated QR codes (gitignored)
├── scripts/         # Python scripts
│   └── generate_art_qr.py
└── venv/            # Python virtual environment (gitignored)
```

---

## Key Concepts Learned

### QR Code Structure
- **Modules** — individual black/white squares (1 bit each)
- **Finder patterns** — 3 large corner squares, allow scanner to orient the code
- **Timing patterns** — alternating row/column 6, help determine module grid
- **Error Correction Levels:** L=7%, M=15%, Q=25%, H=30% damage tolerance
- **Version** — determines matrix size: Version 1=21×21, Version 40=177×177

### QR Code Version & Data
- More data → higher version → larger matrix → more pixels available for art
- Version is auto-selected based on data length
- **Trick:** Pad vCard with whitespace to force larger version (whitespace ignored by contact readers)

### Artistic QR Techniques
1. **Pixel blend** — replace individual modules with image pixels (limited by low resolution)
2. **Zone blend** — image in center zone only, QR wins on edges
3. **Floyd-Steinberg dithering** — error diffusion for better face detail at low resolution
4. **Multiply blend** — image as background layer, QR black modules on top (best for landmarks)
5. **Overlay approach** — image under QR, white modules transparent

---

## Development Journey — Problems & Solutions

### Stage 1: Basic QR Generation (Python)

**Goal:** Generate a QR code with a portrait blended in.

**Starting code had a critical bug:**
```python
# BUG: always True (never False) — image completely overwrites QR
if img_val < 128:
    new_matrix[y][x] = True if qr_val else True  # both branches = True!
else:
    new_matrix[y][x] = False if not qr_val else False  # both = False!
```

**Fix:** Proper blend logic — QR wins on conflict, image only shows where it agrees:
```python
if is_protected(x, y, size):
    new_matrix[y][x] = qr_val  # never touch structural zones
elif img_dark == qr_val:
    new_matrix[y][x] = qr_val  # agreement — image shows through
else:
    new_matrix[y][x] = qr_val  # conflict — QR wins
```

---

### Stage 2: Browser-Based Generator (JavaScript)

**Goal:** Move from Python script to client-side HTML/JS generator for GitHub Pages.

**Problem 1: qrcodejs library unreliable on Android**
- Library rendered QR to HTML table (DOM hack)
- Required `setTimeout(100ms)` to wait for render
- Failed on Android 16 — hung on "Generating matrix..."

**Solution:** Switched to `qrcode-generator` library (unpkg CDN):
```javascript
const qr = qrcode(0, 'H');
qr.addData(data);
qr.make();
// Direct matrix access — no DOM tricks needed
const dark = qr.isDark(y, x);
```

**Problem 2: Portrait not visible**
- QR-wins-always logic made image invisible
- 73×73 matrix = only ~33×33 pixels for face in center zone
- Too small for recognition

**Solution attempts:**
- V1f: Portrait-first blend (image wins) → QR became unreadable (black square result)
- V1g: Light pixels force white, dark defer to QR → partial improvement
- V1h: Zone-based blend (center 40% = portrait, outer = QR) → lace visible but not scannable
- V1j: Floyd-Steinberg dithering → best pixel-level result, but still not recognizable at small size

**Root cause:** 73×73 matrix too small for recognizable face.

---

### Stage 3: Forcing Larger QR Version

**Goal:** More pixels = more recognizable image.

**Solution:** Pad vCard data with whitespace to force larger matrix:
```javascript
const TARGET_LENGTH = 1200;
const padding = ' '.repeat(Math.max(0, TARGET_LENGTH - lines.length));
return vCardLines + padding;
```

**Result:** Matrix grew from 73×73 to 157×157 — 5× more pixels for image.

**New problem:** Portrait was still 73×73 pixels being scaled up — pixelated.

**Fix:** Resize portrait to exact matrix size in browser:
```javascript
ctx.imageSmoothingQuality = 'high';
ctx.drawImage(img, 0, 0, matrixSize, matrixSize);
```

---

### Stage 4: Multiply Blend Technique (Breakthrough)

**Goal:** Make image clearly visible while keeping QR 100% scannable.

**Insight:** Stop trying to merge image into QR matrix pixel-by-pixel.  
Instead: draw image as background, QR black modules on top.

**Technique — CSS multiply blend mode:**
- `multiply(black, anything) = black` → QR modules stay solid
- `multiply(white, grey) = grey` → silhouette tints white modules
- Image visible through white modules, QR readable from black modules

**Problem:** Portrait face on white background → wrong direction  
Face (dark) should be light, background (light) should be dark  
**Solution:** CSS `invert(100%)` filter on the image layer:
```javascript
silCtx.filter = `grayscale(100%) invert(100%) contrast(1.3) brightness(${threshold/140})`;
```

**Result:** Landmark/silhouette images work beautifully — Stephansdom test confirmed.

---

### Stage 5: Finder Pattern Protection

**Problem:** After multiply blend, finder patterns appeared as dotted/grey outlines instead of solid black squares → scanner failed.

**Attempts:**
- V2b: Redraw finder zones after blend → still grey (blend happened before redraw)
- V2c: Extended protected zones list (format info, timing) → still dotted

**Root cause:** Quiet zone (4-module border) not accounted for in coordinate calculations. Finder patterns start at module (0,0) but canvas pixel (0,0) includes the quiet zone offset.

**Final solution (V2d):** Completely different approach — draw image UNDER QR, not through it:
1. White background
2. Silhouette at 55% opacity (full canvas)
3. ONLY black QR modules drawn on top (white modules = transparent)
4. Quiet zone border wiped clean (pure white)
5. Black modules in quiet zone redrawn

```javascript
// Wipe quiet zone clean
ctx.fillStyle = '#fff';
ctx.fillRect(0, 0, CW, QUIET*BOX);         // top
ctx.fillRect(0, CW-QUIET*BOX, CW, QUIET*BOX); // bottom
ctx.fillRect(0, 0, QUIET*BOX, CW);         // left
ctx.fillRect(CW-QUIET*BOX, 0, QUIET*BOX, CW); // right
// Redraw black modules in quiet zone
for (let y = 0; y < size; y++)
  for (let x = 0; x < size; x++)
    if ((x<QUIET||x>=size-QUIET||y<QUIET||y>=size-QUIET) && matrix[y][x])
      ctx.fillRect(x*BOX, y*BOX, BOX, BOX);
```

---

### Stage 6: Portrait vs. Landmark

**Important finding:** The artistic QR technique works much better for:
- **Landmarks, buildings, skylines** — high contrast, strong silhouettes, recognizable outlines
- **Portraits** — require larger print size (plakat/poster), not practical on business card scale

**For business cards:** Use standard layout (photo left, clean QR right).  
**For posters (A3+):** Artistic QR with landmark image works excellently.

---

### Stage 7: Business Card Generator

**Layout:** 85×54mm @ 300 DPI = 1004×638px
```
┌─────────────────────────────────────┐
│              │                      │
│   PORTRAIT   │   [QR CODE]          │
│   (42% width,│   (clean, 100%       │
│   full height│    scannable)        │
│              │                      │
│              │  Full Name           │
│              │  Phone               │
│              │  Email               │
└─────────────────────────────────────┘
```

**Key implementation:**
- Portrait: `object-fit: cover` equivalent — crop to fill panel
- QR: sized to fit available area with margins
- Text: positioned below QR with enough gap (36px)
- Download: PNG ready for print shop at 300 DPI

---

### Stage 8: Unified Generator (V3a)

**Goal:** One page, one form, two outputs.

**Final UI flow:**
1. Enter: Name, Phone, Email
2. Upload: image (portrait for card, landmark for art)
3. Button: 💼 BUSINESS CARD → generates print-ready PNG
4. Button: 🎨 ART QR POSTER → generates artistic QR
5. Both results shown simultaneously with download buttons

---

## Version History

| Version | Description |
|---------|-------------|
| V1a | Basic generator, qrcodejs (unreliable) |
| V1b | Accessibility: larger font, higher contrast |
| V1e | Fixed: switched to qrcode-generator library |
| V1f | Portrait-first blend |
| V1g | Zone-based blend |
| V1j | Floyd-Steinberg dithering |
| V1k | Force version 40 via vCard padding |
| V1m | Dithering confined to center zone |
| V1n | Overlay: portrait as background layer |
| V2a | Poster mode: multiply blend + invert |
| V2b–V2d | Progressive fixes for finder pattern protection |
| V3a | **Unified generator: one form, two buttons** ✅ |

---

## Next Steps (Planned)

### CLI Python Script
```bash
python generate.py --mode card \
  --name "Flavio Flajs" \
  --phone "+436765091488" \
  --email "flavio.flajs@gmail.com" \
  --image portrait.jpg \
  --output business_card.png

python generate.py --mode art \
  --image stephansdom.jpg \
  --threshold 160 \
  --output art_qr.png
```

### Batch Processing from CSV
```bash
python generate.py --mode card --batch contacts.csv --output-dir ./cards/
```

CSV format:
```csv
name,phone,email,image
Flavio Flajs,+436765091488,flavio@gmail.com,flavio.jpg
Jane Doe,+1555000123,jane@example.com,jane.jpg
```

### Potential Improvements
- Adjustable card layout (portrait right, landscape orientation)
- Color QR codes (dark color on light background)
- Custom logo overlay in QR center (uses H-level tolerance)
- PDF export for direct print

---

## Technical References

- **qrcode-generator JS library:** https://unpkg.com/qrcode-generator@1.4.4/qrcode.js
- **Pillow (Python):** Image processing, multiply blend via `ImageChops.multiply()`
- **Floyd-Steinberg dithering:** Error diffusion algorithm for B&W conversion
- **Canvas multiply blend:** `ctx.globalCompositeOperation = 'multiply'`
- **vCard 3.0 spec:** Standard format for contact data in QR codes
- **QR Error Correction H:** 30% damage tolerance — maximum, used for all art QR

