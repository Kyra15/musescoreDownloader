import requests
import re
import os
from patchright.async_api import async_playwright
import base64
import tempfile

saved_pages_data = {}

async def handle_response(response):

    if re.search(r"/score_\d+\.(svg|png)", response.url):
        page_num = re.search(r"score_(\d+)", response.url)
        idx = int(page_num.group(1)) if page_num else len(saved_pages_data)
        # print("SVG:", response.url)

        if response.status == 200 and idx not in saved_pages_data:
            data_bytes = await response.body()
            ext = "svg+xml" if ".svg" in response.url else "png"
            b64_str = base64.b64encode(data_bytes).decode('utf-8')
            data_uri = f"data:image/{ext};base64,{b64_str}"

            saved_pages_data[idx] = data_uri
            print(f"{idx} ({ext}): {len(data_bytes)} bytes")


async def scrape_musescore(ex_str):

    async with async_playwright() as p:
        user_data_dir = os.path.join(tempfile.gettempdir(), "chrome_profile")

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
            wait_time = 0
            max_wait = 20000

            while i not in saved_pages_data and wait_time < max_wait:
                await page.wait_for_timeout(500)
                wait_time += 500
                    
            if i in saved_pages_data:
                print(f"page {i} loaded after {wait_time} ms")
            else:
                print(f"page {i} didn't load after {max_wait} ms")
            
        # page.wait_for_timeout(1000)
        print("finished scraping")
        await context.close()


async def convert_with_playwright(page_data_dict):
    sorted_indices = sorted(page_data_dict.keys())

    html_content = "<!DOCTYPE html><html><body style='margin:0; padding:0;'>"
    for idx in sorted_indices:
        data_uri = page_data_dict[idx]
        html_content += f"<img src='{data_uri}' style='width: 100vw; display: block; page-break-after: always;' />\n"
    html_content += "</body></html>"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--headless=new", "--no-sandbox"]
        )
        page = await browser.new_page()

        await page.set_content(html_content, wait_until="load")
        
        pdf_bytes = await page.pdf(
            print_background=True,
            width="8.27in",
            height="11.69in",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        await browser.close()

    print("success, pdf created")
    return pdf_bytes



# if __name__ == "__main__":
#     ex_str = "https://musescore.com/user/76891138/scores/36754394"

#     if os.path.exists("pages"):
#         shutil.rmtree("pages")
#     os.makedirs("pages")
#     scrape_musescore(ex_str)
#     convert_with_playwright()

