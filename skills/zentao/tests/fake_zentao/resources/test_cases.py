from ..route import Route

ROUTES = [
    Route('test-case.create', 'POST', '/api.php/v2/testcases', 'test-case', 'create', required_query=(), required_body=('productID', 'product', 'title'), enum_values=(('type', ('config', 'feature', 'install', 'interface', 'other', 'performance', 'security', 'unit')), ('stepType', ('group', 'step')))),
    Route('test-case.edit', 'PUT', '/api.php/v2/testcases/{caseID}', 'test-case', 'edit', required_query=(), required_body=('title',), enum_values=(('type', ('config', 'feature', 'install', 'interface', 'other', 'performance', 'security', 'unit')), ('stepType', ('group', 'step')))),
    Route('test-case.list_product', 'GET', '/api.php/v2/products/{productID}/testcases', 'test-case', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'needconfirm', 'wait')),)),
    Route('test-case.list_project', 'GET', '/api.php/v2/projects/{projectID}/testcases', 'test-case', 'list_project', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'needconfirm', 'wait')),)),
    Route('test-case.list_execution', 'GET', '/api.php/v2/executions/{executionID}/testcases', 'test-case', 'list_execution', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'needconfirm', 'wait')),)),
    Route('test-case.view', 'GET', '/api.php/v2/testcases/{caseID}', 'test-case', 'view', required_query=(), required_body=(), enum_values=()),
    Route('test-case.delete', 'DELETE', '/api.php/v2/testcases/{caseID}', 'test-case', 'delete', required_query=(), required_body=(), enum_values=()),
]
