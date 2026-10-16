
from pathlib import Path
from functools import wraps

import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import joblib

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from database import (
    initialize_database,
    initialize_admin_table,
    create_admin,
    get_admin_by_username,
    get_connection,
    save_complaint,
    get_complaints,
    get_filtered_complaints,
    get_total_complaints,
    get_status_counts,
    get_category_counts,
    get_priority_counts,
    get_daily_complaint_counts,
    get_resolution_analytics,
    update_complaint_status,
    get_complaint_by_id,
    validate_coordinates,
    get_map_complaints,
)

from citizen_auth import citizen_bp
from priority_detector import detect_priority_details
from insights_engine import generate_insights


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "civicpulse_model.pkl"


app = Flask(__name__)
app.register_blueprint(citizen_bp)

app.secret_key = os.environ.get("CIVICPULSE_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "CIVICPULSE_SECRET_KEY is not set. "
        "Set it in your environment variables."
    )


if not MODEL_PATH.exists():
    raise FileNotFoundError(
        "Model not found. Run train_model.py first."
    )

model = joblib.load(MODEL_PATH)


# Initialize the existing database without deleting its data.
initialize_database()

# Initialize the admin table.
initialize_admin_table()


# Render admin account bootstrap.
# Credentials are read from environment variables.
admin_username = os.environ.get(
    "CIVICPULSE_ADMIN_USERNAME", ""
).strip()

admin_password = os.environ.get(
    "CIVICPULSE_ADMIN_PASSWORD", ""
)
app.logger.info(
    "Admin bootstrap diagnostic: username_present=%s, "
    "password_present=%s, password_length_ok=%s",
    bool(admin_username),
    bool(admin_password),
    len(admin_password) >= 16,
)
if admin_username and admin_password:
    if len(admin_password) < 16:
        app.logger.warning(
            "Admin bootstrap skipped: password must be "
            "at least 16 characters long."
        )
    else:
        admin_account = get_admin_by_username(admin_username)

        password_hash = generate_password_hash(
            admin_password
        )

        if admin_account:
            with get_connection() as connection:
                connection.execute(
                    """
                    UPDATE admins
                    SET password_hash = ?
                    WHERE username = ?
                    """,
                    (password_hash, admin_username),
                )

            app.logger.info(
                "Configured admin password updated."
            )
        else:
            create_admin(
                admin_username,
                password_hash,
            )

            app.logger.info(
                "Configured admin account created."
            )


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


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def home():
    message = None
    error = None
    complaint_id = None
    predicted_category = None
    predicted_priority = None
    priority_score = None
    priority_reason = None

    if request.method == "POST":
        if (
            session.get("user_role") != "citizen"
            or not session.get("user_id")
        ):
            flash(
                "Please log in or create a citizen account "
                "before submitting a complaint.",
                "error",
            )
            return redirect(url_for("citizen.login"))

        city = request.form.get("city", "").strip()
        complaint_text = request.form.get(
            "complaint", ""
        ).strip()

        latitude, longitude = validate_coordinates(
            request.form.get("latitude"),
            request.form.get("longitude"),
        )

        location_address = request.form.get(
            "location_address", ""
        ).strip()[:300]

        if not city or not complaint_text:
            error = "Please enter both your city and complaint."

        elif len(city) > 100 or len(complaint_text) > 2000:
            error = "City or complaint is too long."

        elif (
            request.form.get("latitude", "").strip()
            and latitude is None
        ) or (
            request.form.get("longitude", "").strip()
            and longitude is None
        ):
            error = (
                "The GPS coordinates are invalid. "
                "Please select your location again or submit "
                "without GPS coordinates."
            )

        else:
            predicted_category = str(
                model.predict([complaint_text])[0]
            )

            details = detect_priority_details(
                complaint_text,
                predicted_category,
            )

            predicted_priority = details.get(
                "priority", "Medium"
            )
            priority_score = details.get("score", 40)
            priority_reason = details.get(
                "reason",
                "Priority details unavailable.",
            )

            complaint_id = save_complaint(
                city,
                complaint_text,
                predicted_category,
                user_id=session["user_id"],
                priority=predicted_priority,
                priority_score=priority_score,
                priority_reason=priority_reason,
                latitude=latitude,
                longitude=longitude,
                location_address=location_address,
            )

            message = (
                "Your complaint has been saved successfully!"
            )

    records = get_complaints(limit=10)

    return render_template(
        "index.html",
        message=message,
        error=error,
        complaint_id=complaint_id,
        predicted_category=predicted_category,
        predicted_priority=predicted_priority,
        predicted_priority_score=priority_score,
        predicted_priority_reason=priority_reason,
        records=records,
    )


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
                error = (
                    "Complaint not found. Please check your ID."
                )

    return render_template(
        "track.html",
        complaint=complaint,
        error=error,
        entered_id=entered_id,
    )


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        complaint_id = request.form.get(
            "complaint_id", type=int
        )
        status = request.form.get("status", "")

        search = request.form.get("search", "").strip()
        selected_status = request.form.get(
            "filter_status", ""
        )
        category = request.form.get("filter_category", "")
        selected_priority = request.form.get(
            "filter_priority", ""
        )
        page = request.form.get(
            "page", 1, type=int
        ) or 1

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

        return redirect(
            url_for(
                "admin",
                search=search,
                status=selected_status,
                category=category,
                priority=selected_priority,
                page=page,
            )
        )

    # Read dashboard filters.
    search = request.args.get("search", "").strip()
    selected_status = request.args.get("status", "")
    category = request.args.get("category", "")
    selected_priority = request.args.get("priority", "")
    page = request.args.get("page", 1, type=int) or 1

    # Get filtered complaints.
    result = get_filtered_complaints(
        search=search,
        status=selected_status,
        category=category,
        priority=selected_priority,
        page=page,
        per_page=10,
    )

    # Get dashboard statistics.
    total_complaints = get_total_complaints()
    status_counts = get_status_counts()
    priority_counts = get_priority_counts()
    category_counts = get_category_counts()

    # Daily complaint trend.
    daily_complaint_counts = get_daily_complaint_counts(7)

    # Resolution time analytics.
    resolution_analytics = get_resolution_analytics()

    # Generate AI-powered insights.
    ai_insights = generate_insights(
        total_complaints=total_complaints,
        status_counts=status_counts,
        priority_counts=priority_counts,
        category_counts=category_counts,
        daily_complaint_counts=daily_complaint_counts,
    )

    return render_template(
        "admin.html",
        total_complaints=total_complaints,
        submitted_count=status_counts.get("Submitted", 0),
        in_progress_count=status_counts.get("In Progress", 0),
        resolved_count=status_counts.get("Resolved", 0),
        category_counts=category_counts,
        priority_counts=priority_counts,
        daily_complaint_counts=daily_complaint_counts,
        resolution_analytics=resolution_analytics,
        ai_insights=ai_insights,
        recent_complaints=result["complaints"],
        search=search,
        selected_status=selected_status,
        selected_category=category,
        selected_priority=selected_priority,
        current_page=result["page"],
        total_pages=result["total_pages"],
        filtered_total=result["total"],
        per_page=result["per_page"],
    )


@app.route("/admin/map")
@login_required
def admin_map():
    """Display the admin complaint map."""
    complaints = get_map_complaints()
    map_records = []

    for complaint in complaints:
        has_coordinates = (
            complaint["latitude"] is not None
            and complaint["longitude"] is not None
        )

        map_records.append(
            {
                "id": complaint["id"],
                "city": complaint["city"],
                "category": complaint["category"],
                "status": complaint["status"],
                "priority": complaint["priority"],
                "priority_score": complaint["priority_score"],
                "latitude": complaint["latitude"],
                "longitude": complaint["longitude"],
                "location_address": complaint["location_address"],
                "created_at": complaint["created_at"],
                "location_type": (
                    "gps" if has_coordinates else "approximate"
                ),
            }
        )

    return render_template(
        "map.html",
        complaints=map_records,
        total_complaints=len(map_records),
        gps_count=sum(
            1 for item in map_records
            if item["location_type"] == "gps"
        ),
        approximate_count=sum(
            1 for item in map_records
            if item["location_type"] == "approximate"
        ),
    )


@app.route("/admin/map/data")
@login_required
def admin_map_data():
    """Return map complaint data as JSON for the map interface."""
    complaints = get_map_complaints()
    map_records = []

    for complaint in complaints:
        has_coordinates = (
            complaint["latitude"] is not None
            and complaint["longitude"] is not None
        )

        map_records.append(
            {
                "id": complaint["id"],
                "city": complaint["city"],
                "category": complaint["category"],
                "status": complaint["status"],
                "priority": complaint["priority"],
                "priority_score": complaint["priority_score"],
                "latitude": complaint["latitude"],
                "longitude": complaint["longitude"],
                "location_address": complaint["location_address"],
                "created_at": complaint["created_at"],
                "location_type": (
                    "gps" if has_coordinates else "approximate"
                ),
            }
        )

    return jsonify({"complaints": map_records})


@app.route("/reverse-geocode", methods=["GET"])
def reverse_geocode():
    """
    Convert GPS coordinates into a readable address using
    OpenStreetMap's Nominatim reverse-geocoding service.
    """
    latitude, longitude = validate_coordinates(
        request.args.get("lat"),
        request.args.get("lon"),
    )

    if latitude is None or longitude is None:
        return jsonify(
            {
                "success": False,
                "address": "",
                "error": "Invalid GPS coordinates.",
            }
        ), 400

    params = urlencode(
        {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "zoom": 18,
            "addressdetails": 1,
        }
    )

    url = (
        "https://nominatim.openstreetmap.org/reverse?"
        + params
    )

    req = Request(
        url,
        headers={
            "User-Agent": (
                "CivicPulseAI/1.0 "
                "(local civic reporting project)"
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=8) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        address = str(
            payload.get("display_name", "")
        ).strip()

        if not address:
            return jsonify(
                {
                    "success": False,
                    "address": "",
                    "error": (
                        "No address was found for these coordinates."
                    ),
                }
            ), 404

        return jsonify(
            {
                "success": True,
                "address": address,
            }
        )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        app.logger.warning(
            "Reverse geocoding failed: %s", exc
        )

        return jsonify(
            {
                "success": False,
                "address": "",
                "error": (
                    "Address lookup is temporarily unavailable."
                ),
            }
        ), 502


if __name__ == "__main__":
    app.run(debug=True)
