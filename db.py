import datetime
import random
import sys

from sqlalchemy import create_engine, exc, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from const import PROTOCOL, USER, PASSWORD, HOST, PORT, DB_NAME
from models import create_tables, Search, Bot, BotSearch


def create_db():
    """Создаем БД"""
    try:
        dsn = f"{PROTOCOL}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"
        engine = create_engine(dsn)
        if not database_exists(engine.url):
            create_database(engine.url)
    except exc.ArgumentError as err:
        print('Incorrect DSN connection string. Details:', err)
        sys.exit()
    else:
        return engine


def register_bot_user(sex, age, city_id, profile, update_time):
    """Вносим пользователя бота в БД"""
    new_user = Bot(sex=sex, age=age, city_id=city_id, profile=profile,
                   update_time=update_time)
    with Session() as session:
        session.add(new_user)
        session.commit()


def check_reg(profile):
    """Проверяем наличие пользователя бота в БД"""
    with Session() as session:
        bot_id = session.query(Bot.bot_id). \
            filter(Bot.profile == profile).first()[0]
        return bot_id


def get_bot_update_time(profile):
    """Получаем дату последнего обновления пользователя бота"""
    with Session() as session:
        bot_update_time = session.query(Bot.update_time). \
            filter(Bot.profile == profile).first()
        if bot_update_time:
            return bot_update_time[0]


def check_if_update_needs(profile):
    """Проверяем наступил ли период для обновления данных в БД"""
    bot_update_time = get_bot_update_time(profile)
    next_period = bot_update_time + datetime.timedelta(days=30.0)
    current_datetime = datetime.datetime.now()
    if next_period < current_datetime:
        return True


def update_bot_and_search(sex, age, city_id, profile):
    """Обновляем записи в таблице пользователя бота(Bot) и в таблице найденных
    пользователей(Search), если наступил период обновления"""
    if check_if_update_needs(profile):
        current_datetime = datetime.datetime.now()
        with Session() as session:
            session.query(Bot).filter(Bot.profile == profile).update(
                {'sex': sex, 'age': age, 'city_id': city_id,
                 'update_time': current_datetime})
            search_ids = [el[0] for el in get_search_ids()]
            session.query(Search).filter(
                Search.search_id.in_(search_ids)).delete()
            session.commit()
            return True


def get_search_ids():
    """Находим какие строчки с первичным ключом в таблице Search
    относятся к таблице Bot через промежуточную таблицу BotSearch"""
    with Session() as session:
        return session.query(Search.search_id).join(BotSearch).join(Bot). \
            filter(Bot.bot_id == BotSearch.bot_id).all()


def create_row_in_search_table(first_name, last_name, profile, top_url_photos):
    """Добавляем в таблицу Search найденных пользователей на основании
    информации из анкеты пользователя бота"""
    with Session() as session:
        search_row = session.execute(insert(Search).returning(
            Search.search_id), [{
                'first_name': first_name, 'last_name': last_name,
                'profile': profile,
                'photo_1': top_url_photos[0]
                if len(top_url_photos) > 0 else None,
                'photo_2': top_url_photos[1]
                if len(top_url_photos) > 1 else None,
                'photo_3': top_url_photos[2]
                if len(top_url_photos) > 2 else None
            }])
        session.commit()
        return search_row.fetchone()[0]


def create_row_in_bot_search_table(search_id, profile):
    """Вносим записи в промежуточную таблицу BotSearch
    для связи многие-ко-многим"""
    with Session() as session:
        bot_id = check_reg(profile)
        bot_search_row = BotSearch(bot_id=bot_id, search_id=search_id)
        session.add(bot_search_row)
        session.commit()


def get_random_search_id():
    """Получаем случайный первичный ключ из таблицы найденных пользователей"""
    search_ids = get_search_ids()
    flat_search_ids = [el[0] for el in search_ids]
    random_search_id = random.choice(flat_search_ids)
    return random_search_id


def get_random_search_row():
    """Получаем случайную запись, которой нет в черном списке,
    среди найденных пользователей"""
    random_search_id = get_random_search_id()
    while check_if_user_in_black_list(random_search_id):
        random_search_id = get_random_search_id()
    with Session() as session:
        return session.query(Search.search_id, Search.first_name,
                             Search.last_name, Search.profile, Search.photo_1,
                             Search.photo_2, Search.photo_3).filter(
            Search.search_id == random_search_id).first()


def get_favourite_list():
    """Получаем содержимое списка избранных"""
    with Session() as session:
        return session.query(Search.search_id, Search.first_name,
                             Search.last_name, Search.profile, Search.photo_1,
                             Search.photo_2, Search.photo_3).filter(
            Search.is_in_favourite_list).all()


def check_if_user_in_favourite_list(search_id):
    """Проверяем есть ли в списке избранных предлагаемый пользователь в чате"""
    with Session() as session:
        favourite_list_check = session.query(Search.is_in_favourite_list). \
            filter(Search.search_id == search_id).first()
    if favourite_list_check:
        return favourite_list_check[0]


def add_to_db_favourite_list(search_id):
    """Добавляем пользователя в список избранных"""
    if not check_if_user_in_favourite_list(search_id):
        with Session() as session:
            favourite_list_check = session.query(Search). \
                filter(Search.search_id == search_id).update(
                {'is_in_favourite_list': True})
            if favourite_list_check:
                session.commit()
                return True
    elif check_if_user_in_favourite_list(search_id):
        return False


def find_search_id_by_profile(profile):
    """Находим по ID анкете среди найденных пользователей в этой же таблице
     соответствующий ему первичный ключ"""
    search_ids = get_search_ids()
    with Session() as session:
        search_id = session.query(Search.search_id).filter(
            Search.profile == profile).first()
        if search_id is not None and (search_id[0],) in search_ids:
            return search_id


def remove_in_db_favourite_list(profile):
    """Удаляем пользователя из списка избранных"""
    search_id = find_search_id_by_profile(profile)
    if search_id:
        with Session() as session:
            session.query(Search).filter(Search.search_id == search_id[0]). \
                update({'is_in_favourite_list': False})
            session.commit()
            return True


def get_black_list():
    """Получаем содержимое черного списка"""
    with Session() as session:
        return session.query(Search.search_id, Search.first_name,
                             Search.last_name, Search.profile, Search.photo_1,
                             Search.photo_2, Search.photo_3).filter(
            Search.is_in_black_list).all()


def check_if_user_in_black_list(search_id):
    """Проверяем есть ли в черном списке предлагаемый пользователь в чате"""
    with Session() as session:
        black_list_check = session.query(Search.is_in_black_list).filter(
                Search.search_id == search_id).first()
    if black_list_check:
        return black_list_check[0]


def add_to_db_black_list(search_id):
    """Добавляем пользователя в черный список"""
    if not check_if_user_in_black_list(search_id):
        with Session() as session:
            black_list_check = session.query(Search).filter(
                Search.search_id == search_id). \
                update({'is_in_black_list': True})
            if black_list_check:
                session.commit()
                return True
    elif check_if_user_in_black_list(search_id):
        return False


def remove_in_db_black_list(profile):
    """Удаляем пользователя из черного списка"""
    search_id = find_search_id_by_profile(profile)
    if search_id:
        with Session() as session:
            session.query(Search).filter(Search.search_id == search_id[0]). \
                update({'is_in_black_list': False})
            session.commit()
            return True


engine = create_db()
create_tables(engine)
Session = sessionmaker(bind=engine)
