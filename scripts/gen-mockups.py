#!/usr/bin/env python3
"""Generuje POGLĄDOWE makiety (nie prawdziwe zrzuty) okna Explorera dla 4 motywów,
na FEJKOWYCH danych — bez żadnych danych osobistych. Zapisuje do docs/screenshots/.

Prawdziwe zrzuty z działającej aplikacji: scripts/gen-screenshots.sh
Uruchom: python3 scripts/gen-mockups.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

S = 2  # render w 2x dla ostrości, potem zmniejszenie
W, H = 1280, 760

FONT_DIRS = ["/usr/share/fonts/noto", "/usr/share/fonts/TTF"]
def _font(names, size):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, int(size * S))
    return ImageFont.load_default()
def f_reg(sz):  return _font(["NotoSans-Regular.ttf", "DejaVuSans.ttf"], sz)
def f_med(sz):  return _font(["NotoSans-Medium.ttf", "NotoSans-Regular.ttf"], sz)
def f_bold(sz): return _font(["NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf"], sz)

def hx(c):
    if not isinstance(c, str):
        return c
    c = c.lstrip("#"); return (int(c[0:2],16), int(c[2:4],16), int(c[4:6],16))
def blend(a, b, t):
    a, b = hx(a), hx(b)
    return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))

PALETTES = {
    "01-fluent-dark": dict(name="Fluent · Dark",
        toolbar="#262626", content="#1c1c1c", sidebar="#202020", text="#e8e8ea",
        dim="#9aa0a8", border="#333334", accent="#4d8bff",
        field="#191919", fborder="#3a3a3b", status="#262626", stext="#9aa0a8", sbtext="#e8e8ea"),
    "02-cobalt-dark": dict(name="Cobalt · Dark",
        toolbar="#101f3a", content="#0e1a30", sidebar="#0a1322", text="#e6eefc",
        dim="#92a3c2", border="#1c3358", accent="#3d7bff",
        field="#0a1730", fborder="#21385f", status="#070e1c", stext="#7e93ba", sbtext="#c8d6f0"),
    "03-aurora-light": dict(name="Aurora · Light",
        toolbar="#eceff4", content="#ffffff", sidebar="#e9edf4", text="#2e3440",
        dim="#4c566a", border="#dbe1ea", accent="#5e81ac",
        field="#ffffff", fborder="#d3dae4", status="#e5e9f0", stext="#4c566a", sbtext="#2e3440"),
    "04-porcelain-light": dict(name="Porcelain · Light",
        toolbar="#f6f6f6", content="#ffffff", sidebar="#f4f5f7", text="#1d1d1f",
        dim="#86868b", border="#e6e6e8", accent="#2f6fed",
        field="#ffffff", fborder="#dcdce0", status="#f6f6f6", stext="#86868b", sbtext="#1d1d1f"),
}

FOLDERS = ["Desktop", "Documents", "Downloads", "Music", "Pictures", "Projects", "Videos", "Work"]
FILES = [("welcome.txt","txt"), ("todo.md","txt"), ("Report.docx","doc"), ("Invoice.pdf","pdf"),
         ("Budget.xlsx","xls"), ("sunrise.jpg","img"), ("song.mp3","aud"), ("setup.zip","zip")]
TYPE_COLOR = {"txt":"#8a8f98","doc":"#2b67d6","pdf":"#d64545","xls":"#1f9d57",
              "img":"#9b59b6","aud":"#d6457f","zip":"#d99a2b"}
PLACES = ["Home", "Desktop", "Documents", "Downloads", "Music", "Pictures", "Videos"]
DEVICES = ["This PC", "Local Disk (C:)", "Data (D:)"]

# helpery rysujące w przestrzeni bazowej (mnożą przez S)
def R(d, box, rad, **kw):   d.rounded_rectangle([c*S for c in box], radius=rad*S, **kw)
def rect(d, box, **kw):     d.rectangle([c*S for c in box], **kw)
def line(d, pts, **kw):     d.line([c*S for p in pts for c in p], **kw)
def T(d, x, y, text, font, fill, anchor="la"):
    d.text((x*S, y*S), text, font=font, fill=hx(fill), anchor=anchor)
def tw(d, text, font):      return d.textlength(text, font=font) / S

def draw_folder(d, x, y, w, h, accent):
    front = blend(accent, "#ffffff", 0.22)
    tab   = blend(accent, "#000000", 0.10)
    R(d, (x, y+h*0.18, x+w, y+h),        rad=7, fill=tab)
    R(d, (x, y+h*0.08, x+w*0.46, y+h*0.42), rad=6, fill=tab)
    R(d, (x, y+h*0.30, x+w, y+h),        rad=7, fill=front)
    R(d, (x, y+h*0.30, x+w, y+h*0.58),   rad=7, fill=accent)

def draw_file(d, x, y, w, h, color, border):
    fold = w*0.30
    pg = blend("#ffffff", border, 0.05)
    d.polygon([(x*S,y*S), ((x+w-fold)*S,y*S), ((x+w)*S,(y+fold)*S),
               ((x+w)*S,(y+h)*S), (x*S,(y+h)*S)],
              fill=pg, outline=blend(border,"#000000",0.12), width=max(1,S))
    d.polygon([((x+w-fold)*S,y*S), ((x+w-fold)*S,(y+fold)*S), ((x+w)*S,(y+fold)*S)],
              fill=blend(border,"#000000",0.10))
    R(d, (x+w*0.18, y+h*0.60, x+w*0.82, y+h*0.78), rad=3, fill=color)

def ellipsis(d, text, font, maxw):
    if tw(d, text, font) <= maxw: return text
    while text and tw(d, text+"…", font) > maxw: text = text[:-1]
    return text+"…"

def render(p):
    img = Image.new("RGB", (W*S, H*S), hx(p["content"]))
    d = ImageDraw.Draw(img)
    sel_side = blend(p["sidebar"], p["accent"], 0.20)
    sel_btn  = blend(p["toolbar"], p["accent"], 0.22)
    TB, TOOL, SB, STAT = 38, 56, 240, 30

    # --- pasek tytułu ---
    rect(d, (0,0,W,TB), fill=blend(p["toolbar"],"#000000",0.05))
    T(d, 16, TB/2, "Home — Explorer", f_med(12.5), p["text"], anchor="lm")
    mx = W-22
    line(d, [(W-66-5,TB/2),(W-66+5,TB/2)], fill=p["dim"], width=max(1,S))            # min
    d.rounded_rectangle([(W-44-5)*S,(TB/2-5)*S,(W-44+5)*S,(TB/2+5)*S], radius=2*S,
                        outline=hx(p["dim"]), width=max(1,S))                         # max
    line(d, [(mx-5,TB/2-5),(mx+5,TB/2+5)], fill="#e2564e", width=max(1,S))            # close
    line(d, [(mx+5,TB/2-5),(mx-5,TB/2+5)], fill="#e2564e", width=max(1,S))

    # --- pasek narzędzi ---
    rect(d, (0,TB,W,TB+TOOL), fill=hx(p["toolbar"]))
    rect(d, (0,TB+TOOL-1,W,TB+TOOL), fill=hx(p["border"]))
    cy = TB+TOOL/2
    def navbtn(x, kind, active=True):
        R(d,(x,cy-15,x+30,cy+15),rad=6,fill=blend(p["toolbar"],p["text"],0.05))
        col = p["text"] if active else p["dim"]
        cxb = x+15
        wln = max(1, int(1.6*S))
        if kind == "back":
            line(d, [(cxb+3,cy-6),(cxb-4,cy),(cxb+3,cy+6)], fill=col, width=wln, joint="curve")
        elif kind == "fwd":
            line(d, [(cxb-3,cy-6),(cxb+4,cy),(cxb-3,cy+6)], fill=col, width=wln, joint="curve")
        elif kind == "up":
            line(d, [(cxb-6,cy+1),(cxb,cy-6),(cxb+6,cy+1)], fill=col, width=wln, joint="curve")
            line(d, [(cxb,cy-6),(cxb,cy+7)], fill=col, width=wln)
        elif kind == "home":
            line(d, [(cxb-7,cy),(cxb,cy-7),(cxb+7,cy)], fill=col, width=wln, joint="curve")
            rect(d, (cxb-5,cy-1,cxb+5,cy+7), fill=col)
    bx = 14
    for k,a in [("back",True),("fwd",False),("up",True),("home",True)]:
        navbtn(bx, k, a); bx += 36
    bx += 8
    # aktywny przycisk widoku (ikony) — akcent, NIE czarny kwadrat (pokazuje poprawkę)
    R(d,(bx,cy-15,bx+30,cy+15),rad=6,fill=sel_btn)
    gx, gy = bx+9, cy-6
    for ox in (0,8):
        for oy in (0,8):
            R(d,(gx+ox,gy+oy,gx+ox+5,gy+oy+5),rad=1,fill=p["accent"])
    bx += 36
    R(d,(bx,cy-15,bx+30,cy+15),rad=6,fill=hx(p["toolbar"]))   # lista (nieaktywny)
    for k in range(3):
        rect(d,(bx+8,cy-6+k*5,bx+10,cy-4.5+k*5),fill=hx(p["dim"]))
        rect(d,(bx+12,cy-6+k*5,bx+22,cy-4.5+k*5),fill=hx(p["dim"]))
    bx += 44
    # pasek adresu (breadcrumb)
    addr_w = W-bx-250
    R(d,(bx,cy-16,bx+addr_w,cy+16),rad=8,fill=p["field"],outline=hx(p["fborder"]),width=max(1,S))
    T(d, bx+14, cy, "This PC", f_reg(12), p["dim"], anchor="lm")
    cwx = bx+14+tw(d,"This PC",f_reg(12))
    T(d, cwx+9, cy, "›", f_reg(12), p["dim"], anchor="lm")
    T(d, cwx+22, cy, "Home", f_reg(12), p["text"], anchor="lm")
    # pole wyszukiwania
    sx = W-236
    R(d,(sx,cy-16,W-16,cy+16),rad=8,fill=p["field"],outline=hx(p["fborder"]),width=max(1,S))
    d.ellipse([(sx+15)*S,(cy-6)*S,(sx+25)*S,(cy+4)*S], outline=hx(p["dim"]), width=max(1,S))
    line(d, [(sx+24,cy+3),(sx+29,cy+8)], fill=p["dim"], width=max(1,S))
    T(d, sx+38, cy, "Search", f_reg(12), p["dim"], anchor="lm")

    # --- panel boczny ---
    top = TB+TOOL
    rect(d,(0,top,SB,H-STAT),fill=hx(p["sidebar"]))
    rect(d,(SB,top,SB+1,H-STAT),fill=hx(p["border"]))
    iy = top+18
    def section(title, items, selected=None):
        nonlocal iy
        T(d, 18, iy, title.upper(), f_bold(8.5), p["dim"])
        iy += 24
        for it in items:
            if it == selected:
                R(d,(8,iy-5,SB-10,iy+19),rad=6,fill=sel_side)
            R(d,(18,iy+2,32,iy+13),rad=3,fill=blend(p["accent"],"#ffffff",0.12))
            T(d, 42, iy+7, it, f_reg(11.5), p["sbtext"], anchor="lm")
            iy += 26
        iy += 12
    section("Places", PLACES, selected="Home")
    section("Devices", DEVICES)
    section("Network", ["Network"])

    # --- obszar zawartości: siatka ikon (widok ikon) ---
    cx0, cy0 = SB+30, top+26
    cols, cw, ch, iw = 5, 168, 138, 74
    items = [("folder",n) for n in FOLDERS] + [("file",n) for n in FILES]
    for idx,(kind,data) in enumerate(items):
        r,c = divmod(idx, cols)
        x, y = cx0 + c*cw, cy0 + r*ch
        ix = x + (cw-iw)/2
        if kind == "folder":
            draw_folder(d, ix, y+6, iw, iw*0.78, p["accent"]); label = data
        else:
            name,t = data
            draw_file(d, ix+iw*0.18, y, iw*0.64, iw*0.84, TYPE_COLOR[t], p["border"]); label = name
        lbl = ellipsis(d, label, f_reg(11), cw-26)
        T(d, x+cw/2, y+iw*0.86+12, lbl, f_reg(11), p["text"], anchor="ma")

    # --- pasek statusu ---
    rect(d,(0,H-STAT,W,H),fill=hx(p["status"]))
    rect(d,(0,H-STAT,W,H-STAT+1),fill=hx(p["border"]))
    T(d, 16, H-STAT/2, "16 items", f_reg(10.5), p["stext"], anchor="lm")
    T(d, W-16, H-STAT/2, p["name"], f_reg(10.5), p["stext"], anchor="rm")

    return img.resize((W, H), Image.LANCZOS)

def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(here, "docs", "screenshots")
    os.makedirs(out_dir, exist_ok=True)
    for slug, p in PALETTES.items():
        render(p).save(os.path.join(out_dir, slug + ".png"))
        print("zapisano", slug + ".png")

if __name__ == "__main__":
    main()
