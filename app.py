
from pathlib import Path
from functools import wraps
import os

import joblib
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.security import check_password_hash

from database import (
    initialize_database,
    save_complaint,
    get_complaints,
    get_total_complaints,
    get_status_counts,
    get_category_counts,
    update_complaint_status,
    get_complaint_by_id,
    get_admin_by_username,
)

# ----------------------------------
# APPLICATION CONFIGURATION
# ----------------------------------

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "civicpulse_model.pkl"

app = Flask(__name__)

# For local development, configure a secret key in your environment.
# Never deploy with a publicly known or hardcoded secret key.
app.secret_key = os.environ.get("CIVICPULSE_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "CIVICPULSE_SECRET_KEY is not set. "
        "Set it in your terminal before starting the app."
    )

# ----------------------------------
# LOAD AI MODEL AND DATABASE
# ----------------------------------

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        "Model not found. Run train_model.py first."
    )

model = joblib.load(MODEL_PATH)
initialize_database()

# ----------------------------------
# ADMIN LOGIN PROTECTION
# ----------------------------------

def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "admin_username" not in session:
            flash(
                "Please log in to access the admin dashboard.",
                "error",
            )
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# ----------------------------------
# ADMIN LOGIN
# ----------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "admin_username" in session:
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin_account = get_admin_by_username(username)

        if (
            admin_account
            and check_password_hash(
                admin_account["password_hash"],
                password,
            )
        ):
            session.clear()
            session["admin_username"] = admin_account["username"]

            flash("Login successful!", "success")
            return redirect(url_for("admin"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


# ----------------------------------
# ADMIN LOGOUT
# ----------------------------------

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ----------------------------------
# HOME PAGE
# ----------------------------------

@app.route("/", methods=["GET", "POST"])
def home():
    message = None
    error = None
    complaint_id = None
    predicted_category = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        complaint = request.form.get("complaint", "").strip()

        if not city or not complaint:
            error = "Please enter both your city and complaint."

        elif len(city) > 100 or len(complaint) > 2000:
            error = "City or complaint is too long."

        else:
            predicted_category = model.predict([complaint])[0]

            complaint_id = save_complaint(
                city,
                complaint,
                predicted_category,
            )

            message = "Your complaint has been saved successfully!"

    records = get_complaints(limit=10)

    return render_template(
        "index.html",
        message=message,
        error=error,
        complaint_id=complaint_id,
        predicted_category=predicted_category,
        records=records,
    )


# ----------------------------------
# COMPLAINT TRACKING
# ----------------------------------

@app.route("/track", methods=["GET", "POST"])
def track_complaint():
    complaint = None
    error = None
    entered_id = ""

    if request.method == "POST":
        entered_id = request.form.get(
            "complaint_id", ""
        ).strip()

        if not entered_id.isdigit() or int(entered_id) <= 0:
            error = "Please enter a valid complaint ID."
        else:
            complaint = get_complaint_by_id(int(entered_id))

            if complaint is None:
                error = "Complaint not found. Please check your ID."

    return render_template(
        "track.html",
        complaint=complaint,
        error=error,
        entered_id=entered_id,
    )


# ----------------------------------
# ADMIN DASHBOARD - PROTECTED
# ----------------------------------

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        complaint_id = request.form.get(
            "complaint_id", type=int
        )
        status = request.form.get("status", "")

        if complaint_id is None:
            flash("Invalid complaint ID.", "error")
        else:
            updated = update_complaint_status(
                complaint_id,
                status,
            )

            if updated:
                flash(
                    "Complaint status updated successfully!",
                    "success",
                )
            else:
                flash(
                    "Could not update complaint status.",
                    "error",
                )

        return redirect(url_for("admin"))

    total_complaints = get_total_complaints()
    status_counts = get_status_counts()
    category_counts = get_category_counts()
    recent_complaints = get_complaints(limit=10)

    submitted_count = status_counts.get("Submitted", 0)
    in_progress_count = status_counts.get("In Progress", 0)
    resolved_count = status_counts.get("Resolved", 0)

    return render_template(
        "admin.html",
        total_complaints=total_complaints,
        submitted_count=submitted_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        category_counts=category_counts,
        recent_complaints=recent_complaints,
    )


# ----------------------------------
# RUN APPLICATION
# ----------------------------------

if __name__ == "__main__":
    app.run(debug=True)
