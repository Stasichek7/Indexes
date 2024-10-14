import sqlite3  # Імпортуємо бібліотеки
import asyncio  
from aiogram import Bot, Dispatcher, types  
from aiogram.types import Message  
from aiogram.filters import Command  
from aiogram.fsm.context import FSMContext  
from aiogram.fsm.storage.memory import MemoryStorage  
from aiogram.fsm.state import StatesGroup, State  

API_TOKEN = '7388192040:AAE6ySUHROsj21UOZkSxs4uOmdVnRrKTmC4' # Токен для Telegram-бота

bot = Bot(token=API_TOKEN)  # Створення бота з використанням токену
dp = Dispatcher(storage=MemoryStorage())  # Створення диспетчера зі сховищем станів у пам'яті

conn = sqlite3.connect('users.db')  # Підключення до бази даних SQLite
cursor = conn.cursor()  # Створення курсора для виконання SQL-запитів

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
    name TEXT,
    age INTEGER,
    profession TEXT           
)
''')  # Створення таблиці користувачів, якщо вона ще не існує
conn.commit()  # Збереження змін у базі даних

# Функція для додавання нового стовпця в таблицю, якщо він ще не існує
def add_column_if_not_exists(column_name, column_type):
    cursor.execute(f"PRAGMA table_info(users)")  # Запит інформації про структуру таблиці
    columns = [column[1] for column in cursor.fetchall()]  # Отримання списку назв стовпців
    if column_name not in columns:  # Якщо потрібного стовпця ще немає
        cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")  # Додавання нового стовпця
        conn.commit()  

# Додавання нових стовпців у таблицю, якщо вони відсутні
add_column_if_not_exists('name', 'TEXT')
add_column_if_not_exists('age', 'INTEGER')
add_column_if_not_exists('profession', 'TEXT')

# Оголошення класу станів для FSM 
class Form(StatesGroup):
    waiting_for_name = State()  # Стан очікування введення імені
    waiting_for_age = State()  # Стан очікування введення віку
    waiting_for_profession = State()  # Стан очікування введення професії


@dp.message(Command(commands=["start"]))
async def send_welcome(message: Message, state: FSMContext):
    user_id = message.from_user.id  # Отримання ID користувача
    username = message.from_user.username  # Отримання імені користувача

    if username is None:  # Якщо користувач не має нікнейму
        username = "Unknown"  # Присвоєння значення "Unknown"

    cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,))  # Перевірка наявності користувача в базі
    user = cursor.fetchone()  # Отримання результату запиту

    if user is None:  # Якщо користувача немає в базі
        cursor.execute('INSERT INTO users (user_id, username) VALUES (?, ?)', (user_id, username))  # Додавання нового користувача
        conn.commit()  
        await message.answer(f"Привіт, {username}! Давайте познайомимось ближче.")  # Привітання користувача
        await message.answer("Як тебе звати?")  # Запит на введення імені
        await state.set_state(Form.waiting_for_name)  # Встановлення стану очікування введення імені
    else:
        name = user[2] if len(user) > 2 else None  # Отримання імені з бази
        age = user[3] if len(user) > 3 else None  # Отримання віку з бази
        profession = user[4] if len(user) > 4 else None  # Отримання професії з бази
        if not name or not age or not profession:  # Якщо дані неповні
            await message.answer("Ваша інформація не повна. Давайте доповнимо:")  # Повідомлення про неповні дані
            if not name:
                await message.answer("Як тебе звати?")  # Запит на введення імені
                await state.set_state(Form.waiting_for_name)  # Встановлення стану очікування введення імені
            elif not age:
                await message.answer("Скільки вам років?")  # Запит на введення віку
                await state.set_state(Form.waiting_for_age)  # Встановлення стану очікування введення віку
            elif not profession:
                await message.answer("Яка у вас професія?")  # Запит на введення професії
                await state.set_state(Form.waiting_for_profession)  # Встановлення стану очікування введення професії
        else:
            await message.answer("Ви вже зареєстровані, і вся інформація повна.")  # Повідомлення, що дані повні

@dp.message(Form.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text  # Отримання введеного імені
    user_id = message.from_user.id  # Отримання ID користувача
    cursor.execute('UPDATE users SET name=? WHERE user_id=?', (name, user_id))  # Оновлення імені в базі даних
    conn.commit()  # Збереження змін у базі

    await state.update_data(name=name)  # Оновлення стану збереженими даними
    await message.answer("Скільки вам років?")  # Запит на введення віку
    await state.set_state(Form.waiting_for_age)  # Встановлення стану очікування введення віку

@dp.message(Form.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    if message.text.isdigit():  # Перевірка, чи є введений текст числом
        age = int(message.text)  # Перетворення введеного віку на ціле число
        if age > 0:  # Перевірка, що вік більше 0
            user_id = message.from_user.id  # Отримання ID користувача
            cursor.execute('UPDATE users SET age=? WHERE user_id=?', (age, user_id))  # Оновлення віку в базі даних
            conn.commit()  # Збереження змін у базі

            await state.update_data(age=age)  # Оновлення стану збереженими даними
            await message.answer("Яка у вас професія?")  # Запит на введення професії
            await state.set_state(Form.waiting_for_profession)  # Перехід до стану очікування професії
        else:
            await message.answer("Будь ласка, введіть реальний вік більше 0.")  # Якщо вік <= 0
    else:
        await message.answer("Будь ласка, введіть число.")  # Якщо введено не число

@dp.message(Form.waiting_for_profession)
async def process_profession(message: Message, state: FSMContext):
    profession = message.text  # Отримання введеної професії
    if len(profession) < 4:  # Перевірка, що професія складається мінімум з 4 символів
        await message.answer("Професія повинна містити щонайменше 4 літери.")  # Повідомлення про помилку
        return

    user_id = message.from_user.id  # Отримання ID користувача
    cursor.execute('UPDATE users SET profession=? WHERE user_id=?', (profession, user_id))  # Оновлення професії в базі даних
    conn.commit()  

    await message.answer(f"Дякую за інформацію!")  # Подяка за введену інформацію
    await state.clear()  # Очищення стану FSM

async def main():
    await dp.start_polling(bot)  # Запуск довготривалого опитування Telegram API

if __name__ == '__main__':
    asyncio.run(main())  
