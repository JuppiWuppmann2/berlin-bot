from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def send_tweet(text: str):
    service = Service("/opt/render/project/src/chromedriver")  # Pfad auf Render
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://x.com/login")
    time.sleep(10)  # Zeit für Login (manuell oder Cookie-basiert)

    # Optional: Cookies laden
    # driver.add_cookie(...)

    driver.get("https://x.com/compose/tweet")
    time.sleep(5)

    tweet_box = driver.find_element(By.CLASS_NAME, "public-DraftEditor-content")
    tweet_box.send_keys(text)
    tweet_box.send_keys(Keys.CONTROL, Keys.ENTER)

    time.sleep(5)
    driver.quit()
