import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from database import (
    get_all_users, get_pending_orders, get_order_details, update_order_status,
    add_or_update_user, delete_user, deduct_credit, update_user_credits, get_user_by_code, get_user_credits
)
from constants import (
    REJECT_REASON, ADMIN_ADD_CODE, ADMIN_ADD_CREDITS, ADMIN_ENTER_CREDITS,
    ADMIN_SELECT_CREDIT_TYPE, ADMIN_ALTER_CREDIT, ADMIN_ID, TX_VERIFICATION_STATE
)

logger = logging.getLogger(__name__)

async def send_user_notification(context: ContextTypes.DEFAULT_TYPE, telegram_id: str, message: str, 
                               keyboard: list = None, order_id: int = None, code: str = None) -> bool:
    """
    Helper to send notifications to users with consistent formatting and error handling.
    
    Args:
        context: Telegram context
        telegram_id: User's Telegram ID
        message: Notification message
        keyboard: Optional inline keyboard
        order_id: Optional order ID for logging
        code: Optional user code for logging
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not telegram_id:
        logger.warning(f"No Telegram ID for user {code or 'unknown'} (order {order_id or 'unknown'})")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ فشل إرسال إشعار للمستخدم {code or 'غير معروف'} (طلب #{order_id or 'غير معروف'}): لا يوجد معرف تلغرام."
        )
        return False

    try:
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await context.bot.send_message(
            chat_id=telegram_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Sent notification to user {code or 'unknown'} (Telegram ID: {telegram_id}, order: {order_id or 'none'})")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to user {code or 'unknown'} (Telegram ID: {telegram_id}): {e}")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ فشل إرسال إشعار للمستخدم {code or 'غير معروف'} (طلب #{order_id or 'غير معروف'}). الرجاء إعلامه يدوياً."
        )
        return False

async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="admin_view_users")],
        [InlineKeyboardButton("📋 عرض الطلبات", callback_data="admin_view_orders")],
        [InlineKeyboardButton("➕ إضافة مستخدم", callback_data="admin_add_user")],
        [InlineKeyboardButton("🔄 تعديل رصيد مستخدم", callback_data="admin_alter_credit")],
        [InlineKeyboardButton("❌ حذف مستخدم", callback_data="admin_delete_user")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "📊 *لوحة تحكم الإدارة*\nاختر إحدى الخيارات:"
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def admin_handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    
    logger.info(f"Admin dashboard action: {action}")
    
    if action == "admin_dashboard":
        await show_admin_dashboard(update, context)
        return ConversationHandler.END
    
    elif action == "admin_view_users":
        users = get_all_users()
        
        if not users:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ *ما فيش مستخدمين في القاعدة.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        response = "*المستخدمين:*\n"
        for user in users:
            user_credits = get_user_credits(user[0]) or {'credits_25go': 0, 'credits_35go': 0, 'credits_60go': 0}
            credits_info = (
                f"• 25GO: {user_credits['credits_25go']}\n"
                f"• 35GO: {user_credits['credits_35go']}\n"
                f"• 60GO: {user_credits['credits_60go']}"
            )
            response += f"الكود: {user[0]}\n{credits_info}\nالتلفون: {user[2] or 'غير متوفر'}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(response) > 4000:
            response = response[:3950] + "\n*...(تم اختصار القائمة لكبر حجمها)*"
        
        await query.edit_message_text(response, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END
    
    elif action == "admin_view_orders":
        orders = get_pending_orders()
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if not orders:
            await query.edit_message_text(
                "❌ *ما فيش طلبات معلقة.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        order_buttons = []
        for o in orders:
            order_buttons.append([InlineKeyboardButton(
                f"طلب #{o[0]}: {o[1]} - {o[3]}",
                callback_data=f"view_order_{o[0]}"
            )])
        
        order_buttons.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")])
        orders_markup = InlineKeyboardMarkup(order_buttons)
        
        await query.edit_message_text(
            "📋 *الطلبات المعلقة:*",
            reply_markup=orders_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif action == "admin_add_user":
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "➕ *أدخل كود المستخدم الجديد:*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return ADMIN_ADD_CODE
    
    elif action == "admin_alter_credit":
        users = get_all_users()
        
        if not users:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ *ما فيش مستخدمين لتعديل الرصيد.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        user_buttons = []
        for user in users:
            user_credits = get_user_credits(user[0]) or {'credits_25go': 0, 'credits_35go': 0, 'credits_60go': 0}
            credits_info = (
                f"25GO: {user_credits['credits_25go']}, "
                f"35GO: {user_credits['credits_35go']}, "
                f"60GO: {user_credits['credits_60go']}"
            )
            user_buttons.append([InlineKeyboardButton(
                f"{user[0]} ({credits_info})",
                callback_data=f"alter_credit_{user[0]}"
            )])
        
        user_buttons.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")])
        users_markup = InlineKeyboardMarkup(user_buttons)
        
        await query.edit_message_text(
            "🔄 *اختر المستخدم لتعديل الرصيد:*",
            reply_markup=users_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif action == "admin_delete_user":
        users = get_all_users()
        
        if not users:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ *ما فيش مستخدمين للحذف.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        user_buttons = []
        for user in users:
            user_buttons.append([InlineKeyboardButton(
                f"حذف {user[0]}",
                callback_data=f"confirm_delete_{user[0]}"
            )])
        
        user_buttons.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")])
        users_markup = InlineKeyboardMarkup(user_buttons)
        
        await query.edit_message_text(
            "🗑️ *اختر المستخدم للحذف:*",
            reply_markup=users_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    return ConversationHandler.END

async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin {update.message.from_user.id} attempted to add user")
        return ConversationHandler.END
    
    code = update.message.text.strip()
    context.user_data['new_user_code'] = code
    
    keyboard = [
        [InlineKeyboardButton("25GO", callback_data="add_25go")],
        [InlineKeyboardButton("35GO", callback_data="add_35go")],
        [InlineKeyboardButton("60GO", callback_data="add_60go")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"➕ *اختر نوع الرصيد للمستخدم {code}:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ADMIN_ADD_CREDITS

async def admin_add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    credit_type = query.data.replace("add_", "")
    context.user_data['credit_type'] = credit_type
    
    logger.info(f"Admin adding credits for user {context.user_data.get('new_user_code')}, type: {credit_type}")
    
    await query.edit_message_text(
        f"💰 *أدخل عدد النقاط للمستخدم {context.user_data['new_user_code']} (نوع الرصيد: {credit_type.upper()}):*",
        parse_mode="Markdown"
    )
    return ADMIN_ENTER_CREDITS

async def admin_enter_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin {update.message.from_user.id} attempted to add credits")
        return ConversationHandler.END
    
    logger.info(f"Processing credit input for user {context.user_data.get('new_user_code')}")
    
    try:
        credits = int(update.message.text)
        code = context.user_data.get('new_user_code')
        credit_type = context.user_data.get('credit_type')
        
        if not code or not credit_type:
            logger.error("Missing code or credit_type in context.user_data")
            await update.message.reply_text(
                "⚠️ *حدث خطأ. حاول مرة أخرى.*",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        if credit_type not in ['25go', '35go', '60go']:
            logger.error(f"Invalid credit type: {credit_type}")
            await update.message.reply_text(
                "❌ *نوع الرصيد غير صالح.*",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        user_credits = get_user_credits(code) or {
            'credits_25go': 0,
            'credits_35go': 0,
            'credits_60go': 0
        }
        
        user_credits[f'credits_{credit_type}'] = credits
        user = get_user_by_code(code)
        if not user:
            logger.error(f"User with code {code} not found")
            return False

        # Extract existing telegram_id (index 5 in user tuple, based on database.py)
        telegram_id = user[5] if len(user) > 5 else None
        try:
            add_or_update_user(
                code,
                user_credits['credits_25go'],
                user_credits['credits_35go'],
                user_credits['credits_60go'],
                telegram_id=telegram_id
            )
            logger.info(f"Updated credits for user {code}: {user_credits}")
        except Exception as e:
            logger.error(f"Failed to update user {code}: {e}")
            await update.message.reply_text(
                "⚠️ *فشل تحديث الرصيد. حاول مرة أخرى.*",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *تم إضافة/تحديث المستخدم {code}*\n"
            f"• 25GO: {user_credits['credits_25go']}\n"
            f"• 35GO: {user_credits['credits_35go']}\n"
            f"• 60GO: {user_credits['credits_60go']}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except ValueError:
        logger.warning(f"Invalid credit input: {update.message.text}")
        await update.message.reply_text(
            "❌ *يرجى إدخال رقم صحيح للنقاط.*",
            parse_mode="Markdown"
        )
        return ADMIN_ENTER_CREDITS
    
    return ConversationHandler.END

async def select_user_for_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, code = query.data.partition('_credit_')
    context.user_data['alter_credit_code'] = code
    
    user_credits = get_user_credits(code)
    if not user_credits:
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ *المستخدم غير موجود.*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    context.user_data['current_credits'] = user_credits
    
    keyboard = [
        [InlineKeyboardButton("25GO", callback_data="edit_25go")],
        [InlineKeyboardButton("35GO", callback_data="edit_35go")],
        [InlineKeyboardButton("60GO", callback_data="edit_60go")],
        [InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"*المستخدم: {code}*\n"
        f"*الرصيد الحالي:*\n"
        f"• 25GO: {user_credits['credits_25go']}\n"
        f"• 35GO: {user_credits['credits_35go']}\n"
        f"• 60GO: {user_credits['credits_60go']}\n\n"
        f"اختر نوع الرصيد لتعديله:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ADMIN_SELECT_CREDIT_TYPE

async def admin_select_credit_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    credit_type = query.data.replace("edit_", "")
    context.user_data['credit_type'] = credit_type
    
    current_value = context.user_data['current_credits'][f'credits_{credit_type}']
    
    await query.edit_message_text(
        f"💰 *أدخل الرصيد الجديد لنوع {credit_type.upper()} (الحالي: {current_value}):*",
        parse_mode="Markdown"
    )
    return ADMIN_ALTER_CREDIT

async def admin_alter_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin {update.message.from_user.id} attempted to alter credit")
        return ConversationHandler.END
    
    try:
        new_credits = int(update.message.text)
        code = context.user_data.get('alter_credit_code')
        credit_type = context.user_data.get('credit_type')
        current_credits = context.user_data.get('current_credits')
        
        if not code or not credit_type or not current_credits:
            await update.message.reply_text(
                "⚠️ *حدث خطأ. حاول مرة أخرى.*",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        current_credits[f'credits_{credit_type}'] = new_credits
        user = get_user_by_code(code)
        if not user:
            logger.error(f"User with code {code} not found")
            return False

        # Extract existing telegram_id (index 5 in user tuple, based on database.py)
        telegram_id = user[5] if len(user) > 5 else None
        add_or_update_user(
            code,
            current_credits['credits_25go'],
            current_credits['credits_35go'],
            current_credits['credits_60go'],
            telegram_id=telegram_id
        )
        
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *تم تعديل رصيد المستخدم {code}*\n"
            f"• 25GO: {current_credits['credits_25go']}\n"
            f"• 35GO: {current_credits['credits_35go']}\n"
            f"• 60GO: {current_credits['credits_60go']}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text(
            "❌ *يرجى إدخال رقم صحيح للرصيد.*",
            parse_mode="Markdown"
        )
        return ADMIN_ALTER_CREDIT
    
    return ConversationHandler.END

async def view_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, order_id = query.data.partition('_order_')
    order_id = int(order_id)
    
    order = get_order_details(order_id)
    if not order:
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ *الطلب غير موجود.*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    code, phone, telegram_id, offer, status = order
    
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_{order_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{order_id}")
        ],
        [InlineKeyboardButton("🔙 العودة للطلبات", callback_data="admin_view_orders")],
        [InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"*تفاصيل الطلب #{order_id}:*\n"
        f"• الكود: {code}\n"
        f"• التلفون: {phone}\n"
        f"• العرض: {offer}\n"
        f"• الحالة: {status}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def confirm_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, code = query.data.partition('_delete_')
    
    deleted = delete_user(code)
    
    keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if deleted:
        message = f"✅ *تم حذف المستخدم {code} بنجاح.*"
    else:
        message = f"❌ *فشل حذف المستخدم {code}. ربما تم حذفه مسبقاً.*"
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

async def admin_handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action = parts[0]
    order_id = int(parts[1])
    
    logger.info(f"Handling order action: {action} for order_id: {order_id}")
    
    order = get_order_details(order_id)
    if not order or order[4] != 'pending':
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await query.edit_message_text(
            "❌ *الطلب غير موجود أو تم معالجته.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        logger.error(f"Invalid order: {order_id}, details: {order}")
        return ConversationHandler.END
    
    code, phone, telegram_id, offer, status = order
    
    if action == "accept":
        user = get_user_by_code(code)
        if not user:
            keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            await query.edit_message_text(
                f"❌ *المستخدم {code} غير موجود.*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        success = deduct_credit(code, offer)
        if not success:
            keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            await query.edit_message_text(
                f"❌ *المستخدم {code} ليس لديه رصيد كافٍ.*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        update_order_status(order_id, 'confirmed')
        
        user_credits = get_user_credits(code) or {
            'credits_25go': 0,
            'credits_35go': 0,
            'credits_60go': 0
        }
        credits_summary = (
            f"• 25GO: {user_credits['credits_25go']}\n"
            f"• 35GO: {user_credits['credits_35go']}\n"
            f"• 60GO: {user_credits['credits_60go']}"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *تم تأكيد الطلب #{order_id}*\n"
            f"• الكود: {code}\n"
            f"• الرقم: {phone}\n"
            f"• العرض: {offer}\n"
            f"• رصيد المستخدم:\n{credits_summary}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        user_message = (
            f"🎉 *تم قبول طلبك #{order_id}!*\n"
            f"• الرقم: {phone}\n"
            f"• العرض: {offer}\n"
            f"• رصيدك المتبقي:\n{credits_summary}\n\n"
            f"نشكرك على استخدام خدماتنا! إذا كنت بحاجة إلى مساعدة، تواصل مع @Support."
        )
        user_keyboard = [
            [InlineKeyboardButton("📝 طلب جديد", callback_data=f"retry_{code}")],
            [InlineKeyboardButton("💰 عرض الرصيد", callback_data=f"check_credits_{code}")],
            [InlineKeyboardButton("📞 الدعم", url="https://t.me/Support")]
        ]
        await send_user_notification(context, telegram_id, user_message, user_keyboard, order_id, code)
        logger.info(f"Order {order_id} accepted")
        return ConversationHandler.END
    
    elif action == "reject":
        context.user_data['reject_order_id'] = order_id
        context.user_data['reject_code'] = code
        context.user_data['reject_phone'] = phone
        context.user_data['reject_offer'] = offer
        
        logger.debug(f"Set reject data: order_id={order_id}, code={code}, phone={phone}, offer={offer}")
        
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_reject")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                f"📝 *أدخل سبب رفض الطلب #{order_id}:*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to edit message for order {order_id}: {e}")
            await query.message.reply_text("⚠️ Error prompting for rejection reason")
            return ConversationHandler.END
        
        logger.info(f"Returning state REJECT_REASON: {REJECT_REASON} for order {order_id}")
        return REJECT_REASON
    
    logger.warning(f"Unknown action: {action} for order_id: {order_id}")
    return ConversationHandler.END

async def admin_reject_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin {update.message.from_user.id} attempted to reject order")
        return ConversationHandler.END
    
    reason = update.message.text.strip()
    if not reason:
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_reject")]]
        await update.message.reply_text(
            "❌ *يرجى إدخال سبب صالح للرفض.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return REJECT_REASON
    
    order_id = context.user_data.get('reject_order_id')
    code = context.user_data.get('reject_code')
    phone = context.user_data.get('reject_phone')
    offer = context.user_data.get('reject_offer')
    
    logger.debug(f"Rejection data: order_id={order_id}, code={code}, phone={phone}, offer={offer}")
    
    if not all([order_id, code, phone, offer]):
        logger.error(f"Missing rejection data: order_id={order_id}, code={code}, phone={phone}, offer={offer}")
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await update.message.reply_text(
            "⚠️ *حدث خطأ في بيانات الطلب.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    try:
        user = get_user_by_code(code)
        if not user:
            logger.error(f"User {code} not found")
            keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            await update.message.reply_text(
                f"❌ *المستخدم {code} غير موجود.*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        telegram_id = user[5] if len(user) > 5 else None
        logger.debug(f"User found: code={code}, telegram_id={telegram_id}")
        
        update_order_status(order_id, 'rejected', reason)
        logger.info(f"Order {order_id} rejected with reason: {reason}")
        
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await update.message.reply_text(
            f"❌ *تم رفض الطلب #{order_id}*\n"
            f"• الكود: {code}\n"
            f"• الرقم: {phone}\n"
            f"• العرض: {offer}\n"
            f"• السبب: {reason}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
        user_message = (
            f"❌ *تم رفض طلبك #{order_id}*\n"
            f"• الرقم: {phone}\n"
            f"• العرض: {offer}\n"
            f"• السبب: {reason}\n\n"
            f"يمكنك المحاولة مجدداً أو التواصل مع الدعم لمزيد من المساعدة."
        )
        user_keyboard = [
            [InlineKeyboardButton("📝 محاولة مرة أخرى", callback_data=f"retry_{code}")],
            [InlineKeyboardButton("📞 الدعم", url="https://t.me/Support")]
        ]
        await send_user_notification(context, telegram_id, user_message, user_keyboard, order_id, code)
    except Exception as e:
        logger.error(f"Error processing rejection for order {order_id}: {e}", exc_info=True)
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await update.message.reply_text(
            f"⚠️ *حدث خطأ أثناء رفض الطلب #{order_id}: {str(e)}*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    for key in ['reject_order_id', 'reject_code', 'reject_phone', 'reject_offer']:
        context.user_data.pop(key, None)
    
    logger.info(f"Rejection completed for order {order_id}")
    return ConversationHandler.END

async def cancel_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await show_admin_dashboard(update, context)
    return ConversationHandler.END

async def handle_refill_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    action = data_parts[0]
    
    if len(data_parts) >= 5 and data_parts[1] == "refill":
        code = data_parts[2]
        sanitized_tx_id = data_parts[3]
        credit_type = data_parts[4]
    else:
        logger.error(f"Invalid callback data: {query.data}")
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await query.edit_message_text(
            "⚠️ *خطأ في بيانات الطلب.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    if credit_type not in ['25go', '35go', '60go']:
        logger.error(f"Invalid credit type: {credit_type}")
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await query.edit_message_text(
            "❌ *نوع الرصيد غير صالح.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    context.user_data['refill_code'] = code
    context.user_data['refill_tx_id'] = sanitized_tx_id
    context.user_data['refill_offer'] = credit_type
    
    user = get_user_by_code(code)
    if not user:
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await query.edit_message_text(
            f"❌ *المستخدم {code} غير موجود.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    telegram_id = user[5] if len(user) > 5 else None
    
    if action == "confirm":
        user_credits = get_user_credits(code) or {
            'credits_25go': 0,
            'credits_35go': 0,
            'credits_60go': 0
        }
        
        added_credits = 50
        user_credits[f'credits_{credit_type}'] += added_credits
        
        try:
            add_or_update_user(
                code,
                user_credits['credits_25go'],
                user_credits['credits_35go'],
                user_credits['credits_60go'],
                telegram_id=telegram_id
            )
            logger.info(f"Added {added_credits} {credit_type} credits for user {code}")
        except Exception as e:
            logger.error(f"Failed to update credits for user {code}: {e}")
            keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            await query.edit_message_text(
                "⚠️ *فشل تحديث الرصيد.*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        credit_type_arabic = {'25go': '25 جيجا', '35go': '35 جيجا', '60go': '60 جيجا'}.get(credit_type)
        amount_paid = {'25go': '150 USDT', '35go': '295 USDT', '60go': '400 USDT'}.get(credit_type)
        
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await query.edit_message_text(
            f"✅ *تم تأكيد شحن الرصيد*\n"
            f"• الكود: {code}\n"
            f"• نوع الرصيد: {credit_type_arabic}\n"
            f"• المبلغ: {amount_paid}\n"
            f"• المعاملة: {sanitized_tx_id}\n"
            f"• الرصيد الجديد:\n"
            f"  - 25GO: {user_credits['credits_25go']}\n"
            f"  - 35GO: {user_credits['credits_35go']}\n"
            f"  - 60GO: {user_credits['credits_60go']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
        user_message = (
            f"🎉 *تم شحن رصيدك بنجاح!*\n"
            f"• نوع الرصيد: {credit_type_arabic}\n"
            f"• النقاط المضافة: {added_credits}\n"
            f"• المبلغ: {amount_paid}\n"
            f"• المعاملة: {sanitized_tx_id}\n"
            f"• رصيدك الحالي:\n"
            f"  - 25GO: {user_credits['credits_25go']}\n"
            f"  - 35GO: {user_credits['credits_35go']}\n"
            f"  - 60GO: {user_credits['credits_60go']}\n\n"
            f"ابدأ طلباً جديداً الآن أو تواصل مع الدعم إذا كنت بحاجة إلى مساعدة!"
        )
        user_keyboard = [
            [InlineKeyboardButton("📝 طلب جديد", callback_data=f"retry_{code}")],
            [InlineKeyboardButton("💰 عرض الرصيد", callback_data=f"check_credits_{code}")],
            [InlineKeyboardButton("📞 الدعم", url="https://t.me/Support")]
        ]
        await send_user_notification(context, telegram_id, user_message, user_keyboard, code=code)
    
    elif action == "reject":
        context.user_data['refill_reject_code'] = code
        context.user_data['refill_reject_tx_id'] = sanitized_tx_id
        context.user_data['refill_reject_credit_type'] = credit_type
        
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_reject")]]
        await query.edit_message_text(
            f"📝 *أدخل سبب رفض شحن الرصيد للمستخدم {code}:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return REJECT_REASON
    
    return ConversationHandler.END

async def admin_refill_reject_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin {update.message.from_user.id} attempted to reject refill")
        return ConversationHandler.END
    
    reason = update.message.text.strip()
    if not reason:
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_reject")]]
        await update.message.reply_text(
            "❌ *يرجى إدخال سبب صالح للرفض.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return REJECT_REASON
    
    code = context.user_data.get('refill_reject_code')
    sanitized_tx_id = context.user_data.get('refill_reject_tx_id')
    credit_type = context.user_data.get('refill_reject_credit_type')
    
    if not all([code, sanitized_tx_id, credit_type]):
        logger.error(f"Missing refill rejection data: code={code}, tx_id={sanitized_tx_id}, credit_type={credit_type}")
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await update.message.reply_text(
            "⚠️ *حدث خطأ في بيانات الرفض.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    user = get_user_by_code(code)
    if not user:
        keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        await update.message.reply_text(
            f"❌ *المستخدم {code} غير موجود.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    telegram_id = user[5] if len(user) > 5 else None
    credit_type_arabic = {'25go': '25 جيجا', '35go': '35 جيجا', '60go': '60 جيجا'}.get(credit_type)
    
    keyboard = [[InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]]
    await update.message.reply_text(
        f"❌ *تم رفض شحن الرصيد*\n"
        f"• الكود: {code}\n"
        f"• نوع الرصيد: {credit_type_arabic}\n"
        f"• المعاملة: {sanitized_tx_id}\n"
        f"• السبب: {reason}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    user_message = (
        f"❌ *تم رفض طلب شحن رصيدك*\n"
        f"• نوع الرصيد: {credit_type_arabic}\n"
        f"• المعاملة: {sanitized_tx_id}\n"
        f"• السبب: {reason}\n\n"
        f"يرجى مراجعة التفاصيل والمحاولة مجدداً أو التواصل مع الدعم."
    )
    user_keyboard = [
        [InlineKeyboardButton("🔄 محاولة مرة أخرى", callback_data=f"retry_refill_{code}")],
        [InlineKeyboardButton("📞 الدعم", url="https://t.me/Support")]
    ]
    await send_user_notification(context, telegram_id, user_message, user_keyboard, code=code)
    
    for key in ['refill_reject_code', 'refill_reject_tx_id', 'refill_reject_credit_type']:
        context.user_data.pop(key, None)
    
    return ConversationHandler.END