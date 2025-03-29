import asyncio
import concurrent
import threading
import time
import aiohttp
import chromedriver_autoinstall
import requests
import pprint
from bs4 import BeautifulSoup as bs
from DB_processing import store_db
from sort_data import sort_data, new_sort_data
from sort_data import info_supplement
from store import store_info
from store import load_data
from store import store_final
from naver_api import crawl_novel_views_api

max_worker = 10

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

url = "https://m.series.naver.com/novel/categoryProductMoreList.series"

def get_last_num():
    url = "https://series.naver.com/novel/categoryProductList.series?categoryTypeCode=all&page=1"
    response = requests.get(url=url, headers=headers)
    tmp = bs(response.text, "lxml")
    last_num = tmp.select("#content > div > div > div.total")[0].text
    last_num = last_num.replace("총", "").replace(",", "").replace("개 작품", "")
    last_num = (round(int(last_num)/25) + 1)
    return int(last_num)

def get_novel_info(last_num, novel_list):
    for i in range(1, last_num):
        url = f"https://series.naver.com/novel/categoryProductList.series?categoryTypeCode=all&page={i}"
        response = requests.get(url=url, headers=headers)
        tmp = bs(response.text, "lxml")
        page = tmp.select("#content > div > ul > li")
        sort_data(page, novel_list)
        print(f"{i}페이지 완료")
    store_info(novel_list)

def get_more_info(novel_list):
    novel_list = load_data()
    info_supplement(novel_list)
    store_final(novel_list)


def fetch_page(offset):
    params = {
        "categoryTypeCode": "all",
        "genreCode:": "",
        "orderTypeCode": "new",
        "isFreePassChecked": "false",
        "start": str(offset)
    }
    pprint.pprint(f"offset {offset} 요청")
    response = requests.get(url=url, headers=headers, params=params)
    data = response.json().get("productList")
    return offset, data

def get_novel_info_api(end_num, batch_size=5, max_workers=max_worker):
    novel_list = []

    # Get first page to detect items per page.
    params = {
        "categoryTypeCode": "all",
        "genreCode:": "",
        "orderTypeCode": "new",
        "isFreePassChecked": "false",
        "start": "0"
    }
    first_response = requests.get(url=url, headers=headers, params=params)
    first_data = first_response.json().get("productList")
    if not first_data:
        pprint.pprint("No data on first page")
        return
    new_sort_data(first_data, novel_list)
    items_per_page = len(first_data)
    pprint.pprint(f"First page count: {items_per_page}")

    current_offset = items_per_page
    total_collected = len(first_data)

    while total_collected < end_num:
        batch_offsets = [current_offset + i * items_per_page for i in range(batch_size)]
        empty_found = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(fetch_page, batch_offsets))

        for offset, data in results:
            if not data:
                pprint.pprint(f"Offset {offset} returned no data. Terminating batch processing.")
                empty_found = True
                break
            new_sort_data(data, novel_list)
            total_collected += len(data)
        if empty_found:
            break

        current_offset = batch_offsets[-1] + items_per_page
        pprint.pprint(f"Progress: {total_collected} records collected so far.")

    pprint.pprint(f"Total collected: {total_collected} novel items")
    store_info(novel_list)
    return novel_list


def get_novel_views_api():
    novel_list = load_data()
    crawl_novel_views_api(novel_list)
    store_db()

# novel_list = []
# last_num = 2
#last_num = get_last_num()
# get_novel_info(last_num, novel_list)
#get_more_info(novel_list)

if __name__ == '__main__':
    chromedriver_autoinstall.install()
    chromedriver_autoinstall.get_version()
    start = time.time()
    end_num = 110000
    #get_novel_info_api(end_num)
    get_novel_views_api()
    end = time.time()
    pprint.pprint(f"크롤링 소요시간: {end - start}초")