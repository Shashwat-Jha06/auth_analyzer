"""
Selenium-based scraper using Chrome.
Runs all blocking Selenium code in a thread executor so it never blocks
the asyncio event loop (critical for SSE streaming to work during scraping).
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Any, Optional
from app.models import ScrapeResult

# One shared thread pool — Selenium is CPU/IO bound, one thread at a time is fine
_executor = ThreadPoolExecutor(max_workers=2)


class SeleniumScraper:
    """Chrome-based scraper. Async interface; all blocking work runs off the event loop."""

    def __init__(self):
        self.viewport = {"width": 1920, "height": 1080}

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def scrape_with_triggers(self, url: str, event_queue=None) -> ScrapeResult:
        """Scrape URL asynchronously — Selenium runs in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._scrape_sync,
            url,
            event_queue,
        )

    # ------------------------------------------------------------------
    # Synchronous implementation (runs inside the thread pool)
    # ------------------------------------------------------------------

    def _scrape_sync(self, url: str, event_queue=None) -> ScrapeResult:
        print(f"[SeleniumScraper] Starting scrape of {url}")

        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            f"--window-size={self.viewport['width']},{self.viewport['height']}"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Selenium Manager (built into Selenium 4.6+) auto-downloads the correct
        # ChromeDriver for whatever Chrome version is installed — no webdriver-manager needed.
        print("[SeleniumScraper] Initializing Chrome driver via Selenium Manager...")
        driver = webdriver.Chrome(options=chrome_options)

        try:
            print(f"[SeleniumScraper] Navigating to {url}")
            driver.get(url)
            time.sleep(3)

            initial_html = driver.page_source
            print(f"[SeleniumScraper] Initial HTML: {len(initial_html)} chars")

            # Handle Cloudflare / bot-detection challenges
            if "just a moment" in initial_html.lower() or "checking your browser" in initial_html.lower():
                print("[SeleniumScraper] Detected challenge page, waiting...")
                time.sleep(5)
                initial_html = driver.page_source

            triggered_states: List[Dict[str, Any]] = []
            final_html = initial_html

            login_selectors = [
                (By.LINK_TEXT, "Log In"),
                (By.LINK_TEXT, "Sign In"),
                (By.LINK_TEXT, "Login"),
                (By.PARTIAL_LINK_TEXT, "log in"),
                (By.PARTIAL_LINK_TEXT, "sign in"),
                (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'log in')]"),
                (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]"),
                (By.CSS_SELECTOR, "a[href*='login']"),
                (By.CSS_SELECTOR, "a[href*='signin']"),
                (By.CSS_SELECTOR, "button[class*='login']"),
                (By.CSS_SELECTOR, "a[class*='login']"),
            ]

            print("[SeleniumScraper] Searching for login triggers...")
            login_trigger_found = False

            for by_method, selector in login_selectors:
                try:
                    element = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((by_method, selector))
                    )
                    if element:
                        try:
                            trigger_text = element.text[:50] if element.text else selector
                        except Exception:
                            trigger_text = selector

                        print(f"[SeleniumScraper] Clicking: '{trigger_text}'")
                        initial_url = driver.current_url
                        element.click()
                        login_trigger_found = True
                        time.sleep(2)

                        current_url = driver.current_url
                        if current_url != initial_url:
                            print(f"[SeleniumScraper] URL changed -> {current_url}")
                            try:
                                WebDriverWait(driver, 8).until(
                                    lambda d: (
                                        d.find_elements(By.CSS_SELECTOR, "input[type='password']")
                                        or d.find_elements(By.CSS_SELECTOR, "input[type='email']")
                                        or d.find_elements(By.CSS_SELECTOR, "input[name*='username' i]")
                                    )
                                )
                                print("[SeleniumScraper] Login form detected!")
                                time.sleep(2)
                            except TimeoutException:
                                print("[SeleniumScraper] No form inputs after 8 s, continuing...")
                                time.sleep(2)
                        else:
                            print("[SeleniumScraper] URL unchanged, checking for modal...")
                            time.sleep(3)

                        final_html = driver.page_source
                        print(f"[SeleniumScraper] Triggered HTML: {len(final_html)} chars")

                        triggered_states.append(
                            {
                                "trigger": {
                                    "description": f"Clicked login trigger: {trigger_text}",
                                    "selector": f"{by_method}={selector}",
                                },
                                "html_before": initial_html,
                                "html_after": final_html,
                            }
                        )
                        break

                except (TimeoutException, NoSuchElementException):
                    continue
                except Exception as e:
                    print(f"[SeleniumScraper] Error with selector {selector}: {e}")
                    continue

            if not login_trigger_found:
                print("[SeleniumScraper] No login triggers found or clicked")

            soup = BeautifulSoup(final_html, "lxml")
            page_title = soup.title.string if soup.title else "No title"

            return ScrapeResult(
                initial_html=final_html,
                final_url=driver.current_url,
                page_title=page_title,
                network_requests=[],
                triggered_states=triggered_states,
            )

        except Exception as e:
            print(f"[SeleniumScraper] Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            print("[SeleniumScraper] Closing browser...")
            driver.quit()
