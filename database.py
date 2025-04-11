import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (code TEXT PRIMARY KEY, credits INTEGER, phone TEXT, telegram_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, phone TEXT, offer TEXT, status TEXT DEFAULT 'pending', reject_reason TEXT)''')
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

def create_order(code, phone, offer):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO orders (code, phone, offer) VALUES (?, ?, ?)", (code, phone, offer))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_pending_orders():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, code, phone, offer, status FROM orders WHERE status = 'pending'")
    result = c.fetchall()
    conn.close()
    return result

def get_order_details(order_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT code, phone, offer, status FROM orders WHERE id = ?", (order_id,))
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
    c.execute("SELECT code, credits, phone FROM users")
    result = c.fetchall()
    conn.close()
    return result

def add_or_update_user(code, credits, telegram_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    if telegram_id:
        c.execute("INSERT OR REPLACE INTO users (code, credits, telegram_id) VALUES (?, ?, ?)", 
                 (code, credits, telegram_id))
    else:
        c.execute("INSERT OR REPLACE INTO users (code, credits) VALUES (?, ?)", 
                 (code, credits))
    conn.commit()
    conn.close()

def delete_user(code):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE code = ?", (code,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def update_user_credits(code, credits):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET credits = ? WHERE code = ?", (credits, code))
    conn.commit()
    conn.close()