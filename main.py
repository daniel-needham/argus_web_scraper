import os
import re
from datetime import datetime
import mysql.connector
import time
time.strftime('%Y-%m-%d %H:%M:%S')

import selenium.common.exceptions
from tqdm import tqdm
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--disable-extensions")
options.add_argument('--disable-application-cache')
options.add_argument('--disable-gpu')
options.add_argument("--no-sandbox")
options.add_argument("--disable-setuid-sandbox")
options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--headless")

os.system('systemctl start mysql')

mydb = mysql.connector.connect(
  host="localhost",
  user="argus",
  password="argus123",
  database="ArgusComments"
)

cursor = mydb.cursor()

driver = uc.Chrome(options=options, use_subprocess=False)
driver.get('https://www.theargus.co.uk/news/')

try:
    element = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mostReadBlock"]/div[1]/ol[1]'))
    )
except element is None:
    print("Top 50 news stories not found")
    os._exit(1)

list_of_stories = element.find_elements(By.TAG_NAME, 'a')
links = [story.get_attribute('href') for story in list_of_stories]

for idx, link in enumerate(links):
    #print(idx + 1)
    driver.get(link)


    try:
        comment_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,
                                            'article-comments__text--inline.mar-mt-0')))
    except selenium.common.exceptions.TimeoutException:
        print("Comment BUTTON not found")
        print(driver.page_source)
        continue

    driver.execute_script("arguments[0].click();", comment_btn)

    try:
        comment_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID,
                                            'comments-list')))
    except selenium.common.exceptions.TimeoutException:
        print("Comments not found")

    try:
        comment = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                                     "div[id^='commentTemplate-']")))
    except selenium.common.exceptions.TimeoutException:
        print("first comment not found (likely no comments)")
        continue

    ## page now loaded - and includes comments
    ## get page data

    #headline
    headline = driver.find_element(By.CLASS_NAME, 'mar-article__headline').get_attribute('innerText')

    article_time = driver.find_element(By.TAG_NAME, 'time').get_attribute('data-timestamp')
    article_time = datetime.fromtimestamp(int(article_time))

    #tags
    tags = driver.find_elements(By.CLASS_NAME, 'article-tags')
    tags = list(set([tag.get_attribute('innerText') for tag in tags]))
    fill = [""] * 4
    tags = tags[:4] + fill[len(tags):]

    #article id
    article_id = re.search(r'\/(\d+)', link).group(1)

    comments = comment_container.find_elements(By.CSS_SELECTOR,
                                                        "div[id^='commentTemplate-']")
    # page attributes

    sql = "INSERT INTO comments (id, url, article_posted, article_id, article_tag1, article_tag2, article_tag3," \
          " article_tag4, headline, user_id, user_name, comment_posted, comment_text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" \
          "ON DUPLICATE KEY UPDATE id=id"

    # print(headline)
    # print(article_time)
    # print(link)
    # print(tags)
    # print(article_id)
    # print(f'# of comments:{len(comments)}')

    for comment in comments:
        #print("--------------------")

        # #page attributes
        # print(headline)
        # print(link)
        # print(tags)
        # print(article_id)

        user_name_div = comment.find_element(By.CLASS_NAME, 'comment__username.comment-username')

        # user id
        user_id = user_name_div.get_attribute('data-user-id')
        if user_id == "":
            continue
        #print(user_id)

        #username
        user_name = user_name_div.get_attribute('data-user-name')
        #print(user_name)


        #time stamp
        time_stamp = comment.find_element(By.CLASS_NAME, 'comment__posted.formatTimeStampEs6.timestamp.posted-date').get_attribute('data-timestamp')
        time_stamp_datetime = datetime.fromtimestamp(int(time_stamp))
        #print(time_stamp_datetime)

        #comment text
        comment_text = comment.find_element(By.CLASS_NAME, 'comment__text.comment-text').get_attribute('innerText')
        #print(comment_text)

        #comment id
        comment_id = article_id + time_stamp
        #print(comment_id)

        val = (comment_id, link, article_time, article_id, tags[0], tags[1], tags[2], tags[3], headline,
               user_id, user_name, time_stamp_datetime, comment_text)

        cursor.execute(sql, val)
        mydb.commit()

#get number of row in table
cursor.execute("SELECT COUNT(*) FROM comments")
print(f'Total row in DB: {cursor.fetchone()[0]}')

driver.quit()
mydb.close()
os.system('systemctl stop mysql')
os._exit(1)

