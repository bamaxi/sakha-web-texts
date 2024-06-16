# Sakha web texts

*This description is in English.
    Описание [на русском языке доступно ниже](#ru)*.


The repository presents code to scrape texts in [Sakha (Yakut) language](https://www.ethnologue.com/language/sah/).
    Texts themselves are also released.

The texts are from several domains:

* **News**: <https://edersaas.ru> and <https://sakha.ysia.ru> news agencies
* **Forums:** <https://forum.ykt.ru> (downloaded via <https://web.archive.org>)
*  **Parallel Bible**: <https://ibtrussia.org/en> parallel Russian — Yakut texts. 

For Russian in the **parallel Bible** domain, Russian Synodal Bible was chosen.

## Dataset statistics
   
*`N` is number of texts.
    `L` stands for 'length' of the `text` field in tokens.
    0-length items are texts with `title` only*.

| subset      | N      | train ratio | test ratio | L tokens avg | L tokens σ | L tokens min | L tokens max |
|-------------|--------|-------------|------------|--------------|------------|--------------|--------------|
| forums      | 81365  | 54.1%       | 54.1%      | 28.19        | 92.82      | 0            | 10022        |
| news        | 51593  | 34.3%       | 34.3%      | 254.57       | 361.90     | 0            | 23162        |
| wikipedia   | 17450  | 11.6%       | 11.6%      | 152.67       | 373.68     | 0            | 20704        |
| **overall** | 150408 | 100%        | 100%       | 120.28       | 276.91     | 0            | 23162        |


## Dataset features

A range of metadata is scraped for the texts, depending on the domain.

## Usage

The code for `forums` and `news` is based on [Scrapy library](https://scrapy.org/) and could be run from the corresponding directories like below (e.g. for *ysia*):

```bash
# in /edersaas
scrapy crawl ysia
```

--- 
<a name="ru"></a>


В репозитории представлен код для скачивания текстов с вебсайтов на [якутском языке](https://www.ethnologue.com/language/sah/).
    Сами тексты также опубликованы.

Тексты скачаны из нескольких доменов:

* **Новости**: <https://edersaas.ru> и <https://sakha.ysia.ru> (новостные агенства)
* **Форумы:** <https://forum.ykt.ru> (загружено через <https://web.archive.org>)
*  **Параллельная Библия**: <https://ibtrussia.org/en> параллельные русско—якутские тексты. 

В качестве русского для **параллельной Библии** был использован русский Синодальный перевод.


## Статистика по датасету
    
*`N` — число текстов.
    `L` это 'длина' поля `text` в токенах.
    Объекты нулевой длины это тексты, у которых есть только заголовок `title`*.


| раздел    | N      | доля в train | доля в test | L средняя (токенов) | L σ (токенов) | L min (токенов) | L max (токенов) |
|-----------|--------|--------------|-------------|---------------------|---------------|-----------------|-----------------|
| форумы    | 81365  | 54.1%        | 54.1%       | 28.19               | 92.82         | 0               | 10022           |
| новости   | 51593  | 34.3%        | 34.3%       | 254.57              | 361.90        | 0               | 23162           |
| Википедия | 17450  | 11.6%        | 11.6%       | 152.67              | 373.68        | 0               | 20704           |
| **всего** | 150408 | 100%         | 100%        | 120.28              | 276.91        | 0               | 23162           |


## Признаки в датасете

Для текстов доступен ряд метаданных, которые определяются доменом текста.

## Использование

Код для `forums` and `news` основан на [библиотеке Scrapy](https://scrapy.org/) и может быть запущен из соответствующих папок как в примере ниже (для *ysia*):

```bash
# в /edersaas
scrapy crawl ysia
```

