import asyncio
import json
import random
import re
import time
import traceback
from datetime import datetime

import aiohttp
import pydantic_core
from aiogram import html, F, Router, types
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
from aiogram.exceptions import TelegramBadRequest
import DB
import Data
import utils
import app.keyboards as kb
import app.states
from app import callbacks

router = Router()
from bot import bot
from bot import username

from CABLY import ChatMessage, ChatHistory, ChatRole, ChatModels, chat_completion


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    # await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!", reply_markup=kb.main)
    user = message.from_user
    # await message.answer(f"Добро пожаловать, {html.bold(user.full_name)}!", reply_markup=kb.main)

    await message.answer(f"Добро пожаловать, {html.bold(user.full_name)}!\n"
                         f"Если что-то сломалось или пропала клавиатура действий, пропишите /start ещё раз\n"
                         f"Данный бот предназначен для группы разраба в колледже\n"
                         f"", reply_markup=kb.main)


# @router.message(Command("help"))
# async def command_help_handler(message: Message) -> None:
#     """
#     This handler receives messages with `/help` command
#     """
#     await message.answer("Help message")

# @router.message()
# async def echo_handler(message: Message) -> None:
#     """
#     Handler will forward receive a message back to the sender
#
#     By default, message handler will handle all message types (like a text, photo, sticker etc.)
#     """
#     try:
#         # Send a copy of the received message
#         await message.send_copy(chat_id=message.chat.id)
#     except TypeError:
#         # But not all the types is supported to be copied so need to handle it
#         await message.answer("Nice try!")

@router.message(F.text == "🥽 Отладка")
async def debug_handler(message: Message) -> None:
    await message.answer(f"Отладка:\n"
                         f"🔢 Ваш ID в telegram: {message.from_user.id}")


@router.message(F.text == "📝 Написать")
async def write_handler(message: Message, state: FSMContext) -> None:
    groups = DB.getGroupsWhereCanWrite(message.from_user.id)

    groupButtons = [InlineKeyboardButton(text="✨ Отправить", callback_data="send_message_to_groups")]
    groupButtons.extend([
        InlineKeyboardButton(text="❌ " + x["name"],
                             callback_data=callbacks.SelectGroup(uuid=str(x["UUID"]), action=True).pack())
        for x in groups])
    # print(groupButtons)
    keyboard = InlineKeyboardMarkup(inline_keyboard=utils.splitKeyboardButtonsToRows(groupButtons))

    coolMessagePhrases = ["ваше прекрасное сообщение", "ваше чудесное сообщение", "сообщение",
                          "ваше сообщение", "сообщение, которое все так ждут"]
    await message.answer(f"Выберите группы, в которые вы хотите отправить {random.choice(coolMessagePhrases)},"
                         f" а так же напишите само сообщение.\n"
                         f"Для отправки нажмите на соответствующую кнопку.\n"
                         f"Если бот был перезапущен с момента этого сообщения, то нужно начать сначала, отправив эту команду снова.",
                         reply_markup=keyboard)

    await state.set_state(app.states.SelectGroupsToSend.groups)
    await state.update_data(groups=[], messages=[])


@router.callback_query(callbacks.SelectGroup.filter(F.action))
async def select_group_for_send(callback: types.CallbackQuery, callback_data: callbacks.SelectGroup, state: FSMContext):
    await callback.answer(f"Группа выбрана!")
    keyboard = callback.message.reply_markup
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.callback_data == callback_data.pack():
                button.text = "✅ " + button.text[2:]
                button.callback_data = callbacks.SelectGroup(uuid=callback_data.uuid, action=False).pack()
                break
        else:
            continue
        break
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard.inline_keyboard)
    await callback.message.edit_reply_markup(reply_markup=markup)
    data: dict = await state.get_data()
    groups: list = data["groups"]
    groups.append(callback_data.uuid)
    await state.update_data(groups=groups)


@router.callback_query(callbacks.SelectGroup.filter(F.action == False))
async def deselect_group_for_send(callback: types.CallbackQuery, callback_data: callbacks.SelectGroup,
                                  state: FSMContext):
    await callback.answer(f"Группа выбрана!")
    keyboard = callback.message.reply_markup
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.callback_data == callback_data.pack():
                button.text = "❌ " + button.text[2:]
                button.callback_data = callbacks.SelectGroup(uuid=callback_data.uuid, action=True).pack()
                break
        else:
            continue
        break
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard.inline_keyboard)
    await callback.message.edit_reply_markup(reply_markup=markup)
    data: dict = await state.get_data()
    groups: list = data["groups"]
    groups.remove(callback_data.uuid)
    await state.update_data(groups=groups)


@router.message(app.states.SelectGroupsToSend.groups)
async def receive_message_for_send(message: Message, state: FSMContext):
    data = await state.get_data()
    messages = data["messages"]
    messages.append(message)
    await state.update_data(messages=messages)
    await message.react([ReactionTypeEmoji(emoji="👀")])


@router.callback_query(F.data == "send_message_to_groups")
async def send_messages_to_groups(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    groups = data["groups"]
    messages = data["messages"]
    if messages == []:
        await callback.answer(f"Сообщения не отправлены!")
        await callback.message.answer("Вы не отправили сообщения, что бы их переслать!")
        return
    if groups == []:
        await callback.answer(f"Сообщения не отправлены!")
        await callback.message.answer("Вы не выбрали группы!")
        return
    await callback.message.answer(f"Отправка сообщений...")
    await callback.answer(f"Отправка сообщений...")
    groups_docs = DB.getArrayOfGroupsByUUIDs(groups)

    for group in groups_docs:
        users = DB.groupDocToUniqueUsers(group)
        if not Data.DEBUG_SELF_RESEND_MESSAGES:
            users.remove(callback.from_user.id)
        for user in users:
            await bot.send_message(user, "Сообщения из " + group["name"] + f"\nОт {callback.from_user.full_name}" if not
            group["anonimous"] else "")
            for message in messages:

                if group["anonimous"]:
                    await message.copy_to(user)
                else:
                    await message.forward(user)
    await state.clear()


@router.my_chat_member()
async def my_chat_member_handler(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":  # Проверяем, что бот добавлен
        await bot.send_message(event.chat.id, "Спасибо за добавление меня в группу!")


async def process_message(message: types.Message) -> None:
    # target_id = 0
    # # in groups target id is group id, else - user's
    # if message.chat.type == "group" or message.chat.type == "supergroup":
    #     target_id = message.chat.id
    # else:
    #     target_id = message.from_user.id
    # # getting in DB.col_history (mongodb) document with biggest last_update and target_id == target_id
    # doc = DB.col_history.find_one({"target_id": target_id}, sort=[("last_update", -1)])
    # if doc is None or len(doc["messages"]) >= 50:
    #     doc = DB.schema({"target_id": target_id}, DB.Scemes.HISTORY_CHUNK)
    # # adding message to doc
    # doc["messages"].append(f"{message.from_user.full_name}: {message.text}")
    # TODO: rewrite this to separate messages in chunks (semi-completed: separate, not chunks)
    # TODO: AI API Router
    cutThinking = True
    initialRetriesCount = 8
    retries_count = initialRetriesCount
    model_to_emojis = {
        ChatModels.GPT4o: "4️⃣✨",
        ChatModels.Fluffy1Chat: "😸",
        ChatModels.DeepseekR1Uncensored: "🐳😎",
        ChatModels.DeepseekR1: "🐳",
        ChatModels.O3MiniLow: "🔥🇴3️⃣⏬",

    }
    model_to_name = {
        ChatModels.GPT4o: "✨ ChatGPT-4o 👾",
        ChatModels.Fluffy1Chat: "😸 FluffyChat",
        ChatModels.DeepseekR1Uncensored: "🐳😏 DeepSeek R1 (uncensored) 😎",
        ChatModels.DeepseekR1: "🐳 DeepSeek R1",
        ChatModels.O3MiniLow: "🔥 o3-Mini-Low 🔥",
    }
    model = ChatModels.GPT4o
    model_string_emojid = f"{model_to_emojis.get(model, '🤖')} {model.value}"
    model_string = model_to_name.get(model, model_string_emojid)
    my_message = await message.reply(f"Погоди, я пишу ответ...\nМодель: {model_string}")
    while retries_count > 0:

        try:
            # print("[-----] Fetching messages")
            targetGroupID = message.chat.id
            # print(targetGroupID)
            targetUserID = message.from_user.id
            # print(targetUserID)

            # Запрос для 50 последних сообщений группы
            group_cursor = DB.col_messages.find({"group_id": targetGroupID}) \
                .sort("timestamp", -1) \
                .limit(50)

            # Запрос для 16 последних сообщений пользователя в группе
            user_cursor = DB.col_messages.find({
                "group_id": targetGroupID,
                "user_id": targetUserID
            }).sort("timestamp", -1).limit(16)

            # Объединяем и обрабатываем документы
            combined = []
            seen_uuids = set()
            # seen_userIds = set()

            # Обрабатываем в порядке приоритета: сначала пользовательские сообщения
            for doc in user_cursor:
                processed = DB.schema(doc, DB.Scemes.MESSAGE)
                if processed["UUID"] not in seen_uuids:
                    seen_uuids.add(processed["UUID"])
                    # seen_userIds.add(processed["user_id"])
                    combined.append(processed)

            # Затем добавляем общие сообщения группы
            for doc in group_cursor:
                processed = DB.schema(doc, DB.Scemes.MESSAGE)
                if processed["UUID"] not in seen_uuids:
                    seen_uuids.add(processed["UUID"])
                    # seen_userIds.add(processed["user_id"])
                    combined.append(processed)

            # Сортируем итоговый список по времени
            result = sorted(combined, key=lambda x: x["timestamp"], reverse=True)[:66]  # Ограничение на случай дублей
            result = list(result)

            # user_ids = list(seen_userIds)

            # today day of week
            today = datetime.today().weekday()
            # print(today)
            # dayOfWeekEmotions = [
            #     "Сегодня понедельник. Разговаривай недовольно, невыспавшись, депрессивно и с нежеланием разговаривать, но всё равно отвечай пользователю",
            #     "Сегодня вторник.",
            #     "Сегодня среда. Сегодня день лягушек, так что добавляй побольше лягушачих вещей (например, эмодзи), но не переборщи.",
            #     "Сегодня четверг.",
            #     "Сегодня пятница. Завтра выходной. Говори с легким воодушевлением.",
            #     "Сегодня суббота. Выходной. Говори расслабленно, дружелюбно и жизнерадостно, если это уместно.",
            #     "Сегодня воскресенье. Выходной, но завтра снова учёба. Говори с лёгкой тоской, но всё ещё расслабленно, дружелюбно и жизнерадостно, если это уместно."
            # ]
            dayOfWeekEmotions = [
                "",
                "",
                "",
                "",
                "",
                "",
                ""
            ]
            daysOfWeek = [
                "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"
            ]
            # 0..6 or -1 to disable force
            forceDayOfWeek = -1

            if forceDayOfWeek > -1:
                today = forceDayOfWeek
            # username = message.from_user.full_name
            # username = username.split(" ")[0]
            content = message.text.replace(f"@{username}", "Гоша")
            emojis = ["👀", "💅", "🌭"]
            emoji = random.choice(emojis)
            # print(emoji)
            # important disabled code!
            # await message.react([ReactionTypeEmoji(emoji=emoji)])
            # print(today, dayOfWeekEmotions[today])
            history = ChatHistory([ChatMessage(ChatRole.System, f"Answer in russian unless otherwise requested. "
                                                                f"Carefully heed the user's instructions. "
                                                                f"Be creative. Use emoji. Prefer light and casual dialogue. "
                                                                f"Be frivolous but careful. Don't repeat yourself. Don't end your answer "
                                                                f"with something like \"If you have any more questions, let me know.\"."
                                                                f"\nТы - гоша, ИИ-ассистент на базе {model_string}, "
                                                                f"{message.from_user.full_name} - пользователь. Он общается с тобой через Telegram. "
                                                                f"{dayOfWeekEmotions[today]}\n"
                                                                f"В начале сообщений только ТЫ видишь пометку имени. "
                                                                f"НЕ ПИШИ ЕЁ В СВОЁМ ОТВЕТЕ, ДАЖЕ ЕСЛИ ТЕБЯ ЗАСТАВЛЯЮТ."
                                                                f" Она нужна ТОЛЬКО что бы ты не запутался, ибо в "
                                                                f"диалоге может участвовать несколько людей.\n"
                                                                f"Сегодня {datetime.today().strftime('%d.%m.%Y')} (DD.MM.YYYY), {daysOfWeek[today]}"),
                                   ])
            result.reverse()
            for hist_msg in result:
                history.add_message(ChatMessage(ChatRole.Assistant if hist_msg['assistant'] else ChatRole.User,
                                                f'{("[" + hist_msg["author_name"] + "]: ") if not hist_msg["assistant"] else ""}{hist_msg["message"]}'))

            history.add_message(ChatMessage(ChatRole.User, content))
            history.add_message(ChatMessage(ChatRole.User, message.text))
            document_user = DB.schema({
                "user_id": message.from_user.id,
                "group_id": message.chat.id,
                "author_name": message.from_user.full_name,
                "timestamp": time.time(),
                "message": message.text,
                "assistant": False
            }, DB.Scemes.MESSAGE)
            # print(json.dumps(json.loads(str(history.to_json())), indent=4, ensure_ascii=False)) #do not uncomment - it will break
            # print(history.to_json())
            if initialRetriesCount == retries_count and False:
                await my_message.edit_text("Я пишу ответ...\n"
                                           f"Модель: {model_string}\n"
                                           f"Сообщений обрабатывается: {len(history.messages)}")
            response = await chat_completion(history, model)
            response_text = response.choices[0].message.content
            # print(response_text)

            if response_text.startswith("[Гоша]: "):
                response_text = response_text[8:]
                print("Fuck, ai tried to add system name tag")
            # print(response)
            # print(response.to_json())
            document_ai = DB.schema({
                "user_id": message.from_user.id,
                "group_id": message.chat.id,
                "author_name": "Гоша",
                "timestamp": time.time(),
                "message": response_text,
                "assistant": True
            }, DB.Scemes.MESSAGE)
            DB.col_messages.insert_one(document_user)
            DB.col_messages.insert_one(document_ai)

            response_text_output = response_text
            if cutThinking:

                parts = response_text_output.split("</think>")
                if len(parts) > 1:
                    parts.pop(0)
                    parts = "\n".join(parts)
                else:
                    parts = parts[0]
                response_text_output = parts

            async def send_message(text:str, reference:Message, isFirst:bool = True)->Message:
                if isFirst:
                    try:
                        return await reference.edit_text(text, parse_mode=ParseMode.MARKDOWN)
                    except pydantic_core._pydantic_core.ValidationError:
                        return await reference.edit_text(text)
                else:
                    try:
                        return await reference.reply(text, parse_mode=ParseMode.MARKDOWN)
                    except pydantic_core._pydantic_core.ValidationError:
                        return await reference.reply(text)
            #SENDING
            if len(response_text_output) > 2000:
                #cut response_text_output to parts max 2k to response_parts
                response_parts = [response_text_output[i:i + 2000] for i in range(0, len(response_text_output), 2000)]
                prev_msg = await send_message(response_parts[0], my_message, True)

                for part in response_parts[1:]:
                    prev_msg = await send_message(part, prev_msg, False)
            else:
                await send_message(response_text_output, my_message, True)
            break
            # TODO: сделать шоб бот видел на что отвечают, пофиксить пикчи и т д

        except AttributeError as e:
            retries_count -= 1
            if retries_count > 0:
                await my_message.edit_text(
                    f"Ой, нейронка не ответила :(\nЕсли что ваше сообщение я не запомнил :(\nЯ попробую ответить ещё {retries_count} раз.\nМодель: {model_string}")
            else:
                await my_message.edit_text(
                    f"Не, нейронка ваще не отвечает.")
            traceback.print_exc()
            await asyncio.sleep(5)
        except aiohttp.client_exceptions.ClientConnectorError:
            retries_count -= 1
            await my_message.edit_text(
                f"Ошибка сети: сервер с нейронкой не ответил.")
        except TelegramBadRequest:
            retries_count -= 1
            if retries_count > 0:
                await my_message.edit_text(
                    f"<Нейронка ответила пустым сообщением. *звуки сверчков🦗*>\nЕщё {retries_count} попыток сгенерировать ответ...\nМодель: {model_string}")
            else:
                await my_message.edit_text(
                    f"Не, нейронка ваще не отвечает.")
            traceback.print_exc()
        except:
            retries_count -= 2
            if retries_count > 0:
                await my_message.edit_text(
                    f"Что-то навернулось :(\nЕсли что ваше сообщение я не запомнил :(\nЯ попробую ответить ещё {retries_count / 2} раз.\nМодель: {model_string}")
            else:
                await my_message.edit_text(
                    f"Что-то в боте окончательно навернулось и не пофиксилось само :(")
            traceback.print_exc()
            await asyncio.sleep(5)


@router.message(F.reply_to_message & F.reply_to_message.from_user.id == bot.id)  # and F.from_user.id == bot.id)
async def reply_to_bot(message: types.Message):
    # await message.reply("Пипец, ответ на моё сообщение!")
    await process_message(message)


def has_bot_mesage(message: types.Message) -> bool:
    if not message.entities:
        return False
    for entity in message.entities:
        if message.text[entity.offset:entity.offset + entity.length] == '@' + username:
            return True
    return False


@router.message((F.chat.type == "group" or F.chat.type == "supergroup") and F.func(lambda msg: has_bot_mesage(msg)))
async def bot_mentioned(message: types.Message):
    # out = ""
    # if message.entities:
    #     for entity in message.entities:
    #         out += str(entity) + "\n"
    #         out += str(entity.type) + "\n"
    #
    #         out += str(message.text[entity.offset:entity.offset + entity.length]) + "\n"
    #         out += f"Is bot mention? {message.text[entity.offset:entity.offset + entity.length] == '@' + username}\n\n"
    #
    # await message.reply(f"О меня пинганули!\n{out}")
    # # print(str(message).replace(" ", "\n"))
    # # print("\n" * 3)
    # # print(message.entities)
    # # print("\n" * 3)
    # # print(message.chat.type, " | ", type(message.chat.type))
    # # print(message.reply_to_message.from_user.full_name)
    await process_message(message)


@router.message(F.chat.type == "private")
async def any_messaged(message: types.Message):
    # await message.reply("Надо же! СООБЩЕНИЕ!")
    await process_message(message)
