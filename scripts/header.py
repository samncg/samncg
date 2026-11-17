"""Build the ASCII header banners (dark + light) for the profile README.

Run locally once: python scripts/header.py   (needs Pillow and a heavy font)
"""
import math
import os
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

COLS, ROWS = 120, 26
W, H = 1000, 270
CW, CH = W / COLS, (H - 10) / ROWS
RAMP = " .,:-~=+*x%#@"
FONT = os.environ.get("HEADER_FONT", r"C:\Windows\Fonts\ariblk.ttf")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")


def mask():
    ss = 4
    img = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(img)
    text = "ncgg"
    size = 100
    f = ImageFont.truetype(FONT, size * ss)
    bbox = d.textbbox((0, 0), text, font=f)
    scale = (W * 0.58 * ss) / (bbox[2] - bbox[0])
    f = ImageFont.truetype(FONT, int(size * ss * scale))
    bbox = d.textbbox((0, 0), text, font=f)
    th = bbox[3] - bbox[1]
    x = int(CW * 4 * ss) - bbox[0]
    y = int((H * ss - th) / 2) - bbox[1] - int(6 * ss)
    d.text((x, y), text, font=f, fill=255)
    small = img.resize((COLS, ROWS), Image.BOX)
    return [[small.getpixel((i, j)) / 255 for i in range(COLS)] for j in range(ROWS)]


def build(theme):
    m = mask()
    rows_dim, rows_tint, rows_mark = [], [], []
    for j in range(ROWS):
        dim, tint, mark = [], [], []
        py = (j + 0.5) * CH
        for i in range(COLS):
            px = (i + 0.5) * CW
            a = math.sin(px * 0.0062 + math.sin(py * 0.011) * 1.6)
            b = math.sin(py * 0.02 + math.sin(px * 0.004) * 2.0)
            w = a * 0.6 + b * 0.4
            contour = math.exp(-(w * w) * 40)
            I = 0.035 + 0.045 * (w * 0.5 + 0.5) + 0.22 * contour
            mv = m[j][i]
            ch_dim = ch_tint = ch_mark = " "
            if mv > 0.12:
                k = min(len(RAMP) - 1, int(3 + mv * (len(RAMP) - 3)))
                ch_mark = RAMP[k]
            elif I >= 0.07:
                g = RAMP[min(len(RAMP) - 1, int((I - 0.07) / 0.93 * len(RAMP)))]
                if contour > 0.45:
                    ch_tint = g
                else:
                    ch_dim = g
            dim.append(ch_dim); tint.append(ch_tint); mark.append(ch_mark)
        rows_dim.append("".join(dim)); rows_tint.append("".join(tint)); rows_mark.append("".join(mark))

    if theme == "dark":
        bg, dimc, tintc, ink, ink2, sub, line = "#000000", "#3a3a3a", "#8b6cf0", "#ededed", "#ffffff", "#8a8a8a", "#222222"
    else:
        bg, dimc, tintc, ink, ink2, sub, line = "#f6f6f4", "#c4c4c4", "#7a52e0", "#121212", "#6b4fd8", "#5c5c5c", "#d8d8d8"

    def layer(rows, cls):
        out = []
        for j, r in enumerate(rows):
            if not r.strip():
                continue
            y = 6 + (j + 0.78) * CH
            out.append(f'<text class="{cls}" x="0" y="{y:.1f}" textLength="{W}" lengthAdjust="spacing">{escape(r)}</text>')
        return "\n    ".join(out)

    tag_x = W - CW * 4
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="ncgg, rendered in ASCII over a field of waves">
  <title>ncgg</title>
  <defs>
    <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="-300" y1="0" x2="0" y2="0">
      <stop offset="0" stop-color="{ink}"/>
      <stop offset="0.5" stop-color="{ink2}"/>
      <stop offset="1" stop-color="{ink}"/>
      <animateTransform attributeName="gradientTransform" type="translate" values="-200 0; 1500 0" dur="5.5s" repeatCount="indefinite"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 12.5px; white-space: pre; }}
    .dim {{ fill: {dimc}; }}
    .tint {{ fill: {tintc}; animation: breathe 6s ease-in-out infinite; }}
    .mark {{ fill: url(#shine); font-weight: 700; }}
    .tag {{ fill: {sub}; font-size: 12px; }}
    .tag b {{ fill: {ink}; }}
    @keyframes breathe {{ 0%, 100% {{ opacity: .45; }} 50% {{ opacity: .9; }} }}
    @media (prefers-reduced-motion: reduce) {{ .tint {{ animation: none; opacity: .7; }} }}
  </style>
  <rect width="{W}" height="{H}" rx="10" fill="{bg}"/>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{line}"/>
  <g>
    {layer(rows_dim, "dim")}
  </g>
  <g>
    {layer(rows_tint, "tint")}
  </g>
  <g>
    {layer(rows_mark, "mark")}
  </g>
  <text class="tag" x="{tag_x:.0f}" y="{H - 22}" text-anchor="end">cad · 3d printing · software · games · ai · robotics   ncgg.dev</text>
</svg>
'''
    with open(os.path.join(OUT, f"header-{theme}.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    build("dark")
    build("light")
    print("header-dark.svg and header-light.svg written")
