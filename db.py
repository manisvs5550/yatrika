# db.py

import mysql.connector
import os

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def fetch_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def insert_user(username, password, role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                   (username, password, role))
    conn.commit()
    cursor.close()
    conn.close()

def fetch_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users ORDER BY role DESC, username DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def update_user_role(username, new_role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
    conn.commit()
    cursor.close()
    conn.close()

def delete_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    cursor.close()
    conn.close()

    # Party management - db.py

def get_all_parties():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM parties ORDER BY party_number")
    parties = cursor.fetchall()
    cursor.close()
    conn.close()
    return parties

def insert_party(party_number, leader_name, member_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO parties (party_number, leader_name, member_name) VALUES (%s, %s, %s)",
                   (party_number, leader_name, member_name))
    conn.commit()
    cursor.close()
    conn.close()

def update_party(party_number, leader_name, member_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE parties SET leader_name = %s, member_name = %s WHERE party_number = %s",
                   (leader_name, member_name, party_number))
    conn.commit()
    cursor.close()
    conn.close()

def delete_party(party_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM parties WHERE party_number = %s", (party_number,))
    conn.commit()
    cursor.close()
    conn.close()

def get_party_by_user(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM parties
        WHERE FIND_IN_SET(%s, leader_name) OR FIND_IN_SET(%s, member_name)
        """, (username, username))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def get_tour_entries_by_user(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM tour_diaries 
        WHERE submitted_by = %s 
        ORDER BY start_date DESC
    """, (username,))
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    return entries

def insert_tour_entry(entry):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tour_diaries 
        (party_number, start_date, office_name, work_done, latitude, longitude, status, submitted_by, remarks, entry_datetime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        entry['party_number'], entry['start_date'], entry['office_name'], entry['work_done'],
        entry['latitude'], entry['longitude'], entry['status'], entry['submitted_by'],
        entry['remarks'], entry['entry_datetime']
    ))
    conn.commit()
    cursor.close()
    conn.close()

def check_duplicate_tour_entry(username, start_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM tour_diaries 
        WHERE submitted_by = %s AND start_date = %s
    """, (username, start_date))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0

def get_pending_tour_entries_for_leader(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT party_number FROM parties 
        WHERE FIND_IN_SET(%s, leader_name)
    """, (username,))
    rows = cursor.fetchall()
    party_numbers = [row['party_number'] for row in rows]

    if not party_numbers:
        cursor.close()
        conn.close()
        return []

    placeholders = ','.join(['%s'] * len(party_numbers))
    query = f"""
        SELECT id, start_date, office_name, work_done, submitted_by, status, remarks 
        FROM tour_diaries
        WHERE party_number IN ({placeholders}) AND status = 'Pending'
        ORDER BY start_date DESC
    """
    cursor.execute(query, tuple(party_numbers))
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    return entries

def update_tour_status(entry_id, status, remarks=''):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tour_diaries 
        SET status = %s, remarks = %s 
        WHERE id = %s
    """, (status, remarks, entry_id))
    conn.commit()
    cursor.close()
    conn.close()

    # Tour Diary Report - db.py

def get_all_tour_entries():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tour_diaries ORDER BY start_date DESC")
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    return entries

def get_tour_entries_by_party_numbers(party_numbers):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if not party_numbers:
        return []
    placeholders = ','.join(['%s'] * len(party_numbers))
    cursor.execute(f"""
        SELECT * FROM tour_diaries 
        WHERE party_number IN ({placeholders})
        ORDER BY start_date DESC
    """, tuple(party_numbers))
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    return entries

def get_user_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users ORDER BY username")
    users = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return users
