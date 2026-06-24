# -*- coding: utf-8 -*-
# Estrae data/layout dalla chiamata Plotly.newPlot del CampoGara3D e li ispeziona.
import json, re

s = open("index.html", "r", encoding="utf-8", errors="replace").read()
app = s[4845666:4845666 + 3305219]
i = app.find("Plotly.newPlot(")
j = app.find('"', i + 15)                      # apertura stringa div-id
k = app.find('"', j + 1)                        # chiusura div-id
rest = app[k + 1:]

def match(src, openc, closec):
    """ritorna la sottostringa bilanciata che inizia al primo openc."""
    a = src.find(openc)
    depth = 0; instr = False; esc = False
    for p in range(a, len(src)):
        c = src[p]
        if instr:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': instr = False
        else:
            if c == '"': instr = True
            elif c == openc: depth += 1
            elif c == closec:
                depth -= 1
                if depth == 0:
                    return src[a:p + 1], a, p + 1
    raise ValueError("no match")

data_str, a, e = match(rest, "[", "]")
layout_str, la, le = match(rest[e:], "{", "}")
data = json.loads(data_str)
layout = json.loads(layout_str)

print("TRACCE:", len(data))
for t in data:
    typ = t.get("type", "?")
    extra = ""
    for ax in ("x", "y", "z"):
        v = t.get(ax)
        if isinstance(v, list) and v:
            flat = v
            if flat and isinstance(flat[0], list):
                flat = [c for row in v for c in row if c is not None]
            flat = [c for c in flat if isinstance(c, (int, float))]
            if flat:
                extra += f" {ax}[{min(flat):.3f}..{max(flat):.3f}]"
    print(f"  - {typ:10s} name={str(t.get('name'))[:24]:24s}{extra}")

print("\nLAYOUT keys:", list(layout.keys()))
sc = layout.get("scene", {})
print("scene keys:", list(sc.keys()))
print("aspectmode:", sc.get("aspectmode"), "aspectratio:", sc.get("aspectratio"))
print("camera:", sc.get("camera"))
for ax in ("xaxis", "yaxis", "zaxis"):
    axd = sc.get(ax, {})
    print(ax, "title=", (axd.get("title") or {}), "range=", axd.get("range"))

# salva data+layout per riuso
json.dump({"data": data, "layout": layout}, open("_fig_extracted.json", "w", encoding="utf-8"))
print("\nsalvato _fig_extracted.json")
