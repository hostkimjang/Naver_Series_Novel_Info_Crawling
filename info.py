class NovelInfo:
    def __init__(self, platform, title, info, author, agegrade, score, new_status, content_type, locate, thumbnail):
        self.platform = platform
        self.title = title
        self.info = info
        self.author = author
        self.agegrade = agegrade
        self.score = score
        self.new_status = new_status
        self.content_type = content_type
        self.locate = locate
        self.thumbnail = thumbnail

    def __str__(self, *args, **kwargs):
        return (f"platform: {self.platform}\n"
                f"title: {self.title}\n"
                f"info: {self.info}\n"
                f"author: {self.author}\n"
                f"agegrade: {self.agegrade}\n"
                f"score: {self.score}\n"
                f"new_status: {self.new_status}\n"
                f"content_type: {self.content_type}\n"
                f"locate: {self.locate}\n"
                f"thumbnail: {self.thumbnail}\n")

    def to_dict(self):
        return {
            "platform": self.platform,
            "title": self.title,
            "info": self.info,
            "author": self.author,
            "agegrade": self.agegrade,
            "score": self.score,
            "new_status": self.new_status,
            "content_type": self.content_type,
            "locate": self.locate,
            "thumbnail": self.thumbnail
        }




def set_novel_info(platform, title, info, author, agegrade, score, new_status, content_type, locate, thumbnail):
    print("-" * 100)
    print(f"platform: {platform}")
    print(f"title: {title}")
    print(f"info: {info}")
    print(f"author: {author}")
    print(f"grade: {agegrade}")
    print(f"score: {score}")
    print(f"new_status: {new_status}")
    print(f"content_type: {content_type}")
    print(f"thumbnail: {thumbnail}")
    print(f"locate: {locate}")
    print("-" * 100)
    return NovelInfo(platform, title, info, author, agegrade, score, new_status, content_type, locate, thumbnail)