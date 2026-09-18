"""
NowCast Fusion — PySTEPS Optical Flow Nowcasting Engine

This is the PRIMARY forecasting method, as specified in the project architecture.
Uses the Lucas-Kanade algorithm via PySTEPS to extrapolate storm cell motion
and generate precipitation forecasts for +30, +60, and +90 minute lead times.

Fallback: If PySTEPS fails for any reason, persistence (last frame repeated)
is used to ensure the API always returns a valid forecast.
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# ─── Unit Conversion Constants ────────────────────────────────────────────────
# PySTEPS optical flow works best on log-transformed (dBR) data.
# This avoids the algorithm being dominated by extreme rain cells.
DBR_ZEROVALUE  = -15.0   # dBR assigned to zero-rain pixels
DBR_THRESHOLD  = 0.1     # mm/hr — below this is treated as no rain


def _mm_to_dbr(R: np.ndarray) -> np.ndarray:
    """Convert precipitation (mm/hr) to logarithmic dBR scale."""
    R_dbr = np.full_like(R, DBR_ZEROVALUE, dtype=float)
    mask  = R >= DBR_THRESHOLD
    R_dbr[mask] = 10.0 * np.log10(R[mask])
    return R_dbr


def _dbr_to_mm(R_dbr: np.ndarray) -> np.ndarray:
    """Convert dBR back to linear mm/hr."""
    R    = np.zeros_like(R_dbr, dtype=float)
    mask = R_dbr > DBR_ZEROVALUE
    R[mask] = 10.0 ** (R_dbr[mask] / 10.0)
    return R


# ─── Public API ───────────────────────────────────────────────────────────────

def get_motion_field(precip_stack: np.ndarray) -> np.ndarray | None:
    """
    Compute the optical flow motion field from a sequence of precipitation frames.

    Args:
        precip_stack: (T, H, W) array in mm/hr, requires T >= 2
    Returns:
        motion_field: (2, H, W) displacement vectors [pixels/timestep],
                      or None if PySTEPS is unavailable / fails.
    """
    try:
        from pysteps import motion

        oflow = motion.get_method("LK")
        R_dbr = np.array([_mm_to_dbr(frame) for frame in precip_stack])
        V     = oflow(R_dbr)
        logger.debug("Motion field computed: shape=%s", V.shape)
        return V

    except Exception as exc:
        logger.error("PySTEPS motion field computation failed: %s", exc)
        return None


def run_optical_flow(
    precip_stack: np.ndarray,
    n_leadtimes: int = 3,
) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Run PySTEPS Lucas-Kanade extrapolation nowcast.

    Steps:
        1. Convert mm/hr → dBR (log transform for better optical flow)
        2. Compute Lucas-Kanade motion vectors from the input sequence
        3. Extrapolate the most recent frame forward by `n_leadtimes` steps
        4. Convert dBR → mm/hr for the output

    Args:
        precip_stack: (T, H, W) recent precipitation frames in mm/hr (T >= 2)
        n_leadtimes:  Number of future frames to predict (each = 30 min)
    Returns:
        forecast_mm:  (n_leadtimes, H, W) forecast in mm/hr
        motion_field: (2, H, W) pixel displacement vectors, or None on failure
    """
    if precip_stack.ndim != 3 or precip_stack.shape[0] < 2:
        logger.warning(
            "precip_stack must be (T>=2, H, W). Got shape %s. Using persistence.",
            precip_stack.shape,
        )
        return _persistence_forecast(precip_stack[-1], n_leadtimes), None

    try:
        from pysteps import motion, nowcasts

        # ── 1. Log-transform ──────────────────────────────────────────────────
        R_dbr = np.array([_mm_to_dbr(frame) for frame in precip_stack])

        # ── 2. Optical flow (Lucas-Kanade) ────────────────────────────────────
        oflow = motion.get_method("LK")
        V     = oflow(R_dbr)
        logger.info("Motion field computed. Max displacement: %.2f px/step", np.nanmax(np.abs(V)))

        # ── 3. Deterministic extrapolation nowcast ────────────────────────────
        extrap    = nowcasts.get_method("extrapolation")
        R_fc_dbr  = extrap(R_dbr[-1], V, n_leadtimes)

        # Replace NaN (unadvected border pixels) with zero-rain value
        R_fc_dbr = np.where(np.isnan(R_fc_dbr), DBR_ZEROVALUE, R_fc_dbr)

        # ── 4. Back-convert to mm/hr ──────────────────────────────────────────
        forecast_mm = np.array([_dbr_to_mm(frame) for frame in R_fc_dbr])
        logger.info(
            "PySTEPS forecast generated: shape=%s, peak=%.2f mm/hr",
            forecast_mm.shape, np.max(forecast_mm),
        )
        return forecast_mm, V

    except ImportError:
        logger.error("PySTEPS is not installed. Run: pip install pysteps. Using persistence fallback.")
    except Exception as exc:
        logger.error("PySTEPS extrapolation failed: %s. Using persistence fallback.", exc)

    return _persistence_forecast(precip_stack[-1], n_leadtimes), None


def _persistence_forecast(last_frame: np.ndarray, n_leadtimes: int) -> np.ndarray:
    """
    Persistence fallback: repeat the last observed frame for every lead time.
    This is the simplest possible forecast and is the baseline PySTEPS is compared against.
    """
    logger.warning("Using persistence forecast (PySTEPS unavailable).")
    return np.stack([last_frame.copy() for _ in range(n_leadtimes)])
