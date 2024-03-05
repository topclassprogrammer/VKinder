import sys

from sqlalchemy import create_engine, exc
from sqlalchemy_utils import database_exists, create_database

from const import PROTOCOL, USER, PASSWORD, HOST, PORT, DB_NAME
from models import create_tables


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

# Регистрация пользователя при условии, что пользователю есть 18 лет
def register_user(vk_id, name, surname, sex, age, city, link_to_profile):
    try:
        new_user = Users(vk_id=vk_id, name=name, surname=surname, sex=sex, age=age, city=city,
                         link_to_profile=link_to_profile)
        users_info = Users.get(vk_id)
        if users_info.age >= 18:
            session.add(new_user)
            session.commit()
            return True
    except (IntegrityError, InvalidRequestError):
        return False

# Проверка регистрации пользователя бота в БД
 def check_db_reg(id):
     current_user_id = session.query(Users).filter(vk_id=id).first()
     return current_user_id

# Проверка Userа в избранном
def check_db_elit(id):
    current_users_id = session.query(Users).filter_by(vk_id=id).first()

    all_users = session.query(Favorite_list).filter_by(uder_id=current_users_id.id).all()
    return all_users

# Проверка Userа в черном списке
def check_db_black(id):
    current_users_id = session.query(Users).filter_by(vk_id=id).first()
    all_users = session.query(Black_list).filter_by(user_id=current_users_id.id).all()
    return all_users

# Удаляет Userа из избранного
def delete_db_elit(id):
    current_user = session.query(Favorite_list).filter_by(vk_id=id).first()
    session.delete(current_user)
    session.commit()

# Удаляет Userа из черного списка
def delet_db_black(id):
    current_user = session.query(Black_list).filter_by(vk_id=id).first()
    session.delete(current_user)
    session.commit()
    
# Пишем сообщение пользователю
def write_msg(user_id, message, attachment=None):
    vk.method('messages.send',
              {'user_id': user_id,
               'message': message,
               'random_id': randrange(10 ** 7),
               'attachment': attachment})

# Добавление пользователя в черный список
def add_to_black_list(event_id, vk_id):
    try:
        new_user = Black_list(
            vk_id=vk_id
        )
        session.add(new_user)
        session.commit()
        write_msg(event_id,
                  'Пользователь заблокирован.')
        return True
    except (IntegrityError, InvalidRequestError):
        write_msg(event_id,
                  'Пользователь уже в черном списке.')
        return False


if __name__ == '__main__':
    engine = create_db()
    create_tables(engine)
