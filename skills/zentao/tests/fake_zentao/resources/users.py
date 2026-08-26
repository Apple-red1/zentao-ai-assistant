from ..route import Route

ROUTES = [
    Route('user.create', 'POST', '/api.php/v2/users', 'user', 'create', required_query=(), required_body=('account', 'realname', 'password', 'visions'), enum_values=(('visions', ('lite', 'rnd')),)),
    Route('user.edit', 'PUT', '/api.php/v2/users/{userID}', 'user', 'edit', required_query=(), required_body=('account',), enum_values=(('visions', ('lite', 'rnd')),)),
    Route('user.list', 'GET', '/api.php/v2/users', 'user', 'list', required_query=(), required_body=(), enum_values=(('browseType', ('inside', 'outside')),)),
    Route('user.view', 'GET', '/api.php/v2/users/{userID}', 'user', 'view', required_query=(), required_body=(), enum_values=()),
    Route('user.delete', 'DELETE', '/api.php/v2/users/{userID}', 'user', 'delete', required_query=(), required_body=(), enum_values=()),
]
