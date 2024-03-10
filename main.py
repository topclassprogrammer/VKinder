import datetime
import uuid

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from const import GROUP_TOKEN, USER_TOKEN
from db import register_bot_user, create_row_in_search_table, create_row_in_bot_search_table, \
    update_bot_and_search, check_if_update_needs, get_random_search_row, \
    get_search_ids, get_favourite_list, add_to_db_favourite_list, \
    remove_in_db_favourite_list, add_to_db_black_list, get_black_list, \
    remove_in_db_black_list, check_if_user_in_black_list, check_if_user_in_favourite_list


class Vkinder:
    def __init__(self, group_token):
        self.vk_session = vk_api.VkApi(token=group_token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)

    def send_message(self, user_id, message, keyboard=None):
        """Отправляем сообщение в чат"""
        random_id = uuid.uuid4().int
        if keyboard is not None:
            self.vk.messages.send(user_id=user_id, message=message, random_id=random_id,
                                  keyboard=keyboard.get_keyboard())
        else:
            self.vk.messages.send(user_id=user_id, message=message, random_id=random_id)

    def send_photo_message(self, user_id, photos):
        """Отправляем фото в чат"""
        for photo in photos:
            random_id = uuid.uuid4().int
            self.vk.messages.send(user_id=user_id, random_id=random_id, attachment=photo)

    def get_bot_info(self, user_id, keyboard=None):
        """Получаем информацию из анкеты пользователя бота"""
        fields = ['sex', 'city', 'relation', 'bdate']
        bot_info = self.vk.users.get(user_ids=user_id, fields=fields)[0]
        self.user_id = bot_info.get('id', '')
        bot_first_name = bot_info.get('first_name', '')
        bot_last_name = bot_info.get('last_name', '')
        self.bot_sex = bot_info.get('sex', '')
        bot_sex_str = "мужской" if self.bot_sex == 2 else "женский" if self.bot_sex == 1 else "не указан"
        self.bot_city = bot_info.get('city', {}).get('title', '')
        self.bot_city_id = bot_info.get('city', {}).get('id', '')
        bot_bdate = bot_info.get('bdate', '')
        self.user_age = self.calculate_age(bot_bdate)
        register_bot_user(self.bot_sex, self.user_age, self.bot_city_id, self.user_id, datetime.datetime.now())
        welcome_message = f"Привет. Я могу подобрать вам пару на основании ваших анкетных данных:\n" \
                       f"{bot_first_name} {bot_last_name}\nПол: {bot_sex_str}\n" \
                       f"Город: {self.bot_city}\nВозраст: {self.user_age}\nЧтобы начать нажмите на кнопку Найти"
        self.send_message(bot_info['id'], welcome_message, keyboard)

    @staticmethod
    def get_keyboard_for_main_menu():
        """Клавиатура в главном меню бота"""
        keyboard = VkKeyboard()
        keyboard.add_button('Найти', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Избранные(меню)', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Черный список(меню)', color=VkKeyboardColor.PRIMARY)
        return keyboard

    @staticmethod
    def get_keyboard_for_preferences(state):
        """Клавиатура в меню предпочтений бота"""
        keyboard = VkKeyboard()
        keyboard.add_button(f"Добавить в {'избранные' if state == 'favourite_list' else 'черный список'}",
                            color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(f"Удалить из {'избранных' if state == 'favourite_list' else 'черного списка'}",
                            color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Список избранных' if state == 'favourite_list' else 'Черный список',
                            color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Назад', color=VkKeyboardColor.SECONDARY)
        return keyboard

    @staticmethod
    def calculate_age(bdate):
        """Подсчитываем возраст на основании предоставляемой даты из анкеты пользователя бота"""
        if bdate:
            bdate = datetime.datetime.strptime(bdate, "%d.%m.%Y")
            today = datetime.date.today()
            age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
            return age
        else:
            return "не указано"

    @staticmethod
    def get_top_liked_photos(user_id):
        """Получаем URL трех фото из профиля анкеты, имеющие наибольшее кол-во лайков"""
        vk_session = vk_api.VkApi(token=USER_TOKEN)
        vk = vk_session.get_api()
        photos_response = vk.photos.get(owner_id=user_id, album_id='profile', rev=1, count=100, extended=1)
        photos = photos_response['items']
        sorted_photos = sorted(photos, key=lambda x: -x['likes']['count'])
        top_photos = sorted_photos[:3]
        top_url_photos = [el['sizes'][-1]['url'] for el in top_photos]
        return top_url_photos

    def add_to_favourite_list(self, user_id, search_id):
        """Добавляем анкету в список избранных"""
        if check_if_user_in_black_list(search_id):
            message = f'Невозможно добавить пользователя в список избранных пока он присутствует в черном списке'
        elif add_to_db_favourite_list(search_id):
            message = f'Пользователь добавлен в список избранных'
        else:
            message = f'Пользователь уже был ранее добавлен в список избранных'
        self.send_message(user_id, message=message)

    def show_favourite_list(self, user_id):
        """Отображаем анкеты в списке избранных"""
        favourite_list = get_favourite_list()
        message = f'В списке избранных находятся {len(favourite_list)} анкет(а/ы).\n\n'
        self.send_message(user_id, message=message)
        if len(favourite_list) != 0:
            for el in favourite_list:
                self.show_search_result(user_id, el)

    def ask_for_favourite_id_to_remove(self, user_id):
        """Справшиваем какую анкету мы хотим удалить из списка избранных"""
        message = 'Напишите цифрами id анкеты пользователя, которого вы хотите удалить из списка избранных'
        self.send_message(user_id, message)

    def remove_from_favourite_list(self, user_id, profile):
        """Удаляем анкету из списка избранных"""
        if remove_in_db_favourite_list(profile):
            message = f'Анкета с id {profile} удалена из списка избранных'
        else:
            message = f'Анкета с id {profile} не обнаружена в списке избранных'
        self.send_message(user_id, message=message)

    def add_to_black_list(self, user_id, search_id):
        """Добавляем анкету в черный список"""
        if check_if_user_in_favourite_list(search_id):
            message = f'Невозможно добавить пользователя в черный список пока он присутствует в списке избранных'
        elif add_to_db_black_list(search_id):
            message = f'Пользователь добавлен в черный список'
        else:
            message = f'Пользователь уже был ранее добавлен в черный список'
        self.send_message(user_id, message=message)

    def show_black_list(self, user_id):
        """Отображаем анкеты в черном списке"""
        black_list = get_black_list()
        message = f'В черном списке находятся {len(black_list)} анкет(а/ы).\n\n'
        self.send_message(user_id, message=message)
        if len(black_list) != 0:
            for el in black_list:
                self.show_search_result(user_id, el)

    def ask_for_black_id_to_remove(self, user_id):
        """Справшиваем какую анкету мы хотим удалить из черного списка"""
        message = 'Напишите цифрами id анкеты пользователя, которого вы хотите удалить из черного списка'
        self.send_message(user_id, message)

    def remove_from_black_list(self, user_id, profile):
        """Удаляем анкету из черного списка"""
        if remove_in_db_black_list(profile):
            message = f'Анкета с id {profile} удалена из черного списка'
        else:
            message = f'Анкета с id {profile} не обнаружена в черном списке'
        self.send_message(user_id, message=message)

    def search_button_response(self, user_id):
        """Оценка события при нажатии на кнопку поиска"""
        if check_if_update_needs(user_id) or len(get_search_ids()) == 0:
            self.search_button_update_response(user_id)
        else:
            search_row = get_random_search_row()
            return self.show_search_result(user_id, search_row)

    def show_search_result(self, user_id, search_row):
        """Отображаем результат среди найденных анкет пользователей в чат"""
        message = ''
        photos = []
        for el in search_row[1:]:
            if isinstance(el, str) and not el.startswith('https://'):
                message += f'{el} '
            elif isinstance(el, int):
                message = message.strip()
                message += f'\nvk.com/id{el}\n'
            # Проверяем случай, когда у пользователя меньше трех фото в профиле
            elif isinstance(el, str) and el.startswith('https://'):
                photos.append(el)
        self.send_message(user_id, message=message)
        self.send_photo_message(user_id, photos=photos)
        return search_row[0]

    def search_button_update_response(self, user_id):
        """Заполняем/обновляем БД найденными подходящими анкетами"""
        update_bot_and_search(sex=self.bot_sex, age=self.user_age, city_id=self.bot_city_id, profile=user_id)
        vk_session = vk_api.VkApi(token=USER_TOKEN)
        vk = vk_session.get_api()
        # Определяем пол противоположный полу пользователя бота
        if self.bot_sex == 1:
            opposite_sex = 2
        elif self.bot_sex == 2:
            opposite_sex = 1
        else:
            opposite_sex = 3

        users_search = vk.users.search(sex=opposite_sex, age_from=self.user_age, age_to=self.user_age,
                                       city=self.bot_city_id, has_photo=1, count=1000)
        # Отсеиваем те анкеты, которые закрыты
        users_search_not_closed = []
        for el in users_search['items']:
            if el['is_closed'] is False:
                users_search_not_closed.append(el)

        count_users = len(users_search_not_closed)
        message = 'Подождите, пожалуйста, идет заполнение локальной БД пользователями ВК'
        self.send_message(user_id, message)
        # Найденные анкеты добавляем в БД
        for el in users_search_not_closed:
            count_users -= 1
            first_name = el['first_name']
            last_name = el['last_name']
            profile = el['id']
            top_url_photos = self.get_top_liked_photos(profile)
            search_id = create_row_in_search_table(first_name, last_name, profile, top_url_photos)
            create_row_in_bot_search_table(search_id, user_id)
            if count_users == 0:
                message = f'Закончилось заполнение локальной БД пользователями ВК.\nМожно начинать поиск'
                self.send_message(user_id, message)
                self.search_button_response(user_id)
            elif count_users % 10 == 0:
                message = f'Осталось {count_users} пользователей'
                self.send_message(user_id, message)


if __name__ == '__main__':
    vkinder = Vkinder(GROUP_TOKEN)
    register = False
    for event in vkinder.longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            response = event.text.lower()
            welcome_message = ['привет', 'hi', 'hello', 'start', 'старт', 'начать']
            if response in welcome_message:
                if register is True:
                    message = 'Вы уже зарегистрированы'
                    vkinder.send_message(event.user_id, message)
                else:
                    register = True
                    vkinder.get_bot_info(event.user_id)
                    keyboard = vkinder.get_keyboard_for_main_menu()
            elif not register:
                message = 'Чтобы зарегистрироваться введите одну из следующих команд:\n' \
                          f'{", ".join(welcome_message)}'
                vkinder.send_message(event.user_id, message)

            elif response == 'найти' and register:
                users_search = vkinder.search_button_response(event.user_id)

            elif response == 'избранные(меню)' and register:
                state = 'favourite_list'
                message = 'Вы в меню избранных'
                keyboard = vkinder.get_keyboard_for_preferences(state)
                vkinder.send_message(event.user_id, message, keyboard)
            elif response == 'добавить в избранные':
                vkinder.add_to_favourite_list(event.user_id, users_search)
            elif response == 'удалить из избранных':
                vkinder.ask_for_favourite_id_to_remove(event.user_id)
            elif response == 'список избранных':
                vkinder.show_favourite_list(event.user_id)

            elif response == 'черный список(меню)' and register:
                state = 'black_list'
                message = 'Вы в меню черного списка'
                keyboard = vkinder.get_keyboard_for_preferences(state)
                vkinder.send_message(event.user_id, message, keyboard)
            elif response == 'добавить в черный список':
                vkinder.add_to_black_list(event.user_id, users_search)
            elif response == 'удалить из черного списка':
                vkinder.ask_for_black_id_to_remove(event.user_id)
            elif response == 'черный список':
                vkinder.show_black_list(event.user_id)

            elif response.isdigit():
                if state == 'favourite_list':
                    vkinder.remove_from_favourite_list(event.user_id, int(response))
                else:
                    vkinder.remove_from_black_list(event.user_id, int(response))

            elif response == 'назад':
                message = 'Вы в главном меню'
                keyboard = vkinder.get_keyboard_for_main_menu()
                vkinder.send_message(event.user_id, message, keyboard)
            else:
                vkinder.send_message(event.user_id, 'Извините, не понял вас')