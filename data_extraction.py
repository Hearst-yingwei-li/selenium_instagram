import argparse
import asyncio
import time
import re
import random
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
import pytz
import unicodedata
import json
import os
import logging
from enum import Enum
import requests

# Configure logging to write to a file
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,  # Set the logging level
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class EnumTimeSpread(Enum):
    LATER = "later"
    MIDDLE = "middle"
    EARLIER = "earlier"
    PIN_EARLIER = "pin_earlier"


TAG_END_OF_LOOP = "END"
# TODO:FIXME:
SPREAD_SHEET_NAME = "Instagramインサイトデータ更新"
WEB_DRIVER_WAIT_TIME = 10
# SPREAD_SHEET_NAME = "Instagramインサイトデータ更新" # "test_instagram"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SLEEP_MIN = 40
SLEEP_MAX = 55
# send message to slack channel/group

SLACK_CHANNEL_MAIL = "aaaaovuxkzuchgnf7qmnfiasc4@hearstmedia.slack.com"
SUBJECT = "[syssv037]Task Completed"
# BODY = "The task has been completed successfully!"
#
obj_post_data = {}
save_rows = []
list_skip = []
list_post_link = []
post_view_height = None

# To avoid Instagram API request restriction (200 api call/hour)
sleep_needed = True
creds = None


def send_email_to_slack(media, start_date, end_date):
    try:
        # Create the email message
        requests.post(
            "https://sp.hearst.co.jp/miscellaneous/mail/send.php",
            data={
                "k": "99d168c18cc88e6af1f1057b7400fe88",
                "title": f"[syssv037] {media}_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}",
                "body": "Task done: Insight data extraction",
                "from": "yingwei.li@hearst.co.jp",
                "to": SLACK_CHANNEL_MAIL,
            },
            verify=False,
        )
    except Exception as e:
        print(f"Error sending email: {e}")
        logging.debug(f"Error sending email: {e}")


def is_pin_post(post_div):
    try:
        svg_element = WebDriverWait(post_div, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.TAG_NAME, "svg"))
        )
        aria_label = svg_element.get_attribute("aria-label")
        # svg_element = post_div.find_element(By.XPATH,".//svg[@aria-label='固定された投稿のアイコン']")
        return aria_label == "固定された投稿のアイコン"
    except NoSuchElementException:
        print("NoSuchElementException: pin post icon")
        logging.debug("<<< NoSuchElementException: pin post icon")
        return False
    except TimeoutException:
        print("TimeoutException: pin post icon")
        return False


async def get_post_time_spread(driver, obj_post, start_date, end_date):
    timezone = pytz.timezone("Asia/Tokyo")
    start_date = timezone.localize(start_date)
    #
    end_date = timezone.localize(end_date)
    #
    # home_window = driver.current_window_handle
    driver.switch_to.new_window("tab")

    driver.get(obj_post["url"])
    time.sleep(5)
    try:
        time_tag = WebDriverWait(driver, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.TAG_NAME, "time"))
        )
        post_time_str = time_tag.get_attribute("datetime")
        post_time = datetime.fromisoformat(
            post_time_str.replace("Z", "+00:00")
        )  # UTC timezone
        post_time = post_time.astimezone(timezone)
        # print(f'get post insight data -------- post date -- {date_time} --------')
        # check post date
        if post_time > end_date:
            list_skip.append(obj_post["url"])
            # close_current_tab(driver, home_window)
            return EnumTimeSpread.LATER, post_time
        elif post_time < start_date:
            # check if is pin post
            is_pin = obj_post["is_pin"]
            if is_pin:
                list_skip.append(obj_post["url"])
                return EnumTimeSpread.PIN_EARLIER, post_time
            else:
                return EnumTimeSpread.EARLIER, post_time
        else:
            return EnumTimeSpread.MIDDLE, post_time

    except TimeoutException:
        # close_current_tab(driver, home_window)
        print("<<< time out exception: post date time")
        logging.debug("<<< timeout exception: post date time")
        return EnumTimeSpread.MIDDLE, None
    except NoSuchElementException:
        # close_current_tab(driver, home_window)
        print("<<< no such element exception: post date time")
        logging.debug("<<< no such element exception: post date time")
        return EnumTimeSpread.MIDDLE, None


def is_url_already_exist(post_url):
    for obj in list_post_link:
        if obj["url"] == post_url:
            return True
    return False


async def get_all_post_urls(driver, start_date, end_date):
    print("<<< get all post urls")
    home_window = driver.current_window_handle
    try:
        mainDiv = WebDriverWait(driver, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "//main[@role='main']"))
        )
        mainChildContainer = WebDriverWait(mainDiv, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(mainChildContainer) == 0:
            return [], 285, 0
        post_containers = WebDriverWait(mainChildContainer[0], 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(post_containers) == 0:
            return [], 285, 0
        postContainer = post_containers[-1]
        postStyleDivs = WebDriverWait(postContainer, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(postStyleDivs) == 0:
            return [], 285, 0
        postStyleDiv = postStyleDivs[0]
        postRowContainer = WebDriverWait(postStyleDiv, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(postRowContainer) == 0:
            return [], 285, 0

        for div_row in postRowContainer:
            divs = div_row.find_elements(By.XPATH, "div")
            # print(f"Number of <div> elements in each row: {len(divs)}")
            for div in divs:
                is_pin = is_pin_post(div)
                # TODO: check PIN status
                a_tags = div.find_elements(By.TAG_NAME, "a")
                if len(a_tags) > 0:
                    a_tag = a_tags[0]
                    href = a_tag.get_attribute("href")
                    if not is_url_already_exist(href):
                        obj_url = {"is_pin": is_pin, "url": href}
                        list_post_link.append(obj_url)
        if not list_post_link:
            return
        view_last_post = list_post_link[-1]
        time_spread, _ = await get_post_time_spread(
            driver=driver,
            obj_post=view_last_post,
            start_date=start_date,
            end_date=end_date,
        )
        close_current_tab(driver, home_window)

        global post_view_height
        if not post_view_height:
            post_view_height = driver.execute_script(
                "return arguments[0].getBoundingClientRect().height;",
                postRowContainer[0],
            )
        scroll_distance = 4 * post_view_height
        if time_spread != EnumTimeSpread.EARLIER:
            # scroll
            print("<<< scroll for more")
            await scroll_for_more(
                driver=driver,
                start_date=start_date,
                end_date=end_date,
                scroll_distance=scroll_distance,
            )
        else:
            logging.debug("<<< get all post list: scroll to end")
        # print(f'row height = {row_height}')
        # TODO: Should be a dict {url,isPined} - For pined post, even if it's post date is not in the start-end time range, instead of return TAG_END_OF_LOOP ,should let the loop go on
    except TimeoutException:
        logging.debug("<<< time out exception : get dom post url")
        await scroll_for_more(
            driver=driver,
            start_date=start_date,
            end_date=end_date,
            scroll_distance=scroll_distance,
        )
    except NoSuchElementException:
        logging.debug("<<< no such element exception : get dom post url")
        await scroll_for_more(
            driver=driver,
            start_date=start_date,
            end_date=end_date,
            scroll_distance=scroll_distance,
        )


async def scroll_for_more(driver, start_date, end_date, scroll_distance):
    print(f"scroll distance --- {scroll_distance}")
    driver.execute_script(f"window.scrollBy(0,{scroll_distance});")
    time.sleep(5)
    await get_all_post_urls(driver, start_date, end_date)


# get all post link
# check pin status
async def get_dom_post_urls(driver):
    post_links = []
    try:
        mainDiv = WebDriverWait(driver, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "//main[@role='main']"))
        )
        mainChildContainer = WebDriverWait(mainDiv, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(mainChildContainer) == 0:
            return [], 285, 0
        post_containers = WebDriverWait(mainChildContainer[0], 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(post_containers) == 0:
            return [], 285, 0
        postContainer = post_containers[-1]
        postStyleDivs = WebDriverWait(postContainer, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        if len(postStyleDivs) == 0:
            return [], 285, 0
        postStyleDiv = postStyleDivs[0]
        postRowContainer = WebDriverWait(postStyleDiv, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "./div"))
        )
        print(f"row count --- {len(postRowContainer)}")
        if len(postRowContainer) == 0:
            return [], 285, 0

        position_y = driver.execute_script(
            "return arguments[0].getBoundingClientRect().top;", postRowContainer[0]
        )

        for div_row in postRowContainer:
            divs = div_row.find_elements(By.XPATH, "div")
            # print(f"Number of <div> elements in each row: {len(divs)}")
            for div in divs:
                is_pin = is_pin_post(div)
                # TODO: check PIN status
                a_tags = div.find_elements(By.TAG_NAME, "a")
                if len(a_tags) > 0:
                    a_tag = a_tags[0]
                    href = a_tag.get_attribute("href")
                    obj_url = {"is_pin": is_pin, "url": href}
                    post_links.append(obj_url)
        # print(post_links)
        # print(f'dom post count ----- {len(post_links)}')
        row_height = driver.execute_script(
            "return arguments[0].getBoundingClientRect().height;", postRowContainer[0]
        )
        # print(f'row height = {row_height}')
        # TODO: Should be a dict {url,isPined} - For pined post, even if it's post date is not in the start-end time range, instead of return TAG_END_OF_LOOP ,should let the loop go on
        return post_links, row_height, position_y if position_y > 0 else 0
    except TimeoutException:
        logging.debug("<<< time out exception : get dom post url")
        return [], 285, 0
    except NoSuchElementException:
        logging.debug("<<< no such element exception : get dom post url")
        return [], 285, 0


def parseNumber(strNumber):
    if "万" in strNumber:
        str_num = strNumber[0:-1]
        value = int(float(str_num) * 10000)
        return str(value)
    return strNumber


def normalize_key(key):
    return unicodedata.normalize("NFKC", key)


# === view ===
def get_view_data(div_view_container, xpath):
    try:
        view_total = WebDriverWait(div_view_container, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return {normalize_key("ビュー"): parseNumber(view_total.text)}
    except NoSuchElementException:
        print("no such element exception: view - ビュー")
        logging.debug("<<< no such element exception: view - ビュー")
        return None
    except TimeoutException:
        print("element timeout: view - ビュー")
        logging.debug("<<< element timeout: view - ビュー")
        return None


def get_view_follower(div_view_container, xpath, is_reel):
    try:
        per_follower = WebDriverWait(div_view_container, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if is_reel:
            if re.search(r"\d", per_follower.text) or "%" in per_follower.text:
                return {
                    normalize_key("ビューフォロワー"): parseNumber(per_follower.text)
                }
            else:
                per_follower = per_follower.find_element(By.XPATH, "./div")
                return {
                    normalize_key("ビューフォロワー"): parseNumber(per_follower.text)
                }
        else:
            return {normalize_key("ビューフォロワー"): parseNumber(per_follower.text)}
    except NoSuchElementException:
        print("no such element exception: view follower - ビューフォロワー")
        logging.debug("<<< no such element exception: view follower - ビューフォロワー")
        return None
    except TimeoutException:
        print("element timeout: view follower - ビューフォロワー")
        logging.debug("<<< element timeout: view follower - ビューフォロワー")
        return None


def get_view_unfollower(div_view_container, xpath, is_reel):
    try:
        per_unfollower = WebDriverWait(div_view_container, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if is_reel:
            if re.search(r"\d", per_unfollower.text) or "%" in per_unfollower.text:
                return {
                    normalize_key("ビューフォロワー以外"): parseNumber(
                        per_unfollower.text
                    )
                }
            else:
                per_unfollower = per_unfollower.find_element(By.XPATH, "./div")
                return {
                    normalize_key("ビューフォロワー以外"): parseNumber(
                        per_unfollower.text
                    )
                }
        else:
            return {
                normalize_key("ビューフォロワー以外"): parseNumber(per_unfollower.text)
            }
    except NoSuchElementException:
        print("no such element exception: view unfollower - ビューフォロワー以外")
        logging.debug(
            "<<< no such element exception: view unfollower - ビューフォロワー以外"
        )
        return None
    except TimeoutException:
        print("element timeout exception: view unfollower - ビューフォロワー以外")
        logging.debug(
            "<<< element timeout exception: view unfollower - ビューフォロワー以外"
        )
        return None


def get_reach_count(div_view_container, xpath):
    try:
        reach_count_div = WebDriverWait(div_view_container, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        # reach_key = reach_count_div.find_element(By.XPATH, "./span")
        reach_key = WebDriverWait(reach_count_div, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "./span"))
        )
        # reach_value = reach_count_div.find_element(By.XPATH, "./div/span")
        reach_value = WebDriverWait(reach_count_div, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "./div/span"))
        )
        return {normalize_key(reach_key.text): parseNumber(reach_value.text)}
    except NoSuchElementException:
        print(
            "no such element exception: reached account/reached account center リーチしたアカウント数/リーチ済みのアカウントセンター内アカウント"
        )
        logging.debug(
            "<<< no such element exception: reached account/reached account center リーチしたアカウント数/リーチ済みのアカウントセンター内アカウント"
        )
        return None
    except TimeoutException:
        print(
            "element timeout exception: reached account/reached account center リーチしたアカウント数/リーチ済みのアカウントセンター内アカウント"
        )
        logging.debug(
            "<<< element timeout exception: reached account/reached account center リーチしたアカウント数/リーチ済みのアカウントセンター内アカウント"
        )
        return None


def get_view_source(div_view_container, xpath):
    try:
        data = {}
        view_source_div = WebDriverWait(div_view_container, WEB_DRIVER_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if view_source_div is None:
            print("No such element: view_source_div")
            logging.debug("<<< No such element: view_source_div")
            return None
        view_source_contents = view_source_div.find_elements(By.XPATH, "./div")
        logging.debug(
            f"<<< get view source ---- view source contents = {view_source_contents}"
        )
        if view_source_contents is not None:
            for content in view_source_contents:
                key_div = content.find_element(By.XPATH, "./div/div[1]/span")
                value_div = content.find_element(By.XPATH, "./div/div[2]/span")
                data[normalize_key(key_div.text)] = parseNumber(value_div.text)
            return data
        else:
            print("No such element: view_source_contents")
            logging.debug("<<< No such element: view_source_contents")
            return None
    except NoSuchElementException:
        print("no such element exception: view source container div")
        logging.debug("<<< element timeout: view source container div")
        return None
    except TimeoutException:
        print("no such element exception: view source container div")
        logging.debug("<<< element timeout: view source container div")
        return None


def parse_view(div_view_container, count_sperator):
    json_view = {}
    if count_sperator == 7:
        view_data = get_view_data(div_view_container, "./div/div/div[2]/div/span")

        view_follower_data = get_view_follower(
            div_view_container, "./div/div/div[3]/div[2]", is_reel=False
        )
        view_unfollower_data = get_view_unfollower(
            div_view_container, "./div/div/div[3]/div[4]", is_reel=False
        )
        reach_data = get_reach_count(
            div_view_container, f"./div/div/div[{count_sperator}]"
        )
        dict_view_data = get_view_source(div_view_container, "./div/div/div[5]")
        if dict_view_data:
            json_view.update(dict_view_data)
    else:
        view_data = get_view_data(
            div_view_container, "./div/div[2]/div/div[1]/div/span"
        )
        view_follower_data = get_view_follower(
            div_view_container,
            "./div/div[2]/div/div[2]/div[2]",
            is_reel=True,
        )
        view_unfollower_data = get_view_unfollower(
            div_view_container,
            "./div/div[2]/div/div[2]/div[4]",
            is_reel=True,
        )
        reach_data = get_reach_count(div_view_container, "./div/div[2]/div/div[4]")
    if view_data:
        json_view.update(view_data)
    if view_follower_data:
        json_view.update(view_follower_data)
    if view_unfollower_data:
        json_view.update(view_unfollower_data)
    if reach_data:
        json_view.update(reach_data)
    return json_view


# --- End View ---


# === Interaction ===
def get_interaction_data(interaction_container, xpath_key, xpath_value):
    try:
        interaction_key = WebDriverWait(
            interaction_container, WEB_DRIVER_WAIT_TIME
        ).until(EC.presence_of_element_located((By.XPATH, xpath_key)))

        interaction_value = WebDriverWait(
            interaction_container, WEB_DRIVER_WAIT_TIME
        ).until(EC.presence_of_element_located((By.XPATH, xpath_value)))
        # print(f'interaction key = {interaction_key.text}  interaction value = {interaction_value.text}')
        return {normalize_key(interaction_key.text): interaction_value.text}
    except NoSuchElementException:
        print("no such element exception: インタラクション")
        return None
    except TimeoutException:
        print("element timeout: インタラクション")
        return None


def get_interaction_follower_unfollower_data(
    interaction_container, xpath_key, xpath_value
):
    try:
        target_key = interaction_container.find_element(By.XPATH, xpath_key)
        target_value = interaction_container.find_element(By.XPATH, xpath_value)

        return {
            normalize_key(f"インタラクション{target_key.text}"): parseNumber(
                target_value.text
            )
        }
    except TimeoutException:
        print("element timeout: インタラクション follower & unfollower")
        return None


def get_post_interaction_data(post_interaction_div, xpath_key, xpath_value):
    try:
        post_interaction_key = WebDriverWait(
            post_interaction_div, WEB_DRIVER_WAIT_TIME
        ).until(EC.presence_of_element_located((By.XPATH, xpath_key)))
        post_interaction_value = WebDriverWait(
            post_interaction_div, WEB_DRIVER_WAIT_TIME
        ).until(EC.presence_of_element_located((By.XPATH, xpath_value)))
        return {
            normalize_key(post_interaction_key.text): parseNumber(
                post_interaction_value.text
            )
        }
        # post_interaction_key = post_interaction_div.find_element(By.XPATH, "./span")
        # post_interaction_value = post_interaction_div.find_element(By.XPATH, "./div/span")
        json_interaction[post_interaction_key.text] = parseNumber(
            post_interaction_value.text
        )
    except NoSuchElementException:
        print("no such element exception: インタラクション follower & unfollower")
        return None
    except TimeoutException:
        print("element timeout: インタラクション follower & unfollower")
        return None


def parse_interaction(div_interaction_container, count_sperator):
    json_interaction = {}
    div_children = div_interaction_container.find_elements(By.XPATH, "./div/div")
    if not div_children or len(div_children) < 6:
        logging.debug(
            f"<<< error: interaction container childer count == {len(div_children)}"
        )
        return json_interaction

    interaction_container = div_children[1]
    post_interaction_container = div_children[3]
    action_account_container = div_children[5]

    # interaction
    interaction_data = get_interaction_data(
        interaction_container, "./div/div[1]/span", "./div/div[1]/div/span"
    )
    if interaction_data:
        json_interaction.update(interaction_data)

    follower_data = get_interaction_follower_unfollower_data(
        interaction_container, "./div/div[2]/div[1]/span", "./div/div[2]/div[2]"
    )
    if follower_data:
        json_interaction.update(follower_data)

    unfollower_data = get_interaction_follower_unfollower_data(
        interaction_container, "./div/div[2]/div[3]/span", "./div/div[2]/div[4]"
    )
    if unfollower_data:
        json_interaction.update(unfollower_data)

    # post interaction
    post_children = post_interaction_container.find_elements(By.XPATH, "./div/div")
    post_interaction_div = post_children[0]

    post_interaction_data = get_post_interaction_data(
        post_interaction_div, "./span", "./div/span"
    )
    if post_interaction_data:
        json_interaction.update(post_interaction_data)

    xpath = "./div/" if count_sperator == 7 else "./"
    for element in post_children[1:]:
        key_div = element.find_element(
            By.XPATH, f"{xpath}div[1]/span"
        )  #'./div/div[1]/span'
        value_div = element.find_element(
            By.XPATH, f"{xpath}div[2]/span"
        )  #'./div/div[2]/span'
        json_interaction[key_div.text] = parseNumber(value_div.text)
        # print(f'element key = {key_div.text}   element value = {value_div.text}')

    # action account
    action_account_key = action_account_container.find_element(By.XPATH, "./span")
    action_account_value = action_account_container.find_element(By.XPATH, "./div/span")
    # print(f'action account  key = {action_account_key.text}   value = {action_account_value.text}')
    json_interaction[action_account_key.text] = parseNumber(action_account_value.text)
    return json_interaction


def parse_profile(div_profile_container):
    json_profile = {}
    profile_container = div_profile_container.find_element(By.XPATH, "./div/div[2]/div")
    children_elements = profile_container.find_elements(By.XPATH, "./div")
    profile_activity = children_elements[0]
    profile_activity_key = profile_activity.find_element(By.XPATH, "./span")
    profile_activity_value = profile_activity.find_element(By.XPATH, "./div/span")
    json_profile[normalize_key(profile_activity_key.text)] = profile_activity_value.text
    for element in children_elements[1:]:
        key_div = element.find_element(By.XPATH, "./div[1]/span")
        value_div = element.find_element(By.XPATH, "./div[2]/span")
        json_profile[normalize_key(key_div.text)] = parseNumber(value_div.text)
    return json_profile


def close_current_tab(driver, home_window):
    driver.close()
    driver.switch_to.window(home_window)
    time.sleep(1)


async def get_post_insight_data(driver, obj_post, start_date, end_date):
    home_window = driver.current_window_handle
    enum_post_time, post_time = await get_post_time_spread(
        driver=driver, obj_post=obj_post, start_date=start_date, end_date=end_date
    )
    if enum_post_time == EnumTimeSpread.EARLIER:
        close_current_tab(driver, home_window)
        print('check post time ---- earlier')
        return TAG_END_OF_LOOP
    elif enum_post_time == EnumTimeSpread.LATER:
        close_current_tab(driver, home_window)
        print('check post time ---- later')
        return None
    elif enum_post_time == EnumTimeSpread.PIN_EARLIER:
        close_current_tab(driver, home_window)
        print('check post time ---- pin earlier')
        return None
    else:
        json_output = {}
        link = obj_post["url"]
        try:
            # wait for all element in page is rendered
            # error sometimes the count_sperator is 2, seems because not all element is rendered~~
            insight_button = WebDriverWait(driver, WEB_DRIVER_WAIT_TIME).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@role='button' and text()='インサイトを見る']")
                )
            )
            driver.execute_script("arguments[0].click();", insight_button)
            print("<<< insight button clicked")
            time.sleep(5)
            WebDriverWait(driver, 10).until(EC.url_contains("insights"))
            print("<<< url contains - insights")

            # find seperators
            hr_separators = WebDriverWait(driver, WEB_DRIVER_WAIT_TIME).until(
                EC.presence_of_all_elements_located((By.XPATH, "//hr"))
            )
            count_sperator = len(hr_separators)
            if count_sperator == 7:
                main_separators = [hr_separators[2], hr_separators[5], hr_separators[6]]
            elif count_sperator == 6:
                main_separators = [hr_separators[1], hr_separators[4], hr_separators[5]]
            else:
                print(
                    f"count_sperator ------- {count_sperator} no enough info is loaded on the website"
                )
                logging.debug(
                    f"<<< count_sperator ------- {count_sperator} no enough info is loaded on the website"
                )
                close_current_tab(driver, home_window)
                return None
            div_separators = [hr.find_element(By.XPATH, "..") for hr in main_separators]
            div_info_root = div_separators[0].find_element(By.XPATH, "..")
            div_info_children = div_info_root.find_elements(By.XPATH, "./div")
            div_view_container = div_info_children[0]
            div_interaction_container = div_info_children[2]
            div_profile_container = div_info_children[4]

            # add entity - Date
            json_output["Date"] = post_time.strftime("%Y-%m-%d %H:%M:%S")
            # add entity - view related
            dict_view = parse_view(div_view_container, count_sperator)
            if dict_view:
                json_output.update(dict_view)

            # add entity - interaction related
            dict_interaction = parse_interaction(
                div_interaction_container, count_sperator
            )
            if dict_interaction:
                json_output.update(dict_interaction)

            # add entity - profile related
            dict_profile = parse_profile(div_profile_container)
            if dict_profile:
                json_output.update(dict_profile)
            close_current_tab(driver, home_window)
            return json_output
        except NoSuchElementException:
            list_skip.append(link)
            close_current_tab(driver, home_window)
            print("<<< no such element  exception: insight button")
            logging.debug("<<< no such element exception: insight button")
            return None
        except TimeoutException:
            list_skip.append(link)
            close_current_tab(driver, home_window)
            print("<<< time out exception")
            logging.debug("<<< timeout exception: insight button")
            return None


def check_scroll_to_end(post_url_list):
    # If both post_url_list is empty and obj_post_data is empty,
    # if not post_url_list and not obj_post_data:
    #     return False
    if not post_url_list:
        logging.debug("<<< check_scroll_to_end: post url list is empty")
        return True
    for obj_post in post_url_list:
        link = obj_post["url"]
        if link not in obj_post_data.keys():
            return False
    return True


def get_temp_json_path(media, start_date, end_date):
    # Define the output path relative to the base path
    # if getattr(sys, "frozen", False):
    #     # If the app is running as a PyInstaller bundle
    #     base_path = sys._MEIPASS
    # else:
    #     # If running in a regular Python environment
    #     base_path = os.path.abspath(".")
    base_path = os.path.abspath(".")
    root_path = os.path.abspath(os.path.join(base_path, "..", ".."))
    output_dir = os.path.join(root_path, "outputs")
    # output_dir = "outputs"
    file_path = os.path.join(
        output_dir,
        f'{media}_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}.json',
    )
    return output_dir, file_path


# Save extracted post data to local
def save_post_data_temp(media, start_date, end_date):
    output_dir, file_path = get_temp_json_path(media, start_date, end_date)

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Proceed to write to the JSON file
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(obj_post_data, file, ensure_ascii=False, indent=4)

    # def save_dict_to_json(data, filename='data.json'):
    # file_path = f'outputs/{media}_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}.json'
    # with open(file_path, "w") as json_file:
    #     json.dump(obj_post_data, json_file, indent=4)
    print(f"Dictionary saved to {file_path}")
    logging.debug(f"<<< Dictionary saved to {file_path}")
    pass


def check_existing_data(media, start_date, end_date):
    _, file_path = get_temp_json_path(media, start_date, end_date)
    # file_path = f'outputs/{media}_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}.json'
    if os.path.exists(file_path):
        # Open and read the JSON file if it exists
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            obj_post_data.update(data)
            urls = list(data.keys())
            list_skip.extend(urls)
        print("File exists, and data is loaded:", data)
        logging.debug(f"<<< File exists, and data is loaded: {list_skip}")
    else:
        print("File does not exist.")
        logging.debug("<<< File does not exist.")


def save_to_spreadsheet(client, media, spreadsheet):
    # print(f"obj_post_data --\n{obj_post_data}")

    # Open the Google Spreadsheet (replace 'spreadsheet_name' with the actual name)
    # spreadsheet = client.open('Instagramインサイトデータ更新')
    spreadsheet = client.open(spreadsheet)

    # Select a specific sheet by its name (or use .sheet1 for the first sheet)
    sheet = spreadsheet.worksheet(media)

    all_keys = get_post_keys()
    header = ["url"] + all_keys
    # print(f'spreat sheet header ----- {header}')
    save_rows.append(header)
    # sheet.insert_row(header, 1)

    # Add data
    for i, (url, values) in enumerate(obj_post_data.items(), start=2):
        row = [url]  # Start with the URL
        # Add the values for each key, or 'empty' if the key doesn't exist for this url
        row += [values.get(key, "") for key in all_keys]
        # Insert the row into the spreadsheet
        save_rows.append(row)
        # sheet.insert_row(row, i)
    sheet.update("A1", save_rows)
    # --------------------------------------------
    pass


def get_post_keys():
    key_list = []
    for _, data in obj_post_data.items():
        keys = list(data.keys())
        for key in keys:
            key = key.replace(" ", "")
            if key not in key_list:
                key_list.append(key)
    return key_list


"""
get post rows from dom, get post info
if get_post_data returns [TAG_END_OF_LOOP], terminate loop
if loop over whole list, scroll page , call this function again
"""


async def get_post_info(driver, media, start_date, end_date):
    for obj_post in list_post_link:
        time.sleep(random.randint(SLEEP_MIN, SLEEP_MAX))
        link = obj_post["url"]
        print(f"\nhref == {link}")
        # print(f'is already processed -- {link in obj_post_data.keys()}')
        if link in obj_post_data.keys() or link in list_skip:
            print(f"link already processed or has no insight or newer than end_date")
            continue
        insight_data = await get_post_insight_data(
            driver, obj_post, start_date, end_date
        )

        if insight_data == TAG_END_OF_LOOP:
            print('end of loop')
            break
        elif insight_data == None:
            print('insight data is None')
            continue
        else:
            obj_post_data.update({link: insight_data})
            save_post_data_temp(media, start_date, end_date)
            print(
                f"<<< save post data: obj_post_data add new data  \nlink = {link} data = {insight_data}"
            )


# async def get_dom_post_info(
#     driver, sheet_client, media, spreadsheet, start_date, end_date, is_save
# ):
#     post_url_list, row_height, offset_y = await get_dom_post_urls(driver)
#     # check if all post exists in final list, if so means that there are no more data
#     scroll_to_end = check_scroll_to_end(post_url_list)

#     if scroll_to_end == True:
#         print("\n<<< srcoll to end ------")
#         logging.debug("\n<<< srcoll to end ------")
#         save_to_spreadsheet(sheet_client, media, spreadsheet)
#         return

#     # print(f'<<< obj_post_data keys -- {obj_post_data.keys()}')
#     scroll_for_more = True
#     for obj_post in post_url_list:
#         link = obj_post["url"]
#         print(f"\nhref == {link}")
#         # print(f'is already processed -- {link in obj_post_data.keys()}')
#         if link in obj_post_data.keys() or link in list_skip:
#             print(f"link already processed or has no insight or newer than end_date")
#             continue
#         if sleep_needed:
#             time.sleep(random.randint(SLEEP_MIN, SLEEP_MAX))

#         insight_data = await get_post_insight_data(
#             driver, obj_post, start_date, end_date
#         )

#         if insight_data == TAG_END_OF_LOOP:
#             # reach target date, terminate loop
#             scroll_for_more = False
#             break
#         elif insight_data == None:
#             print(f"<<< insight data is None -----")
#             continue
#         else:
#             # obj_post_data[link] = insight_data
#             obj_post_data.update({link: insight_data})
#             save_post_data_temp(media, start_date, end_date)
#             print("<<< save post data")
#             print(
#                 f"<<< obj_post_data   add new data  link = {link} data = {insight_data}"
#             )

#     if scroll_for_more == True:
#         # scroll page
#         scroll_distance = 4 * row_height + offset_y
#         driver.execute_script(f"window.scrollBy(0,{scroll_distance});")
#         print(f"----------- scroll for more ----------- ")
#         time.sleep(5)
#         await get_dom_post_info(
#             driver, sheet_client, media, spreadsheet, start_date, end_date, is_save
#         )
#     else:
#         if is_save:
#             save_to_spreadsheet(sheet_client, media, spreadsheet)
#         pass


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
        # check existing data
        check_existing_data(media, start_date, end_date)
        # get post list
        await get_all_post_urls(driver=driver, start_date=start_date, end_date=end_date)
        # extract post data one by one
        await get_post_info(driver, media, start_date, end_date)
        # save data to spread sheet
        save_to_spreadsheet(client, media, SPREAD_SHEET_NAME)
        send_email_to_slack(media, start_date, end_date)


async def run():
    parser = argparse.ArgumentParser(description="Extract data from website")
    parser.add_argument(
        "--media",
        type=str,
        required=True,
        help="media name should be same with sheet name",
    )
    parser.add_argument(
        "--startDate", type=str, required=True, help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--endDate", type=str, required=True, help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--spreadsheet",
        type=str,
        required=False,
        help="spreadsheet name",
        default="Instagramインサイトデータ更新",
    )

    # Parse the arguments
    args = parser.parse_args()
    media = args.media
    start_date = args.startDate
    end_date = args.endDate

    # if media == "ELLE JAPAN":
    # global sleep_needed
    # sleep_needed = True

    # Validate and convert dates
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return

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
