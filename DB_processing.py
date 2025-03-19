import sqlite3
import json
import time
import os
from datetime import datetime
from pprint import pprint


def load_naver_data():
    with open('NaverSeries_Novel_Info_Final.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        pprint(f"총 {len(data)}개 데이터 로드 완료")
        return data


def change_log(result):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_directory = 'DB_Processing_Log'

    # 디렉터리가 없으면 생성
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_file_path = os.path.join(log_directory, f'{timestamp}-log.json')

    def datetime_convert(obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        raise TypeError(f'Type {type(obj)} not supported.')

    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4, default=datetime_convert)


def convert_korean_number_from_view(view_data):
    if not view_data:
        return 0

    try:
        # Parse values from units in detailList, which is more accurate
        total = 0
        if 'detailList' in view_data and view_data['detailList']:
            for item in view_data['detailList']:
                count = item.get('countPrefix', 0)
                unit = item.get('unitPostfix', '')

                multiplier = 1
                if unit == '만':
                    multiplier = 10000
                elif unit == '천':
                    multiplier = 1000
                elif unit == '억':
                    multiplier = 100000000

                total += count * multiplier
            return total

        # Fallback to top level if detailList is not present
        count = view_data.get('countPrefix', 0)
        unit = view_data.get('unitPostfix', '')

        multiplier = 1
        if unit == '만':
            multiplier = 10000
        elif unit == '천':
            multiplier = 1000
        elif unit == '억':
            multiplier = 100000000

        return count * multiplier

    except Exception as e:
        print(f"Error converting view count: {e}")
        return 0


def store_db():
    novel_list = load_naver_data()
    conn = sqlite3.connect('naver_novel.db')
    cur = conn.cursor()
    start_time = time.time()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS novel (
            id INTEGER PRIMARY KEY,
            series_id TEXT,
            platform TEXT,
            title TEXT,
            info TEXT,
            author TEXT,
            location TEXT,
            thumbnail TEXT,
            tags TEXT,
            chapter INTEGER,
            views INTEGER,
            newstatus TEXT,
            finishstatus BOOLEAN,
            agegrade TEXT,
            score REAL,
            content_type TEXT,
            updatedate DATETIME,
            crawltime DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    count = 1
    total = []
    dt = datetime.now()
    for novel in novel_list:
        if novel is None:
            print("데이터가 없습니다 또는 삭제, 작업이 정상으로 완료되지 않음.")
            continue

        views = convert_korean_number_from_view(novel.get('view'))

        # Store complete agegrade object as JSON string
        agegrade_json = None
        if novel.get('agegrade'):
            agegrade_json = json.dumps(novel['agegrade'], ensure_ascii=False)

        existing_record = cur.execute("SELECT * FROM novel WHERE id=?", (novel["id"],)).fetchone()

        if existing_record:
            # Update logic
            print(f"{novel['id']}는 이미 존재합니다. 레코드를 업데이트합니다.")

            changes = {}
            changes = {}

            # Define field mappings (novel_key, db_column_index)
            fields = [
                ("series_id", 1),
                ("platform", 2),
                ("title", 3),
                ("info", 4),
                ("author", 5),
                ("locate", 6),
                ("thumbnail", 7),
                ("content_type", 8),
                ("chapter", 9),
                ("new_status", 11)
            ]

            # Special cases
            special_fields = [
                ("views", 10, views),
                ("agegrade", 13, agegrade_json),
                ("score", 14, novel.get("score")),
                ("content_type", 15, novel.get("content_type")),
                ("last_update", 16, novel.get("last_update"))
            ]

            # Compare regular fields
            for field, index in fields:
                db_value = existing_record[index]
                novel_value = novel.get(field)
                if db_value != novel_value:
                    changes[field] = {"before": db_value, "after": novel_value}

            # Compare special fields
            for field, index, value in special_fields:
                if existing_record[index] != value:
                    changes[field] = {"before": existing_record[index], "after": value}

            if changes:
                print(f"변경된 사항: {changes}")
                total.append({"ID": novel["id"], "Changes": changes})


            cur.execute("""
                UPDATE novel
                SET series_id=?, platform=?, title=?, info=?, author=?, location=?, thumbnail=?,
                    chapter=?, views=?, newstatus=?, agegrade=?, score=?, content_type=?, updatedate=?, crawltime=?
                WHERE id=?
            """, (
                novel.get("series_id"), novel["platform"], novel["title"], novel["info"],
                novel["author"], novel["locate"], novel["thumbnail"], novel["chapter"],
                views, novel.get("new_status", ""), agegrade_json,
                novel.get("score"), novel.get("content_type"), novel.get("last_update"), dt,
                novel["id"]
            ))
        else:
            # Insert logic
            print(f"ID:{novel['id']}는 기존에 존재하지 않습니다. 새 레코드를 추가합니다.")

            cur.execute("""
                INSERT INTO novel
                (id, series_id, platform, title, info, author, location, thumbnail,
                chapter, views, newstatus, agegrade, score, content_type, updatedate, crawltime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                novel["id"], novel.get("series_id"), novel["platform"], novel["title"],
                novel["info"], novel["author"], novel["locate"], novel["thumbnail"],
                novel["chapter"], views, novel.get("new_status", ""), agegrade_json,
                novel.get("score"), novel.get("content_type"), novel.get("last_update"), dt
            ))

        print(f"{count}/{len(novel_list)}번째 데이터 저장 완료")
        count += 1

    end_time = time.time()
    pprint(f"총 {end_time - start_time:.2f}초 소요")
    pprint("데이터 저장 완료")
    conn.commit()
    conn.close()

    if total:
        change_log(total)


if __name__ == '__main__':
    store_db()