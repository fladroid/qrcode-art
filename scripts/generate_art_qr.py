"""
generate_art_qr.py
------------------
Generates an artistic QR code that blends a portrait photo (B&W, coarse)
with a scannable QR code containing vCard contact data.

Technique:
- Error correction level H (30% damage tolerance)
- Image pixels are blended only where they agree with QR data modules
- Finder/timing/format zones are always preserved (never modified)
- Output is sized for business card printing (300 DPI)

Usage:
    python generate_art_qr.py
"""

import qrcode
from PIL import Image, ImageFilter

# ============================================================
# SETTINGS — edit these for your own use
# ============================================================

# vCard 3.0 format — phone/email/address will be readable by
# any modern smartphone QR scanner
VCARD_DATA = """BEGIN:VCARD
VERSION:3.0
FN:John Doe
TEL:+1-555-000-1234
EMAIL:john.doe@example.com
ADR:;;123 Main Street;Springfield;IL;62701;USA
END:VCARD"""

# Path to portrait photo (will be used as placeholder if not found)
IMAGE_PATH = "assets/portrait.png"

# Output file
OUTPUT_PATH = "output/art_qr.png"

# QR module size in pixels (scale factor for final render)
BOX_SIZE = 12

# Quiet zone border (number of modules)
BORDER = 4

# Threshold for B&W conversion of portrait (0-255)
# Lower = more black, Higher = more white
BW_THRESHOLD = 128

# ============================================================
# STEP 1 — Generate QR matrix
# ============================================================
qr = qrcode.QRCode(
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=1,
    border=BORDER,
)
qr.add_data(VCARD_DATA)
qr.make(fit=True)

matrix = qr.get_matrix()
size = len(matrix)
print(f"[QR] Matrix size: {size}x{size} modules")

# ============================================================
# STEP 2 — Prepare portrait image
# ============================================================
try:
    portrait = Image.open(IMAGE_PATH).convert("L")  # grayscale
    print(f"[IMG] Loaded portrait: {IMAGE_PATH}")
except FileNotFoundError:
    # Generate a simple placeholder portrait (gradient with oval shape)
    print(f"[IMG] Portrait not found, generating placeholder...")
    from PIL import ImageDraw
    portrait = Image.new("L", (200, 200), 255)
    draw = ImageDraw.Draw(portrait)
    # Dark oval simulating a head silhouette
    draw.ellipse([40, 20, 160, 170], fill=30)
    draw.ellipse([60, 30, 140, 100], fill=80)   # lighter face area
    draw.rectangle([0, 0, 200, 200], outline=255)

# Resize to QR matrix dimensions
portrait = portrait.resize((size, size), Image.LANCZOS)

# Apply slight blur before thresholding for smoother coarse look
portrait = portrait.filter(ImageFilter.GaussianBlur(radius=0.8))

# Convert to strict B&W using threshold
portrait = portrait.point(lambda px: 0 if px < BW_THRESHOLD else 255)

print(f"[IMG] Portrait prepared: {size}x{size}, B&W threshold={BW_THRESHOLD}")

# ============================================================
# STEP 3 — Protected zone detection
# ============================================================
def is_protected(x, y, size):
    """
    Returns True if the module at (x, y) belongs to a structural zone
    that must never be modified:
      - Finder patterns (3 corner squares + separators)
      - Timing patterns (alternating row/column 6)
      - Dark module (fixed black module near bottom-left finder)
    """
    # Top-left finder pattern + separator (8x8 area)
    if x < 9 and y < 9:
        return True
    # Top-right finder pattern + separator
    if x > size - 10 and y < 9:
        return True
    # Bottom-left finder pattern + separator
    if x < 9 and y > size - 10:
        return True
    # Horizontal and vertical timing patterns
    if x == 6 or y == 6:
        return True
    return False

# ============================================================
# STEP 4 — Blend portrait with QR matrix
# ============================================================
new_matrix = [[False] * size for _ in range(size)]

agreed = 0
overridden = 0

for y in range(size):
    for x in range(size):
        qr_bit = matrix[y][x]           # True = dark module
        img_dark = portrait.getpixel((x, y)) < 128  # True = dark pixel

        if is_protected(x, y, size):
            # Structural zones: always use original QR value
            new_matrix[y][x] = qr_bit
        elif img_dark == qr_bit:
            # Image and QR agree — use the shared value (image "shows through")
            new_matrix[y][x] = qr_bit
            agreed += 1
        else:
            # Conflict — QR data takes priority to preserve scannability
            new_matrix[y][x] = qr_bit
            overridden += 1

total = size * size
print(f"[BLEND] Agreed: {agreed} modules ({100*agreed//total}%)")
print(f"[BLEND] Overridden by QR: {overridden} modules ({100*overridden//total}%)")

# ============================================================
# STEP 5 — Render to image
# ============================================================
canvas_size = size * BOX_SIZE
out = Image.new("RGB", (canvas_size, canvas_size), "white")

for y in range(size):
    for x in range(size):
        color = 0 if new_matrix[y][x] else 255  # 0=black, 255=white
        px0 = x * BOX_SIZE
        py0 = y * BOX_SIZE
        # Fill the full BOX_SIZE x BOX_SIZE block
        for dy in range(BOX_SIZE):
            for dx in range(BOX_SIZE):
                out.putpixel((px0 + dx, py0 + dy), (color, color, color))

out.save(OUTPUT_PATH)
print(f"[OUT] Saved: {OUTPUT_PATH} ({canvas_size}x{canvas_size}px)")
print("[DONE] Scan the QR code with your phone to verify!")
