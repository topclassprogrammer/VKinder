import time, datetime
import vk_api, vk, random
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import re, requests
import bs4
import uuid
import token_vk


class Vkinder:
    def __init__(self, token_vk):
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
        user_sex = user_info.get('sex', '')
        user_sex_str = "мужской" if user_sex == 2 else "женский" if user_sex == 1 else "не указан"
        user_city = user_info.get('city', {}).get('title', '')
        user_relation = user_info.get('relation', '')
        user_bdate = user_info.get('bdate', '')
        user_age = self.calculate_age(user_bdate)

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
                       f"город: {user_city}, семейное положение: {user_relation_str}, возраст: {user_age}"
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
        keyboard.add_button('Поиск', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Избранные контакты', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Чёрный список', color=VkKeyboardColor.POSITIVE)
        return keyboard

    def search_button_response(self, user_id):
        message = "Напишите интересующий вас диапазон возраста, пол, город, в котором проживает человек и его семейное положение"
        self.write_msg(user_id, message)

    # def favorite_contacts_button_response(self, user_id):
    #     # Получаем ID пользователя
    #     user_id = user_id
    #
    #     # Получаем топ-3 фотографии пользователя
    #     photos = self.get_top_liked_photos(user_id)
    #
    #     # Отправляем фотографии пользователю
    #     if photos:
    #         message = "Ваши избранные контакты:"
    #         self.write_msg(user_id, message)
    #         for photo in photos:
    #             self.send_photo(user_id, photo)
    #     else:
    #         message = "У вас нет фотографий"
    #         self.write_msg(user_id, message)

    # def get_top_liked_photos(self, user_id):
    #     # Получить все фотографии пользователя через сообщество
    #     photos_response = self.vk.photos.get(owner_id=user_id, album_id='profile', rev=1, count=100)
    #     photos = photos_response['items']
    #
    #     # Сортировать фотографии по количеству лайков
    #     sorted_photos = sorted(photos, key=lambda x: -x['likes']['count'])
    #
    #     # Вернуть топ-3 фотографии
    #     top_photos = sorted_photos[:3]
    #
    #     return top_photos

    # def send_photo(self, user_id, photo):
    #     # Отправить фотографию пользователю
    #     photo_url = photo['sizes'][-1]['url']
    #     self.vk.messages.send(user_id=user_id, attachment=photo_url)


if __name__ == '__main__':
    vkinder = Vkinder(token_vk.token_vk)
    while True:
        time.sleep(5)
        for event in vkinder.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                response = event.text.lower()
                if response in ['привет', 'hi', 'start']:
                    user_info = vkinder.get_user_info(event.user_id)
                    keyboard = vkinder.get_keyboard()
                    vkinder.user_info_message(user_info, keyboard)
                elif response == 'поиск':
                    vkinder.search_button_response(event.user_id)
                # elif response == 'избранные контакты':
                #     vkinder.favorite_contacts_button_response(event.user_id)
                else:
                    user_info = vkinder.get_user_info(event.user_id)
                    vkinder.write_msg(event.user_id, 'Извините, не понял вас')