import datetime
import uuid

import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from const import GROUP_TOKEN, USER_TOKEN
from db import register_bot_user, create_row_in_search_table, \
    create_row_in_bot_search_table, update_bot_and_search, \
    check_if_update_needs, get_random_search_row, get_search_ids, \
    get_favourite_list, add_to_db_favourite_list, \
    remove_in_db_favourite_list, add_to_db_black_list, get_black_list, \
    remove_in_db_black_list, check_if_user_in_black_list, \
    check_if_user_in_favourite_list, get_profile_by_search_id


class Vkinder:
    def __init__(self, group_token):
        self.vk_session = vk_api.VkApi(token=group_token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)
        self.db_update_percent = 100  # Отсчет от 100 до 0 при заполнении базы
        self.register = False  # Флаг регистрации в базе
        self.state = None  # Флаг нахождения бота в конкретном меню
        self.first_search = None  # Флаг первого поиска после заполнения базы

    def send_message(self, user_id, message, keyboard=None):
        """Отправляем сообщение в чат"""
        random_id = uuid.uuid4().int
        if keyboard is not None:
            self.vk.messages.send(user_id=user_id, message=message,
                                  random_id=random_id,
                                  keyboard=keyboard.get_keyboard())
        else:
            self.vk.messages.send(user_id=user_id, message=message,
                                  random_id=random_id)

    def send_photo_message(self, user_id, photo):
        """Отправляем фото в чат"""
        random_id = uuid.uuid4().int
        self.vk.messages.send(user_id=user_id, random_id=random_id,
                              attachment=photo)

    def check_age(self, user_id):
        """Получаем возраст пользователя"""
        fields = ['sex', 'city', 'bdate']
        bot_info = self.vk.users.get(user_ids=user_id, fields=fields)[0]
        bot_bdate = bot_info['bdate']
        user_age = self._calculate_age(bot_bdate)
        return user_age

    def get_bot_info(self, user_id, keyboard=None):
        """Получаем информацию из анкеты пользователя бота"""
        fields = ['sex', 'city', 'bdate']
        bot_info = self.vk.users.get(user_ids=user_id, fields=fields)[0]
        self.user_id = bot_info['id']
        bot_first_name = bot_info['first_name']
        bot_last_name = bot_info['last_name']
        self.bot_sex = bot_info['sex']
        bot_sex_str = "мужской" if self.bot_sex == 2 else "женский" \
            if self.bot_sex == 1 else "не указан"
        self.bot_city = bot_info['city']['title']
        self.bot_city_id = bot_info['city']['id']
        self.bot_bdate = bot_info['bdate']
        self.user_age = self._calculate_age(self.bot_bdate)
        register_bot_user(self.bot_sex, self.user_age, self.bot_city_id,
                          self.user_id, datetime.datetime.now())
        welcome_message = ("Привет. Я могу подобрать вам пару на основании "
                           f"ваших анкетных данных:\n{bot_first_name} "
                           f"{bot_last_name}\nПол: {bot_sex_str}\nГород: "
                           f"{self.bot_city}\nВозраст: "
                           f"{self.user_age}\nЧтобы начать "
                           "нажмите на кнопку Найти")
        self.send_message(bot_info['id'], welcome_message, keyboard)

    def get_keyboard(self, response):
        """Получаем клавиатуру в зависимости от нахождения в конкретном меню"""
        keyboard = VkKeyboard()
        if self.state is None:
            keyboard.add_button("Найти", color=VkKeyboardColor.PRIMARY)
        elif response == 'избранные(меню)':
            keyboard.add_button("Добавить в избранные",
                                color=VkKeyboardColor.POSITIVE)
            keyboard.add_button("Удалить из избранных",
                                color=VkKeyboardColor.NEGATIVE)
            keyboard.add_line()
            keyboard.add_button("Список избранных",
                                color=VkKeyboardColor.PRIMARY)
            keyboard.add_button('Назад', color=VkKeyboardColor.SECONDARY)
        elif response == 'черный список(меню)':
            keyboard.add_button("Добавить в черный список",
                                color=VkKeyboardColor.POSITIVE)
            keyboard.add_button("Удалить из черного списка",
                                color=VkKeyboardColor.NEGATIVE)
            keyboard.add_line()
            keyboard.add_button("Черный список", color=VkKeyboardColor.PRIMARY)
            keyboard.add_button('Назад', color=VkKeyboardColor.SECONDARY)
        else:
            keyboard.add_button('Найти', color=VkKeyboardColor.PRIMARY)
            keyboard.add_button('Лайк(поставить/убрать)',
                                color=VkKeyboardColor.PRIMARY)
            keyboard.add_line()
            keyboard.add_button('Избранные(меню)',
                                color=VkKeyboardColor.PRIMARY)
            keyboard.add_button('Черный список(меню)',
                                color=VkKeyboardColor.PRIMARY)
        return keyboard

    @staticmethod
    def _calculate_age(bdate):
        """Подсчитываем возраст на основании предоставляемой даты
        из анкеты пользователя бота"""
        if bdate:
            bdate = datetime.datetime.strptime(bdate, "%d.%m.%Y")
            today = datetime.date.today()
            age = today.year - bdate.year - ((today.month, today.day) <
                                             (bdate.month, bdate.day))
            return age
        else:
            return 0

    @staticmethod
    def _get_vk_api_for_user_token():
        vk_session = vk_api.VkApi(token=USER_TOKEN)
        vk = vk_session.get_api()
        return vk

    def get_top_profile_photos(self, user_id):
        """Делаем API запрос для получения фото из профиля анкеты"""
        vk = self._get_vk_api_for_user_token()
        try:
            photos_response = vk.photos.get(owner_id=user_id,
                                            album_id='profile', rev=1,
                                            count=100, extended=1)
        except vk_api.exceptions.ApiError:
            return None
        return self.get_top_photos(photos_response)

    def get_top_tagged_photos(self, user_id):
        """Делаем API запрос для получения фото
        на которых отмечен пользователь"""
        vk = self._get_vk_api_for_user_token()
        try:
            photos_response = vk.photos.getUserPhotos(
                user_id=user_id, count=1000, extended=1)
        except vk_api.exceptions.ApiError:
            return None
        return self.get_top_photos(photos_response)

    @staticmethod
    def get_top_photos(photos_response):
        """Получаем URL трех фото, имеющие наибольшее кол-во лайков"""
        photos = photos_response['items']
        sorted_photos = sorted(photos, key=lambda x: -x['likes']['count'])
        top_photos = sorted_photos[:3]
        top_url_photos = [el['sizes'][-1]['url'] for el in top_photos]
        return top_url_photos

    def add_to_favourite_list(self, user_id, search_id):
        """Добавляем анкету в список избранных"""
        if check_if_user_in_black_list(search_id):
            message = ('Невозможно добавить пользователя в список избранных '
                       'пока он присутствует в черном списке')
            self.send_message(user_id, message=message)
            return
        favourite_list = add_to_db_favourite_list(search_id)
        if favourite_list is None:
            message = ('Прежде чем кого-то добавить в список избранных, '
                       'вам нужно сперва начать поиск пользователя')
        elif favourite_list:
            message = 'Пользователь добавлен в список избранных'
        elif favourite_list is False:
            message = 'Пользователь уже был ранее добавлен в список избранных'
        self.send_message(user_id, message=message)

    def show_favourite_list(self, user_id):
        """Отображаем анкеты в списке избранных"""
        favourite_list = get_favourite_list()
        if len(favourite_list) == 0:
            message = ('В списке избранных никого нет.\n\n')
            self.send_message(user_id, message=message)
        else:
            message = (f'В списке избранных находятся {len(favourite_list)} '
                       'анкет(а/ы).\n\n')
            self.send_message(user_id, message=message)
            for el in favourite_list:
                self.show_search_result(user_id, el)

    def ask_for_favourite_id_to_remove(self, user_id):
        """Спрашиваем какую анкету мы хотим удалить из списка избранных"""
        if len(get_favourite_list()) == 0:
            message = ('Вы не можете кого-либо удалить, '
                       'т.к. список избранных пуст')
        else:
            message = ('Напишите цифрами id анкеты пользователя, '
                       'которого вы хотите удалить из списка избранных')
        self.send_message(user_id, message)

    def remove_from_favourite_list(self, user_id, profile):
        """Удаляем анкету из списка избранных"""
        favourite_list = remove_in_db_favourite_list(profile)
        if favourite_list:
            message = f'Анкета с id {profile} удалена из списка избранных'
        elif favourite_list is False:
            message = ('Вы не можете кого-либо удалить, '
                       'т.к. список избранных пуст')
        else:
            message = f'Анкета с id {profile} не обнаружена в списке избранных'
        self.send_message(user_id, message=message)

    def add_to_black_list(self, user_id, search_id):
        """Добавляем анкету в черный список"""
        if check_if_user_in_favourite_list(search_id):
            message = ('Невозможно добавить пользователя в черный список '
                       'пока он присутствует в списке избранных')
            self.send_message(user_id, message=message)
            return
        black_list = add_to_db_black_list(search_id)
        if black_list is None:
            message = ('Прежде чем кого-то добавить в черный список, '
                       'вам нужно сперва начать поиск пользователя')
        elif black_list:
            message = 'Пользователь добавлен в черный список'
        elif black_list is False:
            message = 'Пользователь уже был ранее добавлен в черный список'
        self.send_message(user_id, message=message)

    def show_black_list(self, user_id):
        """Отображаем анкеты в черном списке"""
        black_list = get_black_list()
        if len(black_list) == 0:
            message = ('В черном списке никого нет.\n\n')
            self.send_message(user_id, message=message)
        else:
            message = (f'В черном списке находятся {len(black_list)} '
                       'анкет(а/ы).\n\n')
            self.send_message(user_id, message=message)
            for el in black_list:
                self.show_search_result(user_id, el)

    def ask_for_black_id_to_remove(self, user_id):
        """Спрашиваем какую анкету мы хотим удалить из черного списка"""
        if len(get_black_list()) == 0:
            message = ('Вы не можете кого-либо удалить, '
                       'т.к. черный список пуст')
        else:
            message = ('Напишите цифрами id анкеты пользователя, '
                       'которого вы хотите удалить из черного списка')
        self.send_message(user_id, message)

    def remove_from_black_list(self, user_id, profile):
        """Удаляем анкету из черного списка"""
        if remove_in_db_black_list(profile):
            message = f'Анкета с id {profile} удалена из черного списка'
        elif remove_in_db_black_list(profile) is False:
            message = 'Вы не можете кого-либо удалить, т.к. черный список пуст'
        else:
            message = f'Анкета с id {profile} не обнаружена в черном списке'
        self.send_message(user_id, message=message)

    def _get_item_id_by_profile_url(self, vk, profile, url):
        """Получаем ID фото из профиля анкеты"""
        try:
            photos = vk.photos.get(owner_id=profile, album_id='profile', rev=1,
                                   count=1000, extended=1)
        except vk_api.exceptions.ApiError:
            return None
        items = photos['items']
        for item in items:
            if item['sizes'][-1]['url'].split('userapi.com')[1] == \
                    url.split('userapi.com')[1]:
                return item['id']

    def _get_item_id_by_tagged_url(self, vk, profile, url):
        """Получаем ID фото на которой отмечен пользователь"""
        try:
            photos = vk.photos.getUserPhotos(user_id=profile, count=1000,
                                             extended=1)
        except vk_api.exceptions.ApiError:
            return None
        items = photos['items']
        for item in items:
            if item['sizes'][-1]['url'].split('userapi.com')[1] == \
                    url.split('userapi.com')[1]:
                return item['id']

    def _add_like(self, vk, profile, item_id):
        """Добавляем/убираем лайк фото по ID фотографии"""
        islike = vk.likes.isLiked(owner_id=profile, type='photo',
                                  item_id=item_id)
        if islike['liked'] == 0:
            vk.likes.add(owner_id=profile, type='photo',
                         item_id=item_id)
            message = f'Поставлен лайк фотографии с номером {response}'
        else:
            vk.likes.delete(owner_id=profile, type='photo', item_id=item_id)
            message = f'Снят лайк с фотографии с номером {response}'
        return message

    def input_like_number(self, users_search, photos_search, response):
        """Обрабатывает введенный пользователем номер фото с целью определить
        относится введенный номер к фотографиям из профиля анкеты или
        к фотографиям на которых пользователя отметили"""
        vk = self._get_vk_api_for_user_token()
        profile = get_profile_by_search_id(users_search)
        response = int(response)
        url = photos_search.get(response)
        if 1 <= response <= 3 and response in range(len(photos_search) + 1):
            item_id = self._get_item_id_by_profile_url(vk, profile, url)
            try:
                message = self._add_like(vk, profile, item_id)
            except vk_api.exceptions.ApiError:
                message = ('Не удалось поставить лайк фотографии '
                           'из профиля анкеты, попробуйте позже')
        elif 4 <= response <= 6 and response in range(len(photos_search) + 1):
            item_id = self._get_item_id_by_tagged_url(vk, profile, url)
            try:
                message = self._add_like(vk, profile, item_id)
            except vk_api.exceptions.ApiError:
                message = ('Не удалось поставить лайк, т.к. либо пользователь '
                           'ограничил доступ к данному отмеченному фото '
                           'настройками приватности, либо возникла ошибка при '
                           'работе с VK API')
        vkinder.send_message(event.user_id, message,
                             keyboard=self.get_keyboard(response))

    def search_button_response(self, user_id):
        """Определение события при нажатии на кнопку поиска - либо начинается
        заполнение БД, либо если БД заполнена, то выдача результата поиска"""
        if check_if_update_needs(user_id) or len(get_search_ids()) == 0:
            self.db_update_percent = 100
            self.state = 'main_menu'
            self.first_search = None
            self.search_button_update_response(user_id)
        else:
            search_row = get_random_search_row()
            return self.show_search_result(user_id, search_row)

    def show_search_result(self, user_id, search_row):
        """Отображаем результат среди найденных анкет пользователей в чат"""
        message = ''
        photos_urls = {}
        for idx, el in enumerate(search_row[4:]):
            if el is not None and el.startswith('https://'):
                photos_urls.setdefault(idx + 1, el)
        for el in search_row[1:]:
            if isinstance(el, str) and not el.startswith('https://'):
                message += f'{el} '
            elif isinstance(el, int):
                message = message.strip()
                message += f'\nvk.com/id{el}\n'
        self.send_message(user_id, message=message)

        message = 'Фото из профиля пользователя:\n'
        self.send_message(user_id, message=message)
        for num, url in photos_urls.items():
            if num <= 3 and url is not None:
                message = f'{num}:'
                self.send_message(user_id, message=message)
                self.send_photo_message(user_id, url)
        if len(photos_urls) > 3:
            message = 'Фото на которых отмечен пользователь:\n'
            self.send_message(user_id, message=message)
            for num, url in photos_urls.items():
                if num > 3 and url is not None:
                    message = f'{num}:'
                    self.send_message(user_id, message=message)
                    self.send_photo_message(user_id, url)
        return search_row[0], photos_urls

    def _get_days_in_month(self, month):
        """Определяем сколько дней не в текущем месяце"""
        return range(1, self.calendar[month] + 1)

    def search_button_update_response(self, user_id):
        """Ищем пользователей с подходящими данными"""
        update_bot_and_search(sex=self.bot_sex, age=self.user_age,
                              city_id=self.bot_city_id, profile=user_id)
        vk = self._get_vk_api_for_user_token()
        # Определяем пол противоположный полу пользователя бота
        if self.bot_sex == 1:
            opposite_sex = 2
        elif self.bot_sex == 2:
            opposite_sex = 1
        else:
            opposite_sex = 3

        self.current_year = datetime.datetime.now().date().year
        self.current_month = datetime.datetime.now().date().month
        self.current_day = datetime.datetime.now().date().day
        self.birth_year = self.bot_bdate.split('.')[-1]
        self.next_birth_year = int(self.birth_year) + 1
        self.calendar = {
            1: 31,
            2: 29 if self.current_year % 4 == 0 else 28,
            3: 31,
            4: 30,
            5: 31,
            6: 30,
            7: 31,
            8: 31,
            9: 30,
            10: 31,
            11: 30,
            12: 31
        }

        message = 'Подождите, пожалуйста, идет заполнение базы ' \
                  'найденными анкетами'
        self.send_message(user_id, message)

        # Ниже идет обход ограничения VK API по выдаче результата поиска
        # не более 1000 элементов. Применяется итерирование по дням года
        # в которых возраст пользователя бота равен возрасту искомого
        # пользователя, т.е. если пользователь, например, родился, 15.04.1990,
        # то итерация идет по периоду 15.04.1990-14.04.1991

        commmon_params = {'sex': opposite_sex, 'city': self.bot_city_id,
                          'has_photo': 1, 'count': 1000}

        # От текущего дня до конца текущего месяца в год рождения
        remaining_days_in_current_month = range(
            self.current_day + 1, self.calendar[self.current_month] + 1)
        for day in remaining_days_in_current_month:
            users_search = vk.users.search(
                **commmon_params, birth_year=self.birth_year,
                birth_month=self.current_month, birth_day=day)
            self.parse_users_search(user_id, users_search)

        # От первого дня начала следующего месяца до конца года рождения
        remaining_months_in_current_year = range(self.current_month + 1,
                                                 len(self.calendar) + 1)
        for month in remaining_months_in_current_year:
            days_in_month = self._get_days_in_month(month)
            for day in days_in_month:
                users_search = vk.users.search(
                    **commmon_params, birth_year=self.birth_year,
                    birth_month=month, birth_day=day)
                self.parse_users_search(user_id, users_search)

        # От 1 января следующего года после года рождения
        # до начала текущего месяца
        remaining_months_next_year = range(1, self.current_month)
        for month in remaining_months_next_year:
            days_in_month = self._get_days_in_month(month)
            for day in days_in_month:
                users_search = vk.users.search(
                    **commmon_params, birth_year=self.next_birth_year,
                    birth_month=month, birth_day=day)
                self.parse_users_search(user_id, users_search)

        # Дни оставшиеся в текущем месяце до текущего дня
        # в следующем году после года рождения
        short_of_days_in_current_month = range(1, self.current_day + 1)
        for day in short_of_days_in_current_month:
            users_search = vk.users.search(
                **commmon_params, birth_year=self.next_birth_year,
                birth_month=self.current_month, birth_day=day)
            self.parse_users_search(user_id, users_search)

        message = ('Закончилось заполнение базы найденными анкетами.\n'
                   f'В базе находится {len(get_search_ids())} анкет(а/ы).\n'
                   'Можете начинать поиск')
        self.send_message(user_id, message,
                          keyboard=self.get_keyboard(response))

    def parse_users_search(self, user_id, users_search):
        """Заполняем/обновляем БД найденными подходящими анкетами"""
        # Отсеиваем те анкеты, которые закрыты
        users_search_not_closed = []
        for el in users_search['items']:
            if el['is_closed'] is False:
                users_search_not_closed.append(el)
        # Найденные анкеты добавляем в БД
        count_search_ids_before_adding = len(get_search_ids())
        for el in users_search_not_closed:
            first_name = el['first_name']
            last_name = el['last_name']
            profile = el['id']
            top_url_profile_photos = self.get_top_profile_photos(profile)
            top_url_tagged_photos = self.get_top_tagged_photos(profile)
            # Если в профиле всего одно фото, которое не кликабельно,
            # то получить ссылку на фото не получится,
            # поэтому такую анкету пропускаем
            if not top_url_profile_photos:
                continue
            search_id = create_row_in_search_table(
                first_name, last_name, profile, top_url_profile_photos,
                top_url_tagged_photos)
            create_row_in_bot_search_table(search_id, user_id)
        # Ниже 0.274 это результат деления 100 процентов на 365 дней в году
        self.db_update_percent -= 0.274
        count_search_ids_after_adding = len(get_search_ids())
        if count_search_ids_after_adding != count_search_ids_before_adding \
                and count_search_ids_after_adding % 5 == 0:
            message = (f'В базe уже есть {count_search_ids_after_adding} '
                       f'найденных(ая) анкет(а/ы).\nОсталось '
                       f'{self.db_update_percent:.1f}% '
                       'до конца заполнения базы.')
            self.send_message(user_id, message)


if __name__ == '__main__':
    vkinder = Vkinder(GROUP_TOKEN)
    for event in vkinder.longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            response = event.text.lower()
            if response and vkinder.register is False:
                if vkinder.check_age(event.user_id) < 18:
                    message = ('Вы не можете использовать бота, '
                               'т.к. ваш возраст менее 18 лет')
                    vkinder.send_message(event.user_id, message)
                else:
                    vkinder.register = True
                    keyboard = vkinder.get_keyboard(response)
                    vkinder.get_bot_info(event.user_id, keyboard)

            elif response == 'найти':
                search = vkinder.search_button_response(event.user_id)
                if search is None:
                    continue
                else:
                    vkinder.state = 'main_menu'
                    vkinder.first_search = True
                    users_search = search[0]
                    photos_search = search[1]

            elif response == 'лайк(поставить/убрать)' and vkinder.state \
                    and not vkinder.first_search:
                vkinder.state = 'like'
                message = ('Вы должны сначала начать поиск '
                           'прежде чем ставить лайк')
                vkinder.send_message(event.user_id, message)
            elif response == 'лайк(поставить/убрать)' and vkinder.state \
                    and vkinder.first_search:
                vkinder.state = 'like'
                message = 'Из предложенных фото напишите цифрой ' \
                          'какой фотографии вы хотите поставить/убрать лайк'
                vkinder.send_message(event.user_id, message)

            elif response == 'избранные(меню)' and not vkinder.first_search:
                message = 'Вы должны сначала начать поиск ' \
                          'прежде чем открывать меню избранных'
                keyboard = vkinder.get_keyboard(response='найти')
                vkinder.send_message(event.user_id, message, keyboard)
            elif response == 'избранные(меню)' and \
                    (vkinder.state == 'main_menu' or vkinder.state == 'like') \
                    and vkinder.first_search:
                vkinder.state = 'favourite_list'
                message = 'Вы в меню избранных'
                keyboard = vkinder.get_keyboard(response)
                vkinder.send_message(event.user_id, message, keyboard)
            elif response == 'добавить в избранные' and \
                    vkinder.state == 'favourite_list':
                vkinder.add_to_favourite_list(event.user_id, users_search)
            elif response == 'удалить из избранных' and \
                    vkinder.state == 'favourite_list':
                vkinder.ask_for_favourite_id_to_remove(event.user_id)
            elif response == 'список избранных' and \
                    vkinder.state == 'favourite_list':
                vkinder.show_favourite_list(event.user_id)

            elif response == 'черный список(меню)' and not \
                    vkinder.first_search:
                keyboard = vkinder.get_keyboard(response='найти')
                message = 'Вы должны сначала начать поиск ' \
                          'прежде чем открывать меню черного списка'
                vkinder.send_message(event.user_id, message, keyboard)
            elif response == 'черный список(меню)' and \
                    (vkinder.state == 'main_menu' or vkinder.state == 'like') \
                    and vkinder.first_search:
                vkinder.state = 'black_list'
                message = 'Вы в меню черного списка'
                keyboard = vkinder.get_keyboard(response)
                vkinder.send_message(event.user_id, message, keyboard)
            elif response == 'добавить в черный список' and \
                    vkinder.state == 'black_list':
                vkinder.add_to_black_list(event.user_id, users_search)
            elif response == 'удалить из черного списка' and \
                    vkinder.state == 'black_list':
                vkinder.ask_for_black_id_to_remove(event.user_id)
            elif response == 'черный список' and vkinder.state == 'black_list':
                vkinder.show_black_list(event.user_id)

            elif response.isdigit() and vkinder.state != 'main_menu':
                if vkinder.state == 'favourite_list':
                    vkinder.remove_from_favourite_list(
                        event.user_id, int(response))
                elif vkinder.state == 'black_list':
                    vkinder.remove_from_black_list(
                        event.user_id, int(response))
                elif vkinder.state == 'like' and int(response) in \
                        range(len(photos_search) + 1):
                    vkinder.input_like_number(users_search, photos_search,
                                              response)
                elif vkinder.state == 'like' and int(response) not in \
                        range(len(photos_search) + 1):
                    message = 'Вы указали неверный номер фотографии. ' \
                              'Нажмите на кнопку Лайк и попробуйте снова'
                    keyboard = vkinder.get_keyboard(response)
                    vkinder.send_message(event.user_id, message, keyboard)
                    vkinder.state = 'main_menu'

            elif response == 'назад':
                vkinder.state = 'main_menu'
                message = 'Вы в главном меню'
                keyboard = vkinder.get_keyboard(response)
                vkinder.send_message(event.user_id, message, keyboard)

            else:
                vkinder.send_message(event.user_id, 'Извините, не понял вас')
