from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from const import Base


class Users(Base):
    __tablename__ = 'user'
    id_vk = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.String(length=60), nullable=False)
    surname = sq.Column(sq.String(length=60), nullable=False)
    sex = sq.Column(sq.String(length=15), nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    city = sq.Column(sq.String(length=75), nullable=False)
    link_to_profile = sq.Column(sq.String(length=150), unique=True)


class Black_list(Base):
    __tablename__ = 'blacklist'
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey("user.id_vk"), nullable=False)
    user_bl_id = sq.Column(sq.Integer, sq.ForeignKey("user.id_vk"), nullable=False)


class Favorite_list(Base):
    __tablename__ = 'favoritelist'
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey("user.id_vk"), nullable=False)
    user_fav_id = sq.Column(sq.Integer, sq.ForeignKey("user.id_vk"), nullable=False)


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
