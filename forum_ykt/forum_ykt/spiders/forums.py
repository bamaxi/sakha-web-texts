import typing as T
from datetime import datetime, timedelta
import json
from itertools import product
from pathlib import Path

import scrapy
import scrapy.crawler
from scrapy.spiders import CrawlSpider
from scrapy import signals

from forum_ykt.items import WebArchiveMetaItem
from forum_ykt.utils import (
    to_webarchive_date,
    convert_snapshot_timestamp,
    encode_url,
)

LATEST_DATE = datetime(2021, 10, 31)
MIN_DATE = datetime(2010, 1, 1)

YEAR_DAYS = 365
SNAPSHOTS_PER_YEAR = 12
DATE_DELTA = timedelta(days=YEAR_DAYS // SNAPSHOTS_PER_YEAR)

latest_date_str = LATEST_DATE.strftime("%Y%m%d")

ARCHIVE_LINK = "http://archive.org/wayback/available?"

FORUM_LINK_PATTERN = FORUM_LINK_PATTERN_2021 = "https://forum.ykt.ru/viewforum.jsp?id={}"
FORUM_LINK_PATTERN_2015 = "https://forum.ykt.ru/mviewforum.jsp?id={}"
FORUM_LINK_PATTERNS = {
    "2021_viewforum": FORUM_LINK_PATTERN_2021,
    "2015_mviewforum": FORUM_LINK_PATTERN_2015,
}

FORUM2ID = {
    "Сахалыы":              149,

    "Ас-үөл":               161,
    "Биир дойдулаахтарым":  150,
    "Билсиhии":             158,
    "Булт-алт":             155,
    "Дьоhун саас":          298,
    "Көрдүүбүн":            152,
    "Кыыс Куо":             160,
    "Кэпсээ":               26,
    "Кэпсээннэр":           154,
    "Санаалар":             27,
    "Саха тыла":            204,
    "Сиэр-туом":            148,
    "Төрөппүттэр":          151,
    "Чэгиэн":               157,
    "Ыччат түhүлгэтэ":      153,
    "Эн&Мин":               156,
}
FORUM2LINK = {forum: FORUM_LINK_PATTERN.format(_id)
              for forum, _id in FORUM2ID.items()}

PAGE_FROM = 1
PAGE_TO = 500
PAGES_RANGE = range(PAGE_FROM, PAGE_TO)



class ForumMeta(T.TypedDict):
    forum_name: str
    forum_style: str
    forum_id: int
    page: int
    query_date: datetime
    orig_url: str

class Source(T.TypedDict):
    orig_url: str
    meta: ForumMeta


DictKeysWithTuple = T.Union[str, int, bool, T.Tuple[str]]
ForumStylePageAtTime = T.Tuple[int, str, int, datetime]


def json_dumps_tuple_keys(mapping: T.Dict[DictKeysWithTuple, T.Any]):
    # https://stackoverflow.com/a/69550057
    string_keys = {json.dumps(k): v for k, v in mapping.items()}
    return json.dumps(string_keys, default=str)

def json_loads_tuple_keys(string: str) -> T.Dict[DictKeysWithTuple, T.Any]:
    # https://stackoverflow.com/a/69550057
    mapping = json.loads(string)
    return {tuple(json.loads(k)): v for k, v in mapping.items()}


class ForumsSpider(scrapy.Spider):
    name = "forums"
    custom_settings = {
        "DOWNLOAD_DELAY": 2
    }
    custom_feed = {
        f"./res/webarchive-forums-meta-by_forum_style_date-4.json": {
            "format": "json",
            "indent": 4,
        }
    }
    out_forum_page_time2snapshot_times = "./res/_forum_page_time2snapshots.json"

    # handle_http_status_list = [404]

    @classmethod
    def from_crawler(cls, crawler: scrapy.crawler.Crawler, *args, **kwargs):
        spider = super(ForumsSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.engine_stopped, signal=signals.engine_stopped)
        return spider

    @staticmethod
    def sort_dict(d: T.Dict):
        return {key: val for key, val in sorted(d.items(), key=lambda k_v: (k_v[0][1], k_v[0][2]))}

    def engine_stopped(self):
        json_s = json_dumps_tuple_keys(self.sort_dict(self.forum_page_time2snapshot_times))
        with open(self.out_forum_page_time2snapshot_times, "w", encoding="utf-8") as f:
            f.write(json_s)

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.setdefault("FEEDS", {}).update(cls.custom_feed)

    def generate_dates(self) -> T.Generator[datetime, None, None]:
        date = LATEST_DATE
        while date > MIN_DATE:
            yield date
            
            date -= DATE_DELTA

    def make_links(self) -> T.Generator[Source, None, None]:
        for date in self.generate_dates():
            for forum_name, forum_id in FORUM2ID.items():
                for forum_link_pattern_name, forum_link_pattern in FORUM_LINK_PATTERNS.items():
                    for page in PAGES_RANGE:                
                        timestamp = to_webarchive_date(date)
                        forum_link = forum_link_pattern.format(forum_id)

                        forum_page_url = f"{forum_link}&page={page}"
                        encoded_url = encode_url(forum_page_url)

                        url = f"{ARCHIVE_LINK}url={encoded_url}&timestamp={timestamp}"
                        data = {
                            "orig_url": url,
                            "meta": {
                                "forum_name": forum_name,
                                "forum_style": forum_link_pattern_name,
                                "forum_id": forum_id,
                                "page": page,
                                "query_date": date,
                                "orig_url": forum_page_url,
                            }
                        }

                        yield data

    @staticmethod
    def make_key_from_meta(meta: ForumMeta):
        return (meta["forum_id"], meta["forum_style"], meta["page"])


    def start_requests(self) -> T.Iterable[scrapy.Request]:
        # we go from newest to oldest, thus times are naturally sorted from newest to oldest too
        self.forum_page_time2snapshot_times: T.Dict[
            ForumStylePageAtTime, T.List[T.Optional[datetime]]
        ] = {}

        for source in self.make_links():
            meta = source["meta"]
            # self.checked.add()

            key = self.make_key_from_meta(meta)
            times = self.forum_page_time2snapshot_times.get(key)

            self.log(f"key: {key}, snapshots: {times}")

            # setup requires that queries for date be emitted with great interval
            #  (> CONCURRENT_REQUESTS), because links are consumed in batches

            if times and times[-1] is None:
                # previous queried date returned nothing
                #   webarchive will give nothing too
                self.log(f"skipping url with timestamp {meta['query_date']} "
                         f"(previous query of same link returned nothing) "
                         f"(url <{meta['orig_url']}>)")
                continue
            if times and times[-1] <= meta["query_date"]:
                # queried date is newer than last closest snapshot,
                #   webarchive will give the same one.
                #   this optimizes both dates and forum_styles 
                self.log(f"skipping url with timestamp {meta['query_date']} "
                         f"(it is >= last closest snapshot {times[-1]}) "
                         f"(url <{meta['orig_url']}>)")
                continue

            yield scrapy.Request(url=source["orig_url"], callback=self.parse, cb_kwargs=meta)


    # def start_requests(self):
    #     sources: T.List[Source] = []

    #     for forum_name, forum_link in FORUM2LINK.items():
    #         url = f"{ARCHIVE_LINK}url={forum_link}&timestamp={latest_date_str}"
    #         source = {
    #             "url": url,
    #             "meta": {
    #                 "forum_name": forum_name,
    #                 "forum_id": FORUM2ID[forum_name],
    #             }
    #         }
    #         sources.append(source)
        
    #     for source in sources:
    #         yield scrapy.Request(url=source["url"], callback=self.parse, cb_kwargs=source["meta"])

    def parse(
        self, response: scrapy.http.Response, **meta
    )-> T.Generator[WebArchiveMetaItem, None, None]:
        # if response.status == 404:

        # web_archive_res: WebArchiveMetaItem = json.loads(response.body)
        # web_archive_res.update(meta)
        web_archive_res = json.loads(response.body)
        if web_archive_res["archived_snapshots"]:
            snapshot = web_archive_res["archived_snapshots"]["closest"]
            real_date = snapshot["real_date"] = convert_snapshot_timestamp(snapshot["timestamp"])
            meta.update(snapshot)
            
            key = self.make_key_from_meta(meta)
            self.forum_page_time2snapshot_times.setdefault(key, []).append(real_date)
            yield meta
        else:
            key = self.make_key_from_meta(meta)
            self.forum_page_time2snapshot_times.setdefault(key, []).append(None)

            meta["available"] = False
            yield meta
