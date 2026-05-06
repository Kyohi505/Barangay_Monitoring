import cv2
import numpy as np
from PIL import Image
from PIL import ImageOps
import easyocr
import re
from io import BytesIO

from pillow_heif import register_heif_opener
register_heif_opener()

print("\nLoading EasyOCR reader...")
reader = easyocr.Reader(['en'], gpu=False, verbose=False)
print("EasyOCR ready!\n")

def detect_validation_number_smart(image_bytes: bytes):
    """
    Detect ONLY the red handwritten validation number
    Filters by: RED color + TOP position + LARGE SIZE + DIGIT ONLY
    """
    
    # Load image
    image_pil = Image.open(BytesIO(image_bytes))
    image_pil = ImageOps.exif_transpose(image_pil)
    max_size = 1920
    if image_pil.width > max_size or image_pil.height > max_size:
        image_pil.thumbnail((max_size, max_size))
        
    cv_image = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    H, W = cv_image.shape[:2]
    
    print(f"Image size: {W}x{H}")
    
    # ======================================================================
    # STEP 1: Find RED colored regions
    # ======================================================================
    print("\nStep 1: Detecting RED regions...")
    
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
    
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask_red1, mask_red2)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    red_mask = cv2.dilate(red_mask, kernel, iterations=2)
    
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    red_regions = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 100:
            x, y, w, h = cv2.boundingRect(contour)
            red_regions.append((x, y, w, h, area))
    
    print(f"Found {len(red_regions)} red regions")
    
    # ======================================================================
    # STEP 2: Run EasyOCR
    # ======================================================================
    print("\nStep 2: Running EasyOCR...")
    
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    results = reader.readtext(enhanced, detail=1)
    print(f"EasyOCR found {len(results)} text regions total")
    
    # ======================================================================
    # STEP 3: Filter by RED + SIZE + POSITION (TOP)
    # ======================================================================
    print("\nStep 3: Filtering by RED + LARGE SIZE + TOP position...")
    
    filtered_results = []
    
    for bbox, text, confidence in results:
        if isinstance(bbox, list) and len(bbox) >= 4:
            pts = np.array(bbox, dtype=np.int32)
            x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
            y_min, y_max = pts[:, 1].min(), pts[:, 1].max()
        else:
            continue
        
        text_width = x_max - x_min
        text_height = y_max - y_min
        text_area = text_width * text_height
        
        # Check if RED
        is_red = False
        for rx, ry, rw, rh, _ in red_regions:
            if not (x_max < rx or x_min > rx + rw or y_max < ry or y_min > ry + rh):
                is_red = True
                break
        
        if not is_red:
            continue
        
        # Check if LARGE (validation number should be big - at least 0.3% of image)
        min_size = (H * W) * 0.003
        if text_area < min_size:
            print(f"  ✗ '{text}' - RED but TOO SMALL (area: {text_area:.0f} < {min_size:.0f})")
            continue
        
        # Check if TOP (validation number should be in upper portion, any horizontal position)
        is_top = y_min < H * 0.4  # Upper 40% of image
        
        # Check if digit-only or mostly digit
        is_digit = bool(re.search(r'\d', text))
        
        if not is_digit:
            print(f"  ✗ '{text}' - RED + LARGE but NO DIGITS")
            continue
        
        if is_top:
            print(f"  ✓ '{text}' (conf: {confidence:.1%}, area: {text_area:.0f}) - RED + LARGE + TOP + DIGIT")
            filtered_results.append((text, confidence, x_min, y_min, text_area))
        else:
            print(f"  ✗ '{text}' - RED + LARGE + DIGIT but not TOP (pos: {x_min},{y_min})")
    
    print(f"\nFiltered down to {len(filtered_results)} candidates")
    
    if not filtered_results:
        return {
            "status": "failed",
            "error": "No validation number found (must be: RED + LARGE + TOP + DIGIT)",
            "detected_number": None,
        }
    
    # ======================================================================
    # STEP 4: Extract the single digit
    # ======================================================================
    print("\nStep 4: Extracting validation digit...")
    
    # Sort by area (largest first - that's the main digit)
    filtered_results.sort(key=lambda x: x[4], reverse=True)
    
    # Take the largest one
    best_text, best_conf, _, _, _ = filtered_results[0]
    digits = re.sub(r"[^0-9]", "", best_text)
    
    # Take only first digit (validation number is 1-3 digits, but using first one found)
    if len(digits) > 1:
        # If multiple digits, take just the first one
        detected_number = digits[0]
        print(f"  Found '{digits}' but taking first digit: '{detected_number}'")
    else:
        detected_number = digits
        print(f"  Found validation digit: '{detected_number}'")
    
    return {
        "status": "success",
        "detected_number": detected_number,
        "confidence": best_conf,
    }