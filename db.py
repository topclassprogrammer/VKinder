import datetime
import sys

from sqlalchemy import create_engine, exc, insert
from sqlalchemy.exc import InvalidRequestError, IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from const import PROTOCOL, USER, PASSWORD, HOST, PORT, DB_NAME
from models import create_tables, VkUsers, VkBotUsers, BotUsers, BotUsersFavourites, Favourites, BotUsersBlackLists, BlackLists


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


# Вносим пользователя бота в БД (без returning и возврата BotUsers.bot_user_id)
def register_bot_user(sex, age, city_id, vk_id, table_update_time):
    new_user = BotUsers(sex=sex, age=age, city_id=city_id, vk_id=vk_id, table_update_time=table_update_time)
    if age >= 18:
        with Session() as session:
            session.add(new_user)
            session.commit()


# Проверка наличия пользователя бота в БД
def check_reg(vk_id):
    with Session() as session:
        vk_user_id = session.query(VkUsers.vk_user_id).filter(VkUsers.vk_user_id == vk_id).first()[0]
        return vk_user_id


# Получаем дату записи в таблице пользователя бота
def get_bot_user_update_time(vk_id):
    with Session() as session:
        bot_datetime = session.query(BotUsers.table_update_time).filter(BotUsers.vk_id == vk_id).first()
        if bot_datetime:
            return bot_datetime[0]


# Обновляем дату записи в таблице пользователя бота
def update_bot_data(sex, age, city, vk_id):
    bot_user_update_time = get_bot_user_update_time(vk_id)
    if bot_user_update_time:
        next_period = bot_user_update_time + datetime.timedelta(days=1.0)
        current_datetime = datetime.datetime.now()
        if next_period < current_datetime:
            with Session() as session:
                session.query(BotUsers).filter(BotUsers.vk_id == vk_id).update({'sex': sex, 'age': age, 'city': city, 'table_update_time': current_datetime})
                session.commit()


# Добавляем в БД записи о найденных пользователей ВК на основании информации из анкеты пользователя бота
def create_vk_users_rows(first_name, last_name, vk_id, top_url_photos):
    with Session() as session:
        vk_user_row = session.execute(insert(VkUsers).returning(VkUsers.vk_user_id), [{
            'first_name': first_name, 'last_name': last_name, 'vk_id': vk_id,
            'link_to_photo_1': top_url_photos[0],
            'link_to_photo_2': top_url_photos[1] if len(top_url_photos) > 1 else None,
            'link_to_photo_3': top_url_photos[2] if len(top_url_photos) > 2 else None,
            'table_update_time': datetime.datetime.now()}])
        session.commit()
        return vk_user_row.fetchone()[0]


# # Проверка пользователя в избранном
# def check_favourite_list(vk_id):
#     with Session() as session:
#         current_user_id = session.query(Users.vk_id).filter_by(vk_id=vk_id).first()[0]
#         all_users = session.query(Preferences.favourite_vk_id).filter_by(favourite_vk_id=vk_id).all()
#     return all_users
#
#
# # Проверка пользователя в черном списке
# def check_black_list(vk_id):
#     with Session() as session:
#         current_user_id = session.query(Users.vk_id).filter_by(vk_id=vk_id).first()[0]
#         all_users = session.query(Preferences.black_vk_id).filter_by(user_id=current_user_id.id).all()
#     return all_users
#
#
# # Удаляет Userа из избранного
# def delete_db_elit(id):
#     current_user = session.query(Favorite_list).filter_by(vk_id=id).first()
#     session.delete(current_user)
#     session.commit()
#
#
# # Удаляет Userа из черного списка
# def delet_db_black(ids):
#     current_user = session.query(Black_list).filter_by(vk_id=id).first()
#     session.delete(current_user)
#     session.commit()
#
#
# #8 Пишем сообщение пользователю
# def write_msg(user_id, message, attachment=None):
#     vk.method('messages.send',
#               {'user_id': user_id,
#                'message': message,
#                'random_id': randrange(10 ** 7),
#                'attachment': attachment})
#
#
# # Добавление пользователя в черный список
# def add_to_black_list(event_id, vk_id):
#     try:
#         new_user = Black_list(
#             vk_id=vk_id
#         )
#         session.add(new_user)
#         session.commit()
#         write_msg(event_id,
#                   'Пользователь заблокирован.')
#         return True
#     except (IntegrityError, InvalidRequestError):
#         write_msg(event_id,
#                   'Пользователь уже в черном списке.')
#         return False


engine = create_db()
create_tables(engine)
Session = sessionmaker(bind=engine)
