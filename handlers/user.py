import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    get_user_by_code, update_user_phone, create_order,
    add_or_update_user, get_user_credits, deduct_credit
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
    logger.error(f"userid user_id: {user_id}")
    keyboard = [[KeyboardButton("/start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"سلام {user_name}!! أكتب الكود متاعك باش تبدأ الطلب.",
        reply_markup=reply_markup
    )
    return IDENTIFY

async def identify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.error(f"indentifying")
    if update.message.text == "/start":
        await update.message.reply_text("أكتب الكود متاعك.")
        return IDENTIFY
    
    code = update.message.text
    telegram_id = update.message.from_user.id
    
    user = get_user_by_code(code)
    if user is None:
        logger.error(f"Invalid code entered: {code}")
        await update.message.reply_text("الكود غير صحيح. راسل الإدارة.")
        return ConversationHandler.END
    
    user_credits = get_user_credits(code)
    if not user_credits:
        logger.error(f"No credits found for code: {code}")
        await update.message.reply_text("حدث خطأ في تحميل رصيدك. راسل الإدارة.")
        return ConversationHandler.END
    
    # Update telegram_id
    add_or_update_user(
        code,
        user_credits['credits_25go'],
        user_credits['credits_35go'],
        user_credits['credits_60go'],
        telegram_id
    )
    total_credits = user_credits['credits_25go'] + user_credits['credits_35go'] + user_credits['credits_60go']
    
    context.user_data['code'] = code
    context.user_data['credits'] = user_credits
    
    if total_credits <= 0:
        keyboard = [[InlineKeyboardButton("شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. يرجى شحن رصيدك.",
            reply_markup=reply_markup
        )
        logger.info(f"User {code} has no credits, prompted to refill")
        return ConversationHandler.END
    elif total_credits < 3:
        keyboard = [
            [InlineKeyboardButton("شحن الرصيد", callback_data="refill_credits")],
            [InlineKeyboardButton("متابعة بدون شحن", callback_data="continue_without_refill")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        credits_summary = (
            f"25GO: {user_credits['credits_25go']}, "
            f"35GO: {user_credits['credits_35go']}, "
            f"60GO: {user_credits['credits_60go']}"
        )
    
        await update.message.reply_text(
            f"تم التحقق من الكود! رصيدك: {credits_summary}. نقترح عليك شحن رصيدك قبل المتابعة.",
            reply_markup=reply_markup
        )
        logger.info(f"User {code} has low credits ({total_credits}), prompted to refill or continue")
        return ConversationHandler.END
    
    credits_summary = (
        f"25GO: {user_credits['credits_25go']}, "
        f"35GO: {user_credits['credits_35go']}, "
        f"60GO: {user_credits['credits_60go']}"
    )

    await update.message.reply_text(
        f"تم التحقق من الكود! رصيدك: {credits_summary}\nأكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    logger.info(f"Transitioning to PHONE state for code: {code}")
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
    
    refill_message = (
        "📌 لشراء الرصيد:\n\n"
        "1. اختر نوع الرصيد الذي تريد شراءه:\n"
        "- 25GO: 150 USDT لـ 50 رصيد\n"
        "- 35GO: 295 USDT لـ 50 رصيد\n"
        "- 60GO: 400 USDT لـ 50 رصيد\n\n"
        f"2. أرسل المبلغ عبر شبكة TRON (TRC20) إلى العنوان التالي: `{USDT_WALLET}`\n\n"
        "✅ ستحصل على 50 رصيد مباشرة بعد التحقق من التحويل\n\n"
        "📝 بعد الإرسال، أرسل لنا رقم المعاملة (TXID) للتحقق وإضافة الرصيد إلى حسابك"
    )
    
    await message(refill_message, parse_mode="Markdown")
    return REFILL_STATE

async def refill_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    code = context.user_data.get('code')
    logger.info(f"Refill credits triggered for user code: {code}")
    
    if not code:
        logger.warning("No user code found in context.user_data")
        await query.edit_message_text("خطأ: يرجى بدء المحادثة باستخدام /start أولاً.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("25GO (150 USDT)", callback_data="refill_25go")],
        [InlineKeyboardButton("35GO (295 USDT)", callback_data="refill_35go")],
        [InlineKeyboardButton("60GO (400 USDT)", callback_data="refill_60go")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_refill")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "اختر نوع الرصيد الذي تريد شحنه:",
        reply_markup=reply_markup
    )
    logger.info(f"Transitioning to state: REFILL_OFFER_CHOICE ({REFILL_OFFER_CHOICE})")
    return REFILL_OFFER_CHOICE

async def handle_refill_offer_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    selected_offer = query.data.replace("refill_", "")
    context.user_data['refill_offer'] = selected_offer
    
    offer_prices = {
        '25go': '150 USDT',
        '35go': '295 USDT',
        '60go': '400 USDT'
    }
    
    price = offer_prices.get(selected_offer, '')
    
    await query.edit_message_text(
        f"📌 لشراء رصيد {selected_offer.upper()}:\n\n"
        f"1. المبلغ المطلوب: {price}\n"
        f"2. أرسل المبلغ عبر شبكة TRON (TRC20) إلى العنوان التالي: `{USDT_WALLET}`\n\n"
        "✅ ستحصل على 50 رصيد مباشرة بعد التحقق من التحويل\n\n"
        "📝 بعد الإرسال، أرسل لنا رقم المعاملة (TXID) للتحقق وإضافة الرصيد إلى حسابك",
        parse_mode="Markdown"
    )
    return REFILL_STATE

async def cancel_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Clear any refill data
    context.user_data.pop('refill_offer', None)
    
    # Return to start
    await start(update, context)
    return ConversationHandler.END

async def continue_without_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    code = context.user_data.get('code')
    user_credits = context.user_data.get('credits')
    
    if not user_credits:
        await query.edit_message_text("حدث خطأ في تحميل رصيدك. راسل الإدارة.")
        return ConversationHandler.END
    
    credits_summary = (
        f"25GO: {user_credits['credits_25go']}, "
        f"35GO: {user_credits['credits_35go']}, "
        f"60GO: {user_credits['credits_60go']}"
    )
    
    await query.edit_message_text(
        f"تم التحقق من الكود! رصيدك: {credits_summary}\nأكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    return PHONE

async def handle_tx_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for when user sends transaction ID"""
    tx_id = update.message.text.strip()
    code = context.user_data.get('code')
    user_credits = context.user_data.get('credits', {})
    user_id = update.message.from_user.id
    offer_type = context.user_data.get('refill_offer', '').upper()  # Get selected offer
    
    # Create a summary of current credits
    if user_credits:
        current_credits = (
            f"25GO: {user_credits.get('credits_25go', 0)}, "
            f"35GO: {user_credits.get('credits_35go', 0)}, "
            f"60GO: {user_credits.get('credits_60go', 0)}"
        )
    else:
        current_credits = "غير متوفر"
    
    logger.info(f"User {code} submitted TXID: {tx_id} for {offer_type} refill")
    
    # Sanitize tx_id to ensure it's safe for callback data
    sanitized_tx_id = re.sub(r'[^a-zA-Z0-9\-_]', '', tx_id)
    sanitized_tx_id = sanitized_tx_id[:30]  # Limit length
    
    # Store the full tx_id in user_data for reference
    context.user_data['full_tx_id'] = tx_id
    
    # Include credit_type in callback data
    credit_type = context.user_data.get('refill_offer', '')
    if not credit_type:
        logger.error(f"No refill_offer found for user {code}")
        await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END
    
    # Create accept/reject buttons for admin
    keyboard = [
        [
            InlineKeyboardButton("✅ تأكيد الشحن", callback_data=f"confirm_refill_{code}_{sanitized_tx_id}_{credit_type}"),
            InlineKeyboardButton("❌ رفض الشحن", callback_data=f"reject_refill_{code}_{sanitized_tx_id}_{credit_type}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Send full TX ID in the message text
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔄 طلب شحن رصيد جديد!\nالكود: {code}\nالعرض: {offer_type}\nالمستخدم: {user_id}\nرقم المعاملة: `{tx_id}`\nالرصيد الحالي: {current_credits}",
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
    logger.info("Phone handler triggered")
    # Double check credits in case user somehow bypassed previous check
    if 'credits' not in context.user_data:
        await update.message.reply_text("عذرًا، ليس لديك معلومات رصيد. الرجاء بدء محادثة جديدة.")
        return ConversationHandler.END
    
    user_credits = context.user_data['credits']
    total_credits = user_credits['credits_25go'] + user_credits['credits_35go'] + user_credits['credits_60go']
    
    if total_credits <= 0:
        await update.message.reply_text("عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. الرجاء التواصل مع الإدارة.")
        return ConversationHandler.END
    
    phone_number = update.message.text
    logger.info(f"Received phone number: {phone_number}")
    
    if not re.match(r'^\d{8}$', phone_number):
        await update.message.reply_text(
            "رقم الهاتف غير صحيح. يجب أن يكون 8 أرقام فقط.\nالرجاء إدخال رقم التلفون مرة أخرى (مثلا 99000111)."
        )
        return PHONE
    
    context.user_data['phone_number'] = phone_number
    
    # First acknowledge the phone number
    await update.message.reply_text(f"تم تسجيل رقم الهاتف: {phone_number}")
    
    # Create offer buttons based on available credits
    keyboard = []
    if user_credits['credits_25go'] > 0:
        keyboard.append([InlineKeyboardButton("25GO", callback_data="25GO")])
    if user_credits['credits_35go'] > 0:
        keyboard.append([InlineKeyboardButton("35GO", callback_data="35GO")])
    if user_credits['credits_60go'] > 0:
        keyboard.append([InlineKeyboardButton("60GO", callback_data="60GO")])
    
    # If no specific credit types are available, show a message
    if not keyboard:
        await update.message.reply_text(
            "عذرًا، ليس لديك رصيد كافي من أي نوع من العروض. الرجاء شحن رصيدك."
        )
        return ConversationHandler.END
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "اختار عرض (حسب الرصيد المتاح):",
        reply_markup=reply_markup
    )
    return OFFER

async def offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    # Final credit check before processing offer
    if 'credits' not in context.user_data:
        await query.edit_message_text("عذرًا، ليس لديك معلومات رصيد. الرجاء بدء محادثة جديدة.")
        return ConversationHandler.END
    
    selected_offer = query.data  # 25GO, 35GO, or 60GO
    phone_number = context.user_data['phone_number']
    code = context.user_data['code']
    user_credits = context.user_data['credits']
    
    # Check if user has credits for this specific offer
    credit_type = f'credits_{selected_offer.lower()}'
    if user_credits.get(credit_type, 0) <= 0:
        await query.edit_message_text(f"عذرًا، ليس لديك رصيد كافي لعرض {selected_offer}. الرجاء اختيار عرض آخر أو شحن رصيدك.")
        return ConversationHandler.END

    # Create order and deduct the specific credit
    order_id = create_order(code, phone_number, selected_offer, telegram_id)
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

    # Format remaining credits for display
    credits_summary = (
        f"25GO: {user_credits['credits_25go']}, "
        f"35GO: {user_credits['credits_35go']}, "
        f"60GO: {user_credits['credits_60go']}"
    )

    await query.edit_message_text(
        f"✅ تم تسجيل الطلب!\nالتلفون: {phone_number}\nالعرض: {selected_offer}\nالرصيد المتبقي: {credits_summary}\nفي انتظار تأكيد الإدارة."
    )
    return ConversationHandler.END

async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    code = parts[1] if len(parts) >= 2 else None
    
    if not code:
        await query.edit_message_text("خطأ في المعلومات. حاول تبدأ من جديد بـ /start.")
        return ConversationHandler.END
    
    user = get_user_by_code(code)
    if not user:
        await query.edit_message_text("ما عندناش معلومات عليك. حاول تبدأ من جديد بـ /start.")
        return ConversationHandler.END
    
    # Get updated credit information
    user_credits = get_user_credits(code)
    if not user_credits:
        await query.edit_message_text("حدث خطأ في تحميل رصيدك. راسل الإدارة.")
        return ConversationHandler.END
    
    # Check if user has any credits
    total_credits = user_credits['credits_25go'] + user_credits['credits_35go'] + user_credits['credits_60go']
    
    if total_credits <= 0:
        await query.edit_message_text("عذرًا، ليس لديك رصيد كافي لتنفيذ طلب. الرجاء شحن رصيدك.")
        return ConversationHandler.END
    
    context.user_data['code'] = code
    context.user_data['credits'] = user_credits
    context.user_data['telegram_id'] = query.from_user.id
    
    # Format credits for display
    credits_summary = (
        f"25GO: {user_credits['credits_25go']}, "
        f"35GO: {user_credits['credits_35go']}, "
        f"60GO: {user_credits['credits_60go']}"
    )
    
    await query.edit_message_text(
        f"رصيدك: {credits_summary}\nأكتب رقم التلفون متاعك (مثلا 99000111)."
    )
    return PHONE
