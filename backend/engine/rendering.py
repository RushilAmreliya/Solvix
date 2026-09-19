"""
NowCast Fusion — Map Rendering Utilities

Converts NumPy precipitation / hazard arrays into transparent PNG images
encoded as base64 data-URIs for embedding in the API response.
Extracted from main.py to keep rendering concerns separate from API logic.
"""
import base64
import io

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from backend.engine.terrain_downscale import downscale_to_1km


def array_to_base64_img(
    arr:        np.ndarray,
    cmap_name:  str            = "jet",
    vmax:       float          = 20.0,
    threshold:  float          = 0.5,
    srtm:       np.ndarray | None = None,
) -> str:
    """
    Convert a 2-D precipitation or hazard array to a smooth transparent PNG
    encoded as a base64 data-URI string suitable for direct use in an
    HTML <img> src or Leaflet ImageOverlay.

    Args:
        arr:       (H, W) precipitation (mm/hr) or hazard probability [0–1]
        cmap_name: Matplotlib colormap name (e.g. "jet", "YlOrRd", "Blues")
        vmax:      Value that maps to the top of the colormap
        threshold: Values below this are rendered fully transparent
        srtm:      Optional (n_lat, n_lon) SRTM elevation grid.
                   When provided, the array is terrain-downscaled to ~1 km
                   resolution before rendering.

    Returns:
        "data:image/png;base64,<...>" string
    """
    if srtm is not None:
        # Terrain-enhanced 1 km resolution
        arr = downscale_to_1km(arr, srtm)
        smooth_arr = np.clip(arr, 0, None).astype(np.float32)
        smooth_arr = cv2.GaussianBlur(smooth_arr, (11, 11), 0)
    else:
        # Standard 10× bicubic upsample + Gaussian smoothing
        h, w = arr.shape
        smooth_arr = cv2.resize(
            arr.astype(np.float32),
            (w * 10, h * 10),
            interpolation=cv2.INTER_CUBIC,
        )
        smooth_arr = np.clip(smooth_arr, 0, None)
        smooth_arr = cv2.GaussianBlur(smooth_arr, (11, 11), 0)

    normed = np.clip(smooth_arr / vmax, 0, 1)
    cmap   = plt.get_cmap(cmap_name)
    rgba   = cmap(normed)

    # Transparency: no-rain pixels are fully transparent, rain pixels are 70% opaque
    rgba[smooth_arr <  threshold, 3] = 0.0
    rgba[smooth_arr >= threshold, 3] = 0.70

    img = Image.fromarray((rgba * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
