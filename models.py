import sqlalchemy as sq
from sqlalchemy.orm import relationship

from const import Base


class Bot(Base):
    """Таблица пользователей бота"""
    __tablename__ = 'bot'
    bot_id = sq.Column(sq.Integer, primary_key=True)
    sex = sq.Column(sq.String(15), nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    city_id = sq.Column(sq.Integer, nullable=False)
    profile = sq.Column(sq.Integer, unique=True)
    update_time = sq.Column(sq.DateTime, nullable=False)
    search = relationship('BotSearch', back_populates='bot')


class BotSearch(Base):
    """Промежуточная таблица при отношении многие-ко-многим для связи пользователей бота
     и найденных результатов ботом"""
    __tablename__ = 'bot_search'
    bot_search_id = sq.Column(sq.Integer, primary_key=True)
    bot_id = sq.Column(sq.Integer, sq.ForeignKey('bot.bot_id', ondelete="CASCADE"))
    search_id = sq.Column(sq.Integer, sq.ForeignKey('search.search_id', ondelete="CASCADE"))
    search = relationship('Search', back_populates='bot')
    bot = relationship('Bot', back_populates='search')


class Search(Base):
    """Таблица найденных результатов ботом"""
    __tablename__ = 'search'
    search_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String(60), nullable=False)
    last_name = sq.Column(sq.String(60), nullable=False)
    profile = sq.Column(sq.Integer, nullable=False)
    photo_1 = sq.Column(sq.String(255))
    photo_2 = sq.Column(sq.String(255))
    photo_3 = sq.Column(sq.String(255))
    is_in_favourite_list = sq.Column(sq.Boolean)
    is_in_black_list = sq.Column(sq.Boolean)
    bot = relationship('BotSearch', back_populates='search')


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
