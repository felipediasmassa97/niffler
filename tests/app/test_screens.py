"""UI regression tests: every screen renders without raising, across widget states.

Loads each screen registered in `main.py`'s `st.navigation(...)` call via Streamlit's
official `AppTest` runner, then exercises every checkbox and selectbox on it (every
value, one at a time), asserting the app never raises. This drives the exact same code
path as a real browser session - `ProcessedLoader`, business rules, charts - without a
browser.

Catches exactly the class of bug this file was written for: a screen (or a non-default
widget state on it) that raises at render time, e.g. a `KeyError` from a per-category
dict missing an entry. It does NOT catch purely visual issues (a chart rendering blank,
bad colors, layout glitches) - AppTest inspects the element tree and script execution,
not pixels.

Requires a populated src/app/.streamlit/secrets.toml (AWS credentials) and network
access to AWS, same as `streamlit run main.py` - it reads the real current snapshot
from S3, not a mocked one, so results reflect whatever data is live right now. Fails
outright (not a skip) when secrets aren't set up, so this stays a hard gate: set up
`src/app/.streamlit/secrets.toml` (see infra/README.md) to run it.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Exception as ExceptionElement

APP_DIR = Path(__file__).resolve().parents[2] / "src" / "app"
MAIN_PY = APP_DIR / "main.py"
SECRETS_PATH = APP_DIR / ".streamlit" / "secrets.toml"


@dataclass
class Failure:
    """One exception observed while exercising a screen."""

    interaction: str
    message: str
    stack_trace: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Format as '<interaction>: <message>' plus a trailing traceback tail."""
        trace = ("\n" + "\n".join(self.stack_trace[-6:])) if self.stack_trace else ""
        return f"{self.interaction}: {self.message}{trace}"


def discover_pages() -> list[tuple[str, str]]:
    """Parse main.py's st.navigation(...) call for registered (name, file) pages.

    Returns [(page_var_name, "screens/<module>.py")] in navigation order, so
    newly added/removed screens are picked up automatically - nothing to
    hardcode or keep in sync by hand.
    """
    tree = ast.parse(MAIN_PY.read_text())
    import_map: dict[str, str] = {}
    nav_order: list[str] = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("screens.")
        ):
            for alias in node.names:
                import_map[alias.asname or alias.name] = node.module
        is_navigation_call = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "navigation"
        )
        if is_navigation_call and node.args and isinstance(node.args[0], ast.List):
            nav_order = [
                elt.id for elt in node.args[0].elts if isinstance(elt, ast.Name)
            ]

    pages = []
    for var_name in nav_order:
        module = import_map.get(var_name)
        if module is None:
            continue
        pages.append((var_name, module.replace("screens.", "screens/") + ".py"))
    return pages


PAGES = discover_pages()


def _record_exceptions(
    exceptions: list[ExceptionElement], interaction: str
) -> list[Failure]:
    return [
        Failure(interaction, exc.value, list(exc.stack_trace)) for exc in exceptions
    ]


def _exercise_widgets(at: AppTest) -> list[Failure]:
    """Cycle every checkbox/selectbox on the currently-loaded page, one at a time."""
    failures: list[Failure] = []

    for i in range(len(at.checkbox)):
        label = at.checkbox[i].label
        original = at.checkbox[i].value
        at.checkbox[i].set_value(not original).run()
        failures += _record_exceptions(
            list(at.exception), f'checkbox "{label}" = {not original}'
        )
        at.checkbox[i].set_value(original).run()

    for i in range(len(at.selectbox)):
        label = at.selectbox[i].label
        original_index = at.selectbox[i].index
        for option_index, option_label in enumerate(at.selectbox[i].options):
            at.selectbox[i].select_index(option_index).run()
            failures += _record_exceptions(
                list(at.exception), f'selectbox "{label}" = "{option_label}"'
            )
        at.selectbox[i].select_index(original_index).run()

    return failures


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    """Load the app with cwd set to src/app, matching `streamlit run main.py`.

    Streamlit resolves `.streamlit/secrets.toml` relative to the current working
    directory, not the script's location - chdir is required for secrets to resolve
    the same way a real `streamlit run` session (always launched from src/app) does.
    """
    monkeypatch.chdir(APP_DIR)
    at = AppTest.from_file(str(MAIN_PY), default_timeout=60)
    at.run()
    return at


@pytest.mark.parametrize(("page_var", "screen_file"), PAGES, ids=[p[1] for p in PAGES])
def test_screen_renders_without_exception(
    app: AppTest, page_var: str, screen_file: str
) -> None:
    """Every registered screen loads, and every widget on it, without raising."""
    del page_var  # only used for the test id
    if not SECRETS_PATH.exists():
        # Checked explicitly (rather than relying on the exception this would
        # naturally raise) so every screen fails uniformly and clearly instead of a
        # crashed initial page load leaving later switch_page()'d screens looking
        # like a false pass.
        pytest.fail(
            f"No {SECRETS_PATH} - set up AWS secrets to run UI screen tests "
            "(see infra/README.md)"
        )
    if screen_file != PAGES[0][1]:
        app.switch_page(screen_file)
        app.run()

    failures = _record_exceptions(list(app.exception), "initial load")
    failures += _exercise_widgets(app)

    assert not failures, "\n\n".join(str(f) for f in failures)
