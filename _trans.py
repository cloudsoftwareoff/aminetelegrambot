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
# from datetime import datetime
# # Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# # Conversation states
# (IDENTIFY, PHONE, OFFER, REJECT_REASON, ADMIN_ADD_CODE, ADMIN_ADD_CREDITS, 
#  ADMIN_DELETE_CONFIRM, ADMIN_SELECT_USER_FOR_CREDIT, ADMIN_ALTER_CREDIT,
#  LOW_CREDIT_WARNING, PAYMENT_METHOD, PAYMENT_PROOF, ADMIN_VERIFY_PAYMENT) = range(13)
# # New states for altering user credits
# ADMIN_SELECT_USER_FOR_CREDIT, ADMIN_ALTER_CREDIT = range(7, 9)

# ADMIN_ID = 8128231719 #7168043490 #8128231719

# USDT_ADDRESS = "TYsdfghjklmnbvcxz1234567890"
# MIN_CREDIT_WARNING = 3  
# MIN_CREDIT_BLOCK = 0 
# # Database setup
# def init_db():
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
#     c.execute('''CREATE TABLE IF NOT EXISTS users 
#                  (code TEXT PRIMARY KEY, credits INTEGER, phone TEXT, telegram_id INTEGER)''')
#     c.execute('''CREATE TABLE IF NOT EXISTS orders 
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, phone TEXT, offer TEXT, status TEXT DEFAULT 'pending', reject_reason TEXT)''')
#     c.execute('''CREATE TABLE IF NOT EXISTS payments 
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, amount REAL, method TEXT, 
#                  proof TEXT, status TEXT DEFAULT 'pending', admin_note TEXT)''')
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
    
#     # Check user's credit
#     code = context.user_data['code']
#     credits = context.user_data['credits']
    
#     if credits <= MIN_CREDIT_BLOCK:
#         # Show payment options
#         keyboard = [
#             [InlineKeyboardButton("💳 شحن الرصيد", callback_data="topup_now")],
#             [InlineKeyboardButton("🔚 إلغاء", callback_data="cancel_topup")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             f"⚠️ رصيدك الحالي ({credits}) غير كافي للطلب.\n"
#             "الرجاء شحن الرصيد للمتابعة:",
#             reply_markup=reply_markup
#         )
#         return LOW_CREDIT_WARNING
    
#     elif credits <= MIN_CREDIT_WARNING:
#         # Show warning but still allow ordering
#         keyboard = [
#             [InlineKeyboardButton("25GO", callback_data="25GO")],
#             [InlineKeyboardButton("35GO", callback_data="35GO")],
#             [InlineKeyboardButton("💳 شحن الرصيد", callback_data="topup_now")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             f"⚠️ رصيدك منخفض ({credits}). يمكنك الطلب الآن أو شحن الرصيد:",
#             reply_markup=reply_markup
#         )
#         return OFFER
    
#     else:
#         # Normal order flow
#         keyboard = [
#             [InlineKeyboardButton("25GO", callback_data="25GO")],
#             [InlineKeyboardButton("35GO", callback_data="35GO")],
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             "اختار عرض:",
#             reply_markup=reply_markup
#         )
#         return OFFER

# async def handle_low_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     action = query.data
    
#     if action == "topup_now":
#         keyboard = [
#             [InlineKeyboardButton("💲 USDT", callback_data="pay_usdt")],
#             [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_order")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             "اختر طريقة الدفع:",
#             reply_markup=reply_markup
#         )
#         return PAYMENT_METHOD
    
#     elif action == "cancel_topup":
#         await query.edit_message_text("تم الإلغاء. يمكنك البدء من جديد بـ /start")
#         return ConversationHandler.END
    
#     return ConversationHandler.END
# async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     method = query.data
    
#     if method == "pay_usdt":
#         context.user_data['payment_method'] = "USDT"
        
#         keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_payment_method")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#         f"💳 طريقة الدفع: USDT\n\n"
#         f"1. أرسل {MIN_CREDIT_WARNING * 2} USDT إلى العنوان التالي:\n"
#         f"<code>{USDT_ADDRESS}</code>\n\n"
#         f"2. بعد التحويل، أرسل لنا معرف المعاملة (Transaction ID)\n\n"
#         f"⏳ سيتم تفعيل رصيدك خلال 24 ساعة بعد التحقق من الدفع.",
#         reply_markup=reply_markup,
#         parse_mode="HTML"
#         )
#         return PAYMENT_PROOF
    
#     elif method == "back_to_payment_method":
#         await handle_low_credit(update, context)
#         return LOW_CREDIT_WARNING
    
#     elif method == "back_to_order":
#         code = context.user_data['code']
#         telegram_id = context.user_data['telegram_id']
        
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("SELECT credits FROM users WHERE code = ?", (code,))
#         result = c.fetchone()
#         conn.close()
        
#         if result:
#             context.user_data['credits'] = result[0]
#             credits = result[0]
            
#             if credits <= MIN_CREDIT_BLOCK:
#                 return await handle_low_credit(update, context)
            
#             keyboard = [
#                 [InlineKeyboardButton("25GO", callback_data="25GO")],
#                 [InlineKeyboardButton("35GO", callback_data="35GO")],
#             ]
#             if credits <= MIN_CREDIT_WARNING:
#                 keyboard.append([InlineKeyboardButton("💳 شحن الرصيد", callback_data="topup_now")])
            
#             reply_markup = InlineKeyboardMarkup(keyboard)
            
#             await query.edit_message_text(
#                 f"رصيدك الحالي: {credits}\nاختار عرض:",
#                 reply_markup=reply_markup
#             )
#             return OFFER
    
#     return ConversationHandler.END

# async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message:
#         transaction_id = update.message.text
        
#         # Basic validation
#         if len(transaction_id) < 10 or not re.match(r'^[a-zA-Z0-9]+$', transaction_id):
#             await update.message.reply_text(
#                 "⚠️ معرف المعاملة غير صالح. يرجى إرسال معرف المعاملة الصحيح (يحتوي على أحرف وأرقام فقط)."
#             )
#             return PAYMENT_PROOF  # Stay in same state to try again
            
#         # Process valid transaction ID
#         code = context.user_data['code']
#         telegram_id = context.user_data['telegram_id']
#         method = context.user_data['payment_method']
        
#         # Save to database
#         conn = sqlite3.connect('users.db')
#         c = conn.cursor()
#         c.execute("""INSERT INTO payments 
#                     (code, amount, method, proof, status) 
#                     VALUES (?, ?, ?, ?, 'pending')""",
#                   (code, MIN_CREDIT_WARNING * 2, method, transaction_id))
#         payment_id = c.lastrowid
#         conn.commit()
#         conn.close()
        
#         # User confirmation with option to check status
#         keyboard = [[InlineKeyboardButton("🔄 تحقق من الحالة", callback_data=f"check_status_{payment_id}")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             "✅ تم استلام معلومات الدفع بنجاح!\n"
#             f"رقم المرجع: PAY-{payment_id}\n"
#             "سيتم مراجعة طلبك من قبل الإدارة وتفعيل رصيدك خلال 24 ساعة.\n\n"
#             "سيتم إعلامك عند التأكيد.",
#             reply_markup=reply_markup,
#             parse_mode="HTML"
#         )
        
#         # Admin notification
#         keyboard = [
#             [
#                 InlineKeyboardButton("✅ تأكيد", callback_data=f"verify_pay_{payment_id}"),
#                 InlineKeyboardButton("❌ رفض", callback_data=f"reject_pay_{payment_id}")
#             ],
#             [InlineKeyboardButton("📩 مراسلة العميل", callback_data=f"message_user_{telegram_id}")]
#         ]
        
#         await context.bot.send_message(
#             chat_id=ADMIN_ID,
#             text=f"🔔 طلب شحن رصيد جديد #{payment_id}\n"
#                  f"الكود: <code>{code}</code>\n"
#                  f"المبلغ: {MIN_CREDIT_WARNING * 2} {method}\n"
#                  f"المعرف: <code>{transaction_id}</code>\n"
#                  f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#             parse_mode="HTML"
#         )
    
#     return ConversationHandler.END  # End the conversation after submission
# async def admin_verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     # Parse callback data more carefully
#     callback_data = query.data
    
#     if callback_data.startswith("verify_pay_"):
#         payment_id = int(callback_data.replace("verify_pay_", ""))
#         action = "verify"
#     elif callback_data.startswith("reject_pay_"):
#         payment_id = int(callback_data.replace("reject_pay_", ""))
#         action = "reject"
#     elif callback_data.startswith("message_user_"):
#         telegram_id = int(callback_data.replace("message_user_", ""))
#         context.user_data['message_user_id'] = telegram_id
#         await query.edit_message_text("أدخل الرسالة التي تريد إرسالها للمستخدم:")
#         return ADMIN_VERIFY_PAYMENT
#     else:
#         await query.edit_message_text("Invalid callback data")
#         return ConversationHandler.END
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
    
#     if action == "verify":
#         # Get payment details including current status
#         c.execute("SELECT code, amount, status FROM payments WHERE id = ?", (payment_id,))
#         payment = c.fetchone()
        
#         if not payment:
#             await query.edit_message_text("Payment not found.")
#             conn.close()
#             return ConversationHandler.END
            
#         code, amount, status = payment
        
#         if status != 'pending':
#             await query.edit_message_text(f"Payment already {status}.")
#             conn.close()
#             return ConversationHandler.END
            
#         credits_to_add = int(amount / 2)  # Assuming 2 credits per 1 USDT
        
#         # Update user credits and payment status in a transaction
#         try:
#             # Get user details before updating
#             c.execute("SELECT telegram_id, credits FROM users WHERE code = ?", (code,))
#             user = c.fetchone()
            
#             if not user:
#                 await query.edit_message_text("User not found.")
#                 conn.close()
#                 return ConversationHandler.END
                
#             telegram_id, current_credits = user
#             new_credits = current_credits + credits_to_add
            
#             # Perform updates
#             c.execute("UPDATE users SET credits = ? WHERE code = ?", (new_credits, code))
#             c.execute("UPDATE payments SET status = 'verified' WHERE id = ?", (payment_id,))
#             conn.commit()
            
#             # Notify user with a button to start new order
#             keyboard = [
#                 [InlineKeyboardButton("🔄 بدء طلب جديد", callback_data=f"retry_{code}_{new_credits}")],
#                 [InlineKeyboardButton("💳 شحن الرصيد", callback_data="topup_now")]
#             ]
#             reply_markup = InlineKeyboardMarkup(keyboard)
            
#             try:
#                 await context.bot.send_message(
#                     chat_id=telegram_id,
#                     text=f"✅ تم تأكيد دفعتك!\nتم إضافة {credits_to_add} رصيد إلى حسابك\nالرصيد الجديد: {new_credits}\n\nيمكنك الآن بدء طلب جديد.",
#                     reply_markup=reply_markup
#                 )
#             except Exception as e:
#                 logger.error(f"Failed to notify user {telegram_id}: {e}")
#                 # Store notification failure to retry later
            
#             # Admin confirmation with option to continue managing
#             keyboard_admin = [
#                 [InlineKeyboardButton("📋 عرض الطلبات", callback_data="admin_view_orders")],
#                 [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="admin_view_users")],
#                 [InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]
#             ]
#             reply_markup_admin = InlineKeyboardMarkup(keyboard_admin)
            
#             await query.edit_message_text(
#                 f"✅ تم تأكيد الدفع #{payment_id}\nتم إضافة {credits_to_add} رصيد للمستخدم {code}",
#                 reply_markup=reply_markup_admin
#             )
            
#         except Exception as e:
#             conn.rollback()
#             logger.error(f"Error verifying payment: {e}")
#             await query.edit_message_text(f"حدث خطأ أثناء معالجة الدفع: {str(e)}")
    
#     elif action == "reject":
#         # Store payment info in context for next step
#         context.user_data['reject_payment_id'] = payment_id
#         context.user_data['reject_payment_code'] = code
        
#         keyboard = [
#             [InlineKeyboardButton("إلغاء", callback_data="cancel_payment_reject")],
#             [InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             f"الرجاء إدخال سبب رفض الدفع #{payment_id}:",
#             reply_markup=reply_markup
#         )
    
#     conn.close()
#     return ADMIN_VERIFY_PAYMENT if action == "reject" else ConversationHandler.END

# async def admin_reject_payment_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     reject_reason = update.message.text
#     payment_id = context.user_data.get('reject_payment_id')
#     code = context.user_data.get('reject_payment_code')
    
#     if not payment_id or not code:
#         await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#         return ConversationHandler.END
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
    
#     try:
#         # Update payment status and add rejection reason
#         c.execute("UPDATE payments SET status = 'rejected', admin_note = ? WHERE id = ?", 
#                  (reject_reason, payment_id))
#         conn.commit()
        
#         # Get user telegram_id to notify them
#         c.execute("SELECT telegram_id FROM users WHERE code = ?", (code,))
#         user = c.fetchone()
        
#         if user:
#             telegram_id = user[0]
#             keyboard = [
#                 [InlineKeyboardButton("🔄 حاول مرة أخرى", callback_data="topup_now")],
#                 [InlineKeyboardButton("🔚 إلغاء", callback_data="cancel")]
#             ]
#             reply_markup = InlineKeyboardMarkup(keyboard)
            
#             await context.bot.send_message(
#                 chat_id=telegram_id,
#                 text=f"❌ تم رفض دفعتك #{payment_id}\nالسبب: {reject_reason}\n"
#                      f"الرجاء التحقق من معلومات الدفع وإعادة المحاولة.",
#                 reply_markup=reply_markup
#             )
        
#         # Admin confirmation with options to continue
#         keyboard_admin = [
#             [InlineKeyboardButton("📋 عرض الطلبات", callback_data="admin_view_orders")],
#             [InlineKeyboardButton("💰 معاملات الدفع", callback_data="admin_view_payments")],
#             [InlineKeyboardButton("🏠 العودة للوحة التحكم", callback_data="admin_dashboard")]
#         ]
#         reply_markup_admin = InlineKeyboardMarkup(keyboard_admin)
        
#         await update.message.reply_text(
#             f"✅ تم رفض الدفع #{payment_id} بنجاح.",
#             reply_markup=reply_markup_admin
#         )
        
#     except Exception as e:
#         logger.error(f"Error rejecting payment: {e}")
#         await update.message.reply_text("حدث خطأ أثناء رفض الدفع")
#     finally:
#         conn.close()
    
#     return ConversationHandler.END

# async def admin_reject_payment_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if update.message.from_user.id != ADMIN_ID:
#         return ConversationHandler.END
    
#     reject_reason = update.message.text
#     payment_id = context.user_data.get('reject_payment_id')
#     code = context.user_data.get('reject_payment_code')
    
#     if not payment_id or not code:
#         await update.message.reply_text("حدث خطأ. الرجاء المحاولة مرة أخرى.")
#         return ConversationHandler.END
    
#     conn = sqlite3.connect('users.db')
#     c = conn.cursor()
    
#     try:
#         # Update payment status and add rejection reason
#         c.execute("UPDATE payments SET status = 'rejected', admin_note = ? WHERE id = ?", 
#                  (reject_reason, payment_id))
#         conn.commit()
        
#         # Get user telegram_id to notify them
#         c.execute("SELECT telegram_id FROM users WHERE code = ?", (code,))
#         user = c.fetchone()
        
#         if user:
#             telegram_id = user[0]
#             await context.bot.send_message(
#                 chat_id=telegram_id,
#                 text=f"❌ تم رفض دفعتك #{payment_id}\nالسبب: {reject_reason}\n"
#                      f"الرجاء التحقق من معلومات الدفع وإعادة المحاولة."
#             )
        
#         keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await update.message.reply_text(
#             f"✅ تم رفض الدفع #{payment_id} بنجاح.",
#             reply_markup=reply_markup
#         )
        
#     except Exception as e:
#         logger.error(f"Error rejecting payment: {e}")
#         await update.message.reply_text("حدث خطأ أثناء رفض الدفع")
#     finally:
#         conn.close()
    
#     return ConversationHandler.END

# async def cancel_payment_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     # Clear stored payment data
#     context.user_data.pop('reject_payment_id', None)
#     context.user_data.pop('reject_payment_code', None)
    
#     await show_admin_dashboard(update, context)
#     return ConversationHandler.END

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
#     return ConversationHandler.END

# async def admin_handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
    
#     # Split the callback data and handle cases with multiple underscores
#     parts = query.data.split('_')
#     if len(parts) < 2:
#         await query.edit_message_text("Invalid request format.")
#         return ConversationHandler.END
    
#     action = parts[0]  # First part is the action (accept/reject)
#     order_id = parts[-1]  # Last part is the order ID
    
#     try:
#         order_id = int(order_id)
#     except ValueError:
#         await query.edit_message_text("Invalid order ID format.")
#         return ConversationHandler.END
    
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
#         conn.close()
#         return ConversationHandler.END
    
#     code, phone, offer = result
    
#     if action == "accept":
#         c.execute("SELECT credits, telegram_id FROM users WHERE code = ?", (code,))
#         user_data = c.fetchone()
#         if user_data:
#             credits, telegram_id = user_data
            
#             if credits > 0:
#                 c.execute("UPDATE users SET credits = credits - 1 WHERE code = ?", (code,))
#                 c.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order_id,))
#                 conn.commit()
                
#                 keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#                 reply_markup = InlineKeyboardMarkup(keyboard)
                
#                 await query.edit_message_text(
#                     f"✅ تم تأكيد الطلب {order_id}.\nالكود: {code}\nالتلفون: {phone}\nالعرض: {offer}\nالرصيد المتبقي: {credits - 1}",
#                     reply_markup=reply_markup
#                 )
                
#                 await context.bot.send_message(
#                     chat_id=telegram_id,
#                     text=f"تم تأكيد طلبك!\nالتلفون: {phone}\nالعرض: {offer}\nالرصيد المتبقي: {credits - 1}"
#                 )
#             else:
#                 keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_dashboard")]]
#                 reply_markup = InlineKeyboardMarkup(keyboard)
#                 await query.edit_message_text(
#                     f"المستخدم {code} ما عندوش رصيد كافي.",
#                     reply_markup=reply_markup
#                 )
    
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
#         conn.close()
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
#     payment_conv_handler = ConversationHandler(
#         entry_points=[
#         CallbackQueryHandler(handle_low_credit, pattern='^topup_now$'),
#         CallbackQueryHandler(select_payment_method, pattern='^(pay_usdt|back_to_payment_method|back_to_order)$'),
#         CallbackQueryHandler(lambda u, c: receive_payment_proof(u, c), pattern='^check_status_')  # Add status check handler
#         ],
#         states={
#         PAYMENT_METHOD: [CallbackQueryHandler(select_payment_method)],
#         PAYMENT_PROOF: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_proof)],
#         LOW_CREDIT_WARNING: [CallbackQueryHandler(handle_low_credit)],
#         },
#         fallbacks=[
#         CommandHandler('cancel', cancel),
#         CallbackQueryHandler(cancel, pattern='^cancel_payment$')  # Add explicit cancel option
#         ],
#         )
    
#     # Admin payment verification handler
#     # Update the entry_points pattern in your admin_payment_verification handler
#     admin_payment_verification = ConversationHandler(
#     entry_points=[
#         CallbackQueryHandler(admin_verify_payment, pattern='^(verify_pay_|reject_pay_|message_user_)'),
#     ],
#     states={
#         ADMIN_VERIFY_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reject_payment_reason)],
#     },
#     fallbacks=[
#         CallbackQueryHandler(cancel_payment_reject, pattern='^cancel_payment_reject$'),
#         CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_dashboard$')
#     ],
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
#     application.add_handler(payment_conv_handler)
#     application.add_handler(admin_payment_verification)
#     application.run_polling()

# if __name__ == '__main__':
#     main()