from rembg import remove, new_session
from PIL import Image
import numpy as np
import cv2
import os

# ================= SESSION CACHE =================
SESSION_CACHE = {}

VALID_MODELS = [
    "u2net",
    "u2netp",
    "u2net_human_seg",
    "isnet-general-use",
    "isnet-anime"
]


def get_session(model_name):
    if model_name not in VALID_MODELS:
        print(f"⚠️ Invalid model '{model_name}', fallback to 'u2net'")
        model_name = "u2net"

    if model_name not in SESSION_CACHE:
        print(f" Loading model: {model_name}")
        SESSION_CACHE[model_name] = new_session(model_name)

    return SESSION_CACHE[model_name]


# ================= RESIZE =================
def resize_if_needed(img, max_size=2048):
    width, height = img.size

    if max(width, height) <= max_size:
        return img, 1.0

    scale = max_size / max(width, height)
    new_size = (int(width * scale), int(height * scale))

    print(f" Resizing: {img.size} → {new_size}")
    return img.resize(new_size, Image.LANCZOS), scale


# ================= MAIN FUNCTION =================
def remove_background(input_image,
                      output_path=None,   # ✅ FIXED
                      model_name="u2net",
                      alpha_matting=False,
                      post_process=True,
                      max_size=2048):

    # -------- Load Image --------
    if isinstance(input_image, str):
        img = Image.open(input_image).convert("RGB")
    elif isinstance(input_image, np.ndarray):
        img = Image.fromarray(cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB))
    elif isinstance(input_image, Image.Image):
        img = input_image.convert("RGB")
    else:
        raise ValueError("Invalid input type")

    original_size = img.size

    # -------- Resize --------
    img_processed, scale = resize_if_needed(img, max_size)

    # -------- Session --------
    session = get_session(model_name)

    # -------- Remove BG --------
    try:
        if alpha_matting:
            result = remove(
                img_processed,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10
            )
        else:
            result = remove(img_processed, session=session)

    except Exception as e:
        print(f" Error: {e}")
        print(" Fallback to default remove()")
        result = remove(img_processed)

    # -------- Resize Back --------
    if scale != 1.0:
        result = result.resize(original_size, Image.LANCZOS)

    # -------- Post Process --------
    if post_process:
        result = clean_edges(result)

    # -------- Save Output (IMPORTANT FIX) --------
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_transparent(result, output_path)

    return result


# ================= EDGE CLEANING =================
def clean_edges(rgba_image, edge_blur=1):
    img = np.array(rgba_image)

    rgb = img[:, :, :3]
    alpha = img[:, :, 3]

    if edge_blur > 0:
        alpha = cv2.GaussianBlur(alpha, (edge_blur * 2 + 1, edge_blur * 2 + 1), 0)

    alpha = np.where(alpha < 10, 0, alpha)
    alpha = np.where(alpha > 245, 255, alpha)

    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def save_transparent(image, output_path):
    ext = os.path.splitext(output_path)[1].lower()

    # ---------------- PNG ----------------
    if ext == ".png":
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image.save(output_path, "PNG")

    # ---------------- WEBP ----------------
    elif ext == ".webp":
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image.save(output_path, "WEBP", lossless=True)

    # ---------------- JPG (FIXED) ----------------
    elif ext in [".jpg", ".jpeg"]:
        # Convert RGBA → RGB with white background
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))  # white bg
            background.paste(image, mask=image.split()[3])  # use alpha as mask
            image = background
        else:
            image = image.convert("RGB")

        image.save(output_path, "JPEG", quality=95)

    # ---------------- TIFF ----------------
    elif ext in [".tif", ".tiff"]:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image.save(output_path, "TIFF")

    # ---------------- DEFAULT ----------------
    else:
        output_path += ".png"
        image = image.convert("RGBA")
        image.save(output_path, "PNG")

    print(f" Saved: {output_path}")
    return output_path