import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    get_user_by_code, update_user_phone, create_order,
    add_or_update_user
)
from constants import *
from .common import cancel

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    if user_id == ADMIN_ID:
        from .admin import show_admin_dashboard
        await show_admin_dashboard(update, context)
        return ConversationHandler.END
    
    context.user_data['telegram_id'] = user_id
    
    keyboard = [[KeyboardButton("/start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"سلام {user_name}!! أكتب الكود متاعك باش تبدأ الطلب.",
        reply_markup=reply_markup
    )
    return IDENTIFY

async def identify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "/start":
        await update.message.reply_text("أكتب الكود متاعك.")
        return IDENTIFY
    
    code = update.message.text
    telegram_id = context.user_data['telegram_id']
    
    user = get_user_by_code(code)
    if user is None:
        await update.message.reply_text("الكود غير صحيح. راسل الإدارة.")
        return ConversationHandler.END
    
    # Check if user has credits
    if user[1] <= 0:
        add_or_update_user(code, user[1], telegram_id)
        context.user_data['code'] = code
        context.user_data['credits'] = user[1]
        
        keyboard = [[InlineKeyboardButton("شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. يرجى شحن رصيدك.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    elif user[1] < 3:
        # Suggest refilling credits
        add_or_update_user(code, user[1], telegram_id)
        context.user_data['code'] = code
        context.user_data['credits'] = user[1]
        
        keyboard = [
            [InlineKeyboardButton("شحن الرصيد", callback_data="refill_credits")],
            [InlineKeyboardButton("متابعة بدون شحن", callback_data="continue_without_refill")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"تم التحقق من الكود! عندك {user[1]} رصيد فقط، نقترح عليك شحن رصيدك قبل المتابعة.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    add_or_update_user(code, user[1], telegram_id)
    
    context.user_data['code'] = code
    context.user_data['credits'] = user[1]
    await update.message.reply_text(
        f"تم التحقق من الكود! عندك {user[1]} رصيد.\nأكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    return PHONE
async def refill_credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for /refill command or refill button"""
    if hasattr(update, 'callback_query'):
        query = update.callback_query
        await query.answer()
        message = query.edit_message_text
    else:
        message = update.message.reply_text
    
    # Check if we have the user's code
    if 'code' not in context.user_data:
        await message(
            "عذرًا، يجب عليك بدء المحادثة باستخدام /start وإدخال الكود الخاص بك أولاً."
        )
        return ConversationHandler.END
    
    await message(
        f"لشحن رصيدك، الرجاء إرسال USDT (شبكة Tron/TRC20) إلى العنوان التالي:\n\n`{USDT_WALLET}`\n\n"
        f"عندما تنتهي من إرسال الأموال، أدخل رقم معرف المعاملة (TXID) للتحقق:",
        parse_mode="Markdown"
    )
    return REFILL_STATE

# Add these new handlers for refill flow
async def refill_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"لشحن رصيدك، الرجاء إرسال USDT (شبكة Tron/TRC20) إلى العنوان التالي:\n\n`{USDT_WALLET}`\n\n"
        f"بعد الإرسال، قم بإدخال رقم معرف المعاملة (TXID) للتحقق:",
    )
    return REFILL_STATE

async def continue_without_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    code = context.user_data.get('code')
    credits = context.user_data.get('credits')
    
    await query.edit_message_text(
        f"تم التحقق من الكود! عندك {credits} رصيد.\nأكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    return PHONE



async def refill_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
    "📌 لشراء الرصيد:\n\n"
    "1. أرسل مبلغ 295 USDT عبر شبكة TRON (TRC20)\n"
    f"2. إلى العنوان التالي: `{USDT_WALLET}`\n\n"
    "✅ ستحصل على 50 رصيد مباشرة بعد التحقق من التحويل\n\n"
    "📝 بعد الإرسال، أرسل لنا رقم المعاملة (TXID) للتحقق وإضافة الرصيد إلى حسابك",
    parse_mode="Markdown"
    )
    return REFILL_STATE

async def continue_without_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    code = context.user_data.get('code')
    credits = context.user_data.get('credits')
    
    await query.edit_message_text(
        f"تم التحقق من الكود! عندك {credits} رصيد.\nأكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    return PHONE


async def handle_tx_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for when user sends transaction ID"""
    tx_id = update.message.text.strip()
    code = context.user_data.get('code')
    user_credits = context.user_data.get('credits', 0)
    user_id = update.message.from_user.id
    
    logger.info(f"User {code} submitted TXID: {tx_id}")
    
    # Sanitize tx_id to ensure it's safe for callback data

    import re
    sanitized_tx_id = re.sub(r'[^a-zA-Z0-9\-_]', '', tx_id)
    sanitized_tx_id = sanitized_tx_id[:30]  # Limit length
    
    # Store the full tx_id in user_data for reference
    context.user_data['full_tx_id'] = tx_id
    
    keyboard = [
    [
        InlineKeyboardButton("✅ تأكيد الشحن", callback_data=f"confirm_refill_{code}_{sanitized_tx_id}"),
        InlineKeyboardButton("❌ رفض الشحن", callback_data=f"reject_refill_{code}_{sanitized_tx_id}")
    ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Send full TX ID in the message text, but use sanitized version in callback data
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔄 طلب شحن رصيد جديد!\nالكود: {code}\nالمستخدم: {user_id}\nرقم المعاملة: `{tx_id}`\nالرصيد الحالي: {user_credits}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Sent refill request to admin for user {code}")
        
        await update.message.reply_text(
            "✅ تم إرسال طلب الشحن! سيتم إشعارك عند التأكيد من قبل الإدارة."
        )
    except Exception as e:
        logger.error(f"Failed to send refill request to admin: {e}")
        await update.message.reply_text(
            "⚠️ حدث خطأ في إرسال طلب الشحن. الرجاء المحاولة مرة أخرى أو التواصل مع الإدارة."
        )
    
    return ConversationHandler.END

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Double check credits in case user somehow bypassed previous check
    if 'credits' not in context.user_data or context.user_data['credits'] <= 0:
        await update.message.reply_text("عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. الرجاء التواصل مع الإدارة.")
        return ConversationHandler.END
    
    phone_number = update.message.text
    
    if not re.match(r'^\d{8}$', phone_number):
        await update.message.reply_text(
            "رقم الهاتف غير صحيح. يجب أن يكون 8 أرقام فقط.\nالرجاء إدخال رقم التلفون مرة أخرى (مثلا 99000111)."
        )
        return PHONE
    
    context.user_data['phone_number'] = phone_number
    
    keyboard = [
        [InlineKeyboardButton("25GO", callback_data="25GO")],
        [InlineKeyboardButton("35GO", callback_data="35GO")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "اختار عرض:",
        reply_markup=reply_markup
    )
    return OFFER

async def offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Final credit check before processing offer
    if 'credits' not in context.user_data or context.user_data['credits'] <= 0:
        await query.edit_message_text("عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. الرجاء التواصل مع الإدارة.")
        return ConversationHandler.END
    
    selected_offer = query.data
    phone_number = context.user_data['phone_number']
    code = context.user_data['code']
    credits = context.user_data['credits']

    order_id = create_order(code, phone_number, selected_offer)
    update_user_phone(code, phone_number)

    # Send message to admin with accept/reject buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_{order_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"طلب جديد!\nرقم الطلب: {order_id}\nالكود: {code}\nالتلفون: `{phone_number}`\nالعرض: {selected_offer}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    await query.edit_message_text(
        f"✅ تم تسجيل الطلب!\nالتلفون: {phone_number}\nالعرض: {selected_offer}\nالرصيد: {credits}\nفي انتظار تأكيد الإدارة."
    )
    return ConversationHandler.END

async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    if len(parts) >= 3:
        code = parts[1]
        try:
            credits = int(parts[2])
        except ValueError:
            credits = 0
    else:
        telegram_id = query.from_user.id
        user = get_user_by_code(code)
        if user:
            code, credits = user[0], user[1]
        else:
            await query.edit_message_text("ما عندناش معلومات عليك. حاول تبدأ من جديد بـ /start.")
            return ConversationHandler.END
    
    # Check credits before allowing retry
    if credits <= 0:
        await query.edit_message_text("عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. الرجاء التواصل مع الإدارة.")
        return ConversationHandler.END
    
    context.user_data['code'] = code
    context.user_data['credits'] = credits
    context.user_data['telegram_id'] = query.from_user.id
    
    await query.edit_message_text(
        f"أكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    return PHONE