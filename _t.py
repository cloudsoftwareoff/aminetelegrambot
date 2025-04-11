# import logging
# import sqlite3
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
# from telegram.ext import (
#     Application,
#     CommandHandler,
#     MessageHandler,
#     filters,
#     ConversationHandler,
#     ContextTypes,
#     CallbackQueryHandler,
# )
# import re
# # Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# # Conversation states
# IDENTIFY, PHONE, OFFER, REJECT_REASON, ADMIN_ADD_CODE, ADMIN_ADD_CREDITS, ADMIN_DELETE_CONFIRM = range(7)
# # New states for altering user credits
# ADMIN_SELECT_USER_FOR_CREDIT, ADMIN_ALTER_CREDIT = range(7, 9)
# USDT_TRANSACTION = 9
# ADMIN_ID = 7168043490 #8128231719

# # Database setup
# def init_db():
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute('''CREATE TABLE IF NOT EXISTS users 
#                  (code TEXT PRIMARY KEY, credits INTEGER, phone TEXT, telegram_id INTEGER)''')
#     c.execute('''CREATE TABLE IF NOT EXISTS orders 
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, phone TEXT, offer TEXT, status TEXT DEFAULT 'pending', reject_reason TEXT)''')
#     conn.commit()
#     conn.close()

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_id = update.message.from_user.id
#     user_name = update.message.from_user.first_name
    
#     # Check if user is admin
#     if user_id == ADMIN_ID:
#         await show_admin_dashboard(update, context)
#         return ConversationHandler.END
    
#     # Regular user flow
#     context.user_data['telegram_id'] = user_id
    
#     keyboard = [[KeyboardButton("/start")]]
#     reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
#     await update.message.reply_text(
#         f"سلام {user_name}!! أكتب الكود متاعك باش تبدأ الطلب.",
#         reply_markup=reply_markup
#     )
#     return IDENTIFY
# async def check_credits_and_notify(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, code: str, credits: int):
#     if credits <= 3:  # Notify when credits are 3 or less
#         keyboard = [
#             [InlineKeyboardButton("إعادة تعبئة الرصيد (10 USDT لكل نقطة)", callback_data=f"refill_{code}")],
#             [InlineKeyboardButton("إلغاء", callback_data=f"cancel_refill_{code}")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await context.bot.send_message(
#             chat_id=telegram_id,
#             text=f"⚠️ رصيدك منخفض! لديك فقط {credits} نقطة(s) متبقية.\nهل ترغب في إعادة تعبئة الرصيد؟ (10 USDT لكل نقطة)",
#             reply_markup=reply_markup
#         )
# async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     keyboard = [
#         [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="admin_view_users")],
#         [InlineKeyboardButton("📋 عرض الطلبات", callback_data="admin_view_orders")],
#         [InlineKeyboardButton("➕ إضافة مستخدم", callback_data="admin_add_user")],
#         [InlineKeyboardButton("🔄 تعديل رصيد مستخدم", callback_data="admin_alter_credit")],
#         [InlineKeyboardButton("❌ حذف مستخدم", callback_data="admin_delete_user")]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     if hasattr(update, 'message') and update.message:
#         await update.message.reply_text(
#             "لوحة تحكم الإدارة\nاختر إحدى الخيارات:",
#             reply_markup=reply_markup
#         )
#     else:
#         await update.callback_query.edit_message_text(
#             "لوحة تحكم الإدارة\nاختر إحدى الخيارات:",
#             reply_markup=reply_markup
#         )

# async def admin_handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     action = query.data
    
#     if action == "admin_dashboard":
#         await show_admin_dashboard(update, context)
#         return ConversationHandler.END
    
#     elif action == "admin_view_users":
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("SELECT code, credits, phone FROM users")
#         users = c.fetchall()
#         conn.close()
        
#         if not users:
#             keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#             await query.edit_message_text(
#                 "ما فماش مستخدمين في القاعدة.",
#                 reply_markup=reply_markup
#             )
#             return ConversationHandler.END
        
#         response = "المستخدمين:\n" + "\n".join([f"الكود: {u[0]}, الرصيد: {u[1]}, التلفون: {u[2] or 'غير متوفر'}" for u in users])
        
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         # If response is too long, truncate it and notify
#         if len(response) > 4000:
#             response = response[:3950] + "\n...(تم اختصار القائمة لكبر حجمها)"
        
#         await query.edit_message_text(response, reply_markup=reply_markup)
#         return ConversationHandler.END
    
#     elif action == "admin_view_orders":
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("SELECT id, code, phone, offer, status FROM orders WHERE status = 'pending'")
#         orders = c.fetchall()
#         conn.close()
        
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         if not orders:
#             await query.edit_message_text(
#                 "ما فماش طلبات في الانتظار.",
#                 reply_markup=reply_markup
#             )
#             return ConversationHandler.END
        
#         order_buttons = []
#         for o in orders:
#             order_buttons.append([InlineKeyboardButton(
#                 f"طلب #{o[0]}: {o[1]} - {o[3]}",
#                 callback_data=f"view_order_{o[0]}"
#             )])
        
#         order_buttons.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")])
#         orders_markup = InlineKeyboardMarkup(order_buttons)
        
#         await query.edit_message_text(
#             "الطلبات المعلقة:",
#             reply_markup=orders_markup
#         )
#         return ConversationHandler.END
    
#     elif action == "admin_add_user":
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#         await query.edit_message_text(
#             "أدخل كود المستخدم الجديد:",
#             reply_markup=reply_markup
#         )
#         return ADMIN_ADD_CODE
    
#     elif action == "admin_alter_credit":
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("SELECT code, credits FROM users")
#         users = c.fetchall()
#         conn.close()
        
#         if not users:
#             keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#             await query.edit_message_text(
#                 "ما فماش مستخدمين لتعديل الرصيد.",
#                 reply_markup=reply_markup
#             )
#             return ConversationHandler.END
        
#         user_buttons = []
#         for user in users:
#             user_buttons.append([InlineKeyboardButton(
#                 f"{user[0]} (الرصيد: {user[1]})",
#                 callback_data=f"alter_credit_{user[0]}"
#             )])
        
#         user_buttons.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")])
#         users_markup = InlineKeyboardMarkup(user_buttons)
        
#         await query.edit_message_text(
#             "اختر المستخدم لتعديل الرصيد:",
#             reply_markup=users_markup
#         )
#         return ConversationHandler.END
    
#     elif action == "admin_delete_user":
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("SELECT code FROM users")
#         users = c.fetchall()
#         conn.close()
        
#         if not users:
#             keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#             await query.edit_message_text(
#                 "ما فماش مستخدمين للحذف.",
#                 reply_markup=reply_markup
#             )
#             return ConversationHandler.END
        
#         user_buttons = []
#         for user in users:
#             user_buttons.append([InlineKeyboardButton(
#                 f"حذف {user[0]}",
#                 callback_data=f"confirm_delete_{user[0]}"
#             )])
        
#         user_buttons.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")])
#         users_markup = InlineKeyboardMarkup(user_buttons)
        
#         await query.edit_message_text(
#             "اختر المستخدم للحذف:",
#             reply_markup=users_markup
#         )
#         return ConversationHandler.END
    
#     return ConversationHandler.END

# async def select_user_for_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     _, _, code = query.data.partition('_credit_')
#     context.user_data['alter_credit_code'] = code
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("SELECT credits FROM users WHERE code = ?", (code,))
#     result = c.fetchone()
#     conn.close()
    
#     if not result:
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#         await query.edit_message_text(
#             "المستخدم غير موجود.",
#             reply_markup=reply_markup
#         )
#         return ConversationHandler.END
    
#     current_credits = result[0]
#     context.user_data['current_credits'] = current_credits
    
#     keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await query.edit_message_text(
#         f"المستخدم: {code}\nالرصيد الحالي: {current_credits}\n\nأدخل الرصيد الجديد:",
#         reply_markup=reply_markup
#     )
#     return ADMIN_ALTER_CREDIT

# async def admin_alter_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     try:
#         new_credits = int(update.message.text)
#         code = context.user_data.get('alter_credit_code')
#         current_credits = context.user_data.get('current_credits')
        
#         if not code:
#             await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#             return ConversationHandler.END
        
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("UPDATE users SET credits = ? WHERE code = ?", (new_credits, code))
#         conn.commit()
#         conn.close()
        
#         change = new_credits - current_credits
#         change_text = f"(+{change})" if change > 0 else f"({change})"
        
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             f"✅ تم تعديل رصيد المستخدم {code}.\nالرصيد السابق: {current_credits}\nالرصيد الجديد: {new_credits} {change_text}",
#             reply_markup=reply_markup
#         )
#     except ValueError:
#         await update.message.reply_text("يرجى إدخال رقم صحيح للرصيد.")
#         return ADMIN_ALTER_CREDIT
    
#     return ConversationHandler.END

# async def view_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     _, _, order_id = query.data.partition('_order_')
#     order_id = int(order_id)
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("SELECT code, phone, offer, status FROM orders WHERE id = ?", (order_id,))
#     result = c.fetchone()
#     conn.close()
    
#     if not result:
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#         await query.edit_message_text(
#             "الطلب غير موجود.",
#             reply_markup=reply_markup
#         )
#         return ConversationHandler.END
    
#     code, phone, offer, status = result
    
#     keyboard = [
#         [
#             InlineKeyboardButton("✅ قبول", callback_data=f"accept_{order_id}"),
#             InlineKeyboardButton("❌ رفض", callback_data=f"reject_{order_id}")
#         ],
#         [InlineKeyboardButton("🔙 العودة للطلبات", callback_data="admin_view_orders")],
#         [InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await query.edit_message_text(
#         f"تفاصيل الطلب #{order_id}:\nالكود: {code}\nالتلفون: {phone}\nالعرض: {offer}\nالحالة: {status}",
#         reply_markup=reply_markup
#     )
#     return ConversationHandler.END

# async def confirm_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     _, _, code = query.data.partition('_delete_')
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("DELETE FROM users WHERE code = ?", (code,))
#     deleted = c.rowcount > 0
#     conn.commit()
#     conn.close()
    
#     if deleted:
#         message = f"✅ تم حذف المستخدم {code} بنجاح."
#     else:
#         message = f"❌ فشل في حذف المستخدم {code}. ربما تم حذفه مسبقاً."
    
#     keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await query.edit_message_text(message, reply_markup=reply_markup)
#     return ConversationHandler.END

# async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     code = update.message.text
#     context.user_data['new_user_code'] = code
    
#     await update.message.reply_text(f"أدخل عدد النقاط للمستخدم {code}:")
#     return ADMIN_ADD_CREDITS

# async def admin_add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     try:
#         credits = int(update.message.text)
#         code = context.user_data.get('new_user_code')
        
#         if not code:
#             await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#             return ConversationHandler.END
        
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("INSERT OR REPLACE INTO users (code, credits) VALUES (?, ?)", (code, credits))
#         conn.commit()
#         conn.close()
        
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             f"✅ تم إضافة/تحديث المستخدم {code} برصيد {credits}.",
#             reply_markup=reply_markup
#         )
#     except ValueError:
#         await update.message.reply_text("يرجى إدخال رقم صحيح للنقاط.")
#         return ADMIN_ADD_CREDITS
    
#     return ConversationHandler.END

# async def identify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.text == "/start":
#         await update.message.reply_text("أكتب الكود متاعك.")
#         return IDENTIFY
    
#     code = update.message.text
#     telegram_id = context.user_data['telegram_id']
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("SELECT credits FROM users WHERE code = ?", (code,))
#     result = c.fetchone()
    
#     if result is None:
#         await update.message.reply_text("الكود غير صحيح. راسل الإدارة.")
#         conn.close()
#         return ConversationHandler.END
    
#     c.execute("INSERT OR REPLACE INTO users (code, credits, telegram_id) VALUES (?, ?, ?)", 
#               (code, result[0], telegram_id))
#     conn.commit()
#     conn.close()
    
#     context.user_data['code'] = code
#     context.user_data['credits'] = result[0]
#     await update.message.reply_text(
#         f"تم التحقق من الكود! عندك {result[0]} رصيد.\nأكتب رقم التلفون متاعك (مثلا 99000111)."
#     )
#     return PHONE
# async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     phone_number = update.message.text
    
#     # Validate phone number (must be exactly 8 digits)
#     if not re.match(r'^\d{8}$', phone_number):
#         await update.message.reply_text(
#             "رقم الهاتف غير صحيح. يجب أن يكون 8 أرقام فقط.\nالرجاء إدخال رقم التلفون مرة أخرى (مثلا 99000111)."
#         )
#         return PHONE
    
#     context.user_data['phone_number'] = phone_number
    
#     keyboard = [
#         [InlineKeyboardButton("25GO", callback_data="25GO")],
#         [InlineKeyboardButton("35GO", callback_data="35GO")],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await update.message.reply_text(
#         "اختار عرض:",
#         reply_markup=reply_markup
#     )
#     return OFFER

# async def offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     selected_offer = query.data
#     phone_number = context.user_data['phone_number']
#     code = context.user_data['code']
#     credits = context.user_data['credits']

#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("INSERT INTO orders (code, phone, offer) VALUES (?, ?, ?)", 
#               (code, phone_number, selected_offer))
#     order_id = c.lastrowid
#     c.execute("UPDATE users SET phone = ? WHERE code = ?", (phone_number, code))
#     conn.commit()
#     conn.close()

#     # Send message to admin with accept/reject buttons
#     keyboard = [
#         [
#             InlineKeyboardButton("✅ قبول", callback_data=f"accept_{order_id}"),
#             InlineKeyboardButton("❌ رفض", callback_data=f"reject_{order_id}")
#         ]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)

#     await context.bot.send_message(
#         chat_id=ADMIN_ID,
#         text=f"طلب جديد!\nرقم الطلب: {order_id}\nالكود: {code}\nالتلفون: `{phone_number}`\nالعرض: {selected_offer}",
#         reply_markup=reply_markup,
#         parse_mode="Markdown"
#     )

#     await query.edit_message_text(
#         f"✅ تم تسجيل الطلب!\nالتلفون: {phone_number}\nالعرض: {selected_offer}\nالرصيد: {credits}\nفي انتظار تأكيد الإدارة."
#     )
    
#     # Check credits and notify if low
#     await check_credits_and_notify(context, query.from_user.id, code, credits - 1)
    
#     return ConversationHandler.END

# async def start_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     _, code = query.data.split('_', 1)
#     context.user_data['refill_code'] = code
    
#     # Get current credits
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("SELECT credits FROM users WHERE code = ?", (code,))
#     credits = c.fetchone()[0]
#     conn.close()
    
#     await query.edit_message_text(
#         f"لإعادة تعبئة الرصيد:\n"
#         f"1. أرسل USDT إلى العنوان التالي: [USDT_ADDRESS_HERE]\n"
#         f"2. أرسل لنا معرف المعاملة (Transaction ID)\n"
#         f"3. سنقوم بتحويل النقاط خلال 24 ساعة\n\n"
#         f"سعر النقطة: 10 USDT\n"
#         f"الحد الأدنى: 1 نقطة\n"
#         f"الرصيد الحالي: {credits} نقطة(s)"
#     )
#     return USDT_TRANSACTION

# async def handle_usdt_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     transaction_id = update.message.text
#     code = context.user_data.get('refill_code')
#     user_id = update.message.from_user.id
    
#     if not code:
#         await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#         return ConversationHandler.END
    
#     # Send transaction details to admin
#     keyboard = [
#         [
#             InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_refill_{code}_{user_id}_{transaction_id}"),
#             InlineKeyboardButton("❌ رفض", callback_data=f"reject_refill_{code}_{user_id}_{transaction_id}")
#         ]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await context.bot.send_message(
#         chat_id=ADMIN_ID,
#         text=f"طلب تعبئة رصيد جديد!\nالكود: {code}\nمعرف المعاملة: {transaction_id}\nمعرف المستخدم: {user_id}",
#         reply_markup=reply_markup
#     )
    
#     await update.message.reply_text(
#         "تم إرسال تفاصيل المعاملة للإدارة. سيتم مراجعتها وإعلامك بالنتيجة."
#     )
#     return ConversationHandler.END

# async def cancel_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     await query.edit_message_text("تم إلغاء عملية إعادة التعبئة.")
#     return ConversationHandler.END


# async def admin_handle_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     action, code, user_id, transaction_id = query.data.split('_', 3)
    
#     if action == "confirm":
#         # Ask admin for number of credits to add
#         context.user_data['refill_code'] = code
#         context.user_data['refill_user_id'] = user_id
#         context.user_data['refill_transaction_id'] = transaction_id
        
#         keyboard = [[InlineKeyboardButton("إلغاء", callback_data="cancel_refill_approval")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             f"كم عدد النقاط التي تريد إضافتها للمستخدم {code}?\nمعرف المعاملة: {transaction_id}",
#             reply_markup=reply_markup
#         )
#         return ADMIN_ALTER_CREDIT
    
#     elif action == "reject":
#         await context.bot.send_message(
#             chat_id=user_id,
#             text=f"تم رفض طلب إعادة تعبئة الرصيد الخاص بك.\nمعرف المعاملة: {transaction_id}\nالرجاء التواصل مع الإدارة لمزيد من المعلومات."
#         )
        
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             f"تم رفض طلب إعادة تعبئة الرصيد للمستخدم {code}.",
#             reply_markup=reply_markup
#         )
    
#     return ConversationHandler.END

# async def admin_confirm_refill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     try:
#         credits_to_add = int(update.message.text)
#         code = context.user_data.get('refill_code')
#         user_id = context.user_data.get('refill_user_id')
#         transaction_id = context.user_data.get('refill_transaction_id')
        
#         if not code:
#             await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#             return ConversationHandler.END
        
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("UPDATE users SET credits = credits + ? WHERE code = ?", (credits_to_add, code))
#         conn.commit()
#         conn.close()
        
#         # Notify user
#         await context.bot.send_message(
#             chat_id=user_id,
#             text=f"✅ تمت إضافة {credits_to_add} نقطة(s) إلى رصيدك!\nمعرف المعاملة: {transaction_id}\nيمكنك الآن تقديم طلبات جديدة."
#         )
        
#         await update.message.reply_text(
#             f"تمت إضافة {credits_to_add} نقطة(s) إلى رصيد المستخدم {code}."
#         )
#     except ValueError:
#         await update.message.reply_text("يرجى إدخال رقم صحيح للنقاط.")
#         return ADMIN_ALTER_CREDIT
    
#     return ConversationHandler.END


# async def admin_handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     action, order_id = query.data.split('_')
#     order_id = int(order_id)
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("SELECT code, phone, offer FROM orders WHERE id = ? AND status = 'pending'", (order_id,))
#     result = c.fetchone()
    
#     if not result:
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#         await query.edit_message_text(
#             "الطلب مش موجود أو تم معالجته.",
#             reply_markup=reply_markup
#         )
#         return ConversationHandler.END
    
#     code, phone, offer = result
    
#     if action == "accept":
#         c.execute("SELECT credits, telegram_id FROM users WHERE code = ?", (code,))
#         user_data = c.fetchone()
#         credits, telegram_id = user_data
        
#         if credits > 0:
#             c.execute("UPDATE users SET credits = credits - 1 WHERE code = ?", (code,))
#             c.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order_id,))
#             conn.commit()
            
#             keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#             reply_markup = InlineKeyboardMarkup(keyboard)
            
#             await query.edit_message_text(
#                 f"✅ تم تأكيد الطلب {order_id}.\nالكود: {code}\nالتلفون: {phone}\nالعرض: {offer}\nالرصيد المتبقي: {credits - 1}",
#                 reply_markup=reply_markup
#             )
            
#             await context.bot.send_message(
#                 chat_id=telegram_id,
#                 text=f"تم تأكيد طلبك!\nالتلفون: {phone}\nالعرض: {offer}\nالرصيد المتبقي: {credits - 1}"
#             )
#         else:
#             keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#             await query.edit_message_text(
#                 f"المستخدم {code} ما عندوش رصيد كافي.",
#                 reply_markup=reply_markup
#             )
    
#     elif action == "reject":
#         # Store order_id in context for the next step
#         context.user_data['reject_order_id'] = order_id
#         context.user_data['reject_code'] = code
#         context.user_data['reject_phone'] = phone
#         context.user_data['reject_offer'] = offer
        
#         keyboard = [[InlineKeyboardButton("إلغاء", callback_data="cancel_reject")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         # Ask admin for rejection reason
#         await query.edit_message_text(
#             f"الرجاء إدخال سبب رفض الطلب رقم {order_id}:",
#             reply_markup=reply_markup
#         )
#         return REJECT_REASON
    
#     conn.close()
#     return ConversationHandler.END

# async def cancel_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     await show_admin_dashboard(update, context)
#     return ConversationHandler.END

# async def admin_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # This function handles the admin's rejection reason
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     reject_reason = update.message.text
#     order_id = context.user_data.get('reject_order_id')
#     code = context.user_data.get('reject_code')
#     phone = context.user_data.get('reject_phone')
#     offer = context.user_data.get('reject_offer')
    
#     if not order_id:
#         await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#         return ConversationHandler.END
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute("SELECT telegram_id, credits FROM users WHERE code = ?", (code,))
#     result = c.fetchone()
    
#     if not result:
#         await update.message.reply_text("المستخدم غير موجود.")
#         conn.close()
#         return ConversationHandler.END
    
#     telegram_id, credits = result
    
#     c.execute("UPDATE orders SET status = 'rejected', reject_reason = ? WHERE id = ?", 
#               (reject_reason, order_id))
#     conn.commit()
#     conn.close()
    
#     keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await update.message.reply_text(
#         f"✅ تم رفض الطلب {order_id}. السبب: {reject_reason}",
#         reply_markup=reply_markup
#     )
    
#     # Send message to user with retry button
#     keyboard = [[InlineKeyboardButton("حاول مرة أخرى", callback_data=f"retry_{code}_{credits}")]]
#     reply_markup = InlineKeyboardMarkup(keyboard)
    
#     await context.bot.send_message(
#         chat_id=telegram_id,
#         text=f"تم رفض طلبك.\nالتلفون: {phone}\nالعرض: {offer}\nالسبب: {reject_reason}",
#         reply_markup=reply_markup
#     )
    
#     return ConversationHandler.END

# async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     await update.message.reply_text("تم الإلغاء.")
#     return ConversationHandler.END

# async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     # Extract code and credits from callback data
#     parts = query.data.split('_')
#     if len(parts) >= 3:
#         code = parts[1]
#         try:
#             credits = int(parts[2])
#         except ValueError:
#             credits = 0
#     else:
#         # Fallback if data is not in expected format
#         telegram_id = query.from_user.id
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("SELECT code, credits FROM users WHERE telegram_id = ?", (telegram_id,))
#         result = c.fetchone()
#         conn.close()
        
#         if result:
#             code, credits = result
#         else:
#             await query.edit_message_text("ما عندناش معلومات عليك. حاول تبدأ من جديد بـ /start.")
#             return ConversationHandler.END
    
#     # Store necessary data in context
#     context.user_data['code'] = code
#     context.user_data['credits'] = credits
#     context.user_data['telegram_id'] = query.from_user.id
    
#     await query.edit_message_text(
#         f"أكتب رقم التلفون متاعك (مثلا 99000111)."
#     )
#     return PHONE

# def main() -> None:
#     init_db()
#     #7560159485:AAFB6_gpanxx8m4CMLHpU0E4McBSjlH8z4c
#     #7739976856:AAHwabJ3g73GGccW4oy72cP8JRmAoodfLTs
#     application = Application.builder().token("7739976856:AAHwabJ3g73GGccW4oy72cP8JRmAoodfLTs").build()

#     # Admin conversation handler for adding users
#     admin_add_conv = ConversationHandler(
#         entry_points=[CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_add_user$')],
#         states={
#             ADMIN_ADD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_code)],
#             ADMIN_ADD_CREDITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_credits)],
#         },
#         fallbacks=[CommandHandler('cancel', cancel)],
#     )
#     refill_conv = ConversationHandler(
#         entry_points=[CallbackQueryHandler(start_refill, pattern='^refill_')],
#         states={
#             USDT_TRANSACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_usdt_transaction)],
#         },
#         fallbacks=[
#             CallbackQueryHandler(cancel_refill, pattern='^cancel_refill_'),
#             CommandHandler('cancel', cancel)
#         ],
#     )
    
#     # Add admin refill approval handler
#     admin_refill_handler = ConversationHandler(
#         entry_points=[CallbackQueryHandler(admin_handle_refill, pattern='^(confirm|reject)_refill_')],
#         states={
#             ADMIN_ALTER_CREDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_confirm_refill)],
#         },
#         fallbacks=[
#             CallbackQueryHandler(cancel_refill, pattern='^cancel_refill_approval'),
#             CommandHandler('cancel', cancel)
#         ],
#     )

#     # Add the new handlers to application
#     application.add_handler(refill_conv)
#     application.add_handler(admin_refill_handler)

#     # Admin conversation handler for altering user credits
#     admin_alter_credit_conv = ConversationHandler(
#         entry_points=[CallbackQueryHandler(select_user_for_credit, pattern='^alter_credit_')],
#         states={
#             ADMIN_ALTER_CREDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_alter_credit)],
#         },
#         fallbacks=[CommandHandler('cancel', cancel)],
#     )
    
#     # Admin conversation handler for rejection process
#     admin_reject_handler = ConversationHandler(
#         entry_points=[CallbackQueryHandler(admin_handle_order, pattern='^reject_')],
#         states={
#             REJECT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reject_reason)],
#         },
#         fallbacks=[
#             CommandHandler('cancel', cancel),
#             CallbackQueryHandler(cancel_reject, pattern='^cancel_reject$')
#         ],
#     )

#     # Main conversation handler for users
#     user_conv_handler = ConversationHandler(
#         entry_points=[
#             CommandHandler('start', start),
#             CallbackQueryHandler(retry, pattern='^retry_')
#         ],
#         states={
#             IDENTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, identify)],
#             PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
#             OFFER: [CallbackQueryHandler(offer, pattern='^(25GO|35GO)$')],
#         },
#         fallbacks=[CommandHandler('cancel', cancel)],
#     )

#     # Add handlers to application
#     application.add_handler(admin_add_conv)
#     application.add_handler(admin_alter_credit_conv)  # Add the new credit alteration handler
#     application.add_handler(admin_reject_handler)
#     application.add_handler(user_conv_handler)
    
#     # Admin dashboard handlers
#     application.add_handler(CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_'))
#     application.add_handler(CallbackQueryHandler(view_order_details, pattern='^view_order_'))
#     application.add_handler(CallbackQueryHandler(confirm_delete_user, pattern='^confirm_delete_'))
#     application.add_handler(CallbackQueryHandler(admin_handle_order, pattern='^accept_'))
    
#     application.run_polling()

# if __name__ == '__main__':
#     main()