# -*- coding: utf-8 -*-
"""Verifica PWA offline su GitHub Pages: registra SW, va offline, ricarica."""
from playwright.sync_api import sync_playwright

URL = "https://marinovinc.github.io/CampoGara3D/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()

    page.goto(URL, wait_until="load")
    # attende registrazione + attivazione service worker
    page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.ready", timeout=30000)
    sw = page.evaluate("async () => { const r = await navigator.serviceWorker.ready; return !!r.active; }")
    print("Service worker attivo:", sw)
    # lascia tempo alla cache di popolarsi (install -> addAll degli ASSETS, incl. 8MB)
    page.wait_for_timeout(8000)
    cached = page.evaluate("""async () => {
        const ks = await caches.keys();
        if (!ks.length) return {keys: ks, n: 0};
        const c = await caches.open(ks[0]);
        const reqs = await c.keys();
        return {keys: ks, n: reqs.length, urls: reqs.map(r => r.url.split('/').pop())};
    }""")
    print("Cache:", cached)

    # OFFLINE: stacca la rete e ricarica
    ctx.set_offline(True)
    print("--- rete OFFLINE ---")
    page.reload(wait_until="load")
    page.wait_for_timeout(2500)
    has_plotly = page.evaluate("() => !!(window.Plotly) || document.body.innerHTML.indexOf('plotly') > -1")
    plot_div = page.locator(".plotly, .js-plotly-plot, .plot-container").count()
    title = page.title()
    print("OFFLINE reload -> Plotly presente:", has_plotly, "| plot div:", plot_div, "| title:", title)
    print("ESITO:", "OK offline" if (has_plotly or plot_div > 0) else "FAIL")

    browser.close()
