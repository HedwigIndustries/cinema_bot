import asyncio
import datetime
import logging
import sqlite3
import sys
import typing as tp
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import ClientSession
from bs4 import BeautifulSoup

import config

conn = sqlite3.connect('films.db')


@dataclass
class Film:
    film_id: int
    name: str | None
    type: str | None
    rating_kp: float | None
    rating_imdb: float | None
    year: int | None
    countries: str | None
    genres: str | None
    length: int | None
    description: str | None
    link_to_watch: str | None
    poster: str | None
    trailer: str | None
    date: datetime.datetime
    count: int

    def __str__(self) -> str:
        fields = []
        for key, value in self.__dict__.items():
            match key:
                case 'name':
                    if value:
                        fields.append(f'<b>Название:</b> <i>{value}</i>')
                case 'type':
                    if value:
                        fields.append(f'<b>Тип:</b> <i>{value}</i>')
                case 'rating_kp':
                    if value:
                        fields.append(f'<b>Рейтинг kinopoisk:</b> <i>{value}</i>')
                case 'rating_imdb':
                    if value:
                        fields.append(f'<b>Рейтинг iMDb:</b> <i>{value}</i>')
                case 'year':
                    if value:
                        fields.append(f'<b>Год производства:</b> <i>{value}</i>')
                case 'countries':
                    if value:
                        fields.append(f'<b>Странa:</b> <i>{value}</i>')
                case 'genres':
                    if value:
                        fields.append(f'<b>Жанр:</b> <i>{value}</i>')
                case 'length':
                    if value:
                        fields.append(f'<b>Время(мин.):</b> <i>{value}</i>')
                case 'description':
                    # print(value)
                    if value:
                        fields.append(f'<b>Описание:</b> <i>{value}</i>')
        return '\n'.join(fields)

    def get_attr(self) -> tuple[tp.Any, ...]:
        return tuple(value for key, value in self.__dict__.items())


dp = Dispatcher()


@dp.message(Command(commands=['start']))
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    text = ('<i>Привет, я игрушечный бот! Я постараюсь найти найти фильм по твоему сообщению!\n'
            'Я напишу тебе краткое описание фильма, год его выпуска, длительность,'
            ' перечислю страны, жанры, список актеров и создателей, покажу рейтинг на кинопоиске и imdb!\n'
            'Команда <code>/help</code> покажет тебе возможности бота.</i>')
    username: tp.Optional[User] = message.from_user.username  # type:ignore
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {username}_films (
            film_id INTEGER,
            name TEXT,
            type TEXT,
            rating_kp REAL,
            rating_imdb REAL,
            year INTEGER,
            countries TEXT,
            genres TEXT,
            length INTEGER,
            description TEXT,
            link_to_watch TEXT,
            poster TEXT,
            trailer TEXT,
            date NUMERIC,
            count INTEGER
        )
    ''')
    conn.commit()
    await message.answer(text=text)


@dp.message(Command(commands=['help']))
async def command_help_handler(message: Message) -> None:
    """
    This handler receives messages with `/help` command
    """
    text = ('<i>Просто напиши мне название фильма, и я постараюсь найти информацию о нем и ссылку на его просмотр!\n'
            'Команда <code>/history</code> покажет историю твоего поиска.\n'
            'Команда <code>/stats</code> покажет статистику твоего поиска. \n'
            'Надеюсь я помог тебе!</i>')
    await message.answer(text=text)


@dp.message(Command(commands=['history']))
async def command_history_handler(message: Message) -> None:
    """
    This handler receives messages with `/history` command
    """
    username = message.from_user.username  # type:ignore
    cursor = conn.cursor()
    cursor.execute(f'SELECT name FROM {username}_films')
    film_names = cursor.fetchall()

    if film_names:
        text = '<i>Твоя история поиска: </i>\n'
        for name in film_names:
            if name:
                cursor.execute(f'SELECT date FROM {username}_films WHERE name = ?', name)
                if (name := str(name)[1:-2]) == "None":
                    continue
                date = cursor.fetchone()
                date = datetime.datetime.strptime(str(date)[2:-10], "%Y-%m-%d %H:%M:%S")
                text += f'<b>Название</b>: <i>{name[1:-1]}</i>, <b>Дата последнего просмотра:</b> <i>{date}</i>\n'
        text += '<i>Интересный список получился, был рад помочь!</i>'
    else:
        text = '<i>От тебя еще не поступало запросов по поиску фильмов.</i>'
    await message.answer(text=text)


@dp.message(Command(commands=['stats']))
async def command_stats_handler(message: Message) -> None:
    """
    This handler receives messages with `/stats` command
    """
    username = message.from_user.username  # type:ignore
    cursor = conn.cursor()
    cursor.execute(f'SELECT name FROM {username}_films')
    film_names = cursor.fetchall()
    if film_names:
        text = '<i>Твоя статистика поиска: </i>\n'
        for name in film_names:
            if name:
                cursor.execute(f'SELECT count FROM {username}_films WHERE name = ?', name)
                if (name := str(name)[1:-2]) == "None":
                    continue
                count = cursor.fetchone()
                count = list(count)[0]
                text += f'<b>Название</b>: <i>{name[1:-1]}</i>, <b>Количество запросов:</b> <i>{count}</i>\n'
        text += '<i>Забавная статистика получилась, был рад помочь!</i>'
    else:
        text = '<i>От тебя еще не поступало запросов по поиску фильмов.</i>'
    await message.answer(text=text)


@dp.message()
async def search(message: types.Message) -> None:
    """
    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    text: str | None = message.text
    username = message.from_user.username  # type:ignore
    if (film := await search_film(text, username)) is None:
        await message.answer(text='<i>Не получилось найти данный фильм. Попробуй поправить название.</i>')
        return
    keyword = InlineKeyboardBuilder()
    if film.trailer:
        keyword.button(text='Трейлер', url=film.trailer)
    if film.link_to_watch:
        keyword.button(text='Cмотреть', url=film.link_to_watch)
    if (bot := message.bot) is None:
        await message.answer(text='<i>Я упал, но обещаю вернуться!.</i>')
        return
    if film.poster:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=film.poster,
            caption=str(film),
            reply_markup=keyword.as_markup()
        )
    else:
        await message.answer(text=str(film))
    return


async def search_film(film_name: str | None, username: tp.Any) -> Film | None:
    if film_name is None:
        return None

    query: str = f'kinopoisk {film_name}'
    url: str = f'https://www.google.com/search?q={query}'
    async with (ClientSession() as session):
        async with session.get(url, headers=config.google_headers) as response:
            if response.status == 200:
                html: str = await response.text()
                if (link := get_first_link(html)) is None:
                    return None
                if (film_id := get_film_id(link)) is None:
                    return None
                new_link = link.replace('.ru', '.gg')
            else:
                return None

            select_query = f"""
                SELECT * FROM {username}_films WHERE film_id = ?
                """
            cursor = conn.cursor()
            cursor.execute(select_query, (film_id,))
            if (resp := cursor.fetchone()) is not None:
                film_id, name, _type, rating_kp, rating_imdb, year, countries, \
                    genres, length, description, link_to_watch, poster, trailer, date, count = resp

                update_query = f"""
                    UPDATE {username}_films SET date = ?, count = count + 1 WHERE film_id = ?
                    """
                cursor.execute(update_query, (datetime.datetime.now(), film_id))
                conn.commit()

                return Film(film_id, name, _type, rating_kp, rating_imdb, year, countries, genres, length, description,
                            link_to_watch, poster, trailer, datetime.datetime.now(), count + 1)

        kp_api_url: str = f'https://api.kinopoisk.dev/v1.4/movie/{film_id}'
        async with session.get(kp_api_url, headers=config.kp_api_headers) as response:
            if response.status == 200:
                kp_json: tp.Any = await response.json()
                film = extract_json(kp_json, film_id, new_link)
            else:
                return None
            cursor.execute(f'''
                    INSERT INTO {username}_films (film_id, name, type, rating_kp, rating_imdb, year, countries,
                     genres, length, description, link_to_watch, poster, trailer, date, count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (film.get_attr()))
            conn.commit()
            return film


def get_first_link(html: str) -> str | None:
    soup = BeautifulSoup(html, 'html.parser')
    link: str | None = soup.find('div', {'class': 'egMi0 kCrYT'}).find('a', href=True).get('href') \
        .replace('/url?q=', '')
    return link


def get_film_id(link: str) -> str | None:
    suffix = link.replace('https://www.kinopoisk.ru/', '')
    if suffix[0] == 'f':
        film_id = suffix.replace('film/', '')
    elif suffix[0] == 's':
        film_id = suffix.replace('series/', '')
    else:
        return None

    return film_id.split('/')[0]


def extract_json(kp_json: tp.Any, film_id: str, new_link: str) -> Film:
    film = Film(
        name=kp_json.get('name'),
        type=kp_json.get('type'),
        rating_kp=safe_float(x.get('kp')) if (x := kp_json.get('rating')) else None,
        rating_imdb=safe_float(x.get('imdb')) if (x := kp_json.get('rating')) else None,
        year=safe_int(kp_json.get('year')),
        countries=", ".join([country['name'] for country in x]) if (x := kp_json.get('countries')) else None,
        genres=", ".join([genre['name'] for genre in x]) if (x := kp_json.get('genres')) else None,
        length=safe_int(kp_json.get('movieLength')),
        description=cut_description(kp_json.get('description'), 0),
        film_id=int(film_id),
        link_to_watch=new_link,
        poster=x.get('url') if (x := kp_json.get('poster')) else None,
        trailer=(y[0].get('url')) if (y := x.get('trailers') if (x := kp_json.get('videos')) else None) else None,
        date=datetime.datetime.now(),
        count=1
    )
    print(kp_json['name'])
    return film


def cut_description(value: str | None, count: int) -> str | None:
    if value is not None:
        if len(value) > 800:
            sentences = value.split(".")
            len_sentences = len(sentences)
            res = ".".join(sentences[:len_sentences // 2])
            return cut_description(res, count + 1)
        else:
            # print(value if count == 0 else (value + "..."))
            return value if count == 0 else (value + "...")
    else:
        return None


def safe_int(value: str | None) -> int | None:
    if value is not None:
        return int(value)
    return value


def safe_float(value: str | None) -> float | None:
    if value is not None:
        return float(value)
    return value


async def main() -> None:
    bot = Bot(config.TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
