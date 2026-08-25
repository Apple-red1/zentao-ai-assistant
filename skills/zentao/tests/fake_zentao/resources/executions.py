from ..route import Route

ROUTES = [
    Route('execution.create', 'POST', '/api.php/v2/executions', 'execution', 'create', required_query=(), required_body=('project', 'name', 'begin', 'end', 'products'), enum_values=(('type', ('kanban', 'sprint', 'stage')), ('attribute', ('concept', 'design', 'dev', 'develop', 'launch', 'mix', 'other', 'plan', 'qa', 'qualify', 'release', 'request', 'review')), ('lifetime', ('long', 'ops', 'short')), ('acl', ('open', 'private')))),
    Route('execution.edit', 'PUT', '/api.php/v2/executions/{executionID}', 'execution', 'edit', required_query=(), required_body=('name', 'begin', 'end'), enum_values=()),
    Route('execution.list', 'GET', '/api.php/v2/executions', 'execution', 'list', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'doing', 'undone', 'wait')),)),
    Route('execution.list_project', 'GET', '/api.php/v2/projects/{projectID}/executions', 'execution', 'list_project', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'doing', 'undone', 'wait')),)),
    Route('execution.view', 'GET', '/api.php/v2/executions/{executionID}', 'execution', 'view', required_query=(), required_body=(), enum_values=()),
    Route('execution.delete', 'DELETE', '/api.php/v2/executions/{executionID}', 'execution', 'delete', required_query=(), required_body=(), enum_values=()),
]
