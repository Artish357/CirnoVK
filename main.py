#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import random
import os
import requests
import time
import vk


# Константы
HOUR = 3600
DAY = HOUR * 24
default_path = os.path.split(os.path.abspath(__file__))[0]


MAX_QUEUED = 3            # Максимальное количество постов в отложке. Помните, что лимит вк -- 50 постов
START_DAY_TIME = 0        # Время с начала дня, с которого будут ставиться посты. По умолчанию 0:00
END_DAY_TIME = 24 * HOUR  # Время с начала дня, до которого будут ставиться посты. По умолчанию 24:00
INTERVAL = HOUR           # Интервал постов. По умолчанию -- 1 час


def post_main():
    """
    Главная функция, публикует посты в отложку группы. Настройка производится изменением констант в шапке программы.
    """
    # Фильтруем посты не от админа группы в отложке

    # Прежде, чем фильтровать, нужно получить айди админа. Предполагаем, что админ это тот, с чьим токеном
    # работает программа
    # Вызов vk.api.users.get, почитать подробнее: https://vk.com/dev/users.get
    admin_id = api.users.get()[0]['id']

    # Получаем отложку паблика
    # Вызов vk.wall.users.get, почитать подробнее: https://vk.com/dev/wall.get
    queued = api.wall.get(owner_id=args.pub, filter='postponed', count=1000)['items']
    queued = [x for x in queued if x['created_by'] == admin_id]

    # Количество постов сейчас в отложке
    q_count = len(queued)

    # Получаем последний пост в отложке, с его времени начинаем генерацию
    # Если его нет, то начинаем с времени через 5 минут после настоящего
    last = time.time() + 5 * 60
    if q_count != 0:
        last = queued[-1]['date']

    # Количество постов, которое будет зарегистрировано в этот раз
    need_posts = MAX_QUEUED - q_count

    # Небольшой трюк чтобы зафиксировать количество постов между 0 и 16
    # Я не помню, почему нельзя кидать более 16 постов за раз. Скорее всего из-за подозрения на спам.
    need_posts = min(max(need_posts, 0), 16)

    # Генерация случайных временных слотов немного труднее, чем может показаться
    # Если содержимое функции schedule вас смущает, то игнорируйте её. Сама суть бота не там.

    # Сгенерировать need_posts временных слотов,
    # с часовым интервалом, начиная с времени last,
    # в периоде между 0:00 и 24:00, с разбросом 0.1
    slots = schedule(need_posts, INTERVAL, last, START_DAY_TIME, END_DAY_TIME, 0.1)

    # Далее, для каждого временного слота мы делаем пост в отложке паблика
    # enumerate возвращает последовательность из индекса элемента последовательности и самого элемента
    for i, slot in enumerate(slots):
        # Получаем список картинок в папке pictures
        pictures = os.listdir(os.path.join(default_path, 'pictures'))
        # И выбираем из них случайную
        image = random.choice(pictures)
        # Необходимо соединить имя картинки с путем до нее чтобы можно было ее прочитать
        image = os.path.join(default_path, 'pictures', image)

        # Открываем картинку как файл b
        with open(image, 'rb') as b:
            # И загружаем в вк
            s = upload_photo(api, b, args.pub)

            # Остается только опубликовать ее в группе
            # Вызов vk.api.wall.post, почитать подробнее: https://vk.com/dev/wall.post
            api.wall.post(owner_id=args.pub, attachments='photo%d_%d' % (s['owner_id'], s['id']), publish_date=slot)
            print('%d/%d posts done' % (i + 1, need_posts))

            # В связи с ограничением вк на количество вызовов, делаем паузу на 1 секунду
            time.sleep(1)

        # Удаляем картинку чтобы избежать повторов
        os.remove(image)


def upload_photo(account, f, group):
    """
    Загружает фото на стену группы. Подробнее: https://vk.com/dev/upload_files
    :param account: Объект vk.API, от имени которого будет загружено фото
    :param f: file-like объект, содержащий фотографию
    :param group: айди группы
    :return: Объект photo согласно https://vk.com/dev/objects/photo содержащийся в словаре
    """
    url = account.photos.getWallUploadServer(group_id=abs(group))['upload_url']
    r = requests.post(url, files={'photo': ("photo.jpeg", f)}).json()
    s = account.photos.saveWallPhoto(group_id=abs(group),
                                     photo=r['photo'],
                                     server=r['server'], hash=r['hash'])[0]
    return s


def schedule(n_posts, interval, last_time, from_time, to_time, random_width=0.0):
    """
    Генерирует список времен для публикации
    :param n_posts: Количество слотов, которые необходимо сгенерировать
    :param interval: Интервал между постами, в количестве секунд
    :param last_time: Время, с которого начинается генерация
    :param from_time: Время с начала для, с которого начинается генерация
    :param to_time:  Время с начала дня, на котором заканчивается генерация
    :param random_width: Разброс 0.0 - 1.0, ограничивает рандом. При 0 вернет число точно по центру, при 1 может
     вернуть любое число в интервале. Помогает не публиковать посты в точное время, вносит разнообразие.
    :return: Список времен для публикации
    """
    # Генерируем список пар минимального и максимального времени для каждого поста
    windows = []
    for x in range(int(from_time), int(to_time), int(interval)):
        windows.append((x, x + interval - 1))

    # Генерируем слот для каждой пары
    slots = []
    last = last_time
    for i in range(n_posts):
        slots.append(time_slot(last, windows, random_width))
        last = slots[-1]
    return slots


def time_slot(from_time, windows, random_width):
    """
    Генерирует одно время для публикации
    :param from_time: Время, с которого стоит начать генерацию
    :param windows: Список, содержащий уже сгенерированные времена
    :param random_width: Разброс 0.0 - 1.0, ограничивает рандом. При 0 вернет число точно по центру, при 1 может
     вернуть любое число в интервале
    :return: Одно время в формате числа с плавающей точкой
    """
    day = from_time // DAY * DAY
    last_point = windows[-1][0] + day
    if from_time > last_point:
        day += DAY
        return day + random_time_between(*windows[0], random_width)
    else:
        for w in windows:
            if w[0] + day >= from_time:
                return day + random_time_between(*w, random_width)


def random_time_between(x, y, random_width):
    """
    Генерирует случайное число в интервале
    :param x: Первое число
    :param y: Второе число
    :param random_width: Разброс 0.0 - 1.0, ограничивает рандом. При 0 вернет число точно по центру, при 1 может
     вернуть любое число в интервале
    :return: Случайное чило между x и y с разбросом random_width
    """
    middle = (x + y) // 2
    scatter = int((y - x) * random_width / 2)
    return int(middle + random.randint(-scatter, scatter))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VK scheduler')
    parser.add_argument('pub', type=int, help="id of the vk public page to post to")
    parser.add_argument('token', type=str, help="access_token of the administrator")
    args = parser.parse_args()
    api = vk.API(vk.Session(args.token), v="5.28")
    post_main()
