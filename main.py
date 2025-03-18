import time
import requests
import pprint
from bs4 import BeautifulSoup as bs
from sort_data import sort_data, new_sort_data
from sort_data import info_supplement
from store import store_info
from store import load_data
from store import store_final

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

def get_more_info(novel_list):
    novel_list = load_data()
    info_supplement(novel_list)
    store_final(novel_list)

def get_novel_info_api(end_num):
    novel_list = []
    url = f"https://m.series.naver.com/novel/categoryProductMoreList.series"
    page = 0
    # response = requests.get(url=url, headers=headers, params=params)
    # data = response.json().get("productList")
    # pprint.pprint(data)
    # pprint.pprint(len(data))

    for i in range(0, end_num):
        params = {
            "categoryTypeCode": "all",
            "genreCode:": "",
            "orderTypeCode": "new",
            "isFreePassChecked": "false",
            "start": f"{page}"
        }

        pprint.pprint(f"페이지 {page} 작업")
        response = requests.get(url=url, headers=headers, params=params)
        data = response.json().get("productList")

        if data == []:
            pprint.pprint(f"더 이상 없음 순회 종료.")
            break

        page += len(data)
        new_sort_data(data, novel_list, count)



# novel_list = []
# last_num = 2
#last_num = get_last_num()
# get_novel_info(last_num, novel_list)
#get_more_info(novel_list)


if __name__ == '__main__':
    end_num = 3
    get_novel_info_api(end_num)
