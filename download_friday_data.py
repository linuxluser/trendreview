#!/usr/bin/env python3

"""Download charts from Finviz website for a set of tickers.
"""


import datetime
import os
import time
import urllib.request
import yaml

from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


_OPENER = None

STUDIES_BASE_DIR = None
YAML_FILE_NAME = None
BASKETS = None
FINVIZ_URL_TMPL = 'https://finviz.com/quote.ashx?t={}&ty=c&ta=1&p=d&r=m6'
MARKETCHAMELEON_URL_TMPL = 'https://marketchameleon.com/Overview/{}/IV/'
CHART_FILENAME_TMPL = '{}-D-M6.png'


def set_global_values():
    """Read config.yaml and load in global values of this script from that."""
    global STUDIES_BASE_DIR
    global YAML_FILE_NAME
    global BASKETS
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.CSafeLoader)
    STUDIES_BASE_DIR = config['Studies Base Directory']
    YAML_FILE_NAME = config['Study Data File']
    BASKETS = config['Baskets']


def scrape_rsi_value(driver):
    css_selector = 'tr.table-dark-row:nth-child(9) > td:nth-child(10) > b:nth-child(1)'
    e = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    try:
        return float(e.text)
    except ValueError:
        return -1


def scrape_title(driver):
    css_selector = 'table.fullview-title > tbody > tr > td > h1 > span > a > b'
    e = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    return e.text


def scrape_iv30(driver):
    """Get the IV-30 value off of the marketchameleon page."""
    css_selector = ' > '.join(('#symov_main_heading',
                               'div',
                               'div',
                               'div:nth-child(2)',
                               'div:nth-child(3)',
                               'span.datatag'))
    e = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    value = e.text.strip()
    value = value.split()[0]   # Only get first word
    value = value.rstrip('%')  # Remove trailing '%' character
    value = float(value)       # Convert to a float
    value = round(value)       # Round to nearest integer
    return value


def publish_chart(driver):
    """Click "publish chart" link and return the URL of the generated chart."""
    a = driver.find_element(By.LINK_TEXT, 'publish chart')
    a.click()
    img = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'img[data-testid="charts-publish-chart-img"]')))
    return img.get_attribute('src')


_STUDY_DIR = None
def make_study_dir():
    """Create a directory based on the date string as part of the path based on the latest Friday."""
    global _STUDY_DIR
    if _STUDY_DIR is None:
        today = datetime.date.today()
        dow = today.weekday()
        if dow == 4:  # Friday
            date_str = today.strftime('%Y-%m-%d')
        elif dow < 4:
            days_back = - (dow + 3)
            date_str = (today + datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
        else:
            days_back = 4 - dow
            date_str = (today + datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
        study_dir = '{}/{}'.format(STUDIES_BASE_DIR, date_str)
        if not os.path.exists(study_dir):
            os.makedirs(study_dir)
            print(f'# Created new study directory: {study_dir}')
        else:
            print(f'# Using existing study directory: {study_dir}')
        _STUDY_DIR = study_dir
    return _STUDY_DIR


def get_local_path(ticker):
    """Build LocalPath value of image."""
    return make_study_dir() + '/' + CHART_FILENAME_TMPL.format(ticker)


def download_chart(driver, url, local_path):
    """Downloads the chart image at url and store it in local_path.

    The driver is required so we can extract the User-Agent string if needed.
    """
    global _OPENER
    # Add user-agent string if it hasn't been done yet
    if _OPENER is None:
        user_agent = driver.execute_script('return navigator.userAgent;')
        _OPENER = urllib.request.build_opener()
        _OPENER.addheaders = [('User-Agent', user_agent)]
        urllib.request.install_opener(_OPENER)
    urllib.request.urlretrieve(url, local_path)


def check_and_close_elite_modal_ad(driver):
    """Check if a Finviz Elite modal ad pops up and if so, close it."""
    try:
        e = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.ID, 'modal-elite-ad-close')))
    except (TimeoutException, NoSuchElementException):
        return
    try:
        e.click()
    except ElementNotInteractableException:
        return


def write_yaml_record(ticker=None, title=None, basket=None, rsi=None,
                      chart_url=None, local_path=None, iv_percent=None):
    """Write a single ticker record and close the file to save progress."""
    if None in (ticker, title, basket, rsi, chart_url, local_path, iv_percent):
        raise ValueError('All arguments required in write_yaml_record')
    chart_filename = os.path.basename(local_path)
    yaml_file_path = '{}/{}'.format(make_study_dir(), YAML_FILE_NAME)
    record = f'''{ticker}:
  Title: "{title}"
  Basket: {basket}
  RSI: {rsi}
  IV%: {iv_percent}
  Chart:
    URL: {chart_url}
    LocalPath: {chart_filename}
'''
    if not os.path.exists(yaml_file_path):
        with open(yaml_file_path, 'w') as f:
            f.write('---\n')
    with open(yaml_file_path, 'a') as f:
        f.write(record)
    return record


def read_study_file_records():
    yaml_file_path = '{}/{}'.format(make_study_dir(), YAML_FILE_NAME)
    if not os.path.exists(yaml_file_path):
        return {}
    with open(yaml_file_path) as f:
        return yaml.load(f, Loader=yaml.CSafeLoader)


def main():
    set_global_values()

    # Setup finviz driver
    finviz_driver = webdriver.Firefox()

    # Setup marketchameleon driver
    mc_options = webdriver.ChromeOptions()
    mc_options.add_argument('--start-maximized')
    mc_options.add_argument('--disable-blink-features=AutomationControlled')
    marketchameleon_driver = webdriver.Chrome(options=mc_options)

    existing_records = read_study_file_records()
    tickers_total = sum(len(BASKETS[b]) for b in BASKETS)
    tickers_processed = 0
    for basket in BASKETS:
        for ticker in BASKETS[basket]:
            tickers_processed += 1
            if ticker in existing_records:
                print(f'# Skipping {ticker} because it already has a record.')
                continue
            print(f'# Beginning work on {ticker} ({tickers_processed} of {tickers_total}).')

            # Get Finviz data
            finviz_driver.get(FINVIZ_URL_TMPL.format(ticker))
            check_and_close_elite_modal_ad(finviz_driver)
            rsi = scrape_rsi_value(finviz_driver)
            title = scrape_title(finviz_driver)
            chart_url = publish_chart(finviz_driver)
            local_path = get_local_path(ticker)
            download_chart(finviz_driver, chart_url, local_path)

            # Get MarketChameleon data
            marketchameleon_driver.get(MARKETCHAMELEON_URL_TMPL.format(ticker))
            iv_percent = scrape_iv30(marketchameleon_driver)

            print(write_yaml_record(
                    ticker=ticker,
                    title=title,
                    basket=basket,
                    iv_percent=iv_percent,
                    rsi=rsi,
                    chart_url=chart_url,
                    local_path=local_path))
            print(f'# Finished work on {ticker}.')

    # Close browsers
    finviz_driver.quit()
    marketchameleon_driver.quit()


if __name__ == '__main__':
    main()
