import time

import requests
import pprint
from bs4 import BeautifulSoup as bs
from sort_data import sort_data
from store import store_info
from store import load_data

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

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

def get_more_info(nove_list):
    nove_list = load_data()
    for i in nove_list:
        locate = i['locate']
        print(locate)
        url = f"https://series.naver.com/{locate}"


novel_list = []
last_num = 5
#last_num = get_last_num()
get_novel_info(last_num, novel_list)
#get_more_info(novel_list)