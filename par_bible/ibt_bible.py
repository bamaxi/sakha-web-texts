import typing as T
import abc
from datetime import datetime
from functools import wraps
import json
from itertools import chain
from typing import Union, List, Dict, Optional

from requests import Session
import bs4
from bs4 import (
    Tag,
    BeautifulSoup
)

from models import TextItem, TextMeta, AuthorMeta
from utils import random_delay_adder, append_list_part, write_json, HEADERS

try:
    from tqdm.auto import tqdm
except ImportError:
    def tqdm(*args, **kwargs):
        return args[0]

# import logging
# import logging.config

# logging.config.fileConfig('logging_edersaas.conf')
# logger = logging.getLogger(__name__)

JOINER = ""

IBT_TEXTS_LINK = "https://ibt.org.ru/ru/text"
PARSER = "lxml"

MAX_PAGES = 3000

session = Session()
session.headers.update(HEADERS)


def remove_extra_space(s: str):
    return re.sub(r"(\s)\1{2,}+", "")


def is_digits_list(lst: T.List[str]) -> T.TypeGuard[T.List[int]]:
    return all(item.isdigit() for item in lst)


def has_elem_name(elem: bs4.PageElement, name: str) -> bool:
    return getattr(elem, "name", None) == name


def list_values_from_select(
    select: bs4.Tag, conv_int: bool=True
) -> T.List[T.Union[float, int, str]]:
    values = []
    for elem in select.children:
        if isinstance(elem, Tag) and elem.name == "option":
            maybe_value = elem.attrs.get("value")
            if maybe_value:
                values.append(maybe_value)

    if conv_int and is_digits_list(values):
        values = [int(val) for val in values]

    return values


ALIGNABLE_PUNCTS: T.Dict[str, str] = {
    ",": ";",
    ";": ",",
}


def try_punct_align(
    s1: str, s2: str, alignable_puncts: T.Dict[str, str]=ALIGNABLE_PUNCTS
) -> T.Optional[T.List[T.Tuple[str]]]:
    ...


texts_versions = {"m1": "YKT", "m2": "RSP"}

text_titles: T.List[str] = [
    "Matt",
    "Mark",
    "Luke",
    "John",
]

title2desc = {
    "Matt": "Евангелие от Матфея",
    "Mark": "Евангелие от Марка",
    "Luke": "Евангелие от Луки",
    "John": "Евангелие от Иоанна",
}



class BaseText(abc.ABC):
    @abc.abstractmethod
    def to_json(self) -> T.Any: ...


class BibleVerse(BaseText):
    i: int
    text: str
    sentences: T.List[str]

    def __init__(
        self, i: int, text: str,
        splitting_func: T.Optional[T.Callable[[str], T.List[str]]]=None
    ) -> None:
        self.i = i
        self.text = text
        self.splitting_func = splitting_func

        splitting_func = splitting_func or self.parse_text
        res = self.parse_text(text)
        if res:
            self.sentences = res
        else:
            # self.sentences = [text]
            self.sentences = text
        

    @staticmethod
    def parse_text(text: str) -> T.List[str]:
        # return text.split(".")
        return 
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.i}, {self.text}, {self.splitting_func})"
    
    def __str__(self) -> str:
        return str(self.sentences)
    
    def to_json(self) -> T.List[str]:
        return self.sentences


class BibleChapter(BaseText):
    i: int
    verses: T.List[BibleVerse]

    def __init__(self, i: int, verses: T.List[BibleVerse]) -> None:
        self.i = i
        self.verses = verses

    def to_json(self) -> T.Any:
        return [verse.to_json() if not isinstance(verse, (dict, list)) else verse
                for verse in self.verses]


class BibleText(BaseText):
    title: str
    chapters: T.List[BibleChapter]

    def __init__(self, title: str, chapters: T.List[BibleChapter]) -> None:
        self.title = title
        self.chapters = chapters

    def to_json(self) -> T.Any:
        return {"title": self.title,
                "chapters": {ch.i: ch.to_json() for ch in self.chapters}}


@random_delay_adder(0.5, 1.0)
def load_chapter(
    text_title: str, chapter: int=1, text_title_template: str = "{title}.{chapter}",
    return_text_container_only=False
) -> bs4.BeautifulSoup:
    
    final_title = text_title_template.format(title=text_title, chapter=chapter)

    page = session.get(
        IBT_TEXTS_LINK,
        params={**texts_versions, **{"l": final_title}}
    )
    print(page.url)

    soup = BeautifulSoup(page.text, "lxml")
    if return_text_container_only:
        return soup.find("div", id="text")

    return soup


def parse_chapter(
    text_container: bs4.Tag, reduce_empty=True
) -> T.Dict[str, BibleVerse]:
    # sah_verses: T.List[BibleVerse] = []
    # ru_verses: T.List[BibleVerse] = []
    verses = []

    verses_els = text_container.find_all("div", class_="interB")
    for verse_el in verses_els:
        if isinstance(verse_el, dict):
            print(verse_el)

        sah_verse, ru_verse = verse_el.find_all("span", class_="vs")

        verse_num = None
        for verse_tag in (sah_verse, ru_verse):
            verse_num_tag = verse_tag.find("sup")
            verse_num = int(verse_num_tag.string)
            verse_num_tag.extract()

        # `.strings` or `.stripped_strings`?
        sah_text = JOINER.join(sah_verse.strings)
        ru_text = JOINER.join(ru_verse.strings)

        verse_sah = BibleVerse(verse_num, sah_text)
        verse_ru = BibleVerse(verse_num, ru_text)
        # sah_verses.append(verse_sah)
        # ru_verses.append(verse_ru)
        verses.append({"ru": verse_ru.to_json(), "sah": verse_sah.to_json()})

        print(verse_num, sah_text, ru_text, sep="\n")
    
    # if reduce_empty:
    #     for verses in (sah_verses, ru_verses):
    #         if not any(v.sentences.strip() for v in verses):
    #             verses.clear()

    # return sah_verses, ru_verses    
    return verses


def process_chapter(
    text_title: str, chapter: int=1, text_title_template: str="{title}.{chapter}",
):
    text_soup = load_chapter(text_title, chapter, text_title_template,
                             return_text_container_only=True)
    return parse_chapter(text_soup)



def all_strings_empty(strings: T.List[str]) -> bool:
    return all(s for s in string)



def process_one_text(text_title, reduce_empty=True):
    # text_sah = BibleText(text_title, [])
    # text_ru = BibleText(text_title, [])
    text = BibleText(text_title, [])

    first_page = load_chapter(text_title)
    chapters = first_page.find("select", id="selchap")
    chapter_indices = list_values_from_select(chapters)

    chapter_soups = chain(
        [(1, first_page)],
        ((ch, load_chapter(text_title, ch)) for ch in chapter_indices)
    )

    pbar = tqdm(chapter_soups)
    for chapter_index, soup in pbar:
        pbar.set_description(f"глава {chapter_index}")
        text_container: T.Optional[bs4.Tag] = soup.find("div", id="text")
        if not text_container:
            raise ValueError(f"no text container")
        
        # chapter_sah = BibleChapter(chapter_index, [])
        # chapter_ru = BibleChapter(chapter_index, [])
        # text_sah.chapters.append(chapter_sah)
        # text_ru.chapters.append(chapter_ru)
        chapter = BibleChapter(chapter_index, [])
        text.chapters.append(chapter)

        # sah_verses, ru_verses = parse_chapter(text_container)
        verses = parse_chapter(text_container)

        # chapter_sah.verses.extend(sah_verses)
        # chapter_ru.verses.extend(ru_verses)
        chapter.verses.extend(verses)

        # verses = text_container.find_all("div", class_="interB")
        # for verse in verses:
        #     sah_verse, ru_verse  = verse.find_all("span", class_="vs")
            
        #     verse_num = None
        #     for verse_tag in (sah_verse, ru_verse):
        #         verse_num_tag = verse_tag.find("sup")
        #         verse_num = int(verse_num_tag.string)
        #         verse_num_tag.extract()

        #     # `.strings` or `.stripped_strings`?
        #     sah_text = ' '.join(sah_verse.strings)
        #     ru_text = ' '.join(ru_verse.strings)
        #     verse_sah = BibleVerse(verse_num, sah_text)
        #     verse_ru = BibleVerse(verse_num, ru_text)
        #     chapter_sah.verses.append(verse_sah)
        #     chapter_ru.verses.append(verse_ru)

        #     print(verse_num, sah_text, ru_text, sep="\n")


    # return {"sah": text_sah.to_json(), "ru": text_ru.to_json()}
    return text.to_json()


def get_text_titles():
    """Load a page with first chapter of Genesis, find all text titles in select"""
    page_soup = load_chapter("Gen", chapter=1, return_text_container_only=False)
    books_select = page_soup.find("select", id="selbook")
    return list_values_from_select(books_select)



def main():
    text_titles = get_text_titles()

    texts = []

    pbar = tqdm(text_titles)
    for title in pbar:
        pbar.set_description(f"Книга: {title}")
        texts.append(process_one_text(title))
        
    with open("bible-sah_ru.json", "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
