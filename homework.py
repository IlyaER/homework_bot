import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

import settings

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
cons = logging.getLogger('errorlog')
cons.setLevel(logging.ERROR)
handler = logging.StreamHandler()
cons.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logging.info(f"Отправка сообщения в Telegram: {message}")
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except TelegramError as error:
        message = f'Сбой отправки сообщения: {error}'
        logging.exception(message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.info("Запрос к API")
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            settings.ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error:
        raise Exception(f"Проблема при подключении: {error}")
    logging.debug(f"Получен ответ от API {homework_statuses}")
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ValueError("Ответ API не 200")
    try:
        hw_statuses = homework_statuses.json()
    except ValueError as error:
        raise ValueError(f"Ответ не в том формате {error}")
    return hw_statuses


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info("Проверка API на корректность")
    logging.info(response)
    if not isinstance(response, dict):
        raise TypeError("API вернул неверный ответ, ответ не есть список!")
    if 'homeworks' not in response.keys():
        raise ValueError('Нет ключа homeworks')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError("API вернул неверный ответ")
    if not response.get('homeworks'):
        return []
    logging.debug(f"Ответ API корректен: {response}")
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    logging.debug("Извлечение информации из запроса:")
    logging.debug(homework)
    if ('homework_name' or 'status') not in homework.keys():
        raise KeyError('Нет нужной информации в запросе')
    homework_name = homework['homework_name']
    homework_status = homework['status']

    verdict = settings.HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logging.error("Нет такого статуса")
        raise KeyError("Нет такого статуса")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    logging.info("Проверка токенов")
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception("Токены отсутствуют. Проверьте наличие файла .env")

    logging.info("Запущен бот")
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1

    hw_status = ''
    error_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response["current_date"]
            check = check_response(response)
            if not check:
                if not hw_status:
                    raise ValueError('Список работ пуст')
                logging.debug('Новых статусов не появилось')
                hw_status = ''
                continue
            hw = check[0]
            message = parse_status(hw)
            if message and message != hw_status:
                send_message(bot, message)
                hw_status = message
            else:
                logging.error(f'Ответ уже был отправлен: {message}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            if error_status != message:
                send_message(bot, message)
            error_status = message
        finally:
            time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
    main()
