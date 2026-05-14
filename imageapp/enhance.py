import cv2
import torch
import os
import gc
import numpy as np
from django.conf import settings
from gfpgan import GFPGANer
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet


def resize_to_512(img):
    """Resize image to 512x512 with aspect ratio preserved (padding)."""
    h, w = img.shape[:2]

    scale = min(512 / w, 512 / h)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(img, (new_w, new_h))

    canvas = np.zeros((512, 512, 3), dtype=np.uint8)

    x_offset = (512 - new_w) // 2
    y_offset = (512 - new_h) // 2

    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

    return canvas


def enhance_image(input_path, output_path):
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    BASE_DIR = settings.BASE_DIR
    MODEL_DIR = os.path.join(BASE_DIR, "models")

    # =========================
    # STEP 0 — Read + Resize
    # =========================
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError("Image not found")

    # ✅ Always convert to 512x512 (safe for memory)
    img = resize_to_512(img)

    try:
        # =========================
        # STEP 1 — GFPGAN
        # =========================
        face_enhancer = GFPGANer(
            model_path=os.path.join(MODEL_DIR, "GFPGANv1.4.pth"),
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
            device=DEVICE
        )

        _, _, face_restored = face_enhancer.enhance(
            img,
            has_aligned=False,
            only_center_face=False,
            paste_back=True,
            weight=0.9
        )

        # =========================
        # STEP 2 — Real-ESRGAN
        # =========================
        rrdbnet = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=4
        )

        upsampler = RealESRGANer(
            scale=4,
            model_path=os.path.join(MODEL_DIR, "RealESRGAN_x4plus.pth"),
            model=rrdbnet,
            tile=0,         
            tile_pad=10,
            pre_pad=0,
            half=True,
            device=DEVICE
        )

        final_img, _ = upsampler.enhance(face_restored, outscale=4)

        # =========================
        # Save Output
        # =========================
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, final_img)

        return output_path

    finally:
        # =========================
        # Cleanup (IMPORTANT)
        # =========================
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()