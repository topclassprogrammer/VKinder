import sqlalchemy as sq
from sqlalchemy.orm import relationship

from const import Base


class VkUsers(Base):
    __tablename__ = 'vk_users'
    vk_user_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String(60), nullable=False)
    last_name = sq.Column(sq.String(60), nullable=False)
    vk_id = sq.Column(sq.Integer, nullable=False)
    link_to_photo_1 = sq.Column(sq.String(255))
    link_to_photo_2 = sq.Column(sq.String(255))
    link_to_photo_3 = sq.Column(sq.String(255))
    table_update_time = sq.Column(sq.DateTime, nullable=False)
    bot_user = relationship('VkBotUsers', back_populates='vk_user')


class VkBotUsers(Base):
    __tablename__ = 'vk_bot_users'
    vk_bot_users_id = sq.Column(sq.Integer, primary_key=True)
    bot_user_id = sq.Column(sq.Integer, sq.ForeignKey('bot_users.bot_user_id', ondelete="CASCADE"))
    vk_user_id = sq.Column(sq.Integer, sq.ForeignKey('vk_users.vk_user_id', ondelete="CASCADE"))
    vk_user = relationship('VkUsers', back_populates='bot_user')
    bot_user = relationship('BotUsers', back_populates='vk_user')


class BotUsers(Base):
    __tablename__ = 'bot_users'
    bot_user_id = sq.Column(sq.Integer, primary_key=True)
    sex = sq.Column(sq.String(15), nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    city_id = sq.Column(sq.Integer, nullable=False)
    vk_id = sq.Column(sq.Integer, unique=True)
    table_update_time = sq.Column(sq.DateTime, nullable=False)
    vk_user = relationship('VkBotUsers', back_populates='bot_user')
    favourite = relationship('BotUsersFavourites', back_populates='bot_user')
    black_list = relationship('BotUsersBlackLists', back_populates='bot_user')


class BotUsersFavourites(Base):
    __tablename__ = 'bot_users_favourites'
    bot_users_favourites_id = sq.Column(sq.Integer, primary_key=True)
    bot_user_id = sq.Column(sq.Integer, sq.ForeignKey('bot_users.bot_user_id', ondelete="CASCADE"))
    favourite_id = sq.Column(sq.Integer, sq.ForeignKey('favourites.favourite_id', ondelete="CASCADE"))
    bot_user = relationship('BotUsers', back_populates='favourite')
    favourite = relationship('Favourites', back_populates='bot_user')


class Favourites(Base):
    __tablename__ = 'favourites'
    favourite_id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True)
    bot_user = relationship('BotUsersFavourites', back_populates='favourite')


class BotUsersBlackLists(Base):
    __tablename__ = 'bot_users_black_lists'
    bot_users_black_lists_id = sq.Column(sq.Integer, primary_key=True)
    bot_user_id = sq.Column(sq.Integer, sq.ForeignKey('bot_users.bot_user_id', ondelete="CASCADE"))
    black_list_id = sq.Column(sq.Integer, sq.ForeignKey('black_lists.black_list_id', ondelete="CASCADE"))
    bot_user = relationship('BotUsers', back_populates='black_list')
    black_list = relationship('BlackLists', back_populates='bot_user')


class BlackLists(Base):
    __tablename__ = 'black_lists'
    black_list_id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True)
    bot_user = relationship('BotUsersBlackLists', back_populates='black_list')


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
