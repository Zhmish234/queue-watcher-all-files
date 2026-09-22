"""
Проверка наличия свободных мест в электронной очереди
Паспортного сервиса (Мюнхен) и уведомление в Telegram.

Диагностический режим: скрипт всегда сохраняет screenshot.png,
чтобы можно было увидеть, что реально видит браузер в CI.
"""

import os
import sys
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = "https://munich.pasport.org.ua/solutions/e-queue"
SERVICE_SELECT = "select[name='service']"
SERVICE_VALUE = "4"
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
        )

        try:
            page.goto(URL, wait_until="load", timeout=45000)
        except PWTimeout:
            print("goto timeout, продолжаем с тем, что успело загрузиться")

        page.wait_for_timeout(5000)

        page.screenshot(path="screenshot.png", full_page=True)
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"Текущий URL после загрузки: {page.url}")
        print(f"Заголовок страницы: {page.title()}")

        for close_text in ["Закрити", "Продовжити", "Accept", "Прийняти"]:
            try:
                btn = page.get_by_text(close_text, exact=True).first
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=1000)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

        try:
            page.wait_for_selector(SERVICE_SELECT, state="visible", timeout=20000)
        except PWTimeout:
            page.screenshot(path="screenshot.png", full_page=True)
            with open("page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            browser.close()
            raise

        page.select_option(SERVICE_SELECT, SERVICE_VALUE)
        page.wait_for_timeout(4000)
        no_slots = page.get_by_text(NO_SLOTS_TEXT, exact=False).count() > 0

        page.screenshot(path="screenshot.png", full_page=True)
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
