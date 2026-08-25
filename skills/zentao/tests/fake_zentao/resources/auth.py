from ..route import Route

ROUTES = [
    Route('token.login', 'POST', '/api.php/v2/users/login', 'token', 'login', required_query=(), required_body=('account', 'password'), enum_values=()),
]
