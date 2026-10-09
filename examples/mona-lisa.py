#!/usr/bin/env python3
"""Draw the Mona Lisa (after Leonardo da Vinci, public domain) as Miro pen strokes.

Writes a scene with 57 pen strokes inside a frame. The template capture needs one
copied pen stroke and one copied frame:

    python3 examples/mona-lisa.py /tmp/mona-scene.json
    python3 scripts/miro-clipboard-compose.py <template.json> /tmp/mona-scene.json /tmp/mona.json
    swift scripts/miro-clipboard-lab.swift replay /tmp/mona.json

Each stroke is a list of board coordinates in the scene's `path` field; the composer
turns it into a positioned Miro stroke.
"""
import json
import math
import sys

def cubic(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                    u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
    return out

def chain(*curves):
    pts = []
    for c in curves:
        pts.extend(c if not pts else c[1:])
    return pts

def ellipse(cx, cy, rx, ry, a0, a1, n=30):
    return [(cx + rx*math.cos(math.radians(a0 + (a1-a0)*i/n)), cy + ry*math.sin(math.radians(a0 + (a1-a0)*i/n))) for i in range(n + 1)]

def wavy(p0, p1, amp, waves, n=40):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
    return [(x0 + dx*t + nx*amp*math.sin(t*waves*2*math.pi), y0 + dy*t + ny*amp*math.sin(t*waves*2*math.pi))
            for t in (i / n for i in range(n + 1))]

def poly(*pts):
    return list(pts)

S = []  # (points, thickness)
def add(pts, t=2): S.append((pts, t))

# Face outline: temple to temple via a narrowing chin
face = []
for i in range(61):
    a = math.radians(215 - 250 * i / 60)
    s, c = math.sin(a), math.cos(a)
    face.append((300 + 88 * c * (1 - 0.24 * max(0, s)), 252 + 108 * s))
add(face, 3)

# Veil over the crown, and the hair framing the face
add(cubic((204, 172), (238, 126), (362, 126), (396, 172)), 2)
add(chain(cubic((300, 140), (244, 136), (200, 186), (198, 262)),
          cubic((198, 262), (196, 350), (186, 420), (172, 486)),
          cubic((172, 486), (165, 505), (176, 515), (166, 532))), 3)
add(chain(cubic((300, 140), (356, 136), (402, 188), (403, 264)),
          cubic((403, 264), (405, 350), (416, 420), (430, 486)),
          cubic((430, 486), (437, 505), (426, 515), (436, 532))), 3)
add(cubic((300, 141), (268, 148), (232, 172), (224, 214)), 2)
add(cubic((300, 141), (332, 148), (368, 172), (376, 214)), 2)
for x0 in (210, 222):
    add(wavy((x0, 215), (x0 - 28, 500), 5, 4), 1.5)
for x0 in (390, 378):
    add(wavy((x0, 215), (x0 + 28, 500), 5, 4), 1.5)

# Eyes, lids and irises
for cx, d in ((268, 1), (332, -1)):
    a, b = cx - 18 * d, cx + 19 * d
    add(cubic((a, 242), (cx - 10 * d, 232), (cx + 8 * d, 231), (b, 240)), 2)
    add(cubic((a, 242), (cx - 8 * d, 249), (cx + 8 * d, 249), (b, 240)), 1.5)
    add(cubic((a + 2 * d, 235), (cx - 8 * d, 225), (cx + 10 * d, 224), (b + 1 * d, 233)), 1)
    add(ellipse(cx + 2 * d, 239, 5.5, 5.5, 200, 340, 12), 2)

# Nose, mouth and the famous smile
add(cubic((291, 246), (293, 270), (294, 290), (291, 303)), 2)
add(cubic((284, 304), (291, 314), (309, 314), (316, 304)), 2)
add(cubic((281, 330), (292, 335), (308, 335), (320, 328)), 2)
add(cubic((292, 343), (297, 345), (303, 345), (308, 343)), 1)
add(cubic((276, 327), (278, 329), (279, 330), (281, 330)), 1)
add(cubic((325, 325), (323, 327), (322, 328), (320, 328)), 1)

# Neck, neckline of the dress, shoulders and sleeves
add(cubic((260, 344), (258, 372), (256, 392), (250, 412)), 2)
add(cubic((340, 344), (342, 372), (346, 392), (352, 412)), 2)
add(cubic((204, 436), (240, 482), (360, 482), (398, 434)), 2.5)
add(wavy((216, 446), (384, 446), 3, 14, 60), 1)
add(chain(cubic((250, 412), (220, 420), (172, 436), (142, 470)),
          cubic((142, 470), (110, 530), (95, 640), (102, 730))), 3)
add(chain(cubic((352, 412), (390, 420), (438, 438), (468, 476)),
          cubic((468, 476), (495, 550), (505, 650), (496, 724))), 3)
for p0, p1 in (((132, 560), (128, 660)), ((160, 590), (156, 690)), ((468, 560), (472, 660)), ((440, 600), (444, 690))):
    add(wavy(p0, p1, 5, 1.5), 1.5)

# Folded hands resting on the arm of the chair
add(cubic((102, 700), (200, 704), (270, 716), (322, 726)), 2.5)
add(cubic((96, 762), (190, 772), (262, 778), (322, 772)), 2.5)
add(chain(cubic((322, 726), (352, 714), (392, 720), (412, 738)), cubic((412, 738), (430, 744), (438, 750), (434, 756))), 2)
for y0 in (744, 754, 764):
    add(cubic((394, y0), (410, y0 + 2), (424, y0 + 4), (430, y0 + 8)), 1.5)
add(cubic((322, 772), (360, 780), (400, 776), (428, 770)), 2)
add(chain(cubic((496, 724), (470, 712), (440, 712), (414, 730)), cubic((414, 730), (396, 744), (392, 760), (400, 774))), 2)

# Landscape: mismatched horizons, mountains, a winding road and a bridge
add(poly((20, 232), (52, 205), (82, 226), (112, 198), (144, 220), (178, 204)), 1.5)
add(wavy((20, 330), (184, 320), 3, 2), 1.5)
add(chain(cubic((40, 478), (100, 440), (52, 410), (118, 392)), cubic((118, 392), (170, 378), (140, 360), (184, 352))), 1.5)
add(poly((420, 190), (452, 168), (488, 186), (520, 162), (556, 182), (584, 168)), 1.5)
add(wavy((420, 282), (584, 276), 3, 2), 1.5)
add(chain(cubic((424, 362), (466, 386), (512, 344), (584, 362))), 1.5)
add(poly((448, 432), (566, 432)), 1.5)
for x0 in (456, 486, 516, 546):
    add(ellipse(x0 + 10, 446, 10, 12, 180, 360, 10), 1.5)

# Loggia parapet behind her
add(poly((20, 522), (140, 516)), 2)
add(poly((462, 516), (584, 522)), 2)
add(poly((26, 522), (26, 470)), 2)
add(poly((578, 522), (578, 470)), 2)

objects = [{"type": "frame", "x": 302, "y": 470, "width": 680, "height": 760,
            "text": "Mona Lisa, after Leonardo da Vinci (line art)", "contains": "all"}]
for pts, t in S:
    objects.append({"type": "paint", "path": [[round(x, 2), round(y, 2)] for x, y in pts],
                    "color": "#1A1A1A", "thickness": t})
out = sys.argv[1] if len(sys.argv) > 1 else "mona-scene.json"
with open(out, "w") as f:
    json.dump({"objects": objects}, f)
print(f"{len(S)} strokes written to {out}")
