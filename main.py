import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Contact
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, BadRequest

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# НАСТРОЙКИ - создайте файл .env или замените на свои значения
BOT_TOKEN = os.getenv('BOT_TOKEN', 'ваш_токен_здесь')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@your_channel')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID', '123456789'))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
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
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            logger.info(f"✅ Пользователь {user_id} (@{username}) подписан")
            
            keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            
            await query.message.reply_text(
                f"""🎉 Отлично, {first_name}! 

Ты успешно подписался!

📝 Теперь поделись своим номером телефона, нажав кнопку ниже:""",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить старое сообщение: {e}")
                
        else:
            logger.info(f"❌ Пользователь {user_id} (@{username}) не подписан")
            
            retry_count = context.user_data.get('retry_count', 0)
            context.user_data['retry_count'] = retry_count + 1
            
            new_text = f"""⚠️ {first_name}, ты ещё не подписан на канал {CHANNEL_USERNAME}!

📢 Пожалуйста, подпишись и попробуй снова!

(Попытка #{retry_count + 1})"""
            
            keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(new_text, reply_markup=reply_markup, parse_mode='HTML')
            except BadRequest as e:
                if "message is not modified" in str(e).lower():
                    await query.message.reply_text(new_text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.message.reply_text(new_text, reply_markup=reply_markup, parse_mode='HTML')
            except Exception:
                await query.message.reply_text(new_text, reply_markup=reply_markup, parse_mode='HTML')
            
    except TelegramError as e:
        logger.error(f"Ошибка Telegram API для пользователя {user_id}: {e}")
        error_text = f"""❌ Ошибка подключения к каналу, {first_name}!

🔧 Проверьте настройки канала и попробуйте позже."""

keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            await query.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Общая ошибка проверки подписки {user_id}: {e}")
        error_text = f"""❌ Произошла ошибка, {first_name}!

🔧 Попробуй ещё раз через минуту:"""
        
        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='check_sub')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            await query.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик полученного контакта"""
    contact = update.message.contact
    user = update.effective_user
    
    text = f"""📱 <b>Новый контакт!</b>

👤 <b>Имя:</b> {contact.first_name}
👤 <b>Фамилия:</b> {contact.last_name or 'Не указана'}
📞 <b>Телефон:</b> <code>{contact.phone_number}</code>
🆔 <b>User ID:</b> <code>{user.id}</code>
🔗 <b>Username:</b> @{user.username or 'Не указан'}
📅 <b>Дата:</b> {update.message.date.strftime('%d.%m.%Y %H:%M')}"""
    
    try:
        await context.bot.send_contact(chat_id=OWNER_CHAT_ID, contact=contact)
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=text, parse_mode='HTML')
        logger.info(f"✅ Контакт отправлен: {contact.phone_number}")
        
    except TelegramError as e:
        logger.error(f"Ошибка отправки контакта: {e}")
        try:
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"📱 <b>Новый контакт (только текст)!</b>\n\n{text}",
                parse_mode='HTML'
            )
        except Exception as e2:
            logger.error(f"Не удалось отправить сообщение: {e2}")
            await update.message.reply_text("❌ Ошибка отправки данных. Попробуйте позже.")
            return
    
    if 'retry_count' in context.user_data:
        del context.user_data['retry_count']
    
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

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN or BOT_TOKEN == 'ваш_токен_здесь':
        logger.error("❌ BOT_TOKEN не установлен!")
        return
    
    if not CHANNEL_USERNAME or CHANNEL_USERNAME == '@your_channel':
        logger.error("❌ CHANNEL_USERNAME не установлен!")
        return
    
    if OWNER_CHAT_ID == 123456789:
        logger.error("❌ OWNER_CHAT_ID не установлен!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^check_sub$'))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Бот запущен!")
    logger.info(f"📢 Канал: {CHANNEL_USERNAME}")
    logger.info(f"👤 Владелец: {OWNER_CHAT_ID}")
    
    application.run_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=10,
        bootstrap_retries=5
    )

if name == '__main__':
    main()