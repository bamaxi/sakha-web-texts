import random
from time import sleep
import json

import requests
from bs4 import BeautifulSoup

HEADERS = {
    # 'authority': 'www.kith.com',
    'cache-control': 'max-age=0',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.106 Safari/537.36',
    'sec-fetch-dest': 'document',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'accept-language': 'ru;q=0.9, en-US;q=0.8, en;q=0.7',
}


def append_list_part(lst, filename, file_list_els_sep='\n'):
    with open(filename, 'a+', encoding='utf-8') as f:
        f.seek(0)
        file_list_els = f.read().split(file_list_els_sep)
        lst = [str(el) for el in lst]
        els_to_append = [el for el in lst
                         if el not in file_list_els]
        f.write(f"""{file_list_els_sep if len(file_list_els) > 1
                     and els_to_append else ''}"""
                + file_list_els_sep.join(el for el in els_to_append))


def random_delay_adder(min, max):
    def add_random_delay(func):
        def delayed_func(*args, **kwargs):
            sleep(random.uniform(min, max))

            return func(*args, **kwargs)

        return delayed_func
    return add_random_delay


def make_page_loader(PARSER):
    def load_page(page_link):
        response = requests.get(page_link)
        soup = BeautifulSoup(response.text, PARSER)
        return soup

    return load_page


def write_json(obj, filename):
    with open(f"{filename}.json", 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
