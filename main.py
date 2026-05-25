import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

BOT_TOKEN = "8702167460:AAGI3uMS37u7h_OkWTpSQVFyC9Ndp0zVhQo"
CHAT_ID = "5446908574"

URL = "https://parking.mos.ru/parking/barrier/subscribe/"

PARKING_ADDRESS = "г. Москва, ул. Донецкая, влд. 34"

last_status = False
last_report_date = ""

# ---------------------------------
# ДАННЫЕ
# ---------------------------------

FULL_NAME = ""

EMAIL = ""

CAR_NUMBER = ""

PHONE = ""

TROIKA = ""


# ---------------------------------
# TELEGRAM
# ---------------------------------

def send_telegram(text):

    try:

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=30
        )

    except Exception as e:

        print("Ошибка Telegram:", e)


# ---------------------------------
# ИНТЕРВАЛ ПРОВЕРКИ
# ---------------------------------

def get_check_interval():

    now = datetime.now()

    # До 31 мая 2026 23:59 — раз в час
    if now < datetime(2026, 6, 1, 0, 0):

        return 3600

    # С 1 июня 2026 до 10 июня 2026 — раз в 5 минут
    elif now < datetime(2026, 6, 11, 0, 0):

        return 300

    return 3600


# ---------------------------------
# ОТЧЕТ 2 РАЗА В ДЕНЬ
# ---------------------------------

def should_send_daily_report():

    global last_report_date

    now = datetime.now()

    current_day = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    report_key = f"{current_day}_{current_time}"

    report_times = [
        "08:00",
        "17:00"
    ]

    if (
        current_time in report_times
        and report_key != last_report_date
    ):

        last_report_date = report_key

        return True

    return False


# ---------------------------------
# ЗАПОЛНЕНИЕ И ОПЛАТА
# ---------------------------------

async def fill_and_get_payment(page):

    print("Заполняем форму")

    form = page.locator("#form-pay-1")

    # ФИО
    await form.locator(
        'input[name="fio"]'
    ).fill(FULL_NAME)

    # EMAIL
    await form.locator(
        'input[name="email"]'
    ).fill(EMAIL)

    # НОМЕР МАШИНЫ
    await form.locator(
        'input[name="grz"]'
    ).fill(CAR_NUMBER)

    # ТЕЛЕФОН
    await form.locator(
        'input[name="phone"]'
    ).fill(PHONE)

    # ТРОЙКА
    await form.locator(
        'input[name="troika_num"]'
    ).fill(TROIKA)

    print("Форма заполнена")

    await page.wait_for_timeout(2000)

    # ---------------------------------
    # ЧЕКБОКСЫ
    # ---------------------------------

    print("Ставим чекбоксы")

    await page.locator(
        'label[for="parking-barries-checkbox4"]'
    ).click()

    await page.locator(
        'label[for="parking-barries-checkbox5"]'
    ).click()

    await page.wait_for_timeout(2000)

    # ---------------------------------
    # ПЕРВАЯ КНОПКА
    # ---------------------------------

    print("Нажимаем первую кнопку")

    await form.get_by_role(
        "button",
        name="Купить абонемент"
    ).click()

    # ---------------------------------
    # ЭКРАН ПРОВЕРКИ
    # ---------------------------------

    print("Ждем экран проверки")

    await page.wait_for_timeout(7000)

    # ---------------------------------
    # ВТОРАЯ КНОПКА
    # ---------------------------------

    print("Нажимаем вторую кнопку")

    second_button = page.locator(
        ".button-pay--js"
    )

    await second_button.wait_for(
        timeout=15000
    )

    await second_button.click()

    print("Ждем ссылку оплаты")

    payment_url = ""

    for i in range(20):

        current_url = page.url

        print(current_url)

        if "yoomoney.ru" in current_url:

            payment_url = current_url
            break

        await page.wait_for_timeout(1000)

    return payment_url


# ---------------------------------
# ПРОВЕРКА ПАРКОВКИ
# ---------------------------------

async def check_parking(page):

    global last_status

    print("\n========================")
    print("ПРОВЕРКА:", datetime.now())
    print("========================")

    await page.goto(URL)

    await page.wait_for_timeout(8000)

    # ---------------------------------
    # СЛЕДУЮЩИЙ МЕСЯЦ
    # ---------------------------------

    await page.get_by_text(
        "На следующий месяц",
        exact=True
    ).click()

    await page.wait_for_timeout(3000)

    # ---------------------------------
    # ОКРУГ
    # ---------------------------------

    dropdowns = page.locator(".select__header")

    await dropdowns.nth(0).click()

    await page.wait_for_timeout(2000)

    await page.get_by_text(
        "Юго-Восточный административный округ"
    ).click()

    await page.wait_for_timeout(3000)

    # ---------------------------------
    # АДРЕС
    # ---------------------------------

    await dropdowns.nth(1).click()

    await page.wait_for_timeout(3000)

    address = page.get_by_text(
        PARKING_ADDRESS
    )

    class_name = await address.get_attribute(
        "class"
    )

    has_places = (
        "disabled"
        not in str(class_name).lower()
    )

    print("Есть места:", has_places)

    # ---------------------------------
    # ОТЧЕТ 2 РАЗА В ДЕНЬ
    # ---------------------------------

    if should_send_daily_report():

        current_time = datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        )

        if has_places:

            send_telegram(
                "✅ Плановая проверка парковки\n\n"
                f"Адрес:\n{PARKING_ADDRESS}\n\n"
                f"Время: {current_time}\n\n"
                "Статус: места ЕСТЬ"
            )

        else:

            send_telegram(
                "❌ Плановая проверка парковки\n\n"
                f"Адрес:\n{PARKING_ADDRESS}\n\n"
                f"Время: {current_time}\n\n"
                "Статус: мест нет"
            )

    # ---------------------------------
    # ЕСЛИ МЕСТО ПОЯВИЛОСЬ
    # ---------------------------------

    if has_places and not last_status:

        send_telegram(
            "🔥 Появилось место!\n\n"
            f"Адрес:\n{PARKING_ADDRESS}\n\n"
            "Начинаю оформление..."
        )

        # ---------------------------------
        # ДАННЫЕ ДЛЯ ПРОВЕРКИ
        # ---------------------------------

        send_telegram(
            "⚠️ Проверьте данные абонемента:\n\n"
            f"ФИО: {FULL_NAME}\n\n"
            f"Email: {EMAIL}\n\n"
            f"Номер ТС: {CAR_NUMBER}\n\n"
            f"Телефон: {PHONE}\n\n"
            f"Тройка: {TROIKA}"
        )

        print("Выбираем адрес")

        await address.click()

        await page.wait_for_timeout(5000)

        try:

            payment_url = await fill_and_get_payment(
                page
            )

            if payment_url:

                send_telegram(
                    "🔥 Ссылка на оплату:\n\n"
                    f"{payment_url}"
                )

                print("Ссылка отправлена")

            else:

                send_telegram(
                    "❌ Не удалось получить ссылку оплаты"
                )

        except Exception as e:

            print("Ошибка оформления:", e)

            send_telegram(
                f"❌ Ошибка оформления:\n{e}"
            )

    if not has_places:

        print("Мест нет")

    last_status = has_places


# ---------------------------------
# MAIN
# ---------------------------------

async def main():

    send_telegram(
        "🚀 Бот запущен"
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        while True:

            try:

                await check_parking(page)

            except Exception as e:

                print("ОШИБКА:", e)

                send_telegram(
                    f"❌ Ошибка бота:\n{e}"
                )

            interval = get_check_interval()

            print(
                f"\nЖдем {interval} секунд"
            )

            await asyncio.sleep(interval)


asyncio.run(main())
