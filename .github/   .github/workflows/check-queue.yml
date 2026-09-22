"""
Проверка наличия свободных мест в электронной очереди
Паспортного сервиса (Мюнхен) и уведомление в Telegram.

Сайт использует Alpine.js и обычный <select name="service" id="service">.
При выборе услуги (value="4" = "Закордонний паспорт та (або) ID-картка")
срабатывает x-on:change, который подгружает доступные дни (getDays).
Если мест нет — на странице появляется текст "всі місця зайняті".
"""

import os
import sys
import requests
from playwright.sync_api import sync_playwright

URL = "https://munich.pasport.org.ua/solutions/e-queue"
SERVICE_SELECT = "select[name='service']"
SERVICE_VALUE = "4"  # "Закордонний паспорт та (або) ID-картка"
NO_SLOTS_TEXT = "всі місця зайняті"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram не настроен (нет токена/chat_id), пропускаю отправку.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
    resp.raise_for_status()


def check_slots() -> bool:
    """Возвращает True, если похоже, что появились свободные места."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)

        # Выбираем услугу через обычный select — надёжнее кликов по тексту.
        page.wait_for_selector(SERVICE_SELECT, timeout=15000)
        page.select_option(SERVICE_SELECT, SERVICE_VALUE)

        # Даём странице время подгрузить статус (Alpine x-on:change -> getDays).
        page.wait_for_timeout(4000)

        # Проверяем, есть ли красное сообщение об отсутствии мест.
        no_slots = page.get_by_text(NO_SLOTS_TEXT, exact=False).count() > 0

        browser.close()
        return not no_slots


def main():
    try:
        slots_available = check_slots()
    except Exception as e:
        print(f"Ошибка при проверке: {e}", file=sys.stderr)
        sys.exit(1)

    if slots_available:
        print("Похоже, места освободились!")
        send_telegram(
            "🎉 На сайте Паспортного сервиса (Мюнхен) похоже появились "
            "свободные места в электронной очереди!\n"
            f"Проверь и записывайся: {URL}"
        )
    else:
        print("Мест пока нет.")


if __name__ == "__main__":
    main()
