# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class ForumYktPipeline:
    def process_item(self, item, spider):
        return item


class RuDatePipeline:
    months = {
        "янв": 1,
        "фев": 2,
        "мар": 3,
        "апр": 4,
        "мая": 5,
        "июн": 6,
        "июл": 7,
        "авг": 8,
        "сен": 9,
        "окт": 10,
        "ноя": 11,
        "дек": 12,
    }

    @classmethod
    def convert_month(cls, month: str) -> int:
        return cls.months[month[:3].lower()]
    
    @classmethod
    def parse_date(cls, timestamp: str, sep=" ") -> datetime:
        day, month, year = timestamp.split(sep)
        month_int = cls.convert_month(month)
        
        return datetime(int(year), month_int, int(day))
