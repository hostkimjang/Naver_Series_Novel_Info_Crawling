class NovelInfo:
    def __init__(self, platform, id, series_id, title, info, author, chapter, agegrade, score, new_status, content_type, locate, thumbnail, last_update):
        self.platform = platform
        self.id = id
        self.series_id = series_id
        self.title = title
        self.info = info
        self.author = author
        self.chapter = chapter
        self.agegrade = agegrade
        self.score = score
        self.new_status = new_status
        self.content_type = content_type
        self.locate = locate
        self.thumbnail = thumbnail
        self.last_update = last_update

    def __str__(self, *args, **kwargs):
        return (f"platform: {self.platform}\n"
                f"id: {self.id}\n"
                f"series_id: {self.series_id}\n"
                f"title: {self.title}\n"
                f"info: {self.info}\n"
                f"author: {self.author}\n"
                f"chapter: {self.chapter}\n"
                f"agegrade: {self.agegrade}\n"
                f"score: {self.score}\n"
                f"new_status: {self.new_status}\n"
                f"content_type: {self.content_type}\n"
                f"locate: {self.locate}\n"
                f"thumbnail: {self.thumbnail}\n"
                f"last_update: {self.last_update}\n"
                )


    def to_dict(self):
        return {
            "platform": self.platform,
            "id": self.id,
            "series_id": self.series_id,
            "title": self.title,
            "info": self.info,
            "author": self.author,
            "chapter": self.chapter,
            "agegrade": self.agegrade,
            "score": self.score,
            "new_status": self.new_status,
            "content_type": self.content_type,
            "locate": self.locate,
            "thumbnail": self.thumbnail,
            "last_update": self.last_update
        }




def set_novel_info(platform, id, series_id, title, info, author, chapter, agegrade, score, new_status, content_type, locate, thumbnail, last_update):
    print("-" * 100)
    print(f"platform: {platform}")
    print(f"id: {id}")
    print(f"series_id: {series_id}")
    print(f"title: {title}")
    print(f"info: {info}")
    print(f"author: {author}")
    print(f"chapter: {chapter}")
    print(f"grade: {agegrade}")
    print(f"score: {score}")
    print(f"new_status: {new_status}")
    print(f"content_type: {content_type}")
    print(f"thumbnail: {thumbnail}")
    print(f"last_update: {last_update}")
    print(f"locate: {locate}")
    print("-" * 100)
    return NovelInfo(platform, id, series_id, title, info, author, chapter, agegrade, score, new_status, content_type, locate, thumbnail, last_update)