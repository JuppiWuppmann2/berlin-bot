import os
import time
import textwrap
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

X_USERNAME = os.getenv("X_USERNAME")
X_PASSWORD = os.getenv("X_PASSWORD")

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def split_into_tweets(text, max_length=280):
    parts = textwrap.wrap(text, width=max_length-10, break_long_words=False)
    tweets = []
    for i, part in enumerate(parts, start=1):
        if len(parts) > 1:
            tweets.append(f"{part} ({i}/{len(parts)})")
        else:
            tweets.append(part)
    return tweets

def post_on_x(text):
    tweets = split_into_tweets(text)
    driver = get_driver()
    driver.get("https://x.com/login")
    time.sleep(5)

    driver.find_element(By.NAME, "text").send_keys(X_USERNAME)
    driver.find_element(By.XPATH, '//span[text()="Weiter"]').click()
    time.sleep(2)
    driver.find_element(By.NAME, "password").send_keys(X_PASSWORD)
    driver.find_element(By.XPATH, '//span[text()="Einloggen"]').click()
    time.sleep(5)

    for tweet in tweets:
        driver.find_element(By.CSS_SELECTOR, "div.public-DraftStyleDefault-block").send_keys(tweet)
        driver.find_element(By.XPATH, '//span[text()="Posten"]').click()
        time.sleep(3)

    driver.quit()
