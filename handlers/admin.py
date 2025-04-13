import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from database import (
    get_all_users, get_pending_orders, get_order_details, update_order_status,
    add_or_update_user, delete_user, deduct_credit, update_user_credits, get_user_by_code, get_user_credits
)
from constants import *
from .common import cancel

logger = logging.getLogger(__name__)

async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="admin_view_users")],
        [InlineKeyboardButton("📋 عرض الطلبات", callback_data="admin_view_orders")],
        [InlineKeyboardButton("➕ إضافة مستخدم", callback_data="admin_add_user")],
        [InlineKeyboardButton("🔄 تعديل رصيد مستخدم", callback_data="admin_alter_credit")],
        [InlineKeyboardButton("❌ حذف مستخدم", callback_data="admin_delete_user")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            "لوحة تحكم الإدارة\nاختر إحدى الخيارات:",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            "لوحة تحكم الإدارة\nاختر إحدى الخيارات:",
            reply_markup=reply_markup
        )

async def admin_handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    
    if action == "admin_dashboard":
        await show_admin_dashboard(update, context)
        return ConversationHandler.END
    
    elif action == "admin_view_users":
        users = get_all_users()
        
        if not users:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "ما فماش مستخدمين في القاعدة.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        response = "المستخدمين:\n"
        for user in users:
            user_credits = get_user_credits(user[0])
            credits_info = (
                f"25GO: {user_credits['credits_25go']}, "
                f"35GO: {user_credits['credits_35go']}, "
                f"60GO: {user_credits['credits_60go']}"
            )
            response += f"الكود: {user[0]}, الرصيد: {credits_info}, التلفون: {user[2] or 'غير متوفر'}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(response) > 4000:
            response = response[:3950] + "\n...(تم اختصار القائمة لكبر حجمها)"
        
        await query.edit_message_text(response, reply_markup=reply_markup)
        return ConversationHandler.END
    
    elif action == "admin_view_orders":
        orders = get_pending_orders()
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if not orders:
            await query.edit_message_text(
                "ما فماش طلبات في الانتظار.",
                reply_markup=reply_markup
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
            "الطلبات المعلقة:",
            reply_markup=orders_markup
        )
        return ConversationHandler.END
    
    elif action == "admin_add_user":
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "أدخل كود المستخدم الجديد:",
            reply_markup=reply_markup
        )
        return ADMIN_ADD_CODE
    
    elif action == "admin_alter_credit":
        users = get_all_users()
        
        if not users:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "ما فماش مستخدمين لتعديل الرصيد.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        user_buttons = []
        for user in users:
            user_credits = get_user_credits(user[0])
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
            "اختر المستخدم لتعديل الرصيد:",
            reply_markup=users_markup
        )
        return ConversationHandler.END
    
    elif action == "admin_delete_user":
        users = get_all_users()
        
        if not users:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "ما فماش مستخدمين للحذف.",
                reply_markup=reply_markup
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
            "اختر المستخدم للحذف:",
            reply_markup=users_markup
        )
        return ConversationHandler.END
    
    return ConversationHandler.END

async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    code = update.message.text
    context.user_data['new_user_code'] = code
    
    keyboard = [
        [InlineKeyboardButton("25GO", callback_data="add_25go")],
        [InlineKeyboardButton("35GO", callback_data="add_35go")],
        [InlineKeyboardButton("60GO", callback_data="add_60go")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"اختر نوع الرصيد لإضافته للمستخدم {code}:",
        reply_markup=reply_markup
    )
    return ADMIN_ADD_CREDITS

async def admin_add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    credit_type = query.data.replace("add_", "")
    context.user_data['credit_type'] = credit_type
    
    logger.info(f"Admin adding credits for user {context.user_data.get('new_user_code')}, type: {credit_type}")
    
    await query.edit_message_text(
        f"أدخل عدد النقاط للمستخدم {context.user_data['new_user_code']} (نوع الرصيد: {credit_type.upper()}):"
    )
    logger.info(f"Transitioning to state: ADMIN_ENTER_CREDITS ({ADMIN_ENTER_CREDITS})")
    return ADMIN_ENTER_CREDITS

async def admin_enter_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        logger.warning("Non-admin attempted to add credits")
        return ConversationHandler.END
    
    logger.info(f"Processing credit input for user {context.user_data.get('new_user_code')}")
    
    try:
        credits = int(update.message.text)
        code = context.user_data.get('new_user_code')
        credit_type = context.user_data.get('credit_type')
        
        if not code or not credit_type:
            logger.error("Missing code or credit_type in context.user_data")
            await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
            return ConversationHandler.END
        
        # Validate credit type
        if credit_type not in ['25go', '35go', '60go']:
            logger.error(f"Invalid credit type: {credit_type}")
            await update.message.reply_text("نوع الرصيد غير صالح.")
            return ConversationHandler.END
        
        # Get current credits
        user_credits = get_user_credits(code) or {
            'credits_25go': 0,
            'credits_35go': 0,
            'credits_60go': 0
        }
        
        # Update the specific credit type
        user_credits[f'credits_{credit_type}'] = credits
        
        # Update user with all credit types
        try:
            add_or_update_user(
                code,
                user_credits['credits_25go'],
                user_credits['credits_35go'],
                user_credits['credits_60go']
            )
            logger.info(f"Successfully updated credits for user {code}: {user_credits}")
        except Exception as e:
            logger.error(f"Failed to update user {code}: {e}")
            await update.message.reply_text("حدث خطأ أثناء تحديث الرصيد. حاول مرة أخرى.")
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ تم إضافة/تحديث المستخدم {code}.\n"
            f"25GO: {user_credits['credits_25go']}\n"
            f"35GO: {user_credits['credits_35go']}\n"
            f"60GO: {user_credits['credits_60go']}",
            reply_markup=reply_markup
        )
        
    except ValueError:
        logger.warning(f"Invalid credit input: {update.message.text}")
        await update.message.reply_text("يرجى إدخال رقم صحيح للنقاط.")
        return ADMIN_ENTER_CREDITS
    
    return ConversationHandler.END

async def select_user_for_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, code = query.data.partition('_credit_')
    context.user_data['alter_credit_code'] = code
    
    user_credits = get_user_credits(code)
    if not user_credits:
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "المستخدم غير موجود.",
            reply_markup=reply_markup
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
        f"المستخدم: {code}\n"
        f"الرصيد الحالي:\n"
        f"25GO: {user_credits['credits_25go']}\n"
        f"35GO: {user_credits['credits_35go']}\n"
        f"60GO: {user_credits['credits_60go']}\n\n"
        f"اختر نوع الرصيد لتعديله:",
        reply_markup=reply_markup
    )
    return ADMIN_SELECT_CREDIT_TYPE

async def admin_select_credit_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    credit_type = query.data.replace("edit_", "")
    context.user_data['credit_type'] = credit_type
    
    current_value = context.user_data['current_credits'][f'credits_{credit_type}']
    
    await query.edit_message_text(
        f"أدخل الرصيد الجديد لنوع {credit_type.upper()} (الحالي: {current_value}):"
    )
    return ADMIN_ALTER_CREDIT

async def admin_alter_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    try:
        new_credits = int(update.message.text)
        code = context.user_data.get('alter_credit_code')
        credit_type = context.user_data.get('credit_type')
        current_credits = context.user_data.get('current_credits')
        
        if not code or not credit_type or not current_credits:
            await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
            return ConversationHandler.END
        
        # Update the specific credit type
        current_credits[f'credits_{credit_type}'] = new_credits
        
        # Update user with all credit types
        add_or_update_user(
            code,
            current_credits['credits_25go'],
            current_credits['credits_35go'],
            current_credits['credits_60go']
        )
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ تم تعديل رصيد المستخدم {code}.\n"
            f"25GO: {current_credits['credits_25go']}\n"
            f"35GO: {current_credits['credits_35go']}\n"
            f"60GO: {current_credits['credits_60go']}",
            reply_markup=reply_markup
        )
    except ValueError:
        await update.message.reply_text("يرجى إدخال رقم صحيح للرصيد.")
        return ADMIN_ALTER_CREDIT
    
    return ConversationHandler.END

async def view_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, order_id = query.data.partition('_order_')
    order_id = int(order_id)
    
    order = get_order_details(order_id)
    if not order:
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "الطلب غير موجود.",
            reply_markup=reply_markup
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
        f"تفاصيل الطلب #{order_id}:\nالكود: {code}\nالتلفون: {phone}\nالعرض: {offer}\nالحالة: {status}",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def confirm_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, code = query.data.partition('_delete_')
    
    deleted = delete_user(code)
    
    if deleted:
        message = f"✅ تم حذف المستخدم {code} بنجاح."
    else:
        message = f"❌ فشل في حذف المستخدم {code}. ربما تم حذفه مسبقاً."
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)
    return ConversationHandler.END

async def admin_handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action = parts[0]
    order_id = int(parts[1])
    
    order = get_order_details(order_id)
    if not order or order[4] != 'pending':  # status is now the 5th column (index 4)
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "الطلب مش موجود أو تم معالجته.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    code, phone, telegram_id, offer, status = order
    
    if action == "accept":
        user = get_user_by_code(code)
        if not user:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"المستخدم {code} غير موجود.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        # Deduct credit only when admin accepts
        success = deduct_credit(code, offer)
        
        if not success:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"المستخدم {code} ما عندوش رصيد كافي.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        update_order_status(order_id, 'confirmed')
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ تم تأكيد الطلب {order_id}.\n"
            f"الكود: {code}\n"
            f"التلفون: {phone}\n"
            f"Telegram ID: {telegram_id}\n"
            f"العرض: {offer}",
            reply_markup=reply_markup
        )
        
        if telegram_id:
            # Get updated credits after deduction
            user_credits = get_user_credits(code)
            if user_credits:
                credits_summary = (
                    f"25GO: {user_credits['credits_25go']}, "
                    f"35GO: {user_credits['credits_35go']}, "
                    f"60GO: {user_credits['credits_60go']}"
                )
            else:
                credits_summary = "غير معروف"
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"تم تأكيد طلبك!\n"
                     f"التلفون: {phone}\n"
                     f"العرض: {offer}\n"
                     f"الرصيد المتبقي: {credits_summary}"
            )    
    elif action == "reject":
        context.user_data['reject_order_id'] = order_id
        context.user_data['reject_code'] = code
        context.user_data['reject_phone'] = phone
        context.user_data['reject_offer'] = offer
        
        keyboard = [[InlineKeyboardButton("إلغاء", callback_data="cancel_reject")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"الرجاء إدخال سبب رفض الطلب رقم {order_id}:",
            reply_markup=reply_markup
        )
        return REJECT_REASON
    
    return ConversationHandler.END

async def cancel_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await show_admin_dashboard(update, context)
    return ConversationHandler.END

async def admin_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    reject_reason = update.message.text
    order_id = context.user_data.get('reject_order_id')
    code = context.user_data.get('reject_code')
    phone = context.user_data.get('reject_phone')
    offer = context.user_data.get('reject_offer')
    
    if not order_id:
        await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END
    
    # Get the complete user record to access the telegram_id
    user = get_user_by_code(code)
    if not user:
        await update.message.reply_text("المستخدم غير موجود.")
        return ConversationHandler.END
    
    # Update order status with rejection reason
    update_order_status(order_id, 'rejected', reject_reason)
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ تم رفض الطلب {order_id}. السبب: {reject_reason}",
        reply_markup=reply_markup
    )
    
    # The telegram_id is at index 5 in the user tuple (based on the DB schema)
    telegram_id = user[5] if len(user) > 5 else None
    
    if telegram_id:
        # Create retry keyboard for the user
        keyboard = [[InlineKeyboardButton("حاول مرة أخرى", callback_data=f"retry_{code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"تم رفض طلبك.\nالتلفون: {phone}\nالعرض: {offer}\nالسبب: {reject_reason}",
                reply_markup=reply_markup
            )
            logger.info(f"Sent rejection notification to user {code} with telegram_id {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send rejection notification to user {code}: {e}")
    else:
        logger.warning(f"Could not send rejection notification to user {code} - no Telegram ID found")
    
    return ConversationHandler.END

async def handle_refill_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for admin confirming or rejecting refill requests"""
    query = update.callback_query
    await query.answer()
    
    # Parse the callback data (format: action_refill_code_txid_credit_type)
    data_parts = query.data.split('_')
    action = data_parts[0]  # confirm or reject
    
    if len(data_parts) >= 5 and data_parts[1] == "refill":
        code = data_parts[2]
        sanitized_tx_id = data_parts[3]
        credit_type = data_parts[4]  # e.g., 25go, 35go, 60go
    else:
        logger.error(f"Invalid callback data for refill confirmation: {query.data}")
        await query.edit_message_text("خطأ في بيانات الطلب")
        return ConversationHandler.END
    
    # Validate credit type
    if credit_type not in ['25go', '35go', '60go']:
        logger.error(f"Invalid credit type: {credit_type}")
        await query.edit_message_text("نوع الرصيد غير صالح")
        return ConversationHandler.END
    
    # Store in context for logging
    context.user_data['refill_code'] = code
    context.user_data['refill_tx_id'] = sanitized_tx_id
    context.user_data['refill_offer'] = credit_type
    
    # Get the complete user record including telegram_id
    user = get_user_by_code(code)
    if not user:
        logger.error(f"User not found: {code}")
        await query.edit_message_text(f"المستخدم {code} غير موجود.")
        return ConversationHandler.END
    
    if action == "confirm":
        # Get current credits
        user_credits = get_user_credits(code) or {
            'credits_25go': 0,
            'credits_35go': 0,
            'credits_60go': 0
        }
        
        # Add 50 credits to the selected type
        added_credits = 50
        user_credits[f'credits_{credit_type}'] += added_credits
        
        # Update user credits
        try:
            add_or_update_user(
                code,
                user_credits['credits_25go'],
                user_credits['credits_35go'],
                user_credits['credits_60go']
            )
            logger.info(f"Successfully added {added_credits} {credit_type} credits for user {code}")
        except Exception as e:
            logger.error(f"Failed to update credits for user {code}: {e}")
            await query.edit_message_text("حدث خطأ أثناء تحديث الرصيد. حاول مرة أخرى.")
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Prepare credit type name in Arabic for the message
        credit_type_arabic = {
            '25go': '25 جيجا',
            '35go': '35 جيجا',
            '60go': '60 جيجا'
        }.get(credit_type, credit_type.upper())
        
        # Prepare the amount paid in Arabic for the message
        amount_paid = {
            '25go': '150 USDT',
            '35go': '295 USDT',
            '60go': '400 USDT'
        }.get(credit_type, 'غير معروف')
        
        # Admin confirmation message
        await query.edit_message_text(
            f"✅ تم تأكيد شحن الرصيد بنجاح!\n\n"
            f"• الكود: {code}\n"
            f"• نوع الرصيد: {credit_type_arabic}\n"
            f"• المبلغ: {amount_paid}\n"
            f"• رقم المعاملة: {sanitized_tx_id}\n\n"
            f"الرصيد الجديد:\n"
            f"- 25GO: {user_credits['credits_25go']}\n"
            f"- 35GO: {user_credits['credits_35go']}\n"
            f"- 60GO: {user_credits['credits_60go']}",
            reply_markup=reply_markup
        )
        
        # Notify user with a detailed message
        telegram_id = user[5] if len(user) > 5 else None
        
        if telegram_id:
            try:
                # Create a keyboard for the user to start a new order
                keyboard = [
                    [InlineKeyboardButton("بدء طلب جديد", callback_data=f"retry_{code}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send notification to user
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🎉 تم قبول معاملتك بنجاح!\n\n"
                         f"• نوع الباقة: {credit_type_arabic}\n"
                         f"• المبلغ: {amount_paid}\n"
                         f"• رقم المعاملة: {sanitized_tx_id}\n\n"
                         f"تم إضافة 50 رصيد إلى حسابك:\n"
                         f"- 25GO: {user_credits['credits_25go']}\n"
                         f"- 35GO: {user_credits['credits_35go']}\n"
                         f"- 60GO: {user_credits['credits_60go']}\n\n"
                         f"يمكنك الآن البدء في طلب جديد.",
                    reply_markup=reply_markup
                )
                logger.info(f"Successfully notified user {code} (Telegram ID: {telegram_id}) about accepted transaction")
            except Exception as e:
                logger.error(f"Failed to send confirmation to user {code}: {e}")
                # Notify admin if user notification failed
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ تمت إضافة الرصيد للمستخدم {code} ولكن فشل إرسال الإشعار له.\n"
                         f"الرجاء إعلامه يدوياً."
                )
        else:
            logger.warning(f"Could not notify user {code} - no Telegram ID found")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ تمت إضافة الرصيد للمستخدم {code} ولكن لا يوجد معرف تلغرام مسجل.\n"
                     f"الرجاء إعلامه يدوياً."
            )
    
    elif action == "reject":
        # Handle rejection
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Prepare credit type name in Arabic for the message
        credit_type_arabic = {
            '25go': '25 جيجا',
            '35go': '35 جيجا',
            '60go': '60 جيجا'
        }.get(credit_type, credit_type.upper())
        
        await query.edit_message_text(
            f"❌ تم رفض طلب شحن الرصيد للمستخدم {code} (نوع الرصيد: {credit_type_arabic}).",
            reply_markup=reply_markup
        )
        
        # Notify user about rejection
        telegram_id = user[5] if len(user) > 5 else None
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"❌ تم رفض طلب شحن الرصيد الخاص بك (نوع الرصيد: {credit_type_arabic}).\n"
                         f"الرجاء التأكد من صحة المعاملة أو التواصل مع الإدارة."
                )
                logger.info(f"Sent rejection notification to user {code} (Telegram ID: {telegram_id})")
            except Exception as e:
                logger.error(f"Failed to send rejection to user {code}: {e}")
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ تم رفض طلب الرصيد للمستخدم {code} ولكن فشل إرسال الإشعار له.\n"
                         f"الرجاء إعلامه يدوياً."
                )
        
    return ConversationHandler.END