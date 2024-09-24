import psycopg2
from datetime import datetime, timedelta

from pywebio.input import input_group, input, PASSWORD, DATE, select, actions
from pywebio.output import put_text, popup, put_buttons, put_table, put_html, put_row, put_link
from pywebio.session import run_js

# Function to connect to PostgreSQL database
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname="postgres", 
            user="postgres", 
            password="1234", 
            host="localhost", 
            port="5432"
        )
        return conn
    except Exception as e:
        popup("Database Connection Error", f"Error: {e}")
        return None

# Function to verify admin credentials
def verify_login(username, password):
    conn = connect_db()
    if conn is None:
        return False
    
    cursor = conn.cursor()
    query = 'SELECT * FROM "ADMIN" WHERE username = %s AND password = %s;'
    cursor.execute(query, (username, password))
    result = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return bool(result)

# Function to handle date range selection and show results
def select_date_range(username):
    # Push a new history state to enable browser back button functionality
    run_js('history.pushState(null, null, "#admin_dashboard");')
    run_js("""
        window.onpopstate = function() {
            window.location.reload();  // Reloads the page to go back to the login screen
        };
    """)
    
    current_date = datetime.now().date().strftime('%Y-%m-%d')
    access_types = ['Any', 'Staff', 'Janitor', 'Student']

    # Calculate the date 5 years ago
    date_5_years_back = datetime.now().date() - timedelta(days=5 * 365)
    formatted_date = date_5_years_back.strftime('%Y-%m-%d')
  
    # Input group for selecting date range
    date_info = input_group("Select Date Range", [
        input("Student ID (optional)", name='student_id', placeholder='Enter student ID (optional)'),
        input("From Date", name='from_date', type=DATE, required=True, value=formatted_date),
        input("To Date", name='to_date', type=DATE, required=True, value=current_date),
        select("Access Type", name='access_type', options=access_types, required=True)
    ])
    
    from_date = date_info['from_date']
    to_date = date_info['to_date']
    student_id = date_info['student_id']  # Can be empty
    access_type = date_info['access_type']

    # Query the sunlab records
    records = query_sunlab_records(from_date, to_date, student_id, access_type)
    
    if records:
        put_text("Records found:")
        headings = ["PSUID", "PSU EMAIL", "FIRST NAME", "LAST NAME", "LOGIN TIME", "LAB ACCESS", "ACCESS TYPE"]
        # Display the table with headings and records
        put_table([headings] + records)  # Combine headings with records
    else:
        put_text("No records found for the selected date range.")

# Function to query sunlab records based on date range
def query_sunlab_records(from_date, to_date, student_id, access_type):
    conn = connect_db()
    if conn is None:
        return []

    cursor = conn.cursor()
    query = 'SELECT u.psu_id, u.psu_email, u.first_name, u.last_name, sr.time_stamp, u.lab_access, u.access_type FROM "SUNLAB_RECORDS" sr JOIN "USERS" u ON sr.psu_id = u.psu_id WHERE sr.time_stamp BETWEEN %s AND %s'
    
    params = [from_date, to_date]
    if student_id:  # If student_id is provided, add it to the query
        query += ' AND u.psu_id = %s'
        params.append(student_id)
    if access_type != 'Any':
        query += ' AND u.access_type = %s'
        params.append(access_type)
    
    query += ' ORDER BY sr.time_stamp desc'
    cursor.execute(query, params)
    records = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return records

def enter_record(psu_id):
    current_date = datetime.now().date().strftime('%Y-%m-%d')
    conn = connect_db()
    if conn is None:
        return []

    cursor = conn.cursor()

    cursor.execute('INSERT INTO "SUNLAB_RECORDS" (psu_id, time_stamp, access_grant) VALUES (%s, %s, %s)', (psu_id, current_date,'Yes'))
  
    conn.commit()
    cursor.close()
    conn.close()

    return True
    


# Function to handle login UI and logic
def admin_login():
    # Creating input fields for login
    put_html("<h1 style='text-align: center;'>SunLab Records User</h1>") 
    choice = actions('Choose Action', ['Admin Login', 'User Registration'])

    if choice == 'Admin Login':
        login_info = input_group("Admin Login", [
            input("Username", name='username', required=True, placeholder='Enter username'),
            input("Password", name='password', type=PASSWORD, required=True, placeholder='Enter password')
        ])
        username = login_info['username']
        password = login_info['password']

        # Verify the credentials
        if verify_login(username, password):
            popup("Login Success", f"Welcome, {username}!")
            put_text(f"Logged in as {username}")
            select_date_range(username)
        else:
            popup("Login Failed", "Invalid username or password. Please try again.")
            put_buttons(["Retry"], onclick=lambda _: run_js("window.location.reload()"))

    elif choice == 'User Registration':
        registration_info = input_group("User Registration", [
            input("PSU ID", name='psu_id', required=True, placeholder='Enter PSU ID'),
        
        ])
        # Save registration details or send them to the backend for processing
        
        psu_id = registration_info['psu_id']

        # Handle registration logic
        if enter_record(psu_id):
            popup("Registration Success", f"Welcome, ")
            
           
        else:
            popup("Registration Failed", "There was an issue with your registration. Please try again.")
            put_buttons(["Retry"], onclick=lambda _: run_js("window.location.reload()"))


# Main function to start the web app
if __name__ == '__main__':
    from pywebio import start_server
    start_server(admin_login, port=8080)
