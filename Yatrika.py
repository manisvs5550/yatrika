from flask import Flask, render_template, request, redirect, session
import os
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
import re
from db import fetch_user_by_username, get_all_users, insert_user, update_user_role, delete_user, get_all_parties, insert_party, update_party, delete_party, get_all_users, get_party_by_user, get_tour_entries_by_user, insert_tour_entry, check_duplicate_tour_entry,get_pending_tour_entries_for_leader, update_tour_status,get_all_tour_entries, get_user_list, get_tour_entries_by_party_numbers, get_party_by_user

from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

USER_FILE = 'logins.xlsx'
PARTY_FILE = 'parties.xlsx'
TOUR_DIR = 'tour_diaries'
os.makedirs(TOUR_DIR, exist_ok=True)

# ---------- Utility Functions ----------

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_excel(USER_FILE)
    return pd.DataFrame(columns=['username', 'password', 'role'])

def save_users(df):
    df.to_excel(USER_FILE, index=False)

def load_parties():
    expected = ['party_number', 'leader_name', 'member_name']
    if os.path.exists(PARTY_FILE):
        df = pd.read_excel(PARTY_FILE)
        for col in expected:
            if col not in df.columns:
                df[col] = ""
        return df[expected]
    return pd.DataFrame(columns=expected)

def save_parties(df):
    df.to_excel(PARTY_FILE, index=False)

def get_party_number(username):
    df = load_parties()
    match = df[df['leader_name'].str.contains(username, na=False) | df['member_name'].str.contains(username, na=False)]
    if not match.empty:
        return match.iloc[0]['party_number']
    return None

# ---------- Routes ----------

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = fetch_user_by_username(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect('/menu')
        else:
            error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/menu')
def menu():
    if 'username' not in session:
        return redirect('/')
    return render_template('main_menu.html', username=session['username'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/users', methods=['GET', 'POST'])
def users():
    if 'username' not in session or session['role'] not in ['Super User', 'Administrator']:
        return redirect('/')

    message = ''
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role = request.form['role']
        action = request.form['action']

        if action == 'Add':
            existing = fetch_user_by_username(username)
            if existing:
                message = 'User already exists.'
            else:
                hashed_pw = generate_password_hash(password)
                insert_user(username, hashed_pw, role)
                message = 'User added successfully.'
        elif action == 'Edit':
            update_user_role(username, role)
            message = 'User updated.'
        elif action == 'Delete':
            delete_user(username)
            message = 'User deleted.'

    users = get_all_users()
    return render_template('user_management.html', users=users, message=message)

@app.route('/parties', methods=['GET', 'POST'])
def parties():
    if 'username' not in session or session['role'] not in ['Super User', 'Administrator']:
        return redirect('/')

    users = get_all_users()
    leaders = [u['username'] for u in users if u['role'] == 'Party Leader']
    members = [u['username'] for u in users if u['role'] == 'Party Member']
    message = ''

    if request.method == 'POST':
        action = request.form['action']
        number = request.form['party_number'].strip()
        leader_list = request.form.getlist('leader_name')
        member_list = request.form.getlist('member_name')
        leader_str = ', '.join(leader_list)
        member_str = ', '.join(member_list)

        existing = [p for p in get_all_parties() if p['party_number'] == number]

        if action == 'Add':
            if existing:
                message = 'Party already exists.'
            else:
                insert_party(number, leader_str, member_str)
                message = 'Party added.'
        elif action == 'Edit':
            update_party(number, leader_str, member_str)
            message = 'Party updated.'
        elif action == 'Delete':
            delete_party(number)
            message = 'Party deleted.'

    parties = get_all_parties()
    return render_template('party_management.html', leaders=leaders, members=members, parties=parties, message=message)

@app.route('/tour', methods=['GET', 'POST'])
def tour():
    if 'username' not in session:
        return redirect('/')

    username = session['username']
    role = session['role']
    if role == 'Super User':
        return render_template('tour_diary.html', default_date=None, role=role, message="Tour diary input is not applicable for Super Users.", entries=[])

    default_date = (datetime.today() - timedelta(days=datetime.today().weekday())).date()
    message = ''
    party_info = get_party_by_user(username)
    party_number = party_info['party_number'] if party_info else None
    entries = get_tour_entries_by_user(username) if party_number else []

    if request.method == 'POST':
        if not party_number:
            message = "No party assigned."
        else:
            start_date = request.form['start_date']
            office = request.form['office_name']
            work = request.form['work_done']
            latitude = request.form.get('latitude', '')
            longitude = request.form.get('longitude', '')
            action = request.form['action']
            status = 'Pending' if action == 'Send' else 'Submitted'
            entry_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if check_duplicate_tour_entry(username, start_date):
                message = f"You’ve already submitted a tour diary for {start_date}."
            else:
                entry = {
                    'party_number': party_number,
                    'start_date': start_date,
                    'office_name': office,
                    'work_done': work,
                    'latitude': latitude,
                    'longitude': longitude,
                    'status': status,
                    'submitted_by': username,
                    'remarks': '',
                    'entry_datetime': entry_datetime
                }
                insert_tour_entry(entry)
                message = "Entry sent for approval." if status == "Pending" else "Entry submitted."
                entries = get_tour_entries_by_user(username)

    return render_template('tour_diary.html', default_date=default_date, role=role, message=message, entries=entries)

@app.route('/review', methods=['GET', 'POST'])
def review():
    if 'username' not in session or session['role'] != 'Party Leader':
        return redirect('/')

    username = session['username']
    message = ''

    if request.method == 'POST':
        entry_id = int(request.form['entry_id'])
        action = request.form['action']
        if action == 'Approve':
            update_tour_status(entry_id, 'Approved')
        elif action == 'Reject':
            update_tour_status(entry_id, 'Rejected', 'Your tour diary entry has been rejected by the Party Leader.')

    entries = get_pending_tour_entries_for_leader(username)
    return render_template("review.html", entries=entries, message=message)

@app.route('/report/users')
def report_users():
    if 'username' not in session or session['role'] not in ['Super User', 'Administrator']:
        return redirect('/')

    df = load_users()
    df = df.sort_values(by=['role', 'username'], ascending=[True, True])
    users = df.to_dict('records')
    return render_template('report_users.html', users=users)

@app.route('/report/parties')
def report_parties():
    if 'username' not in session or session['role'] not in ['Super User', 'Administrator']:
        return redirect('/')

    df = load_parties()
    df = df.sort_values(by='party_number')
    parties = df.to_dict('records')
    return render_template('report_parties.html', parties=parties)

@app.route('/report/inactive', methods=['GET', 'POST'])
def report_inactive():
    if 'username' not in session or session['role'] not in ['Super User', 'Administrator']:
        return redirect('/')

    users_df = load_users()
    parties_df = load_parties()
    inactive_users = []
    report_date = datetime.date.today()

    if request.method == 'POST':
        report_date = datetime.datetime.strptime(request.form['report_date'], "%Y-%m-%d").date()

    for _, user in users_df.iterrows():
        username = user['username']
        role = user['role']
        if role not in ['Party Member', 'Party Leader']:
            continue
        party_number = get_party_number(username)
        if not party_number:
            inactive_users.append({'username': username, 'role': role, 'last_entry': 'No Party'})
            continue

        safe_party_number = sanitize_filename(party_number)
        file_path = os.path.join(TOUR_DIR, f"{safe_party_number}.xlsx")

        last_entry_date = None
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            user_entries = df[df['submitted_by'] == username]
            if not user_entries.empty:
                user_entries['entry_datetime'] = pd.to_datetime(user_entries['entry_datetime'], errors='coerce')
                filtered = user_entries[user_entries['entry_datetime'].dt.date <= report_date]
                if not filtered.empty:
                    last_entry_date = filtered['entry_datetime'].max().strftime("%Y-%m-%d")

        if not last_entry_date:
            inactive_users.append({'username': username, 'role': role, 'last_entry': 'None'})
    
    return render_template('report_inactive.html', users=inactive_users, report_date=report_date)

@app.route('/report/delayed')
def report_delayed():
    if 'username' not in session or session['role'] not in ['Super User', 'Administrator']:
        return redirect('/')

    delayed_entries = []

    if os.path.exists(TOUR_DIR):
        for file in os.listdir(TOUR_DIR):
            if file.endswith('.xlsx'):
                df = pd.read_excel(os.path.join(TOUR_DIR, file))
                if 'start_date' in df.columns and 'entry_datetime' in df.columns:
                    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
                    df['entry_datetime'] = pd.to_datetime(df['entry_datetime'], errors='coerce')
                    df['delay_days'] = (df['entry_datetime'] - df['start_date']).dt.days
                    delayed = df[df['delay_days'] > 3]
                    if not delayed.empty:
                        delayed_entries.extend(delayed.to_dict('records'))

    return render_template('report_delayed.html', entries=delayed_entries)

@app.route('/report/diary', methods=['GET', 'POST'])
def report_diary():
    if 'username' not in session:
        return redirect('/')

    username = session['username']
    role = session['role']
    from_date = to_date = datetime.today().strftime('%Y-%m-%d')
    status_filter = "All"
    selected_user = "All"
    entries = []
    user_list = get_user_list()

    if request.method == 'POST':
        from_date = request.form.get('from_date', from_date)
        to_date = request.form.get('to_date', to_date)
        status_filter = request.form.get('status', 'All')
        selected_user = request.form.get('selected_user', 'All')

    from_dt = datetime.strptime(from_date, '%Y-%m-%d').date()
    to_dt = datetime.strptime(to_date, '%Y-%m-%d').date()

    if role in ['Super User', 'Administrator']:
        raw_entries = get_all_tour_entries()
    else:
        party = get_party_by_user(username)
        party_number = party['party_number'] if party else None
        raw_entries = get_tour_entries_by_party_numbers([party_number]) if party_number else []

    for row in raw_entries:
        row_date = row['start_date']
        if isinstance(row_date, str):
            row_date = datetime.strptime(row_date, '%Y-%m-%d').date()
        if not (from_dt <= row_date <= to_dt):
            continue
        if selected_user != 'All' and row['submitted_by'] != selected_user:
            continue
        if status_filter != 'All' and row['status'] != status_filter:
            continue

        remarks = row.get('remarks') or ''
        entries.append({
            'start_date': row_date,
            'office_name': row.get('office_name', ''),
            'work_done': row.get('work_done', ''),
            'status': row.get('status', ''),
            'submitted_by': row.get('submitted_by', ''),
            'entry_datetime': row.get('entry_datetime', ''),
            'remarks': remarks
        })

    return render_template("report_diary.html",
                           entries=entries,
                           from_date=from_date,
                           to_date=to_date,
                           status_filter=status_filter,
                           selected_user=selected_user,
                           user_list=user_list,
                           role=role)

    # Show only pending entries
    pending = df[df['status'] == 'Pending'].reset_index()
    return render_template('review.html', entries=pending.to_dict('records'), message="")
if __name__ == "__main__":
    app.run(debug=True)