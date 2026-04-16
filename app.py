from flask import Flask,flash, jsonify, render_template, request, redirect, session
import sqlite3
from judge import run_code
from datetime import date, timedelta
from flask_toastr import Toastr
from functools import wraps

app = Flask(__name__)
app.secret_key = "pyquest_secret_key"
toastr=Toastr(app)
def db():
    conn = sqlite3.connect("database.db", timeout=20, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")  # ← Fix 2: WAL mode
    return conn

# Home Page
@app.route("/")
def home():
    # upgrade_db()
   # seed_badges()
    return render_template("Index.html")

# REGISTER
@app.route("/register", methods=["POST","GET"])
def register():
    if request.method == "GET":
        return render_template("register.html",error="")
    
    fullname = request.form["fullname"]
    email = request.form["email"]
    password = request.form["password"]
    role = request.form["role"]

    conn = db()
    c = conn.cursor()

    try:
        c.execute("SELECT * FROM users WHERE email=? or fullname=?", (email.lower(), fullname.lower()))
        if c.fetchone():
            flash("Email or username already exists", "error")
            return render_template("Register.html", error="Email or username already exists")

        c.execute(
            "INSERT INTO users(fullname,email,password,role) VALUES(?,?,?,?)",
            (fullname.lower(),email.lower(),password,role)
        )

        conn.commit()
        flash("User registered successfully!", "success")
    except:
        return render_template("Register.html", error="Email exists")

    conn.close()

    return redirect("/login")
@app.route('/check-email')
def check_email():
    email = request.args.get('email')
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email.lower(),))
    
    if c.fetchone():
        conn.close()
        return jsonify({"exists": True})
    conn.close()
    return jsonify({"exists": False})
# Login
@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "GET":
        return render_template("Login.html",error="")

    email = request.form["email"]
    password = request.form["password"]

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE (email=? OR fullname=?)" " AND password=?", (email.lower(), email.lower(), password))
    user = c.fetchone()
    conn.close()

    if user:
        session["user"] = user[1]
        session["role"] = user[4]
        session["user_id"] = user[0]
        if user[4] == "admin":
            return redirect("/admin")

        elif user[4] == "teacher":
            return redirect("/teacher")
        else:
            # flash('You were successfully logged in', 'success')
            return redirect("/dashboard")
    else:
        flash("Invalid email or password", "error")
        return render_template("Login.html", error="Invalid Email or Password")
# Decorator to protect routes
# def login_required(f):
#     @wraps(f)
#     def wrapper(*args, **kwargs):
#         if "user" not in session:
#             return redirect("/login")
#         return f(*args, **kwargs)
#     return wrapper
# Decorator for role-based access
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Not logged in
            if "user" not in session:
                return redirect("/login")

            # Role check
            user_role = session.get("role")

            if user_role not in roles:
                # return "Unauthorized", 403  # or redirect("/")
                return redirect("/login")
            return f(*args, **kwargs)
        return wrapper
    return decorator
# Logout
@app.route("/logout")
def logout():
    # session.pop("user", None)
    session.clear()  # Clear entire session
    return redirect("/login")

# Dashboard
@app.route("/dashboard")
@role_required("student")
def dashboard():

    conn = db()
    c = conn.cursor()
    # Get user stats
    c.execute("""
    SELECT xp, level, current_streak, longest_streak 
    FROM users WHERE id=?
    """, (session["user_id"],))

    xp, level, streak, longest = c.fetchone()

    xp_needed = level * 100
    current_level_xp = xp % 100

    progress = int((current_level_xp / 100) * 100)
   # Get badges
    # c.execute("""
    # SELECT b.name FROM user_badges ub
    # JOIN badges b ON ub.badge_id = b.id
    # WHERE ub.user_id=?
    # """, (session["user_id"],))

    # badges = [row[0] for row in c.fetchall()]
    c.execute("""
    SELECT b.name,
        CASE WHEN ub.user_id IS NOT NULL THEN 1 ELSE 0 END as unlocked
    FROM badges b
    LEFT JOIN user_badges ub
    ON b.id = ub.badge_id AND ub.user_id=?
    """, (session["user_id"],))

    badges = c.fetchall()
    # 🎯 DAILY CHALLENGE
    today = date.today()

    c.execute("""
        SELECT dc.id, dc.title, dc.problem_id 
        FROM daily_challenges dc
        WHERE dc.date=?
    """, (today,))
    challenge = c.fetchone()

    completed = False

    if challenge:
        challenge_id = challenge[0]

        c.execute("""
            SELECT completed FROM user_daily_status
            WHERE user_id=? AND challenge_id=?
        """, (session["user_id"], challenge_id))

        result = c.fetchone()
        completed = result and result[0] == 1

    conn.close()

    if "user" in session:
        
        return render_template("dashboard.html",
                                name=session["user"],
                                xp=xp,
                                level=level,
                                streak=streak,
                                longest=longest,
                                badges=badges,
                                progress=progress,
                                current_level_xp=current_level_xp,
                                challenge=challenge,
                                completed=completed
                                )
    return redirect("/")

# Admin Dashboard
@app.route("/admin")
@role_required("admin")
def admin():
    admin_name = session["user"].capitalize()
    return render_template("admin.html", name=admin_name)
    # if "user" in session and session["role"].lower() == "admin":
    #     return render_template("admin.html", name=admin_name)
    # return redirect("/")
# Admin Users View
@app.route("/admin/users")
@role_required("admin")
def admin_users():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT id,fullname,role FROM users")
    users = c.fetchall()

    conn.close()

    return render_template("admin_users.html", users=users)
# Admin Update UserRole
@app.route("/admin/update_role/<int:uid>", methods=["POST"])
@role_required("admin")
def update_role(uid):
    new_role = request.form["role"]

    conn = db()
    c = conn.cursor()

    c.execute(
    "UPDATE users SET role=? WHERE id=?",
    (new_role, uid)
    )

    conn.commit()
    conn.close()
    flash("User role updated successfully!", "success")
    return redirect("/admin/users")
# Admin Delete User
@app.route("/admin/delete_user/<int:uid>")
@role_required("admin")
def delete_user(uid):
    conn = db()
    c = conn.cursor()

    c.execute(
    "DELETE FROM users WHERE id=?",
    (uid,)
    )

    conn.commit()
    conn.close()
    flash("User deleted successfully!", "success")
    return redirect("/admin/users")

# Admin Daily Challenge Management
@app.route("/admin/daily_challenge", methods=["GET", "POST"])
@role_required("admin")
def admin_daily_challenge():
    conn = db()
    c = conn.cursor()

    if request.method == "POST":
        problem_id = request.form["problem_id"]
        title = request.form["title"]

        # Remove existing challenge for today
        c.execute("DELETE FROM daily_challenges WHERE date = DATE('now','localtime')")

        # Insert new one
        c.execute("""
            INSERT INTO daily_challenges (title, problem_id, date)
            VALUES (?, ?, DATE('now','localtime'))
        """, (title, problem_id))
        flash('Daily challenge updated successfully!', 'success')
        conn.commit()

    # Fetch problems for dropdown
    c.execute("SELECT id, title FROM problems")
    problems = c.fetchall()

    # Get today's challenge
    c.execute("""
        SELECT title, problem_id FROM daily_challenges 
        WHERE date = DATE('now','localtime')
    """)
    today_challenge = c.fetchone()

    conn.close()
    
    return render_template("admin_challenge.html",
        problems=problems,
        today_challenge=today_challenge
    )
# Teacher Dashboard
@app.route("/teacher")
@role_required("teacher")
def teacher():
    return render_template("teacher.html", name=session["user"])
    
# Teacher Problems View
@app.route("/teacher/problems")
@role_required("teacher")
def teacher_problems():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM problems WHERE teacher_id=?", (session["user"],))
    problems = c.fetchall()

    conn.close()

    return render_template("teacher_problems.html", problems=problems)

# TeacherAdd Problem
@app.route("/add_problem", methods=["POST"])
@role_required("teacher")
def add_problem():

    title = request.form["title"]
    desc = request.form["description"]
    level = request.form["level"]
    inputs = request.form.getlist("input[]")
    outputs = request.form.getlist("output[]")

    conn = db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO problems(title,description,level,teacher_id) VALUES(?,?,?,?)",
        (title,desc,level,session["user_id"])
    )

    pid = c.lastrowid

    for inp, out in zip(inputs, outputs):
        if inp.strip() and out.strip():
            c.execute(
                "INSERT INTO testcases(problem_id,input,expected_output) VALUES(?,?,?)",
                (pid, inp.strip(), out.strip())
            )


    conn.commit()
    conn.close()
    flash("Problem added successfully!", "success")
    return redirect("/manage_problems")
# Teacher Manage Problems
@app.route("/manage_problems")
@role_required("teacher")
def manage_problems():
    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM problems WHERE teacher_id=?", (session["user_id"],))
    problems = c.fetchall()

    conn.close()

    return render_template("manage_problem.html", problems=problems)
@app.route("/teacher/testcases/<int:pid>", methods=["GET"])
@role_required("teacher")
def get_testcase(pid):
    conn = db()
    c = conn.cursor()
    if request.args.get('format') == 'json':
        tcs = c.execute("SELECT input, expected_output FROM testcases WHERE problem_id=?", (pid,)).fetchall()
        conn.close()
        return jsonify({"testcases": [{"input": t[0], "output": t[1]} for t in tcs]})
    return render_template('manage_problem.html', ...)
    # c.execute(
    #     "SELECT input, expected_output FROM testcases WHERE problem_id=?",
    #     (pid,)
    # )
    # test = c.fetchone()
    
    #return jsonify(test)
# Teacher Save Testcases
@app.route('/teacher/testcases/<int:problem_id>', methods=['POST'])
def save_testcases(problem_id):
    conn = db()
    c = conn.cursor()
    data = request.get_json()
    testcases = data.get('testcases', [])
    c.execute("DELETE FROM testcases WHERE problem_id=?", (problem_id,))
    for tc in testcases:
        c.execute("INSERT INTO testcases (problem_id, input, expected_output) VALUES (?,?,?)",
                   (problem_id, tc['input'], tc['output']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# Teacher View/Edit Problem
@app.route("/teacher/edit_problem/<int:pid>", methods=["POST"])
@role_required("teacher")
def edit_problem(pid):

    title = request.form["title"]
    desc = request.form["description"]
    level = request.form["level"]
    inp = request.form["input"]
    out = request.form["output"]

    conn = db()
    c = conn.cursor()

    c.execute(
        "UPDATE problems SET title=?, description=?, level=? WHERE id=?",
        (title,desc,level,pid)
    )

    c.execute(
        "UPDATE testcases SET input=?, expected_output=? WHERE problem_id=?",
        (inp,out,pid)
    )

    conn.commit()
    conn.close()

    return redirect("/manage_problems")
# Teacher Edit Problem
@app.route("/teacher/update_problem/<int:id>", methods=["POST"])
@role_required("teacher")
def update_problem(id):

    if session.get("role") != "teacher":
        return redirect("/login")

    title = request.form["title"]
    description = request.form["description"]
    level = request.form["difficulty"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    UPDATE problems
    SET title=?, description=?, level=?
    WHERE id=? AND teacher_id=?
    """, (title, description, level, id, session["user_id"]))

    conn.commit()
    flash("Problem updated successfully!", "success")
    conn.close()

    return redirect("/manage_problems")
# Teacher Delete Problem
@app.route("/teacher/delete_problem/<int:id>")
@role_required("teacher")
def delete_problem(id):

    if session.get("role") != "teacher":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    DELETE FROM problems
    WHERE id=? AND teacher_id=?
    """, (id, session["user_id"]))

    conn.commit()
    flash("Problem deleted successfully!", "success")
    conn.close()

    return redirect("/manage_problems")
# PROBLEMS BY LEVEL
@app.route("/problems/<level>")
def problems(level):

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM problems WHERE level=?", (level,))
    problems = c.fetchall()

    conn.close()

    return render_template("problems.html", problems=problems, level=level)


# SINGLE PROBLEM
@app.route("/problem/<int:pid>")
def problem(pid):

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM problems WHERE id=?", (pid,))
    problem = c.fetchone()
    
    # get example test case
    c.execute(
        "SELECT input, expected_output FROM testcases WHERE problem_id=? LIMIT 1",
        (pid,)
    )

    example = c.fetchone()

    conn.close()

    return render_template("problem.html", problem=problem, example=example)


# ── submit route: ONE connection for the entire request ──

@app.route("/submit/<int:pid>", methods=["POST"])
@role_required("student")
def submit(pid):

    code = request.form["code"]

    conn = db()                          # ← single connection
    c = conn.cursor()

    try:
        c.execute("SELECT input, expected_output FROM testcases WHERE problem_id=?", (pid,))
        tests = c.fetchall()
        c.execute("SELECT level FROM problems WHERE id=?", (pid,))
        level = c.fetchone()[0]

        point = {0: 10, 1: 20, 2: 30}.get(level, 0)

        # passed = sum(
        #     1 for inp, expected in tests
        #     if run_code(code, inp) == expected
        # )
        results = []
        for inp, expected in tests:
            output = run_code(code, inp)
            passed_tc = output.strip() == expected.strip()
            results.append({
                "input": inp,
                "expected": expected,
                "output": output,
                "passed": passed_tc,
            })
 
        all_passed = all(r["passed"] for r in results)


        if all_passed:
            result = "Correct"
            c.execute("UPDATE users SET points = points + ? WHERE id=?", (point, session["user_id"]))
            on_successful_submission(session["user_id"], pid, c)  # ← passes cursor
            flash('Submission successful!', 'success')
        else:
            result = "Wrong"

        c.execute(
            "INSERT INTO submissions(user, problem_id, code, result) VALUES(?,?,?,?)",
            (session["user_id"], pid, code, result)
        )
        conn.commit()                    # ← single commit at the end
    finally:
        conn.close()                     # ← always closes even on error
   
   
    return jsonify(results)
    # return render_template("result.html", result=result)


# Run Code
@app.route("/run", methods=["POST"])
@role_required("student")
def run():
    # print(request.form["code"])
    data = request.get_json()
    code = data["code"]
    input_data = data.get("input","")
    from judge import run_code

    output = run_code(code, input_data)

    return {"output": output}

@app.route("/teacher/analytics")
def teacher_analytics():

    teacher_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    SELECT 
        problems.title,
        COUNT(DISTINCT submissions.user) as attempts,
        SUM(CASE WHEN submissions.result='Correct' THEN 1 ELSE 0 END) as success
    FROM problems
    LEFT JOIN submissions ON problems.id = submissions.problem_id
    WHERE problems.teacher_id=?
    GROUP BY problems.id
    """, (teacher_id,))

    data = c.fetchall()
    conn.close()

    return render_template("teacher_analytics.html", data=data)

# Leaderboard
@app.route("/leaderboard")
@role_required("student","admin")
def leaderboard():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT fullname, points,level FROM users where role='student' ORDER BY points DESC")
    users = c.fetchall()

    conn.close()

    return render_template("leaderboard.html", users=users)
# Student Progress Page
@app.route("/progress")
def progress():

    if "user" not in session:
        return redirect("/")

    conn = db()
    c = conn.cursor()

    # total submissions
    c.execute(
        "SELECT COUNT(*) FROM submissions WHERE user=?",
        (session["user"],)
    )
    total_submissions = c.fetchone()[0]

    # solved problems
    c.execute(
        "SELECT COUNT(DISTINCT problem_id) FROM submissions WHERE user=? AND result='Correct'",
        (session["user"],)
    )
    solved = c.fetchone()[0]

    # total problems
    c.execute("SELECT COUNT(*) FROM problems")
    total_problems = c.fetchone()[0]

    success_rate = 0
    if total_submissions > 0:
        success_rate = round((solved / total_submissions) * 100, 2)

    # solved list
    c.execute("""
        SELECT problems.title
        FROM submissions
        JOIN problems ON submissions.problem_id = problems.id
        WHERE submissions.user=? AND submissions.result='Correct'
        GROUP BY problems.title
    """, (session["user"],))

    solved_list = c.fetchall()

    conn.close()

    return render_template(
        "progress.html",
        solved=solved,
        total_problems=total_problems,
        total_submissions=total_submissions,
        success_rate=success_rate,
        solved_list=solved_list
    )


#Streak System
def update_streak(user_id,c):
    

    c.execute("SELECT last_active, current_streak, longest_streak FROM users WHERE id=?", (user_id,))
    last_active, current, longest = c.fetchone()

    today = date.today()

    if last_active:
        last_active = date.fromisoformat(last_active)

    if last_active == today:
        return

    if last_active == today - timedelta(days=1):
        current += 1
    else:
        current = 1

    longest = max(longest, current)

    c.execute("""
        UPDATE users 
        SET last_active=?, current_streak=?, longest_streak=? 
        WHERE id=?
    """, (today, current, longest, user_id))

   
# XP System
def add_xp(user_id, amount,c):
   
    c.execute("SELECT xp FROM users WHERE id=?", (user_id,))
    xp = c.fetchone()[0]

    xp += amount
    level = xp // 100 + 1

    c.execute("UPDATE users SET xp=?, level=? WHERE id=?", (xp, level, user_id))

    
# Badge System
BADGES = [
    ("First Solve", "Solve your first problem"),
    ("5 Day Streak", "Maintain a 5 day streak"),
    ("XP 100", "Earn 100 XP"),
]
# Seed badges into database
def seed_badges():
    conn = db()
    c = conn.cursor()

    for name, desc in BADGES:
        c.execute("INSERT OR IGNORE INTO badges (name, description) VALUES (?, ?)", (name, desc))

    conn.commit()
    conn.close()
# Badge Checker
def check_badges(user_id, c):
    

    c.execute("""
        SELECT problems_solved, current_streak, xp 
        FROM users WHERE id=?
    """, (user_id,))
    
    solved, streak, xp = c.fetchone()

    rules = [
        ("First Solve", solved >= 1),
        ("5 Day Streak", streak >= 5),
        ("XP 100", xp >= 100),
    ]

    for name, condition in rules:
        if condition:
            c.execute("SELECT id FROM badges WHERE name=?", (name,))
            badge_id = c.fetchone()[0]

            c.execute("""
                INSERT OR IGNORE INTO user_badges(user_id, badge_id, earned_at)
                VALUES (?, ?, DATE('now'))
            """, (user_id, badge_id))

   
# Daily Challenge System
def check_daily_challenge(user_id, problem_id, c):
    today = date.today()

    c.execute("""
        SELECT id FROM daily_challenges 
        WHERE date=? AND problem_id=?
    """, (today, problem_id))

    challenge = c.fetchone()

    if challenge:
        challenge_id = challenge[0]

        c.execute("""
            INSERT OR REPLACE INTO user_daily_status 
            (user_id, challenge_id, completed)
            VALUES (?, ?, 1)
        """, (user_id, challenge_id))

        add_xp(user_id, 20,c)

   
# On successful submission, update stats and check gamification rewards 
def on_successful_submission(user_id, problem_id,c):
   

    # Increase solved count
    c.execute("""
        UPDATE users 
        SET problems_solved = problems_solved + 1 
        WHERE id=?
    """, (user_id,))
    

    # Gamification pipeline
    update_streak(user_id,c)
    add_xp(user_id, 10,c)
    check_daily_challenge(user_id, problem_id,c)
    check_badges(user_id,c)
# Start Challenge
@app.route("/start")
def start():
    from datetime import date

    user_id = session["user_id"]
    conn = db()
    c = conn.cursor()

    today = date.today()

    # # 1. Try daily challenge
    # c.execute("""
    #     SELECT problem_id FROM daily_challenges WHERE date=?
    # """, (today,))
    # challenge = c.fetchone()

    # if challenge:
    #     conn.close()
    #     return redirect(f"/problem/{challenge[0]}")

    # 2. Smart fallback
    c.execute("SELECT level FROM users WHERE id=?", (user_id,))
    level = c.fetchone()[0]

    if level <= 3:       # User level determines problem difficulty
        difficulty = 0   #"easy" this was originally 1 but we have 0,1,2 as levels
    elif level <= 6:
        difficulty = 1   #"medium"
    else:
        difficulty = 2   #"hard"

    # 3. Avoid solved problems
    c.execute("""
        SELECT id FROM problems 
        WHERE level=? AND id NOT IN (
            SELECT problem_id FROM submissions WHERE user=? AND result='Correct'
        )
        ORDER BY RANDOM() LIMIT 1
    """, (difficulty, user_id))

    problem = c.fetchone()
    conn.close()

    if problem:
        return redirect(f"/problem/{problem[0]}")
    else:
        flash("You're out of problems in this level!", "info")
        return redirect("/dashboard")

if __name__ == "__main__":
    app.run(debug=True)