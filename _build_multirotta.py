# -*- coding: utf-8 -*-
# Genera ROTTA_A_3D.html, ROTTA_B_3D.html, ROTTA_C_3D.html con selettore di rotta A/B/C.
# Batimetria + barca animata + beam ecoscandaglio + rotta tracciata sul fondale + GPS reale.
# Le 3 rotte usano SOLO waypoint reali (rotta A originale + spot SW/NE gia' verificati);
# definizione A/B/C dalla GUIDA_RAPIDA_BARCA.html. Gli orari sono timing dell'animazione.
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
ZS = 6.0
def hhmm(m): return f"{8 + m // 60:02d}:{m % 60:02d}"

# --- LE TRE ROTTE (solo waypoint reali gia' usati nella rotta A / spot verificati) ---
ROUTES = {
 "A": [  # consigliata: NE tonni mattina -> SW profondo pomeriggio (entrambe le partite)
    (0,   41.680, 11.985, "Start NE: cala lo spread (tonni)"),
    (60,  41.665, 11.965, "Bordo NE nel solunare (tonni)"),
    (120, 41.675, 11.990, "Angolo NE: primi tonni"),
    (180, 41.620, 11.910, "Scendi SW verso le strutture"),
    (240, 41.554, 11.861, "Banco 717 m: alalunga"),
    (300, 41.530, 11.873, "Drop-off 924 m: spada (stop&go)"),
    (360, 41.560, 11.885, "Muri / orlo banco W"),
    (450, 41.585, 11.910, "Ultima passata: in pesca fino alle 15:30"),
 ],
 "B": [  # tutto sul profondo SW (banco + muri): alalunga/spada
    (0,   41.620, 11.910, "Discesa verso il profondo SW"),
    (90,  41.554, 11.861, "Banco 717 m: alalunga"),
    (180, 41.530, 11.873, "Drop-off 924 m: spada (stop&go)"),
    (270, 41.560, 11.885, "Muri / orlo banco W"),
    (360, 41.554, 11.861, "Ripasso banco 717 m"),
    (450, 41.530, 11.873, "Ultima passata drop-off 924 m"),
 ],
 "C": [  # tutto sul bordo NE produttivo in-campo: tonni
    (0,   41.680, 11.985, "Start NE: cala lo spread (tonni)"),
    (90,  41.665, 11.965, "Bordo NE nel solunare"),
    (180, 41.675, 11.990, "Angolo NE: primi tonni"),
    (270, 41.665, 11.965, "Ripasso bordo NE solunare"),
    (360, 41.680, 11.985, "Ripasso start NE"),
    (450, 41.675, 11.990, "Ultima passata angolo NE"),
 ],
}
ROUTE_DESC = {"A": "NE tonni + SW profondo (consigliata)",
              "B": "tutto profondo SW (alalunga/spada)",
              "C": "tutto bordo NE (tonni)"}

def route_bar(rk):
    on = lambda k: "rsel-on" if k == rk else ""
    return ('<style>#routeSel{position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:1002;'
      'display:flex;gap:6px;align-items:center;background:rgba(13,22,38,.92);border:1px solid #2c416c;'
      'border-radius:10px;padding:5px 9px;font:600 12px system-ui,-apple-system,sans-serif;color:#9fb0c8;'
      '-webkit-tap-highlight-color:transparent}'
      '#routeSel a{color:#cfe0f2;text-decoration:none;border:1px solid #2c416c;border-radius:7px;padding:4px 9px}'
      '#routeSel a.rsel-on{background:#1e3a63;color:#fff;border-color:#16e0ff}'
      '#routeSel a.guida{border-style:dashed;color:#16e0ff}'
      '@media(max-width:820px){#routeSel{font-size:11px;padding:4px 6px;gap:4px}#routeSel span{display:none}}</style>'
      '<div id="routeSel"><span>Rotta</span>'
      f'<a href="ROTTA_A_3D.html" class="{on("A")}" title="A: NE tonni + SW profondo">A</a>'
      f'<a href="ROTTA_B_3D.html" class="{on("B")}" title="B: tutto profondo SW">B</a>'
      f'<a href="ROTTA_C_3D.html" class="{on("C")}" title="C: tutto bordo NE">C</a>'
      '<a class="guida" href="https://marinovinc.github.io/GaraOstia2026/GUIDA_RAPIDA_BARCA.html" '
      'target="_blank" rel="noopener" title="Apri la guida di bordo">Guida</a>'
      '</div>')

# blocchi UI/JS comuni (legenda/guida/reset/zoom + GPS correzioni) -- identici per ogni rotta
COMMON_BODY = r"""
<style>
#uiToggles{position:fixed;top:48px;left:8px;z-index:1000;display:flex;gap:6px;flex-direction:column}
#uiToggles button{font:600 12px system-ui,-apple-system,sans-serif;background:rgba(19,33,58,.92);
  color:#cfe0f2;border:1px solid #2c416c;border-radius:8px;padding:7px 11px;cursor:pointer;-webkit-tap-highlight-color:transparent}
#uiToggles button.active{background:#1e3a63;color:#fff;border-color:#16e0ff}
#guideBox{position:fixed;top:48px;left:108px;z-index:1001;max-width:250px;background:rgba(13,22,38,.96);
  border:1px solid #2c416c;border-radius:10px;padding:10px 13px;color:#dfeaf5;font:13px system-ui,-apple-system,sans-serif;display:none;box-shadow:0 4px 16px rgba(0,0,0,.5)}
#guideBox h4{margin:0 0 6px;color:#16e0ff;font-size:13px}
#guideBox ul{margin:0;padding-left:16px}#guideBox li{margin:3px 0}
@media(pointer:coarse){.modebar,.modebar-container{display:none!important}}
.zoomRow{display:flex;gap:6px}.zoomRow button{flex:1;font-size:17px!important;padding:3px 0!important;font-weight:700}
#corrPanel{position:fixed;top:48px;right:8px;z-index:1001;width:min(76vw,300px);background:rgba(13,22,38,.95);
  border:1px solid #2c416c;border-radius:10px;padding:8px 11px;color:#dfeaf5;font:13px system-ui,-apple-system,sans-serif;display:none;box-shadow:0 4px 16px rgba(0,0,0,.5)}
#corrPanel .hd{display:flex;justify-content:space-between;align-items:center;gap:6px}
#corrPanel .hd b{color:#16e0ff;font-size:12px}
#corrToggle{background:none;border:none;color:#cfe0f2;font-size:15px;cursor:pointer;padding:0 2px}
#corrBody{margin-top:5px;line-height:1.45}
#tolRow{font-size:11px;color:#9fb0c8;margin-top:7px}#tolRow input{vertical-align:middle;width:100%}
</style>
<div id="uiToggles">
  <button id="btnLeg" title="Mostra/nascondi legenda e scala">Legenda</button>
  <button id="btnGuide" title="Come si usa">Guida</button>
  <button id="btnReset" title="Ripristina la vista">&#8635; Vista</button>
  <button id="btnGps" title="Mostra la tua posizione GPS reale">GPS</button>
  <div class="zoomRow"><button id="btnZoomOut" title="Zoom indietro">&minus;</button><button id="btnZoomIn" title="Zoom avanti">+</button></div>
</div>
<div id="guideBox">
  <h4>Come usare la scena 3D</h4>
  <ul>
    <li><b>Un dito</b>: ruota la scena</li>
    <li><b>Due dita</b>: zoom (pinch)</li>
    <li><b>A / B / C</b> in alto: cambia rotta</li>
    <li><b>Play</b> / slider: la barca percorre la rotta</li>
    <li><b>Beam cyan</b> = ecoscandaglio (barca&rarr;fondo)</li>
    <li><b>Linea arancione</b> = rotta sul fondale (cresce avanzando)</li>
    <li><b>GPS</b>: mostra la tua barca reale (verde); toccala per le correzioni</li>
  </ul>
</div>
<div id="corrPanel">
  <div class="hd"><b>Correzioni rotta</b><button id="corrToggle" title="Comprimi">&#9662;</button></div>
  <div id="corrBody">Attendo posizione GPS&hellip;</div>
  <div id="tolRow">Tolleranza: <span id="tolVal">50 m</span><input id="tolSlider" type="range" min="10" max="300" step="10" value="50"></div>
</div>
<script>
(function(){
  function gd(){return document.querySelector('.plotly-graph-div');}
  function ready(cb){var g=gd();(g&&g._fullLayout&&window.Plotly)?cb(g):setTimeout(function(){ready(cb);},150);}
  var small=window.matchMedia('(pointer: coarse)').matches||window.matchMedia('(max-width:820px)').matches;
  var legOn=!small;
  function applyLeg(g){Plotly.relayout(g,{showlegend:legOn});Plotly.restyle(g,{showscale:legOn},[0]);
    document.getElementById('btnLeg').classList.toggle('active',legOn);}
  ready(function(g){applyLeg(g);
    document.getElementById('btnLeg').addEventListener('click',function(){legOn=!legOn;applyLeg(gd());});});
  var gOpen=false;
  document.getElementById('btnGuide').addEventListener('click',function(){
    gOpen=!gOpen;document.getElementById('guideBox').style.display=gOpen?'block':'none';this.classList.toggle('active',gOpen);});
  var CAM={eye:{x:1.5,y:-1.7,z:1.05},center:{x:0,y:0,z:-0.18}};
  document.getElementById('btnReset').addEventListener('click',function(){
    if(window.Plotly&&gd())Plotly.relayout(gd(),{'scene.camera':CAM});});
})();
</script>
<script>
(function(){
  var R=window.__ROUTE__||[], SP=window.__SPOTS__||[], G=window.__GEO__||{};
  function gd(){return document.querySelector('.plotly-graph-div');}
  function ready(cb){var g=gd();(g&&g._fullLayout&&window.Plotly)?cb(g):setTimeout(function(){ready(cb);},150);}
  function toXY(lat,lon){return {x:(lon-G.LON0)*G.KX, y:(lat-G.LAT0)*G.KY};}
  function dkm(ax,ay,bx,by){var dx=ax-bx,dy=ay-by;return Math.sqrt(dx*dx+dy*dy);}
  function brgTrue(dx,dy){var b=Math.atan2(dx,dy)*180/Math.PI;return (b+360)%360;}
  function nearest(px,py){var best={d:1e9,segi:0};
    for(var i=0;i<R.length-1;i++){var ax=R[i].x,ay=R[i].y,bx=R[i+1].x,by=R[i+1].y;
      var vx=bx-ax,vy=by-ay,L2=vx*vx+vy*vy; var t=L2>0?((px-ax)*vx+(py-ay)*vy)/L2:0; t=Math.max(0,Math.min(1,t));
      var cx=ax+vx*t,cy=ay+vy*t,dd=dkm(px,py,cx,cy); if(dd<best.d){best={d:dd,segi:i};}}
    return best;}
  var watchId=null,realIdx=null,gpsOn=false,lastFix=null,TOL=50,prev=null;
  function setReal(x,y){var g=gd();
    if(realIdx===null){Plotly.addTraces(g,{type:'scatter3d',x:[x],y:[y],z:[G.ZS],mode:'markers+text',
      marker:{size:11,color:'#39ff7a',symbol:'diamond',line:{color:'#06351c',width:2}},
      text:['TU'],textposition:'top center',textfont:{color:'#39ff7a',size:12},
      name:'posizione reale',hoverinfo:'text',hovertext:['la tua barca (GPS) - tocca per le correzioni']});
      realIdx=g.data.length-1;}
    else{Plotly.restyle(g,{x:[[x]],y:[[y]],z:[[G.ZS]]},[realIdx]);}}
  function update(pos){lastFix=pos;
    var lat=pos.coords.latitude,lon=pos.coords.longitude,hd=pos.coords.heading,acc=pos.coords.accuracy;
    var p=toXY(lat,lon); setReal(p.x,p.y);
    var n=nearest(p.x,p.y), xtm=n.d*1000;
    var nx=R[Math.min(n.segi+1,R.length-1)];
    var dx=nx.x-p.x,dy=nx.y-p.y, brg=brgTrue(dx,dy), distWp=Math.sqrt(dx*dx+dy*dy)*1000;
    var bs=null; for(var i=0;i<SP.length;i++){var dd=dkm(p.x,p.y,SP[i].x,SP[i].y); if(!bs||dd<bs.d)bs={d:dd,name:SP[i].name};}
    // COG: usa heading hardware, altrimenti calcola dai due ultimi fix
    var cog=hd;
    if((cog==null||isNaN(cog))&&prev){var pdx=p.x-prev.x,pdy=p.y-prev.y; if(pdx*pdx+pdy*pdy>1e-8)cog=brgTrue(pdx,pdy);}
    prev={x:p.x,y:p.y};
    var vira='prua non disponibile (sei fermo)';
    if(cog!=null&&!isNaN(cog)){var df=((brg-cog+540)%360)-180;
      vira=Math.abs(df)<5?'dritto sulla prua':('vira a '+(df>0?'dritta':'sinistra')+' di '+Math.round(Math.abs(df))+'°');}
    var accTxt=(acc!=null&&!isNaN(acc))?(' · GPS ±'+Math.round(acc)+' m'+(acc>TOL?' (impreciso)':'')):'';
    var wpn=Math.min(n.segi+2,R.length), h;
    if(xtm<=TOL){h='<b style="color:#39ff7a">IN ROTTA</b> &middot; '+Math.round(xtm)+' m dal tracciato (tol '+TOL+' m)<br>'+
      'Prossimo wp '+wpn+': '+Math.round(distWp)+' m a <b>'+Math.round(brg)+'°</b>'+accTxt;}
    else{h='<b style="color:#ffd54a">FUORI ROTTA '+Math.round(xtm)+' m</b><br>'+
      'Tieni <b>'+Math.round(brg)+'°</b> verso wp '+wpn+' ('+Math.round(distWp)+' m)<br>'+
      vira+'<br>Spot vicino: '+bs.name+' ('+Math.round(bs.d*1000)+' m)'+accTxt;}
    document.getElementById('corrBody').innerHTML=h;}
  function gerr(e){document.getElementById('corrBody').innerHTML='<b style="color:#ff6b6b">GPS non disponibile</b><br>'+((e&&e.message)||'permesso negato');}
  function start(){if(!navigator.geolocation){gerr({message:'Geolocalizzazione non supportata'});return;}
    watchId=navigator.geolocation.watchPosition(update,gerr,{enableHighAccuracy:true,maximumAge:1000,timeout:15000});gpsOn=true;}
  function stop(){if(watchId!=null){navigator.geolocation.clearWatch(watchId);watchId=null;}gpsOn=false;prev=null;
    if(realIdx!=null){Plotly.deleteTraces(gd(),[realIdx]);realIdx=null;}}
  document.getElementById('btnGps').addEventListener('click',function(){var pn=document.getElementById('corrPanel');
    if(!gpsOn){start();pn.style.display='block';this.classList.add('active');}
    else{stop();pn.style.display='none';this.classList.remove('active');}});
  document.getElementById('corrToggle').addEventListener('click',function(){var b=document.getElementById('corrBody'),tr=document.getElementById('tolRow');
    var v=(b.style.display==='none'); b.style.display=v?'block':'none'; tr.style.display=v?'block':'none'; this.innerHTML=v?'▾':'▸';});
  document.getElementById('tolSlider').addEventListener('input',function(){TOL=+this.value;
    document.getElementById('tolVal').textContent=TOL+' m'; if(lastFix)update(lastFix);});
  function zoom(f){var g=gd();if(!g||!g._fullLayout)return;var c=g._fullLayout.scene.camera.center,e=g._fullLayout.scene.camera.eye;
    Plotly.relayout(g,{'scene.camera.eye':{x:c.x+(e.x-c.x)*f,y:c.y+(e.y-c.y)*f,z:c.z+(e.z-c.z)*f}});}
  document.getElementById('btnZoomIn').addEventListener('click',function(){zoom(0.8);});
  document.getElementById('btnZoomOut').addEventListener('click',function(){zoom(1.25);});
  ready(function(g){g.on('plotly_click',function(ev){
    if(ev&&ev.points&&ev.points[0]&&realIdx!=null&&ev.points[0].curveNumber===realIdx){
      document.getElementById('corrPanel').style.display='block';
      document.getElementById('corrBody').style.display='block';
      document.getElementById('tolRow').style.display='block';
      document.getElementById('corrToggle').innerHTML='▾';}});});
})();
</script>
"""

SPOTS_NAMED = [(41.675, 11.990, "bordo NE"), (41.55417, 11.86146, "banco 717 m"), (41.53021, 11.87292, "drop-off 924 m")]

def build(rk, WP):
    mins = [w[0] for w in WP]
    rx, ry = [], []
    for _, lat, lon, _ in WP:
        x, y = to_xy(lat, lon); rx.append(x); ry.append(y)
    def pos_at(t):
        if t <= mins[0]: return rx[0], ry[0]
        if t >= mins[-1]: return rx[-1], ry[-1]
        for i in range(len(mins) - 1):
            if mins[i] <= t <= mins[i + 1]:
                f = (t - mins[i]) / (mins[i + 1] - mins[i])
                return rx[i] + (rx[i + 1] - rx[i]) * f, ry[i] + (ry[i + 1] - ry[i]) * f
        return rx[-1], ry[-1]
    SB = []
    for t in range(0, 451, 3):
        bx, by = pos_at(t); sz = seabed_z(bx, by)
        if sz is not None: SB.append((t, bx, by, sz + 4))
    def seabed_until(T):
        return ([p[1] for p in SB if p[0] <= T], [p[2] for p in SB if p[0] <= T], [p[3] for p in SB if p[0] <= T])
    def seabed_wp_until(T):
        xs, ys, zs, tx = [], [], [], []
        for i, (m, lat, lon, _) in enumerate(WP):
            if m <= T:
                sz = seabed_z(rx[i], ry[i])
                if sz is not None:
                    xs.append(rx[i]); ys.append(ry[i]); zs.append(sz + 4); tx.append(f"{i+1} ({sz:.0f} m)")
        return xs, ys, zs, tx
    sea = go.Mesh3d(x=[-15.5, 14.0, 14.0, -15.5], y=[-13.0, -13.0, 14.5, 14.5], z=[0, 0, 0, 0],
                    i=[0, 0], j=[1, 2], k=[2, 3], color="#2b6cc4", opacity=0.16,
                    hoverinfo="skip", name="superficie del mare", showscale=False, flatshading=True)
    route_surf = go.Scatter3d(x=rx, y=ry, z=[ZS] * len(rx), mode="lines+markers+text",
        line=dict(color="#9C6D14", width=6), marker=dict(size=5, color="#9C6D14", line=dict(color="#fff", width=1)),
        text=[str(i + 1) for i in range(len(rx))], textposition="top center",
        textfont=dict(color="#ffe08a", size=12), name=f"Rotta {rk} (piano, superficie)",
        hovertext=[f"{i+1}. {hhmm(WP[i][0])} — {WP[i][3]}" for i in range(len(WP))], hoverinfo="text")
    def beam_pts(bx, by):
        sz = seabed_z(bx, by); sz = sz if sz is not None else -700.0
        return [bx, bx], [by, by], [ZS, sz], sz
    bx0, by0 = rx[0], ry[0]; bX, bY, bZ, bd0 = beam_pts(bx0, by0)
    sx0, sy0, sz0 = seabed_until(0); wx0, wy0, wz0, wt0 = seabed_wp_until(0)
    trail0   = go.Scatter3d(x=[bx0], y=[by0], z=[ZS], mode="lines", line=dict(color="#e23b3b", width=8), name="scia (superficie)", hoverinfo="skip")
    boat0    = go.Scatter3d(x=[bx0], y=[by0], z=[ZS], mode="markers+text",
        marker=dict(size=9, color="#e23b3b", symbol="diamond", line=dict(color="#fff", width=2)),
        text=["barca 08:00"], textposition="bottom center", textfont=dict(color="#ff6b6b", size=13), name="barca", hoverinfo="text", hovertext=["barca"])
    beam0    = go.Scatter3d(x=bX, y=bY, z=bZ, mode="lines", line=dict(color="#16e0ff", width=5), opacity=0.85, name="beam ecoscandaglio", hoverinfo="skip")
    echo0    = go.Scatter3d(x=[bx0], y=[by0], z=[bd0], mode="markers+text",
        marker=dict(size=6, color="#16e0ff", line=dict(color="#063", width=1)),
        text=[f"{bd0:.0f} m"], textposition="bottom center", textfont=dict(color="#8df0ff", size=11), name="eco fondo", hoverinfo="skip")
    bedtrail0 = go.Scatter3d(x=sx0 or [bx0], y=sy0 or [by0], z=sz0 or [bd0], mode="lines",
        line=dict(color="#ff8c1a", width=7), name=f"Rotta {rk} sul FONDALE (si traccia avanzando)", hoverinfo="skip")
    bedwp0   = go.Scatter3d(x=wx0, y=wy0, z=wz0, mode="markers+text",
        marker=dict(size=4, color="#ff8c1a", line=dict(color="#3a2200", width=1)),
        text=wt0, textposition="bottom center", textfont=dict(color="#ffb05a", size=10),
        name="waypoint sul fondale", hoverinfo="text", hovertext=wt0)
    traces = [go.Figure(data=[d]).data[0] for d in data]
    traces += [sea, route_surf, trail0, boat0, beam0, echo0, bedtrail0, bedwp0]
    TRAIL_I, BOAT_I, BEAM_I, ECHO_I, BED_I, BEDWP_I = range(len(traces) - 6, len(traces))
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
    layout["scene"]["camera"] = dict(eye=dict(x=1.5, y=-1.7, z=1.05), center=dict(x=0, y=0, z=-0.18))
    layout["title"] = dict(text=f"Rotta {rk} — {ROUTE_DESC[rk]}", x=0.5, xanchor="center", y=0.985, font=dict(size=14), automargin=True)
    layout["margin"] = dict(l=0, r=0, t=46, b=0)
    layout["paper_bgcolor"] = "#0d1626"; layout["font"] = dict(color="#e8eef6")
    layout["legend"] = dict(x=0.01, y=0.86, bgcolor="rgba(13,22,38,0.85)", bordercolor="#2c416c", borderwidth=1, font=dict(size=10))
    layout["updatemenus"] = [dict(type="buttons", showactive=False, x=0.02, y=0.06, xanchor="left", buttons=[
        dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=300, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
        dict(label="⏸ Pausa", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
    ])]
    layout["sliders"] = [dict(active=0, x=0.12, y=0.04, len=0.8, currentvalue=dict(prefix="Ora: ", font=dict(color="#ffd54a")), pad=dict(b=6),
        steps=[dict(method="animate", label=hhmm(t), args=[[str(t)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))]) for t in steps])]
    fig = go.Figure(data=traces, layout=layout, frames=frames)
    out = f"ROTTA_{rk}_3D.html"
    fig.write_html(out, include_plotlyjs=True, full_html=True, default_width="100%", default_height="100dvh",
                   config={"displayModeBar": True, "scrollZoom": True, "responsive": True})
    head_inject = (
        '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
        f'<meta name="apple-mobile-web-app-title" content="Rotta {rk} 3D">\n'
        '<meta name="theme-color" content="#0d1626">\n'
        f'<title>Rotta {rk} 3D &mdash; Gara Ostia 2026</title>\n'
        '<style>html,body{margin:0;height:100%;background:#0d1626;overflow:hidden;'
        '-webkit-text-size-adjust:100%;overscroll-behavior:none;touch-action:none}.plotly-graph-div{width:100vw;height:100dvh}</style>')
    html = open(out, "r", encoding="utf-8").read().replace("<head>", "<head>\n" + head_inject, 1)
    route_js = json.dumps([{"x": round(rx[i], 4), "y": round(ry[i], 4), "lat": WP[i][1], "lon": WP[i][2], "m": WP[i][0]} for i in range(len(WP))])
    spots_js = json.dumps([{"x": round(to_xy(s[0], s[1])[0], 4), "y": round(to_xy(s[0], s[1])[1], 4), "name": s[2]} for s in SPOTS_NAMED])
    data_js = ('<script>window.__ROUTE__=%s;window.__SPOTS__=%s;window.__GEO__={LAT0:%r,LON0:%r,KX:%r,KY:%r,ZS:%r};</script>'
               % (route_js, spots_js, LAT0, LON0, KX, KY, ZS))
    html = html.replace("</body>", route_bar(rk) + data_js + COMMON_BODY + "\n</body>", 1)
    open(out, "w", encoding="utf-8").write(html)
    return out, len(SB), len(frames)

for rk in ("A", "B", "C"):
    out, nsb, nfr = build(rk, ROUTES[rk])
    print(f"SAVED {out} | punti fondale: {nsb} | frames: {nfr}")
print("OK multirotta: ROTTA_A_3D.html / ROTTA_B_3D.html / ROTTA_C_3D.html con selettore A/B/C + link guida")
