from datetime import date


def calculate_priority_score(task: dict) -> float:
    """
    Calculate an objective maintenance priority score.

    Score range: 0-100

    The department does not directly determine the score.
    The score is calculated from maintenance characteristics.
    """

    score = 0.0

    # ---------------------------------------------------------
    # 1. DEFECT SEVERITY
    # ---------------------------------------------------------

    severity_scores = {
        "CRITICAL": 30,
        "HIGH": 20,
        "MEDIUM": 10,
        "LOW": 5,
    }

    score += severity_scores.get(
        str(task.get("defect_severity", "")).upper(),
        0,
    )

    # ---------------------------------------------------------
    # 2. FAILURE RISK
    # ---------------------------------------------------------

    risk_scores = {
        "CRITICAL": 20,
        "HIGH": 15,
        "MEDIUM": 8,
        "LOW": 3,
    }

    score += risk_scores.get(
        str(task.get("failure_risk", "")).upper(),
        0,
    )

    # ---------------------------------------------------------
    # 3. SAFETY
    # ---------------------------------------------------------

    if task.get("safety_related", False):
        score += 20

    # ---------------------------------------------------------
    # 4. ASSET OPERATIONAL STATUS
    # ---------------------------------------------------------

    status_scores = {
        "FAILED": 10,
        "RESTRICTED": 8,
        "DEGRADED": 5,
        "OPERATIONAL": 0,
    }

    score += status_scores.get(
        str(task.get("asset_operational_status", "")).upper(),
        0,
    )

    # ---------------------------------------------------------
    # 5. OVERDUE
    # ---------------------------------------------------------

    if task.get("overdue", False):
        score += 5

    # ---------------------------------------------------------
    # CAP SCORE
    # ---------------------------------------------------------

    return min(score, 100.0)


def classify_priority(score: float) -> str:
    """
    Convert numeric score into a priority category.
    """

    if score >= 80:
        return "CRITICAL"

    if score >= 60:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


def calculate_priority(task: dict) -> dict:
    """
    Calculate complete priority information for a maintenance task.
    """

    score = calculate_priority_score(task)

    return {
        "task_id": task.get("request_id"),
        "priority_score": round(score, 2),
        "priority": classify_priority(score),
    }