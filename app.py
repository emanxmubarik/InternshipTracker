from flask import Flask, render_template, request, redirect, session
from functools import wraps
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

#setting up database which only runs once
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    #users table (for login/registeration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    #applications table (stores all the internship details)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            deadline TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()

#helper function to connect to database
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


#this makes sure user is logged in before accessing certain pages
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrap


#login page
@app.route("/", methods=["GET", "POST"])
def login():
    message = ""

    #if user is already logged in, send them to home
    if "user_id" in session:
        return redirect("/home")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        #check if user exists
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            #store user in session so we know that they are logged in
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/home")
        else:
            message = "Invalid username or password."

    return render_template("login.html", message=message)


#to register new users
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
            conn.close()
            return redirect("/")
        except sqlite3.IntegrityError:
            message = "Username already exists."
            conn.close()

    return render_template("register.html", message=message)


#logout -> which also clears session
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


#main page (also the spreadsheet page)
@app.route("/home")
@login_required
def home():
    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    #gets all applications for this user
    cursor.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )
    applications = cursor.fetchall()

    conn.close()

    return render_template("home.html", applications=applications)


#add new application
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_application():
    if request.method == "POST":
        company = request.form["company"]
        role = request.form["role"]
        category = request.form["category"]
        status = request.form["status"]
        deadline = request.form["deadline"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO applications
            (user_id, company, role, category, status, deadline)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            company,
            role,
            category,
            status,
            deadline
        ))

        conn.commit()
        conn.close()

        return redirect("/home")

    return render_template("add_application.html")


#delete an application
@app.route("/delete/<int:id>")
@login_required
def delete_application(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM applications WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/home")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
