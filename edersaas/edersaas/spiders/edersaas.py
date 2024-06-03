import typing as T
from datetime import datetime
from urllib.parse import urlencode, parse_qs

import scrapy
from scrapy import Request, FormRequest


PHP_ENDPOINT = "https://edersaas.ru/wp-admin/admin-ajax.php"
# PHP_ENDPOINT = "https://httpbin.org/anything"

HEADERS = {
    "Accept": '*/*',
    "Accept-Encoding": 'gzip, deflate, br, zstd',
    "Accept-Language": 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
    "Connection": 'keep-alive',
    "Content-Length": '3291',
    "Content-Type": 'application/x-www-form-urlencoded; charset=UTF-8',
    "Cookie": '_ym_uid=1715341038638499179; _ym_d=1715341038; _ym_isad=2; pvc_visits[0]=1715427437b166; _gid=GA1.2.1614096029.1715341039; _ym_visorc=w; _ga=GA1.2.895726647.1715341038; _ga_T42JKWV0PR=GS1.1.1715341038.1.1.1715341520.0.0.0; _ga_T42GT1J829=GS1.1.1715341038.1.1.1715341520.0.0.0',
    "Host": 'edersaas.ru',
    "Origin": 'https://edersaas.ru',
    "Referer": 'https://edersaas.ru/category/uopsastuba/',
    "Sec-Fetch-Dest": 'empty',
    "Sec-Fetch-Mode": 'cors',
    "Sec-Fetch-Site": 'same-origin',
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
    "X-Requested-With": 'XMLHttpRequest',
    "sec-ch-ua": '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": '?0',
    "sec-ch-ua-platform": "Windows",
}

HEADERS_2 = {
    'User-Agent': 'python-requests/2.31.0', 
    'Accept-Encoding': 'gzip, deflate', 
    'Accept': '*/*', 
    'Connection': 'keep-alive', 
    'Content-Length': '3192', 
    'Content-Type': 'application/x-www-form-urlencoded',
}

BASE_DATA = dict(
    action = "dmimagloadmore",
    page = "0",
    query = 'a:66:{s:5:"error";s:0:"";s:1:"m";s:0:"";s:1:"p";i:0;s:11:"post_parent";s:0:"";s:7:"subpost";s:0:"";s:10:"subpost_id";s:0:"";s:10:"attachment";s:0:"";s:13:"attachment_id";i:0;s:4:"name";s:0:"";s:8:"pagename";s:0:"";s:7:"page_id";i:0;s:6:"second";s:0:"";s:6:"minute";s:0:"";s:4:"hour";s:0:"";s:3:"day";i:0;s:8:"monthnum";i:0;s:4:"year";i:0;s:1:"w";i:0;s:3:"tag";s:0:"";s:3:"cat";i:2;s:6:"tag_id";s:0:"";s:6:"author";s:0:"";s:11:"author_name";s:0:"";s:4:"feed";s:0:"";s:2:"tb";s:0:"";s:5:"paged";i:0;s:8:"meta_key";s:0:"";s:10:"meta_value";s:0:"";s:7:"preview";s:0:"";s:1:"s";s:0:"";s:8:"sentence";s:0:"";s:5:"title";s:0:"";s:6:"fields";s:0:"";s:10:"menu_order";s:0:"";s:5:"embed";s:0:"";s:12:"category__in";a:0:{}s:16:"category__not_in";a:0:{}s:13:"category__and";a:0:{}s:8:"post__in";a:0:{}s:12:"post__not_in";a:0:{}s:13:"post_name__in";a:0:{}s:7:"tag__in";a:0:{}s:11:"tag__not_in";a:0:{}s:8:"tag__and";a:0:{}s:12:"tag_slug__in";a:0:{}s:13:"tag_slug__and";a:0:{}s:15:"post_parent__in";a:0:{}s:19:"post_parent__not_in";a:0:{}s:10:"author__in";a:0:{}s:14:"author__not_in";a:0:{}s:14:"search_columns";a:0:{}s:19:"ignore_sticky_posts";b:0;s:16:"suppress_filters";b:0;s:13:"cache_results";b:1;s:22:"update_post_term_cache";b:1;s:22:"update_menu_item_cache";b:0;s:19:"lazy_load_term_meta";b:1;s:22:"update_post_meta_cache";b:1;s:9:"post_type";s:0:"";s:14:"posts_per_page";i:10;s:8:"nopaging";b:0;s:17:"comments_per_page";s:2:"50";s:13:"no_found_rows";b:0;s:5:"order";s:4:"DESC";}',
    instance = 'a:10:{s:10:"card_style";s:32:"dmi-card-incolumn+dmi-grid-col-6";s:13:"display_image";s:1:"1";s:14:"position_image";s:3:"top";s:11:"image_style";s:13:"dmi-image-top";s:10:"image_size";s:1:"4";s:12:"display_date";s:0:"";s:9:"title_tag";s:2:"h4";s:15:"display_excerpt";s:0:"";s:16:"display_taxonomy";s:1:"1";s:7:"post_id";i:199051;}',
)



class EdersaasSpider(scrapy.Spider):
    name = "edersaas"
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        # "LOG_FORMATTER": QuietLogFormatter,
        "HTTPCACHE_ENABLED": True,
    }
    custom_feed = {
        "./res/edersaas-01.json": {
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
    def inc_page(page: str) -> int:
        return int(page) + 1

    def start_requests(self):
        data = BASE_DATA
        if hasattr(self, "from_page"):
            page = self.from_page
            data["page"] = page

        req = FormRequest(
            PHP_ENDPOINT, formdata=data, #method="POST", #headers=HEADERS_2,
            callback=self.parse,
            cb_kwargs=data
        )

        yield req

    @staticmethod
    def process_paragraphs(paragraphs: T.Iterable[scrapy.Selector], joiner: str="") -> T.List[str]:
        """Joins text children of a <p> tag, possibly produced by tags like <b>, <strong>, <a>, etc."""
        processed_pars = []
        for par in paragraphs:
            par_elements = par.css(":scope::text, *::text").getall()
            joined_par = joiner.join(par_elements)
            if joined_par:
                processed_pars.append(joined_par)
        
        return processed_pars

    @staticmethod
    def extract_name_from_author_info(author_info: scrapy.Selector):
        return (author_info.css(":scope::text").get() or "").strip().removeprefix("Ааптар:").strip()

    def parse_page(self, response: scrapy.http.Response, **meta):
        article: scrapy.Selector = response.css("article")[0]
        
        article_id = int(article.attrib["id"].split("-")[1])

        published_time = response.xpath('/html/head/meta[@property="article:published_time"]/@content').get()
        self.log(published_time)
        article_published_time = datetime.fromisoformat(published_time)
        modified_time = response.xpath('/html/head/meta[@property="article:modified_time"]/@content').get()
        self.log(modified_time)
        article_modified_time = datetime.fromisoformat(modified_time) if modified_time else None

        author_info = article.css(".dmi-news-author")

        author_name = author_info.css("a::text").get()
        author_link = author_info.css("a").attrib["href"] if author_name else None
        if not author_name:
            author_name = self.extract_name_from_author_info(author_info)

        paragraphs = self.process_paragraphs(article.css(".dmi-news-content p"))
        
        meta.update(dict(
            id = article_id,
            author_name = author_name,
            author_link = author_link,
            article_published = article_published_time,
            article_modified = article_modified_time,
            text = paragraphs,
        ))
        return meta


    def parse(
        self, response: scrapy.http.Response, **meta
    ) -> T.Generator[T.Dict[str, T.Any], None, None]:
        self.log(f'scraping page: {meta["page"]}')

        if not response.body:
            return
        
        article_cards: T.Iterable[scrapy.Selector] = response.css(".dmi-card")
        for card in article_cards:
            categories = card.css(".dmi-card-category *::text").getall()
            categories = [cat for cat in categories if cat.strip()]
            # self.log(categories)

            url = card.css(".dmi-card-title a").attrib["href"]
            title = card.css(".dmi-card-title a::text").get()

            article_data = dict(title=title, url=url, categories=categories)
            self.log(article_data)
            yield Request(url, callback=self.parse_page, cb_kwargs=article_data)

        meta["page"] = str(self.inc_page(meta['page']))
        yield FormRequest(
            PHP_ENDPOINT, formdata=meta,
            callback=self.parse,
            cb_kwargs=meta
        )