from pprint import pprint
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, BigInteger, Text, DateTime, Boolean, text, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from datetime import datetime
import json
import time
import csv
import tempfile

load_dotenv()

BATCH_SIZE = 1000

# Load environment variables
USER = os.getenv('PG_USER')
PASSWORD = os.getenv('PG_PASSWORD')
HOST = os.getenv('PG_HOST')
PORT = os.getenv('PG_PORT')
DBNAME = os.getenv('PG_DB')

db_url = f'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}'
engine = create_engine(db_url, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

Base = declarative_base()

class NaverSeries(Base):
    __tablename__ = 'naver_series'
    id = Column(BigInteger, primary_key=True)
    series_id = Column(Text)
    platform = Column(Text)
    title = Column(Text)
    info = Column(Text)
    author = Column(Text)
    location = Column(Text)
    thumbnail = Column(Text)
    tags = Column(Text)
    chapter = Column(BigInteger, default=0)
    views = Column(BigInteger, default=0)
    newstatus = Column(Text)
    finishstatus = Column(Boolean, default=False)
    agegrade = Column(Text)
    score = Column(Float, default=0.0)
    content_type = Column(Text)
    updatedate = Column(DateTime(timezone=True))
    crawltime = Column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    
    def __repr__(self):
        return f"<NaverSeries(id={self.id}, title='{self.title}', author='{self.author}')>"

def load_novel_data():
    with open('NaverSeries_Novel_Info_Final.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        pprint(f"총 {len(data)}개 데이터 로드 완료")
        return data

def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def safe_parse_datetime(date_str):
    """안전한 날짜 문자열 파싱 함수"""
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # 다양한 날짜 형식 시도
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2002-10-18 08:03:12
        '%Y-%m-%dT%H:%M:%S',  # ISO format
        '%Y-%m-%dT%H:%M:%S.%f',  # ISO format with microseconds
        '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format with timezone
        '%Y-%m-%dT%H:%M:%SZ',  # ISO format with timezone
        '%Y-%m-%d %H:%M:%S.%f',  # with microseconds
        '%Y-%m-%d',  # date only
        '%Y%m%d%H%M%S',  # 20021018080312
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # 모든 형식이 실패하면 현재 시간 반환
    print(f"Warning: Could not parse date '{date_str}', using current time")
    return datetime.now()

def clean_text(val):
    if val is None:
        return ''
    import re
    cleaned = re.sub(r'<br\s*/?>', ' ', str(val), flags=re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = cleaned.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def extract_view_count(view_data):
    """view 데이터에서 조회수 추출"""
    if not view_data:
        return 0
    
    if isinstance(view_data, dict):
        count_prefix = view_data.get('countPrefix', 0)
        unit_postfix = view_data.get('unitPostfix', '')
        
        # 단위 변환 (만, 천 등)
        multiplier = 1
        if unit_postfix == '만':
            multiplier = 10000
        elif unit_postfix == '천':
            multiplier = 1000
        
        return int(count_prefix * multiplier)
    
    return 0

def main_queries():
    with Session() as session:
        try:
            print("--- 상위 5개 소설 조회 ---")
            novels = session.query(NaverSeries).limit(5).all();
            [print(n) for n in novels]
            print("\n--- ID=12186404 소설 조회 ---")
            novel = session.query(NaverSeries).filter(NaverSeries.id == 12186404).first()
            if novel: print(f"Found: {novel.title} by {novel.author}")
            print("\n--- 마지막 5개 소설 조회 ---")
            last_novels = session.query(NaverSeries).order_by(NaverSeries.id.desc()).limit(5).all();
            [print(n) for n in last_novels]
        except Exception as e:
            print(f"쿼리 중 에러 발생: {e}")

def store_db_naver_series_pg_copy():
    novel_list = load_novel_data()

    start_time = time.time()
    dt = datetime.now()
    total_processed = 0

    pprint(f"총 {len(novel_list)}개 데이터 로드 완료")

    with Session() as session:
        db_novels_dict = {n.id: n for n in session.query(NaverSeries)}
        db_ids = set(db_novels_dict.keys())
        print(f"DB에 {len(db_ids)}개 데이터 존재")

        insert_data, update_data, update_log = [], [], []
        field_map = {
            'series_id': 'series_id',
            'platform': 'platform',
            'title': 'title',
            'info': 'info',
            'author': 'author',
            'locate': 'location',  # JSON의 locate를 DB의 location으로 매핑
            'thumbnail': 'thumbnail',
            'chapter': 'chapter',
            'new_status': 'newstatus',  # JSON의 new_status를 DB의 newstatus로 매핑
            'agegrade': 'agegrade',
            'score': 'score',
            'content_type': 'content_type',
            'last_update': 'updatedate'  # JSON의 last_update를 DB의 updatedate로 매핑
        }
        
        for novel in novel_list:
            n_id = novel.get("id")
            if n_id is None: continue
            
            # ID를 정수로 변환
            try:
                n_id = int(n_id)
            except (ValueError, TypeError):
                print(f"Invalid ID: {n_id}, skipping...")
                continue
                
            is_new = n_id not in db_ids
            db_novel = None if is_new else db_novels_dict[n_id]
            payload = {'id': n_id}
            changes = {}
            
            for json_key, orm_key in field_map.items():
                new_val = novel.get(json_key)
                old_val = None if is_new else getattr(db_novel, orm_key)

                # agegrade는 JSON 문자열로 저장
                if json_key == 'agegrade':
                    if new_val is not None:
                        import json as _json
                        new_val = _json.dumps(new_val, ensure_ascii=False)
                elif json_key == 'score':
                    try:
                        new_val = float(new_val) if new_val is not None else 0.0
                    except (ValueError, TypeError):
                        new_val = 0.0

                # 정수형 처리
                if orm_key in ["chapter"]:
                    try:
                        new_val = int(new_val) if new_val is not None else 0
                    except (ValueError, TypeError):
                        new_val = 0

                # 날짜 처리
                if orm_key in ["updatedate"]:
                    if new_val and not isinstance(new_val, datetime):
                        try:
                            new_val = safe_parse_datetime(new_val)
                        except Exception:
                            new_val = dt
                    if not is_new and old_val is not None and new_val is not None:
                        if old_val.replace(tzinfo=None).date() == new_val.replace(tzinfo=None).date():
                            continue  # 날짜 같으면 skip

                if is_new or old_val != new_val:
                    payload[orm_key] = new_val
                    if not is_new:
                        if orm_key == "info":
                            before_clean = clean_text(old_val)
                            after_clean = clean_text(new_val)
                            if before_clean != after_clean:
                                changes[orm_key] = {"before": before_clean, "after": after_clean}
                        else:
                            if str(old_val) != str(new_val):
                                changes[orm_key] = {"before": str(old_val), "after": str(new_val)}

            # view 데이터 처리
            view_data = novel.get('view')
            new_views = extract_view_count(view_data)
            old_views = 0 if is_new else getattr(db_novel, 'views', 0)
            if is_new or new_views != old_views:
                payload['views'] = new_views
                if not is_new:
                    changes['views'] = {"before": str(old_views), "after": str(new_views)}

            # finishstatus 처리 (새로운 소설이면 False, 아니면 기존값 유지)
            if is_new:
                payload['finishstatus'] = False
            else:
                payload['finishstatus'] = getattr(db_novel, 'finishstatus', False)

            # tags 처리 (현재 JSON에는 tags 필드가 없으므로 빈 문자열로 설정)
            if is_new:
                payload['tags'] = ''
            else:
                payload['tags'] = getattr(db_novel, 'tags', '')

            if is_new:
                payload.setdefault('crawltime', dt)
                insert_data.append(payload)
            elif changes:
                payload['crawltime'] = dt
                for col in NaverSeries.__table__.columns:
                    if col.key not in payload:
                        payload[col.key] = getattr(db_novel, col.key)
                if payload.get('author') is None:
                    payload['author'] = 'Unknown'
                if payload.get('title') is None:
                    payload['title'] = 'Unknown Title'
                if payload.get('platform') is None:
                    payload['platform'] = 'NaverSeries'
                update_data.append(payload)
                update_log.append({"ID": n_id, "Changes": changes})
                
        print(f"신규 {len(insert_data)}건, 업데이트 {len(update_data)}건")
        unique_update_data = {}
        for row in update_data:
            unique_update_data[row['id']] = row
        update_data = list(unique_update_data.values())
        print(f"중복 제거 후 업데이트 {len(update_data)}건")

        try:
            if insert_data:
                print(f"신규 데이터 삽입 시작... ({len(insert_data)}건)")
                for i, batch in enumerate(chunked(insert_data, BATCH_SIZE)):
                    session.bulk_insert_mappings(NaverSeries, batch)
                    print(f"신규 데이터 배치 {i+1} 완료 ({len(batch)}건)")

            if update_data:
                print(f"임시 테이블을 사용한 copy 시작... ({len(update_data)}건)")

                #임시 테이블 생성
                temp_table_name = f"temp_naver_series_{int(time.time())}"
                create_temp_table_sql = f"""
                CREATE TEMP TABLE {temp_table_name} (
                    id BIGINT PRIMARY KEY,
                    series_id TEXT,
                    platform TEXT,
                    title TEXT,
                    info TEXT,
                    author TEXT,
                    location TEXT,
                    thumbnail TEXT,
                    tags TEXT,
                    chapter BIGINT,
                    views BIGINT,
                    newstatus TEXT,
                    finishstatus BOOLEAN,
                    agegrade TEXT,
                    score REAL,
                    content_type TEXT,
                    updatedate TIMESTAMP WITH TIME ZONE,
                    crawltime TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """

                session.execute(text(create_temp_table_sql))
                print(f"임시 테이블 {temp_table_name} 생성 완료")

                # 임시 테이블에 데이터 삽입
                print(f"임시 테이블에 {len(update_data)}건 데이터 삽입 중...")
                
                # CSV 파일 생성 및 COPY 명령으로 임시 테이블에 삽입
                print(f"CSV 파일 생성 및 COPY 명령으로 {len(update_data)}건 삽입 중...")
                with tempfile.NamedTemporaryFile('w+', newline='', encoding='utf-8', suffix='.csv', delete=False) as csvfile:
                    writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
                    
                    # 컬럼 순서 정의
                    columns = ['id', 'series_id', 'platform', 'title', 'info', 'author', 'location', 
                              'thumbnail', 'tags', 'chapter', 'views', 'newstatus', 'finishstatus', 
                              'agegrade', 'score', 'content_type', 'updatedate', 'crawltime']
                    
                    # CSV 헤더 작성
                    writer.writerow(columns)
                    
                    # 데이터 행 작성
                    for row in update_data:
                        csv_row = []
                        for col in columns:
                            value = row.get(col)
                            if value is None:
                                csv_row.append('')
                            elif isinstance(value, datetime):
                                csv_row.append(value.isoformat())
                            elif isinstance(value, bool):
                                csv_row.append('1' if value else '0')
                            else:
                                csv_row.append(str(value))
                        writer.writerow(csv_row)
                    
                    csvfile_path = csvfile.name
                
                # COPY 명령으로 임시 테이블에 데이터 삽입
                copy_sql = f"""
                COPY {temp_table_name} FROM STDIN WITH (FORMAT csv, ENCODING 'UTF8', HEADER);
                """
                
                # psycopg2의 copy_expert를 사용하여 클라이언트 측에서 파일 읽기
                with open(csvfile_path, 'r', encoding='utf-8') as f:
                    raw_conn = session.connection().connection
                    with raw_conn.cursor() as cursor:
                        cursor.copy_expert(copy_sql, f)
                
                print(f"COPY 명령으로 {len(update_data)}건 데이터 삽입 완료")
                
                # 임시 CSV 파일 삭제
                os.unlink(csvfile_path)

                # 실제 테이블 업데이트 UPDATE JOIN 실행
                print("실제 테이블 업데이트 시작... UPDATE JOIN 실행")
                update_join_sql = f"""
                UPDATE naver_series SET
                    series_id = temp.series_id,
                    platform = temp.platform,
                    title = temp.title,
                    info = temp.info,
                    author = temp.author,
                    location = temp.location,
                    thumbnail = temp.thumbnail,
                    tags = temp.tags,
                    chapter = temp.chapter,
                    views = temp.views,
                    newstatus = temp.newstatus,
                    finishstatus = temp.finishstatus,
                    agegrade = temp.agegrade,
                    score = temp.score,
                    content_type = temp.content_type,
                    updatedate = temp.updatedate,
                    crawltime = temp.crawltime
                FROM {temp_table_name} temp
                WHERE naver_series.id = temp.id;
                """

                result = session.execute(text(update_join_sql))
                updated_count = result.rowcount
                print(f"업데이트 완료: {updated_count}건")

            session.commit()
            print("모든 작업이 성공적으로 완료되었습니다.")
        except Exception as e:
            session.rollback()
            print(f"오류 발생: {e}")

        end_time = time.time()
        print(f"총 {end_time - start_time:.2f}초 소요")


    # 로그 기록
    if update_log:
        log_directory = 'DB_Processing_Log'
        if not os.path.exists(log_directory): os.makedirs(log_directory)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_file_path = os.path.join(log_directory, f'{timestamp}-naver-series-copy-update-log.json')
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(update_log, f, ensure_ascii=False, indent=4, default=default_serializer)
        print(f"변경로그 저장: {log_file_path}")
    else:
        print("업데이트 로그가 없습니다.")


if __name__ == "__main__":
    print("데이터베이스 연결 및 기본 쿼리 테스트:")
    main_queries()
    print("-" * 40)

    store_db_naver_series_pg_copy()
