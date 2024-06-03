import typing as T
from datetime import datetime
import json
from pathlib import Path

import scrapy
from scrapy import Request

from forum_ykt.spiders import WEB_ARCHIVE_DOMAIN
from forum_ykt.items import WebArchiveMetaItem, Snapshot
from forum_ykt.pipelines import RuDatePipeline
from forum_ykt.utils import safe_strip, safe_int


FORUMS_META_FILENAME = "./res/webarchive-forums-meta.json"


class AuthorMeta(T.TypedDict):
    name: str


class TopicMeta(T.TypedDict):
    title: str
    url: str
    author: AuthorMeta
    num_messages: int
    last_update: datetime
    forum_meta: WebArchiveMetaItem


class TopicsSpider(scrapy.Spider):
    # name = "topics"
    custom_settings = {
        "DOWNLOAD_DELAY": 2
    }
    custom_feed = {
        "./res/pages/webarchive-forums-content.json": {
            "format": "json",
            "indent": 4,
        }
    }

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.setdefault("FEEDS", {}).update(cls.custom_feed)

    def start_requests(self):
        with open(FORUMS_META_FILENAME, "r", encoding="utf-8") as f:
            forums_meta: T.List[WebArchiveMetaItem] = json.load(f)
        
        for meta in forums_meta:
            for key in ("url", "timestamp"):
                orig_val = meta.pop(key)
                meta[f"orig_{key}"] = orig_val

            snapshots: T.Dict[str, Snapshot] = meta.pop("archived_snapshots")
            if len(snapshots) > 1:
                self.log(f"multiple snapshots for {meta['forum_name'] (meta['orig_url'])}")

            closest_snapshot = snapshots["closest"]
            meta.update(closest_snapshot)

            self.log(meta)
            
            yield Request(meta["url"], callback=self.parse, cb_kwargs=meta)


    def parse(
        self, response: scrapy.http.Response, **meta
    ) -> T.Generator[TopicMeta, None, None]:
        for topic in response.css("div.f-topics div.f-topic"):
            title_div = topic.css("div.f-topic_title")
            title = title_div.css("a::text").get()
            
            full_url = title_div.css("a").attrib["href"]
            no_prefix = full_url.removeprefix("/web/")
            snapshot_timestamp, orig_url = no_prefix.split("/", maxsplit=1)
            snapshot_time = datetime.strptime(snapshot_timestamp, "%Y%m%d%H%M%S")
            self.log(f"{no_prefix}, {snapshot_timestamp}, {orig_url}, {snapshot_time}")

            last_update_timestamp = safe_strip(topic.css("div.f-topic_update span::text").get())
            # if last_update_timestamp:
            #     last_update = RuDatePipeline.parse_date(last_update_timestamp)
            # else:
            #     last_update = None

            res = {
                "title": title,
                "url": f"{WEB_ARCHIVE_DOMAIN}{full_url}",
                "orig_url": orig_url,
                "author": safe_strip(topic.css("div.f-topic_author::text").get()),
                "num_messages": safe_int(safe_strip(topic.css("div.f-topic_replies::text").get())),
                "last_update": last_update_timestamp,
                # "forum_meta": meta,
                "snapshot_time": snapshot_time,
                **{(f"forum_{key}" if not key.startswith("forum") else key): val
                   for key, val in meta.items()}
            }

            self.log(res)
            yield res

        pager = response.css("div#paging ul")
        next_page = pager.css("li.yui-pagination_page--active + li a::attr(href)")
        
        if next_page:
            yield response.follow(next_page[0], callback=self.parse, cb_kwargs=meta)
        
