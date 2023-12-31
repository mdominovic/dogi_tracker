import argparse
import asyncio
import datetime
import json
import telegram
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from io import StringIO


URL = "https://drc-20.org/marketplace"
XPATH_CONFIRM_BUTTON = '//*[@id="root"]/section/main/div/div/div/div/button'
XPATH_TABLE = '//*[@id="root"]/section/main/div/div/div/div[3]/div[1]'
DATA_FILE = "dogi_data_v2.json"

def generate_dogi_data(data):
    key = None
    for k, v in data["#Tick"].items():
        if "dogi" in v:
            key = k

    if key == None:
        return None

    price = data["Price"][key]
    price = price.split("$")
    price_doge = price[0]
    price_dollar = price[1]

    return {
        "tick": "dogi",
        "price_doge": price_doge,
        "price_dollar": price_dollar,
        "volume": data["Volume"][key],
        "change_24h": data["24h %"][key],
        "market_cap": data["Market Cap"][key],
        "holders": data["Holders"][key],
        "supply": data["Circulating Supply"][key],
        "timestamp": get_current_time()
    }


def get_current_time():
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    return formatted_datetime


def get_dogi_data(counter=0):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.page_load_strategy = "none"
    driver = Chrome(options=options)
    driver.implicitly_wait(5)
    driver.get(URL)

    try:
        confirm_button = driver.find_elements(By.XPATH, XPATH_CONFIRM_BUTTON)
        confirm_button[0].click()
    except NoSuchElementException:
        pass

    driver.implicitly_wait(3)
    time.sleep(3)
    content = driver.find_elements(By.XPATH, XPATH_TABLE)
    html_string = content[0].get_attribute("innerHTML")
    tables = pd.read_html(StringIO(html_string))
    html_table = tables[0]
    table_data = pd.DataFrame.to_dict(html_table)
    dogi_data = generate_dogi_data(table_data)
    counter = counter + 1
    if dogi_data:
        return dogi_data
    else:
        if counter > 5:
            return "ERROR"
        else:
            get_dogi_data(counter)


def create_message(data):
    message = """
🔔 Crypto Update: {tick}

💲 Price: ${price_dollar} ({price_doge})
📈 24h Change: {change_24h}
💼 Holders: {holders}
💹 Market Cap: {market_cap}
""".format(
        tick=data.get("tick"),
        price_dollar=data.get("price_dollar"),
        price_doge=data.get("price_doge"),
        change_24h=data.get("change_24h"),
        holders=data.get("holders"),
        market_cap=data.get("market_cap"),
    )
    return message


def store_dogi_data(data):
    with open(DATA_FILE, 'r') as file:
        stored_data = json.load(file)
    stored_data.append(data)
    with open(DATA_FILE, 'w') as file:
        json.dump(stored_data, file, indent=4)


async def notify_chat(api_key, chat_id, message):
    bot = telegram.Bot(api_key)
    async with bot:
        await bot.send_message(text=message, chat_id=chat_id)


def main():
    parser = argparse.ArgumentParser(description="Track and notify about Dogi MC")
    parser.add_argument("chat_id", help="Chat ID")
    parser.add_argument("api_key", help="API Key")
    args = parser.parse_args()

    dogi_data = get_dogi_data()
    message = create_message(dogi_data)
    store_dogi_data(dogi_data)
    asyncio.run(notify_chat(str(args.api_key), str(args.chat_id), message))


if __name__ == "__main__":
    main()
