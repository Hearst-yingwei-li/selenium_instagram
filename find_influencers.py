from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
import pytz
import unicodedata
import json
import os
import logging
from enum import Enum
import requests
import asyncio
import argparse


async def execute(client, media, start_date, end_date):
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")

    # Specify the path to the chromedriver executable
    chrome_driver_path = "C:/Users/ddadmin/Desktop/tools/chromedriver-win64/chromedriver.exe"  # chromedriver path

    # Set up the WebDriver with Chrome options
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    window_handles = driver.window_handles
    for handle in window_handles:
        # Switch to the tab
        driver.switch_to.window(handle)

        # Check if the current tab is Instagram by inspecting the URL or title
        if "instagram.com" in driver.current_url:
            print("Found Instagram session")
            print(f"Instagram URL: {driver.current_url}")
            break
        else:
            print(f"Other tab URL: {driver.current_url}")

    # Now you can interact with the Instagram session
    # Example: Print the page title
    print("Page title:", driver.title)
    logging.debug(f"Page title: {driver.title}")
    # Scroll to top to prevent effect from previous process
    # driver.execute_script(f"window.scrollBy(0,{0});")

    if client:
        pass


async def run():
    parser = argparse.ArgumentParser(description="Find influencers")
    parser.add_argument(
        "--hashtag",
        type=str,
        required=True,
        help="hashtag name",
    )

    # Parse the arguments
    args = parser.parse_args()
    hashtag = args.hashtag
    hashtag = hashtag.strip()
    # -------------
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")

    # Specify the path to the chromedriver executable
    chrome_driver_path = "C:/Users/ddadmin/Desktop/tools/chromedriver-win64/chromedriver.exe"  # chromedriver path

    # Set up the WebDriver with Chrome options
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    window_handles = driver.window_handles
    for handle in window_handles:
        # Switch to the tab
        driver.switch_to.window(handle)

        # Check if the current tab is Instagram by inspecting the URL or title
        if "instagram.com" in driver.current_url:
            print("Found Instagram session")
            print(f"Instagram URL: {driver.current_url}")
            break
        else:
            print(f"Other tab URL: {driver.current_url}")

    # Now you can interact with the Instagram session
    # Example: Print the page title
    print("Page title:", driver.title)
    print(driver.title)  # Print the title of the currently opened page

    # check existing data
    check_existing_data(media, start_date, end_date)
    # get post list
    await get_all_post_urls(driver=driver, start_date=start_date, end_date=end_date)
    # extract post data one by one
    await get_post_info(driver, media, start_date, end_date)
    print(f"<<< -------------------- list_post_link -- {list_post_link}")


if __name__ == "__main__":
    asyncio.run(run())
