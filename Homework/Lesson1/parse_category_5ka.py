import time
import json
from pathlib import Path
import requests

class Parse5ka:
    params = {
        "records_per_page": 20,
    }

    def __init__(self, start_url: str, result_path: Path):
        self.start_url = start_url
        self.result_path = result_path

    def _get_response(self, url, *args, **kwargs) -> requests.Response:
        while True:
            response = requests.get(url, *args, **kwargs)
            if response.status_code == 200:
                return response
            time.sleep(1)

    def run(self):
        for product in self.parse(self.start_url):
            self._save(product)

    def parse(self, url):
        while url:
            response = self._get_response(url, params=self.params)
            data = response.json()
            url = data.get("next")
            for product in data.get("results", []):
                yield product

    def _save(self, data):
        file_path = self.result_path.joinpath(f'{data["id"]}.json')
        file_path.write_text(json.dumps(data, ensure_ascii=False))

class Parse5ka_category(Parse5ka):

    def __init__(self, start_url: str, result_path: Path):
        super().__init__(start_url, result_path)

    def parse(self, url):
        response = self._get_response(url)
        data = response.json()
        for category in data:
            category_id = str(category.get("parent_group_code"))
            category_name = str(category.get("parent_group_name"))

            products = []

            parse5ka = Parse5ka("https://5ka.ru/api/v2/special_offers/", self.result_path)
            parse5ka.params["categories"] = category_id

            for product in parse5ka.parse(parse5ka.start_url):
                products += [product]

            category_data = {"name": category_name,
                             "code": category_id,
                             "products": products}
            yield category_data

    def _save(self, data):
        category_id = data["code"]
        file_path = self.result_path.joinpath(f'{category_id}.json')
        #file_path.write_text(json.dumps(data, ensure_ascii=False))
        file_path.write_text(json.dumps(data))

    def run(self):
        for category in self.parse(self.start_url):
            self._save(category)



if __name__ == "__main__":
    file_path = Path(__file__).parent.joinpath("categories")
    if not file_path.exists():
        file_path.mkdir()
    parser = Parse5ka_category("https://5ka.ru/api/v2/categories/", file_path)
    parser.run()