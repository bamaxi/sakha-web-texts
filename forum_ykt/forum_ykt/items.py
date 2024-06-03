# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
import typing as T
from datetime import datetime

import scrapy


class ForumYktItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class Snapshot(T.TypedDict):
    status: str
    available: bool
    url: str
    timestamp: str


class AuthorMeta(T.TypedDict):
    name: str


class WebArchiveMetaItem(T.TypedDict):
    url: str
    archived_snapshots: T.Dict[str, Snapshot]
    timestamp: str
    forum_name: str
    forum_id: int


class TopicHead(T.TypedDict):
    id: int
    head_id: int
    parent_id: None
    
    is_head: bool
    by_owner: bool

    date: datetime
    rating: int
    
    author: AuthorMeta
    author_ip: str

    text: T.List[str]  # paragraph list


class Reply(T.TypedDict):
    id: int
    head_id: int
    parent_id: T.Optional[int]
    
    is_head: bool
    by_owner: T.Optional[bool]

    date: datetime
    rating: int
    
    author: AuthorMeta

    title: T.List[str]
    text: T.List[str]  # paragraph list


TopicItem = T.Union[TopicHead, Reply]


class TopicMetaFull(T.TypedDict):
    title: str
    url: str
    author: AuthorMeta
    num_messages: int
    last_update: datetime
    forum_meta: WebArchiveMetaItem

    snapshot_time: datetime
    forum_name: str
    forum_id: int
    forum_orig_url: str
    forum_orig_timestamp: str
    forum_status: str
    forum_available: bool
    forum_url: str
    forum_timestamp: str
    forum_page: int
    forum_page_url: str
    real_url: str
    real_timestamp: datetime

    replies: T.Optional[T.List[TopicItem]]


# {
#     "url": "https://forum.ykt.ru/viewforum.jsp?id=149",
#     "archived_snapshots": {
#         "closest": {
#             "status": "200",
#             "available": true,
#             "url": "http://web.archive.org/web/20211028024613/https://forum.ykt.ru/viewforum.jsp?id=149",
#             "timestamp": "20211028024613"
#         }
#     },
#     "timestamp": "20211031",
#     "forum_name": "Сахалыы",
#     "forum_id": 149
# },