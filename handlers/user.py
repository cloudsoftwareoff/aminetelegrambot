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
    user_name = update.message.from_user.first_name or "User"
    
    if user_id == ADMIN_ID:
        from .admin import show_admin_dashboard
        await show_admin_dashboard(update, context)
        return ConversationHandler.END
    
    context.user_data['telegram_id'] = user_id
    logger.info(f"Started conversation for user_id: {user_id}, name: {user_name}")
    
    await update.message.reply_text(
        f"👋 مرحبا {user_name}!\n"
        "أدخل الكود الخاص بك (هو رمز حسابك الفريد) لبدء الطلب."
    )
    return IDENTIFY

async def identify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "/start":
        await update.message.reply_text("📝 أدخل الكود الخاص بك مرة أخرى.")
        return IDENTIFY
    
    code = update.message.text.strip()
    telegram_id = update.message.from_user.id
    
    loading_msg = await update.message.reply_text("⏳ جاري التحقق من الكود...")
    
    user = get_user_by_code(code)
    if user is None:
        logger.warning(f"Invalid code entered: {code}")
        keyboard = [[InlineKeyboardButton("🔄 حاول مرة أخرى", callback_data="retry_code")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text(
            "❌ الكود غير صحيح!\nتحقق من الكود وحاول مرة أخرى أو تواصل مع الدعم @Support.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    user_credits = get_user_credits(code)
    if not user_credits:
        logger.error(f"No credits found for code: {code}")
        await loading_msg.edit_text("⚠️ حدث خطأ في تحميل رصيدك. تواصل مع الدعم @Support.")
        return ConversationHandler.END
    
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
    
    credits_summary = (
        "💳 رصيدك الحالي:\n"
        f"• 25GO: {user_credits['credits_25go']}\n"
        f"• 35GO: {user_credits['credits_35go']}\n"
        f"• 60GO: {user_credits['credits_60go']}"
    )
    
    if total_credits <= 0:
        keyboard = [[InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text(
            f"✅ الكود صحيح: {code}\n{credits_summary}\n\n"
            "❌ ليس لديك رصيد كافي لتقديم طلب.\nاشحن رصيدك الآن للمتابعة!",
            reply_markup=reply_markup
        )
        logger.info(f"User {code} has no credits, prompted to refill")
        return ConversationHandler.END
    elif total_credits < 3:
        keyboard = [
            [InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")],
            [InlineKeyboardButton("➡️ متابعة بدون شحن", callback_data="continue_without_refill")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text(
            f"✅ الكود صحيح: {code}\n{credits_summary}\n\n"
            "⚠️ رصيدك منخفض! ننصحك بشحن رصيدك لتجنب الانقطاع.",
            reply_markup=reply_markup
        )
        logger.info(f"User {code} has low credits ({total_credits}), prompted to refill or continue")
        return ConversationHandler.END
    
    await loading_msg.edit_text(
        f"✅ الكود صحيح: {code}\n{credits_summary}\n\n"
        "📱 الخطوة 2 من 3: أدخل رقم هاتفك (8 أرقام، مثل 99000111)."
    )
    logger.info(f"Transitioning to PHONE state for code: {code}")
    return PHONE

async def retry_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("📝 أدخل الكود الخاص بك مرة أخرى.")
    return IDENTIFY

async def refill_credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.reply_text
    
    if 'code' not in context.user_data:
        await message(
            "❌ يجب عليك إدخال الكود الخاص بك أولاً!\nابدأ بـ /start."
        )
        return ConversationHandler.END
    
    code = context.user_data['code']
    await message(
        f"💰 جاهز لشحن رصيدك، {code}؟\nاختر نوع الرصيد من الأزرار أدناه."
    )
    return await refill_credits(update, context)

async def refill_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.edit_message_text
    else:
        message = update.message.reply_text
    
    code = context.user_data.get('code')
    logger.info(f"Refill credits triggered for user code: {code}")
    
    if not code:
        logger.warning("No user code found in context.user_data")
        await message("❌ خطأ: ابدأ بـ /start وأدخل كودك أولاً.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("25GO (150 USDT)", callback_data="refill_25go")],
        [InlineKeyboardButton("35GO (295 USDT)", callback_data="refill_35go")],
        [InlineKeyboardButton("60GO (400 USDT)", callback_data="refill_60go")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_refill")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message(
        f"💳 اختر نوع الرصيد لشحنه، {code}:\n"
        "• 25GO: مناسب للاستخدام الخفيف\n"
        "• 35GO: مثالي للاستخدام المتوسط\n"
        "• 60GO: للاستخدام الثقيل",
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
    
    keyboard = [
    
        [InlineKeyboardButton("🔙 رجوع", callback_data="refill_credits")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 شحن رصيد {selected_offer.upper()}:\n\n"
        f"1️⃣ أرسل {price} عبر شبكة TRON (TRC20).\n"
        f"2️⃣ العنوان: `{USDT_WALLET}`\n"
        f"3️⃣ بعد الإرسال، أدخل رقم المعاملة (TXID).\n\n"
        "✅ ستحصل على 50 رصيد بعد التحقق.\n"
        "❓ للدعم: @Support",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return REFILL_STATE

async def cancel_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    context.user_data.pop('refill_offer', None)
    context.user_data.pop('full_tx_id', None)
    
    code = context.user_data.get('code')
    if not code:
        await query.edit_message_text("❌ ابدأ بـ /start للمتابعة.")
        return ConversationHandler.END
    
    user_credits = get_user_credits(code)
    credits_summary = (
        "💳 رصيدك الحالي:\n"
        f"• 25GO: {user_credits['credits_25go']}\n"
        f"• 35GO: {user_credits['credits_35go']}\n"
        f"• 60GO: {user_credits['credits_60go']}"
    )
    
    total_credits = user_credits['credits_25go'] + user_credits['credits_35go'] + user_credits['credits_60go']
    if total_credits > 0:
        await query.edit_message_text(
            f"🔙 رجعت إلى البداية، {code}!\n{credits_summary}\n\n"
            "📱 أدخل رقم هاتفك (8 أرقام، مثل 99000111)."
        )
        return PHONE
    else:
        keyboard = [[InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🔙 رجعت إلى البداية، {code}!\n{credits_summary}\n\n"
            "❌ ليس لديك رصيد كافي. اشحن الآن!",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

async def continue_without_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    code = context.user_data.get('code')
    user_credits = context.user_data.get('credits')
    
    if not user_credits:
        await query.edit_message_text("⚠️ حدث خطأ في تحميل رصيدك. تواصل مع @Support.")
        return ConversationHandler.END
    
    credits_summary = (
        "💳 رصيدك الحالي:\n"
        f"• 25GO: {user_credits['credits_25go']}\n"
        f"• 35GO: {user_credits['credits_35go']}\n"
        f"• 60GO: {user_credits['credits_60go']}"
    )
    
    await query.edit_message_text(
        f"➡️ متابعة الطلب، {code}!\n{credits_summary}\n\n"
        "📱 الخطوة 2 من 3: أدخل رقم هاتفك (8 أرقام، مثل 99000111)."
    )
    return PHONE

async def handle_tx_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tx_id = update.message.text.strip()
    code = context.user_data.get('code')
    user_credits = context.user_data.get('credits', {})
    user_id = update.message.from_user.id
    offer_type = context.user_data.get('refill_offer', '').upper()
    
    if not code or not offer_type:
        logger.error(f"Missing code or refill_offer for user_id: {user_id}")
        await update.message.reply_text("❌ خطأ: ابدأ من جديد بـ /start.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_txid_{tx_id}")],
        [InlineKeyboardButton("🔄 إعادة إدخال", callback_data="retry_txid")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📝 رقم المعاملة المدخل: `{tx_id}`\nهل هو صحيح؟",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return REFILL_STATE

async def confirm_txid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    tx_id = query.data.replace("confirm_txid_", "")
    code = context.user_data.get('code')
    user_credits = context.user_data.get('credits', {})
    user_id = query.from_user.id
    offer_type = context.user_data.get('refill_offer', '').upper()
    
    current_credits = (
        f"25GO: {user_credits.get('credits_25go', 0)}, "
        f"35GO: {user_credits.get('credits_35go', 0)}, "
        f"60GO: {user_credits.get('credits_60go', 0)}"
    ) if user_credits else "غير متوفر"
    
    logger.info(f"User {code} confirmed TXID: {tx_id} for {offer_type} refill")
    
    sanitized_tx_id = re.sub(r'[^a-zA-Z0-9\-_]', '', tx_id)[:30]
    context.user_data['full_tx_id'] = tx_id
    credit_type = context.user_data.get('refill_offer', '')
    
    if not credit_type:
        logger.error(f"No refill_offer found for user {code}")
        await query.edit_message_text("❌ خطأ: حاول مرة أخرى بـ /refill.")
        return ConversationHandler.END
    
    keyboard = [
        [
            InlineKeyboardButton("✅ تأكيد الشحن", callback_data=f"confirm_refill_{code}_{sanitized_tx_id}_{credit_type}"),
            InlineKeyboardButton("❌ رفض الشحن", callback_data=f"reject_refill_{code}_{sanitized_tx_id}_{credit_type}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔄 طلب شحن رصيد جديد!\nالكود: {code}\nالعرض: {offer_type}\nالمستخدم: {user_id}\nرقم المعاملة: `{tx_id}`\nالرصيد الحالي: {current_credits}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Sent refill request to admin for user {code}")
        
        await query.edit_message_text(
            "✅ تم إرسال طلب الشحن!\nسنخبرك بمجرد تأكيد الإدارة.\n❓ للدعم: @Support"
        )
    except Exception as e:
        logger.error(f"Failed to send refill request to admin: {e}")
        await query.edit_message_text(
            "⚠️ خطأ في إرسال طلب الشحن. حاول مرة أخرى أو تواصل مع @Support."
        )
    
    return ConversationHandler.END

async def retry_txid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 أدخل رقم المعاملة (TXID) مرة أخرى."
    )
    return REFILL_STATE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Phone handler triggered")
    if 'credits' not in context.user_data:
        await update.message.reply_text("❌ خطأ: ابدأ من جديد بـ /start.")
        return ConversationHandler.END
    
    user_credits = context.user_data['credits']
    total_credits = user_credits['credits_25go'] + user_credits['credits_35go'] + user_credits['credits_60go']
    
    if total_credits <= 0:
        keyboard = [[InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ ليس لديك رصيد كافي لتقديم طلب.\nاشحن رصيدك الآن!",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    phone_number = update.message.text.strip()
    logger.info(f"Received phone number: {phone_number}")
    
    if not re.match(r'^\d{8}$', phone_number):
        keyboard = [
            [InlineKeyboardButton("🔄 حاول مرة أخرى", callback_data="retry_phone")],
            [InlineKeyboardButton("🔙 رجوع للكود", callback_data="retry_code")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ رقم الهاتف غير صحيح!\nيجب أن يكون 8 أرقام (مثل 99000111).\nأدخله مرة أخرى أو ارجع لتغيير الكود.",
            reply_markup=reply_markup
        )
        return PHONE
    
    context.user_data['phone_number'] = phone_number
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الرقم", callback_data="confirm_phone")],
        [InlineKeyboardButton("🔄 تغيير الرقم", callback_data="retry_phone")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📱 رقم الهاتف المدخل: {phone_number}\nهل هو صحيح؟",
        reply_markup=reply_markup
    )
    return PHONE

async def confirm_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_credits = context.user_data['credits']
    code = context.user_data['code']
    
    keyboard = []
    if user_credits['credits_25go'] > 0:
        keyboard.append([InlineKeyboardButton("25GO - تصفح خفيف", callback_data="25GO")])
    if user_credits['credits_35go'] > 0:
        keyboard.append([InlineKeyboardButton("35GO - استخدام متوسط", callback_data="35GO")])
    if user_credits['credits_60go'] > 0:
        keyboard.append([InlineKeyboardButton("60GO - استخدام ثقيل", callback_data="60GO")])
    # keyboard.append([InlineKeyboardButton("🔙 تغيير الرقم", callback_data="retry_phone")])
    
    if not any([user_credits['credits_25go'], user_credits['credits_35go'], user_credits['credits_60go']]):
        keyboard = [[InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")]]
        await query.edit_message_text(
            "❌ ليس لديك رصيد كافي من أي عرض.\nاشحن رصيدك الآن!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ تم تأكيد رقم الهاتف!\n\n"
        f"📦 الخطوة 3 من 3: اختر عرضًا متاحًا، {code}:",
        reply_markup=reply_markup
    )
    logger.info(f"User {code} confirmed phone, transitioning to OFFER state")
    return OFFER

async def retry_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📱 أدخل رقم هاتفك مرة أخرى (8 أرقام، مثل 99000111)."
    )
    logger.info(f"User retrying phone entry")
    return PHONE

async def offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if 'credits' not in context.user_data:
        await query.edit_message_text("❌ خطأ: ابدأ من جديد بـ /start.")
        return ConversationHandler.END
    
    selected_offer = query.data
    phone_number = context.user_data['phone_number']
    code = context.user_data['code']
    user_credits = context.user_data['credits']
    
    credit_type = f'credits_{selected_offer.lower()}'
    if user_credits.get(credit_type, 0) <= 0:
        keyboard = [[InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"❌ ليس لديك رصيد كافي لعرض {selected_offer}!\nاشحن رصيدك أو اختر عرضًا آخر.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    order_id = create_order(code, phone_number, selected_offer, context.user_data['telegram_id'])
    update_user_phone(code, phone_number)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_{order_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📦 طلب جديد #{order_id}!\nالكود: {code}\nالتلفون: `{phone_number}`\nالعرض: {selected_offer}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    credits_summary = (
        "💳 رصيدك الحالي:\n"
        f"• 25GO: {user_credits['credits_25go']}\n"
        f"• 35GO: {user_credits['credits_35go']}\n"
        f"• 60GO: {user_credits['credits_60go']}"
    )
    
    await query.edit_message_text(
        f"🎉 تم إرسال طلبك، {code}!\n\n"
        f"📱 الرقم: {phone_number}\n"
        f"📦 العرض: {selected_offer}\n"
        f"{credits_summary}\n\n"
        "⏳ في انتظار تأكيد الإدارة.\n❓ للدعم: @Support"
    )
    logger.info(f"Order {order_id} created for user {code}, offer: {selected_offer}")
    return ConversationHandler.END

async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    code = parts[1] if len(parts) >= 2 else None
    
    if not code:
        await query.edit_message_text("❌ خطأ: ابدأ من جديد بـ /start.")
        return ConversationHandler.END
    
    user = get_user_by_code(code)
    if not user:
        await query.edit_message_text("❌ الكود غير موجود. ابدأ بـ /start أو تواصل مع @Support.")
        return ConversationHandler.END
    
    user_credits = get_user_credits(code)
    if not user_credits:
        await query.edit_message_text("⚠️ خطأ في تحميل رصيدك. تواصل مع @Support.")
        return ConversationHandler.END
    
    total_credits = user_credits['credits_25go'] + user_credits['credits_35go'] + user_credits['credits_60go']
    
    context.user_data['code'] = code
    context.user_data['credits'] = user_credits
    context.user_data['telegram_id'] = query.from_user.id
    
    credits_summary = (
        "💳 رصيدك الحالي:\n"
        f"• 25GO: {user_credits['credits_25go']}\n"
        f"• 35GO: {user_credits['credits_35go']}\n"
        f"• 60GO: {user_credits['credits_60go']}"
    )
    
    if total_credits <= 0:
        keyboard = [[InlineKeyboardButton("💰 شحن الرصيد", callback_data="refill_credits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🔄 حاول مرة أخرى، {code}!\n{credits_summary}\n\n"
            "❌ ليس لديك رصيد كافي. اشحن الآن!",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"🔄 حاول مرة أخرى، {code}!\n{credits_summary}\n\n"
        "📱 الخطوة 2 من 3: أدخل رقم هاتفك (8 أرقام، مثل 99000111)."
    )
    logger.info(f"User {code} retrying order")
    return PHONE
