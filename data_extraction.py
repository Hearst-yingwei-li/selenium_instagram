import time
import argparse
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import asyncio
import pytz
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow

# ACCESS_TOKEN = 'IGQWRNTExZAcEZAzV3FuU0g3NWJKMnhzRW9tZAkV4eUtHZA1JYZA0hWaEp6Y183MmJneHNSUEpSeklVQXBBQktzcnl5aEtPUDVSU0pwUjA2a3ZAqQnFmMjdRbGFPR3YzM0lyd3Q3ZAHo2b01CY1JhZA1lkbmxRbjVlVldfZA3cZD'
# posts_url = f'https://graph.instagram.com/me/media?fields=id,timestamp,children&access_token={ACCESS_TOKEN}'
TAG_END_OF_LOOP = 'END'
SPREAD_SHEET_NAME = 'Instagramインサイトデータ更新'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
#
obj_post_data = {}
list_unprocess = []
# To avoid Instagram API request restriction (200 api call/hour)
sleep_time = 0



async def get_dom_post_urls(driver):
    post_links = []
    mainDiv = driver.find_element(By.XPATH,"//main[@role='main']")
    mainChildContainer = mainDiv.find_elements(By.XPATH,"./div") 
    postContainer = mainChildContainer[0].find_elements(By.XPATH,"./div")[-1]
    postStyleDiv = postContainer.find_elements(By.XPATH,"./div")[0]
    postRowContainer = postStyleDiv.find_elements(By.XPATH,"./div") 
    print(f'row count --- {len(postRowContainer)}')
    position_y = driver.execute_script("return arguments[0].getBoundingClientRect().top;", postRowContainer[0])

    for div_row in postRowContainer:
        divs = div_row.find_elements(By.XPATH, "div")
        # print(f"Number of <div> elements in each row: {len(divs)}")
        for div in divs:
            a_tags = div.find_elements(By.TAG_NAME, "a")
            if len(a_tags) > 0:
                a_tag = a_tags[0]
                href = a_tag.get_attribute("href")
                post_links.append(href)
    # print(post_links)
    # print(f'dom post count ----- {len(post_links)}')
    row_height = driver.execute_script("return arguments[0].getBoundingClientRect().height;",postRowContainer[0])
    # print(f'row height = {row_height}')
    # TODO: Should be a dict {url,isPined} - For pined post, even if it's post date is not in the start-end time range, instead of return TAG_END_OF_LOOP ,should let the loop go on 
    return post_links,row_height,position_y if position_y > 0 else 0

def parseNumber(strNumber):
    if '万' in strNumber:
        str_num = strNumber[0:-1]
        value = int(float(str_num)*10000)
        return str(value)
    return strNumber

def parse_view(div_view_container,count_sperator):
    json_view = {}
    if count_sperator == 7:
        view_total = div_view_container.find_element(By.XPATH,"./div/div/div[2]/div/span") 
        json_view['ビュー'] = parseNumber(view_total.text)

        per_follower = div_view_container.find_element(By.XPATH,"./div/div/div[3]/div[2]")
        json_view['ビューフォロワー'] = parseNumber(per_follower.text)

        per_unfollower = div_view_container.find_element(By.XPATH,"./div/div/div[3]/div[4]") 
        json_view['ビューフォロワー以外'] = parseNumber(per_unfollower.text)
        # 
        view_source_div = div_view_container.find_element(By.XPATH,"./div/div/div[5]")
        view_source_contents = view_source_div.find_elements(By.XPATH,"./div")
        for content in view_source_contents:
            key_div = content.find_element(By.XPATH,"./div/div[1]/span")
            value_div = content.find_element(By.XPATH,"./div/div[2]/span")
            json_view[key_div.text] = parseNumber(value_div.text)
        # 
        reach_count_div = div_view_container.find_element(By.XPATH,f"./div/div/div[{count_sperator}]") #f"./div/div/div[{count_sperator}]
        reach_key = reach_count_div.find_element(By.XPATH,"./span")
        reach_value = reach_count_div.find_element(By.XPATH,"./div/span")
        json_view[reach_key.text] = parseNumber(reach_value.text)
    else:
        view_total = div_view_container.find_element(By.XPATH,"./div/div[2]/div/div[1]/div/span") 
        json_view['ビュー'] = parseNumber(view_total.text)

        # per_follower = div_view_container.find_element(By.XPATH,"./div/div[2]/div/div[2]/div[2]/div") 
        per_follower_div = div_view_container.find_element(By.XPATH,"./div/div[2]/div/div[2]/div[2]") 
        if re.search(r'\d', per_follower_div.text) or '%' in per_follower_div.text:
            json_view['ビューフォロワー'] = parseNumber(per_follower_div.text)
        else:
            per_follower = per_follower_div.find_element(By.XPATH,"./div")
            json_view['ビューフォロワー'] = parseNumber(per_follower.text)

        # per_unfollower = div_view_container.find_element(By.XPATH,"./div/div[2]/div/div[2]/div[4]/div") 
        per_unfollower_div = div_view_container.find_element(By.XPATH,"./div/div[2]/div/div[2]/div[4]") 
        if re.search(r'\d', per_unfollower_div.text) or '%' in per_unfollower_div.text:
            json_view['ビューフォロワー以外'] = parseNumber(per_unfollower_div.text)
        else:
            per_unfollower = per_unfollower_div.find_element(By.XPATH,"./div")
            json_view['ビューフォロワー以外'] = parseNumber(per_unfollower.text)

        reach_count_div = div_view_container.find_element(By.XPATH,"./div/div[2]/div/div[4]") 
        reach_key = reach_count_div.find_element(By.XPATH,"./span")
        reach_value = reach_count_div.find_element(By.XPATH,"./div/span")
        json_view[reach_key.text] = parseNumber(reach_value.text)
    
    return json_view

def parse_interaction(div_interaction_container,count_sperator):
    json_interaction = {}
    div_children = div_interaction_container.find_elements(By.XPATH,'./div/div')
    interaction_container = div_children[1]
    post_interaction_container = div_children[3]
    action_account_container = div_children[5]

    # interaction
    interaction_key = interaction_container.find_element(By.XPATH,'./div/div[1]/span')
    interaction_value = interaction_container.find_element(By.XPATH,'./div/div[1]/div/span')
    json_interaction[interaction_key.text] = parseNumber(interaction_value.text)
    # print(f'interaction key = {interaction_key.text}  interaction value = {interaction_value.text}')
    
    follower_key = interaction_container.find_element(By.XPATH,'./div/div[2]/div[1]/span')
    follower_value = interaction_container.find_element(By.XPATH,'./div/div[2]/div[2]')
    # print(f'------ follower {follower_value.text}')
    json_interaction[f'インタラクション{follower_key.text}'] = parseNumber(follower_value.text)
    # print(f'follower key = {follower_key.text}  follower value = {follower_value.text}')
    
    unfollower_key = interaction_container.find_element(By.XPATH,'./div/div[2]/div[3]/span')
    unfollower_value = interaction_container.find_element(By.XPATH,'./div/div[2]/div[4]')
    json_interaction[f'インタラクション{unfollower_key.text}'] = parseNumber(unfollower_value.text)
    # print(f'unfollower key = {unfollower_key.text}  unfollower value = {unfollower_value.text}')

    # post interaction
    post_children = post_interaction_container.find_elements(By.XPATH,'./div/div')
    post_interaction_div = post_children[0]
    post_interaction_key = post_interaction_div.find_element(By.XPATH,'./span')
    post_interaction_value = post_interaction_div.find_element(By.XPATH,'./div/span')
    json_interaction[post_interaction_key.text] = parseNumber(post_interaction_value.text)
    # post_interaction_key = post_interaction_container.find_element(By.XPATH,'./div/div[1]/span')
    # post_interaction_value = post_interaction_container.find_element(By.XPATH,'./div/div[1]/div/span')
    # print(f'post_interaction key = {post_interaction_key.text}  post_interaction value = {post_interaction_value.text}')
    xpath = './div/' if count_sperator == 7 else './'
    for element in post_children[1:]:
        key_div = element.find_element(By.XPATH,f'{xpath}div[1]/span') #'./div/div[1]/span'
        value_div = element.find_element(By.XPATH,f'{xpath}div[2]/span') #'./div/div[2]/span'
        json_interaction[key_div.text] = parseNumber(value_div.text)
        # print(f'element key = {key_div.text}   element value = {value_div.text}')
    
    # action account
    action_account_key = action_account_container.find_element(By.XPATH,'./span')
    action_account_value = action_account_container.find_element(By.XPATH,'./div/span')
    # print(f'action account  key = {action_account_key.text}   value = {action_account_value.text}')
    json_interaction[action_account_key.text] = parseNumber(action_account_value.text)

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
        json_profile[key_div.text] = parseNumber(value_div.text)
    return json_profile

async def get_post_insight_data(driver,link,start_date,end_date):
    timezone = pytz.timezone('Asia/Tokyo')
    start_date = timezone.localize(start_date)
    #
    end_date = timezone.localize(end_date)
    #
    json_output = {}
    home_window = driver.current_window_handle
    driver.switch_to.new_window('tab')
    driver.get(link)
    #
    time_tag = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "time"))
    )
    date_time_str = time_tag.get_attribute("datetime")
    date_time = datetime.fromisoformat(date_time_str.replace('Z','+00:00')) #UTC timezone
    date_time = date_time.astimezone(timezone)
    # print(f'get post insight data -------- post date -- {date_time} --------')
    # check post date
    if date_time > end_date:
        list_unprocess.append(link)
        driver.close()
        driver.switch_to.window(home_window)
        time.sleep(1)
        print(f'--- current time > end date ')
        return None
    
    if date_time < start_date:
        driver.close()
        driver.switch_to.window(home_window)
        time.sleep(1)
        return TAG_END_OF_LOOP
    
    try:
        # wait for all element in page is rendered!
        # error sometimes the count_sperator is 2, seems because not all element is rendered~~
        insight_button = WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.XPATH,"//div[@role='button' and text()='インサイトを見る']")))
        driver.execute_script("arguments[0].click();",insight_button)
        WebDriverWait(driver, 10).until(EC.url_contains('insights'))
        time.sleep(5)
        # find seperators
        hr_separators = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH,"//hr"))
        )
        count_sperator = len(hr_separators)
        if count_sperator == 7:
            main_separators = [hr_separators[2],hr_separators[5],hr_separators[6]]
        elif count_sperator == 6:
            main_separators = [hr_separators[1],hr_separators[4],hr_separators[5]]
        else:
            print(f'count_sperator ------- {count_sperator} no enough info is loaded on the website')  
            time.sleep(1) 
            return None 
        div_separators = [hr.find_element(By.XPATH,"..") for hr in main_separators]
        div_info_root = div_separators[0].find_element(By.XPATH,"..")
        div_info_children = div_info_root.find_elements(By.XPATH,"./div")
        div_view_container = div_info_children[0]
        div_interaction_container = div_info_children[2]
        div_profile_container = div_info_children[4]

        # add entity - Date
        json_output['Date'] = date_time.strftime('%Y-%m-%d %H:%M:%S')
        # add entity - view related
        json_output.update(parse_view(div_view_container,count_sperator))
        # add entity - interaction related
        json_output.update(parse_interaction(div_interaction_container,count_sperator))
        # add entity - profile related
        json_output.update(parse_profile(div_profile_container))
        
        driver.close()
        driver.switch_to.window(home_window)
        time.sleep(1)
        return json_output
    except TimeoutException:
        list_unprocess.append(link)
        driver.close()
        driver.switch_to.window(home_window)
        time.sleep(1)
        print(f'<<< time out exception')
        return None
    
def check_scroll_to_end(post_url_list):
    # If both post_url_list is empty and obj_post_data is empty, 
    # if not post_url_list and not obj_post_data:
    #     return False
    if not post_url_list:
        return True
    for link in post_url_list:
        if link not in obj_post_data.keys():
            return False
    return True

def save_to_spreadsheet(media,spreadsheet):
    print(f'obj_post_data --\n{obj_post_data}')
    # OAuth 2.0 flow to get the credentials
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json',SCOPES)
    
    # Authenticate using the credentials.json
    creds = flow.run_local_server(port=0)

    # Authorize the client
    client = gspread.authorize(creds)

    # Open the Google Spreadsheet (replace 'spreadsheet_name' with the actual name)
    # spreadsheet = client.open('Instagramインサイトデータ更新')
    spreadsheet = client.open(spreadsheet)

    # Select a specific sheet by its name (or use .sheet1 for the first sheet)
    sheet = spreadsheet.worksheet(media)
    
    all_keys = get_post_keys()
    header = ['url'] + all_keys
    # print(f'spreat sheet header ----- {header}')
    sheet.insert_row(header, 1)
    
    # Add data
    for i, (url, values) in enumerate(obj_post_data.items(), start=2):
        row = [url]  # Start with the URL
        # Add the values for each key, or 'empty' if the key doesn't exist for this url
        row += [values.get(key, '') for key in all_keys]
        # Insert the row into the spreadsheet
        sheet.insert_row(row, i)
    # --------------------------------------------
    pass        

def get_post_keys():
    key_list = []
    for _,data in obj_post_data.items():
        keys = list(data.keys())
        for key in keys:
            key = key.replace(' ','')
            if key not in key_list:
                key_list.append(key)
    return key_list
'''
get post rows from dom, get post info
if get_post_data returns [TAG_END_OF_LOOP], terminate loop
if loop over whole list, scroll page , call this function again
'''

async def get_dom_post_info(driver, media,spreadsheet,start_date,end_date):
    # test_link = 'https://www.instagram.com/reel/DAceh2rBHMK/'
    # insight_data = await get_post_insight_data(driver,test_link,start_date,end_date)
    # return
    
    
    post_url_list,row_height,offset_y = await get_dom_post_urls(driver)
    # print(f'<<< dom post urls -------- {post_url_list}')

    # check if all post exists in final list, if so means that there are no more data
    scroll_to_end = check_scroll_to_end(post_url_list)
    if scroll_to_end == True:
        print(f'\n<<< srcoll to end ------')
        return
    
    # print(f'<<< obj_post_data keys -- {obj_post_data.keys()}')
    scroll_for_more = True
    for link in post_url_list:
        print(f"\nhref == {link}")
        # print(f'is already processed -- {link in obj_post_data.keys()}')
        if link in obj_post_data.keys() or link in list_unprocess:
            print(f'link already processed or has no insight or newer than end_date')
            continue
        
        insight_data = await get_post_insight_data(driver,link,start_date,end_date)
        
        if insight_data == TAG_END_OF_LOOP:
            # reach target date, terminate loop
            scroll_for_more = False
            print(f'<<< get target date ------')
            break
        elif insight_data == None:
            print(f'<<< insight data is None -----')
            continue
        else:
            obj_post_data[link] = insight_data
            print('<<< save post data')
            # print(f'<<< obj_post_data   add new data  link = {link}')
            
    
    if scroll_for_more == True:
        # scroll page
        scroll_distance = 3 * row_height + offset_y
        driver.execute_script(f"window.scrollBy(0,{scroll_distance});")
        print(f'----------- scroll for more ----------- ')
        time.sleep(5)
        await get_dom_post_info(driver,media,spreadsheet,start_date,end_date)
    else:
        time.sleep(sleep_time)
        print(f'sleep ------- {sleep_time}')
        save_to_spreadsheet(media,spreadsheet)
        # print(f'obj_post_data --\n{obj_post_data}')
        pass

async def execute(media,start_date,end_date):
    if media == 'ELLE JAPAN':
        global sleep_time
        sleep_time = 20
    #
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
    # Scroll to top to prevent effect from previous process
    driver.execute_script(f"window.scrollBy(0,{0});")

    # Now you can access the already opened Chrome session
    print(driver.title)  # Print the title of the currently opened page
    await get_dom_post_info(driver,media,SPREAD_SHEET_NAME,start_date,end_date)
    pass

async def run():
    parser = argparse.ArgumentParser(description='Extract data from website')
    parser.add_argument('--media', type=str, required=True, help='media name should be same with sheet name')
    parser.add_argument('--startDate', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--endDate', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--spreadsheet', type=str, required=False, help='spreadsheet name',default='Instagramインサイトデータ更新')

    # Parse the arguments
    args = parser.parse_args()
    media = args.media
    start_date = args.startDate
    end_date = args.endDate
    spreadsheet = args.spreadsheet
    
    if media == 'ELLE JAPAN':
        global sleep_time
        sleep_time = 20
    
    # Validate and convert dates
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return
    
    #-------------
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
    # Scroll to top to prevent effect from previous process
    driver.execute_script(f"window.scrollBy(0,{0});")

    # Now you can access the already opened Chrome session
    print(driver.title)  # Print the title of the currently opened page
    await get_dom_post_info(driver,media,spreadsheet,start_date,end_date)
    
if __name__ == "__main__":
    asyncio.run(run())