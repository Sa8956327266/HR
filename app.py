import streamlit as st
import pandas as pd
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import date

# --- Page Configuration ---
st.set_page_config(page_title="Saudi HR Portal", layout="wide", page_icon="🏢")

# --- Database Initialization ---
DB_FILE = "hr_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Employees table
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                    emp_id TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    password TEXT,
                    role TEXT,
                    iqama_number TEXT,
                    iqama_expiry DATE,
                    gosi_number TEXT,
                    job_title TEXT,
                    salary REAL
                )''')
    # Attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emp_id TEXT,
                    date DATE,
                    status TEXT
                )''')
    # Leave requests table
    c.execute('''CREATE TABLE IF NOT EXISTS leaves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emp_id TEXT,
                    start_date DATE,
                    end_date DATE,
                    reason TEXT,
                    status TEXT
                )''')
    
    # Default Admin Creation if empty
    c.execute("SELECT * FROM employees WHERE role='Admin'")
    if not c.fetchone():
        c.execute("INSERT INTO employees VALUES ('ADM01', 'Admin', 'admin@company.sa', 'admin123', 'Admin', '1000000000', '2030-01-01', 'GOSI-ADM', 'HR Manager', 15000)")
    conn.commit()
    conn.close()

init_db()

# --- Database Helpers ---
def run_query(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_db(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# --- Email Function ---
def send_email(to_email, subject, body):
    if not to_email:
        return False
    
    smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(st.secrets.get("SMTP_PORT", 587))
    sender_email = st.secrets.get("SENDER_EMAIL", "")
    sender_password = st.secrets.get("SENDER_PASSWORD", "")

    if not sender_email or not sender_password:
        return False

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return True
    except Exception as e:
        return False

# --- Authentication State ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login(emp_id, password):
    df = run_query("SELECT * FROM employees WHERE emp_id=? AND password=?", (emp_id, password))
    if not df.empty:
        st.session_state.user = df.iloc[0].to_dict()
        st.rerun()
        return True
    return False

def logout():
    st.session_state.user = None
    st.rerun()

# --- LOGIN SCREEN ---
if st.session_state.user is None:
    st.title("🇸🇦 Saudi HR Management Portal")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Sign In")
        emp_id_input = st.text_input("Employee ID / Admin ID")
        password_input = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            if not login(emp_id_input, password_input):
                st.error("Invalid Credentials!")
    st.stop()

# --- LOGGED IN USER STATE ---
current_user = st.session_state.user
st.sidebar.title(f"Welcome, {current_user['name']}")
st.sidebar.caption(f"Role: **{current_user['role']}** | ID: {current_user['emp_id']}")

if st.sidebar.button("Logout"):
    logout()

# --- ADMIN PANEL ---
if current_user['role'] == "Admin":
    menu = st.sidebar.radio("Navigation", ["Manage Employees", "Mark Attendance", "Leave Requests", "Reports & Saudi Compliance"])

    # 1. Manage Employees
    if menu == "Manage Employees":
        st.header("👥 Employee Directory & Management")
        
        tab1, tab2, tab3 = st.tabs(["View / Search", "Add New Employee", "Update / Delete"])
        
        with tab1:
            emp_df = run_query("SELECT * FROM employees")
            if not emp_df.empty:
                st.dataframe(emp_df.drop(columns=['password']), use_container_width=True)
            else:
                st.info("No employees found.")
            
        with tab2:
            st.subheader("Add Employee Record")
            with st.form("add_emp"):
                e_id = st.text_input("Employee ID (Unique)").strip()
                e_name = st.text_input("Full Name").strip()
                e_email = st.text_input("Email").strip()
                e_pass = st.text_input("Password", type="password")
                e_role = st.selectbox("Role", ["Employee", "Admin"])
                e_iqama = st.text_input("Iqama Number (10 Digits)")
                e_iqama_exp = st.date_input("Iqama Expiry Date")
                e_gosi = st.text_input("GOSI Number")
                e_job = st.text_input("Job Title")
                e_salary = st.number_input("Basic Salary (SAR)", min_value=0.0)
                
                submitted = st.form_submit_button("Save Employee")
                if submitted:
                    if not e_id or not e_name:
                        st.error("⚠️ Employee ID and Name are required!")
                    else:
                        existing = run_query("SELECT * FROM employees WHERE emp_id=?", (e_id,))
                        if not existing.empty:
                            st.error(f"❌ Employee ID '{e_id}' already exists! Please use a unique ID.")
                        else:
                            execute_db("INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?)",
                                       (e_id, e_name, e_email, e_pass, e_role, e_iqama, e_iqama_exp, e_gosi, e_job, e_salary))
                            st.success(f"✅ Employee {e_name} added successfully!")
                            mail_sent = send_email(e_email, "Welcome to HR Portal", f"Hello {e_name},\nYour account has been created.\nID: {e_id}\nPassword: {e_pass}")
                            if mail_sent:
                                st.info("📧 Welcome email sent to employee.")

        with tab3:
            st.subheader("Modify or Delete Employee")
            emp_list = run_query("SELECT emp_id FROM employees")['emp_id'].tolist()
            if emp_list:
                selected_emp = st.selectbox("Select Employee ID to Manage", emp_list)
                
                if selected_emp:
                    emp_data = run_query("SELECT * FROM employees WHERE emp_id=?", (selected_emp,)).iloc[0]
                    
                    with st.form("edit_emp"):
                        u_name = st.text_input("Name", value=emp_data['name'])
                        u_email = st.text_input("Email", value=emp_data['email'])
                        u_role = st.selectbox("Role", ["Employee", "Admin"], index=0 if emp_data['role']=="Employee" else 1)
                        u_iqama = st.text_input("Iqama Number", value=emp_data['iqama_number'])
                        u_job = st.text_input("Job Title", value=emp_data['job_title'])
                        u_salary = st.number_input("Salary (SAR)", value=float(emp_data['salary']))
                        
                        update_btn = st.form_submit_button("Update Details")
                        
                        if update_btn:
                            execute_db("UPDATE employees SET name=?, email=?, role=?, iqama_number=?, job_title=?, salary=? WHERE emp_id=?",
                                       (u_name, u_email, u_role, u_iqama, u_job, u_salary, selected_emp))
                            st.success("Record updated successfully!")
                            st.rerun()

                    if st.button("❌ Delete Employee Record", type="secondary"):
                        execute_db("DELETE FROM employees WHERE emp_id=?", (selected_emp,))
                        st.warning(f"Deleted Employee {selected_emp}")
                        st.rerun()
            else:
                st.info("No employees found.")

    # 2. Mark Attendance
    elif menu == "Mark Attendance":
        st.header("📅 Daily Attendance Entry")
        att_date = st.date_input("Attendance Date", value=date.today())
        
        emps = run_query("SELECT emp_id, name FROM employees WHERE role='Employee'")
        
        if not emps.empty:
            attendance_dict = {}
            st.write("Mark Status:")
            for idx, row in emps.iterrows():
                col_a, col_b = st.columns([2, 2])
                col_a.write(f"**{row['name']}** ({row['emp_id']})")
                attendance_dict[row['emp_id']] = col_b.radio(f"Status for {row['emp_id']}", ["Present", "Absent", "On Leave"], key=row['emp_id'], horizontal=True)

            if st.button("Submit Attendance", type="primary"):
                for e_id, status in attendance_dict.items():
                    execute_db("DELETE FROM attendance WHERE emp_id=? AND date=?", (e_id, att_date))
                    execute_db("INSERT INTO attendance (emp_id, date, status) VALUES (?,?,?)", (e_id, att_date, status))
                st.success("Attendance Recorded Successfully!")
        else:
            st.info("No regular employees found to mark attendance.")

    # 3. Leave Requests
    elif menu == "Leave Requests":
        st.header("🏖️ Manage Leave Applications")
        pending_leaves = run_query("SELECT * FROM leaves WHERE status='Pending'")
        
        if pending_leaves.empty:
            st.info("No pending leave requests.")
        else:
            for idx, row in pending_leaves.iterrows():
                st.write(f"**Leave ID:** {row['id']} | **Emp ID:** {row['emp_id']} | **Dates:** {row['start_date']} to {row['end_date']}")
                st.write(f"**Reason:** {row['reason']}")
                
                c1, c2, _ = st.columns([1, 1, 4])
                if c1.button("Approve", key=f"app_{row['id']}"):
                    execute_db("UPDATE leaves SET status='Approved' WHERE id=?", (row['id'],))
                    emp_mail = run_query("SELECT email FROM employees WHERE emp_id=?", (row['emp_id'],)).iloc[0]['email']
                    send_email(emp_mail, "Leave Request Approved", f"Your leave from {row['start_date']} to {row['end_date']} has been approved.")
                    st.success("Leave Approved!")
                    st.rerun()
                    
                if c2.button("Reject", key=f"rej_{row['id']}"):
                    execute_db("UPDATE leaves SET status='Rejected' WHERE id=?", (row['id'],))
                    emp_mail = run_query("SELECT email FROM employees WHERE emp_id=?", (row['emp_id'],)).iloc[0]['email']
                    send_email(emp_mail, "Leave Request Rejected", f"Your leave request from {row['start_date']} to {row['end_date']} was rejected.")
                    st.warning("Leave Rejected!")
                    st.rerun()
                st.divider()

    # 4. Reports & Saudi Compliance
    elif menu == "Reports & Saudi Compliance":
        st.header("🇸🇦 Saudi HR Compliance Dashboard")
        
        st.subheader("⚠️ Upcoming / Expired Iqama Alerts")
        iqama_df = run_query("SELECT emp_id, name, iqama_number, iqama_expiry FROM employees")
        if not iqama_df.empty:
            iqama_df['iqama_expiry'] = pd.to_datetime(iqama_df['iqama_expiry'])
            today = pd.to_datetime(date.today())
            
            iqama_df['Days_Left'] = (iqama_df['iqama_expiry'] - today).dt.days
            alert_df = iqama_df[iqama_df['Days_Left'] <= 60]
            
            if not alert_df.empty:
                st.warning("Attention: Iqamas expiring within 60 days or already expired!")
                st.dataframe(alert_df, use_container_width=True)
            else:
                st.success("All employee Iqamas are up to date.")
        else:
            st.info("No employee data available.")

# --- EMPLOYEE PANEL ---
else:
    menu = st.sidebar.radio("Navigation", ["My Profile", "My Attendance", "Apply Leave"])
    emp_id = current_user['emp_id']

    if menu == "My Profile":
        st.header("👤 My Saudi Employment Profile")
        emp_info = run_query("SELECT * FROM employees WHERE emp_id=?", (emp_id,)).iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Full Name:** {emp_info['name']}")
            st.write(f"**Employee ID:** {emp_info['emp_id']}")
            st.write(f"**Email:** {emp_info['email']}")
            st.write(f"**Job Title:** {emp_info['job_title']}")
            
        with col2:
            st.write(f"**Iqama ID:** {emp_info['iqama_number']}")
            st.write(f"**Iqama Expiry:** {emp_info['iqama_expiry']}")
            st.write(f"**GOSI Number:** {emp_info['gosi_number']}")
            st.write(f"**Basic Salary:** {emp_info['salary']} SAR")

    elif menu == "My Attendance":
        st.header("📊 My Attendance Record")
        my_att = run_query("SELECT date, status FROM attendance WHERE emp_id=? ORDER BY date DESC", (emp_id,))
        if not my_att.empty:
            st.dataframe(my_att, use_container_width=True)
        else:
            st.info("No attendance records found.")

    elif menu == "Apply Leave":
        st.header("📝 Submit Leave Application")
        
        with st.form("leave_form"):
            s_date = st.date_input("Start Date")
            e_date = st.date_input("End Date")
            reason = st.text_area("Reason for Leave")
            
            submit = st.form_submit_button("Submit Request")
            if submit:
                execute_db("INSERT INTO leaves (emp_id, start_date, end_date, reason, status) VALUES (?,?,?,?,?)",
                           (emp_id, s_date, e_date, reason, "Pending"))
                st.success("Leave request submitted to Admin.")
                
                admin_rows = run_query("SELECT email FROM employees WHERE role='Admin'")
                if not admin_rows.empty:
                    admin_email = admin_rows.iloc[0]['email']
                    send_email(admin_email, f"New Leave Request: {emp_id}", f"Employee {emp_id} submitted leave from {s_date} to {e_date}.")

        st.subheader("My Leave History")
        my_leaves = run_query("SELECT start_date, end_date, reason, status FROM leaves WHERE emp_id=? ORDER BY id DESC", (emp_id,))
        if not my_leaves.empty:
            st.dataframe(my_leaves, use_container_width=True)
        else:
            st.info("No leave requests found.")
