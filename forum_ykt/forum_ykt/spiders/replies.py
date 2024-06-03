import typing as T
from datetime import datetime
from itertools import islice
import json
from pathlib import Path
import re

import scrapy
from scrapy import Request
from scrapy.http import Response
import scrapy.http
import scrapy.logformatter

from forum_ykt.spiders import WEB_ARCHIVE_DOMAIN
from forum_ykt.items import (
    WebArchiveMetaItem,
    Snapshot,
    TopicHead,
    Reply,
    TopicItem
)
from forum_ykt.pipelines import RuDatePipeline
from forum_ykt.utils import (
    safe_strip,
    safe_int,
    DEFAULT_ID,
    extract_query,
    convert_snapshot_timestamp,
    convert_head_timestamp,
    convert_customary_to_datetime,
    extract_webarchive_date,
    tqdm
)
from forum_ykt.spiders.topics import (
    AuthorMeta,
    TopicMetaFull,
)


# class TopicHead(T.TypedDict):
#     id: int
#     head_id: int
#     parent_id: None
    
#     is_head: bool
#     by_owner: bool

#     date: datetime
#     rating: int
    
#     author: AuthorMeta
#     author_ip: str

#     text: T.List[str]  # paragraph list


# class Reply(T.TypedDict):
#     id: int
#     head_id: int
#     parent_id: T.Optional[int]
    
#     is_head: bool
#     by_owner: T.Optional[bool]

#     date: datetime
#     rating: int
    
#     author: AuthorMeta

#     title: T.List[str]
#     text: T.List[str]  # paragraph list

# TopicItem = T.Union[TopicHead, Reply]


TOPICS_META_FILENAME = "./res/pages/webarchive-forums-content-13.json"


class QuietLogFormatter(scrapy.logformatter.LogFormatter):
    def scraped(self, item: scrapy.Item, response: scrapy.http.Response, spider: scrapy.Spider):
        return (
            super().scraped(item, response, spider)
            if spider.settings.getbool("LOG_SCRAPED_ITEMS")
            else None
        )

class RepliesSpider(scrapy.Spider):
    name = "replies"
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "LOG_FILE": "./replies-1.log",
        "LOG_ENABLED": True,
        "LOG_FORMATTER": QuietLogFormatter,
        "HTTPCACHE_ENABLED": True,
    }
    custom_feed = {
        "./res/pages/webarchive-replies-content-5.json": {
            "format": "json",
            "indent": 4,
        }
    }

    default_id = DEFAULT_ID
    default_rating = 0

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.setdefault("FEEDS", {}).update(cls.custom_feed)

    # @classmethod
    # def from_state(cls, state):
    #     TODO
    
    @staticmethod
    def get_topics_data() -> T.List[TopicMetaFull]:
        with open(TOPICS_META_FILENAME, "r", encoding="utf-8") as f:
            topics_meta: T.List[TopicMetaFull] = json.load(f)
        
        return topics_meta[1:]
    
    def filter_topics(self, topics: T.Iterable[TopicMetaFull]) -> T.Generator[TopicMetaFull, None, None]:
        topics_i_from = getattr(self, "topics_i_from", None)
        topics_i_to = getattr(self, "topics_i_to", None)
        topics_iter = islice(topics, topics_i_from, topics_i_to)

        topics_url_pattern = getattr(self, "topics_url_pattern", None)
        if topics_url_pattern:
            pattern = re.compile(topics_url_pattern)
            for topic_meta in topics_iter:
                if pattern.match(topic_meta["url"]):
                    yield topic_meta
        else:
            yield from topics_iter

    def start_requests(self):
        base_topics_meta = self.get_topics_data()

        topics_meta = list(self.filter_topics(base_topics_meta))

        # print(topics_meta)

        for meta in tqdm(topics_meta):
            topic_url = meta["topic_url"]
            self.log((meta["topic_title"], topic_url))

            yield Request(topic_url, callback=self.parse, cb_kwargs=meta)

    # def compute_date(self, date_str):
    #     if 

    def parse_head_date(
        self, response: scrapy.http.Response, head_div: scrapy.Selector
    ) -> T.Union[datetime, str]:                
        date_timestamp = head_div.css(".f-view_createdate::text").get()

        today = extract_webarchive_date(response.url)
        date = convert_customary_to_datetime(date_timestamp, today)

        return date
    

    def parse_head_date(
        self, response: scrapy.http.Response, head_div: scrapy.Selector
    ) -> T.Union[datetime, str]:        
        time_el = head_div.css("time")
        if time_el:
            date = convert_head_timestamp(time_el.attrib["datetime"])
            return date


        date_timestamp = head_div.css(".f-view_createdate::text").get()

        today = extract_webarchive_date(response.url)
        date = convert_customary_to_datetime(date_timestamp, today)

        return date
    

    def parse_reply_date(
        self,  reply_div: scrapy.Selector
    ) -> T.Optional[T.Union[datetime, str]]:
        return datetime.fromtimestamp(safe_int(reply_div.attrib["data-date"]) / 1000)

    @staticmethod
    def parse_ip(content: scrapy.Selector):
        for css in (".f-comment_ip", ".f-user_ip"):
            maybe_ip_el = content.css(css)
            if maybe_ip_el and "data-title" in maybe_ip_el.attrib:
                return maybe_ip_el.attrib["data-title"]

    def parse_head(self, response: scrapy.http.Response) -> TopicHead:
        head_div = response.css("div.f-view")

        rating_div = head_div.css(".f-view_like")
        reply_id = safe_int(rating_div.attrib["data-id"]) or self.default_id
        rating = safe_int(safe_strip(rating_div.css(".f-comment_like_count::text").get())) or self.default_rating
        
        author_name = safe_strip(head_div.css(".topic-view__author::text").get())
        author_ip = head_div.css(".f-user_ip").attrib["data-title"]

        date = self.parse_head_date(response, head_div)

        self.log(f"topic owner ip: {author_ip}")

        text = head_div.css(".f-view_topic-text::text").getall()
        
        topic_head: TopicHead = {
            "id": reply_id,
            "head_id": reply_id,
            "parent_id": None,

            "is_head": True,
            "by_owner": True,

            "date": date,
            "rating": rating,
            "author_name": author_name,
            "author_ip": author_ip,
            "text": text,
        }

        self.log(topic_head)
        
        return topic_head

    @staticmethod
    def make_by_owner_checker(topic_starter_ip: str) -> T.Callable[[str], bool]:
        def is_by_owner(author_ip: str) -> bool:
            return author_ip == topic_starter_ip

        return is_by_owner
    
    def parse_reply(
        self, reply_li: scrapy.Selector, head_id: int, parent_id: T.Optional[int]=None,
        is_by_owner_checker: T.Optional[T.Callable[[str], bool]]=None
    ) -> T.List[Reply]:
        results: T.List[Reply] = []

        reply_id = safe_int(reply_li.attrib["id"].strip("comment-")) or self.default_id

        reply_div = reply_li.css(".f-comment")

        content = reply_li.css(".f-comment_content")[0]
        title = content.css(".f-comment_topic > *::text").getall()
        if len(title) > 1:
            self.logger.info(f"more than 1 string in title for reply: {reply_id}")

        text = content.css("p::text").getall()
        rating = safe_int(safe_strip(content.css(".f-comment_like_count::text").get())) or self.default_rating

        # self.log(text)
        # date = content.css(".f-comment_header_createdate::text")
        date = self.parse_reply_date(reply_div)
        author_name = safe_strip(content.css(".f-user_name::text").get())

        author_ip = self.parse_ip(content)
        # self.log(f"author ip: {author_ip}")
        by_owner = is_by_owner_checker(author_ip) if is_by_owner_checker else None

        reply: Reply = {
            "id": reply_id,
            "head_id": head_id,
            "parent_id": parent_id,

            "is_head": False,
            "by_owner": by_owner,

            "date": date,
            "rating": rating,
            "author_name": author_name,
            "title": title,
            "text": text,
        }

        # self.log(f"parent: `{parent_id}`, current: `{reply_id}`")
        # self.log(reply)

        results.append(reply)

        # further_replies_lists_list = reply_li.css(".f-comments_list")
        further_replies_list = reply_li.xpath("./ul/li")
        # if further_replies_lists_list:
        # self.log(f"further_replies: {further_replies_list}")
        if further_replies_list:
            # further_replies_list = further_replies_lists_list[0]
            # for further_reply in further_replies_list.xpath("/li"):
            for further_reply in further_replies_list:
                res = self.parse_reply(
                    further_reply, head_id, parent_id=reply_id,
                    is_by_owner_checker=is_by_owner_checker
                )
                results.extend(res)

        return results

    def parse(self, response: Response, **meta: T.Any) -> T.Any:
        topic_head = self.parse_head(response)
        head_id = topic_head["id"]
        topic_starter_ip = topic_head.pop("author_ip")
        is_by_owner_checker = self.make_by_owner_checker(topic_starter_ip)

        top_container = response.css("div.f-comments_content")
        top_level_replies_list = top_container.css("ul.topic-comments__items:first-child > li")
        # self.log(f"top-level replies: {len(top_level_replies_list)}")

        all_replies: T.List[TopicItem] = [topic_head]
        for top_level_reply in tqdm(top_level_replies_list):
            branched_replies = self.parse_reply(
                top_level_reply, head_id, is_by_owner_checker=is_by_owner_checker
            )
            # self.log(f"`{len(branched_replies)}` from `{branched_replies[0]}`")
            all_replies.extend(branched_replies)

        meta["replies"] = all_replies
        self.log(f"total replies (1 + len(replies)): {len(all_replies)}")
        yield meta