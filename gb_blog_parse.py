import typing
import requests
import bs4
import time
import json
from urllib.parse import urljoin
from database import db


class GbBlogParse:
    def __init__(self, start_url, database: db.Database):
        self.db = database
        self.start_url = start_url
        self.done_urls = set()
        self.tasks = []
        self.post_count = 0

    def get_task(self, url: str, callback: typing.Callable) -> typing.Callable:
        def task():
            soup = self._get_soup(url)
            return callback(url, soup)

        return task

    def _get_response(self, url, *args, **kwargs) -> requests.Response:
        try_count = 0
        max_try_count = 5
        while try_count <= max_try_count :
            try_count += 1
            response = requests.get(url, *args, **kwargs)
            if response.status_code == 200:
                return response
            if try_count <= max_try_count:
                time.sleep(1)


    def _get_soup(self, url, *args, **kwargs) -> bs4.BeautifulSoup:
        soup = None
        response = self._get_response(url, *args, **kwargs)
        if response:
            soup = bs4.BeautifulSoup(self._get_response(url, *args, **kwargs).text, "lxml")
        return soup

    def _get_item_comment(self, list_comments):
        for item_comment in list_comments:
            #data_item_comment = item_comment
            item_comment_data = item_comment['comment']
            user_data = item_comment_data['user']
            data_item_comment = {"id": item_comment_data["id"],
                                 "parent_comment_id": item_comment_data["parent_id"],
                                 "comment_text": item_comment_data["body"],
                                 "author_data": {"url": user_data["url"],
                                                 "name": user_data["full_name"],
                                                }
                                 }
            child_comment_list = item_comment_data.get("children")
            if child_comment_list:
                data_item_comment["comments"] = self._get_comments_data(child_comment_list)
            yield data_item_comment

    def _get_comments_data(self, json_data):
        comments_data = []
        for item_comment in self._get_item_comment(json_data):
            comments_data.append(item_comment)
        return comments_data

    def _create_comment_data(self, comment_item_tag):
        req_commens_params = {"commentable_type": comment_item_tag.attrs.get("commentable-type"),
                              "commentable_id": comment_item_tag.attrs.get("commentable-id"),
                              "order": comment_item_tag.attrs.get("order")
                             }
        response = self._get_response("https://gb.ru/api/v2/comments", params = req_commens_params)
        if response:
            json_data = response.json()
            comments_data = self._get_comments_data(json_data)
        else:
            comments_data = []
        return comments_data

    def _create_comments_data(self, comments_tag):
        if comments_tag:
            comments_data = self._create_comment_data(comments_tag)
        else:
            comments_data = []
        return comments_data

    def parse_post(self, url, soup):
        if soup:
            author_tag = soup.find("div", attrs={"itemprop": "author"})
            data = {
                "post_data": {
                    "title": soup.find("h1", attrs={"class": "blogpost-title"}).text,
                    "url": url,
                    "img": soup.find("img").attrs.get("src"),
                    "date": soup.find("time", attrs={"itemprop": "datePublished"}).attrs.get("datetime"),
                },
                "author_data": {
                    "url": urljoin(url, author_tag.parent.attrs.get("href")),
                    "name": author_tag.text,
                },
                "tags_data": [
                    {"url": urljoin(url, tag_a.attrs.get("href")), "name": tag_a.text}
                    for tag_a in soup.find_all("a", attrs={"class": "small"})
                ],
                "comments_data": self._create_comments_data(soup.find("comments")),
            }
        else:
            data = {}

        return data

    def parse_feed(self, url, soup):
        if soup:
            ul = soup.find("ul", attrs={"class": "gb__pagination"})
            pag_urls = set(
                urljoin(url, url_a.attrs.get("href"))
                for url_a in ul.find_all("a")
                if url_a.attrs.get("href")
            )
            for pag_url in pag_urls:
                if pag_url not in self.done_urls:
                    task = self.get_task(pag_url, self.parse_feed)
                    self.done_urls.add(pag_url)
                    self.tasks.append(task)

            post_urls = set(
                urljoin(url, url_a.attrs.get("href"))
                for url_a in soup.find_all("a", attrs={"class": "post-item__title"})
                if url_a.attrs.get("href")
            )
            for post_url in post_urls:
                if post_url not in self.done_urls:
                    task = self.get_task(post_url, self.parse_post)
                    self.done_urls.add(post_url)
                    self.tasks.append(task)

    def _exec_tasks(self):
        for task in self.tasks:
            task_result = task()
            if task_result:
                self.save(task_result)

    def run(self):
        task = self.get_task(self.start_url, self.parse_feed)
        self.tasks.append(task)
        self.done_urls.add(self.start_url)
        self._exec_tasks();

    def run_post(self):
        task = self.get_task(self.start_url, self.parse_post)
        self.tasks.append(task)
        self.done_urls.add(self.start_url)
        self._exec_tasks();

    def save(self, data):
        self.db.create_post(data)
        self.post_count += 1
        print(self.post_count)


if __name__ == "__main__":
    database = db.Database("sqlite:///db_blog.db")

    arser = GbBlogParse("https://geekbrains.ru/posts", database)
    arser.run()
    #parser = GbBlogParse("https://gb.ru/posts/i-tut-menya-osenilo-ya-hochu-byt-it-rekruterom", database)
    #parser.run_post()


