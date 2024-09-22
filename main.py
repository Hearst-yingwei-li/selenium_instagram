import time
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import pytz

ACCESS_TOKEN = 'IGQWRNTExZAcEZAzV3FuU0g3NWJKMnhzRW9tZAkV4eUtHZA1JYZA0hWaEp6Y183MmJneHNSUEpSeklVQXBBQktzcnl5aEtPUDVSU0pwUjA2a3ZAqQnFmMjdRbGFPR3YzM0lyd3Q3ZAHo2b01CY1JhZA1lkbmxRbjVlVldfZA3cZD'
posts_url = f'https://graph.instagram.com/me/media?fields=id,timestamp,children&access_token={ACCESS_TOKEN}'
start_date_str = '2024-07-16'
posts_by_days = []
instagram_url = 'https://www.instagram.com/hodinkeejapan/'
TAG_END_OF_LOOP = 'END'

def get_dom_post_urls(driver):
    post_links = []
    mainDiv = driver.find_element(By.XPATH,"//main[@role='main']")
    mainChildContainer = mainDiv.find_elements(By.XPATH,"./div") 
    print(len(mainChildContainer))
    postContainer = mainChildContainer[0].find_elements(By.XPATH,"./div")[-1]
    postStyleDiv = postContainer.find_elements(By.XPATH,"./div")[0]
    postRowContainer = postStyleDiv.find_elements(By.XPATH,"./div") 
    print(len(postRowContainer))

    for div_row in postRowContainer:
        divs = div_row.find_elements(By.XPATH, "div")
        # print(f"Number of <div> elements in each row: {len(divs)}")
        for div in divs:
            a_tags = div.find_elements(By.TAG_NAME, "a")
            if len(a_tags) > 0:
                a_tag = a_tags[0]
                href = a_tag.get_attribute("href")
                post_links.append(href)
    print(post_links)
    print(len(post_links))
    row_height = driver.execute_script("return arguments[0].getBoundingClientRect().height;",postRowContainer[0])
    print(f'row height = {row_height}')
    return post_links,len(postRowContainer),row_height

def parseNumber(strNumber):
    if '万' in strNumber:
        str_num = strNumber[0:-1]
        value = float(str_num)*10000
        return str(value)
    return strNumber

def parse_view(div_view_container,count_sperator):
    json_view = {}

    view_total = div_view_container.find_element(By.XPATH,"./div/div/div[2]/div/span")
    json_view['ビュー'] = parseNumber(view_total.text)

    per_follower = div_view_container.find_element(By.XPATH,"./div/div/div[3]/div[2]")
    json_view['フォロワー'] = per_follower.text

    per_unfollower = div_view_container.find_element(By.XPATH,"./div/div/div[3]/div[4]")
    json_view['フォロワー以外'] = per_unfollower.text

    if count_sperator == 7:
        view_source_div = div_view_container.find_element(By.XPATH,"./div/div/div[5]")
        view_source_contents = view_source_div.find_elements(By.XPATH,"./div")
        for content in view_source_contents:
            key_div = content.find_element(By.XPATH,"./div/div[1]/span")
            value_div = content.find_element(By.XPATH,"./div/div[2]/span")
            json_view[key_div.text] = value_div.text

    reach_count_div = div_view_container.find_element(By.XPATH,f"./div/div/div[{count_sperator}]")
    reach_key = reach_count_div.find_element(By.XPATH,"./span")
    reach_value = reach_count_div.find_element(By.XPATH,"./div/span")
    json_view[reach_key.text] = reach_value.text
    return json_view

def parse_interaction(div_interaction_container):
    json_interaction = {}
    div_children = div_interaction_container.find_elements(By.XPATH,'./div/div')
    interaction_container = div_children[1]
    post_interaction_container = div_children[3]
    action_account_container = div_children[5]

    # interaction
    interaction_key = interaction_container.find_element(By.XPATH,'./div/div[1]/span')
    interaction_value = interaction_container.find_element(By.XPATH,'./div/div[1]/div/span')
    json_interaction[interaction_key.text] = interaction_value.text
    # print(f'interaction key = {interaction_key.text}  interaction value = {interaction_value.text}')
    
    follower_key = interaction_container.find_element(By.XPATH,'./div/div[2]/div[1]/span')
    follower_value = interaction_container.find_element(By.XPATH,'./div/div[2]/div[2]')
    json_interaction[follower_key.text] = follower_value.text
    # print(f'follower key = {follower_key.text}  follower value = {follower_value.text}')
    
    unfollower_key = interaction_container.find_element(By.XPATH,'./div/div[2]/div[3]/span')
    unfollower_value = interaction_container.find_element(By.XPATH,'./div/div[2]/div[4]')
    json_interaction[unfollower_key.text] = unfollower_value.text
    # print(f'unfollower key = {unfollower_key.text}  unfollower value = {unfollower_value.text}')

    # post interaction
    post_children = post_interaction_container.find_elements(By.XPATH,'./div/div')
    post_interaction_div = post_children[0]
    post_interaction_key = post_interaction_div.find_element(By.XPATH,'./span')
    post_interaction_value = post_interaction_div.find_element(By.XPATH,'./div/span')
    json_interaction[post_interaction_key.text] = post_interaction_value.text
    # post_interaction_key = post_interaction_container.find_element(By.XPATH,'./div/div[1]/span')
    # post_interaction_value = post_interaction_container.find_element(By.XPATH,'./div/div[1]/div/span')
    # print(f'post_interaction key = {post_interaction_key.text}  post_interaction value = {post_interaction_value.text}')
    for element in post_children[1:]:
        key_div = element.find_element(By.XPATH,'./div/div[1]/span')
        value_div = element.find_element(By.XPATH,'./div/div[2]/span')
        json_interaction[key_div.text] = value_div.text
        # print(f'element key = {key_div.text}   element value = {value_div.text}')
    
    # action account
    action_account_key = action_account_container.find_element(By.XPATH,'./span')
    action_account_value = action_account_container.find_element(By.XPATH,'./div/span')
    # print(f'action account  key = {action_account_key.text}   value = {action_account_value.text}')
    json_interaction[action_account_key.text] = action_account_value.text

    return json_interaction

def parse_profile(div_profile_container):
    json_profile = {}
    profile_container = div_profile_container.find_element(By.XPATH,'./div/div[2]/div')
    children_elements = profile_container.find_elements(By.XPATH,'./div')
    profile_activity = children_elements[0]
    profile_activity_key = profile_activity.find_element(By.XPATH,'./span')
    profile_activity_value = profile_activity.find_element(By.XPATH,'./div/span')
    json_profile[profile_activity_key.text] = profile_activity_value.text
    for element in children_elements[1:]:
        key_div = element.find_element(By.XPATH,'./div[1]/span')
        value_div = element.find_element(By.XPATH,'./div[2]/span')
        json_profile[key_div.text] = value_div.text
    return json_profile

async def get_post_data(driver,link):
    timezone = pytz.timezone('UTC')
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    start_date = timezone.localize(start_date)
    #
    json_output = []
    home_window = driver.current_window_handle
    driver.switch_to.new_window('tab')
    driver.get(link)
    #
    time_tag = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "time"))
    )
    date_time = time_tag.get_attribute("datetime")
    date_time = datetime.strptime(date_time, "%Y-%m-%d")
    date_time = timezone.localize(date_time)
    print(f'target date - {date_time}   post date -- {date_time}')
    # check post date
    if date_time > start_date:
        driver.close()
        driver.switch_to.window(home_window)
        return TAG_END_OF_LOOP

    try:
        insight_button = WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.XPATH,"//div[@role='button' and text()='インサイトを見る']")))
        print(insight_button.text)
        print(insight_button.is_enabled())
        driver.execute_script("arguments[0].click();",insight_button)
        WebDriverWait(driver, 10).until(EC.url_contains('insights'))
                
        # find seperators
        hr_separators = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH,"//hr"))
        )
        count_sperator = len(hr_separators)
        if count_sperator == 7:
            main_separators = [hr_separators[2],hr_separators[5],hr_separators[6]]
        else:
            main_separators = [hr_separators[1],hr_separators[4],hr_separators[5]]
        div_separators = [hr.find_element(By.XPATH,"..") for hr in main_separators]
        div_info_root = div_separators[0].find_element(By.XPATH,"..")
        div_info_children = div_info_root.find_elements(By.XPATH,"./div")
        div_view_container = div_info_children[0]
        div_interaction_container = div_info_children[2]
        div_profile_container = div_info_children[4]


        json_output.append(parse_view(div_view_container,count_sperator))  
        json_output.append(parse_interaction(div_interaction_container)) 
        json_output.append(parse_profile(div_profile_container)) 
        
        print(json_output)
        driver.close()
        driver.switch_to.window(home_window)
        return json_output
    except TimeoutException:
        driver.close()
        driver.switch_to.window(home_window)
        return None

'''
get post rows from dom, get post info
if get_post_data returns [TAG_END_OF_LOOP], terminate loop
if loop over whole list, scroll page , call this function again
'''
def get_dom_posts():
    pass
def run():
    # start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    # timezone = pytz.timezone('UTC')
    # start_date = timezone.localize(start_date)
    

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

    # Now you can access the already opened Chrome session
    print(driver.title)  # Print the title of the currently opened page
    post_url_list,row_counts,row_height = get_dom_post_urls(driver)
    scroll_distance = row_counts * row_height
    driver.execute_script(f"window.scrollBy(0,{scroll_distance});")

    # post_info = {}
    # count = 0
    # target = 41
    # post_url_list = get_dom_post_urls(driver)
    # for url in post_url_list:
    #     if url in post_info.keys():
    #         continue
    #     post_info[url] = f'Test: {url}'
    #     count += 1
    #     # get url content - date
    #     # if data is earlier than target date,
    # if count < target:
    #     # scroll page
    #     pass
    pass





    

# def request_posts(page_url,start_date):
#     global posts_by_days
#     response = requests.get(page_url)
#     if response.status_code == 200:
#         # Parse the JSON response
#         data = response.json()
#         posts = data['data']

#         last = posts[len(posts)-1]
#         last_timestamp_str = last['timestamp']
#         last_timestamp = datetime.strptime(last_timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
#         print(last_timestamp)
#         print(start_date)
#         print(last_timestamp > start_date)
#         if last_timestamp > start_date:
#             # concate
#             posts_by_days = posts_by_days + posts
#             # request next page
#             paging = data['paging']
#             next_page_url = paging['next']
#             request_posts(next_page_url,start_date)
#         else:
#             for post in posts:
#                 post_timestamp_str = post['timestamp']
#                 post_timestamp = datetime.strptime(post_timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
#                 if post_timestamp >= start_date:
#                    posts_by_days.append(post) 
#                 else:
#                     break
#     else:
#         # Print the error if the request was not successful
#         print(f"Error: {response.status_code}")
#         print(response.json())

# def get_post_total():
#     # loop over target_list,if 'children' exist - plus children length, if not exist, plus one 
#     global posts_by_days
#     total_posts = 0
#     for posts in posts_by_days:
#         if 'children' in posts.keys():
#             children_data = posts['children']['data']
#             total_posts = total_posts + len(children_data)
#         else:
#             total_posts = total_posts + 1
            
    
#     return total_posts

if __name__ == "__main__":
    run()