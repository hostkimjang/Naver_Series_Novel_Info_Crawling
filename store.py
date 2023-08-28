import json

def store_info(info_list):
    with open("NaverSeries_Novel_Info.json", "wt", encoding="utf-8") as f:
        novel_data = []
        for info in info_list:
            novel_dict = {
                "platform": info.platform,
                "title": info.title,
                "info": info.info,
                "author": info.author,
                "agegrade": info.agegrade,
                "score": info.score,
                "new_status": info.new_status,
                "content_type": info.content_type,
                "locate": info.locate,
                "thumbnail": info.thumbnail
            }
            novel_data.append(novel_dict)
        json.dump(novel_data, f, ensure_ascii=False, indent=4)

        count = len(info_list)
        print(f"총 {count}개의 데이터가 저장되었습니다.")
        print("store is done")

