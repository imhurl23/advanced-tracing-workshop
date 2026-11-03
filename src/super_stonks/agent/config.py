import os

import braintrust


def get_braintrust_project_name() -> str:
    # BRAINTRUST_DEFAULT_PROJECT is the workshop standard (the var the bt CLI reads),
    # so agent traffic from the CLI and Streamlit lands in the same project the CLI uses.
    # BRAINTRUST_PROJECT_NAME is kept as a fallback for older setups. No hardcoded
    # default: traces must land in the user's own project, never a shared one.
    project_name = (
        os.getenv("BRAINTRUST_DEFAULT_PROJECT", "").strip()
        or os.getenv("BRAINTRUST_PROJECT_NAME", "").strip()
    )
    if not project_name or "<" in project_name:
        raise RuntimeError(
            "BRAINTRUST_DEFAULT_PROJECT is not set — fill in your project name in .env "
            "(e.g. jane-stonks), then run: set -a; source .env; set +a"
        )
    return project_name


def init_braintrust_logger():
    return braintrust.init_logger(project=get_braintrust_project_name())
