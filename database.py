import sqlite3
import logging
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Updated users table with separate credit types
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (code TEXT PRIMARY KEY, 
                  credits_25go INTEGER DEFAULT 0,
                  credits_35go INTEGER DEFAULT 0,
                  credits_60go INTEGER DEFAULT 0,
                  phone TEXT, 
                  telegram_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  code TEXT, 
                  phone TEXT, 
                  telegram_id INTEGER,
                  offer TEXT, 
                  status TEXT DEFAULT 'pending', 
                  reject_reason TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect('users.db')

def get_user_by_code(code):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE code = ?", (code,))
    result = c.fetchone()
    conn.close()
    return result

def update_user_phone(code, phone):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET phone = ? WHERE code = ?", (phone, code))
    conn.commit()
    conn.close()

def create_order(code, phone, offer, telegram_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO orders (code, phone, telegram_id, offer) VALUES (?, ?, ?, ?)", 
             (code, phone, telegram_id, offer))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_pending_orders():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, code, phone, telegram_id, offer, status FROM orders WHERE status = 'pending'")
    result = c.fetchall()
    conn.close()
    return result

def get_order_details(order_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT code, phone, telegram_id, offer, status FROM orders WHERE id = ?", (order_id,))
    result = c.fetchone()
    conn.close()
    return result

def update_order_status(order_id, status, reject_reason=None):
    conn = get_db_connection()
    c = conn.cursor()
    if reject_reason:
        c.execute("UPDATE orders SET status = ?, reject_reason = ? WHERE id = ?", 
                 (status, reject_reason, order_id))
    else:
        c.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT code, credits_25go, credits_35go, credits_60go, phone FROM users")
    result = c.fetchall()
    conn.close()
    return result

def add_or_update_user(code, credits_25go=0, credits_35go=0, credits_60go=0, telegram_id=None):
    print(f"Updating user {code} with credits: 25GO={credits_25go}, 35GO={credits_35go}, 60GO={credits_60go}, telegram_id={telegram_id}")
    conn = get_db_connection()
    c = conn.cursor()
    if telegram_id:
        c.execute('''INSERT OR REPLACE INTO users 
                    (code, credits_25go, credits_35go, credits_60go, telegram_id) 
                    VALUES (?, ?, ?, ?, ?)''', 
                 (code, credits_25go, credits_35go, credits_60go, telegram_id))
    else:
        c.execute('''INSERT OR REPLACE INTO users 
                    (code, credits_25go, credits_35go, credits_60go) 
                    VALUES (?, ?, ?, ?)''', 
                 (code, credits_25go, credits_35go, credits_60go))
    conn.commit()
    conn.close()
    print(f"Updated user {code} successfully")

def delete_user(code):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE code = ?", (code,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def update_user_credits(code, credit_type, credits):
    """Update specific credit type for a user
    Args:
        code: User code
        credit_type: 'credits_25go', 'credits_35go', or 'credits_60go'
        credits: New credit value
    """
    if credit_type not in ['credits_25go', 'credits_35go', 'credits_60go']:
        raise ValueError("Invalid credit type")
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {credit_type} = ? WHERE code = ?", (credits, code))
    conn.commit()
    conn.close()

def get_user_credits(code):
    """Get all credit balances for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT credits_25go, credits_35go, credits_60go 
                 FROM users WHERE code = ?''', (code,))
    result = c.fetchone()
    conn.close()
    if result:
        return {
            'credits_25go': result[0],
            'credits_35go': result[1],
            'credits_60go': result[2]
        }
    return None

def deduct_credit(code, offer_type):
    """Deduct credit based on offer type
    Args:
        code: User code
        offer_type: '25GO', '35GO', or '60GO'
    Returns:
        bool: True if deduction was successful, False if not enough credits
    """
    credit_type = f'credits_{offer_type.lower()}'
    if credit_type not in ['credits_25go', 'credits_35go', 'credits_60go']:
        raise ValueError("Invalid offer type")
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check current credits
    c.execute(f"SELECT {credit_type} FROM users WHERE code = ?", (code,))
    current_credits = c.fetchone()[0]
    
    if current_credits <= 0:
        conn.close()
        return False
    
    # Deduct credit
    c.execute(f"UPDATE users SET {credit_type} = {credit_type} - 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return True