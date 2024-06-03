import typing as T
from datetime import datetime
import json
from pathlib import Path

import scrapy
from scrapy import Request

from forum_ykt.spiders import WEB_ARCHIVE_DOMAIN
from forum_ykt.items import WebArchiveMetaItem, Snapshot
from forum_ykt.pipelines import RuDatePipeline
from forum_ykt.utils import (
    safe_strip,
    safe_int,
    extract_query,
    convert_snapshot_timestamp,
    convert_customary_to_datetime,
    extract_webarchive_date,
)


# FORUMS_META_FILENAME = "./res/webarchive-forums-meta.json"
FORUMS_META_FILENAME = "./res/webarchive-forums-meta-by_forum_style_date-4.json"


class AuthorMeta(T.TypedDict):
    name: str


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


class PaginationParseResult(T.TypedDict):
    style: str
    result: T.Optional[T.Any]


class PaginationParser:
    """Parses pagination of different forum styles"""

    def __init__(self, logger=None) -> None:
        self.parse_latest = self.parse_2021
        if logger:
            self.log = logger

    def log(self, *args, **kwargs):
        pass
    
    @staticmethod
    def escape_result(
        response: scrapy.http.Response, next_page: T.Optional[str]
    ) -> T.Optional[str]:
        return next_page and response.urljoin(next_page) or None

    def parse_2021(self, response: scrapy.http.Response) -> PaginationParseResult:
        pager = response.css("div#paging ul")
        next_page = pager.css("li.yui-pagination_page--active + li a::attr(href)").get()
        
        return {"style": "2021", "result": self.escape_result(response, next_page)}

    def parse_2014(self, response: scrapy.http.Response) -> PaginationParseResult:
        pager = response.css("div#paging")
        next_page = pager.css("b + a::attr(href)").get()

        return {"style": "2014", "result": self.escape_result(response, next_page)}

    def parse(self, response: scrapy.http.Response) -> T.Optional[PaginationParseResult]:
        """Parse with styles from newest to oldest and return on first sucess"""
        for parse_func in (self.parse_2021, self.parse_2014):
            parse_result = parse_func(response)
            if parse_result["result"]:
                return parse_result
        
        return None


class TopicsSpider(scrapy.Spider):
    name = "topics"
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "LOG_FILE": "./topics-1.log",
        "LOG_STDOUT": True,
        "LOG_ENABLED": True,
        # "LOG_LEVEL": "DEBUG",
        # "LOG_FORMATTER": QuietLogFormatter,
        "HTTPCACHE_ENABLED": True,
    }
    custom_feed = {
        "./res/pages/webarchive-forums-content-13.json": {
            "format": "json",
            "indent": 4,
        }
    }
    # MAX_PAGES = 23

    @classmethod
    def update_settings(cls, settings):
        
        super().update_settings(settings)
        settings.setdefault("FEEDS", {}).update(cls.custom_feed)

    @staticmethod
    def get_forum_data() -> T.List[WebArchiveMetaItem]:
        with open(FORUMS_META_FILENAME, "r", encoding="utf-8") as f:
            forums_meta: T.List[WebArchiveMetaItem] = json.load(f)
        
        return forums_meta

    @staticmethod
    def get_test_forum_data() -> T.List[WebArchiveMetaItem]:
        return [
            {
                "url": "https://forum.ykt.ru/viewforum.jsp?id=149&page=9",
                "archived_snapshots": {
                    "closest": {
                        "status": "200",
                        "available": True,
                        "url": "http://web.archive.org/web/20211028024613/https://forum.ykt.ru/viewforum.jsp?id=149&page=9",
                        "timestamp": "20211028024613"
                    }
                },
                "timestamp": "20211031",
                "forum_name": "Сахалыы",
                "forum_id": 149
            }
        ]

    @staticmethod
    def add_pref_to_keys(d: T.Dict[str, T.Any], keys: T.Optional[T.Iterable[str]]=None, pref: str="orig"):
        if keys is None:
            keys = list(d)

        for key in keys:
            orig_val = d.pop(key)
            d[f"{pref}_{key}"] = orig_val

        return d

    def start_requests(self):
        forums_meta = self.get_forum_data()
        self.pagination_parser = PaginationParser(logger=self.log)
        
        for meta in forums_meta:
            if not meta["available"]:
                continue

            self.add_pref_to_keys(meta, ["url", "timestamp"])
            self.log(meta)

            # snapshots: T.Dict[str, Snapshot] = meta.pop("archived_snapshots")
            # if len(snapshots) > 1:
            #     self.log(f"multiple snapshots for {meta['forum_name'] (meta['orig_url'])}")

            # closest_snapshot = snapshots["closest"]
            # meta.update(closest_snapshot)

            # self.log(meta)
            
            if not hasattr(self, "forum2pages"):
                self.forum2pages = {}
            self.forum2pages[meta["forum_name"]] = 0

            yield Request(meta["orig_url"], callback=self.parse, cb_kwargs=meta)


    def get_real_info(
        self, response: scrapy.http.Response
    ) -> T.Dict[str, str]:
        real_url = response.url
        return {
            "real_url": real_url,
            "real_timestamp": extract_webarchive_date(real_url),
        }

    @staticmethod
    def get_title(topic: scrapy.Selector):
        title_div: scrapy.Selector = topic.css("div.f-topic_title")
        if title_div:
            title: str = title_div.css("a::text").get()
            full_url: str = title_div.css("a").attrib["href"]
        else:
            title_a: scrapy.Selector = topic.css("a.f-topic_title")
            title: str = title_a.css(":scope::text").get()
            full_url: str = title_a.attrib["href"]
        
        no_prefix = full_url.removeprefix("/web/")
        snapshot_timestamp, orig_url = no_prefix.split("/", maxsplit=1)
        # snapshot_time = convert_snapshot_timestamp(snapshot_timestamp)
        # self.log(f"{no_prefix}, {snapshot_timestamp}, {orig_url}, {snapshot_time}")

        title = safe_strip(title)
        return title, full_url, orig_url

    @staticmethod
    def get_author(topic: scrapy.Selector) -> str:
        author = safe_strip(topic.css("div.f-topic_author::text").get())
        if not author:
            author = safe_strip(topic.css("div.f-topic_author .f-topic_author_name::text").get())
        return author

    @staticmethod
    def get_num_messages_last_update(topic: scrapy.Selector) -> int:
        num_messages = safe_strip(topic.css("div.f-topic_replies::text").get())
        if not num_messages:
            num_messages = topic.css("f-topic_footer_comments::text").get()
        
        last_update_timestamp = safe_strip(topic.css("div.f-topic_update span::text").get())
        if not last_update_timestamp:
            last_update_timestamp = topic.css("f-topic_footer_update::text").get()

        return (
            # TODO: do we cover above all the cases where number of replies could occur
            #  (and 0 is correct), or is something missed (and 0 is wrong sometimes)?
            safe_int(safe_strip(num_messages)) or 0, 
            safe_strip(last_update_timestamp)
        )

    def parse(
        self, response: scrapy.http.Response, **meta
    ) -> T.Generator[TopicMetaFull, None, None]:
        for topic in response.css("div.f-topics div.f-topic"):
            real_meta = self.get_real_info(response)
            meta.update(real_meta)

            title, full_url, orig_url = self.get_title(topic)

            num_messages, last_update_timestamp = self.get_num_messages_last_update(topic)
            if last_update_timestamp:
                # last_update = RuDatePipeline.parse_date(last_update_timestamp)
                last_update = convert_customary_to_datetime(last_update_timestamp, real_meta["real_timestamp"])
            else:
                last_update = None

            # if "page" not in meta:
            #     meta["page"] = 1
            #     self.forum2pages[meta["forum_name"]] = 1

            res = {
                "topic_title": title,
                "topic_url": f"{WEB_ARCHIVE_DOMAIN}{full_url}",
                "topic_orig_url": orig_url,
                "topic_author": safe_strip(self.get_author(topic)) or None,
                "topic_num_messages": num_messages,
                "topic_last_update": last_update,
                # "forum_snapshot_time": snapshot_time,
                **{(f"forum_{key}" if not key.startswith("forum") else key): val
                   for key, val in meta.items()},
                # **real_meta
            }

            # self.log(res)
            yield res

        # pager = response.css("div#paging ul")
        # next_page = pager.css("li.yui-pagination_page--active + li a::attr(href)").get()
        # self.log(f"next page is: ({type(next_page)}) {next_page}")
        # next_page_url = response.urljoin(next_page)
        # next_page: PaginationParseResult = self.pagination_parser.parse(response)
        # next_page_url = next_page["result"]
        # self.log(f"next page is: ({type(next_page_url)}) {next_page_url}")
        
        # if next_page_url:# and self.forum2pages[meta["forum_name"]] < self.MAX_PAGES:
        #     page_i = safe_int(extract_query(next_page_url)["page"][0])
        #     meta["forum_page"] = page_i
        #     meta["forum_page_url"] = next_page_url

        #     self.forum2pages[meta["forum_name"]] += 1
        #     yield response.follow(next_page_url, callback=self.parse, cb_kwargs=meta)
