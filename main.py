import time
import requests
import pprint
import re
from bs4 import BeautifulSoup as bs


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

for i in range(1, 2):
    url = f"https://series.naver.com/novel/categoryProductList.series?categoryTypeCode=all&page={i}"
    response = requests.get(url=url, headers=headers)
    tmp = bs(response.text, "lxml")
    page = tmp.select("#content > div > ul > li")

    for i in page:
        episode_status = i.select("div > h3 > em.ico.ico_update")[0].text
        title = i.select("div > h3 > a")[0].text
        scroe = i.select("div > p.info > em.score_num")[0].text
        info = re.sub(r'\s+', ' ', i.select("div > p.dsc")[0].text).strip()
        author = i.select("div > p.info > span.author")[0].text
        thumbnail = i.select("a > img")[0]['src']
        a = i.select("div h3 a")
        a_href = a[0]['href']

        print(episode_status)
        print(title)
        pprint.pprint(info)
        print(author)
        print(thumbnail)
        print(a_href)
        print(scroe)



        time.sleep(100)

        # content > div > ul > li:nth-child(1) > div > h3 > a
    time.sleep(100)