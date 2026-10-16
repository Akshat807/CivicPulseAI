
def generate_insights(
    total_complaints=0,
    status_counts=None,
    priority_counts=None,
    category_counts=None,
    daily_complaint_counts=None,
):
    """Generate actionable dashboard insights from complaint statistics."""

    status_counts = status_counts or {}
    priority_counts = priority_counts or {}
    category_counts = category_counts or {}
    daily_complaint_counts = daily_complaint_counts or []

    insights = []

    # Normalize status and priority names.
    normalized_status = {
        str(key).strip().lower(): int(value or 0)
        for key, value in status_counts.items()
    }

   
    normalized_priority = {
        str(key).strip().lower(): int(value or 0)
        for key, value in priority_counts.items()
    }

    if isinstance(category_counts, dict):
        normalized_categories = {
            str(key).strip(): int(value or 0)
            for key, value in category_counts.items()
        }
    else:
        normalized_categories = {
            str(item["category"]).strip(): int(item.get("total", 0) or 0)
            for item in category_counts
            if isinstance(item, dict) and item.get("category")
        }

    submitted = normalized_status.get("submitted", 0)
    in_progress = normalized_status.get("in progress", 0)
    resolved = normalized_status.get("resolved", 0)

    critical = normalized_priority.get("critical", 0)
    high = normalized_priority.get("high", 0)
    urgent = critical + high

    pending = submitted + in_progress

    # Insight 1: Urgent complaints.
    if urgent > 0:
        insights.append({
            "type": "urgent",
            "title": "Urgent complaints need attention",
            "message": (
                f"{urgent} complaint(s) have Critical or High priority. "
                "Review these complaints first."
            ),
            "recommendation": (
                "Open the complaint queue and review Critical and High "
                "priority cases."
            ),
        })
    else:
        insights.append({
            "type": "success",
            "title": "No urgent complaints recorded",
            "message": (
                "There are currently no Critical or High priority complaints."
            ),
            "recommendation": "Continue monitoring new complaints.",
        })

    # Insight 2: Pending workflow.
    if pending > 0:
        insights.append({
            "type": "workflow",
            "title": "Complaints awaiting action",
            "message": (
                f"{pending} complaint(s) are Submitted or In Progress."
            ),
            "recommendation": (
                "Review pending cases and update their status as work progresses."
            ),
        })
    else:
        insights.append({
            "type": "success",
            "title": "No pending complaints recorded",
            "message": (
                "No Submitted or In Progress complaints were found."
            ),
            "recommendation": "Continue monitoring incoming complaints.",
        })

    # Insight 3: Most frequently reported category.
    if normalized_categories:
        top_category, top_count = max(
            normalized_categories.items(),
            key=lambda item: item[1],
        )

        insights.append({
            "type": "category",
            "title": "Most reported complaint category",
            "message": (
                f"{top_category} has {top_count} recorded complaint(s)."
            ),
            "recommendation": (
                f"Review {top_category} complaints for recurring issues "
                "and possible preventive action."
            ),
        })

    # Insight 4: Resolution progress.
    if total_complaints > 0:
        resolution_rate = round(
            (resolved / total_complaints) * 100, 1
        )
    else:
        resolution_rate = 0.0

    insights.append({
        "type": "resolution",
        "title": "Complaint resolution progress",
        "message": (
            f"{resolution_rate}% of recorded complaints are marked Resolved."
        ),
        "recommendation": (
            "Prioritize pending complaints and keep resolution statuses up to date."
        ),
    })

    # Insight 5: Daily complaint trend detection.
    #
    # Expects entries shaped like:
    # [{"date": "2026-10-15", "total": 3}, ...]
    #
    # Compare the latest day's count against the average of the
    # preceding available days. Only report a spike when the previous
    # average is positive and the latest count is at least double it.
    daily_counts = []

    for item in daily_complaint_counts:
        try:
            count = max(0, int(item.get("total", 0)))
        except (TypeError, ValueError, AttributeError):
            continue

        daily_counts.append({
            "date": str(item.get("date", "")),
            "total": count,
        })

    if len(daily_counts) >= 2:
        previous_counts = [
            item["total"] for item in daily_counts[:-1]
        ]
        latest = daily_counts[-1]

        previous_average = (
            sum(previous_counts) / len(previous_counts)
        )

        if (
            previous_average > 0
            and latest["total"] >= previous_average * 2
        ):
            insights.append({
                "type": "trend",
                "title": "Complaint volume spike detected",
                "message": (
                    f"{latest['total']} complaints were recorded on "
                    f"{latest['date']}, at least twice the average "
                    "of the preceding available days."
                ),
                "recommendation": (
                    "Review recent complaints by category and location "
                    "to determine whether a recurring civic issue needs attention."
                ),
            })
        elif latest["total"] > 0 and previous_average == 0:
            insights.append({
                "type": "trend",
                "title": "New complaint activity detected",
                "message": (
                    f"{latest['total']} complaint(s) were recorded on "
                    f"{latest['date']}, while the preceding available days "
                    "had no recorded complaints."
                ),
                "recommendation": (
                    "Review the latest submissions and continue monitoring "
                    "daily complaint volume."
                ),
            })
        else:
            insights.append({
                "type": "trend",
                "title": "Daily complaint trend",
                "message": (
                    f"{latest['total']} complaint(s) were recorded on "
                    f"{latest['date']}. No significant spike was detected "
                    "by the current rule."
                ),
                "recommendation": (
                    "Continue monitoring daily counts for unusual increases."
                ),
            })
    else:
        insights.append({
            "type": "trend",
            "title": "Daily complaint trend unavailable",
            "message": (
                "More daily complaint-count data is needed to compare trends."
            ),
            "recommendation": (
                "Keep collecting complaint data to enable trend comparisons."
            ),
        })




    return insights
