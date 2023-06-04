#!/usr/bin/env python3

"""Download charts from Finviz website for a set of tickers.
"""


import datetime
import os
import time
import urllib.request

from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


_OPENER = None

STUDY_BASE_DIR = 'study'
YAML_FILE_NAME = 'study.yaml'
BASKETS = {
    'US Stocks': ('SPY', 'IWM', 'DIA'),
    'US Bonds': ('TLT', 'HYG', 'LQD'),
    'International': ('EEM', 'EFA', 'EWZ', 'FXI'),
    'Technology': ('AAPL', 'ADBE', 'AMAT', 'AMD', 'AVGO', 'CRM', 'CRWD', 'DOCU', 'MRVL', 'MSFT', 'NET', 'NFLX', 'NVDA', 'ORCL', 'QQQ', 'SHOP', 'SMH', 'TSM', 'TTD', 'UBER', 'XLK', 'HPQ', 'INTC', 'ARKK', 'CSCO', 'FSLR', 'IBM', 'QCOM', 'SQ', 'TXN'),
    'Communications': ('CMCSA', 'GOOG', 'META', 'DIS', 'BIDU', 'ROKU', 'T', 'VZ'),
    'Consumer': ('AMZN', 'DKNG', 'KO', 'LVS', 'MAR', 'MCD', 'MDLZ', 'PEP', 'RCL', 'TJX', 'XLY', 'COST', 'EXPE', 'HD', 'KR', 'MGM', 'NCLH', 'PG', 'SBUX', 'WMT', 'XLP', 'BABA', 'BBY', 'BYND', 'CHWY', 'CZR', 'F', 'GM', 'JD', 'KSS', 'LOW', 'MO', 'NKE', 'TGT', 'TSLA', 'VFC', 'XRT'),
    'Energy': ('USO', 'APA', 'BP', 'COP', 'CVX', 'DVN', 'HAL', 'KMI', 'MPC', 'MRO', 'OXY', 'RIG', 'SLB', 'XLE', 'XOM', 'XOP'),
    'Health': ('MRK', 'XBI', 'ABT', 'WBA', 'ABBV', 'CVS', 'JNJ', 'MRNA', 'PFE'),
    'Utilities': ('XLU',),
    'Finance': ('AIG', 'BAC', 'BX', 'C', 'COF', 'GS', 'JPM', 'PYPL', 'V', 'XLF', 'AXP', 'FITB', 'KRE', 'MET', 'MS', 'PNC', 'SCHW', 'USB', 'VXX', 'WFC'),
    'Materials': ('CF', 'CLF', 'DOW', 'FCX', 'MOS', 'NEM', 'X', 'XLB'),
    'Industrial': ('AAL', 'GE', 'UAL', 'XHB', 'BA', 'DAL', 'FDX', 'CAT', 'DE', 'LUV', 'UPS'),
    'Precious Metals': ('GDX', 'GLD', 'GOLD', 'SLV'),
    'Real Estate': ('IYR',),
}
FINVIZ_URL_TMPL = 'https://finviz.com/quote.ashx?t={}&ty=c&ta=1&p=d&r=m3'


def scrape_rsi_value(driver):
    css_selector = 'tr.table-dark-row:nth-child(9) > td:nth-child(10) > b:nth-child(1)'
    e = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    try:
        return float(e.text)
    except ValueError:
        return -1


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
        study_dir = '{}/{}'.format(STUDY_BASE_DIR, date_str)
        if not os.path.exists(study_dir):
            os.makedirs(study_dir)
        _STUDY_DIR = study_dir
    return _STUDY_DIR


def get_local_path(ticker):
    return '{}/{}-D-M3.png'.format(make_study_dir(), ticker)


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


def write_yaml_record(ticker, basket, rsi, chart_url, chart_local_path):
    """Write a single ticker record and close the file to save progress."""
    chart_filename = os.path.basename(chart_local_path)
    yaml_file_path = '{}/{}'.format(make_study_dir(), YAML_FILE_NAME)
    record = f'''{ticker}:
  Basket: {basket}
  RSI: {rsi}
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


def main():
    driver = webdriver.Firefox()
    for basket in BASKETS:
        for ticker in BASKETS[basket]:
            driver.get(FINVIZ_URL_TMPL.format(ticker))
            check_and_close_elite_modal_ad(driver)
            rsi = scrape_rsi_value(driver)
            chart_url = publish_chart(driver)
            local_path = get_local_path(ticker)
            download_chart(driver, chart_url, local_path)
            print(write_yaml_record(ticker, basket, rsi, chart_url, local_path))
            print('# Waiting 3s before operating on next ticker ...')
            time.sleep(3)


if __name__ == '__main__':
    main()
