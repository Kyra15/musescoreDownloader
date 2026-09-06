import requests
from playwright.sync_api import sync_playwright
import re
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from pypdf import PdfWriter
from playwright.async_api import async_playwright
import shutil
from patchright.async_api import async_playwright

saved_pages = set()

async def handle_response(response):

    if re.search(r"/score_\d+\.(svg|png)", response.url):
        page_num = re.search(r"score_(\d+)", response.url)
        idx = page_num.group(1) if page_num else str(len(saved_pages))
        # print("SVG:", response.url)

        if response.status == 200 and idx not in saved_pages:
            data = await response.body()
            ext = "svg" if ".svg" in response.url else "png"
            file_path = f"pages/sheet_{idx}.{ext}"

            with open(file_path, "wb") as f:
                f.write(data)

            saved_pages.add(idx)
            print(f"{idx} ({ext}): {len(data)} bytes")


async def solve_cloudflare_if_present(page):
    try:
        for frame in page.frames:
            if "cloudflare" in frame.url or "turnstile" in frame.url:
                checkbox = frame.locator('input[type="checkbox"], .mark')
                if await checkbox.is_visible():
                    print("Cloudflare checkbox detected. Clicking...")
                    await checkbox.click()
                    await page.wait_for_timeout(3000)
    except Exception as e:
        pass


async def scrape_musescore(ex_str):
    if os.path.exists("pages"):
        shutil.rmtree("pages")
    os.makedirs("pages")

    async with async_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "chrome_profile")

        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                "--headless=new",
                "--window-size=1920,1080",
                "--disable-blink-features=AutomationControlled",
                "--enable-webgl",
                "--use-gl=angle",
                "--use-angle=gl",
                "--disable-device-discovery-notifications",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ],
            viewport={"width": 1280, "height": 1000}
        )
        page = context.pages[0]

        page.on("response", handle_response)

        await page.goto(
            ex_str,
            wait_until="domcontentloaded",
            timeout=60000
        )

        solve_cloudflare_if_present(page)

        await page.mouse.wheel(0, 500)
        await page.wait_for_timeout(1000)

        # let musescore js run
        scroller_selector = '[id^="jmuse-scroller-component"]'
        await page.wait_for_selector(scroller_selector, state="attached", timeout=20000)
        scroll_component = page.locator(scroller_selector).first

        children = scroll_component.locator(":scope > .SQS_G")
        await page.wait_for_timeout(2000)
        counter = await children.count()
        for i in range(counter):
            print(f"\nSCROLLING PAGE {i}")

            child = children.nth(i)

            # stupid lazy-loading
            await child.evaluate("el => el.scrollIntoView({ behavior: 'smooth', block: 'center' })")
            expected_idx = str(i)
            wait_time = 0
            max_wait = 20000

            while expected_idx not in saved_pages and wait_time < max_wait:
                await page.wait_for_timeout(500)
                wait_time += 500
                    
            if expected_idx in saved_pages:
                print(f"page {i} loaded after {wait_time} ms")
            else:
                print(f"page {i} didn't load after {max_wait} ms")
            
        # page.wait_for_timeout(1000)
        print("finished scraping")
        await context.close()


def convert_with_playwright():

    pages_dir = os.path.abspath("pages")
    
    if not os.path.exists(pages_dir):
        print(f"dir not found: {pages_dir}")
        return

    files = [f for f in os.listdir(pages_dir) if f.endswith((".svg", ".png"))]
    files.sort(key=lambda x: int(re.search(r'\d+', x).group()))

    if not files:
        print("no pages found to convert")
        return

    html_content = "<!DOCTYPE html><html><body style='margin:0; padding:0;'>"
    for filename in files:
        file_path = os.path.join(pages_dir, filename)
        html_content += f"<img src='file://{file_path}' style='width: 100vw; display: block; page-break-after: always;' />\n"
    html_content += "</body></html>"

    html_path = os.path.abspath("temp_score.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(2000)
        
        page.pdf(
            path="static/output_score.pdf",
            print_background=True,
            width="8.27in", # a4 dimensions
            height="11.69in",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        browser.close()

    if os.path.exists(html_path):
        os.remove(html_path)
        
    print("success, pdf created")



# if __name__ == "__main__":
#     ex_str = "https://musescore.com/user/76891138/scores/36754394"

#     if os.path.exists("pages"):
#         shutil.rmtree("pages")
#     os.makedirs("pages")
#     scrape_musescore(ex_str)
#     convert_with_playwright()

