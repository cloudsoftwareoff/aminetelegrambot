import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from database import (
    get_all_users, get_pending_orders, get_order_details, update_order_status,
    add_or_update_user, delete_user, update_user_credits, get_user_by_code
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
        
        response = "المستخدمين:\n" + "\n".join([f"الكود: {u[0]}, الرصيد: {u[1]}, التلفون: {u[2] or 'غير متوفر'}" for u in users])
        
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
            user_buttons.append([InlineKeyboardButton(
                f"{user[0]} (الرصيد: {user[1]})",
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
    
    await update.message.reply_text(f"أدخل عدد النقاط للمستخدم {code}:")
    return ADMIN_ADD_CREDITS

async def admin_add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    try:
        credits = int(update.message.text)
        code = context.user_data.get('new_user_code')
        
        if not code:
            await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
            return ConversationHandler.END
        
        add_or_update_user(code, credits)
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ تم إضافة/تحديث المستخدم {code} برصيد {credits}.",
            reply_markup=reply_markup
        )
    except ValueError:
        await update.message.reply_text("يرجى إدخال رقم صحيح للنقاط.")
        return ADMIN_ADD_CREDITS
    
    return ConversationHandler.END

async def select_user_for_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    _, _, code = query.data.partition('_credit_')
    context.user_data['alter_credit_code'] = code
    
    user = get_user_by_code(code)
    if not user:
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "المستخدم غير موجود.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    current_credits = user[1]
    context.user_data['current_credits'] = current_credits
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"المستخدم: {code}\nالرصيد الحالي: {current_credits}\n\nأدخل الرصيد الجديد:",
        reply_markup=reply_markup
    )
    return ADMIN_ALTER_CREDIT

async def admin_alter_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    try:
        new_credits = int(update.message.text)
        code = context.user_data.get('alter_credit_code')
        current_credits = context.user_data.get('current_credits')
        
        if not code:
            await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
            return ConversationHandler.END
        
        update_user_credits(code, new_credits)
        
        change = new_credits - current_credits
        change_text = f"(+{change})" if change > 0 else f"({change})"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ تم تعديل رصيد المستخدم {code}.\nالرصيد السابق: {current_credits}\nالرصيد الجديد: {new_credits} {change_text}",
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
    
    code, phone, offer, status = order
    
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
    
    action, order_id = query.data.split('_')
    order_id = int(order_id)
    
    order = get_order_details(order_id)
    if not order or order[3] != 'pending':
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "الطلب مش موجود أو تم معالجته.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    code, phone, offer, _ = order
    
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
        
        credits, telegram_id = user[1], user[3]
        
        if credits > 0:
            update_user_credits(code, credits - 1)
            update_order_status(order_id, 'confirmed')
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ تم تأكيد الطلب {order_id}.\nالكود: {code}\nالتلفون: {phone}\nالعرض: {offer}\nالرصيد المتبقي: {credits - 1}",
                reply_markup=reply_markup
            )
            
            if telegram_id:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"تم تأكيد طلبك!\nالتلفون: {phone}\nالعرض: {offer}\nالرصيد المتبقي: {credits - 1}"
                )
        else:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"المستخدم {code} ما عندوش رصيد كافي.",
                reply_markup=reply_markup
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
    
    user = get_user_by_code(code)
    if not user:
        await update.message.reply_text("المستخدم غير موجود.")
        return ConversationHandler.END
    
    telegram_id, credits = user[3], user[1]
    
    update_order_status(order_id, 'rejected', reject_reason)
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ تم رفض الطلب {order_id}. السبب: {reject_reason}",
        reply_markup=reply_markup
    )
    
    if telegram_id:
        keyboard = [[InlineKeyboardButton("حاول مرة أخرى", callback_data=f"retry_{code}_{credits}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"تم رفض طلبك.\nالتلفون: {phone}\nالعرض: {offer}\nالسبب: {reject_reason}",
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END


async def handle_refill_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for admin confirming or rejecting refill requests"""
    query = update.callback_query
    await query.answer()
     
    # Parse the callback data - format is: "action_refill_code_txid"
    data_parts = query.data.split('_', 3)
    if len(data_parts) < 4:
        await query.edit_message_text("خطأ في بيانات الطلب")
        return ConversationHandler.END
    
    action = data_parts[0]  # confirm or reject
    code = data_parts[2]
    tx_id = data_parts[3].replace('-', '_') 
    
    logger.info(f"Admin {action}ed refill for user {code} with TXID {tx_id}")
    
    user = get_user_by_code(code)
    if not user:
        await query.edit_message_text(f"المستخدم {code} غير موجود.")
        return ConversationHandler.END
    
    current_credits = user[1]
    telegram_id = user[3]
    
    if action == "confirm":
        # Amount to add (can be modified to variable amounts)
        added_credits = 5
        new_credits = current_credits + added_credits
        
        # Update user credits
        update_user_credits(code, new_credits)
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ تم تأكيد شحن رصيد للمستخدم {code}.\nرقم المعاملة: {tx_id}\nالرصيد السابق: {current_credits}\nالرصيد الجديد: {new_credits} (+{added_credits})",
            reply_markup=reply_markup
        )
        
        # Notify user
        if telegram_id:
            retry_keyboard = [[InlineKeyboardButton("بدء طلب جديد", callback_data=f"retry_{code}_{new_credits}")]]
            retry_markup = InlineKeyboardMarkup(retry_keyboard)
            
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"✅ تم شحن رصيدك بنجاح!\nالرصيد السابق: {current_credits}\nالرصيد الجديد: {new_credits}\nيمكنك الآن متابعة طلبك.",
                    reply_markup=retry_markup
                )
            except Exception as e:
                logger.error(f"Failed to send confirmation to user {code}: {e}")
    
    elif action == "reject":
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ تم رفض طلب شحن الرصيد للمستخدم {code}.\nرقم المعاملة: {tx_id}",
            reply_markup=reply_markup
        )
        
        # Notify user about rejection
        if telegram_id:
            retry_keyboard = [[InlineKeyboardButton("محاولة شحن أخرى", callback_data="refill_credits")]]
            retry_markup = InlineKeyboardMarkup(retry_keyboard)
            
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"❌ تم رفض طلب شحن الرصيد الخاص بك.\nرقم المعاملة: {tx_id}\nالرجاء التأكد من صحة المعاملة أو التواصل مع الإدارة.",
                    reply_markup=retry_markup
                )
            except Exception as e:
                logger.error(f"Failed to send rejection to user {code}: {e}")
    
    return ConversationHandler.END
