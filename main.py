from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Any, Awaitable, Callable, Dict
from aiogram import types
from html import escape
import asyncio
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from gigachat import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_gigachat.chat_models import GigaChat
import uuid # СОздает уникальные идентификаторы


token = '7465896802:AAFbeaw5V4dsXRXUkXF8SWfyecgzuMFW6oA'

GigaChatKey = "OTA1NGNjZDktMGVmMS00YjYzLThkZTAtMDRkNThiOWY4MjUyOjhiZTAwYzIwLTExNzQtNDkwNS1iMmY0LTM4NzUzZTA3MzA3YQ=="

llm = GigaChat(
    credentials=GigaChatKey,
    scope="GIGACHAT_API_PERS",
    model="GigaChat",
    verify_ssl_certs=False, # Отключает проверку наличия сертификатов НУЦ Минцифры
    streaming=False,
)

# Машина состояний FSM
class UserForm(StatesGroup):
    FIO = State()
    years = State()
    level = State()
    time = State()
    Second = State()
    task_type = State()


bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

listUser = {}

#Включаем логирование
logging.basicConfig(force=True, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Проверка на регистрацию
class SomeMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        id = data['event_update'].message.chat.id
        state: FSMContext = data['state']
        current_state = await state.get_state()

        if current_state in [UserForm.FIO.state, UserForm.years.state, UserForm.level.state, UserForm.time.state, UserForm.task_type.state]:
            return await handler(event, data)
        
        if data ['event_update'].message.text != '/start':
            async with aiosqlite.connect('users.db') as db:
                async with db.execute("SELECT id FROM users WHERE id = ?", (id, )) as cursor:
                    if await cursor.fetchone() is None:
                        await bot.send_message(chat_id=id, text="Вы не зарегетривроаны! Зарегистрируйтесь. Нажмите на старт")
                        return
        result = await handler(event, data)
        return result

@dp.message(Command('start'), State(None))
async def cmd_start(message: Message, state: FSMContext):
    async with aiosqlite.connect('users.db') as db:
        async with db.execute("SELECT id FROM users WHERE id = ?", (message.from_user.id, )) as cursor:
            if await cursor.fetchone() is None:
                await message.answer(f"Привет, {message.from_user.first_name}! Для использования бота пройдите анкету. Введите ФИО: ")
                await state.set_state(UserForm.FIO)
            else:
                await message.answer(f"Привет {message.from_user.first_name}! Вы уже зарегистрированы")

#Для повторного прохождения
@dp.message(F.text, UserForm.Second)
async def cmd_start2(message: Message, state: FSMContext):
    await message.answer ("Заполните анкету заново. Введите ФИО:")
    await state.set_state(UserForm.FIO)

# Проверка и ввод ФИО
@dp.message(F.text, UserForm.FIO)
async def input_fio(message: Message, state: FSMContext):
    if len(message.text.split()) != 3:
        await message.answer("ФИО введено неверно, введите повторно:")
        return
    await state.update_data(fio=message.text)
    await message.answer("Введите ваш возраст: ")
    await state.set_state(UserForm.years)

# Проверка и ввод возраста
@dp.message(F.text, UserForm.years)
async def input_years(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите корректный возраст: ")
        return
    
    await state.update_data(years=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Очень легкие (для начинающих)"),
            ],
            [
                KeyboardButton(text="Легкие (с небольшими трудностями)"),
            ],
            [
                KeyboardButton(text="Средние (требующие размышления)"),
            ],
             [
                KeyboardButton(text="Сложные (требующие много времени и усилий)"),
            ],
             [
                KeyboardButton(text="Очень сложные (для экспертов)"),
            ],
        ],
        resize_keyboard=True
    )

    await message.answer("Какой уровень сложности логической задачи вы предпочитаете? ", reply_markup=keyboard)
    await state.set_state(UserForm.level)

@dp.message(F.text, UserForm.level)
async def input_level(message: Message, state: FSMContext):
    level_options = [
        "Очень легкие (для начинающих)",
        "Легкие (с небольшими трудностями)",
        "Средние (требующие размышления)",
        "Сложные (требующие много времени и усилий)", 
        "Очень сложные (для экспертов)"
    ]

    if message.text not in level_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов сложности.")
        return
    await state.update_data(level=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Задачи на комбинаторику"),
            ],
            [
                KeyboardButton(text='Загадки'),
            ],
            [
                KeyboardButton(text='Задачи на смекалку'),
            ],
            [
                KeyboardButton(text='Вероятностные задачи'),
            ],
            [
                KeyboardButton(text='Тесты на IQ'),
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(f"Выберите какие задания вы хотите выполнять:", reply_markup=keyboard)
    await state.set_state(UserForm.task_type)

# Выбор типа задач
@dp.message(F.text, UserForm.task_type)
async def input_type_task(message:Message, state:FSMContext):
    task_type_options = [
        "Задачи на комбинаторику",
        "Загадки",
        "Задачи на смекалку",
        "Вероятностные задачи",
        "Тесты на IQ"
    ]
    if message.text not in task_type_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов типа задач.")
        return
    await state.update_data(task_type=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Менее 15 минут"),
            ],
            [
                KeyboardButton(text="15-30 минут"),
            ],
            [
                KeyboardButton(text="30-60 минут"),
            ],
            [
                KeyboardButton(text="Более часа"),
            ],
        ],
        resize_keyboard=True
    )
    
    await message.answer(f"Сколько времени в день вы готовы уделять логическим задачам?", reply_markup=keyboard)
    await state.set_state(UserForm.time)

@dp.message(F.text, UserForm.time)
async def input_time(message: Message, state: FSMContext):

    level_options = [
        "Менее 15 минут",
        "15-30 минут",
        "30-60 минут",
        "Более часа"
    ]
    
    if message.text not in level_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
        return

    await state.update_data(time=message.text)
    data = await state.get_data()

    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT * FROM users WHERE id = ?', (message.from_user.id,))
        user = await cursor.fetchone()

        if user:
            # Обновляем данные пользователя, кроме рейтинга
            await db.execute('UPDATE users SET fio = ?, years = ?, level = ?, time = ?, task_type = ? WHERE id = ?',
                             (data['fio'], data['years'], data['level'], data['time'], data['task_type'], message.from_user.id))
        else:
            # Создаем нового пользователя
            await db.execute('INSERT INTO users (id, fio, years, level, time, task_type, rating, statusrem, quizlevel, quizcount, quizpoints, quizschet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                             (message.from_user.id, data['fio'], data['years'], data['level'], data['time'], data['task_type'], 0, False, "Средние (требующие размышления)", 5, 0, 0))

        await db.commit()

    await message.answer(f"Спасибо, {data['fio']}. Ваши данные сохранены.")
    await state.clear()
    await cmd_mainmenu(message)


# Включение уведомлений
@dp.message(Command('on'))
async def ontext(message: Message):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET statusrem = TRUE WHERE id = ?", (message.from_user.id,))
        await db.commit()
    await message.answer('Напоминания активированы!')

# Остановка уведомлений
@dp.message(Command('off'))
async def offtext(message: Message):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET statusrem = FALSE WHERE id = ?", (message.from_user.id,))
        await db.commit()
    await message.answer('Напоминания отключены!')


menu1 = {
    'menu': [
        {'text': 'Режим викторины'},
        {'text': 'Свободный режим'},
        {'text': 'Уведомления', 'status': False},
        {'text': 'О себе'}
    ],
}

levels = [
        "Очень легкие (для начинающих)",
        "Легкие (с небольшими трудностями)",
        "Средние (требующие размышления)",
        "Сложные (требующие много времени и усилий)",
        "Очень сложные (для экспертов)"
    ]

tasks_types = [
    "Задачи на комбинаторику",
    "Загадки",
    "Задачи на смекалку",
    "Вероятностные задачи",
    "Тесты на IQ"
]

# Главная команда меню
@dp.message(Command('menu'), State(None))
async def cmd_mainmenu(message:Message):
    builder = ReplyKeyboardBuilder()
    user_id = message.from_user.id
    for item in menu1['menu']:
        if item.get('text') == 'Уведомления':
            status = await get_user_status(user_id)
            if status:
                 text = 'Уведомления ✅' 
                 item['status'] = True
            else:
                 text = 'Уведомления ❌' 
                 item['status'] = False
            builder.button(text=text)
        else:
             builder.button(text=item.get('text'))
    builder.adjust(2, 2)
    await message.answer("Вы в главном меню", reply_markup=builder.as_markup(resize_keyboard=True))

#Получение информации о статусе
async def get_user_status(user_id: int):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT statusrem FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            status = result[0]
        return status

#Получение информации о себе
@dp.message(F.text == 'О себе')
async def osebe(message : Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Пройти анкету заново", callback_data="back_to_discription")
    id = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT fio, rating, years, level, time, task_type FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    await message.answer(f"Информация о пользователе\nФИО: {res[0]}\nВаш рейтинг: {res[1]}\nВозраст: {res[2]}\nПредпочитаемая сложность заданий: {res[3]}\nПредпочитаемый тип логических задач: {res[5]}\nКоличество времени, которое готовы тратить: {res[4]}",  reply_markup=builder.as_markup())

    
# Сообщение для пользователя
async def send_msg(dp):
    async with aiosqlite.connect('users.db') as db:
        async with db.execute("SELECT * FROM users WHERE statusrem=TRUE") as cursor:
            async for row in cursor:
                await bot.send_message(chat_id=row[0], text='Пора проходить викторину!')

@dp.message((F.text =='Уведомления ✅') | (F.text == 'Уведомления ❌'))
async def toggle_notifications(message: Message):
    id = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
          status = await get_user_status(id)
          status = not status
          await db.execute("UPDATE users SET statusrem = ? WHERE id = ?", (status, id)) 
          await db.commit()
    await cmd_mainmenu(message)

# FSM для генерации задач для общего обсуждения
class TrueFreeModeState(StatesGroup):
    sentence_answer = State()          # Ответ, хочет ли пользователь продолжать отвечать на вопросы 
    waiting_answer_for_task = State()  # Ожидание ответа на задачу
    freemodeVictorine_answer = State() # окончательный ответ на задачу
    stoping = State()                  # Остановка игры

@dp.message(F.text == "Свободный режим", State(None))
async def true_freemode(message:Message, state:FSMContext):
    await start_freemode(message, state)

@dp.callback_query(F.data == "back_to_freemode_menu")
async def in_start_freemode(callback:CallbackQuery, state:FSMContext):
    await start_freemode(callback.message, state)

# Старт свбодного режима 
@dp.message(Command('freemode'))
async def start_freemode(message:Message, state: FSMContext):
    await message.answer("В свободном режиме вы можете уточнить задачу перед тем, как дать ответ. Играем? ")
    await state.set_state(TrueFreeModeState.sentence_answer)

# Обработка ответа, хочет ли пользователь начать новую задачу
@dp.message(TrueFreeModeState.sentence_answer)
async def confirm_task(message: Message, state: FSMContext):
    if message.text.lower() == 'да':
        level, task_type, builder = await handle_yes_action(state, message.from_user.id)
        await message.answer(f"Ваш текущий уровень сложности: {level}\nВыбранный тип задачи: {task_type}\nВыберите одно из действий:", reply_markup=builder.as_markup())
    elif message.text.lower().strip() == 'нет':
        await state.set_state(TrueFreeModeState.stoping)
        await stoping_free_mode(message, state)
    else:
        await message.answer("Пожалуйста, дайте ответ в формате 'да' или 'нет'.")


async def handle_yes_action(state: FSMContext, user_id: int):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT story, quizlevel, task_type FROM users WHERE id = ?", (user_id,)) as cursor: 
            res = await cursor.fetchone()

    story = res[0] if res[0] is not None else ''
    level = res[1]
    task_type = res[2]

    builder = InlineKeyboardBuilder()
    builder.button(text='Изменить уровень сложности', callback_data='flevel_freemode')
    builder.button(text='Изменить тип задачи', callback_data='flevel_type_freemode')
    builder.button(text='Инфо', callback_data='info2')
    builder.button(text='Получить задачу', callback_data='tasks')
    builder.button(text='Остановить игру', callback_data='stop')
    builder.adjust(2)

    story += f"\n Пользователь: да"
    
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET story = ? WHERE id = ?", (story, user_id))
        await db.commit()

    return level, task_type, builder

# Остановка игры
@dp.callback_query(F.data == 'stop')
async def stoping_free_mode_single(callback:CallbackQuery, state: FSMContext):
    await state.set_state(TrueFreeModeState.stoping)
    await stoping_free_mode(callback.message, state)

# Остановка игры
@dp.message(TrueFreeModeState.stoping)
async def stoping_free_mode(message:Message, state:FSMContext):
    await message.answer(f'Игра остановлена')
    await state.clear()

# Информация о свободной режиме 
@dp.callback_query(F.data == 'info2')
async def info_for_true_free_mode(callback: CallbackQuery):
    description = (
        "Добро пожаловать в режим ответа на задачу с возможностьюю уточнения задачи! \n\n"
        "Вы можете настроить уровень сложности задачи под себя.\n"
        "Если готовы начать игру, нажмите на соответсвующие кнопки. То же самое в противном случае.\n"
        "Вы можете задавать уточняющие вопросы, ответ принимается при его инициализации в явном виде. \nПример:'Мой ответ ...'.\n"
        "Баллы начисляются в зависимости от того, какой уровень сложности выбран: \n"
        "  • Очень легкие: 1 балл\n"
        "  • Легкие: 2 балла\n"
        "  • Средние: 3 балла\n"
        "  • Сложные: 4 балла\n"
        "  • Очень сложные: 5 баллов"
    )
    await callback.message.edit_text(description, reply_markup=await create_back_keyboard_for_freemod())
    await callback.answer()

async def create_back_keyboard_for_freemod():
    builder = InlineKeyboardBuilder()
    builder.button(text='Назад', callback_data='back_to_freemode_menu')
    return builder.as_markup()

# Вызов генерации задачи
@dp.callback_query(F.data == 'tasks')
async def task_single(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Начинаем")
    await callback.answer()
    await state.set_state(TrueFreeModeState.waiting_answer_for_task)
    await generate_question(callback)

# Генерация задачи 
async def generate_question(arg):
    if isinstance(arg, types.Message):
        id = arg.from_user.id
        msg = arg
    elif isinstance(arg, types.CallbackQuery):
        id = arg.from_user.id
        msg = arg.message

    task_id = str(uuid.uuid4()) # идентификатор задачи

    global chat_answer
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT story, quizlevel, task_type FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
            if res:
                story = res[0] if res[0] else ""
                level = res[1]
                task_type = res[2]
            else:
                await msg.answer("произошла проблема связанное с вашей анкетой. Обратитесь к авторам сего произведения.")
                return

    await msg.answer(f"ваш уровень {level}")
    # генерируем задачу
    message_questions = [
    SystemMessage(
        content= "Тебе нужно придумать задачу для развития логического мышления. Обязательно задачу, а не вопрос.Пусть есть 5 уровней сложности: очень лёгкий, лёгкий, сложный, очень сложный. И 6 разных типов задач: задачи на комбинаторику, Загадки, Задачи на смекалку, Криптограммы, Вероятностные задачи, Тесты на IQ."
    ),
    "Придумай задачу, не пиши ответ или объяснение. Задача должна сооветсвовать уровню сложности:" + level + " и типу: " + task_type + ". Убедись, что такой задачи не было предложено ранее и убедись что данные задачи соответсвуют данным сложности и типу:" + level + " и " + task_type + " соответственно."
    f"Проверь чтобы этой задачи не было в истории пользователя со стороны бота в {story}"
    ]

    res = llm.invoke(message_questions)
    await msg.answer(res.content)

    story += f"\nБот: {res.content} (Id: {task_id})"
    task_text = res.content.strip()

    # Созраняем историю в бд
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET story = ?, task_id = ?, task_text = ? WHERE id = ?", (story,task_id,task_text,id))
        await db.commit()

    return task_id

# Обработчик ответа пользователя
@dp.message(TrueFreeModeState.waiting_answer_for_task)
async def answer_waiting(message:Message, state:FSMContext):
    id = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizlevel, quizpoints, story, task_id, task_text FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    level = res[0]
    points = res[1]
    story = res[2]
    task_id = res[3]
    task_text = res[4]

    user_conversation = message.text.lower()

    is_answer_or_question = await checking_answer_or_question(message, task_text, user_conversation)

    if is_answer_or_question == 'ответ':
        await checking_answer(message, user_conversation, task_text, level, points, story, id, state)
    else:
        if is_answer_or_question == 'вопрос':
            await answering_for_questions(message, user_conversation, task_text, story, id)

# Проверка на вопрос или уточнение
async def checking_answer_or_question(message:Message, task_text, user_conversation):
    message_checking = [
        {
            "role":"system",
            "content":  f"Пользователь ввел: '{user_conversation}'"
                        f"Задача: '{task_text}'"
                        "Ты должен определить, введенное сообщение является ответом или вопросом по задачу"
                        "Пользователь может ввести просто слово 'да' или слово 'нет', что тоже является ответом на вопрос, а не вопросом"
                        "Ответь 'ответ' или 'вопрос' без лишних символов, только одно слово"
        }
    ]
    res = await llm.ainvoke(message_checking)
    response = res.content.strip().lower()
    return response

# Проверка Ответа на вопрос
async def checking_answer(message:Message, user_conversation:str, task_text:str, level:str, points: int, story: str, user_id: int, state:FSMContext):

    alfa = 0
    if level == "Очень легкие (для начинающих)":
        alfa = 1
    elif level == "Легкие (с небольшими трудностями)":
        alfa = 2
    elif level == "Средние (требующие размышления)":
        alfa = 3
    elif level == "Сложные (требующие много времени и усилий)":
        alfa = 4
    elif level == "Очень сложные (для экспертов)":
        alfa = 5
    
    message_conversations = [
        SystemMessage(
            content="Ты проверяющий, оцени логическую задачу. Оцени ответ пользователя и выдай только 'Верно' если ответ правильный, 'Неверно' если неправильный. Если ответ неверный, напиши верный ответ и обьясни его. Также и с верным ответом."
        ),
        HumanMessage(
            content=f"Задача: {task_text} \nОтвет пользователя: {user_conversation}"
        )
    ]

    res = await llm.ainvoke(message_conversations)
    answering = res.content.strip()
    if "Верно" in answering:
        points += alfa
    
        new_conversation = f"Пользователь:{user_conversation}\nБот: {answering}"
        story += new_conversation

        # Добавение истории в бд
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET story = ? WHERE id = ?", (story, user_id,))
            await db.commit()

        await message.answer(f'Оценка: {answering}, балл: {points}')

        # Обновление рейтинга 
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT rating FROM users WHERE id = ?", (user_id,)) as cursor:
                rows = await cursor.fetchone()
                rating = int(rows[0]) + points
            await db.execute("UPDATE users SET rating = ?, quizpoints = ? WHERE id = ?", (rating, 0, user_id,))
            await db.commit()
        points = 0
        await state.clear()
        await start_freemode(message, state)
        return
    else:
        await message.answer(f"Оценка: {answering}")
        new_conversation = f"Пользователь:{user_conversation}\nБот: {answering}"
        story += new_conversation
        # Добавение истории в бд
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET story = ? WHERE id = ?", (story, user_id,))
            await db.commit() 
        await state.clear()
        await start_freemode(message, state)
        return

# Ответ на уточняющий вопрос
async def answering_for_questions(message:Message, user_conversation:str, task_text:str, story: str, user_id: int):
    message_conversations = [
        SystemMessage(
            content=f"Отвечай на уточняющие вопросы по задаче{task_text}."
                    f"Вопрос пользвоателя:{user_conversation}"
        ),
        HumanMessage(
            content=f"Задача: {task_text} \nВопрос пользователя: {user_conversation}"
        )
    ]

    res = await llm.ainvoke(message_conversations)
    answering = res.content.strip().lower()
    new_conversation = f"Пользователь:{user_conversation}\nБот: {answering}"
    story += new_conversation
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET story = ? WHERE id = ?", (story, user_id))
    await message.answer(f"Ответ на вопрос: {answering}")

# FSM для генерации задач для викторины
class FreeModeState(StatesGroup):
    answer = State()             # Ответы пользователя
    count = State()              # количество вопросов
    quizmod = State()            # режим викторины 
    notifications = State()      # уведомления
    osebe = State()              # ввод информации пользователя

@dp.message(Command('quizmod'),State(None))
async def cmd_freemod(message: Message):
    await freemode(message)

@dp.message(F.text == "Режим викторины", State(None))
async def button_freemode(message: Message):
    await freemode(message)

@dp.callback_query(F.data == "back_to_menu")
async def inffreemode(callback: CallbackQuery):
    await freemode(callback)
    
@dp.callback_query(F.data == "back_to_discription")
async def inffreemode(callback: CallbackQuery, state: FSMContext):
    await cmd_start2(callback.message, state)

# Завершение викторины
@dp.message(Command('stop'),FreeModeState.answer)
async def cmd_stop(message: Message, state: FSMContext):
    id = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizlevel, quizcount, quizpoints, quizschet FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    points = res[2]
    # Обновляем рейтинг пользователя
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT rating FROM users WHERE id = ?", (id,)) as cursor:
            rows = await cursor.fetchone()
            rating = int(rows[0])+points
        await db.execute("UPDATE users SET rating = ?, quizpoints = ?, quizschet = ? WHERE id = ?", (rating, 0, 0, id)) 
        await db.commit()  
    await message.answer(f'Викторина закончена досрочно\nКоличество заработанных баллов: {points}\nОбщий рейтинг: {rating}')
    await state.clear()

# Окончание викторины
@dp.message(((F.text == "Режим викторины") | (F.text == "Свободный режим") | (F.text == "/start") | (F.text == "/quizmod") | (F.text == "/menu") | (F.text == "/")), FreeModeState.answer)
async def stop_quiz(message: Message, state: FSMContext):
    await message.answer("Для окончания викторины введите команду: /stop")
    await state.set_state(FreeModeState.answer)

# Основная функция режима викторины, выводит меню с выбором уровня и количества задач
async def freemode(arg):
    if isinstance(arg, types.Message):
     id = arg.from_user.id
     msg = arg
    elif isinstance(arg, types.CallbackQuery):
      id = arg.from_user.id
      msg = arg.message
    # Извлекаем текущие уровень сложности и количество задач из базы данных
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizlevel, quizcount, task_type FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    level = res[0]
    count = res[1]
    task_type = res[2]
    # Создаем кнопки для управления режимом викторины
    builder = InlineKeyboardBuilder()
    builder.button(text='Уровень сложности', callback_data='flevel' )
    builder.button(text='Изменить тип задач', callback_data='flevel_type_quiz')
    builder.button(text='Количество задач', callback_data='many' )
    builder.button(text='Начать викторину', callback_data='task1')
    builder.button(text='Инфо', callback_data='info1')
    builder.adjust(2)
    # Выводим меню пользователю
    await msg.answer(f"Режим викторины\nВаш текущий уровень сложности:\n{level}\nВыбранный тип задачи: {task_type}\nКоличество задач: \n{count}\nВыберите действие:", reply_markup=builder.as_markup())

# Обработка выбора количества задач в викторине
@dp.callback_query(F.data == 'many')
async def many_quizmod(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите количество задач")
    await state.set_state(FreeModeState.count)

# Обработка ввода количества задач пользователем
@dp.message(FreeModeState.count)
async def many_choise(message: Message, state: FSMContext):
    id = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizcount FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    count = res[0]
    if not message.text.isdigit() or message.text == "0":
        await message.answer("Введите корректное число: ")
        return
    count = int(message.text)
    async with aiosqlite.connect("users.db") as db:
          await db.execute("UPDATE users SET quizcount = ? WHERE id = ?", (count, id))
          await db.commit()
    await state.clear()
    await freemode(message)

#Режим выбор уровня
@dp.callback_query(F.data.in_(['flevel_freemode', 'flevel']))
async def freemode_level(callback: CallbackQuery):
    id = callback.from_user.id
    source = callback.data
    # Извлекаем текущий уровень сложности
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizlevel FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    level = res[0]
    builder = InlineKeyboardBuilder()
    # Создаем кнопки для выбора уровня сложности
    for i, level_name in enumerate(levels):
       builder.button(text=level_name, callback_data=f'level{i+1}:{source}')
    #builder.button(text='Назад', callback_data='back_to_freemode')
    builder.adjust(1)
    await callback.message.edit_text(f'Изменение уровня сложности\nВаш текущий уровень сложности:\n{level}\nВыберите новый уровень:', reply_markup=builder.as_markup())
    await callback.answer()

# Обработка выбора уровня сложности
@dp.callback_query(F.data.startswith('level'))
async def process_level_choice(callback: CallbackQuery):
    id = callback.from_user.id
    data_parts = callback.data.split(':')
    level_number = int(data_parts[0].replace('level', ''))
    source = data_parts[1]
    level = levels[level_number-1]
    await callback.message.edit_text(f'Вы выбрали уровень сложности: {level}')
    async with aiosqlite.connect("users.db") as db:
          await db.execute("UPDATE users SET quizlevel = ? WHERE id = ?", (level, id))
          await db.commit()
    await callback.answer()
    if source == 'flevel':
        await freemode(callback)
    elif source == 'flevel_freemode':
        level, task_type, builder = await handle_yes_action(state=TrueFreeModeState.sentence_answer, user_id=callback.from_user.id)
        await callback.message.edit_text(f"Ваш текущий уровень сложности: {level}\nВыбранный тип задачи: {task_type}\nВыберите одно из действий:", reply_markup=builder.as_markup())
        await callback.answer()

#Режим викторины вывод информации
@dp.callback_query(F.data == 'info1')
async def infofreemode(callback: CallbackQuery):
    description = (
        "Добро пожаловать в режим викторины!\n\n"
        "Вы можете настроить викторину под себя.\n"
        "Выберите количество вопросов и уровень сложности.\n"
        "За каждый правильный ответ вы получите от 1 до 5 баллов,\n"
        "в зависимости от выбранного уровня сложности:\n\n"
        "  • Очень легкие: 1 балл\n"
        "  • Легкие: 2 балла\n"
        "  • Средние: 3 балла\n"
        "  • Сложные: 4 балла\n"
        "  • Очень сложные: 5 баллов"
    )
    await callback.message.edit_text(description, reply_markup=await create_back_keyboard())
    await callback.answer()

async def create_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data="back_to_menu")
    return builder.as_markup()

#Режим викторины генерация задачи
@dp.callback_query(F.data == 'task1', State(None))
async def taskfreedom(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Начинаем викторину")
    await callback.answer()
    await state.set_state(FreeModeState.answer)
    await process_chat_task(callback)
    
async def process_chat_task(arg):
    if isinstance(arg, types.Message):
     id = arg.from_user.id
     msg = arg
    elif isinstance(arg, types.CallbackQuery):
      id = arg.from_user.id
      msg = arg.message
    global chat_answer
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizlevel, story, task_type FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    level = res[0]
    story = res[1]
    task_type = res[2]
    messages_questions = [
    SystemMessage(
        content= "Тебе нужно придумать задачу для развития логического мышления. Пусть есть 5 уровней сложности: очень лёгкий, лёгкий, сложный, очень сложный. И 6 разных типов задач: задачи на комбинаторику, Загадки, Задачи на смекалку, Криптограммы, Вероятностные задачи, Тесты на IQ."
    ),
    "Придумай задачу, не пиши ответ или объяснение. Задача должна сооветсвовать уровню сложности:" + level + " и типу: " + task_type + ". Убедись, что такой задачи не было предложено ранее и убедись что данные задачи соответсвуют данным сложности и типу:" + level + " и " + task_type + " соответственно."
    f"Проверь чтобы этой задачи не было в истории пользователя со стороны бота в {story}"
    ]
    res = llm.invoke(messages_questions)
    messages_questions.insert(len(messages_questions) - 1,res)
    chat_answer = messages_questions[(len(messages_questions)-2)].content
    await msg.answer(res.content)

    story += f"\nБот: {res.content}"
    # Созраняем историю в бд
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET story = ? WHERE id = ?", (story, id))
        await db.commit()


# Обработчик ответа пользователя
@dp.message(FreeModeState.answer, ~F.text.in_({"/stop", "/listuser","/start","/menu","/on", "/off", "нет", "Режим викторины"}))
async def process_user_answer(message: Message, state: FSMContext):
    id = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT quizlevel, quizcount, quizpoints, quizschet,story FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    count = res[1]
    points = res[2]
    level = res[0]
    schet = res[3]
    story = res[4]
    alfa = 0 
    if level == "Очень легкие (для начинающих)":
        alfa = 1
    elif level == "Легкие (с небольшими трудностями)":
        alfa = 2
    elif level == "Средние (требующие размышления)":
        alfa = 3
    elif level == "Сложные (требующие много времени и усилий)":
        alfa = 4
    elif level == "Очень сложные (для экспертов)":
        alfa = 5

    user_answer = message.text
    messages = [
        SystemMessage(
            content="Ты проверяющий, оцени логическую задачу. Оцени ответ пользователя и выдай только 'Верно' если ответ правильный, 'Неверно' если неправильный. Если ответ неверный, напиши верный ответ."
        ),
        HumanMessage(
            content=f"Задача: {chat_answer} \nОтвет пользователя: {user_answer}"
        )
    ]

    res = await llm.ainvoke(messages)
    evaluation = res.content.strip()

    new_conversation = f"Пользователь:{user_answer}\nБот: {evaluation}"
    story += new_conversation

    if evaluation == "Верно":
        points = points + alfa
    await message.answer(f"Оценка: {evaluation}")

    if schet < count - 1:
        schet = schet + 1
        async with aiosqlite.connect("users.db") as db:
          await db.execute("UPDATE users SET quizpoints = ?, quizschet = ?, story = ? WHERE id = ?", (points, schet, story, id))
          await db.commit()
        await process_chat_task(message)
    else:
        id = int(message.from_user.id)
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT rating FROM users WHERE id = ?", (id,)) as cursor:
                rows = await cursor.fetchone()
                rating = int(rows[0])+points
            await db.execute("UPDATE users SET rating = ?, quizpoints = ?, quizschet = ?, story = ? WHERE id = ?", (rating, 0, 0, story, id)) 
            await db.commit() 
        await message.answer(f'Поздравляем! \nВикторина пройдена\nКоличество заработанных баллов: {points}\nОбщий рейтинг: {rating}')
        schet = 0
        points = 0
        await state.clear()

# Функция изменения типа задачи
@dp.callback_query(F.data.in_(['flevel_type_freemode', 'flevel_type_quiz']))
async def changing_task_type(callback: CallbackQuery):
    print("вызвано")
    id = callback.from_user.id
    source = callback.data
    # Извлекаем текущий уровень сложности
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT task_type FROM users WHERE id = ?", (id,)) as cursor:
            res = await cursor.fetchone()
    type = res[0]
    builder = InlineKeyboardBuilder()
    # Создаем кнопки для выбора уровня сложности
    for i, type_name in enumerate(tasks_types):
       builder.button(text=type_name, callback_data=f'type{i+1}:{source}')
    builder.adjust(1)
    await callback.message.edit_text(f'Изменение типа задачи\nВаш текущий тип задачи:\n{type}\nВыберите новый тип:', reply_markup=builder.as_markup())
    await callback.answer()

# Обработка выбора типа
@dp.callback_query(F.data.startswith('type'))
async def process_type_choice(callback:CallbackQuery):
    print("вызвано снова")
    id = callback.from_user.id
    data_parts = callback.data.split(':')
    type_number = int(data_parts[0].replace('type', ''))
    source = data_parts[1]
    type = tasks_types[type_number-1]
    await callback.message.edit_text(f'Вы выбрали тип задачи: {type}')
    async with aiosqlite.connect("users.db") as db:
          await db.execute("UPDATE users SET  task_type = ? WHERE id = ?", (type, id))
          await db.commit()
    await callback.answer()
    if source == 'flevel_type_quiz':
        await freemode(callback)
    elif source == 'flevel_type_freemode':
        level, task_type, builder = await handle_yes_action(state=TrueFreeModeState.sentence_answer, user_id=callback.from_user.id)
        await callback.message.edit_text(f"Ваш текущий уровень сложности: {level}\nВыбранный тип задачи: {task_type}\nВыберите одно из действий:", reply_markup=builder.as_markup())
        await callback.answer()

# Обработчик для ListUser
@dp.message(Command("listuser"))
async def cmd_listUser(message: Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT fio, rating FROM users") as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await message.answer("Нет сохраненных пользователей")
        return
    response = "Сохраненные данные:\n"
    for fio, rating in rows:
         response += f"ФИО: {fio}, Рейтинг: {rating}\n"
    
    await message.answer(response)

# Ответ на произвольный текст
@dp.message()
async def prtext(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get('fio', 'Пользователь')
    await message.answer(f'Уважаемый {name}, нельзя писать произвольный текст.')

# Подключаемся к базе данных
async def start_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER,
            fio VARCHAR(255),
            years INTEGER,
            level VARCHAR(255),
            task_type VARCHAR(255),
            story TEXT,
            time VARCHAR(255),
            rating INTEGER,
            statusrem BOOLEAN,
            quizlevel VARCHAR(255),
            quizcount INTEGER,
            quizpoints INTEGER,
            quizschet INTEGER,
            task_id INTEGER,
            task_text TEXT
            )
        ''')
        await db.commit()

async def start_bot():
    commands = [
        BotCommand(command='start', description='Начать взаимодействие'),
        BotCommand(command='listuser', description='Показать всех зарегетрированных пользователей'),
        BotCommand(command='menu', description='главное меню'),
        BotCommand(command='quizmod', description='Режим викторины'),
        BotCommand(command='freemode', description='Свободный режим'),
        BotCommand(command='off', description='Отключить уведомления'),
        BotCommand(command='on', description='Включить уведомления'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

# Основная функция запуска бота
async def main():
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    scheduler.add_job(send_msg, 'interval', seconds=10, args=(dp, ))
    scheduler.start()

    dp.startup.register(start_bot)
    dp.message.outer_middleware(SomeMiddleware())
    dp.startup.register(start_db)
    try:
        print("Бот запущен")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        print("Бот остановлен")

asyncio.run(main())
