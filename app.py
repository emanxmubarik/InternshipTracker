from flask import Flask, render_template, request, redirect, session, make_response
import sqlite3
from openpyxl import Workbook
from io import BytesIO

app = Flask(__name__)
app.secret_key = "your_secret_key_here"


#Database
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            applied_date TEXT,
            deadline TEXT,
            job_link TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# Helper function
# -----------------------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# Home page
# -----------------------------
@app.route("/")
def home():
    return render_template("home.html")


# -----------------------------
# Register
# -----------------------------
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
            return redirect("/login")
        except sqlite3.IntegrityError:
            message = "Username already exists."
            conn.close()

    return render_template("register.html", message=message)


# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            message = "Invalid username or password."

    return render_template("login.html", message=message)


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


#Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )
    applications = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ?",
        (user_id,)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Applied'",
        (user_id,)
    )
    applied_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Interview'",
        (user_id,)
    )
    interview_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Offer'",
        (user_id,)
    )
    offer_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Rejected'",
        (user_id,)
    )
    rejected_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        applications=applications,
        total=total,
        applied_count=applied_count,
        interview_count=interview_count,
        offer_count=offer_count,
        rejected_count=rejected_count
    )


# -----------------------------
# Add application
# -----------------------------
@app.route("/add", methods=["GET", "POST"])
def add_application():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        company = request.form["company"]
        role = request.form["role"]
        category = request.form["category"]
        status = request.form["status"]
        applied_date = request.form["applied_date"]
        deadline = request.form["deadline"]
        job_link = request.form["job_link"]
        notes = request.form["notes"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO applications
            (user_id, company, role, category, status, applied_date, deadline, job_link, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            company,
            role,
            category,
            status,
            applied_date,
            deadline,
            job_link,
            notes
        ))
        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_application.html")


# -----------------------------
# Preview application
# -----------------------------
@app.route("/preview/<int:id>")
def preview_application(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM applications WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    )
    application = cursor.fetchone()
    conn.close()

    if application is None:
        return "Application not found.", 404

    return render_template("preview.html", application=application)


# -----------------------------
# Delete application
# -----------------------------
@app.route("/delete/<int:id>")
def delete_application(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM applications WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect("/dashboard")


# -----------------------------
# Export Excel
# -----------------------------
@app.route("/export")
def export_excel():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT company, role, category, status, applied_date, deadline, job_link, notes
        FROM applications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Applications"

    headers = [
        "Company", "Role", "Category", "Status",
        "Applied Date", "Deadline", "Job Link", "Notes"
    ]
    sheet.append(headers)

    for row in rows:
        sheet.append([
            row["company"],
            row["role"],
            row["category"],
            row["status"],
            row["applied_date"],
            row["deadline"],
            row["job_link"],
            row["notes"]
        ])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=applications.xlsx"
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response


# -----------------------------
# Change password
# -----------------------------
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/login")

    message = ""

    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE id = ? AND password = ?",
            (session["user_id"], current_password)
        )
        user = cursor.fetchone()

        if user:
            cursor.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (new_password, session["user_id"])
            )
            conn.commit()
            message = "Password updated successfully."
        else:
            message = "Current password is incorrect."

        conn.close()

    return render_template("change_password.html", message=message)


if __name__ == "__main__":
    app.run(debug=True)