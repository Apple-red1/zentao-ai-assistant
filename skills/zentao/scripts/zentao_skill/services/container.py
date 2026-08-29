from __future__ import annotations

from ..internal.config import load_config
from ..internal.zentao.session import ZentaoSession
from ..internal.zentao.bugs import BugsAPI
from .bugs.service import BugsService
from ..internal.zentao.builds import BuildsAPI
from .builds.service import BuildsService
from ..internal.zentao.epics import EpicsAPI
from .epics.service import EpicsService
from ..internal.zentao.executions import ExecutionsAPI
from .executions.service import ExecutionsService
from ..internal.zentao.feedbacks import FeedbacksAPI
from .feedbacks.service import FeedbacksService
from ..internal.zentao.files import FilesAPI
from .files.service import FilesService
from ..internal.zentao.resources import ResourcesAPI
from .resources.service import ResourcesService
from ..internal.zentao.products import ProductsAPI
from .products.service import ProductsService
from ..internal.zentao.product_plans import ProductPlansAPI
from .product_plans.service import ProductPlansService
from ..internal.zentao.programs import ProgramsAPI
from .programs.service import ProgramsService
from ..internal.zentao.projects import ProjectsAPI
from .projects.service import ProjectsService
from ..internal.zentao.releases import ReleasesAPI
from .releases.service import ReleasesService
from ..internal.zentao.requirements import RequirementsAPI
from .requirements.service import RequirementsService
from ..internal.zentao.stories import StoriesAPI
from .stories.service import StoriesService
from ..internal.zentao.systems import SystemsAPI
from .systems.service import SystemsService
from ..internal.zentao.tasks import TasksAPI
from .tasks.service import TasksService
from ..internal.zentao.test_cases import TestCasesAPI
from .test_cases.service import TestCasesService
from ..internal.zentao.test_tasks import TestTasksAPI
from .test_tasks.service import TestTasksService
from ..internal.zentao.tickets import TicketsAPI
from .tickets.service import TicketsService
from ..internal.zentao.users import UsersAPI
from .users.service import UsersService
from ..internal.zentao.comments import CommentAPI
from .comments.service import CommentService


class Services:
    def __init__(self) -> None:
        self.session = ZentaoSession(load_config())
        self.bug = BugsService(BugsAPI(self.session))
        self.build = BuildsService(BuildsAPI(self.session))
        self.epic = EpicsService(EpicsAPI(self.session))
        self.execution = ExecutionsService(ExecutionsAPI(self.session))
        self.feedback = FeedbacksService(FeedbacksAPI(self.session))
        self.file = FilesService(FilesAPI(self.session))
        self.resource = ResourcesService(ResourcesAPI(self.session))
        self.product = ProductsService(ProductsAPI(self.session))
        self.product_plan = ProductPlansService(ProductPlansAPI(self.session))
        self.program = ProgramsService(ProgramsAPI(self.session))
        self.project = ProjectsService(ProjectsAPI(self.session))
        self.release = ReleasesService(ReleasesAPI(self.session))
        self.requirement = RequirementsService(RequirementsAPI(self.session))
        self.story = StoriesService(StoriesAPI(self.session))
        self.system = SystemsService(SystemsAPI(self.session))
        self.task = TasksService(TasksAPI(self.session))
        self.test_case = TestCasesService(TestCasesAPI(self.session))
        self.test_task = TestTasksService(TestTasksAPI(self.session))
        self.ticket = TicketsService(TicketsAPI(self.session))
        self.user = UsersService(UsersAPI(self.session))
        self.comments = CommentService(CommentAPI(self.session), account=self.session.config.account)
