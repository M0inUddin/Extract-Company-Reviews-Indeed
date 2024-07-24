import time
import pandas as pd
import gradio as gr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import logging
from dotenv import load_dotenv
import os
import random
from selenium.webdriver.common.keys import Keys

# Load environment variables from .env file
load_dotenv()
GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def random_delay(min_seconds=5, max_seconds=15):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def type_text(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.3))  # Simulate typing delay


def sign_in_to_google(driver, email, password):
    driver.get("https://accounts.google.com/signin")
    random_delay()
    email_input = driver.find_element(By.ID, "identifierId")
    type_text(email_input, email)
    email_input.send_keys(Keys.RETURN)
    logging.info("Typed the Google email address.")
    random_delay()

    password_input = driver.find_element(By.NAME, "Passwd")
    type_text(password_input, password)
    password_input.send_keys(Keys.RETURN)
    logging.info("Typed the Google password.")
    random_delay()


def sign_in_to_indeed_with_google(driver):
    driver.execute_script("window.open('https://www.indeed.com/', '_blank');")
    driver.switch_to.window(driver.window_handles[2])
    random_delay()

    try:
        sign_in_button = driver.find_element(
            By.CSS_SELECTOR, 'div[data-gnav-element-name="SignIn"] a'
        )
        sign_in_button.click()
        logging.info("Clicked the Sign In button.")
    except Exception as e:
        logging.error(f"Error locating or clicking the Sign In button: {e}")
        return False

    random_delay()  # Allow time for the sign in page to load

    try:
        google_sign_in_button = driver.find_element(By.ID, "login-google-button")
        google_sign_in_button.click()
        logging.info("Clicked the Google sign in button.")
    except Exception as e:
        logging.error(f"Error locating or clicking the Google sign in button: {e}")
        return False

    random_delay(5, 10)  # Allow time for the Google sign-in window to open

    # Switch to the new Google sign-in window
    driver.switch_to.window(driver.window_handles[-1])
    random_delay()

    return True


def scrape_indeed_reviews(url, pages, email, password):
    # Initialize the Chrome driver
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    sign_in_to_google(driver, GOOGLE_EMAIL, GOOGLE_PASSWORD)

    if not sign_in_to_indeed_with_google(driver):
        driver.quit()
        return pd.DataFrame(), None  # Return an empty DataFrame if sign in fails

    driver.get(url)

    reviews = []

    for page in range(pages):
        logging.info(f"Scraping page {page + 1}/{pages}")
        random_delay()  # Allow time for the page to load

        review_elements = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="reviews[]"]'
        )
        for element in review_elements:
            try:
                rating = element.find_element(
                    By.CSS_SELECTOR, '[itemprop="ratingValue"]'
                ).get_attribute("content")
                title_element = element.find_element(
                    By.CSS_SELECTOR, '[data-testid="titleLink"] span span span'
                )
                title = title_element.text if title_element else "N/A"
                author_element = element.find_element(
                    By.CSS_SELECTOR, '[itemprop="author"]'
                )
                date = author_element.text.split(" - ")[-1].strip()
                role = author_element.find_element(
                    By.CSS_SELECTOR, '[itemprop="name"]'
                ).get_attribute("content")
                review_url = element.find_element(
                    By.CSS_SELECTOR, '[data-testid="titleLink"]'
                ).get_attribute("href")
                reviews.append([rating, date, title, role, review_url])
            except Exception as e:
                logging.error(f"Error scraping review: {e}")

        try:
            next_button = driver.find_element(
                By.CSS_SELECTOR, '[data-testid="next-page"]'
            )
            next_button.click()
        except Exception as e:
            logging.warning(f"Error navigating to the next page or no more pages: {e}")
            break

    driver.quit()

    df = pd.DataFrame(
        reviews, columns=["Rating", "Date", "Title", "Employee Role", "URL"]
    )
    csv_path = "indeed_reviews.csv"
    df.to_csv(csv_path, index=False)
    return df, csv_path


def scrape_and_return_csv(url, pages):
    df, csv_path = scrape_indeed_reviews(url, pages, GOOGLE_EMAIL, GOOGLE_PASSWORD)
    return df, csv_path


iface = gr.Interface(
    fn=scrape_and_return_csv,
    inputs=["text", "number"],
    outputs=["dataframe", "file"],
    title="Scrape Indeed Reviews",
    description="Scrape reviews from Indeed and return a CSV file",
)

if __name__ == "__main__":
    iface.launch(share=True)
