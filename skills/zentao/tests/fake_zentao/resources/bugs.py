from ..route import Route

ROUTES = [
    Route('bug.create', 'POST', '/api.php/v2/bugs', 'bug', 'create', required_query=(), required_body=('productID', 'product', 'title', 'openedBuild'), enum_values=(('type', ('automation', 'codeerror', 'config', 'designdefect', 'install', 'others', 'performance', 'security', 'standard')),)),
    Route('bug.edit', 'PUT', '/api.php/v2/bugs/{bugID}', 'bug', 'edit', required_query=(), required_body=(), enum_values=(('type', ('automation', 'codeerror', 'config', 'designdefect', 'install', 'others', 'performance', 'security', 'standard')),)),
    Route('bug.list_product', 'GET', '/api.php/v2/products/{productID}/bugs', 'bug', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'assignedbyme', 'assignedtome', 'openedbyme', 'unclosed')),)),
    Route('bug.list_project', 'GET', '/api.php/v2/projects/{projectID}/bugs', 'bug', 'list_project', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'unresolved')),)),
    Route('bug.list_execution', 'GET', '/api.php/v2/executions/{executionID}/bugs', 'bug', 'list_execution', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'unresolved')),)),
    Route('bug.view', 'GET', '/api.php/v2/bugs/{bugID}', 'bug', 'view', required_query=(), required_body=(), enum_values=()),
    Route('bug.resolve', 'PUT', '/api.php/v2/bugs/{bugID}/resolve', 'bug', 'resolve', required_query=(), required_body=('resolution',), enum_values=(('resolution', ('bydesign', 'duplicate', 'external', 'fixed', 'notrepro', 'postponed', 'tostory', 'willnotfix')),)),
    Route('bug.close', 'PUT', '/api.php/v2/bugs/{bugID}/close', 'bug', 'close', required_query=(), required_body=(), enum_values=()),
    Route('bug.activate', 'PUT', '/api.php/v2/bugs/{bugID}/activate', 'bug', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('bug.delete', 'DELETE', '/api.php/v2/bugs/{bugID}', 'bug', 'delete', required_query=(), required_body=(), enum_values=()),
]
