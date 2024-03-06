import time, datetime
import vk_api, vk, random
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import re, requests
import bs4
import uuid
import token_vk


class Vkinder:
    def __init__(self, token_vk, app_token):
        self.app_token = app_token
        self.non_date = True
        self.vk_session = vk_api.VkApi(token=token_vk)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)

    def write_msg(self, user_id, message, keyboard=None):
        random_id = uuid.uuid4().int & (1 << 32) - 1
        if keyboard is not None:
            self.vk.messages.send(user_id=user_id, message=message, random_id=random_id, keyboard=keyboard.get_keyboard())
        else:
            self.vk.messages.send(user_id=user_id, message=message, random_id=random_id)

    def user_info_message(self, user_info, keyboard=None):
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

        full_message = f"Привет. Как я могу помочь?\n\n{user_name} {user_last_name}, пол: {user_sex_str}, " \
                       f"город: {self.user_city}, семейное положение: {user_relation_str}, возраст: {self.user_age}"
        self.write_msg(user_info['id'], full_message, keyboard)

    def get_user_info(self, user_id):
        fields = ['sex', 'city', 'relation', 'bdate']
        user_info = self.vk.users.get(user_ids=user_id, fields=fields)[0]
        return user_info

    def calculate_age(self, bdate):
        if bdate:
            bdate = datetime.datetime.strptime(bdate, "%d.%m.%Y")
            today = datetime.date.today()
            age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
            return age
        else:
            return "не указано"

    def get_keyboard(self):
        # Создание клавиатуры
        keyboard = VkKeyboard()
        keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранные контакты', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Чёрный список', color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_keyboard2(self):
        # Создание кнопок
        keyboard = VkKeyboard()
        keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранные контакты', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Чёрный список', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Лайк', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Дизлайк', color=VkKeyboardColor.NEGATIVE)
        return keyboard

    def send_photo(self, user_id, photos):
        # Отправить фотографию пользователю
        for photo in photos:
            random_id = uuid.uuid4().int & (1 << 32) - 1
            self.vk.messages.send(user_id=user_id, random_id=random_id, attachment=photo)


    def get_top_liked_photos(self, user_id):
        vk_session = vk_api.VkApi(token=self.app_token)
        vk = vk_session.get_api()
        photos_response = vk.photos.get(owner_id=user_id, album_id='profile', rev=1, count=100, extended=1)
        photos = photos_response['items']
        # Сортировать фотографии по количеству лайков
        sorted_photos = sorted(photos, key=lambda x: -x['likes']['count'])
        # Вернуть топ-3 фотографии
        top_photos = sorted_photos[:3]
        top_url_photos = [el['sizes'][-1]['url'] for el in top_photos]
        return top_url_photos

    def search_button_response(self, user_id):
        vk_session = vk_api.VkApi(token=self.app_token)
        vk = vk_session.get_api()

        if self.user_sex == 1:
            opposite_sex = 2
        elif self.user_sex == 2:
            opposite_sex = 1
        else:
            opposite_sex = 3

        while True:
            try:
                search_res = vk.users.search(sex=opposite_sex, age_from=self.user_age, age_to=self.user_age, city=self.user_city_id, has_photo=1, count=1000)
                random_id = random.randrange(len(search_res['items']))
                self.non_date = True
                # Выходим из цикла, если профиль не закрыт
                if search_res['items'][random_id]['is_closed'] is False:
                    break
            except vk_api.exceptions.ApiError:
                self.write_msg(user_id, 'Недостаточно данных в вашем профиле для поиска. Минимум необходимых данных: дата рождения, город проживания')
                self.non_date = False
                break

        if self.non_date:
            name = search_res['items'][random_id]['first_name']
            last_name = search_res['items'][random_id]['last_name']
            target_id = search_res['items'][random_id]['id']
            link_to_profile = 'vk.com/id' + str(target_id)
            message = f'{name} {last_name}\n{link_to_profile}'
            self.write_msg(user_id, message, self.get_keyboard2())
            top_url_photos = self.get_top_liked_photos(target_id)
            self.send_photo(user_id, top_url_photos)


if __name__ == '__main__':
    vkinder = Vkinder(token_vk.token_vk, token_vk.app_token)
    for event in vkinder.longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            response = event.text.lower()
            if response in ['привет', 'hi', 'start']:
                user_info = vkinder.get_user_info(event.user_id)
                keyboard = vkinder.get_keyboard()
                vkinder.user_info_message(user_info, keyboard)
            elif response == 'поиск':
                vkinder.search_button_response(event.user_id)
            elif response == 'избранные контакты':
                top_url_photos = vkinder.get_top_liked_photos(event.user_id)
                vkinder.send_photo(event.user_id, top_url_photos)
            else:
                user_info = vkinder.get_user_info(event.user_id)
                vkinder.write_msg(event.user_id, 'Извините, не понял вас')
