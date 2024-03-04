import sys

from sqlalchemy import create_engine, exc
from sqlalchemy_utils import database_exists, create_database

from const import PROTOCOL, USER, PASSWORD, HOST, PORT, DB_NAME
from models import create_tables
import configparser


def create_db():
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

# функция возвращает True, если пользователю есть 18 и он добавлен в базу

def add_user(user_info):
    res = session.query(Users).where(Users.vk_id == user_info['vk_id'])
    # Проверка 18+
    if int(user_info['age']) < 18:
        return False
    # Проверка на существование в базе
    elif len(res.all()) > 0:
        return False
    else:
        session.add(
            Users(vk_id=user_info['vk_id'],
                name=user_info['name'],
                surname=user_info['surname'],
                age=user_info['age'],
                sex=user_info['sex'],
                city=user_info['city'],
                link_to_profile=user_info["link_to_profile"]))
        session.commit()
        return True


if __name__ == '__main__':
    engine = create_db()
    create_tables(engine)
