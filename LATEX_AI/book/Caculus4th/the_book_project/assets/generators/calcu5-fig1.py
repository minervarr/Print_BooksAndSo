# =====================================================================
#  HEADLESS MACRO - "FIGURE 1" Tower of Hanoi  ->  FULLY VECTOR SVG.
#
#  Run:  ./design-figures.sh calcu5-fig1     (all generators: no argument)
#        (on a server without GL:  xvfb-run -a ./design-figures.sh)
#
#  RENDER STYLE SELECTION
#    "shaded" : Auto-exposed grayscale, gradients + soft shadows.
#    "lineart": Technical line-art: pure white fills, thin black outlines,
#               no shadows.
#
#  This revision (exact ink-fit on ALL four edges)
#    * PERFECT-FIT BBOX, no double counting: geometry extents (object
#      path coords, stroke-free) are grown by EXACTLY stroke/2; balloon
#      extents are tracked as INK extents (R_EXT already includes the
#      stroke overshoot) and used as-is. The canvas is the per-edge
#      union of both families -- the previous version added a global
#      PAD on top of the balloons' already-included stroke, leaving a
#      0.30 mm dead strip above balloon "2". Fixed: every border now
#      touches its ink exactly (bottom/left/right -> base stroke,
#      top -> balloon stroke). No PAD constant remains.
#    * SINGLE-STROKE DISCIPLINE (unchanged): every curve is stroked
#      exactly once -- no doubled, fuzzy anti-aliased edges.
#    * Leader lines drawn UNDER the geometry (clean rim emergence).
#    * shape-rendering="geometricPrecision" for smooth curve raster.
# =====================================================================
import FreeCAD as App
import Part, math, os, base64, struct, zlib
import numpy as np

# ----------------------- style & parameters (mm) --------------------
RENDER_STYLE = "lineart"          # Options: "shaded" or "lineart"
LINEART_STROKE_WIDTH = 0.60       # crispness of black outlines (line-art)

SIN_PHI = 0.30
COS_PHI = math.sqrt(1.0 - SIN_PHI**2)

BASE_LEN, BASE_DEPTH, BASE_SHEAR = 187.0, 222.0, 56.0

PEG_R       = 9.0
PEG_H       = 37.0
DISK_T      = 5.0
DISK_R      = [44.0, 35.0, 28.0, 22.5, 18.0]
DISK_HOLE_R = PEG_R

P1 = App.Vector( 79.0,  63.0, 0.0)
P2 = App.Vector(133.5, 172.0, 0.0)
P3 = App.Vector(173.5,  75.0, 0.0)

IMG_W, IMG_H = 1920, 1080              # raster fallback pixel budget
SS     = 2                             # supersampling factor (raster)

# ----------------------- shading (auto-exposed grayscale) ------------
# (Only used if RENDER_STYLE == "shaded")
COL_BASE   = (212.0, 212.0, 212.0)
COL_PEG    = (222.0, 222.0, 222.0)
COL_BG     = (255.0, 255.0, 255.0)
COL_SHADOW = ( 90.0,  90.0,  90.0)

DISK_ALB_LO, DISK_ALB_HI = 176.0, 216.0
COL_DISK = [(v,)*3 for v in
            [DISK_ALB_LO + (DISK_ALB_HI - DISK_ALB_LO) * i / (len(DISK_R)-1)
             for i in range(len(DISK_R))]]

AMB        = 0.28
TARGET_MAX = 0.92
DIFF       = 0.62
KSPEC      = 0.12
SHIN       = 24.0
FILL_K     = 0.38

LIGHT_MAIN = (-0.55, 0.30, 0.78)
LIGHT_FILL = ( 0.36, -0.72, 0.60)
SHADOW_A0  = 0.42

BALLOON_DX = 18.0
BALLOON_DY = -12.0
BALLOON_R  = 3.5
BALLOON_SW = 0.35
BALLOON_FS = 5.0

# ----------------------- 3D scene ------------------------------------
doc = App.newDocument("Hanoi_Figure1")

A = App.Vector(0, 0, 0); B = App.Vector(BASE_LEN, 0, 0)
C = App.Vector(BASE_LEN + BASE_SHEAR, BASE_DEPTH, 0)
D = App.Vector(BASE_SHEAR, BASE_DEPTH, 0)
base_shape = Part.Face(Part.makePolygon([A, B, C, D, A]))

def add(name, shape):
    o = doc.addObject("Part::Feature", name); o.Shape = shape; return o

objs = [add("BasePlane", base_shape)]

# Direct references (no brittle hardcoded indices in the raster fallback)
peg1_obj = add("Peg1", Part.makeCylinder(PEG_R, PEG_H, P1))
objs.append(peg1_obj)

z = 0.0
disk_shapes = []
for i, r in enumerate(DISK_R):
    outer = Part.makeCylinder(r, DISK_T, App.Vector(P1.x, P1.y, z))
    hole  = Part.makeCylinder(DISK_HOLE_R, DISK_T, App.Vector(P1.x, P1.y, z))
    s = outer.cut(hole)
    disk_shapes.append(s)
    objs.append(add("Disk%d" % (i+1), s))
    z += DISK_T

peg2_obj = add("Peg2", Part.makeCylinder(PEG_R, PEG_H, P2))
objs.append(peg2_obj)
peg3_obj = add("Peg3", Part.makeCylinder(PEG_R, PEG_H, P3))
objs.append(peg3_obj)

doc.recompute()

# ----------------------- lighting vectors + auto-exposure ------------
VCAM = App.Vector(0, -COS_PHI, SIN_PHI)

def _norm(v):
    L = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    return (v[0]/L, v[1]/L, v[2]/L)

# Only compute heavy shading math if we are actually going to use it
GAIN = 1.0
KCAP = 1.0
if RENDER_STYLE == "shaded":
    LX, LY, LZ = _norm(LIGHT_MAIN)
    FLX, FLY, FLZ = _norm(LIGHT_FILL)
    _HV = (LX + VCAM.x, LY + VCAM.y, LZ + VCAM.z)
    HX, HY, HZ = _norm(_HV)

    def _raw(nx, ny, nz):
        ndl1 = max(0.0, nx*LX + ny*LY + nz*LZ)
        ndl2 = max(0.0, nx*FLX + ny*FLY + nz*FLZ) * FILL_K
        ndh  = max(0.0, nx*HX + ny*HY + nz*HZ)
        return DIFF * (ndl1 + ndl2) + KSPEC * ndh ** SHIN

    def _raw_vec(Nx, Ny, Nz):
        ndl1 = np.clip(Nx*LX + Ny*LY + Nz*LZ, 0.0, None)
        ndl2 = np.clip(Nx*FLX + Ny*FLY + Nz*FLZ, 0.0, None) * FILL_K
        ndh  = np.clip(Nx*HX + Ny*HY + Nz*HZ, 0.0, None)
        return DIFF * (ndl1 + ndl2) + KSPEC * ndh ** SHIN

    def _compute_gain():
        cand = [_raw(0.0, 0.0, 1.0)]
        for i in range(64):
            u = -1.0 + 2.0*i/63.0
            cand.append(_raw(u, -math.sqrt(max(0.0, 1.0-u*u)), 0.0))
        rmax = max(cand)
        return (TARGET_MAX - AMB) / rmax if rmax > 1e-9 else 1.0

    GAIN = _compute_gain()
    def phong(nx, ny, nz):
        return AMB + GAIN * _raw(nx, ny, nz)
    KCAP = phong(0.0, 0.0, 1.0)
else:
    LX, LY, LZ = 0.0, 0.0, 1.0   # dummies; unused in line-art

def hexcol(col, k):
    return '#%02x%02x%02x' % tuple(min(255, int(round(c*k + 0.5))) for c in col)

# ----------------------- shadow offset from the main light -----------
def shadow_offset(h):
    if LZ <= 1e-6:
        return (0.0, 0.0)
    return (-LX * h / LZ, -LY * h / LZ)

# ----------------------- projection & page fit -----------------------
CX = (BASE_LEN + BASE_SHEAR) / 2.0
CY = (P2.y * SIN_PHI + PEG_H * COS_PHI) / 2.0

def project_pt(p):
    x = (p.x - CX)
    y = (p.y * SIN_PHI + p.z * COS_PHI - CY)
    return (x, y)

# --- Family 1: GEOMETRY extents (path coords, stroke-FREE).
# --- In u-coords (u_y = -py), the SAME top-down orientation SV() uses.
uxs, uys = [], []
for o in objs:
    bb = o.Shape.BoundBox
    for cx_ in (bb.XMin, bb.XMax):
        for cy_ in (bb.YMin, bb.YMax):
            for cz_ in (bb.ZMin, bb.ZMax):
                px, py = project_pt(App.Vector(cx_, cy_, cz_))
                uxs.append(px); uys.append(-py)

# --- Family 2: BALLOON INK extents (R_EXT ALREADY includes the stroke
# --- overshoot -- these must NOT be padded again!)
BALLOON_STROKE = (LINEART_STROKE_WIDTH if RENDER_STYLE == "lineart"
                  else BALLOON_SW)
R_EXT = BALLOON_R + 0.5 * BALLOON_STROKE
bxs, bys = [], []
for (label, P) in [('1', P1), ('2', P2), ('3', P3)]:
    sx, sy = project_pt(App.Vector(P.x, P.y, PEG_H))
    bx = sx + BALLOON_DX
    by = -sy + BALLOON_DY          # top-down: DY<0 moves up on canvas
    bxs.extend([bx - R_EXT, bx + R_EXT])
    bys.extend([by - R_EXT, by + R_EXT])

# --- Merge per edge: geometry grows by exactly stroke/2 (line-art;
# --- shaded fills carry no outer stroke -> 0), balloon ink used as-is.
# --- No global PAD: the canvas hugs the ink on ALL four sides.
STROKE_HALF = (0.5 * LINEART_STROKE_WIDTH
               if RENDER_STYLE == "lineart" else 0.0)

ux0 = min(min(uxs) - STROKE_HALF, min(bxs))
ux1 = max(max(uxs) + STROKE_HALF, max(bxs))
uy0 = min(min(uys) - STROKE_HALF, min(bys))   # top edge (balloon 2 ink)
uy1 = max(max(uys) + STROKE_HALF, max(bys))   # bottom edge (base stroke)

S  = 1.0
CANVAS_W = (ux1 - ux0) * S
CANVAS_H = (uy1 - uy0) * S
OX = -ux0 * S
OY = -uy0 * S

def SV(p):
    px, py = project_pt(p)
    return (px*S + OX, -py*S + OY)

# ----------------------- vector primitives ---------------------------
def ell_path(cx, cy, rx, ry):
    return ('M %.4f %.4f A %.4f %.4f 0 1 1 %.4f %.4f '
            'A %.4f %.4f 0 1 1 %.4f %.4f Z'
            % (cx-rx, cy, rx, ry, cx+rx, cy, rx, ry, cx-rx, cy))

def wall_path(cx, yt, yb, rx, ry):
    """CLOSED wall silhouette (used for FILLS, and shaded mode)."""
    return ('M %.4f %.4f L %.4f %.4f A %.4f %.4f 0 0 0 %.4f %.4f '
            'L %.4f %.4f A %.4f %.4f 0 0 1 %.4f %.4f Z'
            % (cx-rx, yt, cx-rx, yb, rx, ry, cx+rx, yb,
               cx+rx, yt, rx, ry, cx-rx, yt))

def wall_outline_path(cx, yt, yb, rx, ry, bottom=True):
    """OPEN stroke path for line-art cylinder silhouettes:
    left edge + (optional) front bottom arc + right edge.
    The top rim is NEVER included -- it is stroked exactly once by the
    cap ellipse (pegs) or by the evenodd ring (disks). This is what
    eliminates the doubled, fuzzy anti-aliased edges."""
    if bottom:
        return ('M %.4f %.4f L %.4f %.4f A %.4f %.4f 0 0 0 %.4f %.4f '
                'L %.4f %.4f'
                % (cx-rx, yt, cx-rx, yb, rx, ry, cx+rx, yb, cx+rx, yt))
    # no bottom arc (rim already stroked by the ring underneath)
    return ('M %.4f %.4f L %.4f %.4f M %.4f %.4f L %.4f %.4f'
            % (cx-rx, yt, cx-rx, yb, cx+rx, yb, cx+rx, yt))

def wall_gradient(gid, col, cx, rx, nstop=31):
    stops = []
    for i in range(nstop):
        u = -1.0 + 2.0*i/(nstop-1)
        k = phong(u, -math.sqrt(max(0.0, 1.0-u*u)), 0.0)
        stops.append('<stop offset="%.4f" stop-color="%s"/>'
                     % (i/(nstop-1.0), hexcol(col, k)))
    return ('<linearGradient id="%s" gradientUnits="userSpaceOnUse" '
            'x1="%.4f" y1="0" x2="%.4f" y2="0">%s</linearGradient>'
            % (gid, cx-rx, cx+rx, ''.join(stops)))

def shadow_path(P, r, h):
    dx, dy = shadow_offset(h)
    a = SV(App.Vector(P.x, P.y, 0.0))
    b = SV(App.Vector(P.x + dx, P.y + dy, 0.0))
    rx, ry = r*S, r*SIN_PHI*S
    s0 = (a[0]/rx, a[1]/ry)
    s1 = (b[0]/rx, b[1]/ry)
    sdx, sdy = s1[0]-s0[0], s1[1]-s0[1]
    L = math.hypot(sdx, sdy)
    pts = []
    N = 24
    if L < 1e-9:
        for i in range(2*N):
            t = 2*math.pi*i/(2*N)
            pts.append((s0[0]+math.cos(t), s0[1]+math.sin(t)))
    else:
        phi = math.atan2(sdy, sdx)
        for i in range(N+1):
            t = phi - math.pi/2 + math.pi*i/N
            pts.append((s1[0]+math.cos(t), s1[1]+math.sin(t)))
        for i in range(N+1):
            t = phi + math.pi/2 + math.pi*i/N
            pts.append((s0[0]+math.cos(t), s0[1]+math.sin(t)))
    d = 'M ' + ' L '.join('%.4f %.4f' % (u*rx, v*ry) for (u, v) in pts) + ' Z'
    return d, rx

# ----------------------- osifont glyph outlines ----------------------
_PREFERRED = ("osifont.ttf", "osifont-lgpl3fe.ttf",
              "osifont-gpl2fe.ttf", "osifont.otf")

def _osifont_candidates():
    roots = [
        os.path.join(App.getResourceDir(), "fonts"),
        os.path.join(App.getResourceDir(), "data", "fonts"),
        os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Resources", "fonts"),
        os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Resources"),
        App.getResourceDir(),
    ]
    seen, cands = set(), []
    for root in roots:
        if not os.path.isdir(root):
            continue
        dirs = [root]
        try:
            dirs += [os.path.join(root, d) for d in os.listdir(root)
                     if os.path.isdir(os.path.join(root, d))]
        except OSError:
            pass
        for d in dirs:
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for n in names:
                low = n.lower()
                if not (low.endswith(".ttf") or low.endswith(".otf")):
                    continue
                if "osifont" not in low:
                    continue
                if "italic" in low or "oblique" in low:
                    continue
                p = os.path.join(d, n)
                rp = os.path.realpath(p)
                if rp in seen:
                    continue
                seen.add(rp)
                pri = _PREFERRED.index(low) if low in _PREFERRED else 99
                cands.append((pri, p))
    cands.sort(key=lambda t: t[0])
    return [p for _, p in cands]

def _font_is_upright(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        if len(data) < 12:
            return False
        num = struct.unpack(">H", data[4:6])[0]
        tables = {}
        for i in range(num):
            off = 12 + 16*i
            if off + 16 > len(data):
                break
            tag = data[off:off+4].decode("latin-1")
            tables[tag] = struct.unpack(">I", data[off+8:off+12])[0]
        if "head" in tables:
            t = tables["head"]
            if t + 46 <= len(data):
                if struct.unpack(">H", data[t+44:t+46])[0] & 0x0002:
                    return False
        if "OS/2" in tables:
            t = tables["OS/2"]
            if t + 64 <= len(data):
                if struct.unpack(">H", data[t+62:t+64])[0] & 0x0001:
                    return False
        return ("head" in tables) or ("OS/2" in tables)
    except Exception:
        return False

def make_digit_paths():
    fonts = [p for p in _osifont_candidates() if _font_is_upright(p)]
    if not fonts:
        return None
    font = fonts[0]
    res = None
    attempts = [
        lambda: Part.makeWireString('123', font, BALLOON_FS),
        lambda: Part.makeWireString('123', os.path.dirname(font),
                                    os.path.basename(font), BALLOON_FS),
        lambda: Part.makeWireString('123', os.path.dirname(font),
                                    os.path.basename(font), BALLOON_FS, 0.0),
    ]
    for fn in attempts:
        try:
            res = fn()
            break
        except Exception:
            continue
    if res is None:
        return None
    outs = []
    for char_wires in res:
        segs, allp = [], []
        for w in char_wires:
            pts = w.discretize(Deflection=0.02)
            segs.append(pts); allp += pts
        if not allp:
            outs.append('')
            continue
        xs_ = [p.x for p in allp]; ys_ = [p.y for p in allp]
        cx = (min(xs_)+max(xs_))*0.5; cy = (min(ys_)+max(ys_))*0.5
        d = ''
        for pts in segs:
            d += 'M ' + ' L '.join('%.3f %.3f' % (p.x-cx, -(p.y-cy))
                                   for p in pts) + ' Z '
        outs.append(d)
    App.Console.PrintMessage('Digit outlines from: %s\n' % font)
    return outs if len(outs) == 3 else None

# =====================================================================
#  VECTOR SVG BUILDER
# =====================================================================
def build_vector_svg():
    defs, body = [], []

    if RENDER_STYLE == "lineart":
        # -------------------------------------------------------------
        #  LINE-ART MODE
        #  Single-stroke discipline: every visible edge is stroked
        #  EXACTLY ONCE. Walls fill white without stroke; silhouettes
        #  are separate open paths; rims come from caps / rings.
        # -------------------------------------------------------------
        sw = LINEART_STROKE_WIDTH
        SW_ATTR = 'stroke="#000000" stroke-width="%.4f"' % sw

        # Base plane
        bp = [SV(A), SV(B), SV(C), SV(D)]
        dbase = 'M ' + ' L '.join('%.4f %.4f' % p for p in bp) + ' Z'
        body.append('<path d="%s" fill="#ffffff" %s stroke-linejoin="round"/>'
                    % (dbase, SW_ATTR))

        # Leader lines FIRST (under the geometry): they tuck behind the
        # peg-top caps and emerge cleanly at the rim. No halo, no nicks.
        for (label, P) in [('1', P1), ('2', P2), ('3', P3)]:
            sx, sy = SV(App.Vector(P.x, P.y, PEG_H))
            bx, by = sx + BALLOON_DX, sy + BALLOON_DY
            body.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" '
                        '%s stroke-linecap="round"/>'
                        % (sx, sy, bx, by, SW_ATTR))

        def cyl_la(P, r, z0, z1, top='cap', bottom=True):
            """Line-art cylinder.
            top='cap'  -> stroke a full rim ellipse (pegs)
            top='none' -> no rim here; an evenodd ring is drawn on top
            bottom=False -> skip the bottom arc stroke (the rim ellipse
                            underneath already stroked that exact curve)"""
            cT = SV(App.Vector(P.x, P.y, z1))
            cB = SV(App.Vector(P.x, P.y, z0))
            rx, ry = r*S, r*SIN_PHI*S
            # 1) white occluder fill, NO stroke
            body.append('<path d="%s" fill="#ffffff" stroke="none"/>'
                        % (wall_path(cT[0], cT[1], cB[1], rx, ry)))
            # 2) silhouette stroke: left edge [+ front bottom arc] + right edge
            body.append('<path d="%s" fill="none" %s stroke-linecap="round"/>'
                        % (wall_outline_path(cT[0], cT[1], cB[1], rx, ry,
                                             bottom), SW_ATTR))
            # 3) rim, stroked exactly once
            if top == 'cap':
                body.append('<path d="%s" fill="#ffffff" %s/>'
                            % (ell_path(cT[0], cT[1], rx, ry), SW_ATTR))
            return cT, rx

        def ring_la(P, ro, ri, z):
            """Disk top face. fill-rule=evenodd + one stroke outlines BOTH
            the outer rim and the peg hole -- each exactly once."""
            c = SV(App.Vector(P.x, P.y, z))
            body.append('<path fill-rule="evenodd" d="%s %s" fill="#ffffff" '
                        '%s stroke-linejoin="round"/>'
                        % (ell_path(c[0], c[1], ro*S, ro*SIN_PHI*S),
                           ell_path(c[0], c[1], ri*S, ri*SIN_PHI*S), SW_ATTR))

        # Painter order: far -> near
        cyl_la(P2, PEG_R, 0.0, PEG_H)
        cyl_la(P3, PEG_R, 0.0, PEG_H)
        for i, r in enumerate(DISK_R):
            z0 = i*DISK_T
            # top='none': the ring drawn next provides (and strokes) the top
            cyl_la(P1, r, z0, z0+DISK_T, top='none')
            ri = DISK_R[i+1] if i+1 < len(DISK_R) else PEG_R
            ring_la(P1, r, ri, z0+DISK_T)
        # Peg stub above the stack: bottom=False -- the topmost ring already
        # stroked the hole ellipse, which IS this stub's bottom silhouette.
        cyl_la(P1, PEG_R, len(DISK_R)*DISK_T, PEG_H,
               top='cap', bottom=False)

        # Balloons LAST (on top of everything)
        digits = make_digit_paths()
        for idx, (label, P) in enumerate([('1', P1), ('2', P2), ('3', P3)]):
            sx, sy = SV(App.Vector(P.x, P.y, PEG_H))
            bx, by = sx + BALLOON_DX, sy + BALLOON_DY
            body.append('<circle cx="%.3f" cy="%.3f" r="%.4f" fill="#ffffff" '
                        '%s/>' % (bx, by, BALLOON_R, SW_ATTR))
            if digits and digits[idx]:
                body.append('<path d="%s" transform="translate(%.3f,%.3f)" '
                            'fill="#000000"/>' % (digits[idx], bx, by))
            else:
                body.append('<text x="%.3f" y="%.3f" font-family="Arial, Helvetica, sans-serif" '
                            'font-size="%.4f" text-anchor="middle" fill="#000000">%s</text>'
                            % (bx, by + 0.35*BALLOON_FS, BALLOON_FS, label))

    else:
        # -------------------------------------------------------------
        #  SHADED MODE: original auto-exposed grayscale with gradients
        # -------------------------------------------------------------
        bp = [SV(A), SV(B), SV(C), SV(D)]
        dbase = 'M ' + ' L '.join('%.4f %.4f' % p for p in bp) + ' Z'
        defs.append('<clipPath id="baseclip"><path d="%s"/></clipPath>' % dbase)
        body.append('<path d="%s" fill="%s"/>' % (dbase, hexcol(COL_BASE, KCAP)))

        shadow_items = [
            (P1, DISK_R[0], len(DISK_R)*DISK_T),
            (P2, PEG_R,     PEG_H),
            (P3, PEG_R,     PEG_H),
        ]
        sh = []
        for idx, (P, r, h) in enumerate(shadow_items):
            d, rx = shadow_path(P, r, h)
            fid = 'sb%d' % idx
            defs.append('<filter id="%s" x="-60%%" y="-60%%" width="220%%" '
                        'height="220%%"><feGaussianBlur stdDeviation="%.3f"/>'
                        '</filter>' % (fid, 0.25*rx))
            sh.append('<path d="%s" fill="%s" fill-opacity="%.2f" '
                      'filter="url(#%s)"/>'
                      % (d, hexcol(COL_SHADOW, 1.0), SHADOW_A0, fid))
        body.append('<g clip-path="url(#baseclip)">%s</g>' % ''.join(sh))

        gid = [0]
        def cylinder(P, r, z0, z1, col):
            gid[0] += 1
            g = 'gw%d' % gid[0]
            cT = SV(App.Vector(P.x, P.y, z1))
            cB = SV(App.Vector(P.x, P.y, z0))
            rx, ry = r*S, r*SIN_PHI*S
            defs.append(wall_gradient(g, col, cT[0], rx))
            body.append('<path d="%s" fill="url(#%s)"/>'
                        % (wall_path(cT[0], cT[1], cB[1], rx, ry), g))
            body.append('<path d="%s" fill="%s"/>'
                        % (ell_path(cT[0], cT[1], rx, ry), hexcol(col, KCAP)))
            return cT, rx

        def ring(P, ro, ri, z, col):
            c = SV(App.Vector(P.x, P.y, z))
            body.append('<path fill-rule="evenodd" d="%s %s" fill="%s"/>'
                        % (ell_path(c[0], c[1], ro*S, ro*SIN_PHI*S),
                           ell_path(c[0], c[1], ri*S, ri*SIN_PHI*S),
                           hexcol(col, KCAP)))

        cylinder(P2, PEG_R, 0.0, PEG_H, COL_PEG)
        cylinder(P3, PEG_R, 0.0, PEG_H, COL_PEG)
        for i, r in enumerate(DISK_R):
            z0 = i*DISK_T
            cylinder(P1, r, z0, z0+DISK_T, COL_DISK[i])
            ri = DISK_R[i+1] if i+1 < len(DISK_R) else PEG_R
            ring(P1, r, ri, z0+DISK_T, COL_DISK[i])
        cylinder(P1, PEG_R, len(DISK_R)*DISK_T, PEG_H, COL_PEG)

        digits = make_digit_paths()
        for idx, (label, P) in enumerate([('1', P1), ('2', P2), ('3', P3)]):
            sx, sy = SV(App.Vector(P.x, P.y, PEG_H))
            bx, by = sx + BALLOON_DX, sy + BALLOON_DY
            body.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" '
                        'stroke="#000000" stroke-width="%.2f"/>'
                        % (sx, sy, bx, by, BALLOON_SW))
            body.append('<circle cx="%.3f" cy="%.3f" r="%.2f" fill="#ffffff" '
                        'stroke="#000000" stroke-width="%.2f"/>'
                        % (bx, by, BALLOON_R, BALLOON_SW))
            if digits and digits[idx]:
                body.append('<path d="%s" transform="translate(%.3f,%.3f)" '
                            'fill="#000000"/>' % (digits[idx], bx, by))
            else:
                body.append('<text x="%.3f" y="%.3f" font-family="Arial, '
                            'Helvetica, sans-serif" font-size="%.2f" '
                            'text-anchor="middle" fill="#000000">%s</text>'
                            % (bx, by + 0.35*BALLOON_FS, BALLOON_FS, label))

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<svg xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink" '
             'shape-rendering="geometricPrecision" '
             'width="%.4fmm" height="%.4fmm" viewBox="0 0 %.4f %.4f">'
             % (CANVAS_W, CANVAS_H, CANVAS_W, CANVAS_H),
             '<defs>' + ''.join(defs) + '</defs>']
    parts += body
    parts.append('</svg>')
    return '\n'.join(parts)

# =====================================================================
#  RASTER FALLBACK (Shaded mode only)
# =====================================================================
VIEW_DIR = App.Vector(0, COS_PHI, -SIN_PHI)

def tessellate(shape, deflection=0.25):
    verts, facets = shape.tessellate(deflection)
    tris = []
    for f in facets:
        p0 = verts[f[0]]; p1 = verts[f[1]]; p2 = verts[f[2]]
        n = (p1 - p0).cross(p2 - p0)
        L = n.Length
        if L < 1e-12:
            continue
        tris.append(((p0, p1, p2), App.Vector(n.x/L, n.y/L, n.z/L)))
    return tris

PPM = min(IMG_W / CANVAS_W, IMG_H / CANVAS_H)
WS = max(1, int(round(CANVAS_W * PPM)))
HS = max(1, int(round(CANVAS_H * PPM)))
WSs, HSs = WS * SS, HS * SS
KSS = PPM * SS

def to_pixel_ss(xmm, ymm):
    return (xmm * KSS, ymm * KSS)

def row_world_y(py):
    y_mm = py / KSS
    proj = OY - y_mm
    return (proj + CY) / SIN_PHI

def col_world_x(px):
    x_mm = px / KSS
    return (x_mm - OX) + CX

def depth_of(p):
    return p.y * COS_PHI - p.z * SIN_PHI

def _smooth_normals(tri, fn, axis):
    v0, v1, v2 = tri
    if axis is not None and abs(fn.z) < 0.7:
        ns = []
        s = None
        for v in (v0, v1, v2):
            rx, ry = v.x - axis.x, v.y - axis.y
            rl = math.hypot(rx, ry)
            if rl < 1e-9:
                ns.append(fn); continue
            rx, ry = rx / rl, ry / rl
            if s is None:
                s = 1.0 if (rx * fn.x + ry * fn.y) >= 0.0 else -1.0
            ns.append(App.Vector(rx * s, ry * s, 0.0))
        return ns
    return [fn, fn, fn]

def _raster_tri(color, zbuf, tri, vns, dns, base_col):
    (ax_, ay_), (bx_, by_), (cx_, cy_) = [to_pixel_ss(*SV(v)) for v in tri]
    minx = max(0, int(math.floor(min(ax_, bx_, cx_))))
    maxx = min(WSs - 1, int(math.ceil(max(ax_, bx_, cx_))))
    miny = max(0, int(math.floor(min(ay_, by_, cy_))))
    maxy = min(HSs - 1, int(math.ceil(max(ay_, by_, cy_))))
    if maxx < minx or maxy < miny:
        return
    denom = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
    if abs(denom) < 1e-12:
        return
    xs = np.arange(minx, maxx + 1, dtype=np.float64) + 0.5
    ys = np.arange(miny, maxy + 1, dtype=np.float64) + 0.5
    XX, YY = np.meshgrid(xs, ys)
    w0 = ((by_ - cy_) * (XX - cx_) + (cx_ - bx_) * (YY - cy_)) / denom
    w1 = ((cy_ - ay_) * (XX - cx_) + (ax_ - cx_) * (YY - cy_)) / denom
    w2 = 1.0 - w0 - w1
    mask = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not mask.any():
        return
    depth = w0 * dns[0] + w1 * dns[1] + w2 * dns[2]
    sub_z = zbuf[miny:maxy + 1, minx:maxx + 1]
    upd = mask & (depth < sub_z)
    if not upd.any():
        return
    Nx = w0*vns[0].x + w1*vns[1].x + w2*vns[2].x
    Ny = w0*vns[0].y + w1*vns[1].y + w2*vns[2].y
    Nz = w0*vns[0].z + w1*vns[1].z + w2*vns[2].z
    nl = np.sqrt(Nx*Nx + Ny*Ny + Nz*Nz) + 1e-12
    Nx, Ny, Nz = Nx/nl, Ny/nl, Nz/nl
    k = AMB + GAIN * _raw_vec(Nx, Ny, Nz)
    rgb = np.stack([base_col[0]*k, base_col[1]*k, base_col[2]*k], -1)
    cs = color[miny:maxy + 1, minx:maxx + 1]
    cs[upd] = rgb[upd]
    sub_z[upd] = depth[upd]

def _raster_shape(color, zbuf, shape, base_col, axis):
    for tri, fn in tessellate(shape, deflection=0.25):
        if fn.dot(VIEW_DIR) >= 0:
            continue
        vns = _smooth_normals(tri, fn, axis)
        _raster_tri(color, zbuf, tri, vns,
                    [depth_of(v) for v in tri], base_col)

def _paint_ground_shadow(color):
    shadow_items = [
        (P1, DISK_R[0], len(DISK_R)*DISK_T),
        (P2, PEG_R,     PEG_H),
        (P3, PEG_R,     PEG_H),
    ]
    for (P, r, h) in shadow_items:
        dx_w, dy_w = shadow_offset(h)
        p0 = to_pixel_ss(*SV(App.Vector(P.x, P.y, 0.0)))
        p1 = to_pixel_ss(*SV(App.Vector(P.x + dx_w, P.y + dy_w, 0.0)))
        rx, ry = r * KSS, r * SIN_PHI * KSS
        if rx < 1e-6 or ry < 1e-6:
            continue
        x0 = max(0, int(min(p0[0], p1[0]) - rx)); x1 = min(WSs - 1, int(max(p0[0], p1[0]) + rx))
        y0 = max(0, int(min(p0[1], p1[1]) - ry)); y1 = min(HSs - 1, int(max(p0[1], p1[1]) + ry))
        if x1 < x0 or y1 < y0:
            continue
        xs = np.arange(x0, x1 + 1, dtype=np.float64) + 0.5
        ys = np.arange(y0, y1 + 1, dtype=np.float64) + 0.5
        XX, YY = np.meshgrid(xs, ys)
        sx0, sy0 = p0[0] / rx, p0[1] / ry
        sx1, sy1 = p1[0] / rx, p1[1] / ry
        sdx, sdy = sx1 - sx0, sy1 - sy0
        sl2 = sdx * sdx + sdy * sdy
        SX, SY = XX / rx, YY / ry
        if sl2 > 1e-9:
            t = np.clip(((SX - sx0) * sdx + (SY - sy0) * sdy) / sl2, 0.0, 1.0)
        else:
            t = 0.0
        ddx = SX - (sx0 + t * sdx); ddy = SY - (sy0 + t * sdy)
        d2 = ddx * ddx + ddy * ddy
        inside = d2 <= 1.0
        wy = row_world_y(YY) / BASE_DEPTH
        wx = col_world_x(XX)
        inside &= (wy >= 0.0) & (wy <= 1.0)
        inside &= (wx >= BASE_SHEAR * wy) & (wx <= BASE_SHEAR * wy + BASE_LEN)
        if not inside.any():
            continue
        a = SHADOW_A0 * np.clip(1.0 - d2, 0.0, None) ** 1.5
        a = np.where(inside, a, 0.0)[..., None]
        reg = color[y0:y1 + 1, x0:x1 + 1]
        reg[:] = reg * (1.0 - a) + np.array(COL_SHADOW) * a

def flat_render():
    color = np.empty((HSs, WSs, 3), dtype=np.float64)
    color[:, :] = COL_BG
    zbuf = np.full((HSs, WSs), np.inf, dtype=np.float64)
    _raster_shape(color, zbuf, base_shape, COL_BASE, None)
    _paint_ground_shadow(color)
    _raster_shape(color, zbuf, peg2_obj.Shape, COL_PEG, P2)
    _raster_shape(color, zbuf, peg3_obj.Shape, COL_PEG, P3)
    _raster_shape(color, zbuf, peg1_obj.Shape, COL_PEG, P1)
    for i, s in enumerate(disk_shapes):
        _raster_shape(color, zbuf, s, COL_DISK[i], P1)
    img = color.reshape(HS, SS, WS, SS, 3).mean(axis=(1, 3))
    return np.clip(img + 0.5, 0, 255).astype(np.uint8)

def png_from_rgb(img8, w, h):
    def chunk(typ, data):
        c = struct.pack('>I', len(data)) + typ + data
        c += struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
        return c
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += img8[y].tobytes()
    idat = zlib.compress(bytes(raw), 9)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

def build_raster_svg():
    App.Console.PrintMessage('Rendering (flat z-buffer, SSAA x%d)...\n' % SS)
    img8 = flat_render()
    png = png_from_rgb(img8, WS, HS)
    b64 = base64.b64encode(png).decode('ascii')
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<svg xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink" '
             'width="%.4fmm" height="%.4fmm" viewBox="0 0 %.4f %.4f">'
             % (CANVAS_W, CANVAS_H, CANVAS_W, CANVAS_H),
             '<image x="0" y="0" width="%.4f" height="%.4f" '
             'preserveAspectRatio="none" '
             'xlink:href="data:image/png;base64,%s"/>'
             % (CANVAS_W, CANVAS_H, b64)]
    for (label, P) in [('1', P1), ('2', P2), ('3', P3)]:
        sx, sy = SV(App.Vector(P.x, P.y, PEG_H))
        bx, by = sx + BALLOON_DX, sy + BALLOON_DY
        parts.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" '
                     'stroke="#000000" stroke-width="%.2f"/>'
                     % (sx, sy, bx, by, BALLOON_SW))
        parts.append('<circle cx="%.3f" cy="%.3f" r="%.2f" fill="#ffffff" '
                     'stroke="#000000" stroke-width="%.2f"/>'
                     % (bx, by, BALLOON_R, BALLOON_SW))
        parts.append('<text x="%.3f" y="%.3f" font-family="Arial, '
                     'Helvetica, sans-serif" font-size="%.2f" '
                     'text-anchor="middle" fill="#000000">%s</text>'
                     % (bx, by + 0.35*BALLOON_FS, BALLOON_FS, label))
    parts.append('</svg>')
    return '\n'.join(parts)

# =====================================================================
#  Produce the file
# =====================================================================
if RENDER_STYLE == "lineart":
    try:
        svg = build_vector_svg()
        App.Console.PrintMessage('Line-art Vector SVG built successfully.\n')
    except Exception as e:
        App.Console.PrintError('Line-art vector build failed: %s\n' % e)
        raise
else:
    try:
        svg = build_vector_svg()
        App.Console.PrintMessage('Vector SVG built (GAIN=%.4f, KCAP=%.4f).\n'
                                 % (GAIN, KCAP))
    except Exception as e:
        App.Console.PrintWarning('Vector build failed (%s); '
                                 'falling back to raster.\n' % e)
        svg = build_raster_svg()

out_svg = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'rendered',
    os.path.splitext(os.path.basename(__file__))[0] + '.svg'))
os.makedirs(os.path.dirname(out_svg), exist_ok=True)
with open(out_svg, 'w') as fh:
    fh.write(svg)
App.Console.PrintMessage('SVG written: %s  (%.1f KB)\n'
                         % (out_svg, len(svg) / 1024.0))
