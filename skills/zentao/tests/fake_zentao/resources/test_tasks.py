from ..route import Route

ROUTES = [
    Route('test-task.create', 'POST', '/api.php/v2/testtasks', 'test-task', 'create', required_query=(), required_body=('productID', 'product', 'name', 'build', 'begin', 'end'), enum_values=(('type', ('acceptance', 'integrate', 'performance', 'safety', 'system')), ('status', ('blocked', 'doing', 'done', 'wait')))),
    Route('test-task.edit', 'PUT', '/api.php/v2/testtasks/{testtaskID}', 'test-task', 'edit', required_query=(), required_body=('name', 'build', 'begin', 'end'), enum_values=(('type', ('acceptance', 'integrate', 'performance', 'safety', 'system')), ('status', ('blocked', 'doing', 'done', 'wait')))),
    Route('test-task.list_product', 'GET', '/api.php/v2/products/{productID}/testtasks', 'test-task', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'blocked', 'doing', 'done', 'wait')),)),
    Route('test-task.list_project', 'GET', '/api.php/v2/projects/{projectID}/testtasks', 'test-task', 'list_project', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'blocked', 'doing', 'done', 'wait')),)),
    Route('test-task.list_execution', 'GET', '/api.php/v2/executions/{executionID}/testtasks', 'test-task', 'list_execution', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'blocked', 'doing', 'done', 'wait')),)),
    Route('test-task.delete', 'DELETE', '/api.php/v2/testtasks/{testtaskID}', 'test-task', 'delete', required_query=(), required_body=(), enum_values=()),
]
