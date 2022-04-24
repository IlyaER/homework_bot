from telegram.ext import CommandHandler, Updater, Filters, MessageHandler
from telegram import ReplyKeyboardMarkup, Bot
from dotenv import load_dotenv
from http import HTTPStatus

#from exceptions import TypeError

import logging
import requests
import os
import time
import logging

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
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
    logging.info("Отправка сообщения в Telegram")
    print(message)
    #bot.send_message(
    #    chat_id=TELEGRAM_CHAT_ID,
    #    text=message,
    #)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.info("Запрос к API")
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    # logging.info(f"Получен ответ от API {homework_statuses.json()['homeworks']}")
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ValueError("Ответ API не 200")
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info("Проверка API на корректность")
    logging.info(response)
    if isinstance(response, list):
        raise TypeError("API вернул неверный ответ, ответ не должен быть списком")
    if not isinstance(response.get('homeworks'), list):
        raise TypeError("API вернул неверный ответ")
    if not response.get('homeworks'):
        raise ValueError("Список работ пуст")

    logging.info(f"Ответ API корректен: {response}")
    try:
        response.get('homeworks')
    except Exception as error:
        logging.exception(f"Страница выдаёт статус: {response.status_code} {error}")
        pass
    return response.get('homeworks')




def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы."""
    logging.info("Извлечение информации из запроса")
    logging.info(homework)
    #if homework:
    homework_name = homework['homework_name']
    homework_status = homework['status']

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        logging.error("Нет такого статуса")
        raise KeyError("Нет такого статуса")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    #raise ValueError("Список работ пуст")


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    logging.info("Проверка токенов")
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logging.info("Токены присутствуют")
        return True
    else:
        logging.error("Токены отсутствуют. Проверьте наличие файла окружения")
        return False



def main():
    """Основная логика работы бота."""
    logging.info("Запущен бот")
    ...

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) #- 2800000

    hw_status = ''
    if not check_tokens():
        raise Exception("Токены отсутствуют. Проверьте наличие файла окружения")
    while True:
        try:

            response = get_api_answer(current_timestamp)
            #current_timestamp = int(time.time())
            check = check_response(response)
            hw = check[0]
            message = parse_status(hw)
            if message and message != hw_status:
                send_message(bot, message)
                hw_status = message
            else:
                logging.error(f'отсутствует ключ homeworks в ответе: {check}')
            #time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            send_message(bot, message)
            #time.sleep(RETRY_TIME)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
