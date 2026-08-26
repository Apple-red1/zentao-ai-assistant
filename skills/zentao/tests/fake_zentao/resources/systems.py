from ..route import Route

ROUTES = [
    Route('system.create', 'POST', '/api.php/v2/systems', 'system', 'create', required_query=(), required_body=('productID', 'integrated', 'children', 'name'), enum_values=()),
    Route('system.edit', 'PUT', '/api.php/v2/systems/{systemID}', 'system', 'edit', required_query=(), required_body=('name', 'children'), enum_values=()),
    Route('system.list_product', 'GET', '/api.php/v2/products/{productID}/systems', 'system', 'list_product', required_query=(), required_body=(), enum_values=()),
]
