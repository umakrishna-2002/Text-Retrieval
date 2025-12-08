from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid
import hashlib

app = Flask(__name__)
app.secret_key = "super-secret-key"  # move to .env later

# TEMP USER STORE (for learning/demo)
USERS = {}
# structure:
# USERS[email] = {
#   "user_id": "...",
#   "password_hash": "..."
# }

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email in USERS:
            flash("User already exists", "error")
            return redirect(url_for("signup"))

        user_id = str(uuid.uuid4())
        USERS[email] = {
            "user_id": user_id,
            "password_hash": hash_password(password)
        }

        session["user_id"] = user_id
        session["email"] = email

        flash("Signup successful!", "success")
        return redirect(url_for("index"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = USERS.get(email)
        if not user or user["password_hash"] != hash_password(password):
            flash("Invalid credentials", "error")
            return redirect(url_for("login"))

        session["user_id"] = user["user_id"]
        session["email"] = email
        flash("Login successful!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))
