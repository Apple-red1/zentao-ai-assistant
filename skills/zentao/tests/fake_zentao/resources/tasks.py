from ..route import Route

ROUTES = [
    Route('task.create', 'POST', '/api.php/v2/tasks', 'task', 'create', required_query=(), required_body=('name', 'executionID'), enum_values=()),
    Route('task.edit', 'PUT', '/api.php/v2/tasks/{taskID}', 'task', 'edit', required_query=(), required_body=(), enum_values=()),
    Route('task.list_execution', 'GET', '/api.php/v2/executions/{executionID}/tasks', 'task', 'list_execution', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'assignedbyme', 'assignedtome', 'myinvolved', 'unclosed')),)),
    Route('task.view', 'GET', '/api.php/v2/tasks/{taskID}', 'task', 'view', required_query=(), required_body=(), enum_values=()),
    Route('task.start', 'PUT', '/api.php/v2/tasks/{taskID}/start', 'task', 'start', required_query=(), required_body=('realStarted',), enum_values=()),
    Route('task.finish', 'PUT', '/api.php/v2/tasks/{taskID}/finish', 'task', 'finish', required_query=(), required_body=('currentConsumed', 'realStarted', 'finishedDate'), enum_values=()),
    Route('task.close', 'PUT', '/api.php/v2/tasks/{taskID}/close', 'task', 'close', required_query=(), required_body=(), enum_values=()),
    Route('task.activate', 'PUT', '/api.php/v2/tasks/{taskID}/activate', 'task', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('task.delete', 'DELETE', '/api.php/v2/tasks/{taskID}', 'task', 'delete', required_query=(), required_body=(), enum_values=()),
]
