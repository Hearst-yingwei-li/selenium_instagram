import time
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import pytz

ACCESS_TOKEN = 'IGQWRNTExZAcEZAzV3FuU0g3NWJKMnhzRW9tZAkV4eUtHZA1JYZA0hWaEp6Y183MmJneHNSUEpSeklVQXBBQktzcnl5aEtPUDVSU0pwUjA2a3ZAqQnFmMjdRbGFPR3YzM0lyd3Q3ZAHo2b01CY1JhZA1lkbmxRbjVlVldfZA3cZD'
posts_url = f'https://graph.instagram.com/me/media?fields=id,timestamp,children&access_token={ACCESS_TOKEN}'
start_date_str = '2024-07-16'
posts_by_days = []
instagram_url = 'https://www.instagram.com/hodinkeejapan/'



def run():
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    timezone = pytz.timezone('UTC')
    start_date = timezone.localize(start_date)
    driver = webdriver.Chrome()
    driver.get(instagram_url)
    get_post_list(driver)
    pass

def get_post_list(driver):
    post_list = []
    article_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'article')))
    div_row_list = article_element.find_elements(By.XPATH, './div/div/div')
    print(f'len #rows = {len(div_row_list)}')
    for div_row in div_row_list:
        
        div_list = div_row.find_elements(By.XPATH,'./div')
        print(f'len #divs in each row === {len(div_list)}')
        for div in div_list:
            # print(f'class name = {div.get_attribute('class')}')
            a_tag = div.find_element(By.TAG_NAME,'a')
            href = a_tag.get_attribute('href')
            post_list.append(href)
            print(f'a_tag href= {href}')
    # open new web tag, check date & click on 'insight'
    # test_count = 0
    for post_herf in post_list:
        # if test_count > 2:
        #     break
        # test_count = test_count + 1
        
        ##
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(post_herf) 
        time.sleep(2) 
        time_element = driver.find_element(By.TAG_NAME, 'time')
        date_time_str = time_element.get_attribute('datetime')
        print(f'date_time ---- {date_time_str}')
        
        # Find the 'Insight' button
        # sections = driver.find_elements(By.TAG_NAME, 'section')
        # print(f'sections len = {len(sections)}')
        # for section in sections:
        #     div_insight = section.find_element(By.TAG_NAME, 'div')
        #     print(f'sections insight len = {div_insight}')
        
        # div_element = driver.find_element(By.XPATH, "//div[@role='button' and @text()='インサイトを見る']")
        # print(f'btn  {div_element}')
        
        
        
        # time.sleep(3000000000)
            
            
        # Close the current tab    
        driver.close()

        # Switch back to the main tab
        driver.switch_to.window(driver.window_handles[0])
    driver.quit()

    

def request_posts(page_url,start_date):
    global posts_by_days
    response = requests.get(page_url)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        posts = data['data']

        last = posts[len(posts)-1]
        last_timestamp_str = last['timestamp']
        last_timestamp = datetime.strptime(last_timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
        print(last_timestamp)
        print(start_date)
        print(last_timestamp > start_date)
        if last_timestamp > start_date:
            # concate
            posts_by_days = posts_by_days + posts
            # request next page
            paging = data['paging']
            next_page_url = paging['next']
            request_posts(next_page_url,start_date)
        else:
            for post in posts:
                post_timestamp_str = post['timestamp']
                post_timestamp = datetime.strptime(post_timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
                if post_timestamp >= start_date:
                   posts_by_days.append(post) 
                else:
                    break
            # print(f'..... {post_targets}')
            # return post_targets
    else:
        # Print the error if the request was not successful
        print(f"Error: {response.status_code}")
        print(response.json())

def get_post_total():
    # loop over target_list,if 'children' exist - plus children length, if not exist, plus one 
    global posts_by_days
    total_posts = 0
    for posts in posts_by_days:
        if 'children' in posts.keys():
            children_data = posts['children']['data']
            total_posts = total_posts + len(children_data)
        else:
            total_posts = total_posts + 1
            
    
    return total_posts

if __name__ == "__main__":
    run()