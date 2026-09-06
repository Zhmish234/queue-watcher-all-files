"""
Проверка наличия свободных мест в электронной очереди
Паспортного сервиса (Мюнхен) и уведомление в Telegram.

Как это работает:
1. Открываем страницу https://munich.pasport.org.ua/solutions/e-queue
   в headless-браузере (Playwright), потому что доступность мест
   подгружается через JavaScript, а не видна в исходном HTML.
2. Кликаем на поле "Послуга" -> "Обрати" -> выбираем
   "Закордонний паспорт та (або) ID-картка".
3. Смотрим, появляется ли красное сообщение
   "Вибачте, на даний момент всі місця зайняті!".
   - Если сообщение ЕСТЬ -> мест нет, ничего не делаем.
   - Если сообщения НЕТ -> место(а) освободились -> шлём алерт в Telegram.

ВАЖНО: сайт использует кастомный (не нативный <select>) выпадающий
список, поэтому селекторы ниже подобраны по видимому тексту, а не
по CSS id/классам (я не могу выполнить JS сайта заранее, чтобы
подсмотреть точную разметку). Если после первого ручного теста
(см. README, шаг "Отладка") окажется, что элемент не находится —
открой сайт в Chrome, нажми F12 -> Elements, наведи на поле
"Послуга" и пришли мне точный HTML — я поправлю селекторы.
"""

import os
import sys
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = "https://munich.pasport.org.ua/solutions/e-queue"
SERVICE_LABEL_TEXT = "Послуга"
SERVICE_OPTION_TEXT = "Закордонний паспорт та (або) ID-картка"
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

        # Открываем выпадающий список "Послуга".
        # Пытаемся несколько вариантов селектора, т.к. точная разметка неизвестна.
        opened = False
        for attempt in [
            lambda: page.get_by_text("Обрати", exact=True).first.click(timeout=5000),
            lambda: page.locator("select").first.click(timeout=5000),
        ]:
            try:
                attempt()
                opened = True
                break
            except PWTimeout:
                continue

        if not opened:
            browser.close()
            raise RuntimeError(
                "Не удалось открыть выпадающий список 'Послуга' — "
                "нужно поправить селектор (см. инструкцию в README)."
            )

        # Выбираем нужную услугу.
        try:
            page.get_by_text(SERVICE_OPTION_TEXT, exact=False).first.click(timeout=5000)
        except PWTimeout:
            browser.close()
            raise RuntimeError(
                f"Не нашёл пункт '{SERVICE_OPTION_TEXT}' в списке услуг — "
                "нужно поправить селектор (см. инструкцию в README)."
            )

        # Даём странице время подгрузить статус (AJAX).
        page.wait_for_timeout(3000)

        # Проверяем, есть ли красное сообщение об отсутствии мест.
        no_slots = page.get_by_text(NO_SLOTS_TEXT, exact=False).count() > 0

        browser.close()
        return not no_slots


def main():
    try:
        slots_available = check_slots()
    except Exception as e:
        print(f"Ошибка при проверке: {e}", file=sys.stderr)
        # Не шлём алерт при технической ошибке, только пишем в лог,
        # чтобы не спамить ложными "местами есть".
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
