import pprint
import re
import time
from info import set_novel_info
from bs4 import BeautifulSoup as bs


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

def sort_data(page, novel_list):
    for i in page:
        episode_status = i.select("div > h3 > em.ico")
        if not episode_status:
            episode_status = "No"
        else:
            episode_status = episode_status[0].text

        age_status = i.select("div > h3 > em.n19")
        if not age_status:
            age_status = "Age_None"
        else:
            age_status = age_status[0].text


        title = i.select("div > h3 > a")[0].text
        scroe = i.select("div > p.info > em.score_num")[0].text

        info = i.select("div > p.dsc")
        if not info:
            info = "Info None"
        else:
            info = re.sub(r'\s+', ' ', i.select("div > p.dsc")[0].text).strip()

        author = i.select("div > p.info > span.author")[0].text
        thumbnail = i.select("a > img")[0]['src']
        a = i.select("div h3 a")
        locate = a[0]['href']

        novel_info = set_novel_info("NaverSeries",
                                    title,
                                    info,
                                    author,
                                    age_status,
                                    scroe,
                                    episode_status,
                                    "Novel",
                                    locate,
                                    thumbnail)

        novel_list.append(novel_info)

def info_supplement(response, novel_list):
    page = bs(response.text, "lxml",)

    print(page.find("div._synopsis", {"style": "display: none;"}))

    time.sleep(100)