import base64
import concurrent.futures
import hashlib
import hmac
import os
import pprint
import time
import urllib.parse
import chromedriver_autoinstall
import requests
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from store import store_final

max_worker = 50

headers = {
    "User-Agent": "NaverBooks/3.48.0 (Android OS 11; SM-S908E) #PocketReader_AndroidPhone",
    "Accept-Encoding": "gzip"
}

# SeriesApp 하드코딩된 APIsecretKey
naver_api_secret_key = "fkdVcJrQ6PbZ9cY3RJjw2OCl65axjgw04cKmLILUkfJmzXEUUlbwMujkwxVRCJHj"


def update_env_file(cookies):
    """Update .env file with Naver cookies"""
    # Convert dictionary to env file format
    cookie_str = f"NAVER_COOKIE_NID_AUT={cookies.get('NID_AUT', '')}\n"
    cookie_str += f"NAVER_COOKIE_NID_SES={cookies.get('NID_SES', '')}"

    # Read existing .env file
    env_path = ".env"
    try:
        with open(env_path, "r") as file:
            lines = file.readlines()
    except FileNotFoundError:
        lines = []

    # Remove existing cookie entries
    new_lines = []
    for line in lines:
        if not line.startswith(("NAVER_COOKIE_NID_AUT=", "NAVER_COOKIE_NID_SES=")):
            new_lines.append(line.rstrip('\n'))

    # Add the new cookie entries
    for cookie_line in cookie_str.split('\n'):
        new_lines.append(cookie_line)

    # Write back to .env file
    with open(env_path, "w") as file:
        file.write('\n'.join(new_lines))

    print("Cookie information saved to .env file")


def get_naver_cookies(username: str, password: str) -> dict:
    """네이버 로그인 후 NID_AUT와 NID_SES 쿠키를 추출"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # CAPTCHA 확인 위해 headless 비활성화 (성공 시 주석 해제)
    chrome_options.add_argument("--no-sandbox") # Docker 환경 필수 옵션
    chrome_options.add_argument("--disable-dev-shm-usage") # Docker 환경 메모리 문제 방지
    chrome_options.add_argument("--disable-gpu") # GPU 비활성화 (일부 환경 문제 방지)

    # ChromeDriver 자동 설치
    #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    # 우분투 도커 ChromeDriver 자동 설치
    chromedriver_autoinstall.install()
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # 네이버 로그인 페이지 이동
        driver.get("https://nid.naver.com/nidlogin.login")
        wait = WebDriverWait(driver, 10)

        # 아이디 입력 필드가 나타날 때까지 대기
        id_input = wait.until(EC.presence_of_element_located((By.ID, "id")))
        id_input.click()
        print(f"ID 입력: {username}", flush=True)
        # JavaScript로 직접 값 주입 (보안 차단 우회 시도)
        driver.execute_script("arguments[0].value = arguments[1];", id_input, username)
        time.sleep(1)

        # 패스워드 입력 필드가 나타날 때까지 대기
        pw_input = wait.until(EC.presence_of_element_located((By.ID, "pw")))
        pw_input.click()
        #print(f"Password 입력: {password}")
        # JavaScript로 직접 값 주입
        driver.execute_script("arguments[0].value = arguments[1];", pw_input, password)
        time.sleep(1)

        # 로그인 버튼 클릭
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "log.login")))
        login_button.click()
        time.sleep(5)  # 로그인 대기

        # '새로운 환경' 알림에서 '등록안함' 버튼 처리
        try:
            cancel_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.btn_cancel")))
            cancel_button.click()
            print("기기 등록 '등록안함' 처리 완료", flush=True)
        except:
            print("기기 등록 '등록안함' 버튼을 찾을 수 없습니다.", flush=True)

        # CAPTCHA 여부 확인
        if "captcha" in driver.current_url.lower():
            print("CAPTCHA가 나타났습니다. 브라우저에서 해결 후 Enter를 눌러주세요.", flush=True)
            input("계속하려면 Enter를 누르세요...", flush=True)

        # 쿠키 추출
        cookies = driver.get_cookies()
        cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        nid_aut = cookie_dict.get("NID_AUT")
        nid_ses = cookie_dict.get("NID_SES")

        if nid_aut and nid_ses:
            print("로그인 성공, 쿠키 획득 완료", flush=True)
            return {"NID_AUT": nid_aut, "NID_SES": nid_ses}
        else:
            raise Exception("NID_AUT 또는 NID_SES 쿠키를 찾을 수 없습니다.", flush=True)

    finally:
        driver.quit()


def get_hmac_url(base_url, secret_key):
    t = str(int(time.time() * 1000))  # wf.a.c는 0으로 가정
    url_part = base_url[:min(255, len(base_url))]  # vf.a.b() 반영
    data_to_sign = (url_part + t).encode('utf-8')
    secret_bytes = secret_key.encode('utf-8')
    signature = hmac.new(secret_bytes, data_to_sign, hashlib.sha1).digest()
    md = base64.b64encode(signature).decode('utf-8')
    md_encoded = urllib.parse.quote(md)
    separator = '&' if '?' in base_url else '?'
    full_url = f"{base_url}{separator}msgpad={t}&md={md_encoded}"
    return full_url

def is_cookie_valid(cookies):
    """Check if the Naver cookies are still valid"""
    url = "https://nid.naver.com/user2/help/myInfoV2"
    # url = get_hmac_url(test_url, naver_api_secret_key)
    print("Checking cookie validity:", url , flush=True)
    session = requests.Session()
    session.cookies.update(cookies)

    try:
        response = session.get(url, headers=headers, verify=False)
        #pprint.pprint(response.text)
        # Check fo  r unauthorized or forbidden status codes
        if response.status_code in [401, 403] or "<title>네이버 : 로그인</title>" in response.text:
            print("쿠키 유효성 확인 실패:", response.status_code, flush=True)
            return False
        # Check for specific error messages in response
        if response.status_code in [200] and "<title>네이버ID</title>" not in response.text:
            print("쿠키 유효성 확인 성공", flush=True)
            return False
        return True
    except Exception:
        return False


def crawl_naver(base_url, secret_key, cookies: dict, naver_id, naver_pw):
    """
    네이버 시리즈 API를 크롤링하고, 쿠키가 만료되면 갱신합니다.
    """
    url = get_hmac_url(base_url, secret_key)
    print("Requesting:", url, flush=True)

    # requests 세션으로 쿠키 통합
    session = requests.Session()
    session.cookies.update(cookies)

    try:
        response = session.get(url, headers=headers)
        if response.ok:
            print("Success:", response.status_code, flush=True)
            print(response.text)
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            if response.status_code in [401, 403, 500]:  # 인증 실패 시
                print("쿠키가 만료되었을 가능성이 있습니다. 쿠키를 갱신합니다.", flush=True)
                new_cookies = get_naver_cookies(naver_id, naver_pw)
                if new_cookies:
                    print("새로운 쿠키 획득 완료:", new_cookies, flush=True)
                    update_env_file(new_cookies)  # .env 파일 업데이트
                    return crawl_naver(base_url, secret_key, new_cookies, naver_id, naver_pw)  # 재시도
                else:
                    print("쿠키 갱신 실패.", flush=True)
                    return None
            else:
                return None
    except Exception as e:
        print("Exception:", str(e))
        return None

# def crawl_novel_views_api(novel_list):
#     ready_result = crawl_ready_run()
#
#     if ready_result is None:
#         print("쿠키 준비 실패")
#         return
#
#     cookies, naver_id, naver_pw = ready_result
#
#     for i in novel_list:
#         url = f"https://apis.naver.com/series-app/series/v4/contents/{(i['series_id'])}?recommendContents=true&platformType=SERIES_NORMAL"
#         pprint.pprint(url)
#
#         # 크롤링 실행
#         response = crawl_naver(url, naver_api_secret_key, cookies, naver_id, naver_pw)
#
#         if response and 'result' in response and 'contents' in response['result']:
#             contents = response['result']['contents']
#
#             if 'saleVolumeCount' in contents:
#                 sale_volume = contents['saleVolumeCount']
#                 # Store full saleVolumeCount object
#                 i['view'] = sale_volume
#
#                 # You can also extract specific fields if needed
#                 # For example: i['view_count'] = f"{sale_volume['countPrefix']}{sale_volume['unitPostfix']}"
#
#                 print(f"View count added for {i['title']}: {sale_volume}")
#             else:
#                 i['view'] = None
#                 print(f"No saleVolumeCount found for {i['title']}")
#         else:
#             i['view'] = None
#             print(f"Failed to get data for {i['title']}")

def fetch_novel_view(novel, cookies, secret_key, naver_id, naver_pw, counter, lock, total_novels):
    url = f"https://apis.naver.com/series-app/series/v4/contents/{novel['series_id']}?recommendContents=true&platformType=SERIES_NORMAL"

    response = crawl_naver(url, secret_key, cookies, naver_id, naver_pw)

    # Update counter and print progress
    with lock:
        counter['processed'] += 1
        current = counter['processed']
        remaining = total_novels - current
        print(f"진행 중: {current}/{total_novels} (남은 개수: {remaining}) - {novel['title']}")

    if response and 'result' in response and 'contents' in response['result']:
        contents = response['result']['contents']
        if 'saleVolumeCount' in contents:
            sale_volume = contents['saleVolumeCount']
            novel['view'] = sale_volume
            print(f"조회수 추가됨: {novel['title']} - {sale_volume}")
        else:
            novel['view'] = None
            print(f"조회수 정보 없음: {novel['title']}")
    else:
        novel['view'] = None
        print(f"데이터 가져오기 실패: {novel['title']}")

    return novel


def crawl_novel_views_api(novel_list):
    ready_result = crawl_ready_run()
    if ready_result is None:
        print("쿠키 준비 실패", flush=True)
        return
    else:
        print("쿠키 준비 완료 크롤링 준비 대기중...", flush=True)
        cookies, naver_id, naver_pw = ready_result

        time.sleep(30)

        counter = {'processed': 0}
        lock = threading.Lock()
        total_novels = len(novel_list)

        # ThreadPoolExecutor로 병렬 요청 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_worker) as executor:
            futures = [
                executor.submit(fetch_novel_view, novel, cookies, naver_api_secret_key,
                               naver_id, naver_pw, counter, lock, total_novels)
                for novel in novel_list
            ]
            # 모든 요청이 완료될 때까지 대기
            concurrent.futures.wait(futures)

        print(f"완료: {total_novels}개 중 {counter['processed']}개 처리됨", flush=True)
        store_final(novel_list)



def crawl_ready_run():
    naver_id = os.environ.get("NAVER_ID")
    naver_pw = os.environ.get("NAVER_PW")
    nid_aut = os.environ.get("NAVER_COOKIE_NID_AUT")
    nid_ses = os.environ.get("NAVER_COOKIE_NID_SES")

    try:
        if not naver_id or not naver_pw:
            raise Exception("환경변수에 NAVER_ID와 NAVER_PW를 설정해주세요.")

        cookies = {}
        if nid_aut and nid_ses:
            cookies["NID_AUT"] = nid_aut
            cookies["NID_SES"] = nid_ses
            print("쿠키 존재 확인.", flush=True)
            print(cookies)
            print("쿠키 유효성 확인 중...", flush=True)
            is_valid = is_cookie_valid(cookies)
            if not is_valid:
                print("쿠키가 만료되었습니다. 로그인 후 쿠키를 받아옵니다.", flush=True)
                # 로그인 후 쿠키 획득
                cookies = get_naver_cookies(naver_id, naver_pw)
                # 쿠키 env에 저장
                update_env_file(cookies)
                print("획득한 쿠키:", cookies, flush=True)
        else:
            print("네이버 쿠키가 존재 하지 않습니다. 로그인후 쿠키를 받아옵니다.", flush=True)
            # 로그인 후 쿠키 획득
            cookies = get_naver_cookies(naver_id, naver_pw)
            # 쿠키 env에 저장
            update_env_file(cookies)
            print("획득한 쿠키:", cookies, flush=True)

        print("쿠키 유효성 확인 완료!", flush=True)
        return cookies, naver_id, naver_pw

    except Exception as e:
        print(f"오류: {e}", flush=True)
        return None, None, None

if __name__ == '__main__':
    # 네이버 로그인 정보 (실제 값으로 대체)
    naver_id = os.environ.get("NAVER_ID")
    naver_pw = os.environ.get("NAVER_PW")
    nid_aut = os.environ.get("NAVER_COOKIE_NID_AUT")
    nid_ses = os.environ.get("NAVER_COOKIE_NID_SES")

    # 테스트 URL
    test_url = "https://apis.naver.com/series-app/series/v4/contents/360163?recommendContents=true&platformType=SERIES_NORMAL"

    try:
        if not naver_id or not naver_pw:
            raise Exception("환경변수에 NAVER_ID와 NAVER_PW를 설정해주세요.")

        cookies = {}
        if nid_aut and nid_ses:
            cookies["NID_AUT"] = nid_aut
            cookies["NID_SES"] = nid_ses
            print("쿠키 존재 확인.", flush=True)
            print(cookies, flush=True)
        else:
            print("네이버 쿠키가 존재 하지 않습니다. 로그인후 쿠키를 받아옵니다.", flush=True)
            # 로그인 후 쿠키 획득
            cookies = get_naver_cookies(naver_id, naver_pw)
            # 쿠키 env에 저장
            update_env_file(cookies)
            print("획득한 쿠키:", cookies, flush=True)

        # 크롤링 실행
        crawl_naver(test_url, naver_api_secret_key, cookies, naver_id, naver_pw)
    except Exception as e:
        print(f"오류: {e}" , flush=True)