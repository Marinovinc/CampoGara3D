# -*- coding: utf-8 -*-
"""Trasforma CampoGara3D in PWA offline: inietta manifest+SW in index.html,
genera manifest.json, sw.js e le icone. Idempotente e rieseguibile."""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = r"D:\Dev\CampoGara3D"
HTML = os.path.join(BASE, "index.html")
BG = (13, 22, 38)          # #0d1626
ACC = (39, 196, 107)       # #27c46b

# --- 1) inietta manifest + service worker in index.html (senza caricarlo in chat) ---
html = open(HTML, "r", encoding="utf-8", errors="replace").read()
HEAD_TAGS = ('<link rel="manifest" href="manifest.json">'
             '<meta name="theme-color" content="#0d1626">'
             '<meta name="apple-mobile-web-app-capable" content="yes">'
             '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
             '<link rel="apple-touch-icon" href="icon-192.png">')
SW_REG = ('<script>if("serviceWorker" in navigator){'
          'window.addEventListener("load",function(){'
          'navigator.serviceWorker.register("sw.js").catch(function(e){console.log("SW",e);});});}'
          '</script>')

if "manifest.json" not in html:
    i = html.lower().find("</head>")
    if i == -1:   # Plotly minimale: inserisci un head dopo <html>
        h = html.lower().find("<head>")
        if h != -1:
            ins = h + len("<head>")
            html = html[:ins] + HEAD_TAGS + html[ins:]
        else:
            html = HEAD_TAGS + html
    else:
        html = html[:i] + HEAD_TAGS + html[i:]
    j = html.lower().rfind("</body>")
    if j == -1:
        html = html + SW_REG
    else:
        html = html[:j] + SW_REG + html[j:]
    open(HTML, "w", encoding="utf-8").write(html)
    print("OK index.html: iniettati manifest + registrazione SW")
else:
    print("index.html gia' PWA: nessuna modifica")

# --- 2) manifest.json ---
manifest = '''{
  "name": "Campo Gara 3D - Roma/Ostia 2026",
  "short_name": "Campo 3D",
  "description": "Scena 3D del campo gara - 62 Campionato Italiano Traina d'Altura",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#0d1626",
  "theme_color": "#0d1626",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ]
}
'''
open(os.path.join(BASE, "manifest.json"), "w", encoding="utf-8").write(manifest)
print("OK manifest.json")

# --- 3) service worker (cache-first, offline dopo la prima apertura) ---
sw = '''// PWA Campo Gara 3D - cache-first per uso offline a bordo
const CACHE = 'campo3d-v1';
const ASSETS = ['./', 'index.html', 'manifest.json', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request, {ignoreSearch: true}).then(r =>
      r || fetch(e.request).then(resp => {
        try { const cp = resp.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); } catch (_) {}
        return resp;
      }).catch(() => caches.match('index.html'))
    )
  );
});
'''
open(os.path.join(BASE, "sw.js"), "w", encoding="utf-8").write(sw)
print("OK sw.js")

# --- 4) icone 192 e 512 ---
def font(sz):
    for n in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        p = os.path.join(r"C:\Windows\Fonts", n)
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def make_icon(size):
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)
    # cornice
    m = int(size * 0.08)
    d.rounded_rectangle([m, m, size - m, size - m], radius=int(size * 0.12),
                        outline=ACC, width=max(3, size // 48))
    # "3D"
    f1 = font(int(size * 0.42))
    d.text((size / 2, size * 0.42), "3D", font=f1, fill=ACC, anchor="mm")
    # sottotitolo
    f2 = font(int(size * 0.12))
    d.text((size / 2, size * 0.72), "CAMPO GARA", font=f2, fill=(232, 238, 246), anchor="mm")
    im.save(os.path.join(BASE, f"icon-{size}.png"))

make_icon(192)
make_icon(512)
print("OK icon-192.png, icon-512.png")
print("PWA pronta.")
