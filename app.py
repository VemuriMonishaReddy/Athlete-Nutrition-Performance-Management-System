from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
import mysql.connector
from dotenv import load_dotenv
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

ROLE_ENDPOINTS = {
    "ADMIN": {"*"},
    "COACH": {
        "index", "dashboard", "logout", "athletes", "workout_plans",
        "add_workout_plan", "edit_workout_plan", "delete_workout_plan",
        "attendance", "add_attendance", "edit_attendance", "delete_attendance",
        "competitions", "add_competition", "edit_competition", "delete_competition",
        "performance", "add_performance", "edit_performance", "delete_performance",
        "progress", "add_progress", "edit_progress", "delete_progress",
        "exercises", "add_exercise", "edit_exercise", "delete_exercise"
    },
    "NUTRITIONIST": {
        "index", "dashboard", "logout", "athletes", "diet_plans",
        "add_diet_plan", "edit_diet_plan", "delete_diet_plan",
        "progress", "food", "add_food", "edit_food", "delete_food"
    },
    "ATHLETE": {"index", "dashboard", "logout", "my_profile", "my_records"}
}


def current_role():
    return session.get("role")


def get_current_user():
    return session.get("user")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "error")
                return redirect(url_for("login", next=request.path))
            if session.get("role") not in roles:
                flash("You are not authorized to access this page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def ensure_auth_table():
    """Create only the authentication table if it is missing; never touch existing project tables."""
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS App_User (
            User_ID INT AUTO_INCREMENT PRIMARY KEY,
            Username VARCHAR(100) NOT NULL UNIQUE,
            Password_Hash VARCHAR(255) NOT NULL,
            Role ENUM('ADMIN','COACH','NUTRITIONIST','ATHLETE') NOT NULL,
            Athlete_ID INT NULL,
            Coach_ID INT NULL,
            Nutritionist_ID INT NULL,
            Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    """)
    cursor.execute("SELECT COUNT(*) FROM App_User")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("SELECT Athlete_ID FROM Athlete ORDER BY Athlete_ID LIMIT 1")
        athlete_row = cursor.fetchone()
        cursor.execute("SELECT Coach_ID FROM Coach ORDER BY Coach_ID LIMIT 1")
        coach_row = cursor.fetchone()
        cursor.execute("SELECT Nutritionist_ID FROM Nutritionist ORDER BY Nutritionist_ID LIMIT 1")
        nutritionist_row = cursor.fetchone()
        defaults = [
            ("admin", "admin123", "ADMIN", None, None, None),
            ("coach", "coach123", "COACH", None, coach_row[0] if coach_row else None, None),
            ("nutritionist", "nutrition123", "NUTRITIONIST", None, None, nutritionist_row[0] if nutritionist_row else None),
            ("athlete", "athlete123", "ATHLETE", athlete_row[0] if athlete_row else None, None, None),
        ]
        cursor.executemany("""
            INSERT INTO App_User
            (Username, Password_Hash, Role, Athlete_ID, Coach_ID, Nutritionist_ID)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [(u, generate_password_hash(p), r, a, c, n) for u,p,r,a,c,n in defaults])
    connection.commit()
    cursor.close()
    connection.close()


@app.context_processor
def inject_auth_context():
    return {"current_user": get_current_user(), "current_role": current_role()}


@app.before_request
def protect_routes():
    endpoint = request.endpoint
    if endpoint in {None, "login", "static"}:
        return
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))
    role = session.get("role")
    allowed = ROLE_ENDPOINTS.get(role, set())
    if "*" not in allowed and endpoint not in allowed:
        flash("You are not authorized to access this page.", "error")
        return redirect(url_for("dashboard"))


def get_auth_user_by_username(username):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM App_User WHERE Username = %s", (username,))
    user = cursor.fetchone()
    cursor.close(); connection.close()
    return user


def auth_record_for_session():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM App_User WHERE User_ID = %s", (session.get("user_id"),))
    user = cursor.fetchone()
    cursor.close(); connection.close()
    return user

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )


@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")
        try:
            ensure_auth_table()
            user = get_auth_user_by_username(username)
            if not user or not check_password_hash(user["Password_Hash"], password):
                flash("Invalid username or password.", "error")
                return render_template("login.html")
            session.clear()
            session["user_id"] = user["User_ID"]
            session["username"] = user["Username"]
            session["role"] = user["Role"]
            session["user"] = {
                "User_ID": user["User_ID"],
                "Username": user["Username"],
                "Role": user["Role"],
                "Athlete_ID": user["Athlete_ID"],
                "Coach_ID": user["Coach_ID"],
                "Nutritionist_ID": user["Nutritionist_ID"],
            }
            next_url = request.args.get("next") or request.form.get("next")
            return redirect(next_url if next_url and next_url.startswith("/") else url_for("dashboard"))
        except mysql.connector.Error as exc:
            flash(f"Database connection error: {exc}", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    user = auth_record_for_session()
    role = user["Role"]
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    stats = {}
    for table, key in [
        ("Athlete", "athletes"), ("Coach", "coaches"), ("Sport", "sports"),
        ("Nutritionist", "nutritionists"), ("Diet_Plan", "diet_plans"),
        ("Workout_Plan", "workout_plans"), ("Competition", "competitions")
    ]:
        cursor.execute(f"SELECT COUNT(*) AS total FROM `{table}`")
        stats[key] = cursor.fetchone()["total"]
    personal = {}
    if role == "ATHLETE" and user.get("Athlete_ID"):
        aid = user["Athlete_ID"]
        queries = {
            "attendance": "SELECT COUNT(*) AS total FROM Attendance WHERE Athlete_ID=%s",
            "performance": "SELECT COUNT(*) AS total FROM Performance WHERE Athlete_ID=%s",
            "progress": "SELECT COUNT(*) AS total FROM Progress WHERE Athlete_ID=%s",
            "diet": "SELECT COUNT(*) AS total FROM Diet_Plan WHERE Athlete_ID=%s",
            "workout": "SELECT COUNT(*) AS total FROM Workout_Plan WHERE Athlete_ID=%s",
        }
        for key, q in queries.items():
            cursor.execute(q, (aid,)); personal[key] = cursor.fetchone()["total"]
    elif role == "COACH" and user.get("Coach_ID"):
        cid = user["Coach_ID"]
        cursor.execute("SELECT COUNT(*) AS total FROM Athlete WHERE Coach_ID=%s", (cid,)); personal["assigned_athletes"] = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM Workout_Plan WHERE Coach_ID=%s", (cid,)); personal["workouts"] = cursor.fetchone()["total"]
    elif role == "NUTRITIONIST" and user.get("Nutritionist_ID"):
        nid = user["Nutritionist_ID"]
        cursor.execute("SELECT COUNT(*) AS total FROM Diet_Plan WHERE Nutritionist_ID=%s", (nid,)); personal["diet_plans"] = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(DISTINCT Athlete_ID) AS total FROM Diet_Plan WHERE Nutritionist_ID=%s", (nid,)); personal["assigned_athletes"] = cursor.fetchone()["total"]
    cursor.close(); connection.close()
    return render_template("dashboard.html", stats=stats, personal=personal, user=user)


@app.route("/my-profile")
def my_profile():
    user = auth_record_for_session()
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    athlete = coach = nutritionist = None
    if user.get("Athlete_ID"):
        cursor.execute("SELECT * FROM Athlete WHERE Athlete_ID=%s", (user["Athlete_ID"],)); athlete = cursor.fetchone()
    if user.get("Coach_ID"):
        cursor.execute("SELECT * FROM Coach WHERE Coach_ID=%s", (user["Coach_ID"],)); coach = cursor.fetchone()
    if user.get("Nutritionist_ID"):
        cursor.execute("SELECT * FROM Nutritionist WHERE Nutritionist_ID=%s", (user["Nutritionist_ID"],)); nutritionist = cursor.fetchone()
    cursor.close(); connection.close()
    return render_template("my_profile.html", user=user, athlete=athlete, coach=coach, nutritionist=nutritionist)


@app.route("/my-records")
def my_records():
    user = auth_record_for_session()
    if user["Role"] != "ATHLETE" or not user.get("Athlete_ID"):
        return redirect(url_for("dashboard"))
    aid = user["Athlete_ID"]
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    cursor.execute("""SELECT a.*, s.Sport_Name, c.Name AS Coach_Name FROM Athlete a LEFT JOIN Sport s ON a.Sport_ID=s.Sport_ID LEFT JOIN Coach c ON a.Coach_ID=c.Coach_ID WHERE a.Athlete_ID=%s""", (aid,)); athlete = cursor.fetchone()
    cursor.execute("""SELECT d.*, n.Name AS Nutritionist_Name FROM Diet_Plan d LEFT JOIN Nutritionist n ON d.Nutritionist_ID=n.Nutritionist_ID WHERE d.Athlete_ID=%s ORDER BY d.Start_Date DESC""", (aid,)); diet_plans = cursor.fetchall()
    cursor.execute("""SELECT w.*, c.Name AS Coach_Name FROM Workout_Plan w LEFT JOIN Coach c ON w.Coach_ID=c.Coach_ID WHERE w.Athlete_ID=%s ORDER BY w.Start_Date DESC""", (aid,)); workouts = cursor.fetchall()
    cursor.execute("SELECT * FROM Attendance WHERE Athlete_ID=%s ORDER BY Attendance_Date DESC", (aid,)); attendance_records = cursor.fetchall()
    cursor.execute("""SELECT p.*, c.Competition_Name FROM Performance p LEFT JOIN Competition c ON p.Competition_ID=c.Competition_ID WHERE p.Athlete_ID=%s ORDER BY p.Performance_Date DESC""", (aid,)); performances = cursor.fetchall()
    cursor.execute("SELECT * FROM Progress WHERE Athlete_ID=%s ORDER BY Record_Date DESC", (aid,)); progress_records = cursor.fetchall()
    cursor.close(); connection.close()
    return render_template("my_records.html", athlete=athlete, diet_plans=diet_plans, workouts=workouts, attendance_records=attendance_records, performances=performances, progress_records=progress_records)


@app.route("/athletes")
def athletes():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    role = session.get("role")
    user = auth_record_for_session() if role in {"COACH", "NUTRITIONIST"} else None
    query = """
        SELECT DISTINCT
            a.Athlete_ID, a.Name, a.Age, a.Gender, a.Height, a.Weight, a.Contact,
            a.Sport_ID, a.Coach_ID, s.Sport_Name, c.Name AS Coach_Name
        FROM Athlete a
        JOIN Sport s ON a.Sport_ID = s.Sport_ID
        LEFT JOIN Coach c ON a.Coach_ID = c.Coach_ID
    """
    params = ()
    if role == "COACH" and user and user.get("Coach_ID"):
        query += " WHERE a.Coach_ID = %s"
        params = (user["Coach_ID"],)
    elif role == "NUTRITIONIST" and user and user.get("Nutritionist_ID"):
        query += " JOIN Diet_Plan dp ON dp.Athlete_ID = a.Athlete_ID WHERE dp.Nutritionist_ID = %s"
        params = (user["Nutritionist_ID"],)
    query += " ORDER BY a.Athlete_ID"
    cursor.execute(query, params)

    athletes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("athletes.html", athletes=athletes)


@app.route("/athletes/add", methods=["GET", "POST"])
def add_athlete():

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        height = request.form["height"]
        weight = request.form["weight"]
        contact = request.form["contact"]
        sport_id = request.form["sport_id"]
        coach_id = request.form["coach_id"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Athlete
            (Name, Age, Gender, Height, Weight, Contact, Sport_ID, Coach_ID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name,
            age,
            gender,
            height,
            weight,
            contact,
            sport_id,
            coach_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("athletes"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Sport ORDER BY Sport_Name")
    sports = cursor.fetchall()

    cursor.execute("SELECT * FROM Coach ORDER BY Name")
    coaches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "athlete_form.html",
        sports=sports,
        coaches=coaches
    )

@app.route("/athletes/edit/<int:athlete_id>", methods=["GET", "POST"])
def edit_athlete(athlete_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        height = request.form["height"]
        weight = request.form["weight"]
        contact = request.form["contact"]
        sport_id = request.form["sport_id"]
        coach_id = request.form["coach_id"]

        cursor.execute("""
            UPDATE Athlete
            SET Name = %s,
                Age = %s,
                Gender = %s,
                Height = %s,
                Weight = %s,
                Contact = %s,
                Sport_ID = %s,
                Coach_ID = %s
            WHERE Athlete_ID = %s
        """, (
            name,
            age,
            gender,
            height,
            weight,
            contact,
            sport_id,
            coach_id,
            athlete_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("athletes"))

    cursor.execute(
        "SELECT * FROM Athlete WHERE Athlete_ID = %s",
        (athlete_id,)
    )

    athlete = cursor.fetchone()

    cursor.execute("SELECT * FROM Sport ORDER BY Sport_Name")
    sports = cursor.fetchall()

    cursor.execute("SELECT * FROM Coach ORDER BY Name")
    coaches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "athlete_form.html",
        athlete=athlete,
        sports=sports,
        coaches=coaches,
        edit_mode=True
    )

@app.route("/athletes/delete/<int:athlete_id>", methods=["POST"])
def delete_athlete(athlete_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        # Delete records that depend on Diet_Plan
        cursor.execute("""
            DELETE FROM Diet_Plan_Food
            WHERE Diet_ID IN (
                SELECT Diet_ID
                FROM Diet_Plan
                WHERE Athlete_ID = %s
            )
        """, (athlete_id,))

        # Delete records that depend on Workout_Plan
        cursor.execute("""
            DELETE FROM Workout_Exercise
            WHERE Workout_ID IN (
                SELECT Workout_ID
                FROM Workout_Plan
                WHERE Athlete_ID = %s
            )
        """, (athlete_id,))

        # Delete athlete-related records
        cursor.execute("""
            DELETE FROM Attendance
            WHERE Athlete_ID = %s
        """, (athlete_id,))

        cursor.execute("""
            DELETE FROM Performance
            WHERE Athlete_ID = %s
        """, (athlete_id,))

        cursor.execute("""
            DELETE FROM Progress
            WHERE Athlete_ID = %s
        """, (athlete_id,))

        cursor.execute("""
            DELETE FROM Diet_Plan
            WHERE Athlete_ID = %s
        """, (athlete_id,))

        cursor.execute("""
            DELETE FROM Workout_Plan
            WHERE Athlete_ID = %s
        """, (athlete_id,))

        # Finally delete the athlete
        cursor.execute("""
            DELETE FROM Athlete
            WHERE Athlete_ID = %s
        """, (athlete_id,))

        connection.commit()

    except Exception as e:

        connection.rollback()
        print("Error deleting athlete:", e)

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("athletes"))

@app.route("/coaches")
def coaches():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            c.Coach_ID,
            c.Name,
            c.Experience,
            c.Contact,
            s.Sport_Name
        FROM Coach c
        LEFT JOIN Sport s
            ON c.Sport_ID = s.Sport_ID
        ORDER BY c.Coach_ID
    """)

    coaches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("coaches.html", coaches=coaches)

@app.route("/coaches/add", methods=["GET", "POST"])
def add_coach():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        experience = request.form["experience"]
        contact = request.form["contact"]
        sport_id = request.form["sport_id"]

        cursor.execute("""
            INSERT INTO Coach (Name, Experience, Contact, Sport_ID)
            VALUES (%s, %s, %s, %s)
        """, (name, experience, contact, sport_id))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("coaches"))

    cursor.execute("SELECT Sport_ID, Sport_Name FROM Sport ORDER BY Sport_Name")
    sports = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("add_coach.html", sports=sports)

@app.route("/coaches/edit/<int:coach_id>", methods=["GET", "POST"])
def edit_coach(coach_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        experience = request.form["experience"]
        contact = request.form["contact"]
        sport_id = request.form["sport_id"]

        cursor.execute("""
            UPDATE Coach
            SET Name = %s,
                Experience = %s,
                Contact = %s,
                Sport_ID = %s
            WHERE Coach_ID = %s
        """, (name, experience, contact, sport_id, coach_id))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("coaches"))

    cursor.execute(
        "SELECT * FROM Coach WHERE Coach_ID = %s",
        (coach_id,)
    )

    coach = cursor.fetchone()

    cursor.execute(
        "SELECT Sport_ID, Sport_Name FROM Sport ORDER BY Sport_Name"
    )

    sports = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_coach.html",
        coach=coach,
        sports=sports
    )

@app.route("/coaches/delete/<int:coach_id>", methods=["POST"])
def delete_coach(coach_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM Coach WHERE Coach_ID = %s",
        (coach_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("coaches"))

@app.route("/sports")
def sports():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Sport_ID, Sport_Name
        FROM Sport
        ORDER BY Sport_ID
    """)

    sports = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("sports.html", sports=sports)

@app.route("/sports/add", methods=["GET", "POST"])
def add_sport():

    if request.method == "POST":

        sport_name = request.form["sport_name"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Sport (Sport_Name)
            VALUES (%s)
        """, (sport_name,))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("sports"))

    return render_template("sport_form.html")

@app.route("/sports/edit/<int:sport_id>", methods=["GET", "POST"])
def edit_sport(sport_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        sport_name = request.form["sport_name"]

        cursor.execute("""
            UPDATE Sport
            SET Sport_Name = %s
            WHERE Sport_ID = %s
        """, (sport_name, sport_id))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("sports"))

    cursor.execute("""
        SELECT Sport_ID, Sport_Name
        FROM Sport
        WHERE Sport_ID = %s
    """, (sport_id,))

    sport = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "sport_form.html",
        sport=sport,
        edit_mode=True
    )

@app.route("/sports/delete/<int:sport_id>", methods=["POST"])
def delete_sport(sport_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Get sport name
        cursor.execute("""
            SELECT Sport_Name
            FROM Sport
            WHERE Sport_ID = %s
        """, (sport_id,))

        sport = cursor.fetchone()

        if not sport:
            flash("Sport not found.", "error")
            return redirect(url_for("sports"))

        sport_name = sport["Sport_Name"]

        # Check dependencies
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM Athlete
            WHERE Sport_ID = %s
        """, (sport_id,))

        athlete_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM Coach
            WHERE Sport_ID = %s
        """, (sport_id,))

        coach_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM Competition
            WHERE Sport_ID = %s
        """, (sport_id,))

        competition_count = cursor.fetchone()["count"]

        # Prevent deletion if sport is being used
        if athlete_count > 0 or coach_count > 0 or competition_count > 0:

            flash(
                f"Cannot delete {sport_name}. "
                f"It is being used by "
                f"{athlete_count} athlete(s), "
                f"{coach_count} coach(es), and "
                f"{competition_count} competition(s). "
                f"Reassign or delete these records first.",
                "error"
            )

            return redirect(url_for("sports"))

        # Safe to delete
        cursor.execute("""
            DELETE FROM Sport
            WHERE Sport_ID = %s
        """, (sport_id,))

        connection.commit()

        flash(
            f"{sport_name} deleted successfully.",
            "success"
        )

    except Exception as e:

        connection.rollback()

        print("Error deleting sport:", e)

        flash(
            "An error occurred while deleting the sport.",
            "error"
        )

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("sports"))

@app.route("/nutritionists")
def nutritionists():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            Nutritionist_ID,
            Name,
            Qualification,
            Contact
        FROM Nutritionist
        ORDER BY Nutritionist_ID
    """)

    nutritionists = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "nutritionists.html",
        nutritionists=nutritionists
    )


@app.route("/nutritionists/add", methods=["GET", "POST"])
def add_nutritionist():

    if request.method == "POST":

        name = request.form["name"]
        qualification = request.form["qualification"]
        contact = request.form["contact"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Nutritionist
            (Name, Qualification, Contact)
            VALUES (%s, %s, %s)
        """, (
            name,
            qualification,
            contact
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("nutritionists"))

    return render_template("add_nutritionist.html")


@app.route("/nutritionists/edit/<int:nutritionist_id>", methods=["GET", "POST"])
def edit_nutritionist(nutritionist_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        qualification = request.form["qualification"]
        contact = request.form["contact"]

        cursor.execute("""
            UPDATE Nutritionist
            SET Name = %s,
                Qualification = %s,
                Contact = %s
            WHERE Nutritionist_ID = %s
        """, (
            name,
            qualification,
            contact,
            nutritionist_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("nutritionists"))

    cursor.execute("""
        SELECT *
        FROM Nutritionist
        WHERE Nutritionist_ID = %s
    """, (nutritionist_id,))

    nutritionist = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "edit_nutritionist.html",
        nutritionist=nutritionist
    )


@app.route("/nutritionists/delete/<int:nutritionist_id>", methods=["POST"])
def delete_nutritionist(nutritionist_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Nutritionist
        WHERE Nutritionist_ID = %s
    """, (nutritionist_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("nutritionists"))

# =========================
# DIET PLAN
# =========================

@app.route("/diet-plans")
def diet_plans():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT d.Diet_ID, d.Athlete_ID, d.Nutritionist_ID, d.Plan_Name, d.Start_Date, d.End_Date, d.Calories_Target,
               a.Name AS Athlete_Name, n.Name AS Nutritionist_Name
        FROM Diet_Plan d
        JOIN Athlete a ON d.Athlete_ID = a.Athlete_ID
        JOIN Nutritionist n ON d.Nutritionist_ID = n.Nutritionist_ID
    """
    params = ()
    if session.get("role") == "NUTRITIONIST":
        user = auth_record_for_session()
        query += " WHERE d.Nutritionist_ID = %s"
        params = (user["Nutritionist_ID"],)
    query += " ORDER BY d.Diet_ID"
    cursor.execute(query, params)

    diet_plans = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "diet_plans.html",
        diet_plans=diet_plans
    )


@app.route("/diet-plans/add", methods=["GET", "POST"])
def add_diet_plan():

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        nutritionist_id = request.form["nutritionist_id"]
        plan_name = request.form["plan_name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"] or None
        calories_target = request.form["calories_target"] or None

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Diet_Plan
            (
                Athlete_ID,
                Nutritionist_ID,
                Plan_Name,
                Start_Date,
                End_Date,
                Calories_Target
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            athlete_id,
            nutritionist_id,
            plan_name,
            start_date,
            end_date,
            calories_target
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("diet_plans"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)
    athletes = cursor.fetchall()

    cursor.execute("""
        SELECT Nutritionist_ID, Name
        FROM Nutritionist
        ORDER BY Name
    """)
    nutritionists = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_diet_plan.html",
        athletes=athletes,
        nutritionists=nutritionists
    )


@app.route("/diet-plans/edit/<int:diet_id>", methods=["GET", "POST"])
def edit_diet_plan(diet_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        nutritionist_id = request.form["nutritionist_id"]
        plan_name = request.form["plan_name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"] or None
        calories_target = request.form["calories_target"] or None

        cursor.execute("""
            UPDATE Diet_Plan
            SET Athlete_ID = %s,
                Nutritionist_ID = %s,
                Plan_Name = %s,
                Start_Date = %s,
                End_Date = %s,
                Calories_Target = %s
            WHERE Diet_ID = %s
        """, (
            athlete_id,
            nutritionist_id,
            plan_name,
            start_date,
            end_date,
            calories_target,
            diet_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("diet_plans"))

    cursor.execute("""
        SELECT *
        FROM Diet_Plan
        WHERE Diet_ID = %s
    """, (diet_id,))

    diet_plan = cursor.fetchone()

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)
    athletes = cursor.fetchall()

    cursor.execute("""
        SELECT Nutritionist_ID, Name
        FROM Nutritionist
        ORDER BY Name
    """)
    nutritionists = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_diet_plan.html",
        diet_plan=diet_plan,
        athletes=athletes,
        nutritionists=nutritionists
    )


@app.route("/diet-plans/delete/<int:diet_id>", methods=["POST"])
def delete_diet_plan(diet_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Diet_Plan
        WHERE Diet_ID = %s
    """, (diet_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("diet_plans"))


# =========================
# WORKOUT PLAN
# =========================

@app.route("/workout-plans")
def workout_plans():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT w.Workout_ID, w.Athlete_ID, w.Coach_ID, w.Plan_Name, w.Start_Date, w.End_Date,
               a.Name AS Athlete_Name, c.Name AS Coach_Name
        FROM Workout_Plan w
        JOIN Athlete a ON w.Athlete_ID = a.Athlete_ID
        JOIN Coach c ON w.Coach_ID = c.Coach_ID
    """
    params = ()
    if session.get("role") == "COACH":
        user = auth_record_for_session()
        query += " WHERE w.Coach_ID = %s"
        params = (user["Coach_ID"],)
    query += " ORDER BY w.Workout_ID"
    cursor.execute(query, params)

    workout_plans = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "workout_plans.html",
        workout_plans=workout_plans
    )


@app.route("/workout-plans/add", methods=["GET", "POST"])
def add_workout_plan():

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        coach_id = request.form["coach_id"]
        plan_name = request.form["plan_name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"] or None

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Workout_Plan
            (
                Athlete_ID,
                Coach_ID,
                Plan_Name,
                Start_Date,
                End_Date
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            athlete_id,
            coach_id,
            plan_name,
            start_date,
            end_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("workout_plans"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)
    athletes = cursor.fetchall()

    cursor.execute("""
        SELECT Coach_ID, Name
        FROM Coach
        ORDER BY Name
    """)
    coaches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_workout_plan.html",
        athletes=athletes,
        coaches=coaches
    )


@app.route("/workout-plans/edit/<int:workout_id>", methods=["GET", "POST"])
def edit_workout_plan(workout_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        coach_id = request.form["coach_id"]
        plan_name = request.form["plan_name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"] or None

        cursor.execute("""
            UPDATE Workout_Plan
            SET Athlete_ID = %s,
                Coach_ID = %s,
                Plan_Name = %s,
                Start_Date = %s,
                End_Date = %s
            WHERE Workout_ID = %s
        """, (
            athlete_id,
            coach_id,
            plan_name,
            start_date,
            end_date,
            workout_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("workout_plans"))

    cursor.execute("""
        SELECT *
        FROM Workout_Plan
        WHERE Workout_ID = %s
    """, (workout_id,))

    workout_plan = cursor.fetchone()

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)
    athletes = cursor.fetchall()

    cursor.execute("""
        SELECT Coach_ID, Name
        FROM Coach
        ORDER BY Name
    """)
    coaches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_workout_plan.html",
        workout_plan=workout_plan,
        athletes=athletes,
        coaches=coaches
    )


@app.route("/workout-plans/delete/<int:workout_id>", methods=["POST"])
def delete_workout_plan(workout_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Workout_Plan
        WHERE Workout_ID = %s
    """, (workout_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("workout_plans"))


# =========================
# ATTENDANCE
# =========================

@app.route("/attendance")
def attendance():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT at.Attendance_ID, at.Athlete_ID, a.Name AS Athlete_Name, at.Attendance_Date, at.Status
        FROM Attendance at JOIN Athlete a ON at.Athlete_ID = a.Athlete_ID
    """
    params = ()
    if session.get("role") == "COACH":
        user = auth_record_for_session(); query += " WHERE a.Coach_ID = %s"; params = (user["Coach_ID"],)
    query += " ORDER BY at.Attendance_Date, a.Name"
    cursor.execute(query, params)

    attendance_records = cursor.fetchall()

    cursor.close()
    connection.close()

    attendance_dates = sorted(
        set(record["Attendance_Date"] for record in attendance_records)
    )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            Athlete_ID,
            Name
        FROM Athlete
        ORDER BY Name
    """)

    athletes = cursor.fetchall()

    cursor.close()
    connection.close()

    attendance_matrix = {}

    for athlete in athletes:

        athlete_id = athlete["Athlete_ID"]

        attendance_matrix[athlete_id] = {
            "name": athlete["Name"],
            "records": {},
            "present": 0,
            "total": 0,
            "percentage": 0
        }

    for record in attendance_records:

        athlete_id = record["Athlete_ID"]
        attendance_date = record["Attendance_Date"]
        status = record["Status"]

        attendance_matrix[athlete_id]["records"][attendance_date] = status

        attendance_matrix[athlete_id]["total"] += 1

        if status == "Present":
            attendance_matrix[athlete_id]["present"] += 1

    for athlete_id in attendance_matrix:

        total = attendance_matrix[athlete_id]["total"]
        present = attendance_matrix[athlete_id]["present"]

        if total > 0:
            attendance_matrix[athlete_id]["percentage"] = round(
                (present / total) * 100,
                2
            )

    return render_template(
        "attendance.html",
        attendance_matrix=attendance_matrix,
        attendance_dates=attendance_dates
    )

@app.route("/attendance/add", methods=["GET", "POST"])
def add_attendance():

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        attendance_date = request.form["attendance_date"]
        status = request.form["status"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Attendance
            (
                Athlete_ID,
                Attendance_Date,
                Status
            )
            VALUES (%s, %s, %s)
        """, (
            athlete_id,
            attendance_date,
            status
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("attendance"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)

    athletes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_attendance.html",
        athletes=athletes
    )


@app.route("/attendance/edit/<int:attendance_id>", methods=["GET", "POST"])
def edit_attendance(attendance_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        attendance_date = request.form["attendance_date"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE Attendance
            SET Athlete_ID = %s,
                Attendance_Date = %s,
                Status = %s
            WHERE Attendance_ID = %s
        """, (
            athlete_id,
            attendance_date,
            status,
            attendance_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("attendance"))

    cursor.execute("""
        SELECT *
        FROM Attendance
        WHERE Attendance_ID = %s
    """, (attendance_id,))

    attendance_record = cursor.fetchone()

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)

    athletes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_attendance.html",
        attendance=attendance_record,
        athletes=athletes
    )


@app.route("/attendance/delete/<int:attendance_id>", methods=["POST"])
def delete_attendance(attendance_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Attendance
        WHERE Attendance_ID = %s
    """, (attendance_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("attendance"))


# =========================
# COMPETITION
# =========================

@app.route("/competitions")
def competitions():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.Competition_ID,
            c.Sport_ID,
            s.Sport_Name,
            c.Competition_Name,
            c.Competition_Date,
            c.Location
        FROM Competition c
        JOIN Sport s
            ON c.Sport_ID = s.Sport_ID
        ORDER BY c.Competition_ID
    """)

    competitions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "competitions.html",
        competitions=competitions
    )


@app.route("/competitions/add", methods=["GET", "POST"])
def add_competition():

    if request.method == "POST":

        sport_id = request.form["sport_id"]
        competition_name = request.form["competition_name"]
        competition_date = request.form["competition_date"]
        location = request.form["location"] or None

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Competition
            (
                Sport_ID,
                Competition_Name,
                Competition_Date,
                Location
            )
            VALUES (%s, %s, %s, %s)
        """, (
            sport_id,
            competition_name,
            competition_date,
            location
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("competitions"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Sport_ID, Sport_Name
        FROM Sport
        ORDER BY Sport_Name
    """)

    sports = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_competition.html",
        sports=sports
    )


@app.route("/competitions/edit/<int:competition_id>", methods=["GET", "POST"])
def edit_competition(competition_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        sport_id = request.form["sport_id"]
        competition_name = request.form["competition_name"]
        competition_date = request.form["competition_date"]
        location = request.form["location"] or None

        cursor.execute("""
            UPDATE Competition
            SET Sport_ID = %s,
                Competition_Name = %s,
                Competition_Date = %s,
                Location = %s
            WHERE Competition_ID = %s
        """, (
            sport_id,
            competition_name,
            competition_date,
            location,
            competition_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("competitions"))

    cursor.execute("""
        SELECT *
        FROM Competition
        WHERE Competition_ID = %s
    """, (competition_id,))

    competition = cursor.fetchone()

    cursor.execute("""
        SELECT Sport_ID, Sport_Name
        FROM Sport
        ORDER BY Sport_Name
    """)

    sports = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_competition.html",
        competition=competition,
        sports=sports
    )


@app.route("/competitions/delete/<int:competition_id>", methods=["POST"])
def delete_competition(competition_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Competition
        WHERE Competition_ID = %s
    """, (competition_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("competitions"))


# =========================
# PERFORMANCE
# =========================

@app.route("/performance")
def performance():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT p.Performance_ID, p.Athlete_ID, a.Name AS Athlete_Name, p.Competition_ID, c.Competition_Name,
               p.Score, p.Rank_Position, p.Medal, p.Performance_Date
        FROM Performance p JOIN Athlete a ON p.Athlete_ID=a.Athlete_ID
        JOIN Competition c ON p.Competition_ID=c.Competition_ID
    """
    params = ()
    if session.get("role") == "COACH":
        user = auth_record_for_session(); query += " WHERE a.Coach_ID = %s"; params = (user["Coach_ID"],)
    query += " ORDER BY p.Performance_ID"
    cursor.execute(query, params)

    performances = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "performance.html",
        performances=performances
    )


@app.route("/performance/add", methods=["GET", "POST"])
def add_performance():

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        competition_id = request.form["competition_id"]
        score = request.form["score"] or None
        rank_position = request.form["rank_position"] or None
        medal = request.form["medal"] or None
        performance_date = request.form["performance_date"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Performance
            (
                Athlete_ID,
                Competition_ID,
                Score,
                Rank_Position,
                Medal,
                Performance_Date
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            athlete_id,
            competition_id,
            score,
            rank_position,
            medal,
            performance_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("performance"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)
    athletes = cursor.fetchall()

    cursor.execute("""
        SELECT Competition_ID, Competition_Name
        FROM Competition
        ORDER BY Competition_Name
    """)
    competitions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_performance.html",
        athletes=athletes,
        competitions=competitions
    )


@app.route("/performance/edit/<int:performance_id>", methods=["GET", "POST"])
def edit_performance(performance_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        competition_id = request.form["competition_id"]
        score = request.form["score"] or None
        rank_position = request.form["rank_position"] or None
        medal = request.form["medal"] or None
        performance_date = request.form["performance_date"]

        cursor.execute("""
            UPDATE Performance
            SET Athlete_ID = %s,
                Competition_ID = %s,
                Score = %s,
                Rank_Position = %s,
                Medal = %s,
                Performance_Date = %s
            WHERE Performance_ID = %s
        """, (
            athlete_id,
            competition_id,
            score,
            rank_position,
            medal,
            performance_date,
            performance_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("performance"))

    cursor.execute("""
        SELECT *
        FROM Performance
        WHERE Performance_ID = %s
    """, (performance_id,))

    performance_record = cursor.fetchone()

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)
    athletes = cursor.fetchall()

    cursor.execute("""
        SELECT Competition_ID, Competition_Name
        FROM Competition
        ORDER BY Competition_Name
    """)
    competitions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_performance.html",
        performance=performance_record,
        athletes=athletes,
        competitions=competitions
    )


@app.route("/performance/delete/<int:performance_id>", methods=["POST"])
def delete_performance(performance_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Performance
        WHERE Performance_ID = %s
    """, (performance_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("performance"))


# =========================
# PROGRESS
# =========================

@app.route("/progress")
def progress():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.Progress_ID,
            p.Athlete_ID,
            a.Name AS Athlete_Name,
            p.Record_Date,
            p.Weight,
            p.BMI,
            p.Body_Fat_Percentage,
            p.Notes
        FROM Progress p
        JOIN Athlete a
            ON p.Athlete_ID = a.Athlete_ID
        ORDER BY p.Progress_ID
    """)

    progress_records = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "progress.html",
        progress_records=progress_records
    )


@app.route("/progress/add", methods=["GET", "POST"])
def add_progress():

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        record_date = request.form["record_date"]
        weight = request.form["weight"] or None
        bmi = request.form["bmi"] or None
        body_fat_percentage = request.form["body_fat_percentage"] or None
        notes = request.form["notes"] or None

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Progress
            (
                Athlete_ID,
                Record_Date,
                Weight,
                BMI,
                Body_Fat_Percentage,
                Notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            athlete_id,
            record_date,
            weight,
            bmi,
            body_fat_percentage,
            notes
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("progress"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)

    athletes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_progress.html",
        athletes=athletes
    )


@app.route("/progress/edit/<int:progress_id>", methods=["GET", "POST"])
def edit_progress(progress_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        athlete_id = request.form["athlete_id"]
        record_date = request.form["record_date"]
        weight = request.form["weight"] or None
        bmi = request.form["bmi"] or None
        body_fat_percentage = request.form["body_fat_percentage"] or None
        notes = request.form["notes"] or None

        cursor.execute("""
            UPDATE Progress
            SET Athlete_ID = %s,
                Record_Date = %s,
                Weight = %s,
                BMI = %s,
                Body_Fat_Percentage = %s,
                Notes = %s
            WHERE Progress_ID = %s
        """, (
            athlete_id,
            record_date,
            weight,
            bmi,
            body_fat_percentage,
            notes,
            progress_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("progress"))

    cursor.execute("""
        SELECT *
        FROM Progress
        WHERE Progress_ID = %s
    """, (progress_id,))

    progress_record = cursor.fetchone()

    cursor.execute("""
        SELECT Athlete_ID, Name
        FROM Athlete
        ORDER BY Name
    """)

    athletes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_progress.html",
        progress=progress_record,
        athletes=athletes
    )


@app.route("/progress/delete/<int:progress_id>", methods=["POST"])
def delete_progress(progress_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM Progress
        WHERE Progress_ID = %s
    """, (progress_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("progress"))

# =========================
# FOOD / EXERCISE GENERIC CRUD
# =========================

def table_metadata(table_name):
    if table_name not in {"Food", "Exercise"}:
        raise ValueError("Unsupported table")
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """, (os.getenv("DB_NAME", "athlete_management"), table_name))
    columns = cursor.fetchall()
    cursor.execute("""
        SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND CONSTRAINT_NAME='PRIMARY'
        ORDER BY ORDINAL_POSITION
    """, (os.getenv("DB_NAME", "athlete_management"), table_name))
    pk_row = cursor.fetchone()
    cursor.close(); connection.close()
    return columns, (pk_row["COLUMN_NAME"] if pk_row else (columns[0]["COLUMN_NAME"] if columns else None))


def generic_records(table_name):
    columns, pk = table_metadata(table_name)
    if not columns or not pk:
        return columns, pk, []
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM `{table_name}` ORDER BY `{pk}`")
    rows = cursor.fetchall(); cursor.close(); connection.close()
    return columns, pk, rows


def generic_save(table_name, record_id=None):
    columns, pk = table_metadata(table_name)
    editable = [c for c in columns if c["COLUMN_NAME"] != pk and "auto_increment" not in c["EXTRA"] and "GENERATED" not in c["EXTRA"].upper()]
    if request.method != "POST":
        return False
    connection = get_db_connection(); cursor = connection.cursor()
    try:
        values = []
        for col in editable:
            raw = request.form.get(col["COLUMN_NAME"], "")
            values.append(raw if raw != "" else None)
        names = [c["COLUMN_NAME"] for c in editable]
        if record_id is None:
            placeholders = ",".join(["%s"] * len(names))
            cursor.execute(f"INSERT INTO `{table_name}` ({','.join('`'+n+'`' for n in names)}) VALUES ({placeholders})", values)
        else:
            sets = ",".join(f"`{n}`=%s" for n in names)
            cursor.execute(f"UPDATE `{table_name}` SET {sets} WHERE `{pk}`=%s", values + [record_id])
        connection.commit(); flash(f"{table_name} record saved successfully.", "success"); return True
    except mysql.connector.Error as exc:
        connection.rollback(); flash(f"Database error: {exc}", "error"); return False
    finally:
        cursor.close(); connection.close()


@app.route("/food")
def food():
    columns, pk, rows = generic_records("Food")
    return render_template("generic_table.html", title="Food", columns=columns, pk=pk, rows=rows, add_endpoint="add_food", edit_endpoint="edit_food", delete_endpoint="delete_food")

@app.route("/food/add", methods=["GET", "POST"])
def add_food():
    columns, pk = table_metadata("Food")
    if generic_save("Food"): return redirect(url_for("food"))
    editable = [c for c in columns if c["COLUMN_NAME"] != pk and "auto_increment" not in c["EXTRA"]]
    return render_template("generic_form.html", title="Add Food", columns=editable, record=None, action=url_for("add_food"))

@app.route("/food/edit/<record_id>", methods=["GET", "POST"])
def edit_food(record_id):
    columns, pk = table_metadata("Food")
    if generic_save("Food", record_id): return redirect(url_for("food"))
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM `Food` WHERE `{pk}`=%s", (record_id,)); record = cursor.fetchone()
    cursor.close(); connection.close()
    editable = [c for c in columns if c["COLUMN_NAME"] != pk and "auto_increment" not in c["EXTRA"]]
    return render_template("generic_form.html", title="Edit Food", columns=editable, record=record, action=url_for("edit_food", record_id=record_id))

@app.route("/food/delete/<record_id>", methods=["POST"])
def delete_food(record_id):
    columns, pk = table_metadata("Food")
    connection = get_db_connection(); cursor = connection.cursor()
    try:
        cursor.execute(f"DELETE FROM `Food` WHERE `{pk}`=%s", (record_id,)); connection.commit(); flash("Food record deleted.", "success")
    except mysql.connector.Error as exc:
        connection.rollback(); flash(f"Cannot delete food record: {exc}", "error")
    finally:
        cursor.close(); connection.close()
    return redirect(url_for("food"))

@app.route("/exercises")
def exercises():
    columns, pk, rows = generic_records("Exercise")
    return render_template("generic_table.html", title="Exercises", columns=columns, pk=pk, rows=rows, add_endpoint="add_exercise", edit_endpoint="edit_exercise", delete_endpoint="delete_exercise")

@app.route("/exercises/add", methods=["GET", "POST"])
def add_exercise():
    columns, pk = table_metadata("Exercise")
    if generic_save("Exercise"): return redirect(url_for("exercises"))
    editable = [c for c in columns if c["COLUMN_NAME"] != pk and "auto_increment" not in c["EXTRA"]]
    return render_template("generic_form.html", title="Add Exercise", columns=editable, record=None, action=url_for("add_exercise"))

@app.route("/exercises/edit/<record_id>", methods=["GET", "POST"])
def edit_exercise(record_id):
    columns, pk = table_metadata("Exercise")
    if generic_save("Exercise", record_id): return redirect(url_for("exercises"))
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM `Exercise` WHERE `{pk}`=%s", (record_id,)); record = cursor.fetchone()
    cursor.close(); connection.close()
    editable = [c for c in columns if c["COLUMN_NAME"] != pk and "auto_increment" not in c["EXTRA"]]
    return render_template("generic_form.html", title="Edit Exercise", columns=editable, record=record, action=url_for("edit_exercise", record_id=record_id))

@app.route("/exercises/delete/<record_id>", methods=["POST"])
def delete_exercise(record_id):
    columns, pk = table_metadata("Exercise")
    connection = get_db_connection(); cursor = connection.cursor()
    try:
        cursor.execute(f"DELETE FROM `Exercise` WHERE `{pk}`=%s", (record_id,)); connection.commit(); flash("Exercise record deleted.", "success")
    except mysql.connector.Error as exc:
        connection.rollback(); flash(f"Cannot delete exercise record: {exc}", "error")
    finally:
        cursor.close(); connection.close()
    return redirect(url_for("exercises"))

if __name__ == "__main__":
    app.run(debug=True)