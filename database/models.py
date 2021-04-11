from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, ForeignKey, Table


Base = declarative_base()


class UrlMixin:
    url = Column(String, nullable=False, unique=True)


class IdMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)

class IdStringMixin:
    id = Column(String, nullable=False, primary_key=True)


tag_post = Table(
    "tag_post",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("post.id")),
    Column("tag_id", Integer, ForeignKey("tag.id")),
)


class Author(Base, UrlMixin, IdMixin):
    __tablename__ = "author"
    name = Column(String)
    posts = relationship("Post")


class Comment(Base, IdMixin):
    __tablename__ = "comment"
    post_id = Column(Integer, ForeignKey("post.id"))
    post = relationship("Post")
    parent_comment_id = Column(Integer, ForeignKey("comment.id"))
    #parent_comment = relationship("Comment")
    text = Column(String)
    author_id = Column(Integer, ForeignKey("author.id"))
    author = relationship(Author)
    comments = relationship("Comment")

class Post(Base, UrlMixin, IdMixin):
    __tablename__ = "post"
    title = Column(String, nullable=False)
    img = Column(String)
    date = Column(String)
    author_id = Column(Integer, ForeignKey("author.id"))
    author = relationship(Author)
    tags = relationship("Tag", secondary=tag_post)
    comments = relationship(Comment)

class Tag(Base, UrlMixin, IdMixin):
    __tablename__ = "tag"
    name = Column(String)
    posts = relationship(Post, secondary=tag_post)


