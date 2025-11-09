import sqlite3
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, g, jsonify, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from datetime import datetime

# --- config ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "replace-this-with-a-secure-random-secret"  # change for production
DB_PATH = Path("instance") / "bmi.db"
DB_PATH.parent.mkdir(exist_ok=True)

# --- DB helpers ---
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        g._database = db
    return db

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bmi_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        weight REAL NOT NULL,
        height_cm REAL NOT NULL,
        bmi REAL NOT NULL,
        category TEXT NOT NULL,
        note TEXT,
        recorded_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# --- simple auth helpers ---
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    user = db.execute("SELECT id, username, created_at FROM users WHERE id = ?", (uid,)).fetchone()
    return user

# --- routes ---
@app.before_request
def before_request():
    init_db()  # ensure tables exist on each request (cheap)

@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Please provide username and password", "error")
            return redirect(url_for("register"))
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.utcnow().isoformat())
            )
            db.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.", "error")
            return redirect(url_for("register"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    db = get_db()
    rows = db.execute(
        "SELECT id, weight, height_cm, bmi, category, note, recorded_at FROM bmi_records WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 100",
        (user["id"],)
    ).fetchall()
    history = [dict(r) for r in rows]
    return render_template("dashboard.html", user=user, history=history)

# API: save BMI
@app.route("/api/save_bmi", methods=["POST"])
def save_bmi():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Not authenticated"}), 401

    data = request.get_json() or {}
    try:
        weight = float(data.get("weight"))
        height_cm = float(data.get("height_cm"))
        bmi = float(data.get("bmi"))
        category = data.get("category", "")
        note = data.get("note", None)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid payload"}), 400

    now = datetime.utcnow().isoformat()
    db = get_db()
    db.execute(
        "INSERT INTO bmi_records (user_id, weight, height_cm, bmi, category, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user["id"], weight, height_cm, bmi, category, note, now)
    )
    db.commit()
    return jsonify({"ok": True})

# API: quick server-side BMI check (optional)
@app.route("/api/check_bmi", methods=["POST"])
def check_bmi():
    payload = request.get_json() or {}
    try:
        w = float(payload.get("weight"))
        hcm = float(payload.get("height_cm"))
        if w <= 0 or hcm <= 0:
            raise ValueError
    except Exception:
        return jsonify({"ok": False, "error": "Invalid inputs"}), 400
    h = hcm / 100.0
    bmi = w / (h * h)
    rounded = round(bmi, 1)
    # determine category
    if rounded < 18.5:
        cat = "Underweight"
    elif rounded < 25:
        cat = "Healthy"
    elif rounded < 30:
        cat = "Overweight"
    else:
        cat = "Obese"
    return jsonify({"ok": True, "bmi": rounded, "category": cat})

# run
if __name__ == "__main__":
    app.run(debug=True)
