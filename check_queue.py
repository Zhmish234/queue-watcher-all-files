import os
import sys
import time
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = "https://munich.pasport.org.ua/solutions/e-queue"
SERVICE_SELECT = "select[name='service']"
SERVICE_VALUE = "4"
NO_SLOTS_TEXT = "всі місця зайняті"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram не настроен")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
    resp.raise_for_status()


def date_option_count(page):
    try:
        return page.locator("select[name='date']").locator("option").count()
    except Exception:
        return 0


def check_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        try:
            page.goto(URL, wait_until="load", timeout=45000)
        except PWTimeout:
            print("goto timeout, продолжаем")
        page.wait_for_timeout(5000)
        page.wait_for_selector(SERVICE_SELECT, state="visible", timeout=30000)
        page.select_option(SERVICE_SELECT, SERVICE_VALUE)

        result = None
        deadline = time.time() + 25
        while time.time() < deadline:
            if page.get_by_text(NO_SLOTS_TEXT, exact=False).count() > 0:
                result = False
                break
            if date_option_count(page) > 1:
                result = True
                break
            page.wait_for_timeout(1000)

        if result is None:
            result = date_option_count(page) > 1

        page.screenshot(path="screenshot.png", full_page=True)
        print("итоговое число опций в 'день':", date_option_count(page))
        browser.close()
        return result


def main():
    try:
        slots_available = check_slots()
    except Exception as e:
        print(f"Ошибка при проверке: {e}", file=sys.stderr)
        sys.exit(1)
    if slots_available:
        print("Места ЕСТЬ!")
        send_telegram("🎉 В электронной очереди Паспортного сервиса (Мюнхен) появились места!\n" + URL)
    else:
        print("Мест пока нет.")


if __name__ == "__main__":
    main()
