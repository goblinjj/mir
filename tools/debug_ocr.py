"""Test OCR monster name detection on a screenshot.

Usage:
    python tools/test_ocr.py                          # use tools/screenshot.png
    python tools/test_ocr.py path/to/screenshot.png   # use specified file
    python tools/test_ocr.py --save                   # save intermediate images
"""

import os
import sys
import argparse

# Must set before paddle imports
os.environ["FLAGS_use_mkldnn"] = "0"

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vision.ocr import MonsterDetector


def crop_game_viewport(frame, minimap_x=1230):
    """Replicate the bot's viewport cropping logic."""
    h, w = frame.shape[:2]
    right = min(minimap_x, w)
    bottom = int(h * 0.65)
    top = int(h * 0.03)
    return frame[top:bottom, 0:right], top


def main():
    parser = argparse.ArgumentParser(description="Test OCR monster detection")
    parser.add_argument("image", nargs="?", default="tools/screenshot.png",
                        help="Path to screenshot image")
    parser.add_argument("--save", action="store_true",
                        help="Save intermediate images for debugging")
    parser.add_argument("--no-crop", action="store_true",
                        help="Skip viewport cropping")
    args = parser.parse_args()

    # Load image
    frame = cv2.imread(args.image)
    if frame is None:
        print(f"Error: cannot load image: {args.image}")
        sys.exit(1)
    print(f"Loaded: {args.image} ({frame.shape[1]}x{frame.shape[0]})")

    # Crop viewport
    if not args.no_crop:
        viewport, y_offset = crop_game_viewport(frame)
        print(f"Viewport: {viewport.shape[1]}x{viewport.shape[0]} (y_offset={y_offset})")
    else:
        viewport = frame
        y_offset = 0

    # Preprocess
    processed = MonsterDetector.preprocess_frame(viewport)
    print(f"Preprocessed: {processed.shape[1]}x{processed.shape[0]}")

    # Init detector and run OCR
    print("\nInitializing PaddleOCR...")
    detector = MonsterDetector()

    print("Running detection...")
    monsters = detector.detect(viewport)

    # Print results
    print(f"\n{'='*50}")
    print(f"Detected {len(monsters)} monsters:")
    for m in monsters:
        mtype = detector.classify(m.name)
        print(f"  [{mtype:6s}] {m.name} at ({m.x}, {m.y + y_offset}) conf={m.confidence:.2f}")

    if not monsters:
        print("  (none)")

    # Also run raw OCR on preprocessed image to show all text
    print(f"\n{'='*50}")
    print("All OCR text (including non-monster):")
    try:
        results = detector.ocr_engine.ocr(processed, cls=False)
        if results and results[0]:
            for line in results[0]:
                bbox, (text, conf) = line
                print(f"  '{text.strip()}' conf={conf:.2f}")
        else:
            print("  (no text detected)")
    except Exception as e:
        print(f"  Error: {e}")

    # Save debug images
    if args.save:
        out_dir = os.path.dirname(args.image) or "."

        cv2.imwrite(os.path.join(out_dir, "ocr_viewport.png"), viewport)
        cv2.imwrite(os.path.join(out_dir, "ocr_processed.png"), processed)

        # Draw detection boxes on viewport
        annotated = viewport.copy()
        for m in monsters:
            cv2.circle(annotated, (m.x, m.y), 5, (0, 255, 0), -1)
            cv2.putText(annotated, m.name, (m.x + 10, m.y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imwrite(os.path.join(out_dir, "ocr_annotated.png"), annotated)

        print(f"\nSaved: ocr_viewport.png, ocr_processed.png, ocr_annotated.png")


if __name__ == "__main__":
    main()
