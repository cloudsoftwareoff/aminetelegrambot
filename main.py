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
    admin_enter_credits, select_user_for_credit, admin_select_credit_type,
    admin_alter_credit, view_order_details, confirm_delete_user, admin_handle_order,
    admin_reject_reason_text, cancel_reject, handle_refill_confirmation,
    admin_refill_reject_reason_text
)
from handlers.user import (
    start, refill_credits_command, identify, phone, offer, retry,
    continue_without_refill, refill_credits, handle_tx_id, cancel_refill,
    handle_refill_offer_choice, confirm_txid, retry_txid, confirm_phone, retry_phone,
    retry_code
)
from database import init_db
from constants import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    admin_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_add_user$')],
        states={
            ADMIN_ADD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_code)],
            ADMIN_ADD_CREDITS: [
                CallbackQueryHandler(admin_add_credits, pattern='^(add_25go|add_35go|add_60go)$')
            ],
            ADMIN_ENTER_CREDITS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_enter_credits)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    admin_alter_credit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_user_for_credit, pattern='^alter_credit_')],
        states={
            ADMIN_SELECT_CREDIT_TYPE: [
                CallbackQueryHandler(admin_select_credit_type, pattern='^(edit_25go|edit_35go|edit_60go)$')
            ],
            ADMIN_ALTER_CREDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_alter_credit)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    admin_order_reject_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_handle_order, pattern='^reject_\d+$'),
        ],
        states={
            REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reject_reason_text),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel_reject, pattern='^cancel_reject$')
        ],
        name="admin_order_reject_handler"
    )
    
    admin_refill_reject_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_refill_confirmation, pattern='^reject_refill_')
        ],
        states={
            REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_refill_reject_reason_text),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel_reject, pattern='^cancel_reject$')
        ],
        name="admin_refill_reject_handler"
    )
    
    user_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            # CommandHandler('reset', reset),
            # CallbackQueryHandler(proceed_to_phone, pattern='^proceed_to_phone$')  ,
            CallbackQueryHandler(retry, pattern='^retry_'),
            CallbackQueryHandler(continue_without_refill, pattern='^continue_without_refill$'),
            CallbackQueryHandler(retry_code, pattern='^retry_code$'),
            CallbackQueryHandler(proceed_to_phone, pattern='^proceed_to_phone$')
        ],
        states={
            IDENTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, identify)],
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone),
                CallbackQueryHandler(confirm_phone, pattern='^confirm_phone$'),
                CallbackQueryHandler(retry_phone, pattern='^retry_phone$'),
                CallbackQueryHandler(retry_code, pattern='^retry_code$')
            ],
            OFFER: [CallbackQueryHandler(offer, pattern='^(25GO|35GO|60GO)$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    refill_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(refill_credits, pattern='^refill_credits$'),
            CommandHandler('refill', refill_credits_command)
        ],
        states={
            REFILL_OFFER_CHOICE: [
                CallbackQueryHandler(handle_refill_offer_choice, pattern='^refill_(25go|35go|60go)$'),
                CallbackQueryHandler(cancel_refill, pattern='^cancel_refill$')
            ],
            REFILL_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tx_id),
                CallbackQueryHandler(confirm_txid, pattern='^confirm_txid_'),
                CallbackQueryHandler(retry_txid, pattern='^retry_txid$'),
                CallbackQueryHandler(handle_refill_offer_choice, pattern='^refill_(25go|35go|60go)$'),
                CallbackQueryHandler(refill_credits, pattern='^refill_credits$')
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel_refill, pattern='^cancel_refill$')
        ],
    )

    application.add_handler(admin_add_conv)
    application.add_handler(admin_alter_credit_conv)
    application.add_handler(admin_order_reject_handler)
    application.add_handler(admin_refill_reject_handler)
    application.add_handler(user_conv_handler)
    application.add_handler(refill_conv_handler)
    
    application.add_handler(CallbackQueryHandler(admin_handle_dashboard, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(view_order_details, pattern='^view_order_'))
    application.add_handler(CallbackQueryHandler(confirm_delete_user, pattern='^confirm_delete_'))
    application.add_handler(CallbackQueryHandler(admin_handle_order, pattern='^(accept|reject)_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_refill_confirmation, pattern='^(confirm|reject)_refill_'))
    
    logger.info("Starting bot polling")
    application.run_polling()

if __name__ == '__main__':
    main()