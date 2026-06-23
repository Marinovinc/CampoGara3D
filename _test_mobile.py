# -*- coding: utf-8 -*-
"""Verifica resa mobile su iPhone emulato (GitHub Pages)."""
from playwright.sync_api import sync_playwright

URL = "https://marinovinc.github.io/CampoGara3D/?cb=mob"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    iphone = p.devices["iPhone 12"]
    ctx = browser.new_context(**iphone)
    page = ctx.new_page()
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(4000)

    vp = page.viewport_size
    # viewport meta presente?
    has_vp = page.evaluate("() => { const m=document.querySelector('meta[name=viewport]'); return m? m.content : null; }")
    # il plot riempie lo schermo?
    dim = page.evaluate("""() => {
        const d = document.querySelector('.plotly-graph-div');
        if (!d) return null;
        const r = d.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height) };
    }""")
    # modebar presente + scala applicata
    mb = page.evaluate("""() => {
        const m = document.querySelector('.modebar');
        if (!m) return null;
        const cs = getComputedStyle(m);
        const btns = document.querySelectorAll('.modebar-btn').length;
        const rect = m.getBoundingClientRect();
        return { transform: cs.transform, buttons: btns, h: Math.round(rect.height) };
    }""")
    # canvas WebGL della scena 3D presente?
    gl = page.evaluate("() => document.querySelectorAll('canvas').length")

    print("Schermo emulato (iPhone 12):", vp)
    print("viewport meta:", has_vp)
    print("plot div (px):", dim, "  -> riempie lo schermo:", bool(dim and dim['w'] >= vp['width']-2 and dim['h'] >= vp['height']-2))
    print("modebar:", mb)
    print("canvas WebGL:", gl)
    page.screenshot(path="D:/Dev/CampoGara3D/_test_mobile.png")
    print("screenshot salvato")
    browser.close()
