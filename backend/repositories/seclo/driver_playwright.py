import logging
from pathlib import Path
from time import sleep

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def test_container():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Create a new page
        page = browser.new_page()
        
        print("Navigating to x.com...")
        page.goto("https://x.com")
        
        title = page.title()
        print(f"Page title: {title}")

def full_test():
    logger.debug("Start container test")
    logger.debug("Cool!")
    # for log in pwcontainer.logs(stream=True):
    #     print(log)
    # print("shoot")
    test_container()
