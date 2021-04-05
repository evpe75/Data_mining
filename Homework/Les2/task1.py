import datetime as dt
from urllib.parse import urljoin
import requests
import bs4
import pymongo
import time

MONTHS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "мая": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}

class ParseError(Exception):
    def __init__(self, message):
        self.__message = message

    @property
    def message(self):
        return self.__message

class MagnitParse:

    def __init__(self, url, db_client):
        self.url = url
        self.db = db_client["Data_Mining"]
        self.db_collection = self.db["magnit_products"]

    def _get_item_tags(self, catalog):
        for item_a in catalog.find_all("a", attrs = {"class": "card-sale_catalogue"}):
            yield item_a

    def parse_datetime(self, promo_date_tag, idx):
        str_ret_dt = ""
        tags_p = promo_date_tag.find_all("p")
        if tags_p.__len__() >= idx+1:
            promo_date = tags_p[idx].text
            str_promo_date = str(promo_date).replace("с ", "").replace("до ", "")
            dt_mon  = MONTHS.get(str_promo_date.split(" ")[1][:3], 0)
            if dt_mon > 0:
                dt_year = dt.datetime.now().year
                dt_day = int(str_promo_date.split(" ")[0])
                str_ret_dt =  str(dt.datetime(dt_year, dt_mon, dt_day))

        return str_ret_dt

    def _get_template(self):
        return {
            "url": lambda a: urljoin(self.url, a.get("href", "")),
            "promo_name": lambda a: "" if a.find("div", attrs = {"class": "card-sale__header"}) is None else
                                    a.find("div", attrs = {"class": "card-sale__header"}).text,
            "product_name": lambda a: "" if a.find("div", attrs = {"class": "card-sale__title"}) is None else
                                    a.find("div", attrs = {"class": "card-sale__title"}).text,
            "old_price": lambda a: 0.0 if a.find("div", attrs = {"class": "label__price_old"}) is None else
                                    float(".".join(
                                        [a.find("div", attrs = {"class": "label__price_old"}).find(
                                                    "span", attrs = {"class": "label__price-integer"}).text,
                                        a.find("div", attrs = {"class": "label__price_old"}).find(
                                                    "span", attrs = {"class": "label__price-decimal"}).text])),
            "new_price": lambda a: 0.0 if a.find("div", attrs = {"class": "label__price_old"}) is None else
                                    float(".".join(
                                        [a.find("div", attrs = {"class": "label__price_new"}).find(
                                                    "span", attrs = {"class": "label__price-integer"}).text,
                                        a.find("div", attrs = {"class": "label__price_new"}).find(
                                                    "span", attrs = {"class": "label__price-decimal"}).text])),
            "image_url": lambda a: "" if a.find("img", attrs = {"class": "lazy"}) is None else
                                    urljoin(self.url, a.find("img", attrs = {"class": "lazy"}).get("data-src", "")),
            "date_from": lambda a: "" if a.find("div", attrs = {"class": "card-sale__date"}) is None else
                                    self.parse_datetime(a.find("div", attrs = {"class": "card-sale__date"}), 0),
            "date_to": lambda a: "" if a.find("div", attrs = {"class": "card-sale__date"}) is None else
                                    self.parse_datetime(a.find("div", attrs = {"class": "card-sale__date"}), 1)
        }

    def _save(self, item_a):
        data = {}
        for key, funk in self._get_template().items():
            try:
                data[key] = funk(item_a)
            except (AttributeError, ValueError):
                pass

        if data["date_from"] and data["date_to"]:
            date_from = dt.datetime.strptime(data["date_from"], "%Y-%m-%d %H:%M:%S")
            date_to   = dt.datetime.strptime(data["date_to"], "%Y-%m-%d %H:%M:%S")
            if date_from > date_to:
                dt_year = date_to.year + 1
                dt_mon = date_to.month
                dt_day = date_to.day
                new_date_to = dt.datetime(dt_year, dt_mon, dt_day)
                data["date_to"] = str(new_date_to)

        self.db_collection.insert_one(data)

    def _parse(self, soup):
        сatalogue_main = soup.find("div", attrs={"class": "сatalogue__main"})
        if not сatalogue_main is None:
            for item_tag in self._get_item_tags(сatalogue_main):
                self._save(item_tag)

    def run(self):
        idx = 0
        try:
            while True:
                idx += 1
                responce = requests.get(self.url)
                if (responce.status_code == 200):
                    soup = bs4.BeautifulSoup(responce.text, "lxml")
                    self._parse(soup)
                    break

                if (idx > 5):
                    raise ParseError("Неудачная попытка запроса")
                else:
                    time.sleep(1)

        except ParseError as e:
            print(e.message)


if __name__ == "__main__":
    url = "https://magnit.ru/promo/"
    db_client = pymongo.MongoClient("mongodb://localhost:27017")

    parser = MagnitParse(url, db_client)
    parser.run()


