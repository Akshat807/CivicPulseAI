
import re


PRIORITY_ORDER = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

# Immediate-danger phrases.
CRITICAL_PHRASES = [
    "live wire",
    "exposed live wire",
    "electric wire is sparking",
    "sparks are coming",
    "electrocution",
    "electric shock",
    "fire has started",
    "building has collapsed",
    "people are trapped",
    "person is trapped",
    "life threatening",
    "person is unconscious",
    "people are drowning",
    "electrical fire",
]

HIGH_PHRASES = [
    "major flooding",
    "severe flooding",
    "deep flood water",
    "road has collapsed",
    "large pothole",
    "major water pipe burst",
    "sewage overflowing",
    "electric pole is falling",
    "power line is down",
    "multiple people injured",
    "water pipe has burst",
    "houses are underwater",
    "medical waste",
    "hazardous waste",
    "contaminated water",
]

NEGATION_PATTERN = re.compile(
    r"\b(no|not|never|without|isn't|aren't|wasn't|weren't|"
    r"doesn't|don't|didn't|cannot|can't|hasn't|haven't|"
    r"has no|there is no|there are no)\b",
    re.IGNORECASE,
)


def normalize_text(text):
    """Normalize complaint text for rule matching."""
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_clauses(text):
    """
    Split text into small clauses so that a negation in one
    clause is less likely to affect a separate statement.
    """
    return re.split(
        r"[.!?;,\n]+|\bbut\b|\bhowever\b|\balthough\b",
        text,
    )


def phrase_is_present(phrase, clause):
    """Check for a phrase without matching inside another word."""
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, clause) is not None


def phrase_is_negated(phrase, clause):
    """
    Basic negation handling.

    Examples:
      'No live wire is present' -> negated
      'The live wire is sparking' -> not negated

    This is a heuristic, not a complete language-understanding model.
    """
    match = re.search(
        r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
        clause,
    )

    if not match:
        return False

    preceding_text = clause[:match.start()].strip()

    # Only inspect nearby words before the matched phrase.
    preceding_words = preceding_text.split()[-5:]
    nearby_text = " ".join(preceding_words)

    if not nearby_text:
        return False

    # Avoid treating "not only" as a negation.
    if re.search(r"\bnot only\b", nearby_text):
        return False

    return bool(NEGATION_PATTERN.search(nearby_text))


def find_matching_phrases(text, phrases):
    """
    Return matching phrases that are not explicitly negated.
    """
    matches = []

    for clause in split_clauses(text):
        clause = clause.strip()

        if not clause:
            continue

        for phrase in phrases:
            if phrase_is_present(phrase, clause):
                if not phrase_is_negated(phrase, clause):
                    matches.append(phrase)

    return list(dict.fromkeys(matches))


def detect_priority_details(complaint, category=None):
    """
    Return priority, score and explanation.

    Priority score is a rule-based urgency indicator from 0 to 100.
    It is not a probability or a guarantee of real-world severity.
    """
    text = normalize_text(complaint)
    category_text = normalize_text(category)

    if not text:
        return {
            "priority": "Medium",
            "score": 40,
            "reason": "Complaint text is empty; manual review is needed.",
            "matched_signals": [],
        }

    critical_matches = find_matching_phrases(
        text,
        CRITICAL_PHRASES,
    )

    high_matches = find_matching_phrases(
        text,
        HIGH_PHRASES,
    )

    # Critical safety indicators take precedence.
    if critical_matches:
        return {
            "priority": "Critical",
            "score": 95,
            "reason": (
                "Potential immediate safety risk detected: "
                + ", ".join(critical_matches)
            ),
            "matched_signals": critical_matches,
        }

    # Serious hazards or disruption.
    if high_matches:
        return {
            "priority": "High",
            "score": 75,
            "reason": (
                "Serious hazard or disruption detected: "
                + ", ".join(high_matches)
            ),
            "matched_signals": high_matches,
        }

    # Category-specific indicators.
    category_rules = {
        "electrical hazard": {
            "high": [
                "wire",
                "cable",
                "sparking",
                "electric pole",
                "power line",
                "exposed wire",
            ],
            "medium": [
                "street light",
                "streetlight",
                "power outage",
                "electricity",
                "voltage",
            ],
        },
        "flooding": {
            "high": [
                "deep water",
                "water entering homes",
                "houses underwater",
                "water entering house",
                "trapped",
            ],
            "medium": [
                "waterlogging",
                "waterlogged",
                "water on road",
                "heavy rain",
                "drain overflow",
            ],
        },
        "road damage": {
            "high": [
                "deep cracks",
                "collapsed road",
                "large pothole",
                "road collapse",
            ],
            "medium": [
                "pothole",
                "broken road",
                "damaged road",
                "road crack",
            ],
        },
        "water issue": {
            "high": [
                "pipe burst",
                "contaminated",
                "sewage",
                "dirty drinking water",
            ],
            "medium": [
                "water supply stopped",
                "no water supply",
                "water leakage",
                "low water pressure",
                "water shortage",
            ],
        },
        "waste management": {
            "high": [
                "medical waste",
                "dead animal",
                "hazardous waste",
                "chemical waste",
            ],
            "medium": [
                "garbage",
                "waste collection",
                "overflowing bin",
                "rubbish",
                "trash",
            ],
        },
    }

    rules = category_rules.get(category_text, {})

    # Check category rules clause by clause to reduce
    # false positives from simple negated statements.
    for level in ("high", "medium"):
        matches = find_matching_phrases(
            text,
            rules.get(level, []),
        )

        if matches:
            if level == "high":
                return {
                    "priority": "High",
                    "score": 75,
                    "reason": (
                        "A serious issue indicator was found for "
                        f"{category or 'this complaint'}: "
                        + ", ".join(matches)
                    ),
                    "matched_signals": matches,
                }

            return {
                "priority": "Medium",
                "score": 50,
                "reason": (
                    "A routine civic issue indicator was found: "
                    + ", ".join(matches)
                ),
                "matched_signals": matches,
            }

    # Generic wording when the category does not provide a match.
    return {
        "priority": "Medium",
        "score": 40,
        "reason": (
            "No strong urgency indicator was detected. "
            "Manual review may change the priority."
        ),
        "matched_signals": [],
    }


def detect_priority(complaint, category=None):
    """
    Backward-compatible function.

    Existing app.py calls can continue using:
        priority = detect_priority(complaint, category)
    """
    result = detect_priority_details(complaint, category)
    return result["priority"]


if __name__ == "__main__":
    test_cases = [
        (
            "A live wire is hanging on the road",
            "Electrical Hazard",
            "Critical",
        ),
        (
            "A large pothole has damaged the road",
            "Road Damage",
            "High",
        ),
        (
            "Water supply has stopped in our area",
            "Water Issue",
            "Medium",
        ),
        (
            "Garbage has not been collected for two days",
            "Waste Management",
            "Medium",
        ),
        (
            "People are trapped in deep flood water",
            "Flooding",
            "Critical",
        ),
        (
            "No live wire is present near our house",
            "Electrical Hazard",
            "Medium",
        ),
        (
            "There is a pothole on the road",
            "Road Damage",
            "Medium",
        ),
        (
            "A street light is not working",
            "Electrical Hazard",
            "Medium",
        ),
    ]

    print("\nCivicPulse AI - Priority Engine 2.0\n")

    passed = 0

    for complaint, category, expected in test_cases:
        result = detect_priority_details(complaint, category)
        actual = result["priority"]
        success = actual == expected

        if success:
            passed += 1

        print(f"Complaint: {complaint}")
        print(f"Category:  {category}")
        print(f"Priority:  {actual}")
        print(f"Score:     {result['score']}/100")
        print(f"Reason:    {result['reason']}")
        print(f"Test:      {'PASS' if success else 'CHECK'}")
        print("-" * 60)

    print(f"\nTests passed: {passed}/{len(test_cases)}")
