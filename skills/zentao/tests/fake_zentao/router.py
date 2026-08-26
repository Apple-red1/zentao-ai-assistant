from __future__ import annotations

from .route import Route
from .resources.bugs import ROUTES as routes_bugs
from .resources.builds import ROUTES as routes_builds
from .resources.epics import ROUTES as routes_epics
from .resources.executions import ROUTES as routes_executions
from .resources.feedbacks import ROUTES as routes_feedbacks
from .resources.files import ROUTES as routes_files
from .resources.products import ROUTES as routes_products
from .resources.product_plans import ROUTES as routes_product_plans
from .resources.programs import ROUTES as routes_programs
from .resources.projects import ROUTES as routes_projects
from .resources.releases import ROUTES as routes_releases
from .resources.requirements import ROUTES as routes_requirements
from .resources.stories import ROUTES as routes_stories
from .resources.systems import ROUTES as routes_systems
from .resources.tasks import ROUTES as routes_tasks
from .resources.test_cases import ROUTES as routes_test_cases
from .resources.test_tasks import ROUTES as routes_test_tasks
from .resources.tickets import ROUTES as routes_tickets
from .resources.auth import ROUTES as routes_auth
from .resources.users import ROUTES as routes_users

ALL_ROUTES: tuple[Route, ...] = tuple(route for group in [routes_bugs, routes_builds, routes_epics, routes_executions, routes_feedbacks, routes_files, routes_products, routes_product_plans, routes_programs, routes_projects, routes_releases, routes_requirements, routes_stories, routes_systems, routes_tasks, routes_test_cases, routes_test_tasks, routes_tickets, routes_auth, routes_users] for route in group)
FAKE_ENDPOINT_IDS = frozenset(route.endpoint_id for route in ALL_ROUTES)

def match(method: str, path: str) -> tuple[Route, dict[str, int]] | None:
    for route in ALL_ROUTES:
        if route.method != method:
            continue
        found = route.regex.match(path)
        if found:
            return route, {key: int(value) for key, value in found.groupdict().items()}
    return None
