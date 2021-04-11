from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import models


table_mapper = {
    "post_data": models.Post,
    "author_data": models.Author,
}


class Database:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        models.Base.metadata.create_all(bind=engine)
        self.maker = sessionmaker(bind=engine)
        self.created_authors = {}

    def get_or_create(self, session, model, filter, **data):
        db_instance = None
        if model is models.Author:
            db_instance = self.created_authors.get(data['url'])

        if not db_instance:
            db_instance = session.query(model).filter_by(**filter).first()
            if not db_instance:
                db_instance = model(**data)

        if model is models.Author:
            self.created_authors[data['url']] = db_instance

        return db_instance

    def _create_comments(self, session, parent_model, data_comments):
        list_comments = []
        for comment in data_comments:
            comment_data = {"id": comment["id"], "text": comment["comment_text"]}
            instance_comment = self.get_or_create(session, models.Comment, {"id": comment["id"]}, **comment_data)

            author_data = comment["author_data"]
            instance_author = self.get_or_create(session, models.Author, {"url": author_data["url"]}, **author_data)
            instance_comment.author = instance_author

            list_comments.append(instance_comment)

            if isinstance(parent_model, models.Post):
                instance_comment.post = parent_model
            elif isinstance(parent_model, models.Comment):
                instance_comment.parent_comment_id = parent_model.id

            comment_comments = comment.get("comments")
            if comment_comments:
                self._create_comments(session, instance_comment, comment_comments)

        if list_comments:
            parent_model.comments.extend(list_comments)


    def create_post(self, data):
        session = self.maker()
        post = None
        for key, model in table_mapper.items():
            instance = self.get_or_create(session, model, {"url": data[key]["url"]}, **data[key])
            if isinstance(instance, models.Post):
                post = instance
            elif isinstance(instance, models.Author):
                post.author = instance
        post.tags.extend(
            [
                self.get_or_create(session, models.Tag, {"url": tag_data["url"]}, **tag_data)
                for tag_data in data["tags_data"]
            ]
        )

        data_comments = data["comments_data"]
        self._create_comments(session, post, data_comments)

        try:
            session.add(post)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
        #print(1)