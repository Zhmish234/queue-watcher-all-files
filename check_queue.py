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


def describe_selects(page):
    info = []
    for s in page.locator("select").all():
        try:
            info.append((s.get_attribute("name"), s.is_visible(), s.is_enabled(), s.locator("option").count()))
        except Exception:
            pass
    return info


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
        deadline = time.time() + 60
        while time.time() < deadline:
            if page.get_by_text(NO_SLOTS_TEXT, exact=False).count() > 0:
                result = False
                break
            for name, vis, en, n in describe_selects(page):
                if name != "service" and vis and en and n > 1:
                    result = True
            if result is not None:
                break
            page.wait_for_timeout(1000)

        page.screenshot(path="screenshot.png", full_page=True)
        print("selects:", describe_selects(page))
        browser.close()
        if result is None:
            raise RuntimeError("Страница не дозагрузилась за 60 сек, результат неясен")
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
