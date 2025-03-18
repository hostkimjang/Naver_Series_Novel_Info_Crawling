import time
import hmac
import hashlib
import base64
import urllib.parse
import requests

# 요청 헤더 (네트워크 로그 반영)
headers = {
    "User-Agent": "NaverBooks/3.48.0 (Android OS 11; SM-S908E) #PocketReader_AndroidPhone",
    "Accept-Encoding": "gzip"
}


def get_hmac_url(base_url, secret_key):
    # 현재 시간 (밀리초 단위, vf.a.d()의 Calendar.getInstance().getTimeInMillis() 재현)
    t = str(int(time.time() * 1000))  # wf.a.c는 0으로 가정

    # URL의 앞 255자만 사용 (vf.a.b() 반영)
    url_part = base_url[:min(255, len(base_url))]

    # HMAC-SHA1 서명 계산 (vf.a.c()와 vf.a.a() 로직)
    data_to_sign = (url_part + t).encode('utf-8')  # paramString + msgpad
    secret_bytes = secret_key.encode('utf-8')
    signature = hmac.new(secret_bytes, data_to_sign, hashlib.sha1).digest()

    # Base64 인코딩 후 URL 인코딩 (vf.a.e() 반영)
    md = base64.b64encode(signature).decode('utf-8')
    md_encoded = urllib.parse.quote(md)

    # 쿼리 스트링 구분자 처리 (vf.a.e()의 ?/& 로직)
    separator = '&' if '?' in base_url else '?'
    full_url = f"{base_url}{separator}msgpad={t}&md={md_encoded}"
    return full_url


def crawl_naver(base_url, secret_key, interval=5):
    url = get_hmac_url(base_url, secret_key)
    print("Requesting:", url)
    try:
        response = requests.get(url, headers=headers, verify=False)  # SSL 검증 비활성화
        if response.ok:
            print("Success:", response.status_code)
            # Gzip 압축 해제 후 텍스트 출력
            print(response.text)
        else:
            print("Error:", response.status_code, response.text)
    except Exception as e:
        print("Exception:", str(e))
    time.sleep(interval)


if __name__ == '__main__':
    # 테스트 URL (제공된 예시 기반)
    base_url = "https://apis.naver.com/series-app/series/v4/contents/569813?recommendContents=true&platformType=SERIES_NORMAL"

    # secretKey는 아직 확인되지 않음, 공백으로 유지하거나 추정값 입력 가능
    naver_api_secret_key = "5f36ae8f-bc10-4c6f-81c6-b51efd5c9288"  # 예: "mySecret" 또는 "7tp2BgQ33S61" (nac) 테스트 가능

    crawl_naver(base_url, naver_api_secret_key)