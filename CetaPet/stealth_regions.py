"""Frame-relative anatomy for the shared material; no timing or shader copies."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StealthRegions:
    # Coordinates refer to the entire transparent frame, in [0, 1].
    # Faces: (cx, cy, rx, ry); tie: (left, top, right, bottom, feather).
    faces: tuple = ()
    tie: tuple = ()
    # Protected rectangles: (cx, cy, half_width, half_height, feather_x, feather_y).
    protected: tuple = ()
    refraction: bool = False
    # (cx, cy, half-width, half-height, feather-x, feather-y, residual gain,
    # transition delay). Overlap uses strongest influence, never multiplication.
    visibility: tuple = ()
    ribbon_gain: float = 1.0
    rest_core_adjust: float = 0.0


# Unknown adapters retain the shared tint/opacity animation without guessing anatomy.
GENERIC_REGIONS = StealthRegions()

# Calibrated against the 768x1152 SDK-rendered v11 loop, including blink/gaze/mouth
# extremes. These feathered envelopes cover its small motion, not future poses.
V11_REGIONS = StealthRegions(
    faces=((.456, .209, .030, .015), (.539, .211, .030, .015),
           (.495, .230, .010, .008), (.495, .241, .020, .010)),
    tie=(.580, .158, .705, .326, .012),
    protected=((.496, .217, .085, .052, .035, .025),
               (.500, .110, .140, .055, .030, .020),
               (.495, .780, .150, .220, .040, .040)),
    refraction=True,
    visibility=((.50, .20, .095, .065, .055, .055, 1.14, .018),
                (.50, .31, .18, .08, .07, .06, 1.10, .012),
                (.50, .43, .18, .07, .06, .06, 1.08, .008),
                (.50, .71, .12, .12, .045, .065, .65, -.025)),
    ribbon_gain=1.16,
    rest_core_adjust=-.033333333333,
)
