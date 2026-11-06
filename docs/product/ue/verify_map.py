from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
MAP = (ROOT / "page-map.html").resolve()
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
    page.goto(MAP.as_uri(), wait_until="load")
    page.wait_for_timeout(800)
    print("screens:", page.locator(".screen").count())
    print("edges:", page.locator(".edge-line").count())
    (ROOT / "verification").mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT / "verification" / "overview.png"), full_page=False)

    page.locator('.screen[data-id="MP01"]').click(force=True)
    page.wait_for_timeout(700)
    print("inspector hidden:", page.locator("#inspector").get_attribute("hidden"))
    print("title:", page.locator("#inspector h1").inner_text())
    page.screenshot(path=str(ROOT / "verification" / "selected.png"), full_page=False)

    # interaction tab + target jump
    tab = page.locator('#tab-interaction')
    if not tab.is_disabled():
        tab.click()
        page.wait_for_timeout(200)
        print("flow cards:", page.locator("#inspector .flow-card").count())
        first_go = page.locator("#panel-interaction .flow-target").first
        if first_go.count():
            first_go.click(force=True)
            page.wait_for_timeout(500)
            print("after jump title:", page.locator("#inspector h1").inner_text())

    page.locator("#modules").click()
    page.wait_for_timeout(150)
    module_buttons = page.locator("#module-menu button")
    print("modules:", module_buttons.count())
    if module_buttons.count() > 1:
        module_buttons.nth(1).click(force=True)
        page.wait_for_timeout(300)
        print("module title:", page.locator("#module-title").inner_text())

    # search
    page.locator("#search-toggle").click()
    page.locator("#search").fill("导入")
    page.wait_for_timeout(200)
    print("search results:", page.locator("#results button").count())
    page.keyboard.press("Escape")

    # zoom
    before = page.locator("#zoom-value").inner_text()
    page.locator("#zoom-in").click()
    page.wait_for_timeout(200)
    after = page.locator("#zoom-value").inner_text()
    print("zoom:", before, "->", after)

    # export page PNG
    page.locator('.screen[data-id="MP04"]').click(force=True)
    page.wait_for_timeout(500)
    page.locator("#export-trigger").click()
    page.wait_for_timeout(200)
    with page.expect_download(timeout=20000) as dl:
        page.locator("#export-page").click()
    download = dl.value
    download.save_as(str(ROOT / "verification" / "export-MP04.png"))
    print("download:", download.suggested_filename)

    page.locator("#export-trigger").click()
    page.wait_for_timeout(200)
    with page.expect_download(timeout=30000) as dl2:
        page.locator("#export-ue").click()
    download2 = dl2.value
    download2.save_as(str(ROOT / "verification" / "export-MP04-annotated.png"))
    print("download UE:", download2.suggested_filename)

    print("console errors:", len(errors))
    for e in errors[:10]:
        print(e)
    browser.close()
