# -*- coding: utf-8 -*-
import logging
import os
from datetime import timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, BadRequest

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ОТЛАДКА: Показать доступные переменные окружения
logger.info("🔍 DEBUG: Запуск бота на Railway...")
logger.info("🔍 DEBUG: Все переменные окружения:")
for key in os.environ:
    if any(x in key.upper() for x in ['BOT', 'CHANNEL', 'OWNER', 'TELEGRAM']):
        value = os.getenv(key)
        display_value = "***" if len(value or "") > 5 else value
        logger.info(f"🔍 DEBUG: {key} = {display_value}")

# НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (RAILWAY)
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')  # может быть с '@' или без
OWNER_CHAT_ID = os.getenv('OWNER_CHAT_ID', '0')

# ОТЛАДКА: Проверка конкретных переменных
logger.info(f"🔍 DEBUG: BOT_TOKEN: {'НАЙДЕН' if BOT_TOKEN else 'ОТСУТСТВУЕТ'} (длина: {len(BOT_TOKEN) if BOT_TOKEN else 0})")
logger.info(f"🔍 DEBUG: CHANNEL_USERNAME: {'НАЙДЕН' if CHANNEL_USERNAME else 'ОТСУТСТВУЕТ'} (значение: '{CHANNEL_USERNAME}')")
logger.info(f"🔍 DEBUG: OWNER_CHAT_ID: {'НАЙДЕН' if OWNER_CHAT_ID else 'ОТСУТСТВУЕТ'} (значение: '{OWNER_CHAT_ID}')")

def channel_username_clean(username: str) -> str:
    return (username or "").lstrip('@')

def channel_link(username: str) -> str:
    return f"https://t.me/{channel_username_clean(username)}"

# ГЛАВНЫЕ ФУНКЦИИ БОТА (ТОЧНО КАК В РАБОЧЕМ ВАРИАНТЕ)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - предлагает подписаться на канал"""
    keyboard = [
        [InlineKeyboardButton("✅ Подписался/-ась 🙂‍↕️", callback_data='check_sub')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    first_name = (update.effective_user.first_name or "Друзья")
    link = channel_link(CHANNEL_USERNAME)

    text = (
        f"Приятно познакомиться, {first_name}! 🙌\n\n"
        "Я — виртуальный ассистент Марины Кузьминичны.\n\n"
        "Чтобы записаться на персональный разбор, подпишитесь на наш канал:\n\n"
        f"<a href=\"{link}\">📌Подписаться</a>\n\n"
        "После подписки нажми кнопку ниже"
    )

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки проверки подписки"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name or "Друг"
    username = query.from_user.username or "нет username"
    link = channel_link(CHANNEL_USERNAME)

    try:
        # Проверяем подписку на канал
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if chat_member.status in ['member', 'administrator', 'creator']:
            # Пользователь подписан - просим контакт
            logger.info(f"✅ Пользователь {user_id} (@{username}) подписан")

            keyboard = [[
                KeyboardButton("📱 Поделиться номером", request_contact=True)
            ]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

            await query.message.reply_text(
                f"🎉 Прекрасно, {first_name}!\n\n"
                "Вижу вашу подписку!\n\n"
                "📝 Поделитесь, пожалуйста, вашим контактом, чтобы записаться на консультацию.\n\n"
                "Нажмите на кнопку ⬇️\n",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

            # Удаляем старое сообщение с кнопкой проверки
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить старое сообщение: {e}")

        else:
            # Пользователь не подписан
            logger.info(f"❌ Пользователь {user_id} (@{username}) не подписан")

            # Правильный подсчет попыток
            retry_count = context.user_data.get('retry_count', 0)
            context.user_data['retry_count'] = retry_count + 1

            new_text = (
                f"⚠️ {first_name}, к сожалению, вы ещё не подписались..\n\n"
                "📢 Пожалуйста, подпишитесь и попробуйте снова!\n\n"
                f"<a href=\"{link}\">📌Подписаться</a>\n\n"
                f"(Попытка #{retry_count + 1})"
            )

            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                # Пытаемся отредактировать сообщение
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except BadRequest as e:
                if "message is not modified" in str(e).lower():
                    # Если сообщение не изменилось, отправляем новое
                    await query.message.reply_text(
                        new_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                else:
                    # Для других ошибок BadRequest тоже отправляем новое сообщение
                    await query.message.reply_text(
                        new_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Ошибка редактирования сообщения: {e}")
                # В крайнем случае отправляем новое сообщение
                await query.message.reply_text(
                    new_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )

    except TelegramError as e:
        logger.error(f"Ошибка Telegram API для пользователя {user_id}: {e}")

        # Обработка ошибок Telegram API
        error_text = (
            f"❌ Ошибка подключения к каналу, {first_name}!\n\n"
            "Возможные причины:\n"
            "• Канал не найден\n"
            "• Бот не добавлен в администраторы канала\n"
            "• Канал приватный\n\n"
            "🔧 Решение:\n"
            f"1. Убедитесь, что канал публичный ({CHANNEL_USERNAME})\n"
            "2. Добавьте бота как администратора в канал\n\n"
            "Попробуйте позже или свяжитесь с поддержкой."
        )

        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                error_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception:
            await query.message.reply_text(
                error_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Общая ошибка проверки подписки {user_id}: {e}")

        error_text = (
            f"❌ Произошла неожиданная ошибка, {first_name}!\n\n"
            "🔧 Техническая команда уже работает над проблемой.\n\n"
            "Пожалуйста, попробуйте ещё раз через минуту."
        )

        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                error_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception:
            await query.message.reply_text(
                error_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик полученного контакта"""
    contact = update.message.contact
    user = update.effective_user

    # +3 часа к серверному времени Telegram (UTC)
    dt_plus3 = update.message.date + timedelta(hours=3)

    text = f"""📱 <b>Новый контакт!</b>

👤 <b>Имя:</b> {contact.first_name}
👤 <b>Фамилия:</b> {contact.last_name or 'Не указана'}
📞 <b>Телефон:</b> <code>{contact.phone_number}</code>
🆔 <b>User ID:</b> <code>{user.id}</code>
🔗 <b>Username:</b> @{user.username or 'Не указан'}
📅 <b>Дата:</b> {dt_plus3.strftime('%d.%m.%Y %H:%M')}"""

    try:
        # Отправляем контакт владельцу (API требует явно номер/имя)
        await context.bot.send_contact(
            chat_id=int(OWNER_CHAT_ID),
            phone_number=contact.phone_number,
            first_name=contact.first_name,
            last_name=contact.last_name or ""
        )

        # Доп. текст с деталями
        await context.bot.send_message(
            chat_id=int(OWNER_CHAT_ID),
            text=text,
            parse_mode='HTML'
        )

        logger.info(f"✅ Контакт отправлен: {contact.phone_number}")

    except TelegramError as e:
        logger.error(f"Ошибка отправки контакта владельцу: {e}")
        # Резервно — только текст
        try:
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text=f"📱 <b>Новый контакт (только текст)!</b>\n\n{text}",
                parse_mode='HTML'
            )
            logger.info("✅ Текстовое сообщение с контактом отправлено")
        except Exception as e2:
            logger.error(f"Не удалось отправить даже текстовое сообщение: {e2}")
            await update.message.reply_text("❌ Ошибка отправки данных владельцу. Попробуйте позже.")
            return

    # Сброс счётчика попыток
    context.user_data.pop('retry_count', None)

    # Удаляем клавиатуру и благодарим
    await update.message.reply_text(
        f"✅ Отлично, {contact.first_name}!\n\n"
        "Передал ваш контакт Марине Кузьминичне!\n\n"
        "🙌 В течении 15 минут она свяжется с Вами и запишет на консультацию!",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Обновление {update} вызвало ошибку {context.error}")
    # Если это callback_query, пытаемся ответить пользователю
    try:
        if update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
    except Exception:
        pass

def run_bot():
    """Запуск бота для Railway"""
    # Проверка настроек
    if not BOT_TOKEN:
        logger.error("❌ ОШИБКА: Не установлен BOT_TOKEN!")
        logger.error("🔧 Проверьте переменные окружения в Railway Dashboard → Variables")
        logger.error("🔧 Убедитесь, что добавлена переменная: BOT_TOKEN")
        return

    if not CHANNEL_USERNAME:
        logger.error("❌ ОШИБКА: Не установлен CHANNEL_USERNAME!")
        logger.error("🔧 Проверьте переменные окружения в Railway Dashboard → Variables")
        logger.error("🔧 Убедитесь, что добавлена переменная: CHANNEL_USERNAME, например @avitotest1809")
        return

    try:
        owner_id = int(OWNER_CHAT_ID)
        logger.info(f"✅ OWNER_CHAT_ID валиден: {owner_id}")
    except ValueError:
        logger.error("❌ ОШИБКА: OWNER_CHAT_ID должен быть числом!")
        logger.error("🔧 Проверьте переменные окружения в Railway Dashboard → Variables")
        logger.error("🔧 Пример: OWNER_CHAT_ID = 788399571")
        return

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^check_sub$'))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_error_handler(error_handler)

    # Запуск бота
    logger.info("🚀 Бот успешно запущен на Railway!")
    logger.info(f"📢 Канал для проверки: {CHANNEL_USERNAME}")
    logger.info(f"👤 Контакты отправляются пользователю: {OWNER_CHAT_ID}")
    logger.info("📱 Бот готов к работе! Отправьте /start в Telegram")
    logger.info("=" * 60)

    # Запуск polling с настройками для Railway
    application.run_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=10,
        bootstrap_retries=5,
        allowed_updates=Update.ALL_TYPES
    )

# ЗАПУСК БОТА
if __name__ == '__main__':
    run_bot()
