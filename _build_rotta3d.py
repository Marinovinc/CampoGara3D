# -*- coding: utf-8 -*-
# ROTTA_A_3D.html: batimetria 3D + Rotta A in superficie + barca animata + beam ecoscandaglio
# + percorso sul FONDALE tracciato progressivamente mentre la barca lo percorre.
import json, math, base64
import numpy as np
import plotly.graph_objects as go

fig_src = json.load(open("_fig_extracted.json", "r", encoding="utf-8"))
data = fig_src["data"]
layout = fig_src["layout"]

_DT = {"f8": "<f8", "f4": "<f4", "i4": "<i4", "i2": "<i2", "i1": "<i1",
       "u4": "<u4", "u2": "<u2", "u1": "|u1"}
def decode(v):
    if isinstance(v, dict) and "bdata" in v:
        arr = np.frombuffer(base64.b64decode(v["bdata"]), dtype=_DT[v["dtype"]])
        if v.get("shape"):
            arr = arr.reshape(*[int(n) for n in str(v["shape"]).split(",")])
        return arr.astype(float)
    return np.asarray(v, dtype=float)

surf = data[0]
SX, SY, SZ = decode(surf["x"]), decode(surf["y"]), decode(surf["z"])
xa, ya = SX[0, :].copy(), SY[:, 0].copy()
Z = SZ.copy()
if xa[0] > xa[-1]: xa = xa[::-1]; Z = Z[:, ::-1]
if ya[0] > ya[-1]: ya = ya[::-1]; Z = Z[::-1, :]

def seabed_z(qx, qy):
    qx = min(max(qx, xa[0]), xa[-1]); qy = min(max(qy, ya[0]), ya[-1])
    j = max(min(np.searchsorted(xa, qx) - 1, len(xa) - 2), 0)
    i = max(min(np.searchsorted(ya, qy) - 1, len(ya) - 2), 0)
    tx = (qx - xa[j]) / (xa[j + 1] - xa[j]) if xa[j + 1] != xa[j] else 0
    ty = (qy - ya[i]) / (ya[i + 1] - ya[i]) if ya[i + 1] != ya[i] else 0
    c = np.array([Z[i, j], Z[i, j + 1], Z[i + 1, j], Z[i + 1, j + 1]])
    w = np.array([(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty])
    val = np.nansum(c * w) / np.nansum(w[~np.isnan(c)]) if np.any(~np.isnan(c)) else np.nan
    if np.isnan(val):
        win = Z[max(0, i - 3):i + 4, max(0, j - 3):j + 4]
        val = np.nanmean(win) if np.any(~np.isnan(win)) else np.nan
    return None if np.isnan(val) else float(val)

LAT0, LON0 = 41.587, 11.940
KX = 111.320 * math.cos(math.radians(LAT0)); KY = 110.574
def to_xy(lat, lon): return (lon - LON0) * KX, (lat - LAT0) * KY

WP = [
    (0,   41.680, 11.985, "Start NE: cala lo spread (tonni)"),
    (60,  41.665, 11.965, "Bordo NE nel solunare (tonni)"),
    (120, 41.675, 11.990, "Angolo NE: primi tonni"),
    (180, 41.620, 11.910, "Scendi SW verso le strutture"),
    (240, 41.554, 11.861, "Banco 717 m: alalunga"),
    (300, 41.530, 11.873, "Drop-off 924 m: spada (stop&go)"),
    (360, 41.560, 11.885, "Muri / orlo banco W"),
    (450, 41.585, 11.910, "Ultima passata: in pesca fino alle 15:30"),
]
mins = [w[0] for w in WP]
rx, ry = [], []
for _, lat, lon, _ in WP:
    x, y = to_xy(lat, lon); rx.append(x); ry.append(y)
ZS = 6.0
def hhmm(m): return f"{8 + m // 60:02d}:{m % 60:02d}"
def pos_at(t):
    if t <= mins[0]: return rx[0], ry[0]
    if t >= mins[-1]: return rx[-1], ry[-1]
    for i in range(len(mins) - 1):
        if mins[i] <= t <= mins[i + 1]:
            f = (t - mins[i]) / (mins[i + 1] - mins[i])
            return rx[i] + (rx[i + 1] - rx[i]) * f, ry[i] + (ry[i + 1] - ry[i]) * f
    return rx[-1], ry[-1]

# campionamento denso del fondale lungo la rotta, con il minuto associato
SB = []  # (t, x, y, z_fondale)
for t in range(0, 451, 3):
    bx, by = pos_at(t); sz = seabed_z(bx, by)
    if sz is not None: SB.append((t, bx, by, sz + 4))
def seabed_until(T):
    xs = [p[1] for p in SB if p[0] <= T]; ys = [p[2] for p in SB if p[0] <= T]; zs = [p[3] for p in SB if p[0] <= T]
    return xs, ys, zs
def seabed_wp_until(T):
    xs, ys, zs, tx = [], [], [], []
    for i, (m, lat, lon, _) in enumerate(WP):
        if m <= T:
            sz = seabed_z(rx[i], ry[i])
            if sz is not None:
                xs.append(rx[i]); ys.append(ry[i]); zs.append(sz + 4); tx.append(f"{i+1} ({sz:.0f} m)")
    return xs, ys, zs, tx

# --- piano del mare ---
sea = go.Mesh3d(x=[-15.5, 14.0, 14.0, -15.5], y=[-13.0, -13.0, 14.5, 14.5], z=[0, 0, 0, 0],
                i=[0, 0], j=[1, 2], k=[2, 3], color="#2b6cc4", opacity=0.16,
                hoverinfo="skip", name="superficie del mare", showscale=False, flatshading=True)

# --- rotta in superficie (piano completo, riferimento) ---
route_surf = go.Scatter3d(x=rx, y=ry, z=[ZS] * len(rx), mode="lines+markers+text",
    line=dict(color="#9C6D14", width=6), marker=dict(size=5, color="#9C6D14", line=dict(color="#fff", width=1)),
    text=[str(i + 1) for i in range(len(rx))], textposition="top center",
    textfont=dict(color="#ffe08a", size=12), name="Rotta A (piano, superficie)",
    hovertext=[f"{i+1}. {hhmm(WP[i][0])} — {WP[i][3]}" for i in range(len(WP))], hoverinfo="text")

def beam_pts(bx, by):
    sz = seabed_z(bx, by); sz = sz if sz is not None else -700.0
    return [bx, bx], [by, by], [ZS, sz], sz

bx0, by0 = rx[0], ry[0]; bX, bY, bZ, bd0 = beam_pts(bx0, by0)
sx0, sy0, sz0 = seabed_until(0); wx0, wy0, wz0, wt0 = seabed_wp_until(0)

# --- tracce animate (crescono col tempo): scia superficie, barca, beam, eco, rotta-fondale, wp-fondale ---
trail0   = go.Scatter3d(x=[bx0], y=[by0], z=[ZS], mode="lines", line=dict(color="#e23b3b", width=8), name="scia (superficie)", hoverinfo="skip")
boat0    = go.Scatter3d(x=[bx0], y=[by0], z=[ZS], mode="markers+text",
    marker=dict(size=9, color="#e23b3b", symbol="diamond", line=dict(color="#fff", width=2)),
    text=["barca 08:00"], textposition="bottom center", textfont=dict(color="#ff6b6b", size=13), name="barca", hoverinfo="text", hovertext=["barca"])
beam0    = go.Scatter3d(x=bX, y=bY, z=bZ, mode="lines", line=dict(color="#16e0ff", width=5), opacity=0.85, name="beam ecoscandaglio", hoverinfo="skip")
echo0    = go.Scatter3d(x=[bx0], y=[by0], z=[bd0], mode="markers+text",
    marker=dict(size=6, color="#16e0ff", line=dict(color="#063", width=1)),
    text=[f"{bd0:.0f} m"], textposition="bottom center", textfont=dict(color="#8df0ff", size=11), name="eco fondo", hoverinfo="skip")
bedtrail0 = go.Scatter3d(x=sx0 or [bx0], y=sy0 or [by0], z=sz0 or [bd0], mode="lines",
    line=dict(color="#ff8c1a", width=7), name="Rotta A sul FONDALE (si traccia avanzando)", hoverinfo="skip")
bedwp0   = go.Scatter3d(x=wx0, y=wy0, z=wz0, mode="markers+text",
    marker=dict(size=4, color="#ff8c1a", line=dict(color="#3a2200", width=1)),
    text=wt0, textposition="bottom center", textfont=dict(color="#ffb05a", size=10),
    name="waypoint sul fondale", hoverinfo="text", hovertext=wt0)

traces = [go.Figure(data=[d]).data[0] for d in data]
traces += [sea, route_surf, trail0, boat0, beam0, echo0, bedtrail0, bedwp0]
TRAIL_I, BOAT_I, BEAM_I, ECHO_I, BED_I, BEDWP_I = range(len(traces) - 6, len(traces))

# --- frames ---
frames = []; steps = list(range(0, 451, 15))
for t in steps:
    bx, by = pos_at(t); bX, bY, bZ, bd = beam_pts(bx, by)
    txs = [rx[i] for i in range(len(mins)) if mins[i] <= t] + [bx]
    tys = [ry[i] for i in range(len(mins)) if mins[i] <= t] + [by]
    sx, sy, sz = seabed_until(t); wx, wy, wz, wt = seabed_wp_until(t)
    frames.append(go.Frame(name=str(t), data=[
        go.Scatter3d(x=txs, y=tys, z=[ZS] * len(txs), mode="lines", line=dict(color="#e23b3b", width=8)),
        go.Scatter3d(x=[bx], y=[by], z=[ZS], mode="markers+text",
            marker=dict(size=9, color="#e23b3b", symbol="diamond", line=dict(color="#fff", width=2)),
            text=[f"barca {hhmm(t)}"], textposition="bottom center", textfont=dict(color="#ff6b6b", size=13)),
        go.Scatter3d(x=bX, y=bY, z=bZ, mode="lines", line=dict(color="#16e0ff", width=5), opacity=0.85),
        go.Scatter3d(x=[bx], y=[by], z=[bd], mode="markers+text",
            marker=dict(size=6, color="#16e0ff", line=dict(color="#063", width=1)),
            text=[f"{bd:.0f} m"], textposition="bottom center", textfont=dict(color="#8df0ff", size=11)),
        go.Scatter3d(x=sx or [bx], y=sy or [by], z=sz or [bd], mode="lines", line=dict(color="#ff8c1a", width=7)),
        go.Scatter3d(x=wx, y=wy, z=wz, mode="markers+text",
            marker=dict(size=4, color="#ff8c1a", line=dict(color="#3a2200", width=1)),
            text=wt, textposition="bottom center", textfont=dict(color="#ffb05a", size=10)),
    ], traces=[TRAIL_I, BOAT_I, BEAM_I, ECHO_I, BED_I, BEDWP_I]))

# --- layout ---
layout["scene"]["camera"] = dict(eye=dict(x=1.5, y=-1.7, z=1.05), center=dict(x=0, y=0, z=-0.18))
layout["title"] = dict(text="Rotta A — traina in 3D", x=0.5, xanchor="center", y=0.985,
                       font=dict(size=15), automargin=True)
layout["margin"] = dict(l=0, r=0, t=46, b=0)
layout["paper_bgcolor"] = "#0d1626"; layout["font"] = dict(color="#e8eef6")
layout["legend"] = dict(x=0.01, y=0.90, bgcolor="rgba(13,22,38,0.85)", bordercolor="#2c416c", borderwidth=1, font=dict(size=10))
layout["updatemenus"] = [dict(type="buttons", showactive=False, x=0.02, y=0.06, xanchor="left", buttons=[
    dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=300, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
    dict(label="⏸ Pausa", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
])]
layout["sliders"] = [dict(active=0, x=0.12, y=0.04, len=0.8, currentvalue=dict(prefix="Ora: ", font=dict(color="#ffd54a")), pad=dict(b=6),
    steps=[dict(method="animate", label=hhmm(t), args=[[str(t)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))]) for t in steps])]

fig = go.Figure(data=traces, layout=layout, frames=frames)
fig.write_html("ROTTA_A_3D.html", include_plotlyjs=True, full_html=True,
               default_width="100%", default_height="100dvh",
               config={"displayModeBar": True, "scrollZoom": True, "responsive": True})

# --- iniezione meta iOS / mobile (iPhone, iPad) ---
head_inject = (
    '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
    '<meta name="apple-mobile-web-app-title" content="Rotta A 3D">\n'
    '<meta name="theme-color" content="#0d1626">\n'
    '<title>Rotta A 3D &mdash; Gara Ostia 2026</title>\n'
    '<style>html,body{margin:0;height:100%;background:#0d1626;overflow:hidden;'
    '-webkit-text-size-adjust:100%;overscroll-behavior:none;'
    'touch-action:none}.plotly-graph-div{width:100vw;height:100dvh}</style>'
)
html = open("ROTTA_A_3D.html", "r", encoding="utf-8").read()
html = html.replace("<head>", "<head>\n" + head_inject, 1)

# --- UI a scomparsa: legenda + scala colore + guida (default nascoste su mobile/iPad) ---
body_inject = r"""
<style>
#uiToggles{position:fixed;top:8px;left:8px;z-index:1000;display:flex;gap:6px;flex-direction:column}
#uiToggles button{font:600 12px system-ui,-apple-system,sans-serif;background:rgba(19,33,58,.92);
  color:#cfe0f2;border:1px solid #2c416c;border-radius:8px;padding:7px 11px;cursor:pointer;
  -webkit-tap-highlight-color:transparent}
#uiToggles button.active{background:#1e3a63;color:#fff;border-color:#16e0ff}
#guideBox{position:fixed;top:8px;left:108px;z-index:1001;max-width:250px;background:rgba(13,22,38,.96);
  border:1px solid #2c416c;border-radius:10px;padding:10px 13px;color:#dfeaf5;
  font:13px system-ui,-apple-system,sans-serif;display:none;box-shadow:0 4px 16px rgba(0,0,0,.5)}
#guideBox h4{margin:0 0 6px;color:#16e0ff;font-size:13px}
#guideBox ul{margin:0;padding-left:16px}#guideBox li{margin:3px 0}
@media(min-width:1025px){#uiToggles{top:10px;left:10px}}
@media(pointer:coarse){.modebar,.modebar-container{display:none!important}}
</style>
<div id="uiToggles">
  <button id="btnLeg" title="Mostra/nascondi legenda e scala">Legenda</button>
  <button id="btnGuide" title="Come si usa">Guida</button>
  <button id="btnReset" title="Ripristina la vista">&#8635; Vista</button>
</div>
<div id="guideBox">
  <h4>Come usare la scena 3D</h4>
  <ul>
    <li><b>Un dito</b>: ruota la scena</li>
    <li><b>Due dita</b>: zoom (pinch)</li>
    <li><b>Play</b> / slider: la barca percorre la rotta</li>
    <li><b>Beam cyan</b> = ecoscandaglio (barca&rarr;fondo)</li>
    <li><b>Linea arancione</b> = rotta sul fondale (cresce avanzando)</li>
  </ul>
</div>
<script>
(function(){
  function gd(){return document.querySelector('.plotly-graph-div');}
  function ready(cb){var g=gd();(g&&g._fullLayout&&window.Plotly)?cb(g):setTimeout(function(){ready(cb);},150);}
  var small=window.matchMedia('(pointer: coarse)').matches||window.matchMedia('(max-width:820px)').matches;   // mobile + iPad (touch)
  var legOn=!small;                                                  // di default nascosta su mobile/iPad
  function applyLeg(g){Plotly.relayout(g,{showlegend:legOn});Plotly.restyle(g,{showscale:legOn},[0]);
    document.getElementById('btnLeg').classList.toggle('active',legOn);}
  ready(function(g){
    applyLeg(g);
    document.getElementById('btnLeg').addEventListener('click',function(){legOn=!legOn;applyLeg(gd());});
  });
  var gOpen=false;
  document.getElementById('btnGuide').addEventListener('click',function(){
    gOpen=!gOpen;document.getElementById('guideBox').style.display=gOpen?'block':'none';
    this.classList.toggle('active',gOpen);
  });
  var CAM={eye:{x:1.5,y:-1.7,z:1.05},center:{x:0,y:0,z:-0.18}};
  document.getElementById('btnReset').addEventListener('click',function(){
    if(window.Plotly&&gd())Plotly.relayout(gd(),{'scene.camera':CAM});
  });
})();
</script>
"""
html = html.replace("</body>", body_inject + "\n</body>", 1)
open("ROTTA_A_3D.html", "w", encoding="utf-8").write(html)
print("SAVED ROTTA_A_3D.html | punti fondale:", len(SB), "| frames:", len(frames), "| iOS meta: ok")
