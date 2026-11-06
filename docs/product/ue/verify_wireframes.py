from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PAGE = (ROOT / "wireframes.html").resolve()
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
    page.goto(PAGE.as_uri(), wait_until="load")
    page.wait_for_timeout(600)
    cards = page.locator(".wf-card").count()
    links = page.locator(".wf-open").count()
    map_links = page.locator('.wf-open[href^="page-map.html#"]').count()
    print("cards:", cards)
    print("links:", links)
    print("map links:", map_links)
    (ROOT / "verification").mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT / "verification" / "wireframes.png"), full_page=False)
    print("console errors:", len(errors))
    for error in errors[:10]:
        print(error)
    browser.close()
