import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from handlers.common import cancel
from handlers.admin import (
    show_admin_dashboard, admin_handle_dashboard, admin_add_code, admin_add_credits,
    select_user_for_credit, admin_alter_credit, view_order_details, confirm_delete_user,
    admin_handle_order, cancel_reject, admin_reject_reason,handle_refill_confirmation,
)
from handlers.user import start,refill_credits_command, identify, phone, offer, retry,continue_without_refill,refill_credits,handle_tx_id
from database import init_db
from constants import *

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Admin conversation handler for adding users
    admin_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_add_user$')],
        states={
            ADMIN_ADD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_code)],
            ADMIN_ADD_CREDITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_credits)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Admin conversation handler for altering user credits
    admin_alter_credit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_user_for_credit, pattern='^alter_credit_')],
        states={
            ADMIN_ALTER_CREDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_alter_credit)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Admin conversation handler for rejection process
    admin_reject_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_handle_order, pattern='^reject_')],
        states={
            REJECT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reject_reason)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel_reject, pattern='^cancel_reject$')
        ],
    )

    # Main conversation handler for users
    user_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(retry, pattern='^retry_')
        ],
        states={
            IDENTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, identify)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            OFFER: [CallbackQueryHandler(offer, pattern='^(25GO|35GO)$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add handlers to application
    application.add_handler(admin_add_conv)
    application.add_handler(admin_alter_credit_conv)
    application.add_handler(admin_reject_handler)
    application.add_handler(user_conv_handler)
    
    # Admin dashboard handlers
    application.add_handler(CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(view_order_details, pattern='^view_order_'))
    application.add_handler(CallbackQueryHandler(confirm_delete_user, pattern='^confirm_delete_'))
    application.add_handler(CallbackQueryHandler(admin_handle_order, pattern='^accept_'))
    # Update the user conversation handler to include the refill state
    user_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(retry, pattern='^retry_')
        ],
        states={
            IDENTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, identify)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            OFFER: [CallbackQueryHandler(offer, pattern='^(25GO|35GO)$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    refill_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("refill", refill_credits_command),
            CallbackQueryHandler(refill_credits_command, pattern='^refill_credits$')
        ],
        states={
            REFILL_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tx_id)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(refill_conv_handler)

    application.add_handler(user_conv_handler)
    
    application.add_handler(CallbackQueryHandler(refill_credits, pattern='^refill_credits$'))
    application.add_handler(CallbackQueryHandler(continue_without_refill, pattern='^continue_without_refill$'))
    application.add_handler(CallbackQueryHandler(handle_refill_confirmation, pattern='^(confirm|reject)_refill_'))
    
    application.run_polling()

if __name__ == '__main__':
    main()