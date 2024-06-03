import typing as T
from abc import ABCMeta, ABC
from dataclasses import asdict, dataclass, field
import datetime as dt


# __all__ = [
#     "Author",
#     "Ongoing",
# ]


DateType = T.Union[dt.date, 'Ongoing']
DateAndRangeType = T.Union[dt.date, 'DateRange', 'Ongoing']


# @dataclass
# class Format:
#     TEXT_META_KEY: str

# class TSAKorpusFormat(Format):
#     TEXT_META_KEY = "meta"


def filter_empty(d: T.Dict[T.Any, T.Any]):
    return {key: val for key, val in d.items() if val is not None}


class BaseMeta(ABC):
    def to_tsakorpus_json(self) -> T.Dict[str, T.Any]: ...


class BaseTextItem(ABC): ...

class Ongoing:
    """Mock end date.
    
    Evaluates to :func:`datetime.date.today()` on comparison except for `==`"""
    def __eq__(self, other: object) -> bool:
        return type(other) is Ongoing

    def __lt__(self, other: dt.date) -> bool:
        return dt.date.today() < other
    
    def __gt__(self, other: dt.date) -> bool:
        return dt.date.today() > other

    def __le__(self, other: dt.date) -> bool:
        return dt.date.today() <= other
    
    def __ge__(self, other: dt.date) -> bool:
        return dt.date.today() >= other
    
    @property
    def year(self):
        # return dt.date.today().year
        return None


ONGOING = Ongoing()
# DATE_UKNOWN = object()


class DateRange:
    start: T.Optional[DateType]
    end: T.Optional[DateType]

    def __init__(
        self, start: T.Optional[DateType] = None,
        end: T.Optional[DateType] = None
    ) -> None:
        self.start = start
        self.end = end

        self.is_start_known = (
            # start is not DATE_UKNOWN and 
            start is not None)
        
        ongoing = end is ONGOING
        self.is_ongoing = ongoing
        self.is_end_known = (
            # end is not DATE_UKNOWN and 
            end is not None and not ongoing
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DateRange):
            raise ValueError(f"Testing equality with object of type {type(other)}"
                             f"not supported: {other}")
        return self.start == other.start and self.end == other.end         

    def __contains__(self, other: T.Union[dt.date, 'DateRange']) -> bool:
        if not (self.is_start_known and self.is_end_known):
            return False
        if isinstance(other, dt.date):
            return self.start <= other <= self.end
        elif isinstance(other, DateRange):
            return self.start <= other.start and self.end >= other.end
        else:
            raise ValueError(f"Testing membership for object of type {type(other)}"
                             f"not supported: {other}")

    def intersects(self, other: 'DateRange') -> bool:
        if not (self.is_start_known and self.is_end_known):
            return False
        return self.start <= other.start <= self.end or self.start <= other.end <= self.end

    def __and__(self, other: 'DateRange') -> bool: 
        return self.intersects(other)


@dataclass
class AuthorMeta(BaseMeta):
    full_name: T.Optional[str] = None
    first_name: T.Optional[str] = None
    last_name: T.Optional[str] = None
    date_born: T.Optional[T.Union[dt.date, DateRange]] = None
    date_died: T.Optional[DateAndRangeType] = None


NO_AUTHOR = AuthorMeta(full_name="<no author>")

def default_author():
    return [NO_AUTHOR]


def _get_year(maybe_date: T.Optional[T.Union[dt.date, Ongoing]]) -> T.Optional[int]:
    return maybe_date.year if (maybe_date is not None) else None


@dataclass
class TextMeta(BaseMeta):
    NO_TITLE = "<no title>"

    title: str = NO_TITLE
    chapter: T.Optional[T.Union[str, int]] = None
    writing_date: T.Optional[DateAndRangeType] = None

    authors: T.List[AuthorMeta] = field(default_factory=lambda: [NO_AUTHOR])

    url: T.Optional[str] = None

    def to_tsakorpus_json(self):
        base_dict = asdict(self)

        writing_date = base_dict["writing_date"]
        if isinstance(writing_date, DateRange):
            base_dict.update(dict(
                year_from = _get_year(writing_date.start),
                year_to = _get_year(writing_date.end)
            ))

        base_dict["author"] = ", ".join([author.full_name for author in self.authors])
        base_dict["authors"] = [asdict(author) for author in self.authors]

        return base_dict
        


# @dataclass
# class SentenceMeta(BaseMeta): ... 


@dataclass
class TextItem:
    meta: TextMeta
    sentences: T.List['SentenceItem']

    def to_tsakorpus_json(self):
        return asdict(self)
    

@dataclass
class SentenceItem:
    text: str
    tokens: T.List['Token']
    lang: str  # the primary (?) language of the sentence
    meta: BaseMeta




# @dataclass
# class DerivedTextItemMixin(TextItem):
#     orig_text: TextItem = field(default_factory=lambda: TextItem())


# @dataclass
# class TranslatedTextItemMixin(DerivedTextItemMixin): ...
