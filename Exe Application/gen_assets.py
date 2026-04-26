"""
gen_assets.py — generates volcano.ico and logo.png
Run once: python gen_assets.py
"""
import math, struct, zlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── colour palette ──────────────────────────────────────────
BG        = (18,  18,  24)
LAVA      = (255,  80,  20)
LAVA2     = (255, 160,  30)
SMOKE     = (80,   75,  90)
ORANGE    = (255, 130,  30)
WHITE     = (255, 255, 255)
DARK      = (12,  10,  16)

def draw_volcano_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    s   = size

    # sky bg — dark gradient approximation
    for y in range(s):
        t = y / s
        r = int(18  + t * 10)
        g = int(18  + t * 8)
        b = int(24  + t * 14)
        d.line([(0, y), (s, y)], fill=(r, g, b, 255))

    # lava glow behind crater
    glow_r = int(s * 0.28)
    cx, cy = s // 2, int(s * 0.44)
    for i in range(glow_r, 0, -1):
        alpha = int(140 * (1 - i / glow_r) ** 1.5)
        col   = (255, int(80 + 60 * (1 - i/glow_r)), 10, alpha)
        d.ellipse([cx - i, cy - i//2, cx + i, cy + i//2], fill=col)

    # volcano body — trapezoid
    bw  = int(s * 0.82)
    bh  = int(s * 0.52)
    bx  = (s - bw) // 2
    by  = s - bh
    top_w = int(s * 0.30)
    top_x = (s - top_w) // 2
    top_y = int(s * 0.40)

    poly = [
        (top_x,       top_y),
        (top_x + top_w, top_y),
        (bx + bw,     s),
        (bx,          s),
    ]
    # main rock face
    d.polygon(poly, fill=(55, 48, 60))

    # highlight on left slope
    hi_poly = [
        (top_x,       top_y),
        (top_x + top_w//3, top_y),
        (bx + bw//5,  s),
        (bx,          s),
    ]
    d.polygon(hi_poly, fill=(70, 62, 78))

    # crater rim
    rim_w = int(top_w * 1.05)
    rim_x = (s - rim_w) // 2
    d.ellipse([rim_x, top_y - int(s*0.04), rim_x + rim_w, top_y + int(s*0.06)],
              fill=(45, 38, 52))

    # lava pool inside crater
    lava_w = int(top_w * 0.60)
    lava_x = (s - lava_w) // 2
    d.ellipse([lava_x, top_y - int(s*0.02), lava_x + lava_w, top_y + int(s*0.04)],
              fill=LAVA)

    # lava streams down slope
    for ox, strength in [(-top_w//6, 0.85), (top_w//8, 0.70), (top_w//3, 0.55)]:
        sx  = s//2 + ox
        for seg in range(12):
            t   = seg / 12
            t2  = (seg+1) / 12
            x1  = sx + int(ox * t * 0.4)
            y1  = top_y + int((s - top_y) * t)
            x2  = sx + int(ox * t2 * 0.4)
            y2  = top_y + int((s - top_y) * t2)
            a   = int(220 * strength * (1 - t))
            r   = int(255)
            g   = int(80  + 80 * t)
            lw  = max(1, int(s * 0.025 * (1 - t * 0.6)))
            for w in range(lw):
                d.line([(x1+w, y1), (x2+w, y2)], fill=(r, g, 10, a))

    # smoke puffs
    for i, (ox, oy, r) in enumerate([(-s//8, -s//7, s//9),
                                       (s//10, -s//5, s//12),
                                       (-s//18, -s//4, s//14)]):
        sx2 = s // 2 + ox
        sy2 = top_y + oy
        a   = 120 - i * 25
        d.ellipse([sx2 - r, sy2 - r, sx2 + r, sy2 + r],
                  fill=(SMOKE[0], SMOKE[1], SMOKE[2], a))

    img = img.filter(ImageFilter.SMOOTH)
    return img

def make_icon(path: str):
    sizes = [256, 128, 64, 48, 32, 24, 16]
    imgs  = [draw_volcano_icon(s) for s in sizes]
    imgs[0].save(
        path, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=imgs[1:]
    )
    print(f"  icon → {path}")

def make_logo(path: str):
    W, H = 600, 180
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)

    # dark rounded-rect background
    def rrect(d, xy, r, fill):
        x0,y0,x1,y1 = xy
        d.rectangle([x0+r,y0, x1-r,y1], fill=fill)
        d.rectangle([x0,y0+r, x1,y1-r], fill=fill)
        for cx,cy in [(x0+r,y0+r),(x1-r,y0+r),(x0+r,y1-r),(x1-r,y1-r)]:
            d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=fill)

    rrect(d, (0, 0, W-1, H-1), 20, (22, 20, 30, 255))

    # volcano mini icon embedded
    icon = draw_volcano_icon(120)
    img.paste(icon, (14, 30), icon)

    # title text (use default font, scaled)
    try:
        fnt_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        fnt_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        fnt_big = ImageFont.load_default()
        fnt_sm  = fnt_big

    tx = 148
    d.text((tx, 28),  "VOLCANO ERUPTION",  font=fnt_big, fill=LAVA)
    d.text((tx, 76),  "MONITOR",           font=fnt_big, fill=WHITE)
    d.text((tx, 124), "Real-time ultrasonic sensor dashboard", font=fnt_sm, fill=(150, 140, 170))

    # accent line
    d.rectangle([tx, 118, tx + 320, 120], fill=LAVA)

    img.save(path, format="PNG")
    print(f"  logo → {path}")

if __name__ == "__main__":
    make_icon("/home/claude/VolcanoApp/volcano.ico")
    make_logo("/home/claude/VolcanoApp/logo.png")
    print("Assets generated.")
