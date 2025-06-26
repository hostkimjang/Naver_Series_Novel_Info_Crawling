import asyncio
import concurrent
import threading
import time
import aiohttp
from dotenv import load_dotenv
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
from db_connect import store_db_naver_series_pg_copy

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
    
    try:
        response = requests.get(url=url, headers=headers, params=params, timeout=30)
        
        # HTTP 상태 코드 확인
        if response.status_code != 200:
            pprint.pprint(f"HTTP 오류 {response.status_code} for offset {offset}: {response.text[:200]}")
            return offset, None
        
        # 응답 내용 확인
        if not response.text.strip():
            pprint.pprint(f"빈 응답 for offset {offset}")
            return offset, None
        
        # JSON 파싱 시도
        try:
            json_data = response.json()
            data = json_data.get("productList")
            return offset, data
        except requests.exceptions.JSONDecodeError as e:
            pprint.pprint(f"JSON 파싱 오류 for offset {offset}: {e}")
            pprint.pprint(f"응답 내용 (처음 500자): {response.text[:500]}")
            return offset, None
            
    except requests.exceptions.Timeout:
        pprint.pprint(f"타임아웃 오류 for offset {offset}")
        return offset, None
    except requests.exceptions.RequestException as e:
        pprint.pprint(f"네트워크 오류 for offset {offset}: {e}")
        return offset, None
    except Exception as e:
        pprint.pprint(f"예상치 못한 오류 for offset {offset}: {e}")
        return offset, None

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
    
    try:
        first_response = requests.get(url=url, headers=headers, params=params, timeout=30)
        if first_response.status_code != 200:
            pprint.pprint(f"첫 페이지 요청 실패: HTTP {first_response.status_code}")
            return
            
        first_data = first_response.json().get("productList")
        if not first_data:
            pprint.pprint("첫 페이지에 데이터가 없습니다")
            return
        new_sort_data(first_data, novel_list)
        items_per_page = len(first_data)
        pprint.pprint(f"첫 페이지 아이템 수: {items_per_page}")
    except Exception as e:
        pprint.pprint(f"첫 페이지 처리 중 오류: {e}")
        return

    current_offset = items_per_page
    total_collected = len(first_data)
    consecutive_empty_batches = 0
    max_empty_batches = 3  # 연속으로 3번 빈 응답이 오면 중단

    while total_collected < end_num and consecutive_empty_batches < max_empty_batches:
        batch_offsets = [current_offset + i * items_per_page for i in range(batch_size)]
        empty_found = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(fetch_page, batch_offsets))

        batch_has_data = False
        for offset, data in results:
            if data is None:
                pprint.pprint(f"Offset {offset}에서 데이터 없음")
                continue
            if not data:
                pprint.pprint(f"Offset {offset}에서 빈 데이터 반환")
                continue
            new_sort_data(data, novel_list)
            total_collected += len(data)
            batch_has_data = True

        if not batch_has_data:
            consecutive_empty_batches += 1
            pprint.pprint(f"연속 빈 배치: {consecutive_empty_batches}/{max_empty_batches}")
        else:
            consecutive_empty_batches = 0  # 데이터가 있으면 카운터 리셋

        current_offset = batch_offsets[-1] + items_per_page
        pprint.pprint(f"진행 상황: 지금까지 {total_collected}개 수집됨")

    if consecutive_empty_batches >= max_empty_batches:
        pprint.pprint(f"연속 {max_empty_batches}번 빈 응답으로 인해 크롤링 중단")

    pprint.pprint(f"총 수집된 소설: {total_collected}개")
    store_info(novel_list)
    return novel_list


def get_novel_views_api():
    novel_list = load_data()
    crawl_novel_views_api(novel_list)
    store_db()
    store_db_naver_series_pg_copy()

# novel_list = []
# last_num = 2
#last_num = get_last_num()
# get_novel_info(last_num, novel_list)
#get_more_info(novel_list)

if __name__ == '__main__':
    load_dotenv()
    print("크롤러 시작", flush=True)
    chromedriver_autoinstall.install()
    print(chromedriver_autoinstall.get_version(), flush=True)
    print(chromedriver_autoinstall.get_platform(), flush=True)
    start = time.time()
    end_num = 110000
    get_novel_info_api(end_num)
    get_novel_views_api()
    end = time.time()
    print(f"크롤링 소요시간: {end - start}초")