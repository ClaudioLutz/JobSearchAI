"""
Web Content Fetcher - Reliable content extraction from any URL.

Uses multiple strategies with automatic fallback:
1. Jina Reader API (handles JS, PDFs, dynamic content - free)
2. Playwright with stealth (for sites that block Jina)
3. Simple requests (last resort fallback)
"""

import requests
from typing import Optional, Tuple
from urllib.parse import quote

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("web_content_fetcher")

# Jina Reader API - free, handles JS/PDF/dynamic content
JINA_READER_BASE = "https://r.jina.ai/"

# Request timeout settings
DEFAULT_TIMEOUT = 30
JINA_TIMEOUT = 60  # Jina may take longer for complex pages


def fetch_with_jina_reader(url: str, timeout: int = JINA_TIMEOUT) -> Optional[str]:
    """
    Fetch URL content using Jina Reader API.

    Jina Reader handles:
    - JavaScript-rendered pages
    - PDFs
    - Dynamic content
    - Returns clean markdown

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Markdown content or None if failed
    """
    jina_url = f"{JINA_READER_BASE}{url}"

    logger.info(f"Fetching via Jina Reader: {url}")

    try:
        headers = {
            'Accept': 'text/markdown',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(jina_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        content = response.text

        if content and len(content) > 100:
            logger.info(f"Jina Reader success: {len(content)} chars")
            return content
        else:
            logger.warning("Jina Reader returned insufficient content")
            return None

    except requests.exceptions.Timeout:
        logger.warning(f"Jina Reader timeout for {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Jina Reader failed: {e}")
        return None


def fetch_with_playwright(url: str, timeout: int = 30000) -> Optional[str]:
    """
    Fetch URL content using Playwright with stealth settings.

    Args:
        url: The URL to fetch
        timeout: Page load timeout in milliseconds

    Returns:
        Text content or None if failed
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not available")
        return None

    logger.info(f"Fetching via Playwright: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            page = context.new_page()

            # Navigate and wait for content
            page.goto(url, wait_until='networkidle', timeout=timeout)
            page.wait_for_timeout(2000)  # Extra wait for dynamic content

            # Get full HTML
            html = page.content()
            browser.close()

        # Parse HTML to text
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Remove non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'aside']):
            element.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)

        if content and len(content) > 100:
            logger.info(f"Playwright success: {len(content)} chars")
            return content
        else:
            logger.warning("Playwright returned insufficient content")
            return None

    except Exception as e:
        logger.error(f"Playwright failed: {e}")
        return None


def fetch_with_requests(url: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Simple fallback using requests (may miss dynamic content).

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Text content or None if failed
    """
    logger.info(f"Fetching via requests: {url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)

        if content and len(content) > 100:
            logger.info(f"Requests success: {len(content)} chars")
            return content
        else:
            logger.warning("Requests returned insufficient content")
            return None

    except Exception as e:
        logger.error(f"Requests failed: {e}")
        return None


def fetch_page_content(url: str, prefer_jina: bool = True) -> Tuple[Optional[str], str]:
    """
    Fetch page content using the best available method with automatic fallback.

    Strategy order:
    1. Jina Reader (if prefer_jina=True) - best for JS/PDF/dynamic
    2. Playwright - for sites that block Jina
    3. Simple requests - last resort

    Args:
        url: The URL to fetch
        prefer_jina: Whether to try Jina Reader first (recommended)

    Returns:
        Tuple of (content, method_used) or (None, 'failed')
    """
    logger.info(f"Fetching content from: {url}")

    # Strategy 1: Jina Reader (handles most cases including JS/PDF)
    if prefer_jina:
        content = fetch_with_jina_reader(url)
        if content:
            return content, 'jina_reader'

    # Strategy 2: Playwright
    content = fetch_with_playwright(url)
    if content:
        return content, 'playwright'

    # Strategy 3: Simple requests (fallback)
    content = fetch_with_requests(url)
    if content:
        return content, 'requests'

    # If Jina was skipped, try it as last resort
    if not prefer_jina:
        content = fetch_with_jina_reader(url)
        if content:
            return content, 'jina_reader'

    logger.error(f"All fetch methods failed for: {url}")
    return None, 'failed'


# Convenience function for job extraction pipeline
def get_job_page_content(job_url: str) -> Optional[str]:
    """
    Fetch job posting page content - optimized for job sites.

    This is the main entry point for the job extraction pipeline.
    Uses Jina Reader as primary method since it handles:
    - JavaScript-rendered job postings
    - Embedded PDFs
    - Dynamic content loading

    Args:
        job_url: URL of the job posting

    Returns:
        Page content as text/markdown, or None if failed
    """
    content, method = fetch_page_content(job_url, prefer_jina=True)

    if content:
        logger.info(f"Successfully fetched job page using {method}")
        return content

    return None


if __name__ == '__main__':
    # Test the fetcher
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    test_url = "https://www.ostjob.ch/job/it-system-engineer-in-m-w-d-pensum-80-100/1044613"

    print(f"\nTesting content fetcher with: {test_url}\n")

    content, method = fetch_page_content(test_url)

    if content:
        print(f"Success! Method: {method}")
        print(f"Content length: {len(content)} chars")
        print("\n--- First 1000 chars ---")
        print(content[:1000])
    else:
        print("Failed to fetch content")
