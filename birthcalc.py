import asyncio
import logging
import sys
from datetime import datetime, timedelta
from aiogram.filters import CommandStart
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "7069972969:AAFq3JsL0coP7uGzQSgvMmfsZN8Cv4-2iac"

# Initialize Bot instance with a default parse mode which will be passed to all API calls
bot = Bot(TOKEN)

# All handlers should be attached to the Dispatcher
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Berlin")


# Connect to PostgreSQL database
async def connect_to_db():
    return await asyncpg.create_pool(user='datesbotdb_owner', password='YQimvcXhf61V',
                                     database='datesbotdb',
                                     host='ep-curly-field-a2j6alo3-pooler.eu-central-1.aws.neon.tech')


# Function to retrieve birthdays from the database
async def get_birthdays_from_db(pool):
    async with pool.acquire() as conn:
        birthdays = await conn.fetch('''SELECT user_id, birth_date FROM user_birthdays''')
    return birthdays


def days_until_same_year(target_date):
    today = datetime.now()
    today = today.date()
    target_date = target_date.replace(year=today.year)
    if today > target_date:
        target_date = target_date.replace(year=today.year + 1)
    delta = target_date - today
    return delta.days


# Function to send reminders for upcoming birthdays
async def send_birthday_reminders(pool):
    try:
        birthdays = await get_birthdays_from_db(pool)
        today = datetime.now().date()
        for user_id, birth_date in birthdays:
            if birth_date.month == today.month and birth_date.day == today.day:
                message = f"С днем рождения! 🎉 Сегодня у вас праздник!"
            else:
                message = f"До Вашего Дня Рождения осталось {days_until_same_year(birth_date)} дней! Скоро праздник! <3"
            await bot.send_message(user_id, message)
        logging.info("Messages sent!")
    except Exception as e:
        logging.error(f"Error sending birthday reminders: {e}")


# Handler for the /start command
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Hello, {hbold(message.from_user.full_name)}! Send me the date of your birth and I will calculate time to it!")


# Handler for user messages
@dp.message()
async def handle_user_message(message: types.Message) -> None:
    try:
        user_id = message.from_user.id
        birth_date = datetime.strptime(message.text, "%d-%m").date()
        await insert_birthday_to_db(user_id, birth_date)
        await message.reply(f"До {birth_date.strftime('%d-%m')} осталось {days_until_same_year(birth_date)} дней.")
    except ValueError:
        await message.reply("Неправильный формат даты! Пожалуйста, отправьте дату в формате ДД-ММ (например, 31-12).")


# Function to insert user's birthday into the database
async def insert_birthday_to_db(user_id, birth_date):
    pool = await connect_to_db()
    async with pool.acquire() as conn:
        await conn.execute(
            '''INSERT INTO user_birthdays (user_id, birth_date) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET birth_date = $2''',
            user_id, birth_date)


# Main function
async def main() -> None:
    # Connect to PostgreSQL
    # Start scheduler for birthday reminders
    # scheduler.add_job(send_birthday_reminders, trigger="cron", hour=21, minute=7)  # Send reminders every day at 8:00 AM
    scheduler.add_job(send_birthday_reminders, trigger="cron", hour=12, minute=45, args=[await connect_to_db()])
    scheduler.start()
    # Start bot
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
