import typing as T
from datetime import datetime
import re
from urllib.parse import urlparse, quote as encode_url

try:
    from tqdm.auto import tqdm
    TQDM_AVAILABLE=True
except ImportError:
    def tqdm(iter: T.Iterable[T.Any], *args, **kwargs):
        return iter
    


WEBARCHIVE_DATE_FORMAT = "%Y%m%d"
WEBARCHIVE_DATETIME_FORMAT = "%Y%m%d%H%M%S"

FORUM_YKT_TOPIC_HEAD_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

DEFAULT_ID = -1


def safe_strip(obj: T.Optional[str]):
    return (obj or "").strip()

def safe_int(obj: str) -> T.Optional[int]:
    if obj.isdigit():
        return int(obj)
    return None


def to_webarchive_date(date: datetime) -> str:
    return date.strftime(WEBARCHIVE_DATE_FORMAT)


def convert_snapshot_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, WEBARCHIVE_DATETIME_FORMAT)


def convert_head_timestamp(timestamp: str) -> datetime:
    timestamp = timestamp + "0" * 3  # to get microseconds
    return datetime.strptime(timestamp, FORUM_YKT_TOPIC_HEAD_DATETIME_FORMAT)


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


def ru_month_to_int(ru_month: str) -> int:
    return months[ru_month[:3]]


def convert_time_str(time_str: str) -> T.Tuple[int, int, int]:
    time_sep = ":"
    if time_sep in time_str:
        parts = time_str.split(time_sep)
        if len(parts) == 2:
            hour, minute = map(int, parts)
            return hour, minute, 0

    raise ValueError(f"unknown pattern for time with time_sep=`{time_sep}`: {time_str}")


def convert_customary_to_datetime(time: str, today: datetime) -> T.Union[datetime, str]:
    close_day_sep = ", "
    if close_day_sep in time:
        close_day, time_str = time.split(close_day_sep)

        if close_day.lower() == "вчера":
            day = today.day - 1
            hour, minute, second = convert_time_str(time_str)
            return datetime(today.year, today.month, day, hour, minute, second)
    
    date_sep = " "
    time_sep = ":"
    if date_sep in time:
        parts = time.split(date_sep)
        if len(parts) == 4:
            day, month, year, time_str = parts

            day = int(day)
            month = ru_month_to_int(month)
            year = int(year)
            hour, minute, second = convert_time_str(time_str)
            return datetime(today.year, today.month, today.day, hour, minute, second)
        elif len(parts) == 3:
            day, month, year_or_time = parts

            day = int(day)
            month = ru_month_to_int(month)
            if time_sep in year_or_time:
                hour, minute, second = convert_time_str(year_or_time)
                return datetime(today.year, month, day, hour, minute, second)
            else:
                year = int(year_or_time)
                return datetime(year, month, day)
        elif len(parts) == 2:
            day, month = parts
            
            day = int(day)
            month = ru_month_to_int(month)
            year = today.year
        else:
            raise ValueError(f"unknown pattern with date_sep=`{date_sep}`: {time}")

        return datetime(year, month, day)
    
    if time_sep in time:
        hour, minute, second = convert_time_str(time)
        return datetime(today.year, today.month, today.day, hour, minute, second)

    return f"<{time}>"


def extract_webarchive_date(
    url: str, timestamp_pat=re.compile(r"\d{14}")
) -> T.Optional[datetime]:
    res = timestamp_pat.search(url)
    if res:
        return convert_snapshot_timestamp(res[0])
    else:
        return None


def extract_query(url: str) -> T.Dict[str, T.List[str]]:
    parsed_url = urlparse(url)
    query_str = parsed_url.query
    
    query = {}
    for part in query_str.split("&"):
        key, val = part.split("=")
        query.setdefault(key, []).append(val)

    return query