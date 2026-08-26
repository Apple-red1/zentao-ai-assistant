from ..route import Route

ROUTES = [
    Route('project.create', 'POST', '/api.php/v2/projects', 'project', 'create', required_query=(), required_body=('name', 'model', 'begin', 'end'), enum_values=(('model', ('agileplus', 'kanban', 'scrum', 'waterfall', 'waterfallplus')),)),
    Route('project.edit', 'PUT', '/api.php/v2/projects/{projectID}', 'project', 'edit', required_query=(), required_body=('name', 'model', 'begin', 'end'), enum_values=(('model', ('agileplus', 'kanban', 'scrum', 'waterfall', 'waterfallplus')),)),
    Route('project.list', 'GET', '/api.php/v2/projects', 'project', 'list', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'doing', 'undone', 'wait')),)),
    Route('project.list_program', 'GET', '/api.php/v2/programs/{programID}/projects', 'project', 'list_program', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'doing', 'undone', 'wait')),)),
    Route('project.delete', 'DELETE', '/api.php/v2/projects/{projectID}', 'project', 'delete', required_query=(), required_body=(), enum_values=()),
]
