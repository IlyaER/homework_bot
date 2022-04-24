import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 6
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

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
    except Exception as error:
        message = f'Сбой отправки сообщения: {error}'
        logging.exception(message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.info("Запрос к API")
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    logging.debug(f"Получен ответ от API {homework_statuses}")
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ValueError("Ответ API не 200")
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info("Проверка API на корректность")
    logging.info(response)
    if isinstance(response, list):
        raise TypeError("API вернул неверный ответ, ответ не есть список!")
    if not isinstance(response.get('homeworks'), list):
        raise TypeError("API вернул неверный ответ")
    if not response.get('homeworks'):
        return []

    logging.debug(f"Ответ API корректен: {response}")
    try:
        response.get('homeworks')
    except Exception as error:
        logging.exception(f"Страница выдаёт ошибку: {error}")
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    logging.debug("Извлечение информации из запроса:")
    logging.debug(homework)
    homework_name = homework['homework_name']
    homework_status = homework['status']

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        logging.error("Нет такого статуса")
        raise KeyError("Нет такого статуса")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    logging.info("Проверка токенов")
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logging.info("Токены присутствуют")
        return True
    else:
        logging.critical("Токены отсутствуют. Проверьте наличие файла .env")
        return False


def main():
    """Основная логика работы бота."""
    logging.info("Запущен бот")

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1

    hw_status = ''
    error_status = ''

    if not check_tokens():
        raise Exception("Токены отсутствуют. Проверьте наличие файла .env")
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response["current_date"]
            check = check_response(response)
            if not check:
                if hw_status == '':
                    raise ValueError('Список работ пуст')
                logging.debug('Новых статусов не появилось')
                continue
            hw = check[0]
            message = parse_status(hw)
            if message and message != hw_status:
                send_message(bot, message)
                hw_status = message
            else:
                logging.error(f'отсутствует ключ homeworks в ответе: {check}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            if error_status != message:
                send_message(bot, message)
            error_status = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
