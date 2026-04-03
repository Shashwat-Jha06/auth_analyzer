from playwright.async_api import async_playwright, Browser, Page
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import asyncio
import sys
from app.config import settings
from app.models import TriggerAction, ScrapeResult

# Windows + Python 3.12 fix for Playwright subprocess issues
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class DeepScraper:
    """
    Deep scraping with Playwright - handles JavaScript rendering,
    trigger detection, and lazy-loaded authentication components.
    """
    
    def __init__(self, browserless_token: Optional[str] = None):
        self.browserless_token = browserless_token or settings.BROWSERLESS_TOKEN
        self.browser: Optional[Browser] = None
        self.network_requests: List[str] = []
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.launch_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close_browser()
    
    async def launch_browser(self):
        """Launch browser (local or Browserless)"""
        if self.browserless_token:
            # Use Browserless.io - connect directly via CDP (no local driver needed)
            print(f"[Scraper] Connecting to Browserless.io...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"wss://chrome.browserless.io?token={self.browserless_token}"
            )
            print(f"[Scraper] Connected to Browserless successfully")
        else:
            # Use local Chromium for development (requires Python 3.11 or subprocess support)
            print(f"[Scraper] Launching local Chromium...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True
            )
    
    async def close_browser(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def scrape_with_triggers(self, url: str) -> ScrapeResult:
        """
        Main scraping method with trigger detection and execution.
        Returns complete scrape result with all states.
        """
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Track network requests
        self.network_requests = []
        page.on('request', lambda req: self.network_requests.append(req.url))
        
        try:
            # Stage 1: Initial page load
            print(f"[Scraper] Navigating to {url}")
            await page.goto(str(url), wait_until='networkidle', timeout=settings.SCRAPE_TIMEOUT)
            
            # Wait for JavaScript to execute
            await page.wait_for_timeout(settings.WAIT_FOR_NETWORK_IDLE)
            
            initial_html = await page.content()
            page_title = await page.title()
            
            print(f"[Scraper] Initial page loaded: {page_title}")
            
            # Stage 2: Detect potential triggers
            triggers = await self._detect_triggers(page, initial_html)
            
            print(f"[Scraper] Detected {len(triggers)} potential triggers")
            
            # Stage 3: Execute triggers and capture state changes
            triggered_states = []
            for trigger in triggers[:5]:  # Limit to 5 triggers to avoid timeouts
                try:
                    html_before = await page.content()
                    
                    # Execute trigger
                    await self._execute_trigger(page, trigger)
                    
                    # Wait for changes
                    await page.wait_for_timeout(2000)
                    
                    html_after = await page.content()
                    
                    # Check if HTML changed
                    if html_before != html_after:
                        triggered_states.append({
                            'trigger': trigger.dict(),
                            'html_before': html_before,
                            'html_after': html_after,
                            'new_elements': await self._find_new_elements(page, html_before, html_after)
                        })
                        print(f"[Scraper] Trigger '{trigger.description}' revealed new content")
                    else:
                        print(f"[Scraper] Trigger '{trigger.description}' - no change")
                
                except Exception as e:
                    print(f"[Scraper] Error executing trigger: {e}")
                    continue
            
            final_url = page.url
            
            return ScrapeResult(
                initial_html=initial_html,
                triggered_states=triggered_states,
                network_requests=self.network_requests,
                page_title=page_title,
                final_url=final_url
            )
        
        finally:
            await context.close()
    
    async def _detect_triggers(self, page: Page, html: str) -> List[TriggerAction]:
        """
        Detect potential triggers that might reveal authentication components.
        Uses heuristics to find buttons, links, and actions.
        """
        triggers = []
        
        # Common auth trigger patterns
        auth_text_patterns = [
            'sign in', 'log in', 'login', 'signin',
            'sign up', 'signup', 'register', 'create account',
            'get started', 'join', 'member'
        ]
        
        # 1. Find clickable buttons/links with auth-related text
        for pattern in auth_text_patterns:
            try:
                # Try to find button
                button_selector = f"button:has-text('{pattern}')"
                if await page.locator(button_selector).first.count() > 0:
                    triggers.append(TriggerAction(
                        action_type='click',
                        selector=button_selector,
                        description=f"Click button: '{pattern}'"
                    ))
                
                # Try to find link
                link_selector = f"a:has-text('{pattern}')"
                if await page.locator(link_selector).first.count() > 0:
                    triggers.append(TriggerAction(
                        action_type='click',
                        selector=link_selector,
                        description=f"Click link: '{pattern}'"
                    ))
            except:
                pass
        
        # 2. Find common login routes
        common_routes = ['/login', '/signin', '/auth', '/register', '/signup']
        current_url = page.url
        
        for route in common_routes:
            if route not in current_url:
                base_url = current_url.split('?')[0].rstrip('/')
                login_url = base_url + route
                triggers.append(TriggerAction(
                    action_type='navigate',
                    url=login_url,
                    description=f"Navigate to {route}"
                ))
        
        # 3. Find user icon/menu triggers
        user_icon_selectors = [
            '[aria-label*="user" i]',
            '[aria-label*="account" i]',
            '[aria-label*="profile" i]',
            '.user-menu',
            '#user-menu',
            '.account-menu'
        ]
        
        for selector in user_icon_selectors:
            try:
                if await page.locator(selector).first.count() > 0:
                    triggers.append(TriggerAction(
                        action_type='click',
                        selector=selector,
                        description=f"Click user menu: {selector}"
                    ))
            except:
                pass
        
        # Deduplicate triggers
        seen = set()
        unique_triggers = []
        for trigger in triggers:
            key = f"{trigger.action_type}:{trigger.selector or trigger.url}"
            if key not in seen:
                seen.add(key)
                unique_triggers.append(trigger)
        
        return unique_triggers[:10]  # Return top 10 triggers
    
    async def _execute_trigger(self, page: Page, trigger: TriggerAction):
        """
        Execute a trigger action (click, navigate, hover).
        """
        try:
            if trigger.action_type == 'click' and trigger.selector:
                # Click with timeout
                element = page.locator(trigger.selector).first
                await element.click(timeout=5000)
                await page.wait_for_load_state('networkidle', timeout=5000)
            
            elif trigger.action_type == 'navigate' and trigger.url:
                # Navigate to URL
                await page.goto(trigger.url, wait_until='networkidle', timeout=10000)
            
            elif trigger.action_type == 'hover' and trigger.selector:
                # Hover over element
                element = page.locator(trigger.selector).first
                await element.hover(timeout=5000)
                await page.wait_for_timeout(1000)
        
        except Exception as e:
            print(f"[Scraper] Failed to execute trigger: {e}")
            raise
    
    async def _find_new_elements(self, page: Page, html_before: str, html_after: str) -> List[str]:
        """
        Find new elements that appeared after trigger.
        """
        soup_before = BeautifulSoup(html_before, 'html.parser')
        soup_after = BeautifulSoup(html_after, 'html.parser')
        
        # Simple approach: find forms/inputs in after that aren't in before
        new_forms = []
        
        for form in soup_after.find_all('form'):
            if str(form) not in html_before:
                new_forms.append(str(form))
        
        for input_elem in soup_after.find_all('input', type='password'):
            if str(input_elem) not in html_before:
                new_forms.append(str(input_elem))
        
        return new_forms[:10]  # Limit to 10 new elements
