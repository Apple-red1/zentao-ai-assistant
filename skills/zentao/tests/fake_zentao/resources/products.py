from ..route import Route

ROUTES = [
    Route('product.create', 'POST', '/api.php/v2/products', 'product', 'create', required_query=(), required_body=('name',), enum_values=(('type', ('branch', 'normal', 'platform')), ('acl', ('open', 'private')))),
    Route('product.edit', 'PUT', '/api.php/v2/products/{productID}', 'product', 'edit', required_query=(), required_body=('name',), enum_values=(('type', ('branch', 'normal', 'platform')), ('acl', ('open', 'private')))),
    Route('product.list', 'GET', '/api.php/v2/products', 'product', 'list', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'closed', 'noclosed')),)),
    Route('product.list_program', 'GET', '/api.php/v2/programs/{programID}/products', 'product', 'list_program', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'closed', 'noclosed')),)),
    Route('product.view', 'GET', '/api.php/v2/products/{productID}', 'product', 'view', required_query=(), required_body=(), enum_values=()),
    Route('product.delete', 'DELETE', '/api.php/v2/products/{productID}', 'product', 'delete', required_query=(), required_body=(), enum_values=()),
]
