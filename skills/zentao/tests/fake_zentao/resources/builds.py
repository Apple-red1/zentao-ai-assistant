from ..route import Route

ROUTES = [
    Route('build.create', 'POST', '/api.php/v2/builds', 'build', 'create', required_query=(), required_body=('executionID', 'product', 'name', 'system', 'builder', 'date'), enum_values=()),
    Route('build.edit', 'PUT', '/api.php/v2/builds/{buildID}', 'build', 'edit', required_query=(), required_body=('execution', 'product', 'name', 'system', 'builder', 'date'), enum_values=()),
    Route('build.list_project', 'GET', '/api.php/v2/projects/{projectID}/builds', 'build', 'list_project', required_query=(), required_body=(), enum_values=(('browseType', ('active', 'all', 'closed')),)),
    Route('build.list_execution', 'GET', '/api.php/v2/executions/{executionID}/builds', 'build', 'list_execution', required_query=(), required_body=(), enum_values=(('browseType', ('active', 'all', 'closed')),)),
    Route('build.delete', 'DELETE', '/api.php/v2/builds/{buildID}', 'build', 'delete', required_query=(), required_body=(), enum_values=()),
]
