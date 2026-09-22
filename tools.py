"""Tools the agent can call.

These are plain Python functions: no LLM involved, so the same input always gives
the same output. The model only DECIDES which tool to call; our code RUNS it.
"""
from datetime import date

from retrieval import search_regulations as semantic_search

# METU letter grade -> grade points.
# Source: METU NCC Undergraduate Education Regulation (2026), Article 24(5).
# NA counts as FF (0.00) in grade point averages, Article 24(5)(b).
GRADE_POINTS = {
    "AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0,
    "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0, "NA": 0.0,
}


def get_today() -> dict:
    today = date.today()
    return {"today": today.isoformat(), "weekday": today.strftime("%A")}


def days_until(target_date: str) -> dict:
    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        # Errors are returned as data, not raised: the model can read them and fix its call.
        return {"error": f"'{target_date}' is not a valid date. Use YYYY-MM-DD."}
    return {"target_date": target_date, "days_left": (target - date.today()).days}


def calculate_gpa(courses: list[dict]) -> dict:
    total_credits = 0.0
    total_points = 0.0
    for course in courses:
        grade = str(course.get("grade", "")).strip().upper()
        if grade not in GRADE_POINTS:
            return {"error": f"Unknown letter grade '{grade}'. Valid grades: {', '.join(GRADE_POINTS)}"}
        credits = float(course.get("credits", 0))
        total_credits += credits
        total_points += credits * GRADE_POINTS[grade]
    if total_credits == 0:
        return {"error": "Total credits is zero; nothing to average."}
    return {"gpa": round(total_points / total_credits, 2), "total_credits": total_credits}


def search_regulations(query: str) -> dict:
    return {"results": semantic_search(query, k=4)}


# What the MODEL sees: a name, a description and the parameters of each tool.
# The model never sees the Python code above, only these descriptions.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_regulations",
            "description": (
                "Searches the official METU NCC Undergraduate Education Regulation (2026) and returns the "
                "most relevant articles with their Turkish text. Use it for ANY question about academic rules: "
                "course withdrawal, add-drop, attendance, grades, repeating courses, probation, course load, "
                "graduation, etc. The query can be in Turkish or English."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look for, e.g. 'dersten çekilme kuralları'."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_today",
            "description": "Returns today's date (YYYY-MM-DD) and weekday. Use it whenever the answer depends on the current date.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "days_until",
            "description": "Returns how many days are left from today until the given date. Negative means the date has passed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_date": {"type": "string", "description": "Target date in YYYY-MM-DD format."},
                },
                "required": ["target_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_gpa",
            "description": "Calculates a METU-style GPA (4.00 scale) from courses' credits and letter grades. Always use this instead of doing the math yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "courses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "credits": {"type": "number", "description": "Credit hours of the course."},
                                "grade": {"type": "string", "description": "Letter grade: AA, BA, BB, CB, CC, DC, DD, FD, FF or NA."},
                            },
                            "required": ["credits", "grade"],
                        },
                    },
                },
                "required": ["courses"],
            },
        },
    },
]

# Name -> function, so the agent loop can find the Python function the model asked for.
TOOL_FUNCTIONS = {
    "search_regulations": search_regulations,
    "get_today": get_today,
    "days_until": days_until,
    "calculate_gpa": calculate_gpa,
}
