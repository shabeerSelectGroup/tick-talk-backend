"""30 corporate networking bingo prompts — human bingo / find-someone-who."""

from app.models.enums import TaskType

# (slug, title, description hint for host — title is the checkbox label)
NETWORKING_BINGO_CATEGORIES: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    (
        "travel",
        "Travel & Personal",
        [
            ("loves-traveling", "Loves traveling", "Find someone who loves traveling"),
            (
                "visited-5-countries",
                "Has visited more than 5 countries",
                "Find someone who has visited more than 5 countries",
            ),
            ("enjoys-road-trips", "Enjoys road trips", "Find someone who enjoys road trips"),
            (
                "lived-another-city",
                "Has lived in another city",
                "Find someone who has lived in another city",
            ),
            (
                "loves-adventure",
                "Loves adventure activities",
                "Find someone who loves adventure activities",
            ),
        ],
    ),
    (
        "professional",
        "Professional",
        [
            ("works-in-hr", "Works in HR", "Find someone who works in HR"),
            ("works-in-finance", "Works in Finance", "Find someone who works in Finance"),
            ("works-in-it", "Works in IT", "Find someone who works in IT"),
            ("manages-team", "Manages a team", "Find someone who manages a team"),
            (
                "experience-10-years",
                "Has more than 10 years of experience",
                "Find someone with more than 10 years of experience",
            ),
        ],
    ),
    (
        "skills",
        "Skills",
        [
            (
                "good-with-technology",
                "Good with technology",
                "Find someone who is good with technology",
            ),
            (
                "speaks-3-languages",
                "Speaks 3 or more languages",
                "Find someone who speaks 3 or more languages",
            ),
            (
                "public-speaking",
                "Good at public speaking",
                "Find someone who is good at public speaking",
            ),
            (
                "problem-solver",
                "Excellent problem solver",
                "Find someone who is an excellent problem solver",
            ),
            (
                "professional-cert",
                "Has completed a professional certification",
                "Find someone who has completed a professional certification",
            ),
        ],
    ),
    (
        "fun_facts",
        "Fun Facts",
        [
            (
                "plays-sports",
                "Plays sports regularly",
                "Find someone who plays sports regularly",
            ),
            ("loves-football", "Loves football", "Find someone who loves football"),
            ("loves-cricket", "Loves cricket", "Find someone who loves cricket"),
            ("enjoys-cooking", "Enjoys cooking", "Find someone who enjoys cooking"),
            (
                "loves-movies",
                "Loves watching movies",
                "Find someone who loves watching movies",
            ),
        ],
    ),
    (
        "networking",
        "Networking & Leadership",
        [
            (
                "intl-conference",
                "Has attended an international conference",
                "Find someone who has attended an international conference",
            ),
            ("trained-team", "Has trained a team", "Find someone who has trained a team"),
            ("led-project", "Has led a project", "Find someone who has led a project"),
            ("mentors-others", "Mentors others", "Find someone who mentors others"),
            (
                "multiple-industries",
                "Has worked in multiple industries",
                "Find someone who has worked in multiple industries",
            ),
        ],
    ),
    (
        "ice_breakers",
        "Ice Breakers",
        [
            (
                "birthday-this-month",
                "Is celebrating a birthday this month",
                "Find someone celebrating a birthday this month",
            ),
            ("unique-hobby", "Has a unique hobby", "Find someone with a unique hobby"),
            (
                "coffee-daily",
                "Drinks coffee every day",
                "Find someone who drinks coffee every day",
            ),
            (
                "prefers-tea",
                "Prefers tea over coffee",
                "Find someone who prefers tea over coffee",
            ),
            (
                "new-role-year",
                "Started a new role within the last year",
                "Find someone who started a new role within the last year",
            ),
        ],
    ),
]

BINGO_TASK_COUNT = sum(len(items) for _, _, items in NETWORKING_BINGO_CATEGORIES)


def networking_bingo_task_templates() -> list[dict]:
    """Flat task rows for event creation (all manual bingo prompts)."""
    templates: list[dict] = []
    order = 0
    for category_slug, _category_label, items in NETWORKING_BINGO_CATEGORIES:
        for slug, title, description in items:
            templates.append(
                {
                    "slug": f"bingo-{slug}",
                    "title": title,
                    "description": description,
                    "type": TaskType.SELFIE,
                    "points": 0,
                    "config_json": {
                        "bingo": True,
                        "category": category_slug,
                    },
                }
            )
            order += 1
    return templates
