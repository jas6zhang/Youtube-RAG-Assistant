#!/usr/bin/env python3
"""Render a 1280x800 Chrome Web Store screenshot mockup of the extension UI."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 800
img = Image.new("RGB", (W, H), "#0f0f0f")
d = ImageDraw.Draw(img)

AR = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def f(size, bold=False):
    return ImageFont.truetype(ARB if bold else AR, size)


def rrect(box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def wrap(text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(x, y, text, font, fill, max_w, lh):
    for line in wrap(text, font, max_w):
        d.text((x, y), line, font=font, fill=fill)
        y += lh
    return y


# ---- top bar ----
d.rectangle([0, 0, W, 56], fill="#0f0f0f")
d.line([0, 56, W, 56], fill="#272727", width=1)
rrect([24, 18, 46, 38], 4, fill="#FF0000")
d.polygon([(31, 23), (31, 33), (40, 28)], fill="#fff")
d.text((54, 18), "YouTube", font=f(20, True), fill="#fff")
rrect([430, 16, 830, 40], 12, fill="#121212", outline="#303030")
d.text((446, 21), "how transformers work", font=f(14), fill="#aaa")

# ---- primary column: video player ----
px, py, pw = 24, 80, 760
ph = int(pw * 9 / 16)
# gradient-ish player using vertical bands
for i in range(ph):
    t = i / ph
    r = int(0x3b + (0xb2 - 0x3b) * t)
    g = int(0x2f + (0x3a - 0x2f) * t)
    b = int(0x6b + (0x48 - 0x6b) * t)
    d.line([(px, py + i), (px + pw, py + i)], fill=(r, g, b))
# round the corners by masking edges with bg
mask = Image.new("L", (pw, ph), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw, ph], radius=12, fill=255)
player = img.crop((px, py, px + pw, py + ph))
bg = Image.new("RGB", (pw, ph), "#0f0f0f")
bg.paste(player, (0, 0), mask)
img.paste(bg, (px, py))
d = ImageDraw.Draw(img)
# play button
cx, cy = px + pw // 2, py + ph // 2
rrect([cx - 34, cy - 24, cx + 34, cy + 24], 12, fill=(0, 0, 0, 0) if False else "#00000088" if False else (20, 20, 20))
d.rounded_rectangle([cx - 34, cy - 24, cx + 34, cy + 24], radius=12, fill=(30, 30, 30))
d.polygon([(cx - 10, cy - 13), (cx - 10, cy + 13), (cx + 14, cy)], fill="#fff")
# scrub bar
d.rectangle([px, py + ph - 4, px + pw, py + ph], fill=(255, 255, 255, 255))
d.rectangle([px, py + ph - 4, px + pw, py + ph], fill="#4d4d4d")
d.rectangle([px, py + ph - 4, px + int(pw * 0.38), py + ph], fill="#FF0000")

# video title + meta
ty = py + ph + 16
d.text((px, ty), "Transformers Explained: Attention Is All You Need", font=f(20, True), fill="#fff")
d.text((px, ty + 32), "248,913 views  ·  Ask the assistant anything about this video →", font=f(14), fill="#aaa")
# chips
chy = ty + 64
cxp = px
for label in ["\U0001F44D 12K", "Share", "Save", "···"]:
    wlab = d.textlength(label, font=f(13)) + 24
    rrect([cxp, chy, cxp + wlab, chy + 32], 8, fill="#272727")
    d.text((cxp + 12, chy + 8), label, font=f(13), fill="#ddd")
    cxp += wlab + 8

# ---- secondary column: the extension card ----
sx, sy, sw = 812, 80, 444
card_x, card_y, card_w = sx, sy, sw
# card background (dynamic height)
card_h = 430
rrect([card_x, card_y, card_x + card_w, card_y + card_h], 8, fill="#ffffff", outline="#cccccc")
# red badge
badge = "RAG ASSISTANT"
bw = d.textlength(badge, font=f(11, True)) + 20
rrect([card_x + card_w - bw - 14, card_y - 11, card_x + card_w - 14, card_y + 13], 12, fill="#FF0000")
d.text((card_x + card_w - bw - 14 + 10, card_y - 8), badge, font=f(11, True), fill="#fff")

ix = card_x + 15
iw = card_w - 30
d.text((ix, card_y + 14), "Youtube Video Assistant", font=f(17, True), fill="#333")

# question input box
qy = card_y + 46
rrect([ix, qy, ix + iw, qy + 52], 4, fill="#ffffff", outline="#dddddd")
para(ix + 8, qy + 8, "Why is self-attention better than an RNN for long sequences?",
     f(13), "#333", iw - 16, 18)

# ask button
by = qy + 62
rrect([ix, by, ix + iw, by + 38], 4, fill="#FF0000")
btxt = "Ask Question"
d.text((ix + (iw - d.textlength(btxt, font=f(14, True))) / 2, by + 10), btxt, font=f(14, True), fill="#fff")

# answer panel
ay = by + 50
ah = 210
rrect([ix, ay, ix + iw, ay + ah], 4, fill="#f5f5f5")
tx = ix + 12
tw = iw - 24
yy = ay + 12
d.text((tx, yy), "Answer:", font=f(13, True), fill="#222")
yy += 20
ans = ("Self-attention lets the model relate every token to every other token in a "
       "single step, so long-range dependencies are captured directly. It also removes "
       "the sequential bottleneck of RNNs, making training far more parallelizable.")
yy = para(tx, yy, ans, f(13), "#222", tw, 19)
yy += 8
d.text((tx, yy), "Most Relevant Timestamps:", font=f(13, True), fill="#222")
yy += 22
for ts, snip in [("3:12", "“…attention connects any two positions with a constant number of operations…”"),
                 ("7:45", "“…no recurrence, the whole sequence is processed in parallel…”")]:
    d.text((tx + 6, yy), ts, font=f(13, True), fill="#065fd4")
    ln = para(tx + 50, yy, snip, f(11), "#555", tw - 56, 15)
    yy = max(ln, yy + 18) + 4

# support link
sup = "❤ Support this extension"
d.text((card_x + card_w - 15 - d.textlength(sup, font=f(12)), card_y + card_h - 24),
       sup, font=f(12), fill="#888")

img.save("/Users/jaszha/Youtube-RAG-Assistant/store-screenshot.jpg", "JPEG", quality=92)
print("saved store-screenshot.jpg", img.size, img.mode)
