"""Faint, full-body mist refraction with independently protected source sampling.

The illustration is always sampled at its original resolution. Only the smooth
material masks are low resolution; no desktop pixels are read or synthesized.
"""
from functools import lru_cache
import math
import random

try:
    import numpy as np
except ImportError:
    np = None  # Older/offline installations can still render the same material.

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

CYCLE = 60.0
MATERIAL_BLEND = .5
VEIL_BASE_OPACITY = .025
DISPERSAL_BASE_OPACITY = .0015
# Nominal base before the spatial quiet envelope; the deep-quiet midpoint
# retains one half of the veil endpoint instead of going completely to zero.
HIDDEN_BASE_OPACITY = ((1-MATERIAL_BLEND)*VEIL_BASE_OPACITY
                       + MATERIAL_BLEND*DISPERSAL_BASE_OPACITY)
HIDDEN_PEAK_OPACITY = .12
FIELD_WIDTH, FIELD_HEIGHT = 40, 56
REFLECTION_COLOR = (157, 171, 187)
# Opacity alone keeps a short, soft after-presence. Positive weights preserve
# the continuous cycle average and cannot exceed the baseline temporal peak.
# Sample analytic time, never old rendered frames: recall remains reversible.
TRACE_SAMPLES = ((0.0, .50), (.60, .30), (1.40, .20))
# Five unevenly spaced rests per minute. Core widths compensate for the
# final 8-bit alpha rounding at the soft shoulders; validate rendered durations.
# Each tuple is (center, authored zero core, requested final-zero duration).
DISAPPEAR_WINDOWS = ((7.0, .7754, 1.08), (19.2, 1.2322, 1.50),
                     (31.8, .8256, 1.08), (44.8, 3.6948, 4.00),
                     (55.8, 1.0386, 1.27))
DISAPPEAR_CENTERS = tuple(window[0] for window in DISAPPEAR_WINDOWS)
FACE_GAIN, TIE_GAIN = 1.52, 1.65
IDENTITY_MAX_LIFT = .018
TIE_CHROMA_STRENGTH = .184
# Trim the added identity emphasis; keep the underlying mist unchanged.
FACE_EMPHASIS_SCALE, TIE_EMPHASIS_SCALE = .95, .92
_FACE_ELLIPSES = ((118, 251, 31, 33), (204, 278, 31, 33),
                  (166, 289, 9, 12), (151, 308, 16, 12))


def _ease(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return x*x*(3-2*x)


# Seeded once. Sampling a continuous field avoids frame-to-frame random sparkle.
_rng = random.Random(73109)
_NOISE = tuple(_rng.random() for _ in range(32*32))
del _rng


def _noise(x, y):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x-ix, y-iy
    fx = fx*fx*fx*(fx*(fx*6-15)+10)
    fy = fy*fy*fy*(fy*(fy*6-15)+10)
    a = _NOISE[(iy & 31)*32+(ix & 31)]
    b = _NOISE[(iy & 31)*32+((ix+1) & 31)]
    c = _NOISE[((iy+1) & 31)*32+(ix & 31)]
    d = _NOISE[((iy+1) & 31)*32+((ix+1) & 31)]
    return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy


@lru_cache(maxsize=1)
def _coordinates():
    points = []
    for row in range(FIELD_HEIGHT):
        y = row/(FIELD_HEIGHT-1)
        for col in range(FIELD_WIDTH):
            x = col/(FIELD_WIDTH-1)
            # Protect coordinates, not material coverage: eyes/mouth stay anchored
            # while the same translucent film passes over face, ears and legs.
            face_x = _ease((abs(x-.54)-.18)/.095)
            face_y = _ease((abs(y-.305)-.095)/.065)
            face_free = max(face_x, face_y)
            ear_free = _ease((y-.23)/.10)
            leg_free = 1-_ease((y-.69)/.11)
            sampling_free = face_free*ear_free*leg_free
            delay = .10+.74*_noise(x*3.1+7.2, y*4.5+1.7)+.08*y
            # Smooth spatial phases give different patches their own lifetime.
            # They are cached, so no per-frame random sparkle or extra sampling.
            phi = math.tau*_noise(x*2.9+13.1, y*3.6+2.5)
            psi = math.tau*_noise(x*3.4+1.2, y*2.8+19.7)
            quiet_shift = .055*(2*_noise(x*2.4+18.7, y*3.2+7.4)-1)
            points.append((x, y, sampling_free, delay, phi, psi, quiet_shift))
    return tuple(points)


def _fields_scalar(phase):
    """The exact 0.5 field midpoint between veil and dispersing mist endpoints."""
    local_phase = phase*(CYCLE/12)  # Keep the existing 12-second texture drift.
    c, s = math.cos(local_phase), math.sin(local_phase)
    c2, s2 = math.cos(local_phase*2), math.sin(local_phase*2)
    values = []
    for x, y, sampling_free, delay, phi, psi, quiet_shift in _coordinates():
        # Small, differently directed drifts: texture changes within the body;
        # nothing revolves around it or travels as a whole horizontal stripe.
        u = x*4.1+.28*math.sin(y*5.3-local_phase)+.42*c
        v = y*6.0+.23*math.sin(x*6.7+local_phase)+.38*s
        n = _noise(u+9.3, v+6.8)
        detail = _noise(u*2.15+.15*c2+3.2, v*1.85+.17*s2+12.4)
        veil = _ease((n-.33)/.48)
        ridge = math.exp(-((n-.52)/.09)**2)
        fragment = _ease((detail-.40)/.38)
        filament = ridge*fragment
        life = .5+.30*math.sin(2*local_phase+phi)+.20*math.sin(3*local_phase+psi)
        gate = _ease((life-.30)/.45)
        # A rare deep dispersal, staggered in space rather than a whole-body
        # opacity pulse. At the midpoint a faint veil remains during this rest.
        distance = abs((phase-4.9+quiet_shift+math.pi) % math.tau-math.pi)
        quiet = _ease((distance-.08)/.48)
        veil_opacity = min(HIDDEN_PEAK_OPACITY,
                           VEIL_BASE_OPACITY+.010*veil+.071*filament)
        mist_presence = gate*(.016+.010*veil+.074*filament)
        mist_opacity = min(HIDDEN_PEAK_OPACITY,
                           quiet*(DISPERSAL_BASE_OPACITY+mist_presence))
        # Blend control fields, not two rendered pictures: all four channels
        # share one noise evaluation and one protected surface composition.
        opacity = veil_opacity+MATERIAL_BLEND*(mist_opacity-veil_opacity)
        lens_weight = (1-MATERIAL_BLEND)+MATERIAL_BLEND*gate*quiet
        lens_a = .20*veil*sampling_free*lens_weight
        lens_b = .16*filament*sampling_free*lens_weight
        veil_tint = .07*veil+.22*filament
        mist_tint = gate*quiet*(.025*veil+.18*filament)
        tint = veil_tint+MATERIAL_BLEND*(mist_tint-veil_tint)
        values.append((opacity, lens_a, lens_b, tint, delay+.055*(n-.5)))
    return tuple(values)


@lru_cache(maxsize=1)
def _array_coordinates():
    points = np.asarray(_coordinates(), dtype=np.float64).T.copy()
    noise = np.asarray(_NOISE, dtype=np.float64)
    points.flags.writeable = noise.flags.writeable = False
    return points, noise


def _array_ease(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


def _array_noise(x, y, noise):
    ix, iy = np.floor(x).astype(np.intp), np.floor(y).astype(np.intp)
    fx, fy = x-ix, y-iy
    fx = fx*fx*fx*(fx*(fx*6-15)+10)
    fy = fy*fy*fy*(fy*(fy*6-15)+10)
    a = noise[(iy & 31)*32+(ix & 31)]
    b = noise[(iy & 31)*32+((ix+1) & 31)]
    c = noise[((iy+1) & 31)*32+(ix & 31)]
    d = noise[((iy+1) & 31)*32+((ix+1) & 31)]
    return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy


@lru_cache(maxsize=3)
def _fields(phase):
    """Batch the scalar equations in float64 without quantizing animation time."""
    if np is None:
        return _fields_scalar(phase)
    points, noise = _array_coordinates()
    x, y, sampling_free, delay, phi, psi, quiet_shift = points
    local = phase*(CYCLE/12)
    c, s = math.cos(local), math.sin(local)
    c2, s2 = math.cos(local*2), math.sin(local*2)
    u = x*4.1+.28*np.sin(y*5.3-local)+.42*c
    v = y*6.0+.23*np.sin(x*6.7+local)+.38*s
    n = _array_noise(u+9.3, v+6.8, noise)
    detail = _array_noise(u*2.15+.15*c2+3.2, v*1.85+.17*s2+12.4, noise)
    veil = _array_ease((n-.33)/.48)
    ridge = np.exp(-((n-.52)/.09)**2)
    filament = ridge*_array_ease((detail-.40)/.38)
    life = .5+.30*np.sin(2*local+phi)+.20*np.sin(3*local+psi)
    gate = _array_ease((life-.30)/.45)
    distance = np.abs((phase-4.9+quiet_shift+math.pi) % math.tau-math.pi)
    quiet = _array_ease((distance-.08)/.48)
    veil_opacity = np.minimum(HIDDEN_PEAK_OPACITY, VEIL_BASE_OPACITY+.010*veil+.071*filament)
    mist_presence = gate*(.016+.010*veil+.074*filament)
    mist_opacity = np.minimum(HIDDEN_PEAK_OPACITY, quiet*(DISPERSAL_BASE_OPACITY+mist_presence))
    opacity = veil_opacity+MATERIAL_BLEND*(mist_opacity-veil_opacity)
    lens_weight = (1-MATERIAL_BLEND)+MATERIAL_BLEND*gate*quiet
    lens_a = .20*veil*sampling_free*lens_weight
    lens_b = .16*filament*sampling_free*lens_weight
    veil_tint = .07*veil+.22*filament
    mist_tint = gate*quiet*(.025*veil+.18*filament)
    tint = veil_tint+MATERIAL_BLEND*(mist_tint-veil_tint)
    values = np.column_stack((opacity, lens_a, lens_b, tint, delay+.055*(n-.5)))
    values.flags.writeable = False
    return values


def _mask(values, size, channel, gain=1.0, progress=None):
    pixels = bytearray(FIELD_WIDTH*FIELD_HEIGHT*4)
    if np is not None and isinstance(values, np.ndarray):
        alpha = values[:, channel]*gain
        if progress is not None:
            visible = 1-_array_ease((progress*1.65-values[:, 4])/.65)
            alpha = visible+(1-visible)*values[:, 0]
        # rint and Python round both use round-to-even. RGB remains zero and
        # Qt receives the same RGBA8888 mask and smooth scaling operation.
        pixels[3::4] = np.rint(alpha*255).astype(np.uint8).tobytes()
    else:
        for i, value in enumerate(values):
            alpha = value[channel]*gain
            if progress is not None:
                visible = 1-_ease((progress*1.65-value[4])/.65)
                alpha = visible+(1-visible)*value[0]
            pixels[i*4+3] = round(alpha*255)
    low = QImage(pixels, FIELD_WIDTH, FIELD_HEIGHT, FIELD_WIDTH*4,
                 QImage.Format_RGBA8888).copy()
    return low.scaled(size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def _lingering_fields(phase, fields):
    """Let local visibility settle and fade without trailing image geometry.

    Only opacity is time-filtered. Refraction, tint and transition timing keep
    their original values at the current time; no colors are mixed across time.
    """
    delayed = [(weight, _fields((phase-math.tau*seconds/CYCLE) % math.tau))
               for seconds, weight in TRACE_SAMPLES[1:]]
    if np is not None and isinstance(fields, np.ndarray):
        values = fields.copy()
        values[:, 0] *= TRACE_SAMPLES[0][1]
        for weight, previous in delayed:
            values[:, 0] += weight*previous[:, 0]
        values.flags.writeable = False
        return values
    return tuple((TRACE_SAMPLES[0][1]*value[0]
                  + sum(weight*previous[i][0] for weight, previous in delayed),
                  *value[1:]) for i, value in enumerate(fields))


def _surface(raw, phase, fields, strength=1.0):
    surface = raw.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    surface.setDevicePixelRatio(1)
    scale = raw.width()/144
    # Require nearby source coverage before mixing a refracted sample. Narrow
    # hair strands and antialiased edges keep their original detail and width.
    interior = raw.copy()
    p = QPainter(interior)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    for dx, dy in ((-1.5, 0), (1.5, 0), (0, -1.5), (0, 1.5)):
        p.drawImage(QPointF(dx*scale, dy*scale), raw)
    p.end()
    local_phase = phase*(CYCLE/12)
    offsets = ((.85*math.sin(local_phase+.4), .35*math.cos(local_phase)),
               (-.65*math.cos(local_phase+1.1), .40*math.sin(local_phase*2+.6)))
    for channel, (dx, dy) in enumerate(offsets, 1):
        lens = QImage(raw.size(), QImage.Format_ARGB32_Premultiplied)
        lens.fill(Qt.transparent)
        p = QPainter(lens)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(QPointF(dx*scale, dy*scale), raw)
        p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        p.drawImage(0, 0, _mask(fields, raw.size(), channel, strength))
        p.drawImage(0, 0, interior)
        p.end()
        p = QPainter(surface)
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        p.drawImage(0, 0, lens)
        p.end()
    # A muted film also covers protected anatomy, without moving its source
    # pixels. Original line contrast remains beneath this low-opacity tint.
    tint = _mask(fields, raw.size(), 3, strength)
    p = QPainter(tint)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(tint.rect(), QColor(*REFLECTION_COLOR))
    p.end()
    p = QPainter(surface)
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    p.drawImage(0, 0, tint)
    p.end()
    return surface


def material_surface(raw, phase):
    """Unattenuated detail surface for diagnostic comparison with the artwork."""
    phase = round(phase % math.tau, 9)
    return _surface(raw, phase, _fields(phase))


def _presence_fields(phase, traces):
    """Independent regional rests with a shared, softly approached zero window."""
    seconds = phase*CYCLE/math.tau
    if np is not None and isinstance(traces, np.ndarray):
        points, _ = _array_coordinates()
        _, _, _, delay, phi, psi, _ = points
        life = .55+.28*np.sin(3*phase+phi)+.17*np.sin(5*phase+psi)
        regional = .06+.94*_array_ease((life-.10)/.55)
        edge = min(abs((seconds-center+CYCLE/2) % CYCLE-CYCLE/2)-core/2
                   for center, core, _ in DISAPPEAR_WINDOWS)
        rest = _array_ease(edge/(.85+.65*delay))
        return regional, rest
    result = []
    edge = min(abs((seconds-center+CYCLE/2) % CYCLE-CYCLE/2)-core/2
               for center, core, _ in DISAPPEAR_WINDOWS)
    for point in _coordinates():
        _, _, _, delay, phi, psi, _ = point
        life = .55+.28*math.sin(3*phase+phi)+.17*math.sin(5*phase+psi)
        regional = .06+.94*_ease((life-.10)/.55)
        # Regional ramps share a completely invisible core, not a hard cut.
        rest = _ease(edge/(.85+.65*delay))
        result.append((regional, rest))
    return tuple(zip(*result))


@lru_cache(maxsize=6)
def _pixel_coordinates(width, height):
    # Called only on the NumPy path: never cache None during scalar fallback.
    y, x = np.mgrid[:height, :width].astype(np.float64)
    return x*720/width, y*1000/height


def _head_pose(raw, time):
    pose = raw.text('sakura_head_pose').split(',')
    if len(pose) == 3:
        return tuple(map(float, pose))
    phase = math.tau*(time % 12)/12
    return 4.5*math.sin(phase), -1.5*math.sin(3*phase), 1.4*math.sin(phase)


def _identity_region(raw, time):
    """Evaluate the unchanged weights only where their support can be nonzero."""
    sway, dy, tilt = _head_pose(raw, time)
    angle = math.radians(tilt)
    c, s = math.cos(angle), math.sin(angle)
    width, height = raw.width(), raw.height()
    # The tie selector is exactly zero outside this rectangle. Bound each
    # rotated facial ellipse at its outer feather radius, then pad by two
    # physical pixels so floating-point boundary rounding cannot clip support.
    left, top, right, bottom = .63*720, .23*1000, .855*720, .525*1000
    for cx, cy, rx, ry in _FACE_ELLIPSES:
        center_x, center_y = 178+cx*410/372-385, 50+cy*467/471-400
        center_x, center_y = (c*center_x-s*center_y+385+sway,
                              s*center_x+c*center_y+400+dy)
        radius_x, radius_y = rx*1.16*410/372, ry*1.16*467/471
        extent_x = math.hypot(c*radius_x, s*radius_y)
        extent_y = math.hypot(s*radius_x, c*radius_y)
        left, right = min(left, center_x-extent_x), max(right, center_x+extent_x)
        top, bottom = min(top, center_y-extent_y), max(bottom, center_y+extent_y)
    x0, x1 = max(0, math.floor(left*width/720)-2), min(width, math.ceil(right*width/720)+2)
    y0, y1 = max(0, math.floor(top*height/1000)-2), min(height, math.ceil(bottom*height/1000)+2)
    region = (slice(y0, y1), slice(x0, x1))
    all_x, all_y = _pixel_coordinates(width, height)
    x, y = all_x[region], all_y[region]
    # Keep the original float64 coordinates and operation order. This is an
    # exact domain reduction, not lower-resolution sampling or approximation.
    dx, yy = x-sway-385, y-dy-400
    u = (c*dx+s*yy+385-178)*372/410
    v = (-s*dx+c*yy+400-50)*471/467
    face = np.zeros_like(x)
    for cx, cy, rx, ry in _FACE_ELLIPSES:
        distance = np.sqrt(((u-cx)/rx)**2+((v-cy)/ry)**2)
        face = np.maximum(face, 1-_array_ease((distance-.74)/.42))
    image = raw.copy(x0, y0, x1-x0, y1-y0).convertToFormat(QImage.Format_RGBA8888)
    rgba = np.frombuffer(image.constBits(), np.uint8).reshape(y1-y0, x1-x0, 4)
    red, green, blue = (rgba[:, :, i].astype(np.float64) for i in range(3))
    roi = (_array_ease((x/720-.63)/.025)*(1-_array_ease((x/720-.83)/.025))
           *_array_ease((y/1000-.23)/.025)*(1-_array_ease((y/1000-.50)/.025)))
    tie = roi*_array_ease((red-np.maximum(green, blue)-12)/28)*_array_ease((red-65)/35)
    return region, face, tie


def _identity_weights(raw, time):
    """Full-size diagnostic weights; the render path uses only their support."""
    if np is not None:
        region, face, tie = _identity_region(raw, time)
        faces = np.zeros((raw.height(), raw.width()), np.float64)
        ties = np.zeros_like(faces)
        faces[region], ties[region] = face, tie
        return faces, ties
    sway, dy, tilt = _head_pose(raw, time)
    angle = math.radians(tilt)
    c, s = math.cos(angle), math.sin(angle)
    image = raw.convertToFormat(QImage.Format_RGBA8888)
    width, height = image.width(), image.height()
    faces, ties = [], []
    for py in range(height):
        for px in range(width):
            x, y = px*720/width, py*1000/height
            dx, yy = x-sway-385, y-dy-400
            u, v = (c*dx+s*yy+207)*372/410, (-s*dx+c*yy+350)*471/467
            face = max(1-_ease((math.hypot((u-cx)/rx, (v-cy)/ry)-.74)/.42)
                       for cx, cy, rx, ry in _FACE_ELLIPSES)
            red, green, blue, _ = image.pixelColor(px, py).getRgb()
            roi = (_ease((x/720-.63)/.025)*(1-_ease((x/720-.83)/.025))
                   *_ease((y/1000-.23)/.025)*(1-_ease((y/1000-.50)/.025)))
            faces.append(face)
            ties.append(roi*_ease((red-max(green, blue)-12)/28)*_ease((red-65)/35))
    return faces, ties


def _enrich_tie_red(surface, selection, progress):
    """Make only the original red tie richer without changing surface alpha.

    Work on premultiplied ARGB directly: reducing G/B preserves alpha and
    shading while leaving R intact. Reuse the visibility selector so no second
    source-resolution identity pass or wider color mask is introduced.
    """
    strength = TIE_CHROMA_STRENGTH*_ease(progress/.55)
    if np is not None:
        region, _, ties = selection
        packed = np.frombuffer(surface.bits(), np.uint32).reshape(
            surface.height(), surface.bytesPerLine()//4)[:, :surface.width()][region]
        factor = 1-strength*ties
        green = np.rint(((packed >> 8) & 255)*factor).astype(np.uint32)
        blue = np.rint((packed & 255)*factor).astype(np.uint32)
        packed[:] = (packed & np.uint32(0xffff0000)) | (green << 8) | blue
    else:
        _, ties = selection
        width = surface.width()
        for i, weight in enumerate(ties):
            if weight <= 0:
                continue
            x, y = i % width, i // width
            packed = surface.pixel(x, y)
            factor = 1-strength*weight
            green = round(((packed >> 8) & 255)*factor)
            blue = round((packed & 255)*factor)
            surface.setPixel(x, y, (packed & 0xffff0000) | (green << 8) | blue)
    return surface


def _visibility_mask(raw, phase, traces, progress, time, selection=None):
    regional, rest = _presence_fields(phase, traces)
    # Keep extra masks at the existing 40x56 control resolution. Only feature
    # selection uses source-resolution pixels so thin red ties are not widened.
    if np is not None and isinstance(traces, np.ndarray):
        body = traces.copy()
        body[:, 0] *= regional*rest
        identity = traces.copy()
        identity[:, 0] *= (.90+.10*regional)*rest
    else:
        body = tuple((value[0]*regional[i]*rest[i], *value[1:]) for i, value in enumerate(traces))
        identity = tuple((value[0]*(.90+.10*regional[i])*rest[i], *value[1:]) for i, value in enumerate(traces))
    base = _mask(body, raw.size(), 0, progress=progress)
    identity_mask = _mask(identity, raw.size(), 0, progress=progress)
    # The masks already carry the fade. A constant lift cap keeps their
    # monotonic fall through quantized plateaus; a growing cap can brighten
    # one alpha level near the end. Zero masks still have no alpha floor.
    if np is not None:
        region, faces, ties = selection if selection is not None else _identity_region(raw, time)
        pixels = np.frombuffer(base.bits(), np.uint8).reshape(raw.height(), raw.width(), 4)
        a = pixels[:, :, 3][region].astype(np.float64)
        b = np.frombuffer(identity_mask.constBits(), np.uint8).reshape(raw.height(), raw.width(), 4)[:, :, 3][region].astype(np.float64)
        weight = np.maximum(faces, ties)
        gain = (FACE_GAIN-1)*faces+(TIE_GAIN-1)*ties
        scaled_gain = ((FACE_GAIN-1)*faces*FACE_EMPHASIS_SCALE
                       +(TIE_GAIN-1)*ties*TIE_EMPHASIS_SCALE)
        emphasis_scale = np.divide(scaled_gain, gain, out=np.ones_like(gain), where=gain > 0)
        lifted = b+np.minimum(b*gain, 255*IDENTITY_MAX_LIFT)*emphasis_scale
        alpha = np.rint(a+(lifted-a)*weight).clip(0, 255).astype(np.uint8)
        # Outside this exact support weight=0, hence the old expression is
        # identically the body's existing alpha. Reuse that image unchanged.
        pixels[:, :, 3][region] = alpha
        return base
    faces, ties = selection if selection is not None else _identity_weights(raw, time)
    data = bytearray(bytes(base.constBits()))
    other = bytes(identity_mask.constBits())
    for i, (face, tie) in enumerate(zip(faces, ties)):
        a, b = data[i*4+3], other[i*4+3]
        gain = (FACE_GAIN-1)*face+(TIE_GAIN-1)*tie
        scaled_gain = ((FACE_GAIN-1)*face*FACE_EMPHASIS_SCALE
                       +(TIE_GAIN-1)*tie*TIE_EMPHASIS_SCALE)
        emphasis_scale = scaled_gain/gain if gain > 0 else 1
        lifted = b+min(b*gain,255*IDENTITY_MAX_LIFT)*emphasis_scale
        data[i*4+3] = min(255, max(0, round(a+(lifted-a)*max(face, tie))))
    return QImage(data, raw.width(), raw.height(), raw.width()*4, QImage.Format_RGBA8888).copy()


def irregular_stealth(frame, progress, time):
    """One reversible material state for dissolve, hidden hold and reappearance."""
    if progress <= 0:
        return frame
    progress = min(1.0, progress)
    dpr = frame.devicePixelRatio()
    raw = frame.copy()
    raw.setDevicePixelRatio(1)
    phase = round(math.tau*(time % CYCLE)/CYCLE, 9)
    fields = _fields(phase)
    out = _surface(raw, phase, fields, _ease(progress/.55))
    selection = _identity_region(raw, time) if np is not None else _identity_weights(raw, time)
    _enrich_tie_red(out, selection, progress)
    traces = _lingering_fields(phase, fields)
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, _visibility_mask(raw, phase, traces, progress, time, selection))
    p.end()
    out.setDevicePixelRatio(dpr)
    return out
