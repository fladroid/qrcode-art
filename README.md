# QR Code Art

Artistic QR code generator that blends a portrait photo with a scannable vCard QR code.

## Technique
- Error correction level **H** (30% damage tolerance)
- Portrait converted to coarse B&W, blended where it agrees with QR data modules
- Structural zones (finder/timing patterns) are always preserved
- Output sized for business card printing

## Usage
```bash
python3 -m venv venv
venv/bin/pip install qrcode pillow
venv/bin/python scripts/generate_art_qr.py
```

## Project structure
```
qrcode-art/
├── assets/        # Input images (portrait.png)
├── output/        # Generated QR codes
├── scripts/       # Python scripts
└── README.md
```
