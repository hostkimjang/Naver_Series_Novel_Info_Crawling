import pprint
import re
import time
import requests
from info import set_novel_info
from html import unescape
from bs4 import BeautifulSoup as bs


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

def sort_data(page, novel_list):
    for i in page:
        pprint.pprint(i)
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

def info_supplement(novel_list):
    count = 1
    for novel in novel_list:
        locate = novel['locate']
        url = f"https://series.naver.com/{locate}"
        response = requests.get(url=url, headers=headers)
        page = response.text
        #pprint.pprint(page, sort_dicts=False)

        #더보기 추가 시놉시스 display:block 파서 해결 정규식 노가다
        pattern = r'<div class="_synopsis" style="display: none">(.*?)<span class="al_r">'
        matches = re.findall(pattern, page, re.DOTALL)
        results = []
        for match in matches:
            cleaned_match = re.sub(r'&nbsp;|\xa0', ' ', unescape(match))
            cleaned_match = re.sub(r'\s+', ' ', cleaned_match)
            cleaned_match = cleaned_match.replace('\n', '').replace('\t', '').replace('<br/>', '').replace('\r', '')
            results.append(cleaned_match.strip())
        #pprint.pprint(results)
        if not results:
            if novel['info']:
                print("이건 더보기 내용없어")
                #pprint.pprint(novel)
            else:
                print("정보도, 더보기 내용도 없음.")
                #pprint.pprint(novel)
        else:
            combined_result = '\n'.join(results)
            novel['info'] = combined_result
            #pprint.pprint(novel, sort_dicts=False)

        page = bs(page, "lxml")
        tag = page.select("li.info_lst ul li span a")
        if not tag:
            novel['tag'] = "Tag_None"
        else:
            novel['tag'] = tag[0].text

        pprint.pprint(novel, sort_dicts=False)
        print(f"{count}번째 데이터가 추가되었습니다.")
        count += 1

def new_sort_data(data, novel_list):
    for i in data:
        id = i['productNo']
        series_id = i['originalProductId']
        title = i['expansionProductName']
        info = i['synopsis']
        author = i['authorNames']
        chapter = i['totalVolumeCount']
        agegrade = i['seeingGradeCodeType']
        score = i['starScore']
        new_status = ""
        content_type = i['productType']
        locate = i['detailPCPageUrlByNstoreKey']
        thumbnail = i['originalCopyThumbnailUrl']
        last_update = i['lastVolumeUpdateDate']


        novel_info = set_novel_info(platform="NaverSeries",
                                    id=id,
                                    series_id=series_id,
                                    title=title,
                                    info=info,
                                    author=author,
                                    chapter=chapter,
                                    agegrade=agegrade,
                                    score=score,
                                    new_status=new_status,
                                    content_type=content_type,
                                    locate=locate,
                                    thumbnail=thumbnail,
                                    last_update=last_update
                                    )
        novel_list.append(novel_info)

