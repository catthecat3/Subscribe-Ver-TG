import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Contact
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, BadRequest

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (Render)
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID', '0'))

# ГЛАВНЫЕ ФУНКЦИИ БОТА (АДАПТИРОВАНО ПОД v21)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - предлагает подписаться на канал"""
    keyboard = [[InlineKeyboardButton("✅ Я подписался!", callback_data='check_sub')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""🔥 Привет! 

Чтобы получить доступ к контенту, подпишись на наш канал:

📢 {CHANNEL_USERNAME}

После подписки нажми кнопку ниже 👇"""
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки проверки подписки"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name or "Друг"
    username = query.from_user.username or "нет username"
    
    try:
        # Проверяем подписку на канал
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            # Пользователь подписан - просим контакт
            logger.info(f"✅ Пользователь {user_id} (@{username}) подписан")
            
            keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(
                keyboard, 
                resize_keyboard=True, 
                one_time_keyboard=True
            )
            
            # Отправляем новое сообщение с кнопкой контакта
            await query.message.reply_text(
                f"""🎉 Отлично, {first_name}! 

Ты успешно подписался!

📝 Теперь поделись своим номером телефона, нажав кнопку ниже:""",
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
            
            # Создаем уникальный текст для избежания "Message is not modified"
            new_text = f"""⚠️ {first_name}, ты еще не подписан на канал {CHANNEL_USERNAME}!

📢 Пожалуйста, подпишись и попробуй снова!

(Попытка #{retry_count + 1})"""
            
            keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]]
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
        error_text = f"""❌ Ошибка подключения к каналу, {first_name}!

Возможные причины:
• Канал не найден
• Бот не добавлен в администраторы канала
• Канал приватный

🔧 Решение: 
1. Убедитесь, что канал публичный ({CHANNEL_USERNAME})
2. Добавьте бота как администратора в канал

Попробуйте позже или свяжитесь с поддержкой."""
        
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
        
        error_text = f"""❌ Произошла неожиданная ошибка, {first_name}!

🔧 Техническая команда уже работает над проблемой.

Пожалуйста, попробуй еще раз через минуту:"""
        
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
    
    # Формируем сообщение для владельца
    text = f"""📱 <b>Новый контакт!</b>

👤 <b>Имя:</b> {contact.first_name}
👤 <b>Фамилия:</b> {contact.last_name or 'Не указана'}
📞 <b>Телефон:</b> <code>{contact.phone_number}</code>
🆔 <b>User ID:</b> <code>{user.id}</code>
🔗 <b>Username:</b> @{user.username or 'Не указан'}
📅 <b>Дата:</b> {update.message.date.strftime('%d.%m.%Y %H:%M')}"""
    
    try:
        # Отправляем контакт владельцу
        await context.bot.send_contact(
            chat_id=OWNER_CHAT_ID,
            contact=contact
        )
        
        # Отправляем дополнительное текстовое сообщение с деталями
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=text,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Контакт отправлен: {contact.phone_number}")
        
    except TelegramError as e:
        logger.error(f"Ошибка отправки контакта владельцу: {e}")
        
        # Если не удалось отправить контакт, отправляем только текстовое сообщение
        try:
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"📱 <b>Новый контакт (только текст)!</b>\n\n{text}",
                parse_mode='HTML'
            )
            logger.info(f"✅ Текстовое сообщение с контактом отправлено")
        except Exception as e2:
            logger.error(f"Не удалось отправить даже текстовое сообщение: {e2}")
            await update.message.reply_text("❌ Ошибка отправки данных владельцу. Попробуйте позже.")
            return
    
    # Сбрасываем счетчик попыток
    if 'retry_count' in context.user_data:
        del context.user_data['retry_count']
    
    # Удаляем клавиатуру и благодарим
    markup = ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"""✅ Спасибо, {contact.first_name}! 

Твои данные успешно отправлены.

🎁 Скоро с тобой свяжутся!""",
        reply_markup=markup,
        parse_mode='HTML'
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Обновление {update} вызвало ошибку {context.error}")
    
    # Если это callback_query, пытаемся ответить пользователю
    if update and hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
        except Exception:
            pass

def run_bot():
    """Запуск бота для Render"""
    # Проверка настроек
    if not BOT_TOKEN:
        logger.error("❌ ОШИБКА: Не установлен BOT_TOKEN! Проверьте Environment Variables в Render")
        return
    
    if not CHANNEL_USERNAME:
        logger.error("❌ ОШИБКА: Не установлен CHANNEL_USERNAME! Проверьте Environment Variables в Render")
        return
    
    try:
        owner_id = int(OWNER_CHAT_ID)
    except ValueError:
        logger.error("❌ ОШИБКА: OWNER_CHAT_ID должен быть числом! Проверьте Environment Variables в Render")
        return
    
    # Создание приложения (v21)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^check_sub$'))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("🚀 Бот успешно запущен!")
    logger.info(f"📢 Канал для проверки: {CHANNEL_USERNAME}")
    logger.info(f"👤 Контакты отправляются пользователю: {OWNER_CHAT_ID}")
    logger.info("📱 Бот готов к работе!")
    logger.info("=" * 60)
    
    # Запуск polling (v21 - упрощенный синтаксис)
    application.run_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=10,
        bootstrap_retries=5
    )

# ЗАПУСК БОТА
if __name__ == '__main__':
    run_bot()
