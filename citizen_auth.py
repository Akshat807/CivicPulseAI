
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    create_citizen,
    get_citizen_by_email,
    get_complaints_by_user,
)

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")


def citizen_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if (
            session.get("user_role") != "citizen"
            or not session.get("user_id")
        ):
            flash("Please log in with your citizen account.", "error")
            return redirect(url_for("citizen.login"))

        return view_function(*args, **kwargs)

    return wrapped_view


@citizen_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_role") == "citizen":
        return redirect(url_for("citizen.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("Please fill in all required fields.", "error")
            return render_template("signup.html")

        if len(name) > 100 or len(email) > 254:
            flash("Name or email is too long.", "error")
            return render_template("signup.html")

        if (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
        ):
            flash("Please enter a valid email address.", "error")
            return render_template("signup.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        password_hash = generate_password_hash(password)

        try:
            create_citizen(name, email, password_hash)
        except Exception as error:
            # A UNIQUE constraint violation means the email is already used.
            import sqlite3

            if isinstance(error, sqlite3.IntegrityError):
                flash(
                    "An account with this email already exists.",
                    "error",
                )
                return render_template("signup.html")

            raise

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("citizen.login"))

    return render_template("signup.html")


@citizen_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_role") == "citizen":
        return redirect(url_for("citizen.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_citizen_by_email(email)

        if (
            user is None
            or not check_password_hash(user["password_hash"], password)
        ):
            flash("Invalid email or password.", "error")
            return render_template("citizen_login.html")

        # Clear only the previous citizen session values.
        # Do not clear the admin session or other unrelated session data.
        session.pop("user_id", None)
        session.pop("user_name", None)
        session.pop("user_role", None)

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = "citizen"

        flash("Welcome back!", "success")
        return redirect(url_for("citizen.dashboard"))

    return render_template("citizen_login.html")


@citizen_bp.route("/logout", methods=["POST"])
def logout():
    if session.get("user_role") == "citizen":
        session.pop("user_id", None)
        session.pop("user_name", None)
        session.pop("user_role", None)
        flash("You have been logged out.", "success")

    return redirect(url_for("home"))


@citizen_bp.route("/dashboard")
@citizen_required
def dashboard():
    user_id = session["user_id"]
    complaints = get_complaints_by_user(user_id)

    total = len(complaints)
    resolved = sum(
        1 for item in complaints
        if item["status"] == "Resolved"
    )
    pending = total - resolved

    return render_template(
        "citizen_dashboard.html",
        complaints=complaints,
        total=total,
        resolved=resolved,
        pending=pending,
        user_name=session.get("user_name", "Citizen"),
    )
