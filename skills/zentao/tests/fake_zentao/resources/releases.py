from ..route import Route

ROUTES = [
    Route('release.create', 'POST', '/api.php/v2/releases', 'release', 'create', required_query=(), required_body=('productID', 'system', 'name', 'build', 'date'), enum_values=(('status', ('fail', 'normal', 'terminate', 'wait')),)),
    Route('release.edit', 'PUT', '/api.php/v2/releases/{releaseID}', 'release', 'edit', required_query=(), required_body=('productID', 'product', 'system', 'name', 'build', 'date'), enum_values=(('status', ('fail', 'normal', 'terminate', 'wait')),)),
    Route('release.list_product', 'GET', '/api.php/v2/products/{productID}/releases', 'release', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'fail', 'normal', 'terminate', 'wait')),)),
    Route('release.delete', 'DELETE', '/api.php/v2/releases/{releaseID}', 'release', 'delete', required_query=(), required_body=(), enum_values=()),
]
