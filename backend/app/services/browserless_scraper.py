"""
Browserless.io scraper — no clicking, no triggers.
Loads the page, waits for full render, returns the complete HTML.
All extraction is done on the Python side via html_extractor.
"""
import aiohttp
import uuid
from bs4 import BeautifulSoup
from app.models import ScrapeResult


class BrowserlessScraper:
    """Cloud browser scraper via Browserless.io REST API."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://chrome.browserless.io"

    async def scrape_with_triggers(self, url: str, event_queue=None) -> ScrapeResult:
        """
        Load the URL in a headless cloud browser, wait for full JS render,
        and return the complete page HTML. No clicking — pure extraction.
        """
        print(f"[BrowserlessScraper] Scraping {url}")

        if event_queue:
            event_queue.put({
                "event": "progress",
                "stage": "scraping",
                "timestamp": str(uuid.uuid4()),
                "data": {"message": "Launching cloud browser..."}
            })

        # JavaScript executed inside the Browserless browser
        script = r"""
        export default async ({ page, context }) => {
            const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

            // Realistic viewport + headers
            await page.setViewport({ width: 1440, height: 900 });
            await page.setExtraHTTPHeaders({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.google.com/',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none'
            });

            // Navigate — wait for no pending network requests at all
            await page.goto(context.url, { waitUntil: 'networkidle0', timeout: 45000 });

            // Extra wait for JS frameworks (React, Vue) to hydrate and render
            // dynamic components like OAuth buttons that load after initial paint
            await wait(5000);

            // Capture full rendered HTML
            const html = await page.content();
            const finalUrl = page.url();

            console.log('Page loaded:', finalUrl, '| HTML size:', html.length, 'chars');

            return { html, finalUrl };
        };
        """

        async with aiohttp.ClientSession() as session:
            api_url = f"{self.base_url}/function?token={self.token}"
            payload = {"code": script, "context": {"url": url}}

            if event_queue:
                event_queue.put({
                    "event": "progress",
                    "stage": "scraping",
                    "timestamp": str(uuid.uuid4()),
                    "data": {"message": "Page loading and rendering..."}
                })

            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=90)) as response:
                print(f"[BrowserlessScraper] Response status: {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Browserless API error {response.status}: {error_text[:300]}")

                result = await response.json()

        html = result.get("html", "") if isinstance(result, dict) else ""
        final_url = result.get("finalUrl", url) if isinstance(result, dict) else url

        print(f"[BrowserlessScraper] Got {len(html)} chars of HTML from {final_url}")

        if event_queue:
            event_queue.put({
                "event": "progress",
                "stage": "scraping",
                "timestamp": str(uuid.uuid4()),
                "data": {"message": f"Page captured ({len(html):,} chars) — extracting auth components..."}
            })

        soup = BeautifulSoup(html, "lxml")
        page_title = soup.title.string if soup.title else "No title"

        return ScrapeResult(
            initial_html=html,
            final_url=final_url,
            page_title=page_title,
            network_requests=[],
            triggered_states=[],   # no clicking — single-pass extraction
        )
