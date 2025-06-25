import asyncio
import csv
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel, PeerChat
from telethon import events
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Получение данных из .env
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
FORWARD_CHAT_ID = int(os.getenv("FORWARD_CHAT_ID"))

KEYWORDS_FILE = 'keywords.csv'
CHATS_FILE = 'chats.csv'


# Загрузить ключевые слова
def load_keywords():
    with open(KEYWORDS_FILE, encoding='utf-8') as f:
        return [row[0].strip().lower() for row in csv.reader(f) if row]


# Загрузить список чатов
def load_chats():
    with open(CHATS_FILE, encoding='utf-8') as f:
        return [line[0].strip() for line in csv.reader(f) if line]


# Получить entity по ID, username или названию
async def get_entity(client, chat_identifier):
    try:
        if chat_identifier.isdigit() or (chat_identifier.startswith('-') and chat_identifier[1:].isdigit()):
            chat_id = int(chat_identifier)
            if chat_id > 0:
                return await client.get_input_entity(PeerChat(chat_id))
            else:
                return await client.get_input_entity(PeerChannel(chat_id))
        elif chat_identifier.startswith('@'):
            return await client.get_input_entity(chat_identifier)
        else:
            async for dialog in client.iter_dialogs():
                if dialog.name.lower() == chat_identifier.lower():
                    return dialog.entity
        return None
    except Exception as e:
        print(f"Ошибка при получении чата {chat_identifier}: {e}")
        return None


# Обработчик новых сообщений
async def handler(event):
    chat = await event.get_chat()
    sender = await event.get_sender()

    chat_title = chat.title if hasattr(chat, 'title') else str(getattr(chat, 'id', 'unknown'))
    text = event.message.text.lower() if event.message.text else ""

    for keyword in load_keywords():
        if keyword in text:
            print(f"[{chat_title}] Найдено совпадение: '{keyword}'")
            message_preview = text[:200] + "..." if len(text) > 200 else text

            # Отправляем себе в ЛС
            await event.client.send_message(
                'me',
                f"⚠️ Совпадение по ключевому слову: **'{keyword}'**\n"
                f"Чат: **{chat_title}**\n\n"
                f"{message_preview}"
            )

            # Пересылаем сообщение в FORWARD_CHAT_ID
            await event.client.forward_messages(FORWARD_CHAT_ID, event.message)


# Основная функция
async def main():
    client = TelegramClient('session_user', API_ID, API_HASH)

    await client.start(phone=PHONE)
    print("Клиент запущен.")

    monitored_entities = []

    for chat_identifier in load_chats():
        entity = await get_entity(client, chat_identifier)
        if entity:
            monitored_entities.append(entity)
            print(f"Добавлен чат: {chat_identifier}")

    @client.on(events.NewMessage(chats=[e for e in monitored_entities]))
    async def _(event):
        await handler(event)

    print("Ожидание новых сообщений...")
    await client.run_until_disconnected()


# Запуск
if __name__ == '__main__':
    asyncio.run(main())