import datetime
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import uuid

from GitHub.VKinder.db import register_bot_user
from const import GROUP_TOKEN, USER_TOKEN
from db import create_vk_users_rows


class Vkinder:
    def __init__(self, group_token):
        self.vk_session = vk_api.VkApi(token=group_token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)

    def write_msg(self, user_id, message, keyboard=None):
        random_id = uuid.uuid4().int & (1 << 32) - 1
        if keyboard is not None:
            self.vk.messages.send(user_id=user_id, message=message, random_id=random_id, keyboard=keyboard.get_keyboard())
        else:
            self.vk.messages.send(user_id=user_id, message=message, random_id=random_id)

    def get_user_info(self, user_id):
        fields = ['sex', 'city', 'relation', 'bdate']
        user_info = self.vk.users.get(user_ids=user_id, fields=fields)[0]
        return user_info

    def user_info_message(self, user_info, keyboard=None):
        self.user_id = user_info.get('id', '')
        user_name = user_info.get('first_name', '')
        user_last_name = user_info.get('last_name', '')
        self.user_sex = user_info.get('sex', '')
        user_sex_str = "мужской" if self.user_sex == 2 else "женский" if self.user_sex == 1 else "не указан"
        self.user_city = user_info.get('city', {}).get('title', '')
        self.user_city_id = user_info.get('city', {}).get('id', '')
        user_relation = user_info.get('relation', '')
        user_bdate = user_info.get('bdate', '')
        self.user_age = self.calculate_age(user_bdate)

        if user_relation is not None:
            relation_mapping = {
                1: 'не женат/не замужем',
                2: 'есть друг/есть подруга',
                3: 'помолвлен/помолвлена',
                4: 'женат/замужем',
                5: 'всё сложно',
                6: 'в активном поиске',
                7: 'влюблён/влюблена',
                8: 'в гражданском браке'
            }
            user_relation_str = relation_mapping.get(user_relation, "не указано")
        else:
            user_relation_str = "не указано"
        register_bot_user(self.user_sex, self.user_age, self.user_city_id, self.user_id, datetime.datetime.now())  # БД
        full_message = f"Привет. Как я могу помочь?\n\n{user_name} {user_last_name}, пол: {user_sex_str}, " \
                       f"город: {self.user_city}, семейное положение: {user_relation_str}, возраст: {self.user_age}"
        self.write_msg(user_info['id'], full_message, keyboard)

    def get_keyboard(self):
        # Создание клавиатуры
        keyboard = VkKeyboard()
        keyboard.add_button('Поиск', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Избранные контакты', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Чёрный список', color=VkKeyboardColor.POSITIVE)
        return keyboard

    def calculate_age(self, bdate):
        if bdate:
            bdate = datetime.datetime.strptime(bdate, "%d.%m.%Y")
            today = datetime.date.today()
            age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
            return age
        else:
            return "не указано"

    def get_top_liked_photos(self, user_id):
        vk_session = vk_api.VkApi(token=USER_TOKEN)
        vk = vk_session.get_api()
        photos_response = vk.photos.get(owner_id=user_id, album_id='profile', rev=1, count=100, extended=1)
        photos = photos_response['items']
        # Сортировать фотографии по количеству лайков
        sorted_photos = sorted(photos, key=lambda x: -x['likes']['count'])
        # Вернуть топ-3 фотографии
        top_photos = sorted_photos[:3]
        top_url_photos = [el['sizes'][-1]['url'] for el in top_photos]
        return top_url_photos

    def favorite_contacts_button_response(self, user_id):
        # Получаем ID пользователя
        user_id = user_id

        # Получаем топ-3 фотографии пользователя
        photos = self.get_top_liked_photos(user_id)

        # Отправляем фотографии пользователю
        if photos:
            message = "Ваши избранные контакты:"
            self.write_msg(user_id, message)
            for photo in photos:
                self.send_photo(user_id, photo)
        else:
            message = "У вас нет избранных контактов"
            self.write_msg(user_id, message)

    def send_photo(self, user_id, photos):
        # Отправить фотографию пользователю
        for photo in photos:
            random_id = uuid.uuid4().int & (1 << 32) - 1
            self.vk.messages.send(user_id=user_id, random_id=random_id, attachment=photo)

    def search_button_response(self, user_id):
        vk_session = vk_api.VkApi(token=USER_TOKEN)
        vk = vk_session.get_api()

        if self.user_sex == 1:
            opposite_sex = 2
        elif self.user_sex == 2:
            opposite_sex = 1
        else:
            opposite_sex = 3

        users_search = vk.users.search(sex=opposite_sex, age_from=self.user_age, age_to=self.user_age, city=self.user_city_id, has_photo=1, count=1000)
        users_search_not_closed = []
        for el in users_search['items']:
            if el['is_closed'] is False:
                users_search_not_closed.append(el)

        count_users = len(users_search_not_closed)
        for el in users_search_not_closed:
            count_users -= 1
            first_name = el['first_name']
            last_name = el['last_name']
            vk_id = el['id']
            top_url_photos = self.get_top_liked_photos(vk_id)
            create_vk_users_rows(first_name, last_name, vk_id, top_url_photos)
            if count_users == 0:
                message = f'Закончилось заполнение локальной БД пользователями ВК'
                self.write_msg(user_id, message)
            elif count_users % 10 == 0:
                message = f'Подождите, пожалуйста, идет заполнение локальной БД пользователями ВК. Осталось {count_users} пользователей'
                self.write_msg(user_id, message)


if __name__ == '__main__':
    vkinder = Vkinder(GROUP_TOKEN)
    for event in vkinder.longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            response = event.text.lower()
            if response in ['привет', 'hi', 'start']:
                user_info = vkinder.get_user_info(event.user_id)
                keyboard = vkinder.get_keyboard()
                vkinder.user_info_message(user_info, keyboard)
            elif response == 'поиск':
                users_search = vkinder.search_button_response(event.user_id)
            elif response == 'избранные контакты':
                vkinder.favorite_contacts_button_response(event.user_id)
            else:
                user_info = vkinder.get_user_info(event.user_id)
                vkinder.write_msg(event.user_id, 'Извините, не понял вас')
